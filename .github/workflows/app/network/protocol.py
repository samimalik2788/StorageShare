"""
StorageShare - Communication Protocol
JSON-based messaging protocol for device communication
"""

import json
import time
from app.utils.constants import MSG_TYPE


class Message:
    """Represents a protocol message between devices"""

    def __init__(self, msg_type, sender_id, sender_name="", payload=None):
        self.type = msg_type
        self.sender_id = sender_id
        self.sender_name = sender_name
        self.timestamp = time.time()
        self.payload = payload or {}
        self.message_id = f"{sender_id}_{int(self.timestamp * 1000)}"

    def to_json(self):
        """Serialize message to JSON string"""
        return json.dumps({
            "type": self.type,
            "sender_id": self.sender_id,
            "sender_name": self.sender_name,
            "timestamp": self.timestamp,
            "message_id": self.message_id,
            "payload": self.payload
        })

    @staticmethod
    def from_json(json_str):
        """Deserialize JSON string to Message object"""
        try:
            data = json.loads(json_str)
            msg = Message(
                msg_type=data["type"],
                sender_id=data["sender_id"],
                sender_name=data.get("sender_name", ""),
                payload=data.get("payload", {})
            )
            msg.timestamp = data.get("timestamp", time.time())
            msg.message_id = data.get("message_id", "")
            return msg
        except (json.JSONDecodeError, KeyError) as e:
            return None

    def __repr__(self):
        return f"Message(type={self.type}, sender={self.sender_id}, payload={self.payload})"


