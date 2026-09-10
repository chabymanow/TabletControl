import ipaddress
import json
import socket

import psutil

from http.server import SimpleHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

from .auth import (
    authentication_enabled,
    create_device_token,
    create_pairing_code,
    get_authenticated_device,
    get_paired_devices,
    get_pairing_seconds_remaining,
    is_authorized,
    pairing_is_active,
    remove_paired_device,
    update_paired_device_name,
    verify_pairing_code,
)
from .commands import get_commands, run_command
from .config import (
    LOG_REQUESTS,
    PAIRING_CODE_TTL_SECONDS,
    PORT,
    SESSION_COOKIE_NAME,
    SESSION_MAX_AGE_SECONDS,
    WEB_DIR,
)
from .stats import get_stats


def get_primary_ipv4():
    connection = None

    try:
        connection = socket.socket(
            socket.AF_INET,
            socket.SOCK_DGRAM
        )
        connection.connect(("1.1.1.1", 80))
        address = connection.getsockname()[0]
        parsed_address = ipaddress.ip_address(address)

        if (
            parsed_address.version == 4
            and not parsed_address.is_loopback
            and not parsed_address.is_link_local
            and not parsed_address.is_unspecified
        ):
            return address
    except (OSError, ValueError):
        pass
    finally:
        if connection is not None:
            connection.close()

    try:
        interface_stats = psutil.net_if_stats()

        for interface_name, addresses in psutil.net_if_addrs().items():
            if interface_name == "lo":
                continue

            interface = interface_stats.get(interface_name)
            if interface is not None and not interface.isup:
                continue

            for address in addresses:
                if address.family != socket.AF_INET:
                    continue

                try:
                    parsed_address = ipaddress.ip_address(address.address)
                except ValueError:
                    continue

                if (
                    parsed_address.is_loopback
                    or parsed_address.is_link_local
                    or parsed_address.is_unspecified
                ):
                    continue

                if parsed_address.is_private:
                    return address.address

        for interface_name, addresses in psutil.net_if_addrs().items():
            if interface_name == "lo":
                continue

            for address in addresses:
                if address.family != socket.AF_INET:
                    continue

                try:
                    parsed_address = ipaddress.ip_address(address.address)
                except ValueError:
                    continue

                if (
                    not parsed_address.is_loopback
                    and not parsed_address.is_link_local
                    and not parsed_address.is_unspecified
                ):
                    return address.address
    except (OSError, ValueError):
        pass

    return None


