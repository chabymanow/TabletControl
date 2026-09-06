#!/usr/bin/env python3

import json
import os
import subprocess
import threading
import time

from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

import psutil


PORT = 8765

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

COMMANDS_DIR = os.path.expanduser(
    "~/tabletCommands"
)


previous_network = psutil.net_io_counters()
previous_network_time = time.time()

network_lock = threading.Lock()


def get_temperature():
    try:
        temperatures = psutil.sensors_temperatures()

        preferred_names = [
            "k10temp",
            "coretemp",
            "zenpower",
            "cpu_thermal",
        ]

        for name in preferred_names:
            if name not in temperatures:
                continue

            values = [
                sensor.current
                for sensor in temperatures[name]
                if sensor.current is not None
            ]

            if values:
                return round(max(values), 1)

    except Exception:
        pass

    return None


def get_network_speed():
    global previous_network
    global previous_network_time

    with network_lock:
        now = time.time()
        current = psutil.net_io_counters()

        elapsed = now - previous_network_time

        if elapsed <= 0:
            return 0, 0

        download = (
            current.bytes_recv -
            previous_network.bytes_recv
        ) / elapsed

        upload = (
            current.bytes_sent -
            previous_network.bytes_sent
        ) / elapsed

        previous_network = current
        previous_network_time = now

        return (
            max(download, 0),
            max(upload, 0),
        )


def get_disks():
    disks = []

    try:
        result = subprocess.run(
            [
                "/usr/bin/lsblk",
                "-J",
                "-b",
                "-o",
                "NAME,PATH,TYPE,FSTYPE,MOUNTPOINTS,SIZE,MODEL",
            ],
            capture_output=True,
            text=True,
            check=True,
        )

        data = json.loads(
            result.stdout
        )

    except Exception as error:
        print(
            f"Disk discovery failed: {error}"
        )

        return disks


    def process_device(
        device,
        parent_model="",
        parent_device=""
    ):
        name = device.get("name", "")
        path = device.get("path", "")
        device_type = device.get("type", "")
        filesystem = device.get("fstype") or ""
        size = device.get("size") or 0
        model = device.get("model") or parent_model

        mountpoints = device.get("mountpoints") or []

        if isinstance(
            mountpoints,
            str
        ):
            mountpoints = [
                mountpoints
            ]

        valid_mountpoints = [
            mountpoint
            for mountpoint in mountpoints
            if mountpoint
        ]

        children = device.get(
            "children",
            []
        )

        #
        # Mounted filesystem / partition
        #
        if valid_mountpoints:
            preferred_mountpoint = (
                "/"
                if "/" in valid_mountpoints
                else valid_mountpoints[0]
            )

            try:
                usage = psutil.disk_usage(
                    preferred_mountpoint
                )

                disks.append(
                    {
                        "device": path,
                        "name": name,
                        "model": model,
                        "parent": parent_device,
                        "type": device_type,
                        "mountpoint": preferred_mountpoint,
                        "mountpoints": valid_mountpoints,
                        "filesystem": filesystem,
                        "percent": usage.percent,
                        "used": usage.used,
                        "free": usage.free,
                        "total": usage.total,
                        "mounted": True,
                    }
                )

            except (
                PermissionError,
                OSError
            ):
                pass

        #
        # Standalone physical disk with no partitions
        #
        elif (
            device_type == "disk"
            and not children
            and size > 0
        ):
            disks.append(
                {
                    "device": path,
                    "name": name,
                    "model": model,
                    "parent": parent_device,
                    "type": device_type,
                    "mountpoint": "",
                    "mountpoints": [],
                    "filesystem": filesystem,
                    "percent": None,
                    "used": None,
                    "free": None,
                    "total": size,
                    "mounted": False,
                }
            )

        #
        # Unmounted partition / encrypted / LVM volume
        #
        elif (
            device_type in {
                "part",
                "crypt",
                "lvm",
            }
            and size > 0
        ):
            disks.append(
                {
                    "device": path,
                    "name": name,
                    "model": model,
                    "parent": parent_device,
                    "type": device_type,
                    "mountpoint": "",
                    "mountpoints": [],
                    "filesystem": filesystem,
                    "percent": None,
                    "used": None,
                    "free": None,
                    "total": size,
                    "mounted": False,
                }
            )

        for child in children:
            process_device(
                child,
                model,
                path
            )


    for device in data.get(
        "blockdevices",
        []
    ):
        process_device(
            device
        )


    #
    # Remove duplicate entries.
    #
    unique_disks = {}

    for disk in disks:
        key = (
            disk["device"],
            disk["mountpoint"],
        )

        unique_disks[key] = disk


    #
    # Put root first, followed by mounted
    # drives, then unmounted drives.
    #
    result = list(
        unique_disks.values()
    )

    result.sort(
        key=lambda disk: (
            disk["mountpoint"] != "/",
            not disk["mounted"],
            disk["device"],
        )
    )

    return result


