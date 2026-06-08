"""
StorageShare - Home Screen
Displays paired devices and quick actions
"""

from kivy.uix.screenmanager import Screen
from kivy.lang import Builder
from kivy.properties import StringProperty, NumericProperty, BooleanProperty
from kivy.uix.boxlayout import BoxLayout
import os

kv_path = os.path.join(os.path.dirname(__file__), '..', '..', 'assets', 'kv', 'home.kv')
Builder.load_file(kv_path)


class DeviceCard(BoxLayout):
    """Widget class for device cards in RecycleView"""
    device_id = StringProperty('')
    device_name = StringProperty('Unknown Device')
    ip_address = StringProperty('')
    quota_mb = NumericProperty(1024)
    used_mb = NumericProperty(0)
    usage_percent = NumericProperty(0)
    is_connected = BooleanProperty(False)


class HomeScreen(Screen):
    """Main home screen showing paired devices"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = 'home'

    def on_enter(self):
        """Refresh device list when screen is shown"""
        app = self._get_app()
        if app:
            app.refresh_devices()

    def _get_app(self):
        """Get the app instance"""
        from kivy.app import App
        return App.get_running_app()