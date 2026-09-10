import json
import shutil
import subprocess
import threading
import time

import psutil


previous_network = (psutil.net_io_counters())

previous_network_time = (time.time())

network_lock = (threading.Lock())

def get_temperature():
    try:
        temperatures = (psutil.sensors_temperatures())

        preferred_names = ["k10temp", "coretemp", "zenpower", "cpu_thermal",]

        for name in preferred_names:
            if name not in temperatures:
                continue

            values = [
                sensor.current
                for sensor in temperatures[name]
                if sensor.current is not None
            ]

            if values:
                return round(
                    max(values),
                    1
                )

    except Exception:
        pass

    return None


def get_network_speed():
    global previous_network
    global previous_network_time

    with network_lock:
        now = time.time()

        current = (psutil.net_io_counters())

        elapsed = (now - previous_network_time)

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


    def process_device(device, parent_model="", parent_device=""):
        name = device.get("name", "")

        path = device.get("path", "")
        device_type = device.get("type", "")
        filesystem = (device.get("fstype") or "")
        size = (device.get("size") or 0)
        model = (device.get("model") or parent_model)
        mountpoints = (device.get("mountpoints") or [])

        if isinstance(mountpoints, str):
            mountpoints = [mountpoints]

        valid_mountpoints = [mountpoint
            for mountpoint in mountpoints
            if mountpoint
        ]

        children = device.get("children", [])


        #
        # Ignore virtual read-only package images such as Snap mounts.
        # These appear as /dev/loop* devices with squashfs and are not
        # user storage volumes.
        #
        if (
            device_type == "loop"
            or filesystem == "squashfs"
            or any(
                mountpoint == "/snap"
                or mountpoint.startswith("/snap/")
                for mountpoint in valid_mountpoints
            )
        ):
            return


        #
        # Mounted filesystem / partition
        #
        if valid_mountpoints:
            preferred_mountpoint = ("/"
                if "/" in valid_mountpoints
                else valid_mountpoints[0]
            )

            try:
                usage = (psutil.disk_usage(preferred_mountpoint))
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
        # Standalone physical disk
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
        # Unmounted partition / encrypted / LVM
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


    for device in data.get("blockdevices", []):
        process_device(device)

    #
    # Remove duplicates
    #
    unique_disks = {}

    for disk in disks:
        key = (
            disk["device"],
            disk["mountpoint"],
        )

        unique_disks[key] = disk


    result = list(unique_disks.values())


    #
    # Root first, then mounted,
    # then unmounted.
    #
    result.sort(
        key=lambda disk: (
            disk["mountpoint"] != "/",
            not disk["mounted"],
            disk["device"],
        )
    )

    return result

def get_stats():
    memory = (psutil.virtual_memory())
    download, upload = (get_network_speed())
    uptime_seconds = int(time.time() - psutil.boot_time())

    return {
        "cpu": psutil.cpu_percent(interval=0.1),

        "memory": {
            "percent": memory.percent,
            "used": memory.used,
            "total": memory.total,
        },

        "disks": get_disks(),

        "temperature": (
            get_temperature()
        ),

        "network": {
            "download": download,
            "upload": upload,
        },

        "uptime": uptime_seconds,
    }
