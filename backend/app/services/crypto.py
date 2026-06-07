import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from app.config import get_settings


class CredentialCipher:
    def __init__(self, secret_key: str | None = None) -> None:
        settings = get_settings()
        raw = secret_key or settings.dashboard_secret_key
        if not raw:
            raise ValueError("DASHBOARD_SECRET_KEY is required for credential encryption")
        digest = hashlib.sha256(raw.encode("utf-8")).digest()
        self._fernet = Fernet(base64.urlsafe_b64encode(digest))

    def encrypt(self, plaintext: str) -> str:
        return self._fernet.encrypt(plaintext.encode("utf-8")).decode("utf-8")

    def decrypt(self, ciphertext: str) -> str:
        try:
            return self._fernet.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
        except InvalidToken as exc:
            raise ValueError("Invalid encrypted credential blob") from exc


def encrypt_credentials(username: str | None, password: str | None) -> str | None:
    if not username and not password:
        return None
    payload = f"{username or ''}:{password or ''}"
    return CredentialCipher().encrypt(payload)


def decrypt_credentials(blob: str | None) -> tuple[str | None, str | None]:
    if not blob:
        return None, None
    plain = CredentialCipher().decrypt(blob)
    username, _, password = plain.partition(":")
    return username or None, password or None