import os
import subprocess

from .config import COMMANDS_DIR


def format_command_label(
    filename
):
    name = os.path.splitext(filename)[0]
    label = (name .replace("_", " ") .replace("-", " "))
    formatted_label = ""

    for character in label:
        if (
            character.isupper()
            and formatted_label
            and not formatted_label.endswith(
                " "
            )
        ):
            formatted_label += " "

        formatted_label += character

    return (
        formatted_label.strip().title()
    )


def get_commands():
    commands = []

    if not COMMANDS_DIR.is_dir():
        return commands

    for filename in sorted(os.listdir(COMMANDS_DIR)
    ):
        path = (COMMANDS_DIR / filename)

        if not path.is_file():
            continue

        if not os.access(path, os.X_OK):
            continue

        commands.append(
            {
                "file": filename,
                "label": format_command_label(filename),
            }
        )

    return commands


def run_command(
    filename
):
    safe_filename = (os.path.basename(filename))

    if safe_filename != filename: 
        raise ValueError("Invalid command name")

    path = (COMMANDS_DIR / safe_filename)

    if not path.is_file():
        raise FileNotFoundError("Command does not exist")

    if not os.access(path, os.X_OK):
        raise PermissionError("Command is not executable")

    subprocess.Popen([str(path)], cwd=str(COMMANDS_DIR),
        start_new_session=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )