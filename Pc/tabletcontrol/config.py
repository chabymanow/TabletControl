import os

from pathlib import Path


def get_boolean_environment(name, default=False):
    value = os.environ.get(name)

    if value is None:
        return default

    return value.strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


HOST = os.environ.get("TABLETCONTROL_HOST", "0.0.0.0").strip() or "0.0.0.0"
PORT = int(os.environ.get("TABLETCONTROL_PORT", "8765"))
PACKAGE_DIR = Path(__file__).resolve().parent
PC_DIR = PACKAGE_DIR.parent
WEB_DIR = PC_DIR
COMMANDS_DIR = Path(os.path.expanduser(os.environ.get("TABLETCONTROL_COMMANDS_DIR", "~/tabletCommands")))
CONFIG_DIR = Path(os.path.expanduser(os.environ.get("TABLETCONTROL_CONFIG_DIR", "~/.config/tabletcontrol")))
AUTH_FILE = CONFIG_DIR / "auth.json"
REQUIRE_AUTH = get_boolean_environment("TABLETCONTROL_REQUIRE_AUTH", False)
PAIRING_CODE_TTL_SECONDS = 300
PAIRING_MAX_ATTEMPTS = 5
SESSION_COOKIE_NAME = "tabletcontrol_session"
SESSION_MAX_AGE_SECONDS = 31536000
LOG_REQUESTS = get_boolean_environment("TABLETCONTROL_LOG_REQUESTS", False)