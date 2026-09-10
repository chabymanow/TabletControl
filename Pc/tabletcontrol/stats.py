import json
import shutil
import subprocess
import threading
import time

import psutil


previous_network = psutil.net_io_counters()
previous_network_time = time.time()
network_lock = threading.Lock()


def get_temperature():
    try:
        temperatures = psutil.sensors_temperatures()
        preferred_names = ["k10temp", "coretemp", "zenpower", "cpu_thermal"]

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
            return (0, 0)

        download = (current.bytes_recv - previous_network.bytes_recv) / elapsed
        upload = (current.bytes_sent - previous_network.bytes_sent) / elapsed
        previous_network = current
        previous_network_time = now

        return (
            max(download, 0),
            max(upload, 0),
        )


def get_disks():
    disks = []
    lsblk_path = shutil.which("lsblk")

    if not lsblk_path:
        return disks

    try:
        result = subprocess.run(
            [
                lsblk_path,
                "-J",
                "-b",
                "-o",
                "NAME,PATH,TYPE,FSTYPE,MOUNTPOINTS,SIZE,MODEL",
            ],
            capture_output=True,
            text=True,
            check=True,
        )

        data = json.loads(result.stdout)

    except Exception as error:
        print(f"Disk discovery failed: {error}")
        return disks

    ignored_mountpoints = {
        "/boot",
        "/boot/efi",
        "/efi",
        "[SWAP]",
    }

    def get_mountpoints(device):
        mountpoints = device.get("mountpoints") or []

        if isinstance(mountpoints, str):
            mountpoints = [mountpoints]

        return [
            mountpoint
            for mountpoint in mountpoints
            if mountpoint
        ]

    def is_ignored_device(device):
        filesystem = (device.get("fstype") or "").lower()
        device_type = (device.get("type") or "").lower()
        path = device.get("path") or ""
        mountpoints = get_mountpoints(device)

        if device_type == "loop" or path.startswith("/dev/loop"):
            return True

        if filesystem in {"squashfs", "swap"}:
            return True

        if any(
            mountpoint == "/snap"
            or mountpoint.startswith("/snap/")
            for mountpoint in mountpoints
        ):
            return True

        return False

    def has_visible_mounted_descendant(device):
        if is_ignored_device(device):
            return False

        visible_mountpoints = [
            mountpoint
            for mountpoint in get_mountpoints(device)
            if mountpoint not in ignored_mountpoints
        ]

        if visible_mountpoints:
            return True

        return any(
            has_visible_mounted_descendant(child)
            for child in device.get("children", [])
        )

    def append_unmounted_disk(device):
        size = device.get("size") or 0

        if size <= 0:
            return

        disks.append(
            {
                "device": device.get("path", ""),
                "name": device.get("name", ""),
                "model": device.get("model") or "",
                "parent": "",
                "type": device.get("type", ""),
                "mountpoint": "",
                "mountpoints": [],
                "filesystem": device.get("fstype") or "",
                "percent": None,
                "used": None,
                "free": None,
                "total": size,
                "mounted": False,
            }
        )

    def process_device(device, parent_model="", parent_device=""):
        if is_ignored_device(device):
            return

        name = device.get("name", "")
        path = device.get("path", "")
        device_type = device.get("type", "")
        filesystem = device.get("fstype") or ""
        model = device.get("model") or parent_model
        mountpoints = get_mountpoints(device)
        children = device.get("children", [])

        visible_mountpoints = [
            mountpoint
            for mountpoint in mountpoints
            if mountpoint not in ignored_mountpoints
        ]

        if visible_mountpoints:
            preferred_mountpoint = (
                "/"
                if "/" in visible_mountpoints
                else visible_mountpoints[0]
            )

            try:
                usage = psutil.disk_usage(preferred_mountpoint)

                disks.append(
                    {
                        "device": path,
                        "name": name,
                        "model": model,
                        "parent": parent_device,
                        "type": device_type,
                        "mountpoint": preferred_mountpoint,
                        "mountpoints": visible_mountpoints,
                        "filesystem": filesystem,
                        "percent": usage.percent,
                        "used": usage.used,
                        "free": usage.free,
                        "total": usage.total,
                        "mounted": True,
                    }
                )

            except (PermissionError, OSError):
                pass

        for child in children:
            process_device(child, model, path)

    for device in data.get("blockdevices", []):
        if is_ignored_device(device):
            continue

        process_device(device)

        # If an entire physical disk has no mounted user-visible volume,
        # represent it once as a disk instead of listing every unmounted
        # partition (EFI, recovery, Windows partitions, etc.).
        if (
            device.get("type") == "disk"
            and not has_visible_mounted_descendant(device)
        ):
            append_unmounted_disk(device)

    unique_disks = {}

    for disk in disks:
        key = (
            disk["device"],
            disk["mountpoint"],
        )
        unique_disks[key] = disk

    result = list(unique_disks.values())

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
    uptime_seconds = int(time.time() - psutil.boot_time())

    return {
        "cpu": psutil.cpu_percent(interval=0.1),
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
