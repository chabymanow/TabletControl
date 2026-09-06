# TabletControl

TabletControl turns an Android tablet into a companion dashboard and remote control for a Linux PC.

The project consists of two parts:

- **PC Agent** — a lightweight Python web server that collects system information and runs configured commands.
- **Android App** — an Android application that connects to the PC Agent over the local network and displays the TabletControl dashboard.

The complete source code for both components is contained in this repository.

---

## Features

### System monitoring

TabletControl displays live information from the connected Linux PC:

- CPU usage
- Memory usage
- CPU temperature
- Download speed
- Upload speed
- System uptime
- Mounted storage
- Unmounted storage devices
- Storage usage

System statistics are refreshed automatically every two seconds.

### Remote commands

Executable scripts placed in:

```text
~/tabletCommands
```

are automatically discovered by the PC Agent and displayed as buttons on the dashboard.

Pressing a command button on the tablet launches the corresponding script on the Linux PC.

This can be used for tasks such as:

- Launching applications
- Starting a work environment
- Opening websites
- Starting games
- Running maintenance scripts
- Starting custom workflows
- Controlling other software

---

# Architecture

```text
┌──────────────────────┐
│    Android Tablet    │
│                      │
│    TabletControl     │
└──────────┬───────────┘
           │
           │ HTTP / Local Network
           │ Port 8765
           │
           ▼
┌──────────────────────┐
│      Linux PC        │
│                      │
│    Python Agent      │
│      server.py       │
├──────────────────────┤
│ System statistics    │
│ Storage information  │
│ Command discovery    │
│ Command execution    │
└──────────────────────┘
```

The PC Agent listens on:

```text
0.0.0.0:8765
```

The Android device connects using the PC's local network address, for example:

```text
http://192.168.1.100:8765
```

---

# Repository Structure

```text
TabletControl/
│
├── Android/
│   ├── app/
│   ├── gradle/
│   ├── build.gradle.kts
│   ├── settings.gradle.kts
│   └── ...
│
├── PC/
│   ├── server.py
│   ├── index.html
│   └── style.css
│
├── README.md
├── LICENSE
└── .gitignore
```

---

# Requirements

## Linux PC

The PC Agent currently targets Linux.

Required software:

- Python 3
- `psutil`
- `lsblk`

The current implementation expects `lsblk` at:

```text
/usr/bin/lsblk
```

## Android

The Android client is written in Kotlin using Jetpack Compose.

Current minimum Android version:

```text
Android 9.0
API 28
```

The Android application requires network access to communicate with the PC.

---

# Installing the PC Agent

Clone the repository:

```bash
git clone https://github.com/chabymanow/TabletControl.git
```

Enter the PC directory:

```bash
cd TabletControl/PC
```

Create a Python virtual environment:

```bash
python3 -m venv .venv
```

Activate it:

```bash
source .venv/bin/activate
```

Install the required Python dependency:

```bash
python -m pip install psutil
```

Start TabletControl:

```bash
python server.py
```

The server should report:

```text
Tablet Dashboard
----------------
Listening on port 8765
Commands: /home/USERNAME/tabletCommands
```

---

# Finding the PC IP Address

TabletControl requires the local IP address of the Linux PC.

One way to find the address is:

```bash
/usr/bin/ip route get 1.1.1.1
```

Look for:

```text
src 192.168.x.x
```

For example:

```text
src 192.168.1.100
```

The TabletControl address would therefore be:

```text
http://192.168.1.100:8765
```

You can test the server from another device by opening this address in a browser.

The PC and tablet must be able to communicate over the network.

---

# Android Installation

Normal users can install TabletControl using the signed APK available from the GitHub **Releases** section.

Open:

```text
https://github.com/chabymanow/TabletControl/releases
```

Download the latest:

```text
TabletControl.apk
```

Install the APK on the Android tablet.

Android may ask for permission to install applications from the browser or file manager being used.

---

# Connecting the Android App

Before connecting:

1. Start the TabletControl PC Agent.
2. Make sure the tablet and PC can communicate over the local network.
3. Find the PC's local IP address.
4. Configure the Android app with the PC address.

Example:

```text
192.168.1.100
```

The PC Agent uses port:

```text
8765
```

The resulting server address is:

```text
http://192.168.1.100:8765
```

The Android application stores its local TabletControl settings on the device.

---

# Creating Remote Commands

TabletControl discovers commands from:

```text
~/tabletCommands
```

Create the directory if it does not already exist:

```bash
mkdir -p ~/tabletCommands
```

## Example command

Create:

```text
~/tabletCommands/open_browser.sh
```

with:

```bash
#!/usr/bin/env bash

firefox &
```

Make it executable:

```bash
chmod +x ~/tabletCommands/open_browser.sh
```

Reload the TabletControl dashboard.

A button will appear as:

```text
Open Browser
```

Pressing the button launches the script on the PC.

---

# Command Naming

TabletControl automatically converts command filenames into readable button names.

For example:

```text
start_work.sh
```

becomes:

```text
Start Work
```

and:

```text
gaming-mode.sh
```

becomes:

