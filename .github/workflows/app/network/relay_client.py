"""
StorageShare - Relay Client Module
Connects devices over the internet via a relay server
"""

import socket
import threading
import json
import time
import struct
from app.utils.constants import DEFAULT_PORT, BUFFER_SIZE
from app.network.protocol import Message


class RelayClient:
    """Client for connecting to a relay server for internet-based device discovery"""

    def __init__(self, device_id, device_name, relay_host, relay_port=8080):
        self.device_id = device_id
        self.device_name = device_name
        self.relay_host = relay_host
        self.relay_port = relay_port
        self.sock = None
        self.connected = False
        self._receive_thread = None
        self._message_handlers = {}
        self._lock = threading.Lock()
        self.session_id = None

    def connect(self):
        """Connect to the relay server"""
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(10.0)
            self.sock.connect((self.relay_host, self.relay_port))
            self.sock.settimeout(60.0)

            # Register with relay server
            register_msg = {
                "action": "register",
                "device_id": self.device_id,
                "device_name": self.device_name
            }
            self._send_raw(register_msg)

            # Receive session
            response = self._receive_raw()
            if response and response.get("status") == "ok":
                self.session_id = response.get("session_id")
                self.connected = True

                self._receive_thread = threading.Thread(
                    target=self._receive_loop,
                    daemon=True
                )
                self._receive_thread.start()
                return True

            return False
        except Exception as e:
            print(f"[RelayClient] Connection failed: {e}")
            return False

    def disconnect(self):
        """Disconnect from relay server"""
        self.connected = False
        if self.sock:
            try:
                self.sock.close()
            except:
                pass

    def send_to_device(self, target_device_id, message):
        """Send a message to another device via relay"""
        if not self.connected:
            return False
        payload = {
            "action": "relay",
            "target_device_id": target_device_id,
            "message": {
                "type": message.type,
                "sender_id": message.sender_id,
                "sender_name": message.sender_name,
                "payload": message.payload
            }
        }
        return self._send_raw(payload)

    def send_message(self, message):
        """Send a regular message via relay"""
        return self.send_to_device("*", message)

    def _send_raw(self, data_dict):
        """Send raw JSON data"""
        with self._lock:
            try:
                data = json.dumps(data_dict).encode('utf-8')
                self.sock.sendall(struct.pack('!I', len(data)) + data)
                return True
            except:
                self.connected = False
                return False

    def _receive_raw(self):
        """Receive raw JSON data"""
        try:
            raw_len = self.sock.recv(4)
            if not raw_len:
                return None
            msg_len = struct.unpack('!I', raw_len)[0]
            data = b''
            while len(data) < msg_len:
                chunk = self.sock.recv(min(msg_len - len(data), BUFFER_SIZE))
                if not chunk:
                    return None
                data += chunk
            return json.loads(data.decode('utf-8'))
        except:
            return None

    def _receive_loop(self):
        """Receive messages from relay"""
        while self.connected:
            try:
                data = self._receive_raw()
                if data is None:
                    break

                msg_type = data.get("type", "")
                if msg_type in self._message_handlers:
                    msg = Message(
                        msg_type=msg_type,
                        sender_id=data.get("sender_id", ""),
                        sender_name=data.get("sender_name", ""),
                        payload=data.get("payload", {})
                    )
                    try:
                        self._message_handlers[msg_type](msg.sender_id, msg)
                    except Exception as e:
                        print(f"[RelayClient] Handler error: {e}")
            except:
                break
        self.connected = False

    def register_handler(self, msg_type, handler):
        """Register a message handler"""
        self._message_handlers[msg_type] = handler

    def get_online_devices(self):
        """Get list of online devices from relay"""
        if not self.connected:
            return []
        self._send_raw({"action": "list_devices"})
        response = self._receive_raw()
        if response and response.get("status") == "ok":
            return response.get("devices", [])
        return []