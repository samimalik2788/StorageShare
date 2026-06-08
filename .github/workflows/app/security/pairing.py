"""
StorageShare - Security & Pairing Module
4-digit pairing code generation and verification
"""

import random
import string
import hashlib
import secrets
import time
from app.utils.constants import PAIRING_CODE_LENGTH, PAIRING_CODE_TIMEOUT, SESSION_TOKEN_LENGTH


class PairingManager:
    """Manages 4-digit pairing codes and session tokens"""

    def __init__(self):
        self._pending_codes = {}  # device_id -> {code, timestamp, attempts}
        self._active_sessions = {}  # device_id -> session_token

    def generate_pairing_code(self, device_id):
        """Generate a 4-digit pairing code for a device"""
        code = ''.join(random.choices(string.digits, k=PAIRING_CODE_LENGTH))
        self._pending_codes[device_id] = {
            'code': code,
            'timestamp': time.time(),
            'attempts': 0
        }
        return code

    def verify_pairing_code(self, device_id, entered_code):
        """Verify a 4-digit pairing code. Returns (success, message)"""
        if device_id not in self._pending_codes:
            return False, "No pending pairing request"

        pending = self._pending_codes[device_id]

        # Check timeout
        if time.time() - pending['timestamp'] > PAIRING_CODE_TIMEOUT:
            del self._pending_codes[device_id]
            return False, "Pairing code has expired"

        # Check attempts
        if pending['attempts'] >= 3:
            del self._pending_codes[device_id]
            return False, "Too many failed attempts. Please request a new code."

        # Verify code
        pending['attempts'] += 1
        if pending['code'] == entered_code:
            # Generate session token
            session_token = self.generate_session_token()
            self._active_sessions[device_id] = session_token
            del self._pending_codes[device_id]
            return True, session_token

        return False, "Invalid pairing code"

    def generate_session_token(self):
        """Generate a secure random session token"""
        return secrets.token_hex(SESSION_TOKEN_LENGTH)

    def validate_session(self, device_id, session_token):
        """Validate if a session token is still active"""
        if device_id in self._active_sessions:
            return self._active_sessions[device_id] == session_token
        return False

    def revoke_session(self, device_id):
        """Revoke a session on disconnect"""
        if device_id in self._active_sessions:
            del self._active_sessions[device_id]

    def get_pending_code(self, device_id):
        """Get the pending pairing code for display (without revealing full code)"""
        if device_id in self._pending_codes:
            code = self._pending_codes[device_id]['code']
            remaining = PAIRING_CODE_TIMEOUT - (time.time() - self._pending_codes[device_id]['timestamp'])
            return {
                'code': code,
                'remaining_seconds': max(0, int(remaining))
            }
        return None

    def is_pairing_active(self, device_id):
        """Check if there's an active pairing for this device"""
        if device_id in self._pending_codes:
            if time.time() - self._pending_codes[device_id]['timestamp'] > PAIRING_CODE_TIMEOUT:
                del self._pending_codes[device_id]
                return False
            return True
        return False

    def hash_code(self, code):
        """Hash a pairing code for secure transmission"""
        return hashlib.sha256(code.encode()).hexdigest()


class DeviceIdentity:
    """Generate and manage device identity"""

    @staticmethod
    def generate_device_id():
        """Generate a unique device identifier"""
        return secrets.token_hex(16)

    @staticmethod
    def get_device_name():
        """Get a friendly device name"""
        import platform
        return platform.node() or "Android Device"