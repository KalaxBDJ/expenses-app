import hashlib
import hmac
import secrets
import string


HASH_NAME = "sha256"
ITERATIONS = 120_000
SALT_BYTES = 16


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(SALT_BYTES)
    digest = hashlib.pbkdf2_hmac(HASH_NAME, password.encode("utf-8"), salt, ITERATIONS)
    return f"pbkdf2_{HASH_NAME}${ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        algorithm, iterations, salt_hex, digest_hex = stored_hash.split("$", 3)
        if algorithm != f"pbkdf2_{HASH_NAME}":
            return False
        expected = bytes.fromhex(digest_hex)
        actual = hashlib.pbkdf2_hmac(
            HASH_NAME,
            password.encode("utf-8"),
            bytes.fromhex(salt_hex),
            int(iterations),
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(actual, expected)


def create_session_token() -> str:
    return secrets.token_urlsafe(32)


def create_api_key() -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(48))


def hash_api_key(api_key: str) -> str:
    digest = hashlib.sha256(api_key.encode("utf-8")).hexdigest()
    return f"sha256${digest}"


def verify_api_key(api_key: str, stored_hash: str) -> bool:
    try:
        algorithm, digest_hex = stored_hash.split("$", 1)
        if algorithm != "sha256":
            return False
    except (ValueError, TypeError):
        return False
    actual = hashlib.sha256(api_key.encode("utf-8")).hexdigest()
    return hmac.compare_digest(actual, digest_hex)
