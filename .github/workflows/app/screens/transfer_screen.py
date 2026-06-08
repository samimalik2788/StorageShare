"""
StorageShare - Transfer Screen
Shows file transfer progress and history
"""

from kivy.uix.screenmanager import Screen
from kivy.lang import Builder
from kivy.properties import StringProperty, BooleanProperty, NumericProperty
from kivy.uix.boxlayout import BoxLayout
import os

kv_path = os.path.join(os.path.dirname(__file__), '..', '..', 'assets', 'kv', 'transfer.kv')
Builder.load_file(kv_path)


class TransferHistoryItem(BoxLayout):
    """Widget for a transfer history entry"""
    file_name = StringProperty('')
    file_size = StringProperty('0 B')
    transfer_type = StringProperty('upload')
    status = StringProperty('completed')
    time = StringProperty('')


class TransferScreen(Screen):
    """Screen showing current and past file transfers"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = 'transfer'

    def update_progress(self, file_name, current_bytes, total_bytes, speed=0):
        """Update transfer progress display"""
        self.ids.transfer_file_name.text = f"Transferring: {file_name}"
        self.ids.transfer_status.text = f"{self._format_size(current_bytes)} of {self._format_size(total_bytes)}"

        percent = (current_bytes / max(total_bytes, 1)) * 100
        self.ids.transfer_progress.value = min(percent, 100)

        if speed > 0:
            self.ids.speed_label.text = f"{self._format_size(speed)}/s"

    def reset(self):
        """Reset transfer display"""
        self.ids.transfer_file_name.text = "No active transfers"
        self.ids.transfer_status.text = "0 of 0 KB"
        self.ids.transfer_progress.value = 0
        self.ids.speed_label.text = "0 KB/s"

    def _format_size(self, size_bytes):
        """Format file size"""
        if size_bytes == 0:
            return "0 B"
        units = ['B', 'KB', 'MB', 'GB']
        i = 0
        size = float(size_bytes)
        while size >= 1024 and i < len(units) - 1:
            size /= 1024
            i += 1
        return f"{size:.1f} {units[i]}"