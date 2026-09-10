import hashlib
import hmac
import json
import secrets
import threading
import time

from .config import (
    AUTH_FILE,
    CONFIG_DIR,
    PAIRING_CODE_TTL_SECONDS,
    PAIRING_MAX_ATTEMPTS,
    REQUIRE_AUTH,
    SESSION_COOKIE_NAME,
)

_auth_lock = threading.RLock()
_pairing_code_hash = None
_pairing_expires_at = 0
_pairing_attempts = 0

def authentication_enabled():
    return REQUIRE_AUTH

def hash_value(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()

def load_auth_data():
    if not AUTH_FILE.exists():
        return {"devices": []}

    try:
        with AUTH_FILE.open("r", encoding="utf-8") as file:
            data = json.load(file)

        if not isinstance(data, dict):
            return {"devices": []}

        devices = data.get("devices")

        if not isinstance(devices, list):
            data["devices"] = []

        return data

    except (OSError, json.JSONDecodeError):
        return {"devices": []}

def save_auth_data(data):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    temporary_file = AUTH_FILE.with_suffix(".tmp")

    with temporary_file.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=4)

    temporary_file.chmod(0o600)
    temporary_file.replace(AUTH_FILE)

def create_pairing_code():
    global _pairing_code_hash
    global _pairing_expires_at
    global _pairing_attempts

    code = f"{secrets.randbelow(1000000):06d}"

    with _auth_lock:
        _pairing_code_hash = hash_value(code)
        _pairing_expires_at = (time.time() + PAIRING_CODE_TTL_SECONDS)
        _pairing_attempts = 0

    return code

def pairing_is_active():
    with _auth_lock:
        if _pairing_code_hash is None:
            return False

        return time.time() < _pairing_expires_at

def get_pairing_seconds_remaining():
    with _auth_lock:
        if _pairing_code_hash is None:
            return 0

        remaining = int(_pairing_expires_at - time.time())

        return max(0, remaining)

def clear_pairing():
    global _pairing_code_hash
    global _pairing_expires_at
    global _pairing_attempts

    with _auth_lock:
        _pairing_code_hash = None
        _pairing_expires_at = 0
        _pairing_attempts = 0

def verify_pairing_code(code):
    global _pairing_attempts
    supplied_hash = hash_value(code.strip())

    with _auth_lock:
        if _pairing_code_hash is None:
            return False

        if time.time() >= _pairing_expires_at:
            clear_pairing()

            return False

        if _pairing_attempts >= PAIRING_MAX_ATTEMPTS:
            clear_pairing()

            return False

        if not hmac.compare_digest(supplied_hash, _pairing_code_hash):
            _pairing_attempts += 1
            if _pairing_attempts >= PAIRING_MAX_ATTEMPTS:
                clear_pairing()
            return False
        clear_pairing()
        return True

def create_device_token(device_name):
    token = secrets.token_urlsafe(32)
    token_hash = hash_value(token)
    device_id = secrets.token_hex(8)
    device = {
        "id": device_id,
        "name": device_name.strip() or "Android Tablet",
        "token_hash": token_hash,
        "created_at": int(time.time()),
        "last_used": int(time.time()),
    }

    with _auth_lock:
        data = load_auth_data()
        data["devices"].append(device)
        save_auth_data(data)

    return {
        "device_id": device_id,
        "token": token,
    }

def validate_token(token):
    if not token:
        return None

    token_hash = hash_value(token)

    with _auth_lock:
        data = load_auth_data()

        for device in data["devices"]:
            stored_hash = device.get("token_hash", "")

            if hmac.compare_digest(token_hash, stored_hash):
                device["last_used"] = int(time.time())
                save_auth_data(data)

                return device

    return None

def get_bearer_token(headers):
    authorization = headers.get("Authorization", "")
    prefix = "Bearer "
    if not authorization.startswith(prefix):
        return None

    return authorization[len(prefix):].strip()

def get_cookie_token(headers):
    cookie_header = headers.get("Cookie", "")

    if not cookie_header:
        return None

    cookies = cookie_header.split(";")

    for cookie in cookies:
        name, separator, value = cookie.strip().partition("=")

        if (separator and name == SESSION_COOKIE_NAME):
            return value.strip()

    return None


def get_authenticated_device(headers):
    token = get_bearer_token(headers)

    if not token:
        token = get_cookie_token(headers)

    return validate_token(token)


def is_authorized(headers):
    if not authentication_enabled():
        return True

    return get_authenticated_device(headers) is not None


def get_paired_devices():
    with _auth_lock:
        data = load_auth_data()

        return [
            {
                "id": device.get("id"),
                "name": device.get("name"),
                "created_at": device.get("created_at"),
                "last_used": device.get("last_used"),
            }
            for device in data["devices"]
        ]


def update_paired_device_name(device_id, device_name):
    clean_name = str(device_name).strip()[:80]

    if not clean_name:
        return False

    with _auth_lock:
        data = load_auth_data()

        for device in data["devices"]:
            if device.get("id") == device_id:
                if device.get("name") != clean_name:
                    device["name"] = clean_name
                    save_auth_data(data)

                return True

    return False


def remove_paired_device(device_id):
    with _auth_lock:
        data = load_auth_data()

        original_count = len(data["devices"])

        data["devices"] = [
            device
            for device in data["devices"]
            if device.get("id") != device_id
        ]

        if len(data["devices"]) == original_count:
            return False

        save_auth_data(data)

        return True