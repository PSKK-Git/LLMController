import hashlib
import secrets

KEY_PREFIX = "sk-"


def hash_api_key(key: str) -> str:
    """Deterministic SHA-256 hex digest used for DB lookup."""
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def generate_api_key() -> tuple[str, str]:
    """Return (plaintext_key, key_hash). Plaintext is shown to the caller once."""
    plaintext = KEY_PREFIX + secrets.token_urlsafe(32)
    return plaintext, hash_api_key(plaintext)