class ProtocolHandler:
    """Handles creation and parsing of protocol messages"""

    @staticmethod
    def create_discovery_request(device_id, device_name):
        """Create a discovery broadcast request"""
        return Message(
            msg_type=MSG_TYPE["DISCOVERY_REQUEST"],
            sender_id=device_id,
            sender_name=device_name
        )

    @staticmethod
    def create_discovery_response(device_id, device_name, quota_mb=0, used_mb=0):
        """Create a discovery response"""
        return Message(
            msg_type=MSG_TYPE["DISCOVERY_RESPONSE"],
            sender_id=device_id,
            sender_name=device_name,
            payload={"quota_mb": quota_mb, "used_mb": used_mb}
        )

    @staticmethod
    def create_pairing_request(device_id, device_name):
        """Create a pairing request message"""
        return Message(
            msg_type=MSG_TYPE["PAIRING_REQUEST"],
            sender_id=device_id,
            sender_name=device_name
        )

    @staticmethod
    def create_pairing_code_message(device_id, device_name, code):
        """Send the 4-digit pairing code (Device A -> Device B)"""
        return Message(
            msg_type=MSG_TYPE["PAIRING_CODE"],
            sender_id=device_id,
            sender_name=device_name,
            payload={"code": code}
        )

    @staticmethod
    def create_pairing_verified(device_id, device_name, session_token, quota_mb):
        """Pairing verification successful"""
        return Message(
            msg_type=MSG_TYPE["PAIRING_VERIFIED"],
            sender_id=device_id,
            sender_name=device_name,
            payload={"session_token": session_token, "quota_mb": quota_mb}
        )

    @staticmethod
    def create_pairing_failed(device_id, device_name, reason):
        """Pairing failed message"""
        return Message(
            msg_type=MSG_TYPE["PAIRING_FAILED"],
            sender_id=device_id,
            sender_name=device_name,
            payload={"reason": reason}
        )

    @staticmethod
    def create_file_list_request(device_id, device_name, path="/", session_token=""):
        """Request list of files from remote device"""
        return Message(
            msg_type=MSG_TYPE["FILE_LIST_REQUEST"],
            sender_id=device_id,
            sender_name=device_name,
            payload={"path": path, "session_token": session_token}
        )

    @staticmethod
    def create_file_list_response(device_id, device_name, files, session_token=""):
        """Response with list of files"""
        return Message(
            msg_type=MSG_TYPE["FILE_LIST_RESPONSE"],
            sender_id=device_id,
            sender_name=device_name,
            payload={"files": files, "session_token": session_token}
        )

    @staticmethod
    def create_upload_request(device_id, device_name, file_name, file_size, destination_path, session_token=""):
        """Request to upload a file"""
        return Message(
            msg_type=MSG_TYPE["FILE_UPLOAD_REQUEST"],
            sender_id=device_id,
            sender_name=device_name,
            payload={
                "file_name": file_name,
                "file_size": file_size,
                "destination_path": destination_path,
                "session_token": session_token
            }
        )

    @staticmethod
    def create_upload_accept(device_id, device_name, transfer_id, session_token=""):
        """Accept file upload"""
        return Message(
            msg_type=MSG_TYPE["FILE_UPLOAD_ACCEPT"],
            sender_id=device_id,
            sender_name=device_name,
            payload={"transfer_id": transfer_id, "session_token": session_token}
        )

    @staticmethod
    def create_upload_reject(device_id, device_name, reason, session_token=""):
        """Reject file upload"""
        return Message(
            msg_type=MSG_TYPE["FILE_UPLOAD_REJECT"],
            sender_id=device_id,
            sender_name=device_name,
            payload={"reason": reason, "session_token": session_token}
        )

    @staticmethod
    def create_file_chunk(device_id, device_name, transfer_id, chunk_index, data, is_last=False, session_token=""):
        """Send a chunk of file data"""
        return Message(
            msg_type=MSG_TYPE["FILE_CHUNK"],
            sender_id=device_id,
            sender_name=device_name,
            payload={
                "transfer_id": transfer_id,
                "chunk_index": chunk_index,
                "is_last": is_last,
                "data": data,  # base64 encoded data
                "session_token": session_token
            }
        )

    @staticmethod
    def create_download_request(device_id, device_name, file_path, session_token=""):
        """Request to download a file from remote"""
        return Message(
            msg_type=MSG_TYPE["FILE_DOWNLOAD_REQUEST"],
            sender_id=device_id,
            sender_name=device_name,
            payload={"file_path": file_path, "session_token": session_token}
        )

    @staticmethod
    def create_create_folder_request(device_id, device_name, folder_path, session_token=""):
        """Request to create a folder on remote device"""
        return Message(
            msg_type=MSG_TYPE["CREATE_FOLDER_REQUEST"],
            sender_id=device_id,
            sender_name=device_name,
            payload={"folder_path": folder_path, "session_token": session_token}
        )

    @staticmethod
    def create_create_folder_response(device_id, device_name, success, message="", session_token=""):
        """Response for create folder request"""
        return Message(
            msg_type=MSG_TYPE["CREATE_FOLDER_RESPONSE"],
            sender_id=device_id,
            sender_name=device_name,
            payload={"success": success, "message": message, "session_token": session_token}
        )

    @staticmethod
    def create_quota_check(device_id, device_name, file_size, session_token=""):
        """Check if quota allows this file"""
        return Message(
            msg_type=MSG_TYPE["QUOTA_CHECK"],
            sender_id=device_id,
            sender_name=device_name,
            payload={"file_size": file_size, "session_token": session_token}
        )

    @staticmethod
    def create_quota_response(device_id, device_name, allowed, remaining_mb, session_token=""):
        """Quota check response"""
        return Message(
            msg_type=MSG_TYPE["QUOTA_RESPONSE"],
            sender_id=device_id,
            sender_name=device_name,
            payload={
                "allowed": allowed,
                "remaining_mb": remaining_mb,
                "session_token": session_token
            }
        )

    @staticmethod
    def create_transfer_complete(device_id, device_name, transfer_id, session_token=""):
        """File transfer completed successfully"""
        return Message(
            msg_type=MSG_TYPE["TRANSFER_COMPLETE"],
            sender_id=device_id,
            sender_name=device_name,
            payload={"transfer_id": transfer_id, "session_token": session_token}
        )

    @staticmethod
    def create_transfer_error(device_id, device_name, transfer_id, error_code, error_msg, session_token=""):
        """File transfer error"""
        return Message(
            msg_type=MSG_TYPE["TRANSFER_ERROR"],
            sender_id=device_id,
            sender_name=device_name,
            payload={
                "transfer_id": transfer_id,
                "error_code": error_code,
                "error_msg": error_msg,
                "session_token": session_token
            }
        )

    @staticmethod
    def create_disconnect(device_id, device_name, session_token=""):
        """Disconnect message"""
        return Message(
            msg_type=MSG_TYPE["DISCONNECT"],
            sender_id=device_id,
            sender_name=device_name,
            payload={"session_token": session_token}
        )

    @staticmethod
    def create_ping(device_id, device_name):
        """Ping keep-alive"""
        return Message(
            msg_type=MSG_TYPE["PING"],
            sender_id=device_id,
            sender_name=device_name
        )

    @staticmethod
    def create_pong(device_id, device_name):
        """Pong response"""
        return Message(
            msg_type=MSG_TYPE["PONG"],
            sender_id=device_id,
            sender_name=device_name
        )