"""
StorageShare - Discovery Screen
Shows nearby devices discovered via UDP broadcast
"""

from kivy.uix.screenmanager import Screen
from kivy.lang import Builder
from kivy.properties import StringProperty
from kivy.uix.boxlayout import BoxLayout
import os

kv_path = os.path.join(os.path.dirname(__file__), '..', '..', 'assets', 'kv', 'discovery.kv')
Builder.load_file(kv_path)


class DiscoveredDeviceCard(BoxLayout):
    """Widget for a discovered device in the list"""
    device_id = StringProperty('')
    device_name = StringProperty('Unknown Device')
    ip_address = StringProperty('')


class DiscoveryScreen(Screen):
    """Screen to discover nearby devices"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = 'discover'

    def on_enter(self):
        """Start discovery when entering screen"""
        app = self._get_app()
        if app:
            app.start_discovery_view()

    def on_leave(self):
        """Stop discovery when leaving screen"""
        app = self._get_app()
        if app:
            app.stop_discovery_view()

    def _get_app(self):
        from kivy.app import App
        return App.get_running_app()