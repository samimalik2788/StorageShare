"""
StorageShare - File Management Module
Handles local file system operations for shared storage
"""

import os
import time
import shutil
from pathlib import Path


class FileManager:
    """Manages local file operations for the shared storage"""

    def __init__(self, base_path=None):
        if base_path is None:
            # Default: Use a "StorageShare" folder on internal storage
            self.base_path = os.path.join(
                os.path.expanduser("~"),
                "StorageShare"
            )
        else:
            self.base_path = base_path
        self._ensure_base_path()

    def _ensure_base_path(self):
        """Ensure the base storage directory exists"""
        os.makedirs(self.base_path, exist_ok=True)

    def get_base_path(self):
        """Get the base storage path"""
        return self.base_path

    def list_files(self, relative_path="", session_token=None):
        """List files and directories in the given path"""
        full_path = os.path.join(self.base_path, relative_path)
        full_path = os.path.normpath(full_path)

        # Security: Prevent path traversal
        if not full_path.startswith(os.path.normpath(self.base_path)):
            return []

        try:
            items = []
            for item in os.listdir(full_path):
                item_path = os.path.join(full_path, item)
                is_dir = os.path.isdir(item_path)
                size = 0
                if not is_dir:
                    try:
                        size = os.path.getsize(item_path)
                    except:
                        size = 0

                items.append({
                    "name": item,
                    "path": os.path.join(relative_path, item).replace("\\", "/"),
                    "is_dir": is_dir,
                    "size": size,
                    "size_formatted": self._format_size(size),
                    "modified": os.path.getmtime(item_path)
                })

            items.sort(key=lambda x: (not x['is_dir'], x['name'].lower()))
            return items
        except FileNotFoundError:
            return []
        except PermissionError:
            return []

    def create_folder(self, relative_path, session_token=None):
        """Create a new folder"""
        full_path = os.path.join(self.base_path, relative_path)
        full_path = os.path.normpath(full_path)

        # Security: Prevent path traversal
        if not full_path.startswith(os.path.normpath(self.base_path)):
            return False, "Access denied"

        try:
            os.makedirs(full_path, exist_ok=True)
            return True, "Folder created successfully"
        except PermissionError:
            return False, "Permission denied"
        except Exception as e:
            return False, str(e)

    def get_file_info(self, relative_path):
        """Get information about a file"""
        full_path = os.path.join(self.base_path, relative_path)
        full_path = os.path.normpath(full_path)

        if not full_path.startswith(os.path.normpath(self.base_path)):
            return None

        try:
            if os.path.exists(full_path):
                stat = os.stat(full_path)
                return {
                    "name": os.path.basename(full_path),
                    "path": relative_path,
                    "is_dir": os.path.isdir(full_path),
                    "size": stat.st_size,
                    "size_formatted": self._format_size(stat.st_size),
                    "modified": stat.st_mtime,
                    "created": stat.st_ctime
                }
        except:
            pass
        return None

    def get_used_space(self):
        """Calculate total used space in the storage directory"""
        total = 0
        try:
            for dirpath, dirnames, filenames in os.walk(self.base_path):
                for f in filenames:
                    try:
                        fp = os.path.join(dirpath, f)
                        total += os.path.getsize(fp)
                    except:
                        pass
        except:
            pass
        return total

    def write_file_chunk(self, relative_path, data, mode='ab'):
        """Write a chunk of data to a file"""
        full_path = os.path.join(self.base_path, relative_path)
        full_path = os.path.normpath(full_path)

        if not full_path.startswith(os.path.normpath(self.base_path)):
            return False

        try:
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, mode) as f:
                f.write(data)
            return True
        except Exception as e:
            print(f"[FileManager] Write error: {e}")
            return False

    def read_file_chunk(self, relative_path, offset=0, chunk_size=65536):
        """Read a chunk of data from a file"""
        full_path = os.path.join(self.base_path, relative_path)
        full_path = os.path.normpath(full_path)

        if not full_path.startswith(os.path.normpath(self.base_path)):
            return None

        try:
            with open(full_path, 'rb') as f:
                f.seek(offset)
                return f.read(chunk_size)
        except Exception as e:
            print(f"[FileManager] Read error: {e}")
            return None

    def delete_file(self, relative_path):
        """Delete a file or directory"""
        full_path = os.path.join(self.base_path, relative_path)
        full_path = os.path.normpath(full_path)

        if not full_path.startswith(os.path.normpath(self.base_path)):
            return False, "Access denied"

        try:
            if os.path.isdir(full_path):
                shutil.rmtree(full_path)
            else:
                os.remove(full_path)
            return True, "Deleted successfully"
        except FileNotFoundError:
            return False, "File not found"
        except Exception as e:
            return False, str(e)

    def _format_size(self, size_bytes):
        """Format file size in human-readable format"""
        if size_bytes == 0:
            return "0 B"
        units = ['B', 'KB', 'MB', 'GB', 'TB']
        i = 0
        size = float(size_bytes)
        while size >= 1024 and i < len(units) - 1:
            size /= 1024
            i += 1
        return f"{size:.1f} {units[i]}"