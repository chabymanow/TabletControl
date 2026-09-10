# TabletControl

TabletControl turns an Android tablet into a companion dashboard and remote control for a Linux PC.

It has two parts:

- **Android app** — connects to a Linux PC over the local network, displays the dashboard, and sends command requests.
- **Linux PC Agent** — serves the dashboard, reports system information, manages pairing, discovers custom commands, and runs them.

The Android and Linux source code is included in this repository. Signed Android APKs are distributed through GitHub Releases.

---

## Features

TabletControl currently provides:

- CPU usage
- memory usage
- CPU temperature when supported by the Linux hardware/sensors
- current download and upload speed
- system uptime
- useful mounted storage volumes
- automatic filtering of Snap loop devices, SquashFS images, swap, and boot/EFI mounts
- one summary card for a completely unmounted physical disk instead of every unmounted partition
- remote command buttons
- automatic discovery of executable command files
- Android-to-PC pairing with a temporary six-digit code
- per-device authentication tokens
- paired-device management from the local PC
- two-sided Android disconnect/unpair
- automatic startup through a systemd user service
- graphical-session environment integration for commands that launch desktop applications
- automatic LAN IP detection
- automatic LAN-only UFW rule setup when UFW is active
- a terminal-based Linux updater through `update.sh`

System statistics are refreshed every two seconds.

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
           │ HTTP + pairing token
           │ TCP port 8765
           │
           ▼
┌──────────────────────┐
│      Linux PC        │
│                      │
│  TabletControl Agent │
├──────────────────────┤
│ System statistics    │
│ Storage information  │
│ Pairing/authentication│
│ Command discovery    │
│ Command execution    │
└──────────────────────┘
```

The default PC Agent address is:

```text
0.0.0.0:8765
```

A typical Android connection address looks like:

```text
http://192.168.1.100:8765
```

The PC and Android tablet must be able to communicate over the same local network.

TabletControl currently uses plain HTTP on the LAN. Authentication prevents an unpaired client from using protected API endpoints, but HTTP traffic itself is not encrypted. Do not expose TabletControl directly to the public internet.

---

## Repository structure

```text
TabletControl/
├── install.sh
├── update.sh
├── README.md
├── .gitignore
│
├── Pc/
│   ├── index.html
│   ├── pair.html
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

# Linux installation

## 1. Clone the repository

```bash
git clone https://github.com/chabymanow/TabletControl.git
cd TabletControl
```

## 2. Run the installer

```bash
./install.sh
```

The installer is a Bash script and can be launched from Bash, Fish, Zsh, and other interactive shells. Do not source it.

Do not run:

```bash
source install.sh
```

### Python virtual-environment support

TabletControl uses a private Python virtual environment. If the installer reports that venv support is missing, install the appropriate package and run `./install.sh` again.

Debian/Ubuntu:

```bash
sudo apt install python3-venv
```

Fedora:

```bash
sudo dnf install python3
```

Arch/CachyOS:

```bash
sudo pacman -S python
```

---

## What the installer does

The installer:

- checks for Python 3
- checks for a systemd user manager
- checks Python virtual-environment support
- installs the PC Agent into:

```text
~/.local/share/tabletcontrol
```

- creates or reuses a private Python virtual environment
- installs `psutil`
- creates the command directory:

```text
~/tabletCommands
```

- creates or migrates the configuration file:

```text
~/.config/tabletcontrol/tabletcontrol.env
```

- creates the user service:

```text
~/.config/systemd/user/tabletcontrol.service
```

- installs a desktop-session helper and XDG autostart entry so graphical commands can inherit the current Wayland/X11 session environment
- enables TabletControl to start automatically with the user's systemd session
- detects the main local IPv4 address
- checks whether UFW is active
- when UFW is active, determines the local IPv4 subnet and adds a LAN-only TCP rule for the configured TabletControl port
- starts or restarts TabletControl
- verifies that the service is running
- prints the local dashboard, pairing page, Android IP, and port

TabletControl itself runs as the current user. Root privileges are not required for the application or systemd user service. If UFW is active, the installer uses `sudo` for the firewall rule and may ask for the user's password.

A typical UFW rule created by the installer looks like:

```text
8765/tcp  ALLOW IN  192.168.1.0/24
```

This is intentionally limited to the detected local subnet rather than allowing the port from everywhere.

Ubuntu UFW documentation:

https://documentation.ubuntu.com/server/how-to/security/firewalls/

---

# PC dashboard and pairing

Open the PC dashboard locally:

```text
http://127.0.0.1:8765
```

Open the local pairing page:

```text
http://127.0.0.1:8765/pair
```

The pairing page is intended for use on the PC itself. It shows the detected Android connection IP/port, can generate a temporary pairing code, lists paired devices, and can revoke devices.

The temporary pairing code:

- is six digits
- is valid for five minutes
- is invalidated after successful pairing
- allows a maximum of five failed attempts before being cleared

After successful pairing, the PC creates a unique device token. The PC stores only the SHA-256 hash of the token in:

```text
~/.config/tabletcontrol/auth.json
```

The Android app stores its token encrypted with AES/GCM using Android Keystore.

---