```text
Gaming Mode
```

The file extension is not displayed.

Only regular files with executable permission are shown.

---

# Example Work Command

A command can launch several programs at once.

For example:

```bash
#!/usr/bin/env bash

google-chrome-stable &
whatsapp-for-linux &
outlook-for-linux &
```

Save the script as:

```text
~/tabletCommands/start_work.sh
```

Then:

```bash
chmod +x ~/tabletCommands/start_work.sh
```

TabletControl will automatically display:

```text
Start Work
```

---

# Dashboard API

The PC Agent exposes a small HTTP API used by the dashboard.

## GET `/api/stats`

Returns current system information.

Example structure:

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

## GET `/api/commands`

Returns executable commands currently available in:

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

## POST `/api/run`

Runs one of the available commands.

Request format:

```text
Content-Type: application/x-www-form-urlencoded
```

Body:

```text
command=start_work.sh
```

Example success response:

```json
{
    "success": true,
    "message": "Command started"
}
```

---

# Storage Detection

TabletControl uses Linux `lsblk` to discover storage devices.

The dashboard can display:

- Device name
- Mount point
- Filesystem
- Used space
- Total space
- Usage percentage
- Unmounted devices

The root filesystem is displayed first, followed by other mounted devices and then unmounted devices.

---

# CPU Temperature

TabletControl attempts to obtain CPU temperature information using `psutil`.

The current PC Agent checks common Linux sensor groups including:

```text
k10temp
coretemp
zenpower
cpu_thermal
```

If no compatible temperature sensor is available, the dashboard displays:

```text
N/A
```

---

# Network Traffic

TabletControl calculates current download and upload speed using network byte counters.

The values displayed by the dashboard represent approximately:

```text
B/s
KB/s
MB/s
GB/s
```

depending on the current transfer rate.

---

# Development

## Android

The Android application uses:

- Kotlin
- Jetpack Compose
- Android Studio
- Gradle Kotlin DSL

Package:

```text
com.chaby.tabletcontrol
```

Build the debug version from the Android directory:

```bash
./gradlew assembleDebug
```

For public distribution, generate a signed release APK using Android Studio:

```text
Build
→ Generate Signed App Bundle or APK
→ APK
```

Keep the signing keystore private.

Do not commit the release keystore or its passwords to Git.

---

## PC

The PC Agent uses:

- Python
- `http.server`
- `psutil`
- `lsblk`
- HTML
- CSS
- JavaScript

Run it during development with:

```bash
python server.py
```

---

# Security

## Important

The current TabletControl PC Agent is intended for use on a **trusted local network**.

The server listens on all network interfaces:

```text
0.0.0.0:8765
```

The current implementation does not include authentication.

The `/api/run` endpoint can execute any executable file that has been deliberately placed in:

```text
~/tabletCommands
```

Therefore:

**Do not expose port 8765 directly to the public internet.**

Do not configure router port forwarding for TabletControl.

Only place scripts in `~/tabletCommands` that you trust.

Authentication/pairing should be added before TabletControl is used across untrusted networks.

---

# Troubleshooting

## Android shows "Web page not available"

Check that the PC Agent is running:

```bash
python server.py
```

Then test the address from the tablet's browser:

```text
http://PC-IP:8765
```

If the browser cannot connect, check:

- The PC IP address
- Wi-Fi/network connectivity
- Linux firewall settings
- Whether port 8765 is accessible

---

## Dashboard works in the browser but not in the Android app

The Android application connects to the local server using HTTP.

The application therefore requires:

```xml
<uses-permission android:name="android.permission.INTERNET" />
```

and currently allows local cleartext HTTP traffic.

---

## No command buttons appear

Check:

```bash
ls -la ~/tabletCommands
```

Commands must be executable.

For example:

```bash
chmod +x ~/tabletCommands/my_command.sh
```

Then reload the dashboard.

---

## CPU temperature displays N/A

The Linux system may expose temperature information using a sensor name that TabletControl does not currently recognise.

This does not affect the rest of the dashboard.

---

## The PC IP address changed

Most home networks assign addresses using DHCP, so the PC address may occasionally change.

Find the current address again and update the TabletControl Android connection settings.

---

# Releases

GitHub Releases are used for distributing ready-to-install versions of TabletControl.

A release may contain:

```text
TabletControl.apk
```

while the Git repository contains the complete Android and PC source code.

Example versioning:

```text
v0.1.0
v0.1.1
v0.2.0
v1.0.0
```

---

# Planned Improvements

Potential future improvements include:

- Secure tablet-to-PC pairing
- Authentication tokens
- Automatic PC discovery
- Multiple PC support
- Linux installer
- systemd user service
- Automatic startup
- GitHub Actions release builds
- Connection status and diagnostics
- Improved command management
- Custom command icons
- Command groups
- Wake-on-LAN support

---

# Contributing

Issues, suggestions and pull requests are welcome.

When reporting a problem, include:

- Linux distribution
- Android version
- TabletControl version
- Relevant error output
- Steps needed to reproduce the problem

---

# License

A project licence will be specified in the `LICENSE` file.
