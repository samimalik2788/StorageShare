"""
StorageShare - TCP Client Module
Connects to other devices for communication and file transfer
"""

import socket
import threading
import json
import struct
import time
from app.utils.constants import DEFAULT_PORT, BUFFER_SIZE
from app.network.protocol import Message


class StorageClient:
    """TCP client that connects to a remote device"""

    def __init__(self, device_id, device_name):
        self.device_id = device_id
        self.device_name = device_name
        self.sock = None
        self.connected = False
        self.remote_id = None
        self.remote_name = ""
        self._receive_thread = None
        self._message_handlers = {}
        self._lock = threading.Lock()

    def connect(self, host, port=DEFAULT_PORT, timeout=10.0):
        """Connect to a remote device"""
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(timeout)
            self.sock.connect((host, port))
            self.sock.settimeout(60.0)
            self.connected = True

            # Start receive thread
            self._receive_thread = threading.Thread(
                target=self._receive_loop,
                daemon=True
            )
            self._receive_thread.start()

            print(f"[Client] Connected to {host}:{port}")
            return True
        except Exception as e:
            print(f"[Client] Connection failed to {host}:{port} - {e}")
            self.connected = False
            return False

    def disconnect(self):
        """Disconnect from remote device"""
        self.connected = False
        if self.sock:
            try:
                self.sock.close()
            except:
                pass
            self.sock = None
        self.remote_id = None
        self.remote_name = ""
        print("[Client] Disconnected")

    def send_message(self, message):
        """Send a message to the connected device"""
        with self._lock:
            if self.sock and self.connected:
                try:
                    data = message.to_json().encode('utf-8')
                    self.sock.sendall(struct.pack('!I', len(data)) + data)
                    return True
                except Exception as e:
                    print(f"[Client] Send error: {e}")
                    self.connected = False
        return False

    def _receive_loop(self):
        """Continuously receive messages from the remote device"""
        while self.connected:
            try:
                data = self._receive_message()
                if data is None:
                    break

                msg = Message.from_json(data)
                if msg is None:
                    continue

                self.remote_id = msg.sender_id
                self.remote_name = msg.sender_name

                # Handle the message
                if msg.type in self._message_handlers:
                    try:
                        self._message_handlers[msg.type](msg.sender_id, msg)
                    except Exception as e:
                        print(f"[Client] Handler error for {msg.type}: {e}")

            except Exception as e:
                if self.connected:
                    print(f"[Client] Receive error: {e}")
                break

        self.connected = False
        # Notify disconnection
        if "DISCONNECT" in self._message_handlers:
            try:
                self._message_handlers["DISCONNECT"](None, None)
            except:
                pass

    def _receive_message(self):
        """Receive a complete message (length-prefixed)"""
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
            return data.decode('utf-8')
        except:
            return None

    def register_handler(self, msg_type, handler):
        """Register a handler for a specific message type"""
        self._message_handlers[msg_type] = handler

    def is_connected(self):
        """Check if client is connected"""
        return self.connected