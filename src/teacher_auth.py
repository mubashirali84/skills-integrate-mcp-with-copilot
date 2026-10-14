import hashlib
import secrets

PASSWORD_HASH_ITERATIONS = 310_000


def hash_password(password: str, salt: bytes) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PASSWORD_HASH_ITERATIONS,
    ).hex()


def create_password_hash(password: str) -> tuple[str, str]:
    salt = secrets.token_bytes(16)
    return salt.hex(), hash_password(password, salt)
