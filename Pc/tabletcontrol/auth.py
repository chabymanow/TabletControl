import hmac

from .config import AUTH_TOKEN

def authentication_enabled():
    return bool(AUTH_TOKEN)

def is_authorized(headers):
    if not authentication_enabled():
        return True

    authorization = headers.get("Authorization", "")

    prefix = "Bearer "

    if not authorization.startswith(prefix):
        return False

    supplied_token = (authorization[len(prefix):].strip())

    return hmac.compare_digest(supplied_token, AUTH_TOKEN)