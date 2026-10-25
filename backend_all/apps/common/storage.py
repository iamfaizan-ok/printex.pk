import os
import uuid
from pathlib import Path
from django.conf import settings


class PrivateDocumentStorage:
    """
    Handles secure storage of uploaded customer PDF documents outside the public web root.
    Files are stored with UUID-based keys to eliminate path traversal vulnerabilities.
    """

    def __init__(self):
        self.base_dir = Path(getattr(settings, 'PRIVATE_STORAGE_ROOT', settings.BASE_DIR / 'private_storage'))
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save_file(self, file_bytes: bytes, file_extension: str = '.pdf') -> str:
        """
        Saves raw bytes into private storage using a random unguessable UUID.
        Returns storage key (relative file path).
        """
        key = f"docs/{uuid.uuid4().hex}{file_extension}"
        full_path = self.base_dir / key
        full_path.parent.mkdir(parents=True, exist_ok=True)

        with open(full_path, 'wb') as f:
            f.write(file_bytes)

        return key

    def get_full_path(self, storage_key: str) -> Path:
        """
        Resolves storage key to absolute path and prevents path traversal.
        """
        clean_key = os.path.normpath(storage_key).lstrip('\\/')
        target_path = (self.base_dir / clean_key).resolve()

        if not str(target_path).startswith(str(self.base_dir.resolve())):
            raise ValueError("Path traversal attempt detected.")

        return target_path

    def file_exists(self, storage_key: str) -> bool:
        path = self.get_full_path(storage_key)
        return path.exists() and path.is_file()

    def read_bytes(self, storage_key: str) -> bytes:
        path = self.get_full_path(storage_key)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {storage_key}")
        with open(path, 'rb') as f:
            return f.read()

    def delete_file(self, storage_key: str) -> bool:
        path = self.get_full_path(storage_key)
        if path.exists():
            path.unlink()
            return True
        return False


private_storage = PrivateDocumentStorage()