# Android app

You can build the Android application from source or install a signed APK from GitHub Releases.

Latest release:

https://github.com/chabymanow/TabletControl/releases/latest

All releases:

https://github.com/chabymanow/TabletControl/releases

The Android app currently requires Android 9 / API 28 or newer.

## Connect and pair

1. Make sure the Linux PC Agent is running.
2. On the PC, open `http://127.0.0.1:8765/pair`.
3. In the Android app, enter the PC's LAN IP address and port.
4. If authentication is enabled, start pairing on the PC.
5. Enter the six-digit pairing code on Android.
6. After pairing, the Android app saves the PC connection and encrypted authentication token.

Default port:

```text
8765
```

## Disconnect / unpair

The Android Settings screen can disconnect from the current PC.

A normal disconnect is two-sided:

```text
Android tablet
    ↓
POST /api/pair/unpair
    ↓
PC removes that tablet from its paired-device list
    ↓
Android clears its saved token and PC address
    ↓
Connection screen
```

If the PC cannot be reached, Android offers a **Disconnect locally** option. In that case the Android app clears its local connection, but the PC may still list the old tablet until it is removed from the PC pairing page.

---

# Remote commands

TabletControl automatically discovers executable regular files inside:

```text
~/tabletCommands
```

Each executable file becomes a button on the dashboard.

For example, create:

```text
~/tabletCommands/startWork.sh
```

with:

```bash
#!/usr/bin/env bash

firefox &
```

Make it executable:

```bash
chmod +x ~/tabletCommands/startWork.sh
```

Reload the dashboard. The command will appear as a readable button label.

Examples:

```text
startWork.sh       → Start Work
startDevelopment.sh → Start Development
liveServer.sh      → Live Server
```

Only executable regular files are displayed. TabletControl invokes the exact discovered filename rather than evaluating arbitrary shell text from the API request.

---

# Graphical commands

Commands that open desktop applications need the graphical session environment, especially on Wayland.

The installer creates:

```text
~/.local/share/tabletcontrol/import-session-environment.sh
```

and an XDG autostart entry that imports available variables such as:

```text
DISPLAY
WAYLAND_DISPLAY
DBUS_SESSION_BUS_ADDRESS
XDG_RUNTIME_DIR
XAUTHORITY
XDG_SESSION_TYPE
XDG_CURRENT_DESKTOP
```

It then refreshes the TabletControl user service so command scripts can start graphical applications in the logged-in desktop session.

XDG Autostart specification:

https://specifications.freedesktop.org/autostart/latest/

---

# Configuration

TabletControl stores PC Agent configuration in:

```text
~/.config/tabletcontrol/tabletcontrol.env
```

Default settings are equivalent to:

```text
TABLETCONTROL_HOST=0.0.0.0
TABLETCONTROL_PORT=8765
TABLETCONTROL_COMMANDS_DIR=/home/USER/tabletCommands
TABLETCONTROL_CONFIG_DIR=/home/USER/.config/tabletcontrol
TABLETCONTROL_REQUIRE_AUTH=1
TABLETCONTROL_LOG_REQUESTS=0
```

After changing the configuration manually, restart the service:

```bash
systemctl --user restart tabletcontrol.service
```

The installer preserves existing configuration values during upgrades and adds missing settings from newer versions.

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

Follow logs:

```bash
journalctl --user -u tabletcontrol.service -f
```

Systemd service documentation:

https://www.freedesktop.org/software/systemd/man/latest/systemd.service.html

---

# Updating the Linux PC Agent

Linux updates are intentionally performed from the terminal rather than from the web dashboard.

From the TabletControl Git repository run:

```bash
./update.sh
```

The updater:

- verifies that it is running from a Git clone
- verifies that the `origin` remote exists
- refuses to continue when local repository changes are present
- fetches the current branch from GitHub
- refuses diverged history rather than overwriting local work
- applies only a fast-forward update
- shows the commits that were downloaded
- runs `install.sh` to refresh the installed PC Agent and restart the service

If there are local changes, commit, stash, or remove them first.

Because `install.sh` also checks UFW, an update may ask for the sudo password on systems where UFW is active.

Manual equivalent:

```bash
git pull --ff-only origin main
./install.sh
```

Git documentation:

https://git-scm.com/docs/git-pull

---

# Storage monitoring

TabletControl uses `lsblk` for block-device discovery and `psutil.disk_usage()` for filesystem usage.

The dashboard focuses on user-relevant storage. It ignores:

- `/dev/loop*` devices
- SquashFS package images such as Snap mounts
- swap
- `/boot`
- `/boot/efi`
- `/efi`

Mounted user-visible filesystems are displayed normally. If a complete physical disk has no visible mounted filesystem, TabletControl displays the physical disk once rather than showing every unmounted partition such as EFI, recovery, or Windows partitions.

`lsblk` documentation:

https://man7.org/linux/man-pages/man8/lsblk.8.html

`psutil` documentation:

https://psutil.readthedocs.io/

---

# PC Agent API

The main endpoints are listed below.

## Tablet-facing pairing endpoints

```text
GET  /api/pair/status
POST /api/pair
POST /api/pair/unpair
```