class DashboardHandler(SimpleHTTPRequestHandler):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB_DIR), **kwargs)

    def end_headers(self):
        self.send_header(
            "Cache-Control",
            "no-store, no-cache, must-revalidate"
        )
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def send_json(self, data, status=200, headers=None):
        body = json.dumps(data).encode("utf-8")

        self.send_response(status)
        self.send_header(
            "Content-Type",
            "application/json; charset=utf-8"
        )
        self.send_header("Content-Length", str(len(body)))

        if headers:
            for name, value in headers.items():
                self.send_header(name, value)

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

    def is_local_request(self):
        return self.client_address[0] in {
            "127.0.0.1",
            "::1",
        }

    def is_safe_local_browser_request(self):
        if not self.is_local_request():
            return False

        fetch_site = self.headers.get(
            "Sec-Fetch-Site",
            ""
        ).lower()

        if fetch_site not in {
            "",
            "same-origin",
            "none",
        }:
            return False

        origin = self.headers.get("Origin", "")

        if not origin:
            return True

        return origin in {
            f"http://127.0.0.1:{PORT}",
            f"http://localhost:{PORT}",
            f"http://[::1]:{PORT}",
        }

    def require_local_management(self):
        if self.is_safe_local_browser_request():
            return True

        self.send_error_json(
            "This action is only available locally on the PC.",
            403
        )
        return False

    def require_authorization(self):
        if self.is_safe_local_browser_request():
            return True

        if is_authorized(self.headers):
            return True

        self.send_error_json("Unauthorized", 401)
        return False

    def read_request_data(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
        except ValueError:
            raise ValueError("Invalid Content-Length")

        if length <= 0:
            return {}

        body = self.rfile.read(length).decode("utf-8")
        content_type = self.headers.get("Content-Type", "")

        if "application/json" in content_type:
            try:
                data = json.loads(body)
            except json.JSONDecodeError:
                raise ValueError("Invalid JSON")

            if not isinstance(data, dict):
                raise ValueError("Request body must be an object")

            return data

        parsed = parse_qs(body)
        return {
            key: values[0]
            for key, values in parsed.items()
            if values
        }

    def handle_pairing_info(self):
        if not self.require_local_management():
            return

        address = get_primary_ipv4()

        self.send_json(
            {
                "success": True,
                "hostname": socket.gethostname(),
                "ip": address,
                "port": PORT,
                "url": f"http://{address}:{PORT}" if address else None,
            }
        )

    def handle_pairing_status(self):
        self.send_json(
            {
                "success": True,
                "authentication_required": authentication_enabled(),
                "pairing_active": pairing_is_active(),
                "expires_in": get_pairing_seconds_remaining(),
            }
        )

    def handle_pairing_start(self):
        if not self.require_local_management():
            return

        code = create_pairing_code()

        self.send_json(
            {
                "success": True,
                "code": code,
                "expires_in": PAIRING_CODE_TTL_SECONDS,
            }
        )

    def handle_pairing(self):
        try:
            data = self.read_request_data()
        except ValueError as error:
            self.send_error_json(str(error), 400)
            return

        code = str(data.get("code", "")).strip()
        device_name = str(
            data.get("device_name", "Android Tablet")
        ).strip()

        if not code:
            self.send_error_json("Pairing code is required.", 400)
            return

        if not verify_pairing_code(code):
            self.send_error_json(
                "Invalid or expired pairing code.",
                401
            )
            return

        credentials = create_device_token(device_name)
        token = credentials["token"]

        cookie = (
            f"{SESSION_COOKIE_NAME}={token}; "
            f"Path=/; "
            f"Max-Age={SESSION_MAX_AGE_SECONDS}; "
            f"HttpOnly; "
            f"SameSite=Strict"
        )

        self.send_json(
            {
                "success": True,
                "device_id": credentials["device_id"],
                "token": token,
            },
            headers={
                "Set-Cookie": cookie,
            }
        )

    def handle_paired_devices(self):
        if not self.require_local_management():
            return

        self.send_json(
            {
                "success": True,
                "devices": get_paired_devices(),
            }
        )

    def handle_remove_device(self):
        if not self.require_local_management():
            return

        try:
            data = self.read_request_data()
        except ValueError as error:
            self.send_error_json(str(error), 400)
            return

        device_id = str(data.get("device_id", "")).strip()

        if not device_id:
            self.send_error_json("Device ID is required.", 400)
            return

        if not remove_paired_device(device_id):
            self.send_error_json("Device not found.", 404)
            return

        self.send_json(
            {
                "success": True,
                "message": "Device removed.",
            }
        )

    def handle_device_name(self):
        device = get_authenticated_device(self.headers)

        if device is None:
            self.send_error_json("Unauthorized", 401)
            return

        try:
            data = self.read_request_data()
        except ValueError as error:
            self.send_error_json(str(error), 400)
            return

        device_name = str(data.get("device_name", "")).strip()[:80]

        if not device_name:
            self.send_error_json("Device name is required.", 400)
            return

        if not update_paired_device_name(device.get("id"), device_name):
            self.send_error_json("Device not found.", 404)
            return

        self.send_json(
            {
                "success": True,
                "message": "Device name updated.",
                "device_name": device_name,
            }
        )

    def handle_unpair(self):
        device = get_authenticated_device(self.headers)

        if device is None:
            self.send_error_json("Unauthorized", 401)
            return

        device_id = device.get("id")

        if not device_id or not remove_paired_device(device_id):
            self.send_error_json("Device not found.", 404)
            return

        expired_cookie = (
            f"{SESSION_COOKIE_NAME}=; "
            f"Path=/; "
            f"Max-Age=0; "
            f"HttpOnly; "
            f"SameSite=Strict"
        )

        self.send_json(
            {
                "success": True,
                "message": "Device unpaired.",
            },
            headers={
                "Set-Cookie": expired_cookie,
            }
        )

    def serve_pairing_page(self):
        if not self.require_local_management():
            return

        self.path = "/pair.html"
        return super().do_GET()

    def do_GET(self):
        path = urlparse(self.path).path

        if path in {
            "/pair",
            "/pair.html",
        }:
            self.serve_pairing_page()
            return

        if path == "/api/pair/info":
            self.handle_pairing_info()
            return

        if path == "/api/pair/status":
            self.handle_pairing_status()
            return

        if path == "/api/pair/devices":
            self.handle_paired_devices()
            return

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

        if path == "/api/pair/start":
            self.handle_pairing_start()
            return

        if path == "/api/pair":
            self.handle_pairing()
            return

        if path == "/api/pair/remove":
            self.handle_remove_device()
            return

        if path == "/api/pair/name":
            self.handle_device_name()
            return

        if path == "/api/pair/unpair":
            self.handle_unpair()
            return

        if path != "/api/run":
            self.send_error_json("Not found", 404)
            return

        if not self.require_authorization():
            return

        try:
            data = self.read_request_data()
        except ValueError as error:
            self.send_error_json(str(error), 400)
            return

        filename = str(data.get("command", "")).strip()

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
            self.send_error_json(
                f"Unable to start command: {error}",
                500
            )

    def log_message(self, format, *args):
        if LOG_REQUESTS:
            super().log_message(format, *args)
