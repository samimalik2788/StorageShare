"""
StorageShare - Internet Relay Server
Lightweight server to help devices find each other over the internet
"""

import socket
import threading
import json
import struct
import time
from http.server import HTTPServer, BaseHTTPRequestHandler

# In-memory device registry
devices = {}  # session_id -> {device_id, device_name, socket, address, last_seen}
devices_lock = threading.Lock()


class RelayHandler(BaseHTTPRequestHandler):
    """Simple HTTP relay handler for device registration and routing"""

    def do_GET(self):
        if self.path == '/status':
            self._send_json({"status": "ok", "devices_online": len(devices), "version": "1.0.0"})
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode('utf-8')

        try:
            data = json.loads(body)
            action = data.get('action', '')

            if action == 'register':
                device_id = data.get('device_id')
                device_name = data.get('device_name')
                session_id = f"{device_id}_{int(time.time())}"

                with devices_lock:
                    devices[session_id] = {
                        'device_id': device_id,
                        'device_name': device_name,
                        'address': self.client_address,
                        'last_seen': time.time()
                    }

                self._send_json({"status": "ok", "session_id": session_id})

            elif action == 'list_devices':
                with devices_lock:
                    device_list = [
                        {
                            'device_id': d['device_id'],
                            'device_name': d['device_name'],
                            'address': f"{d['address'][0]}:{d['address'][1]}"
                        }
                        for d in devices.values()
                    ]
                self._send_json({"status": "ok", "devices": device_list})

            elif action == 'relay':
                target_id = data.get('target_device_id')
                message = data.get('message', {})
                self._route_message(target_id, message)
                self._send_json({"status": "ok", "relayed": True})

            else:
                self._send_json({"status": "error", "message": "Unknown action"})

        except Exception as e:
            self._send_json({"status": "error", "message": str(e)})

    def _send_json(self, data):
        response = json.dumps(data).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(response)))
        self.end_headers()
        self.wfile.write(response)

    def _route_message(self, target_id, message):
        """Route message to target device or broadcast"""
        with devices_lock:
            for session_id, device_info in devices.items():
                if target_id == '*' or device_info['device_id'] == target_id:
                    # In a full implementation, this would forward via TCP
                    pass

    def log_message(self, format, *args):
        """Override to reduce logging noise"""
        if '/status' not in str(args):
            super().log_message(format, *args)


class TCPRelayServer:
    """TCP-based relay server for device communication"""

    def __init__(self, host='0.0.0.0', port=8080):
        self.host = host
        self.port = port
        self.server = None
        self.running = False
        self._client_connections = {}  # device_id -> socket

    def start(self):
        """Start the TCP relay server"""
        try:
            self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server.bind((self.host, self.port))
            self.server.listen(10)
            self.server.settimeout(1.0)
            self.running = True

            thread = threading.Thread(target=self._accept_loop, daemon=True)
            thread.start()

            print(f"[Relay Server] Listening on {self.host}:{self.port}")
            return True
        except Exception as e:
            print(f"[Relay Server] Failed to start: {e}")
            return False

    def stop(self):
        """Stop the relay server"""
        self.running = False
        if self.server:
            try:
                self.server.close()
            except:
                pass

    def _accept_loop(self):
        """Accept incoming relay connections"""
        while self.running:
            try:
                client_sock, addr = self.server.accept()
                thread = threading.Thread(
                    target=self._handle_client,
                    args=(client_sock, addr),
                    daemon=True
                )
                thread.start()
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    time.sleep(0.5)

    def _handle_client(self, client_sock, addr):
        """Handle a relay client connection"""
        device_id = None
        try:
            while self.running:
                raw_len = client_sock.recv(4)
                if not raw_len:
                    break
                msg_len = struct.unpack('!I', raw_len)[0]
                data = b''
                while len(data) < msg_len:
                    chunk = client_sock.recv(min(msg_len - len(data), 8192))
                    if not chunk:
                        break
                    data += chunk

                if not data:
                    break

                msg = json.loads(data.decode('utf-8'))
                action = msg.get('action', '')

                if action == 'register':
                    device_id = msg.get('device_id')
                    device_name = msg.get('device_name', 'Unknown')
                    session_id = f"{device_id}_{int(time.time())}"

                    with devices_lock:
                        self._client_connections[device_id] = client_sock
                        devices[session_id] = {
                            'device_id': device_id,
                            'device_name': device_name,
                            'address': addr,
                            'last_seen': time.time()
                        }

                    response = {"status": "ok", "session_id": session_id}
                    self._send_raw(client_sock, response)
                    print(f"[Relay] Device registered: {device_name} ({device_id[:8]}...)")

                elif action == 'relay':
                    target_id = msg.get('target_device_id', '')
                    message = msg.get('message', {})

                    if target_id in self._client_connections:
                        target_sock = self._client_connections[target_id]
                        forward_msg = {
                            "type": message.get("type", ""),
                            "sender_id": message.get("sender_id", ""),
                            "sender_name": message.get("sender_name", ""),
                            "payload": message.get("payload", {})
                        }
                        self._send_raw(target_sock, forward_msg)
                        response = {"status": "ok", "relayed": True}
                    else:
                        response = {"status": "error", "message": "Device not found"}

                    self._send_raw(client_sock, response)

                elif action == 'list_devices':
                    device_list = []
                    with devices_lock:
                        for d in devices.values():
                            device_list.append({
                                'device_id': d['device_id'],
                                'device_name': d['device_name']
                            })
                    self._send_raw(client_sock, {"status": "ok", "devices": device_list})

        except Exception as e:
            print(f"[Relay] Client error: {e}")
        finally:
            if device_id:
                with devices_lock:
                    if device_id in self._client_connections:
                        del self._client_connections[device_id]
                    # Also clean up from devices dict
                    to_remove = [k for k, v in devices.items() if v['device_id'] == device_id]
                    for k in to_remove:
                        del devices[k]
            try:
                client_sock.close()
            except:
                pass

    def _send_raw(self, sock, data_dict):
        """Send raw JSON data over socket"""
        try:
            data = json.dumps(data_dict).encode('utf-8')
            sock.sendall(struct.pack('!I', len(data)) + data)
            return True
        except:
            return False


def start_http_relay(port=5000):
    """Start HTTP relay server (lighter weight)"""
    server = HTTPServer(('0.0.0.0', port), RelayHandler)
    print(f"[HTTP Relay] Listening on port {port}")
    server.serve_forever()


if __name__ == '__main__':
    import sys
    
    print("StorageShare Relay Server")
    print("========================")
    
    port = 8080
    if len(sys.argv) > 1:
        port = int(sys.argv[1])

    # Start TCP relay
    tcp_relay = TCPRelayServer(port=port)
    if tcp_relay.start():
        print(f"TCP Relay running on port {port}")
        print("Press Ctrl+C to stop")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nShutting down...")
            tcp_relay.stop()