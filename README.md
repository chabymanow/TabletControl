# TabletControl

TabletControl turns an Android tablet into a companion dashboard and remote control for a Linux PC.

It consists of two parts:

- **Android app** — connects to the PC over the local network and displays the dashboard.
- **Linux PC Agent** — serves the dashboard, reports system information, discovers custom commands, and runs them on request.

The complete Android and Linux source code is included in this repository.

---

## Features

TabletControl currently provides:

- CPU usage
- Memory usage
- CPU temperature
- Download speed
- Upload speed
- System uptime
- Storage usage
- Mounted and unmounted drive information
- Remote command buttons
- Automatic command discovery
- Automatic startup through a systemd user service
- Automatic local IP detection during installation

System information is refreshed automatically every two seconds.

---

## How it works

```text
┌──────────────────────┐
│    Android Tablet    │
│                      │
│    TabletControl     │
└──────────┬───────────┘
           │
           │ Local network
           │ HTTP
           │ Port 8765
           │
           ▼
┌──────────────────────┐
│      Linux PC        │
│                      │
│  TabletControl Agent │
├──────────────────────┤
│ System statistics    │
│ Storage information  │
│ Command discovery    │
│ Command execution    │
└──────────────────────┘
```

The PC Agent listens on port:

```text
8765
```

A typical connection address looks like:

```text
http://192.168.1.100:8765
```

The PC and Android device must be able to communicate over the same local network.

---

## Repository structure

```text
TabletControl/
├── install.sh
├── README.md
├── LICENSE
├── .gitignore
│
├── PC/
│   ├── index.html
│   ├── style.css
│   │
│   └── tabletcontrol/
│       ├── __init__.py
│       ├── main.py
│       ├── api.py
│       ├── stats.py
│       ├── commands.py
│       ├── auth.py
│       └── config.py
│
└── Android/
    └── Android Studio project
```

---

# Installation

## 1. Clone the repository

```bash
git clone https://github.com/chabymanow/TabletControl.git
cd TabletControl
```

## 2. Run the installer

```bash
chmod +x install.sh
./install.sh
```

The installer is a Bash script, so it can be launched from Fish, Bash, Zsh, and other interactive shells using:

```bash
./install.sh
```

Do not source the installer.

For example, do not run:

```bash
source install.sh
```

---

## What the installer does

The installer:

- checks for Python 3
- checks for systemd user services
- checks Python virtual-environment support
- installs the PC Agent into:

```text
~/.local/share/tabletcontrol
```

- creates a private Python virtual environment
- installs the required Python dependency
- creates the command directory:

```text
~/tabletCommands
```

- creates the configuration file:

```text
~/.config/tabletcontrol/tabletcontrol.env
```

- creates the systemd user service:

```text
~/.config/systemd/user/tabletcontrol.service
```

- enables TabletControl to start automatically when you log in
- starts TabletControl immediately
- verifies that the service started successfully
- detects the main local IPv4 address
- prints the address to enter in the Android app

A successful installation should end with output similar to:

```text
TabletControl installed successfully

Service:
  tabletcontrol.service

Commands directory:
  /home/user/tabletCommands

PC address:
  http://192.168.1.100:8765

Android app:
  Enter: 192.168.1.100
```

The installer does not require root privileges and does not modify firewall settings.

---

# Android app

You can either build the Android application from source or install the signed APK from GitHub Releases.

Latest releases:

https://github.com/chabymanow/TabletControl/releases/latest

After installing the app:

1. Make sure TabletControl is running on the Linux PC.
2. Open TabletControl on Android.
3. Enter the IP address shown by the installer.
4. Connect.

Example:

```text
192.168.1.100
```

The PC Agent uses port `8765`.

---

# Remote commands

TabletControl automatically discovers executable files inside:

```text
~/tabletCommands
```

Each executable file becomes a button on the dashboard.

## Example

Create:

```text
~/tabletCommands/start_work.sh
```

with:

```bash
#!/usr/bin/env bash

firefox &
```

Make it executable:

```bash
chmod +x ~/tabletCommands/start_work.sh
```

Reload the TabletControl dashboard.

The file:

```text
start_work.sh
```

will appear as:

```text
Start Work
```

---

## Command naming

TabletControl converts command filenames into readable button labels.

Examples:

```text
start_work.sh
```

becomes:

```text
Start Work
```

```text
gaming-mode.sh
```

becomes:

```text
Gaming Mode
```

Only regular files with executable permission are displayed.

---

# Configuration

TabletControl stores its PC Agent configuration in:

```text
~/.config/tabletcontrol/tabletcontrol.env
```

Default values:

```text
TABLETCONTROL_HOST=0.0.0.0
TABLETCONTROL_PORT=8765
TABLETCONTROL_COMMANDS_DIR=/home/USER/tabletCommands
TABLETCONTROL_AUTH_TOKEN=
```

After changing configuration, restart the service:

```bash
systemctl --user restart tabletcontrol.service
```

---

# Service management

Check the service:

```bash
systemctl --user status tabletcontrol.service
```

Restart it:

```bash
systemctl --user restart tabletcontrol.service
```

Stop it:

```bash
systemctl --user stop tabletcontrol.service
```

Start it:

```bash
systemctl --user start tabletcontrol.service
```

View live logs:

```bash
journalctl --user -u tabletcontrol.service -f
```

The systemd user service starts TabletControl automatically when the user logs in.

Systemd documentation:

