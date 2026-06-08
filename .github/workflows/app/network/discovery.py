"""
StorageShare - Device Discovery Module
UDP broadcast for discovering nearby devices on local network
"""

import socket
import threading
import json
import time
import struct
from app.utils.constants import DISCOVERY_PORT, BROADCAST_ADDR, DISCOVERY_INTERVAL, DEVICE_TIMEOUT
from app.network.protocol import ProtocolHandler, Message


class DeviceDiscovery:
    """Handles UDP broadcast discovery of nearby devices"""

    def __init__(self, device_id, device_name, on_device_found=None, on_device_lost=None):
        self.device_id = device_id
        self.device_name = device_name
        self.on_device_found = on_device_found  # callback(device_id, device_name, ip_address)
        self.on_device_lost = on_device_lost  # callback(device_id)
        self.running = False
        self.sock = None
        self._discovered_devices = {}  # device_id -> {name, ip, last_seen, quota_mb, used_mb}
        self._broadcast_thread = None
        self._listen_thread = None
        self._cleanup_thread = None

    def start(self):
        """Start discovery service (broadcast + listen)"""
        self.running = True

        # Create UDP socket
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            self.sock.bind(('', DISCOVERY_PORT))
            self.sock.settimeout(1.0)
        except Exception as e:
            print(f"[Discovery] Socket error: {e}")
            return False

        # Start threads
        self._broadcast_thread = threading.Thread(target=self._broadcast_loop, daemon=True)
        self._listen_thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)

        self._broadcast_thread.start()
        self._listen_thread.start()
        self._cleanup_thread.start()

        print(f"[Discovery] Started discovery for {self.device_name} ({self.device_id})")
        return True

    def stop(self):
        """Stop discovery service"""
        self.running = False
        if self.sock:
            try:
                self.sock.close()
            except:
                pass
            self.sock = None
        print("[Discovery] Stopped")

    def _broadcast_loop(self):
        """Continuously broadcast discovery requests"""
        while self.running:
            try:
                if self.sock:
                    msg = ProtocolHandler.create_discovery_request(
                        self.device_id, self.device_name
                    )
                    data = msg.to_json().encode('utf-8')
                    self.sock.sendto(data, (BROADCAST_ADDR, DISCOVERY_PORT))
            except Exception as e:
                pass
            time.sleep(DISCOVERY_INTERVAL)

    def _listen_loop(self):
        """Listen for discovery requests and responses"""
        while self.running:
            try:
                if not self.sock:
                    time.sleep(0.5)
                    continue

                data, addr = self.sock.recvfrom(1024)
                msg = Message.from_json(data.decode('utf-8'))
                if msg is None:
                    continue

                # Ignore messages from self
                if msg.sender_id == self.device_id:
                    continue

                ip_address = addr[0]

                if msg.type == "DISCOVERY_REQ":
                    # Respond to discovery request
                    response = ProtocolHandler.create_discovery_response(
                        self.device_id, self.device_name
                    )
                    self.sock.sendto(response.to_json().encode('utf-8'), (ip_address, DISCOVERY_PORT))

                    # Add to discovered devices
                    self._update_device(msg.sender_id, msg.sender_name, ip_address)

                elif msg.type == "DISCOVERY_RES":
                    # Process discovery response
                    quota_mb = msg.payload.get("quota_mb", 0)
                    used_mb = msg.payload.get("used_mb", 0)
                    self._update_device(
                        msg.sender_id, msg.sender_name, ip_address,
                        quota_mb=quota_mb, used_mb=used_mb
                    )

            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    time.sleep(0.5)

    def _update_device(self, device_id, device_name, ip_address, quota_mb=0, used_mb=0):
        """Add or update a discovered device"""
        is_new = device_id not in self._discovered_devices
        self._discovered_devices[device_id] = {
            'name': device_name,
            'ip': ip_address,
            'last_seen': time.time(),
            'quota_mb': quota_mb,
            'used_mb': used_mb
        }
        if is_new and self.on_device_found:
            self.on_device_found(device_id, device_name, ip_address)

    def _cleanup_loop(self):
        """Remove devices that haven't been seen recently"""
        while self.running:
            now = time.time()
            lost_devices = []
            for device_id, info in self._discovered_devices.items():
                if now - info['last_seen'] > DEVICE_TIMEOUT:
                    lost_devices.append(device_id)

            for device_id in lost_devices:
                if self.on_device_lost:
                    self.on_device_lost(device_id)
                del self._discovered_devices[device_id]

            time.sleep(DEVICE_TIMEOUT // 2)

    def get_discovered_devices(self):
        """Get list of currently discovered devices"""
        return dict(self._discovered_devices)

    def get_device_ip(self, device_id):
        """Get IP address of a discovered device"""
        if device_id in self._discovered_devices:
            return self._discovered_devices[device_id]['ip']
        return None

    def is_device_available(self, device_id):
        """Check if a device was recently seen"""
        if device_id in self._discovered_devices:
            now = time.time()
            return (now - self._discovered_devices[device_id]['last_seen']) < DEVICE_TIMEOUT
        return False