import shutil
import subprocess

from .config import PC_DIR


UPDATE_HELPER = PC_DIR / "run-update.sh"
UPDATE_UNIT = "tabletcontrol-update.service"


def start_update():
    systemctl = shutil.which("systemctl")
    systemd_run = shutil.which("systemd-run")

    if not systemctl or not systemd_run:
        raise RuntimeError("systemd update tools are not available on this PC.")

    if not UPDATE_HELPER.is_file():
        raise FileNotFoundError(
            "The dashboard updater is not installed. Run install.sh once from the TabletControl repository."
        )

    active = subprocess.run(
        [
            systemctl,
            "--user",
            "is-active",
            "--quiet",
            UPDATE_UNIT,
        ],
        check=False,
    )

    if active.returncode == 0:
        return {
            "success": False,
            "message": "A TabletControl update is already running.",
        }

    result = subprocess.run(
        [
            systemd_run,
            "--user",
            "--unit=tabletcontrol-update",
            "--collect",
            "--no-block",
            "/bin/bash",
            str(UPDATE_HELPER),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        message = (result.stderr or result.stdout).strip()

        raise RuntimeError(
            message or "Unable to start the TabletControl update."
        )

    return {
        "success": True,
        "message": "Update started. TabletControl will restart automatically.",
    }