def get_stats():
    memory = psutil.virtual_memory()

    download, upload = get_network_speed()

    uptime_seconds = int(
        time.time() -
        psutil.boot_time()
    )

    return {
        "cpu": psutil.cpu_percent(
            interval=0.1
        ),

        "memory": {
            "percent": memory.percent,
            "used": memory.used,
            "total": memory.total,
        },

        "disks": get_disks(),

        "temperature": get_temperature(),

        "network": {
            "download": download,
            "upload": upload,
        },

        "uptime": uptime_seconds,
    }


def get_commands():
    commands = []

    if not os.path.isdir(
        COMMANDS_DIR
    ):
        return commands

    for filename in sorted(
        os.listdir(
            COMMANDS_DIR
        )
    ):
        path = os.path.join(
            COMMANDS_DIR,
            filename
        )

        if not os.path.isfile(
            path
        ):
            continue

        if not os.access(
            path,
            os.X_OK
        ):
            continue

        name = os.path.splitext(
            filename
        )[0]

        label = (
            name
            .replace("_", " ")
            .replace("-", " ")
        )

        #
        # Add spaces before capital letters.
        #
        formatted_label = ""

        for character in label:
            if (
                character.isupper()
                and formatted_label
                and not formatted_label.endswith(" ")
            ):
                formatted_label += " "

            formatted_label += character

        formatted_label = (
            formatted_label
            .strip()
            .title()
        )

        commands.append(
            {
                "file": filename,
                "label": formatted_label,
            }
        )

    return commands


def run_command(
    filename
):
    safe_filename = os.path.basename(
        filename
    )

    if safe_filename != filename:
        raise ValueError(
            "Invalid command name"
        )

    path = os.path.join(
        COMMANDS_DIR,
        safe_filename
    )

    if not os.path.isfile(
        path
    ):
        raise FileNotFoundError(
            "Command does not exist"
        )

    if not os.access(
        path,
        os.X_OK
    ):
        raise PermissionError(
            "Command is not executable"
        )

    subprocess.Popen(
        [path],
        cwd=COMMANDS_DIR,
        start_new_session=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


class DashboardHandler(
    SimpleHTTPRequestHandler
):

    def end_headers(
        self
    ):
        self.send_header(
            "Cache-Control",
            "no-store, no-cache, must-revalidate"
        )

        self.send_header(
            "Pragma",
            "no-cache"
        )

        self.send_header(
            "Expires",
            "0"
        )

        super().end_headers()


    def send_json(
        self,
        data,
        status=200
    ):
        body = json.dumps(
            data
        ).encode(
            "utf-8"
        )

        self.send_response(
            status
        )

        self.send_header(
            "Content-Type",
            "application/json"
        )

        self.send_header(
            "Content-Length",
            str(len(body))
        )

        self.end_headers()

        self.wfile.write(
            body
        )


    def do_GET(
        self
    ):
        path = urlparse(
            self.path
        ).path

        if path == "/api/stats":
            self.send_json(
                get_stats()
            )

            return

        if path == "/api/commands":
            self.send_json(
                get_commands()
            )

            return

        return super().do_GET()


    def do_POST(
        self
    ):
        path = urlparse(
            self.path
        ).path

        if path != "/api/run":
            self.send_json(
                {
                    "success": False,
                    "message": "Not found",
                },
                404
            )

            return

        length = int(
            self.headers.get(
                "Content-Length",
                0
            )
        )

        body = self.rfile.read(
            length
        ).decode(
            "utf-8"
        )

        data = parse_qs(
            body
        )

        filename = data.get(
            "command",
            [""]
        )[0]

        try:
            run_command(
                filename
            )

            self.send_json(
                {
                    "success": True,
                    "message": "Command started",
                }
            )

        except Exception as error:
            self.send_json(
                {
                    "success": False,
                    "message": str(error),
                },
                400
            )


    def log_message(
        self,
        format,
        *args
    ):
        return


if __name__ == "__main__":
    os.chdir(
        BASE_DIR
    )

    server = ThreadingHTTPServer(
        (
            "0.0.0.0",
            PORT
        ),
        DashboardHandler
    )

    print("")
    print("Tablet Dashboard")
    print("----------------")
    print(
        f"Listening on port {PORT}"
    )
    print(
        f"Commands: {COMMANDS_DIR}"
    )
    print("")

    try:
        server.serve_forever()

    except KeyboardInterrupt:
        print(
            "\nStopping dashboard."
        )

        server.server_close()