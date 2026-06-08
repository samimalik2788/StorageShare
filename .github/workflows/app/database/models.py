"""
StorageShare - Database Models
SQLite database for paired devices, quotas, and transfer history
"""

import sqlite3
import json
import os
from datetime import datetime
from app.utils.constants import DB_NAME


class DatabaseManager:
    """Manages SQLite database for StorageShare"""

    def __init__(self, db_path=None):
        if db_path is None:
            # Store database in app's data directory
            self.db_path = DB_NAME
        else:
            self.db_path = db_path
        self.conn = None
        self._connect()
        self._create_tables()

    def _connect(self):
        """Connect to SQLite database"""
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row

    def _create_tables(self):
        """Create necessary tables if they don't exist"""
        cursor = self.conn.cursor()

        # Paired devices table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS paired_devices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_name TEXT NOT NULL,
                device_id TEXT UNIQUE NOT NULL,
                ip_address TEXT,
                port INTEGER DEFAULT 9876,
                quota_mb INTEGER DEFAULT 1024,
                used_mb INTEGER DEFAULT 0,
                session_token TEXT,
                pairing_code TEXT,
                is_connected INTEGER DEFAULT 0,
                last_seen TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Transfer history table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transfer_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT NOT NULL,
                file_name TEXT NOT NULL,
                file_size INTEGER DEFAULT 0,
                transfer_type TEXT CHECK(transfer_type IN ('upload', 'download')),
                status TEXT CHECK(status IN ('completed', 'failed', 'cancelled')),
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                FOREIGN KEY (device_id) REFERENCES paired_devices(device_id)
            )
        """)

        # Quota alerts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS quota_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT NOT NULL,
                alert_type TEXT CHECK(alert_type IN ('warning', 'critical', 'exceeded')),
                used_mb INTEGER DEFAULT 0,
                quota_mb INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (device_id) REFERENCES paired_devices(device_id)
            )
        """)

        self.conn.commit()

    # ===== Device Management =====

    def add_device(self, device_name, device_id, ip_address=None, port=9876, quota_mb=1024):
        """Add a paired device to the database"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO paired_devices
            (device_name, device_id, ip_address, port, quota_mb, last_seen)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (device_name, device_id, ip_address, port, quota_mb, datetime.now()))
        self.conn.commit()
        return cursor.lastrowid

    def remove_device(self, device_id):
        """Remove a paired device"""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM paired_devices WHERE device_id = ?", (device_id,))
        self.conn.commit()
        return cursor.rowcount > 0

    def get_device(self, device_id):
        """Get device info by ID"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM paired_devices WHERE device_id = ?", (device_id,))
        return cursor.fetchone()

    def get_all_devices(self):
        """Get all paired devices"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM paired_devices ORDER BY last_seen DESC")
        return cursor.fetchall()

    def update_device_status(self, device_id, is_connected, ip_address=None):
        """Update device connection status"""
        cursor = self.conn.cursor()
        now = datetime.now()
        if ip_address:
            cursor.execute("""
                UPDATE paired_devices
                SET is_connected = ?, ip_address = ?, last_seen = ?
                WHERE device_id = ?
            """, (1 if is_connected else 0, ip_address, now, device_id))
        else:
            cursor.execute("""
                UPDATE paired_devices
                SET is_connected = ?, last_seen = ?
                WHERE device_id = ?
            """, (1 if is_connected else 0, now, device_id))
        self.conn.commit()

    def update_device_quota(self, device_id, quota_mb):
        """Update storage quota for a device"""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE paired_devices SET quota_mb = ? WHERE device_id = ?
        """, (quota_mb, device_id))
        self.conn.commit()

    def update_used_storage(self, device_id, used_mb):
        """Update used storage amount"""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE paired_devices SET used_mb = ? WHERE device_id = ?
        """, (used_mb, device_id))
        self.conn.commit()

    def set_session_token(self, device_id, token):
        """Set session token for an active connection"""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE paired_devices SET session_token = ? WHERE device_id = ?
        """, (token, device_id))
        self.conn.commit()

    def clear_session_token(self, device_id):
        """Clear session token on disconnect"""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE paired_devices SET session_token = NULL, is_connected = 0
            WHERE device_id = ?
        """, (device_id,))
        self.conn.commit()

    def get_connected_devices(self):
        """Get currently connected devices"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM paired_devices WHERE is_connected = 1")
        return cursor.fetchall()

    # ===== Transfer History =====

    def add_transfer(self, device_id, file_name, file_size, transfer_type, status='completed'):
        """Record a file transfer"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO transfer_history
            (device_id, file_name, file_size, transfer_type, status, completed_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (device_id, file_name, file_size, transfer_type, status, datetime.now()))
        self.conn.commit()
        return cursor.lastrowid

    def get_transfer_history(self, device_id=None, limit=50):
        """Get transfer history, optionally filtered by device"""
        cursor = self.conn.cursor()
        if device_id:
            cursor.execute("""
                SELECT * FROM transfer_history
                WHERE device_id = ?
                ORDER BY started_at DESC LIMIT ?
            """, (device_id, limit))
        else:
            cursor.execute("""
                SELECT * FROM transfer_history
                ORDER BY started_at DESC LIMIT ?
            """, (limit,))
        return cursor.fetchall()

    # ===== Quota Management =====

    def check_quota(self, device_id, file_size_bytes):
        """Check if adding a file would exceed quota. Returns (allowed, remaining_mb)"""
        device = self.get_device(device_id)
        if not device:
            return False, 0

        used_mb = device['used_mb'] or 0
        quota_mb = device['quota_mb'] or 1024
        file_size_mb = file_size_bytes / (1024 * 1024)

        remaining_mb = quota_mb - used_mb
        if file_size_mb <= remaining_mb:
            return True, remaining_mb
        return False, remaining_mb

    def get_quota_usage(self, device_id):
        """Get quota usage as percentage"""
        device = self.get_device(device_id)
        if not device:
            return 0
        quota = device['quota_mb'] or 1
        used = device['used_mb'] or 0
        return (used / quota) * 100

    def add_quota_alert(self, device_id, alert_type, used_mb, quota_mb):
        """Create a quota alert"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO quota_alerts (device_id, alert_type, used_mb, quota_mb)
            VALUES (?, ?, ?, ?)
        """, (device_id, alert_type, used_mb, quota_mb))
        self.conn.commit()

    # ===== Utilities =====

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()

    def __del__(self):
        self.close()