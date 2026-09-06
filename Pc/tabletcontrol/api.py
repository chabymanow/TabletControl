import json

from http.server import (SimpleHTTPRequestHandler)
from urllib.parse import (parse_qs, urlparse)
from .auth import is_authorized
from .commands import (get_commands, run_command)
from .config import (LOG_REQUESTS, WEB_DIR)
from .stats import (get_stats)

class DashboardHandler(SimpleHTTPRequestHandler):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB_DIR), **kwargs)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def send_json(self, data, status=200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type","application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_error_json(self, message, status):
        self.send_json(
            {
                "success": False,
                "message": message,
            },
            status
        )

    def require_authorization(self):
        if is_authorized(self.headers):
            return True
        self.send_error_json("Unauthorized", 401)

        return False

    def do_GET(self):
        path = urlparse(self.path).path

        if path == "/api/stats":
            if not self.require_authorization():
                return

            self.send_json(get_stats())

            return

        if path == "/api/commands":
            if not self.require_authorization():
                return

            self.send_json(get_commands())

            return

        return super().do_GET()

    def do_POST(self):
        path = urlparse(self.path).path

        if path != "/api/run":
            self.send_error_json("Not found", 404)
            return


        if not self.require_authorization():
            return

        try:
            length = int(self.headers.get("Content-Length", 0))

        except ValueError:
            self.send_error_json("Invalid Content-Length", 400)

            return

        if length <= 0:
            self.send_error_json("Empty request", 400)

            return

        body = self.rfile.read(length).decode("utf-8")

        data = parse_qs(body)

        filename = data.get("command", [""])[0]

        if not filename:
            self.send_error_json("Command is required", 400)

            return

        try:
            run_command(filename)

            self.send_json(
                {
                    "success": True,
                    "message": "Command started",
                }
            )

        except (
            ValueError,
            FileNotFoundError,
            PermissionError
        ) as error:
            self.send_error_json(str(error), 400)

        except OSError as error:
            self.send_error_json(f"Unable to start command: {error}", 500)

    def log_message(self, format, *args):
        if LOG_REQUESTS:
            super().log_message(format, *args)