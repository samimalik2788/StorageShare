"""
StorageShare - TCP Server Module
Handles incoming connections from other devices
"""

import socket
import threading
import json
import base64
import os
import time
import struct
from app.utils.constants import DEFAULT_PORT, BUFFER_SIZE
from app.network.protocol import Message


class StorageServer:
    """TCP server that listens for connections from other devices"""

    def __init__(self, device_id, device_name, host='0.0.0.0', port=DEFAULT_PORT):
        self.device_id = device_id
        self.device_name = device_name
        self.host = host
        self.port = port
        self.running = False
        self.server_sock = None
        self._clients = {}  # client_id -> {socket, thread, address}
        self._message_handlers = {}
        self._lock = threading.Lock()

    def start(self):
        """Start the TCP server"""
        try:
            self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_sock.bind((self.host, self.port))
            self.server_sock.listen(5)
            self.server_sock.settimeout(1.0)
            self.running = True

            self._accept_thread = threading.Thread(target=self._accept_loop, daemon=True)
            self._accept_thread.start()

            print(f"[Server] Listening on {self.host}:{self.port}")
            return True
        except Exception as e:
            print(f"[Server] Failed to start: {e}")
            return False

    def stop(self):
        """Stop the server"""
        self.running = False
        with self._lock:
            for client_id, client_info in self._clients.items():
                try:
                    client_info['socket'].close()
                except:
                    pass
            self._clients.clear()
        if self.server_sock:
            try:
                self.server_sock.close()
            except:
                pass
        print("[Server] Stopped")

    def _accept_loop(self):
        """Accept incoming connections"""
        while self.running:
            try:
                client_sock, addr = self.server_sock.accept()
                client_sock.settimeout(60.0)
                client_thread = threading.Thread(
                    target=self._handle_client,
                    args=(client_sock, addr),
                    daemon=True
                )
                client_thread.start()
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    time.sleep(0.5)

    def _handle_client(self, client_sock, addr):
        """Handle a connected client"""
        client_id = None
        try:
            while self.running:
                data = self._receive_message(client_sock)
                if data is None:
                    break

                msg = Message.from_json(data)
                if msg is None:
                    continue

                client_id = msg.sender_id

                # Register client
                with self._lock:
                    if client_id not in self._clients:
                        self._clients[client_id] = {
                            'socket': client_sock,
                            'thread': threading.current_thread(),
                            'address': addr,
                            'name': msg.sender_name
                        }

                # Handle the message
                if msg.type in self._message_handlers:
                    try:
                        self._message_handlers[msg.type](client_id, msg)
                    except Exception as e:
                        print(f"[Server] Handler error for {msg.type}: {e}")

        except Exception as e:
            print(f"[Server] Client error: {e}")
        finally:
            if client_id:
                with self._lock:
                    if client_id in self._clients:
                        del self._clients[client_id]
                # Notify disconnection
                if "DISCONNECT" in self._message_handlers:
                    try:
                        self._message_handlers["DISCONNECT"](client_id, None)
                    except:
                        pass
            try:
                client_sock.close()
            except:
                pass

    def _receive_message(self, sock):
        """Receive a complete message (length-prefixed)"""
        try:
            # Read 4-byte length prefix
            raw_len = sock.recv(4)
            if not raw_len:
                return None
            msg_len = struct.unpack('!I', raw_len)[0]

            # Read the actual message
            data = b''
            while len(data) < msg_len:
                chunk = sock.recv(min(msg_len - len(data), BUFFER_SIZE))
                if not chunk:
                    return None
                data += chunk
            return data.decode('utf-8')
        except:
            return None

    def send_message(self, client_id, message):
        """Send a message to a specific client"""
        with self._lock:
            if client_id in self._clients:
                try:
                    data = message.to_json().encode('utf-8')
                    # Send length-prefixed message
                    self._clients[client_id]['socket'].sendall(
                        struct.pack('!I', len(data)) + data
                    )
                    return True
                except Exception as e:
                    print(f"[Server] Send error to {client_id}: {e}")
                    del self._clients[client_id]
        return False

    def broadcast(self, message, exclude=None):
        """Send message to all connected clients"""
        with self._lock:
            for client_id in list(self._clients.keys()):
                if client_id != exclude:
                    self.send_message(client_id, message)

    def register_handler(self, msg_type, handler):
        """Register a handler for a specific message type"""
        self._message_handlers[msg_type] = handler

    def get_connected_clients(self):
        """Get list of connected client IDs"""
        with self._lock:
            return list(self._clients.keys())

    def get_client_info(self, client_id):
        """Get info about a connected client"""
        with self._lock:
            if client_id in self._clients:
                info = self._clients[client_id]
                return {
                    'id': client_id,
                    'name': info['name'],
                    'address': info['address']
                }
        return None

    def disconnect_client(self, client_id):
        """Forcefully disconnect a client"""
        with self._lock:
            if client_id in self._clients:
                try:
                    self._clients[client_id]['socket'].close()
                except:
                    pass
                del self._clients[client_id]