`GET /api/pair/status` allows the Android app to determine whether pairing is required and whether a pairing window is active.

`POST /api/pair` exchanges a valid temporary code for a device token.

`POST /api/pair/unpair` requires the tablet's authentication token and removes that specific paired device.

## Local PC pairing-management endpoints

```text
GET  /api/pair/info
POST /api/pair/start
GET  /api/pair/devices
POST /api/pair/remove
```

These management actions are restricted to safe localhost browser requests.

## Protected dashboard endpoints

```text
GET  /api/stats
GET  /api/commands
POST /api/run
```

LAN clients must authenticate when `TABLETCONTROL_REQUIRE_AUTH=1`. Safe localhost browser requests are trusted so the PC dashboard and pairing management can be used locally without a tablet token.

There is deliberately **no web API for installing Linux updates**. Use `./update.sh` from the terminal.

---

# Security

TabletControl is designed for a trusted local network.

By default:

- the PC Agent listens on `0.0.0.0:8765`
- LAN authentication is enabled
- pairing must be initiated locally on the PC
- paired token hashes are stored with the PC configuration
- Android keeps its raw token encrypted using Android Keystore
- UFW, when active, is configured for the detected LAN subnet rather than the public internet

Important limitations:

- TabletControl currently uses plain HTTP, not HTTPS
- traffic can therefore be observed by an attacker who already has suitable access to the local network
- the command directory contains executable code and should contain only scripts you trust

Do not:

- expose TCP port `8765` directly to the public internet
- configure router port forwarding for TabletControl
- place untrusted executable files in `~/tabletCommands`

Android Keystore documentation:

https://developer.android.com/privacy-and-security/keystore

---

# Troubleshooting

## Android cannot connect to the PC

First check the service:

```bash
systemctl --user status tabletcontrol.service
```

Check that TabletControl is listening on the LAN interface:

```bash
ss -ltnp | grep 8765
```

Normally you should see a listener on:

```text
0.0.0.0:8765
```

Check the configured host and port:

```bash
cat ~/.config/tabletcontrol/tabletcontrol.env
```

Find the PC LAN address:

```bash
hostname -I
```

If UFW is enabled, inspect its rules:

```bash
sudo ufw status numbered
```

For a `192.168.1.x` network, a suitable LAN-only rule looks like:

```text
8765/tcp  ALLOW IN  192.168.1.0/24
```

Running `./install.sh` again will attempt to detect an active UFW installation and configure the current local subnet automatically.

## Local dashboard works but Android does not

If `http://127.0.0.1:8765` works on the PC but Android cannot connect, the most likely checks are:

- correct PC LAN IP
- correct TabletControl port
- PC and tablet are on networks that can communicate
- UFW or another firewall permits the TabletControl port from the LAN
- the service is listening on `0.0.0.0`, not only `127.0.0.1`

## No command buttons appear

Check the command directory:

```bash
ls -la ~/tabletCommands
```

Commands must have executable permission:

```bash
chmod +x ~/tabletCommands/startWork.sh
```

## Graphical command works in a terminal but not from TabletControl

Refresh the desktop session variables and restart the service:

```bash
systemctl --user import-environment DISPLAY WAYLAND_DISPLAY DBUS_SESSION_BUS_ADDRESS XDG_RUNTIME_DIR
systemctl --user restart tabletcontrol.service
```

The installer also installs an autostart helper to perform this integration at desktop login.

## Port 8765 is already in use

```bash
ss -ltnp | grep 8765
```

Stop the conflicting process or old development server before restarting TabletControl.

## View recent errors

```bash
journalctl --user -u tabletcontrol.service -n 50 --no-pager
```

---

# Android development and signed releases

The Android client is written with:

- Kotlin
- Jetpack Compose
- Gradle Kotlin DSL

Package name:

```text
com.chaby.tabletcontrol
```

Minimum SDK:

```text
28
```

Release signing values are read from Gradle properties rather than being committed into the repository.

Typical release build:

```bash
cd Android
./gradlew assembleRelease
```

Generated APK:

```text
Android/app/build/outputs/apk/release/app-release.apk
```

Do not commit APK files or signing keystores to the repository. Publish signed APKs as GitHub Release assets instead.

Android app signing documentation:

https://developer.android.com/studio/publish/app-signing

GitHub Releases documentation:

https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases

---

# PC Agent development

The PC Agent is written in Python and uses the standard-library `ThreadingHTTPServer` together with `psutil`.

Main modules:

```text
config.py    Configuration
stats.py     CPU, memory, temperature, storage, network and uptime
commands.py  Command discovery and execution
auth.py      Pairing and authentication
api.py       HTTP API and static dashboard serving
main.py      PC Agent entry point
```

To run the PC Agent manually from the `Pc` directory:

```bash
python -m tabletcontrol.main
```

Python HTTP server documentation:

https://docs.python.org/3/library/http.server.html

---

# Contributing

Issues, suggestions, and pull requests are welcome.

When reporting a problem, useful information includes:

- Linux distribution
- desktop environment / Wayland or X11
- Android version
- TabletControl version or Git commit
- relevant service log output
- steps required to reproduce the issue