https://www.freedesktop.org/software/systemd/man/latest/systemd.service.html

---

# PC Agent API

TabletControl currently exposes three API endpoints used by the web dashboard and Android client.

## `GET /api/stats`

Returns current system information.

Example:

```json
{
    "cpu": 12.4,
    "memory": {
        "percent": 38.2,
        "used": 12884901888,
        "total": 34359738368
    },
    "disks": [],
    "temperature": 48.5,
    "network": {
        "download": 10240,
        "upload": 2048
    },
    "uptime": 86400
}
```

---

## `GET /api/commands`

Returns the executable commands currently available in:

```text
~/tabletCommands
```

Example:

```json
[
    {
        "file": "start_work.sh",
        "label": "Start Work"
    }
]
```

---

## `POST /api/run`

Runs one of the available commands.

Request type:

```text
application/x-www-form-urlencoded
```

Example body:

```text
command=start_work.sh
```

Example response:

```json
{
    "success": true,
    "message": "Command started"
}
```

---

# System monitoring

## CPU and memory

TabletControl uses `psutil` to read CPU and memory information.

psutil documentation:

https://psutil.readthedocs.io/

---

## CPU temperature

TabletControl checks common Linux temperature sensor groups including:

```text
k10temp
coretemp
zenpower
cpu_thermal
```

If no compatible CPU temperature sensor is available, the dashboard displays:

```text
N/A
```

---

## Storage

TabletControl uses `lsblk` to discover Linux storage devices and `psutil` to obtain filesystem usage.

The dashboard can display:

- device path
- mount point
- filesystem
- used space
- total space
- usage percentage
- unmounted devices

`lsblk` documentation:

https://man7.org/linux/man-pages/man8/lsblk.8.html

---

## Network traffic

Download and upload speed are calculated using network byte counters and displayed using appropriate units such as:

```text
KB/s
MB/s
GB/s
```

---

# Development

## PC Agent

The PC Agent is written in Python.

Main modules:

```text
config.py
```

Application configuration.

```text
stats.py
```

CPU, memory, temperature, storage, network and uptime collection.

```text
commands.py
```

Command discovery, command labels and command execution.

```text
api.py
```

HTTP API and web-file serving.

```text
auth.py
```

Authentication support for future secure pairing.

```text
main.py
```

PC Agent entry point.

To run the PC Agent manually from the `PC` directory:

```bash
python -m tabletcontrol.main
```

Python HTTP server documentation:

https://docs.python.org/3/library/http.server.html

---

## Android

The Android client is written in:

- Kotlin
- Jetpack Compose
- Gradle Kotlin DSL

Package:

```text
com.chaby.tabletcontrol
```

Android Jetpack Compose documentation:

https://developer.android.com/develop/ui/compose

---

# Security

## Important

The current version is intended for use on a trusted local network.

By default, the PC Agent listens on:

```text
0.0.0.0:8765
```

Authentication support exists in the PC Agent, but authentication is currently disabled by default while Android pairing is still being developed.

This means another device that can reach the PC on port `8765` may be able to access the TabletControl API.

Therefore:

- do not expose port `8765` directly to the public internet
- do not configure router port forwarding for TabletControl
- use TabletControl only on a trusted local network
- only place trusted executable files in `~/tabletCommands`

Future versions are planned to add secure tablet-to-PC pairing and authentication tokens.

---

# Troubleshooting

## Android shows "Web page not available"

Check that the service is running:

```bash
systemctl --user status tabletcontrol.service
```

Test the dashboard from the PC:

```text
http://localhost:8765
```

Then test from the tablet browser:

```text
http://PC-IP:8765
```

If the PC works but the tablet does not, check:

- the IP address
- Wi-Fi or LAN connectivity
- firewall settings
- whether both devices are on networks that can communicate

---

## No command buttons appear

Check the command directory:

```bash
ls -la ~/tabletCommands
```

Commands must be executable.

Example:

```bash
chmod +x ~/tabletCommands/start_work.sh
```

---

## Port 8765 is already in use

Check what is listening on the port:

```bash
ss -ltnp | grep 8765
```

If an older TabletControl service or development server is still running, stop it before starting the new service.

---

## View errors

Use:

```bash
journalctl --user -u tabletcontrol.service -n 50 --no-pager
```

or follow logs live:

```bash
journalctl --user -u tabletcontrol.service -f
```

---

# Updating

For now, update by pulling the latest source and running the installer again:

```bash
git pull
./install.sh
```

The installer replaces the installed application files while preserving:

- the existing Python virtual environment where possible
- the existing TabletControl configuration
- the user's `~/tabletCommands` directory

---

# Releases

Ready-to-install Android APKs are published through GitHub Releases:

https://github.com/chabymanow/TabletControl/releases

The repository itself contains the complete source code for both the Android app and Linux PC Agent.

---

# Planned improvements

Planned or possible future improvements include:

- secure Android-to-PC pairing
- authentication tokens
- QR-code pairing
- automatic PC discovery
- multiple PC support
- command groups
- custom command icons
- richer command metadata
- improved diagnostics
- installer updates
- clean uninstaller
- automatic release builds
- Wake-on-LAN support

---

# Contributing

Issues, suggestions and pull requests are welcome.

When reporting a problem, please include:

- Linux distribution
- Android version
- TabletControl version
- relevant log output
- steps required to reproduce the problem

---

# License

See the `LICENSE` file in this repository.
