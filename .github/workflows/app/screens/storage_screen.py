"""
StorageShare - Storage Screen
Browse remote device storage, create folders, upload/download files
"""

from kivy.uix.screenmanager import Screen
from kivy.lang import Builder
from kivy.properties import StringProperty, BooleanProperty, NumericProperty
from kivy.uix.boxlayout import BoxLayout
import os

kv_path = os.path.join(os.path.dirname(__file__), '..', '..', 'assets', 'kv', 'storage.kv')
Builder.load_file(kv_path)


class FileItem(BoxLayout):
    """Widget for a file/folder in the remote storage browser"""
    file_name = StringProperty('')
    file_path = StringProperty('')
    file_size = StringProperty('0 B')
    is_dir = BooleanProperty(False)
    size_bytes = NumericProperty(0)


class StorageScreen(Screen):
    """Screen for browsing and managing remote device storage"""

    current_device_id = StringProperty('')
    current_device_name = StringProperty('')
    current_path = StringProperty('/')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = 'storage'
        self._path_stack = ['/']

    def open_device(self, device_id, device_name):
        """Open storage browser for a specific device"""
        self.current_device_id = device_id
        self.current_device_name = device_name
        self.current_path = '/'
        self._path_stack = ['/']
        self.ids.toolbar.title = f"{device_name}"
        self._refresh_files()

    def navigate_to(self, path):
        """Navigate to a specific path"""
        self.current_path = path
        self._path_stack.append(path)
        self._refresh_files()

    def go_up(self):
        """Go up one directory level"""
        if len(self._path_stack) > 1:
            self._path_stack.pop()
            self.current_path = self._path_stack[-1]
            self._refresh_files()

    def create_folder(self, folder_name):
        """Create a new folder on the remote device"""
        app = self._get_app()
        if app:
            new_path = os.path.join(self.current_path, folder_name).replace('\\', '/')
            app.create_remote_folder(self.current_device_id, new_path)
            self._refresh_files()

    def _refresh_files(self):
        """Request file list from remote device"""
        self.ids.path_label.text = self.current_path or '/'
        app = self._get_app()
        if app:
            app.request_file_list(self.current_device_id, self.current_path)

    def update_file_list(self, files):
        """Update the file list display"""
        data = []
        for f in files:
            data.append({
                'file_name': f['name'],
                'file_path': f['path'],
                'file_size': f['size_formatted'],
                'is_dir': f['is_dir'],
                'size_bytes': f['size']
            })
        self.ids.file_list.data = data

    def update_quota_display(self, used_mb, quota_mb):
        """Update quota progress bar"""
        percent = (used_mb / max(quota_mb, 1)) * 100
        self.ids.quota_bar.value = min(percent, 100)
        self.ids.quota_label.text = f"{used_mb}MB / {quota_mb}MB"

    def _get_app(self):
        from kivy.app import App
        return App.get_running_app()