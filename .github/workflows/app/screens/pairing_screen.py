"""
StorageShare - Pairing Screen
4-digit code entry and storage quota configuration
"""

from kivy.uix.screenmanager import Screen
from kivy.lang import Builder
from kivy.clock import Clock
from kivy.properties import StringProperty, NumericProperty
from kivy.uix.boxlayout import BoxLayout
import os

kv_path = os.path.join(os.path.dirname(__file__), '..', '..', 'assets', 'kv', 'pairing.kv')
Builder.load_file(kv_path)


class PairingScreen(Screen):
    """Screen for 4-digit pairing code entry and quota settings"""

    target_device_id = StringProperty('')
    target_device_name = StringProperty('')
    target_ip = StringProperty('')
    is_granting = False  # True if this device is granting access (entering code)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = 'pairing'
        self._timer_event = None
        self._remaining_time = 120
        self.is_granting = False

    def setup_requestor(self, device_id, device_name, ip_address):
        """Setup for device requesting access (shows code to enter on other device)"""
        self.target_device_id = device_id
        self.target_device_name = device_name
        self.target_ip = ip_address
        self.is_granting = False

        # Generate and show the 4-digit code
        app = self._get_app()
        if app:
            code = app.start_pairing_request(device_id, device_name, ip_address)
            if code:
                # Display code digits in the input fields as read-only
                self.ids.digit1.text = code[0] if len(code) > 0 else ''
                self.ids.digit2.text = code[1] if len(code) > 1 else ''
                self.ids.digit3.text = code[2] if len(code) > 2 else ''
                self.ids.digit4.text = code[3] if len(code) > 3 else ''

                # Make them read-only
                for field in [self.ids.digit1, self.ids.digit2, self.ids.digit3, self.ids.digit4]:
                    field.disabled = True

                self.ids.title_label.text = f"Pairing with {device_name}"
                self.ids.pairing_info.text = "Share this code with the other device"
                self.ids.action_btn.text = "Waiting for grant..."
                self.ids.action_btn.disabled = True
                self.ids.quota_card.opacity = 0

        self._start_timer()

    def setup_grantor(self, device_id, device_name, ip_address):
        """Setup for device granting access (enters code from other device)"""
        self.target_device_id = device_id
        self.target_device_name = device_name
        self.target_ip = ip_address
        self.is_granting = True

        # Clear code fields for input
        for field in [self.ids.digit1, self.ids.digit2, self.ids.digit3, self.ids.digit4]:
            field.disabled = False
            field.text = ''

        self.ids.title_label.text = f"Grant access to {device_name}"
        self.ids.pairing_info.text = "Enter the 4-digit code shown on the other device"
        self.ids.action_btn.text = "Enter Code & Grant Access"
        self.ids.action_btn.disabled = False
        self.ids.quota_card.opacity = 1

        # Focus on first digit
        Clock.schedule_once(lambda dt: self.ids.digit1.focus, 0.5)

        self._start_timer()

    def _start_timer(self):
        """Start the pairing code timer"""
        self._remaining_time = 120
        if self._timer_event:
            self._timer_event.cancel()
        self._timer_event = Clock.schedule_interval(self._update_timer, 1.0)

    def _update_timer(self, dt):
        """Update the timer display"""
        self._remaining_time -= 1
        self.ids.timer_label.text = f"Time remaining: {self._remaining_time}s"

        if self._remaining_time <= 0:
            if self._timer_event:
                self._timer_event.cancel()
            self.ids.timer_label.text = "Code expired"
            self.ids.action_btn.disabled = True
            app = self._get_app()
            if app:
                app.show_snackbar("Pairing code expired. Please try again.")

    def set_quota(self, quota_mb):
        """Set the storage quota preset"""
        self.ids.quota_input.text = str(quota_mb)

    def get_entered_code(self):
        """Get the 4-digit code from input fields"""
        return (self.ids.digit1.text + self.ids.digit2.text +
                self.ids.digit3.text + self.ids.digit4.text)

    def get_quota_mb(self):
        """Get the quota value from input"""
        try:
            return int(self.ids.quota_input.text)
        except:
            return 1024

    def _get_app(self):
        from kivy.app import App
        return App.get_running_app()