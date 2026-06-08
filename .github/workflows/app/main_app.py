"""
StorageShare - Main Application Class
Ties together UI, networking, security, and storage modules
"""

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.core.window import Window
from kivy.clock import Clock
from kivy.lang import Builder

from app.utils.constants import APP_NAME, APP_VERSION, DEFAULT_PORT
from app.security.pairing import PairingManager, DeviceIdentity
from app.database.models import DatabaseManager
from app.network.discovery import DeviceDiscovery
from app.network.server import StorageServer
from app.network.client import StorageClient
from app.network.protocol import ProtocolHandler, Message
from app.network.relay_client import RelayClient
from app.storage.file_manager import FileManager
from app.screens.splash_screen import SplashScreen
from app.screens.home_screen import HomeScreen
from app.screens.discovery_screen import DiscoveryScreen
from app.screens.pairing_screen import PairingScreen
from app.screens.storage_screen import StorageScreen
from app.screens.transfer_screen import TransferScreen
from app.screens.settings_screen import SettingsScreen

import os
import threading


class StorageShareApp(App):
    """Main StorageShare Application"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.title = APP_NAME

        # Device identity
        self.device_id = None
        self.device_name = None

        # Managers
        self.pairing_manager = PairingManager()
        self.db_manager = DatabaseManager()
        self.file_manager = FileManager()

        # Network components
        self.discovery = None
        self.server = None
        self.clients = {}  # device_id -> StorageClient
        self.relay_client = None
        self._current_client = None  # Currently active client

        # Active transfers
        self._active_transfers = {}

    def build(self):
        """Build the application UI"""
        # Initialize device identity
        self._init_device_identity()

        # Set theme
        self.theme_cls.primary_palette = "Green"
        self.theme_cls.accent_palette = "Teal"
        self.theme_cls.theme_style = "Light"

        # Create screen manager
        sm = ScreenManager()
        sm.add_widget(SplashScreen(name='splash'))
        sm.add_widget(HomeScreen(name='home'))
        sm.add_widget(DiscoveryScreen(name='discover'))
        sm.add_widget(PairingScreen(name='pairing'))
        sm.add_widget(StorageScreen(name='storage'))
        sm.add_widget(TransferScreen(name='transfer'))
        sm.add_widget(SettingsScreen(name='settings'))

        # Start network services
        Clock.schedule_once(lambda dt: self._start_network_services(), 1)

        return sm

    def _init_device_identity(self):
        """Initialize or load device identity"""
        self.device_id = DeviceIdentity.generate_device_id()
        self.device_name = DeviceIdentity.get_device_name()
        if not self.device_name or self.device_name == "Unknown":
            self.device_name = f"Android-{self.device_id[:8]}"

    def _start_network_services(self):
        """Start discovery and server"""
        # Start device discovery
        self.discovery = DeviceDiscovery(
            self.device_id,
            self.device_name,
            on_device_found=self._on_device_discovered,
            on_device_lost=self._on_device_lost
        )
        self.discovery.start()

        # Start TCP server
        self.server = StorageServer(self.device_id, self.device_name)
        self.server.start()

        # Register server message handlers
        self._register_server_handlers()

    def _register_server_handlers(self):
        """Register handlers for incoming server messages"""
        from app.utils.constants import MSG_TYPE

        self.server.register_handler(MSG_TYPE["PAIRING_REQUEST"], self._handle_pairing_request)
        self.server.register_handler(MSG_TYPE["PAIRING_CODE"], self._handle_pairing_code)
        self.server.register_handler(MSG_TYPE["PAIRING_VERIFIED"], self._handle_pairing_verified)
        self.server.register_handler(MSG_TYPE["PAIRING_FAILED"], self._handle_pairing_failed)
        self.server.register_handler(MSG_TYPE["FILE_LIST_REQUEST"], self._handle_file_list_request)
        self.server.register_handler(MSG_TYPE["FILE_UPLOAD_REQUEST"], self._handle_upload_request)
        self.server.register_handler(MSG_TYPE["FILE_CHUNK"], self._handle_file_chunk)
        self.server.register_handler(MSG_TYPE["FILE_DOWNLOAD_REQUEST"], self._handle_download_request)
        self.server.register_handler(MSG_TYPE["CREATE_FOLDER_REQUEST"], self._handle_create_folder_request)
        self.server.register_handler(MSG_TYPE["DISCONNECT"], self._handle_disconnect)
        self.server.register_handler(MSG_TYPE["PING"], self._handle_ping)

    def _on_device_discovered(self, device_id, device_name, ip_address):
        """Callback when a new device is discovered"""
        # Check if already paired
        device = self.db_manager.get_device(device_id)
        if device:
            self.db_manager.update_device_status(device_id, True, ip_address)
        else:
            self.db_manager.add_device(device_name, device_id, ip_address)

        # If discovery screen is active, update UI
        screen = self._get_screen('discover')
        if screen:
            self._update_discovery_ui()

    def _on_device_lost(self, device_id):
        """Callback when a device is no longer visible"""
        self.db_manager.update_device_status(device_id, False)
        screen = self._get_screen('discover')
        if screen:
            self._update_discovery_ui()

    # ===== Screen Navigation =====

    def go_home(self):
        """Navigate to home screen"""
        self.root.current = 'home'
        self.root.transition.direction = 'right'

    def go_to_discovery(self):
        """Navigate to discovery screen"""
        self.root.current = 'discover'
        self.root.transition.direction = 'left'

    def switch_to(self, screen_name):
        """Switch to a screen"""
        if screen_name == 'home':
            self.go_home()
        elif screen_name == 'discover':
            self.go_to_discovery()
        elif screen_name == 'settings':
            self.root.current = 'settings'

    def switch_to_internet_discovery(self):
        """Switch to internet discovery mode"""
        self.show_snackbar("Internet mode - Enter relay server in Settings")

    def open_device_storage(self, device_id):
        """Open storage browser for a paired device"""
        device = self.db_manager.get_device(device_id)
        if not device:
            self.show_snackbar("Device not found")
            return

        # Connect to the device
        self._connect_to_device(device_id, device['ip_address'], device['port'])

        # Navigate to storage screen
        screen = self._get_screen('storage')
        screen.open_device(device_id, device['device_name'])
        self.root.current = 'storage'

    # ===== Discovery =====

    def start_discovery_view(self):
        """Start updating discovery UI"""
        self._update_discovery_ui()

    def stop_discovery_view(self):
        """Stop updating discovery UI"""
        pass

    def _update_discovery_ui(self):
        """Update the discovery screen with found devices"""
        screen = self._get_screen('discover')
        if not screen:
            return

        container = screen.ids.devices_container
        container.clear_widgets()

        devices = self.discovery.get_discovered_devices() if self.discovery else {}
        for device_id, info in devices.items():
            # Skip self
            if device_id == self.device_id:
                continue

            from app.screens.discovery_screen import DiscoveredDeviceCard
            card = DiscoveredDeviceCard()
            card.device_id = device_id
            card.device_name = info['name']
            card.ip_address = info['ip']
            container.add_widget(card)

        # Update status
        count = len([d for d in devices if d != self.device_id])
        screen.ids.status_label.text = f"Found {count} device(s) nearby"

    # ===== Pairing =====

    def request_pairing(self, device_id, device_name, ip_address):
        """Start pairing process with a discovered device"""
        # Navigate to pairing screen as requestor
        screen = self._get_screen('pairing')
        screen.setup_requestor(device_id, device_name, ip_address)
        self.root.current = 'pairing'

    def start_pairing_request(self, target_device_id, target_device_name, target_ip):
        """Generate pairing code and send pairing request"""
        # Generate 4-digit code
        code = self.pairing_manager.generate_pairing_code(self.device_id)

        # Connect to target device and send pairing request
        client = StorageClient(self.device_id, self.device_name)
        if client.connect(target_ip, DEFAULT_PORT):
            self._current_client = client
            self.clients[target_device_id] = client

            # Register handlers for pairing flow
            client.register_handler("PAIRING_VER", self._handle_pairing_verified_client)
            client.register_handler("PAIRING_FAIL", self._handle_pairing_failed_client)

            # Send pairing request
            req = ProtocolHandler.create_pairing_request(self.device_id, self.device_name)
            client.send_message(req)

            # Send the code for verification
            code_msg = ProtocolHandler.create_pairing_code_message(
                self.device_id, self.device_name, code
            )
            client.send_message(code_msg)

            return code
        else:
            self.show_snackbar("Failed to connect to device")
            return None

    def submit_pairing(self):
        """Submit pairing code and quota to grant access"""
        screen = self._get_screen('pairing')
        code = screen.get_entered_code()
        quota_mb = screen.get_quota_mb()

        if len(code) != 4:
            screen.ids.error_label.text = "Please enter the complete 4-digit code"
            return

        # Verify pairing code
        success, result = self.pairing_manager.verify_pairing_code(
            screen.target_device_id, code
        )

        if success:
            # Store pairing in database
            self.db_manager.add_device(
                screen.target_device_name,
                screen.target_device_id,
                screen.target_ip,
                quota_mb=quota_mb
            )

            # Send verified response to requestor
            verified_msg = ProtocolHandler.create_pairing_verified(
                self.device_id,
                self.device_name,
                result,  # session token
                quota_mb
            )

            if self._current_client and self._current_client.is_connected():
                self._current_client.send_message(verified_msg)

            self.show_snackbar(f"Access granted! {quota_mb}MB shared")
            self.go_home()
        else:
            screen.ids.error_label.text = result

    def _handle_pairing_request(self, client_id, msg):
        """Handle incoming pairing request (Device A requests access)"""
        if not msg:
            return

        # Navigate to pairing screen as grantor
        screen = self._get_screen('pairing')
        screen.setup_grantor(client_id, msg.sender_name, "")

        Clock.schedule_once(lambda dt: self._switch_to_screen('pairing'))

    def _handle_pairing_code(self, client_id, msg):
        """Handle incoming pairing code"""
        if not msg:
            return
        code = msg.payload.get("code", "")
        self.pairing_manager._pending_codes[client_id] = {
            'code': code,
            'timestamp': msg.timestamp,
            'attempts': 0
        }

    def _handle_pairing_verified(self, client_id, msg):
        """Handle pairing verified response"""
        if not msg:
            return
        session_token = msg.payload.get("session_token", "")
        quota_mb = msg.payload.get("quota_mb", 1024)

        # Store in database
        device = self.db_manager.get_device(client_id)
        if device:
            self.db_manager.set_session_token(client_id, session_token)
            self.db_manager.update_device_quota(client_id, quota_mb)
            self.db_manager.update_device_status(client_id, True)

        self.show_snackbar("Pairing successful!")
        self.go_home()

    def _handle_pairing_failed(self, client_id, msg):
        """Handle pairing failed"""
        if not msg:
            return
        reason = msg.payload.get("reason", "Unknown error")
        self.show_snackbar(f"Pairing failed: {reason}")
        self.go_home()

    def _handle_pairing_verified_client(self, sender_id, msg):
        """Client-side handler for pairing verified"""
        self._handle_pairing_verified(sender_id, msg)

    def _handle_pairing_failed_client(self, sender_id, msg):
        """Client-side handler for pairing failed"""
        self._handle_pairing_failed(sender_id, msg)

    def set_quota_preset(self, value):
        """Set quota preset from pairing screen buttons"""
        screen = self._get_screen('pairing')
        if screen:
            screen.set_quota(int(value))

    # ===== Remote Storage Operations =====

    def request_file_list(self, device_id, path):
        """Request file list from remote device"""
        client = self._get_client(device_id)
        if not client:
            return

        device = self.db_manager.get_device(device_id)
        session_token = device['session_token'] if device else ""

        msg = ProtocolHandler.create_file_list_request(
            self.device_id, self.device_name, path, session_token
        )
        client.send_message(msg)

    def create_remote_folder(self, device_id, folder_path):
        """Request to create a folder on remote device"""
        client = self._get_client(device_id)
        if not client:
            return

        device = self.db_manager.get_device(device_id)
        session_token = device['session_token'] if device else ""

        msg = ProtocolHandler.create_create_folder_request(
            self.device_id, self.device_name, folder_path, session_token
        )
        client.send_message(msg)

    def upload_file(self):
        """Upload selected file to remote device"""
        # This would use a file chooser dialog
        self.show_snackbar("Select a file to upload (file picker)")

    def download_file(self, file_path):
        """Download a file from remote device"""
        # Get current storage screen context
        screen = self._get_screen('storage')
        if not screen:
            return

        device_id = screen.current_device_id
        client = self._get_client(device_id)
        if not client:
            return

        device = self.db_manager.get_device(device_id)
        session_token = device['session_token'] if device else ""

        msg = ProtocolHandler.create_download_request(
            self.device_id, self.device_name, file_path, session_token
        )
        client.send_message(msg)

    def show_create_folder_dialog(self):
        """Show dialog to create a new folder"""
        from kivy.uix.textinput import TextInput
        from kivy.uix.boxlayout import BoxLayout
        from kivy.uix.popup import Popup
        from kivy.uix.button import Button

        content = BoxLayout(orientation='vertical', spacing=10, padding=10)
        text_input = TextInput(hint_text='Folder name', multiline=False)
        content.add_widget(text_input)

        btn_layout = BoxLayout(orientation='horizontal', spacing=10, size_hint_y=None, height=40)

        def on_confirm(instance):
            screen = self._get_screen('storage')
            if screen and text_input.text.strip():
                screen.create_folder(text_input.text.strip())
            popup.dismiss()

        def on_cancel(instance):
            popup.dismiss()

        confirm_btn = Button(text='Create', on_release=on_confirm)
        cancel_btn = Button(text='Cancel', on_release=on_cancel)
        btn_layout.add_widget(confirm_btn)
        btn_layout.add_widget(cancel_btn)
        content.add_widget(btn_layout)

        popup = Popup(title='Create Folder', content=content,
                      size_hint=(0.8, 0.4), auto_dismiss=False)
        popup.open()

    def on_file_click(self, file_path, is_dir):
        """Handle file/folder click in storage browser"""
        screen = self._get_screen('storage')
        if screen and is_dir:
            screen.navigate_to(file_path)

    def go_up_directory(self):
        """Go up one directory in storage browser"""
        screen = self._get_screen('storage')
        if screen:
            screen.go_up()

    # ===== Server Handlers =====

    def _handle_file_list_request(self, client_id, msg):
        """Handle file list request from remote device"""
        if not msg:
            return
        path = msg.payload.get("path", "/")
        files = self.file_manager.list_files(path)
        response = ProtocolHandler.create_file_list_response(
            self.device_id, self.device_name, files
        )
        self.server.send_message(client_id, response)

    def _handle_upload_request(self, client_id, msg):
        """Handle file upload request"""
        if not msg:
            return
        file_name = msg.payload.get("file_name", "")
        file_size = msg.payload.get("file_size", 0)
        destination = msg.payload.get("destination_path", "")

        # Check quota
        allowed, remaining = self.db_manager.check_quota(client_id, file_size)
        if allowed:
            transfer_id = f"{client_id}_{int(msg.timestamp)}"
            self._active_transfers[transfer_id] = {
                'file_name': file_name,
                'destination': destination,
                'received': 0,
                'total': file_size
            }

            accept = ProtocolHandler.create_upload_accept(
                self.device_id, self.device_name, transfer_id
            )
            self.server.send_message(client_id, accept)
        else:
            reject = ProtocolHandler.create_upload_reject(
                self.device_id, self.device_name,
                f"Quota exceeded. {remaining:.0f}MB remaining"
            )
            self.server.send_message(client_id, reject)

    def _handle_file_chunk(self, client_id, msg):
        """Handle incoming file chunk"""
        if not msg:
            return
        transfer_id = msg.payload.get("transfer_id", "")
        chunk_data = msg.payload.get("data", "")
        is_last = msg.payload.get("is_last", False)

        if transfer_id in self._active_transfers:
            transfer = self._active_transfers[transfer_id]

            # Write chunk to file (simplified - would need base64 decoding)
            dest_path = os.path.join(transfer['destination'], transfer['file_name'])
            self.file_manager.write_file_chunk(dest_path, chunk_data.encode())

            transfer['received'] += len(chunk_data)

            if is_last:
                # Update used storage
                old_used = self.db_manager.get_device(client_id)['used_mb'] or 0
                new_used = old_used + (transfer['total'] / (1024 * 1024))
                self.db_manager.update_used_storage(client_id, int(new_used))

                # Record transfer
                self.db_manager.add_transfer(
                    client_id, transfer['file_name'],
                    transfer['total'], 'upload', 'completed'
                )

                complete = ProtocolHandler.create_transfer_complete(
                    self.device_id, self.device_name, transfer_id
                )
                self.server.send_message(client_id, complete)
                del self._active_transfers[transfer_id]

    def _handle_download_request(self, client_id, msg):
        """Handle file download request"""
        if not msg:
            return
        file_path = msg.payload.get("file_path", "")

        file_info = self.file_manager.get_file_info(file_path)
        if file_info and not file_info['is_dir']:
            # Send file in chunks (simplified)
            accept = ProtocolHandler.create_download_accept(
                self.device_id, self.device_name, f"down_{int(msg.timestamp)}"
            )
            self.server.send_message(client_id, accept)
        else:
            reject = ProtocolHandler.create_download_reject(
                self.device_id, self.device_name, "File not found"
            )
            self.server.send_message(client_id, reject)

    def _handle_create_folder_request(self, client_id, msg):
        """Handle create folder request"""
        if not msg:
            return
        folder_path = msg.payload.get("folder_path", "")
        success, message = self.file_manager.create_folder(folder_path)
        response = ProtocolHandler.create_create_folder_response(
            self.device_id, self.device_name, success, message
        )
        self.server.send_message(client_id, response)

    def _handle_disconnect(self, client_id, msg):
        """Handle disconnect from remote device"""
        self.db_manager.clear_session_token(client_id)
        if client_id in self.clients:
            self.clients[client_id].disconnect()
            del self.clients[client_id]

    def _handle_ping(self, client_id, msg):
        """Handle ping - respond with pong"""
        pong = ProtocolHandler.create_pong(self.device_id, self.device_name)
        self.server.send_message(client_id, pong)

    # ===== Internet Relay =====

    def toggle_internet_mode(self):
        """Toggle between WiFi and internet mode"""
        if self.relay_client and self.relay_client.connected:
            self.relay_client.disconnect()
            self.show_snackbar("Switched to WiFi mode")
        else:
            self.show_snackbar("Configure relay server in Settings")

    def connect_relay(self):
        """Connect to relay server for internet mode"""
        screen = self._get_screen('settings')
        if not screen:
            return

        host = screen.ids.relay_host_input.text.strip()
        if not host:
            self.show_snackbar("Enter relay server address")
            return

        self.relay_client = RelayClient(
            self.device_id, self.device_name, host
        )

        if self.relay_client.connect():
            self.show_snackbar(f"Connected to relay: {host}")
        else:
            self.show_snackbar(f"Failed to connect to relay: {host}")

    # ===== UI Helpers =====

    def refresh_devices(self):
        """Refresh paired devices list on home screen"""
        screen = self._get_screen('home')
        if not screen:
            return

        devices = self.db_manager.get_all_devices()
        data = []
        for device in devices:
            used = device['used_mb'] or 0
            quota = device['quota_mb'] or 1024
            data.append({
                'device_id': device['device_id'],
                'device_name': device['device_name'],
                'quota_mb': quota,
                'used_mb': used,
                'usage_percent': (used / max(quota, 1)) * 100,
                'is_connected': bool(device['is_connected']),
                'ip_address': device['ip_address'] or ''
            })

        screen.ids.devices_list.data = data

    def get_paired_devices_count(self):
        """Get count of paired devices"""
        return len(self.db_manager.get_all_devices())

    def show_snackbar(self, message):
        """Show a snackbar notification"""
        from kivymd.uix.snackbar import Snackbar
        Snackbar(text=message, duration=3).open()

    def show_paired_devices(self):
        """Show paired devices management dialog"""
        devices = self.db_manager.get_all_devices()
        if not devices:
            self.show_snackbar("No paired devices")
            return

        device_list = "\n".join([
            f"{d['device_name']} - {d['used_mb']}MB/{d['quota_mb']}MB"
            for d in devices
        ])
        self.show_snackbar(f"Paired devices:\n{device_list}")

    def _connect_to_device(self, device_id, ip, port):
        """Connect to a paired device"""
        if device_id in self.clients and self.clients[device_id].is_connected():
            return

        client = StorageClient(self.device_id, self.device_name)
        if client.connect(ip, port):
            self.clients[device_id] = client
            self._current_client = client

            # Register handlers
            client.register_handler("FILE_LIST_RES", self._handle_file_list_response)
            client.register_handler("QUOTA_RES", self._handle_quota_response)
            client.register_handler("TRANSFER_COMPLETE", self._handle_transfer_complete)
            client.register_handler("DISCONNECT", self._handle_disconnect)

    def _get_client(self, device_id):
        """Get or create a client for a device"""
        if device_id not in self.clients or not self.clients[device_id].is_connected():
            device = self.db_manager.get_device(device_id)
            if device and device['ip_address']:
                self._connect_to_device(device_id, device['ip_address'], device['port'])
        return self.clients.get(device_id)

    def _handle_file_list_response(self, sender_id, msg):
        """Handle file list from remote device"""
        if not msg:
            return
        files = msg.payload.get("files", [])
        screen = self._get_screen('storage')
        if screen:
            screen.update_file_list(files)

    def _handle_quota_response(self, sender_id, msg):
        """Handle quota check response"""
        if not msg:
            return
        allowed = msg.payload.get("allowed", False)
        remaining = msg.payload.get("remaining_mb", 0)
        if not allowed:
            self.show_snackbar(f"Quota exceeded! {remaining}MB remaining")

    def _handle_transfer_complete(self, sender_id, msg):
        """Handle transfer completion"""
        if not msg:
            return
        transfer_id = msg.payload.get("transfer_id", "")
        self.show_snackbar("Transfer completed!")
        # Refresh file list
        screen = self._get_screen('storage')
        if screen:
            screen._refresh_files()

    def _switch_to_screen(self, screen_name):
        """Schedule a screen switch on the main thread"""
        Clock.schedule_once(lambda dt: setattr(self.root, 'current', screen_name))

    def _get_screen(self, name):
        """Get a screen by name"""
        if self.root:
            return self.root.get_screen(name)
        return None

    def on_stop(self):
        """Cleanup on app exit"""
        self.discovery.stop() if self.discovery else None
        self.server.stop() if self.server else None
        for client in self.clients.values():
            client.disconnect()
        self.db_manager.close()