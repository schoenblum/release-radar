"""Fernet encryption for API keys stored in the database (R5.2.4).

``FERNET_KEY`` encrypts all new values. Older keys listed in ``FERNET_KEYS``
stay readable, so a key can be rotated without downtime. HANDOVER section 7 has
the procedure.
"""

from cryptography.fernet import Fernet, MultiFernet

from app.config import get_settings


def _build_fernet() -> MultiFernet:
    settings = get_settings()
    keys = [settings.FERNET_KEY]
    if settings.FERNET_KEYS:
        keys += [key.strip() for key in settings.FERNET_KEYS.split(",") if key.strip()]
    return MultiFernet([Fernet(key.encode("ascii")) for key in keys])


_fernet = _build_fernet()


def encrypt(plaintext: str) -> bytes:
    return _fernet.encrypt(plaintext.encode("utf-8"))


def decrypt(token: bytes) -> str:
    return _fernet.decrypt(token).decode("utf-8")


def rotate_token(token: bytes) -> bytes:
    """Re-encrypt under the primary key so older keys can be retired."""
    return _fernet.rotate(token)
