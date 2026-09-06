import os
from pathlib import Path

HOST = "0.0.0.0"
PORT = 8765

PACKAGE_DIR = Path(__file__).resolve().parent
PC_DIR = PACKAGE_DIR.parent
WEB_DIR = PC_DIR
COMMANDS_DIR = Path(os.path.expanduser("~/tabletCommands"))
AUTH_TOKEN = os.environ.get("TABLETCONTROL_AUTH_TOKEN", "").strip()
LOG_REQUESTS = False