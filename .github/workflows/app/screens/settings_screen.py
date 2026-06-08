"""
StorageShare - Settings Screen
App configuration, paired devices management, relay server settings
"""

from kivy.uix.screenmanager import Screen
from kivy.lang import Builder
import os

kv_path = os.path.join(os.path.dirname(__file__), '..', '..', 'assets', 'kv', 'settings.kv')
Builder.load_file(kv_path)


class SettingsScreen(Screen):
    """Settings and configuration screen"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = 'settings'

    def on_enter(self):
        """Update display when entering settings"""
        app = self._get_app()
        if app:
            self.ids.device_name_label.text = f"Name: {app.device_name}"
            self.ids.device_name_label.text += f"\nID: {app.device_id[:16]}..."

            paired = app.get_paired_devices_count()
            self.ids.paired_count.text = f"{paired} devices paired"

    def _get_app(self):
        from kivy.app import App
        return App.get_running_app()