#!/usr/bin/env bash

set -Eeuo pipefail

#
# TabletControl installer
#
# Installs the Linux PC Agent for the current user.
# Root privileges are not required for the app itself. If UFW is active,
# sudo is used once to add a LAN-only firewall rule for TabletControl.
#

APP_NAME="TabletControl"
SERVICE_NAME="tabletcontrol.service"

SCRIPT_DIR="$(
    cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1
    pwd -P
)"

if [ -d "${SCRIPT_DIR}/Pc" ]
then
    SOURCE_DIR="${SCRIPT_DIR}/Pc"
elif [ -d "${SCRIPT_DIR}/PC" ]
then
    SOURCE_DIR="${SCRIPT_DIR}/PC"
else
    SOURCE_DIR="${SCRIPT_DIR}/Pc"
fi

INSTALL_DIR="${HOME}/.local/share/tabletcontrol"
VENV_DIR="${INSTALL_DIR}/.venv"
SESSION_HELPER="${INSTALL_DIR}/import-session-environment.sh"
UPDATE_HELPER="${INSTALL_DIR}/run-update.sh"

CONFIG_ROOT="${HOME}/.config"
CONFIG_DIR="${CONFIG_ROOT}/tabletcontrol"
ENV_FILE="${CONFIG_DIR}/tabletcontrol.env"

SYSTEMD_DIR="${CONFIG_ROOT}/systemd/user"
SERVICE_FILE="${SYSTEMD_DIR}/${SERVICE_NAME}"

AUTOSTART_DIR="${CONFIG_ROOT}/autostart"
AUTOSTART_FILE="${AUTOSTART_DIR}/tabletcontrol-session.desktop"

COMMANDS_DIR="${HOME}/tabletCommands"

DEFAULT_HOST="0.0.0.0"
DEFAULT_PORT="8765"

print_header()
{
    printf '\n'
    printf '========================================\n'
    printf '  %s Installer\n' "${APP_NAME}"
    printf '========================================\n'
    printf '\n'
}

info()
{
    printf '• %s\n' "$*"
}

success()
{
    printf '✓ %s\n' "$*"
}

warn()
{
    printf '⚠ %s\n' "$*" >&2
}

fail()
{
    printf '✗ %s\n' "$*" >&2
    exit 1
}

command_exists()
{
    command -v "$1" >/dev/null 2>&1
}

require_source_files()
{
    [ -d "${SOURCE_DIR}" ] ||
        fail "PC source directory not found. Expected ${SCRIPT_DIR}/Pc"

    [ -d "${SOURCE_DIR}/tabletcontrol" ] ||
        fail "Python package not found: ${SOURCE_DIR}/tabletcontrol"

    [ -f "${SOURCE_DIR}/tabletcontrol/main.py" ] ||
        fail "Missing: ${SOURCE_DIR}/tabletcontrol/main.py"

    [ -f "${SOURCE_DIR}/index.html" ] ||
        fail "Missing: ${SOURCE_DIR}/index.html"

    [ -f "${SOURCE_DIR}/pair.html" ] ||
        fail "Missing: ${SOURCE_DIR}/pair.html"

    [ -f "${SOURCE_DIR}/style.css" ] ||
        fail "Missing: ${SOURCE_DIR}/style.css"

    [ -f "${SCRIPT_DIR}/update.sh" ] ||
        fail "Missing: ${SCRIPT_DIR}/update.sh"
}

require_commands()
{
    command_exists python3 ||
        fail "Python 3 is required but was not found."

    command_exists systemctl ||
        fail "systemctl was not found. TabletControl requires a systemd-based Linux system."

    command_exists systemd-run ||
        fail "systemd-run was not found. TabletControl requires systemd-run for dashboard updates."

    if ! systemctl --user show-environment >/dev/null 2>&1
    then
        fail "The systemd user manager is not available for this user. Log in normally and run the installer again."
    fi

    if ! command_exists lsblk
    then
        warn "lsblk was not found. Storage-device information may be unavailable."
    fi
}

check_venv_support()
{
    local test_dir

    test_dir="$(mktemp -d)"

    if ! python3 -m venv "${test_dir}/venv" >/dev/null 2>&1
    then
        rm -rf "${test_dir}"

        printf '\n' >&2
        warn "Python virtual-environment support is missing."
        printf '\n' >&2
        printf 'Install it using your distribution package manager, then run this installer again.\n' >&2
        printf '\n' >&2
        printf 'Examples:\n' >&2
        printf '  Debian/Ubuntu: sudo apt install python3-venv\n' >&2
        printf '  Fedora:        sudo dnf install python3\n' >&2
        printf '  Arch/CachyOS:  sudo pacman -S python\n' >&2
        printf '\n' >&2

        exit 1
    fi

    rm -rf "${test_dir}"
}

stop_existing_service()
{
    if systemctl --user cat "${SERVICE_NAME}" >/dev/null 2>&1
    then
        info "Stopping existing TabletControl service..."
        systemctl --user stop "${SERVICE_NAME}" >/dev/null 2>&1 || true
    fi
}

install_application_files()
{
    info "Installing PC Agent..."

    mkdir -p "${INSTALL_DIR}"

    rm -rf "${INSTALL_DIR}/tabletcontrol"

    cp -R \
        "${SOURCE_DIR}/tabletcontrol" \
        "${INSTALL_DIR}/tabletcontrol"

    find "${INSTALL_DIR}/tabletcontrol" \
        -type d \
        -name '__pycache__' \
        -prune \
        -exec rm -rf {} + \
        2>/dev/null || true

    install -m 0644 \
        "${SOURCE_DIR}/index.html" \
        "${INSTALL_DIR}/index.html"

    install -m 0644 \
        "${SOURCE_DIR}/pair.html" \
        "${INSTALL_DIR}/pair.html"

    install -m 0644 \
        "${SOURCE_DIR}/style.css" \
        "${INSTALL_DIR}/style.css"

    {
        printf '#!/usr/bin/env bash\n'
        printf 'set -Eeuo pipefail\n'
        printf 'exec bash %q\n' "${SCRIPT_DIR}/update.sh"
    } > "${UPDATE_HELPER}"

    chmod 0755 "${UPDATE_HELPER}"

    success "PC Agent files installed"
    success "Dashboard updater linked to: ${SCRIPT_DIR}"
}

create_virtual_environment()
{
    if [ -x "${VENV_DIR}/bin/python" ] && \
       "${VENV_DIR}/bin/python" -c 'import sys' >/dev/null 2>&1
    then
        success "Existing Python virtual environment found"
        return
    fi

    info "Creating Python virtual environment..."

    rm -rf "${VENV_DIR}"
    python3 -m venv "${VENV_DIR}"

    success "Python virtual environment created"
}

install_python_dependencies()
{
    info "Installing Python dependencies..."

    "${VENV_DIR}/bin/python" \
        -m pip \
        install \
        --disable-pip-version-check \
        --quiet \
        "psutil>=5.9"

    success "Python dependencies installed"
}

create_commands_directory()
{
    mkdir -p "${COMMANDS_DIR}"
    success "Commands directory ready: ${COMMANDS_DIR}"
}

ensure_env_setting()
{
    local name="$1"
    local value="$2"

    if ! grep -q "^${name}=" "${ENV_FILE}" 2>/dev/null
    then
        printf '%s=%s\n' "${name}" "${value}" >> "${ENV_FILE}"
    fi
}

create_or_migrate_config()
{
    mkdir -p "${CONFIG_DIR}"
    chmod 0700 "${CONFIG_DIR}"

    if [ ! -f "${ENV_FILE}" ]
    then
        cat > "${ENV_FILE}" <<EOF
# TabletControl PC Agent configuration
#
# This file is loaded by the systemd user service.
# Restart TabletControl after changing it:
#
#   systemctl --user restart tabletcontrol.service

TABLETCONTROL_HOST=${DEFAULT_HOST}
TABLETCONTROL_PORT=${DEFAULT_PORT}
TABLETCONTROL_COMMANDS_DIR=${COMMANDS_DIR}
TABLETCONTROL_CONFIG_DIR=${CONFIG_DIR}

# LAN clients must pair before using the protected API.
# Localhost remains trusted for PC-side dashboard and pairing management.
TABLETCONTROL_REQUIRE_AUTH=1

# Set to 1 only when debugging HTTP requests.
TABLETCONTROL_LOG_REQUESTS=0
EOF

        success "Configuration created: ${ENV_FILE}"
    else
        info "Migrating existing TabletControl configuration..."

        sed -i '/^TABLETCONTROL_AUTH_TOKEN=/d' "${ENV_FILE}"

        ensure_env_setting "TABLETCONTROL_HOST" "${DEFAULT_HOST}"
        ensure_env_setting "TABLETCONTROL_PORT" "${DEFAULT_PORT}"
        ensure_env_setting "TABLETCONTROL_COMMANDS_DIR" "${COMMANDS_DIR}"
        ensure_env_setting "TABLETCONTROL_CONFIG_DIR" "${CONFIG_DIR}"
        ensure_env_setting "TABLETCONTROL_REQUIRE_AUTH" "1"
        ensure_env_setting "TABLETCONTROL_LOG_REQUESTS" "0"

        success "Existing configuration preserved and updated"
    fi

    chmod 0600 "${ENV_FILE}"
}

create_session_helper()
{
    cat > "${SESSION_HELPER}" <<'EOF'
#!/usr/bin/env bash

set -u

variables=()

for name in \
    DISPLAY \
    WAYLAND_DISPLAY \
    DBUS_SESSION_BUS_ADDRESS \
    XDG_RUNTIME_DIR \
    XAUTHORITY \
    XDG_SESSION_TYPE \
    XDG_CURRENT_DESKTOP
do
    if [ -n "${!name:-}" ]
    then
        variables+=("${name}")
    fi
done

if [ "${#variables[@]}" -gt 0 ]
then
    systemctl --user import-environment "${variables[@]}" >/dev/null 2>&1 || true
fi

systemctl --user try-restart tabletcontrol.service >/dev/null 2>&1 || true
EOF

    chmod 0755 "${SESSION_HELPER}"

    mkdir -p "${AUTOSTART_DIR}"

    cat > "${AUTOSTART_FILE}" <<EOF
[Desktop Entry]
Type=Application
Name=TabletControl Session Environment
Comment=Make the graphical desktop session available to TabletControl commands
Exec="${SESSION_HELPER}"
Terminal=false
NoDisplay=true
X-GNOME-Autostart-enabled=true
EOF

    chmod 0644 "${AUTOSTART_FILE}"

    success "Graphical-session integration installed"
}

import_current_session_environment()
{
    local variables=()
    local name

    for name in \
        DISPLAY \
        WAYLAND_DISPLAY \
        DBUS_SESSION_BUS_ADDRESS \
        XDG_RUNTIME_DIR \
        XAUTHORITY \
        XDG_SESSION_TYPE \
        XDG_CURRENT_DESKTOP
    do
        if [ -n "${!name:-}" ]
        then
            variables+=("${name}")
        fi
    done

    if [ "${#variables[@]}" -gt 0 ]
    then
        systemctl --user import-environment "${variables[@]}"
        success "Current graphical-session environment imported"
    else
        warn "No graphical-session variables were detected. GUI commands will be refreshed automatically at the next desktop login."
    fi
}

create_systemd_service()
{
    mkdir -p "${SYSTEMD_DIR}"

    cat > "${SERVICE_FILE}" <<'EOF'
[Unit]
Description=TabletControl PC Agent
After=network.target

[Service]
Type=simple
WorkingDirectory=%h/.local/share/tabletcontrol
EnvironmentFile=-%h/.config/tabletcontrol/tabletcontrol.env
Environment=PYTHONUNBUFFERED=1
ExecStart=%h/.local/share/tabletcontrol/.venv/bin/python -m tabletcontrol.main
Restart=on-failure
RestartSec=2

[Install]
WantedBy=default.target
EOF

    success "systemd user service installed"
}

enable_service()
{
    info "Starting TabletControl..."

    systemctl --user daemon-reload
    systemctl --user enable "${SERVICE_NAME}" >/dev/null

    import_current_session_environment

    systemctl --user restart "${SERVICE_NAME}"

    sleep 1

    if systemctl --user is-active --quiet "${SERVICE_NAME}"
    then
        success "TabletControl service is running"
    else
        printf '\n' >&2
        warn "TabletControl did not start successfully."
        printf '\n' >&2

        systemctl --user status \
            "${SERVICE_NAME}" \
            --no-pager \
            >&2 || true

        printf '\n' >&2
        printf 'Recent log output:\n' >&2
        printf '\n' >&2

        journalctl --user \
            -u "${SERVICE_NAME}" \
            -n 30 \
            --no-pager \
            >&2 || true

        exit 1
    fi
}

get_configured_value()
{
    local name="$1"

    sed -n \
        "s/^${name}=//p" \
        "${ENV_FILE}" \
        2>/dev/null |
    tail -n 1
}

get_configured_port()
{
    local port

    port="$(get_configured_value TABLETCONTROL_PORT)"

    if [ -z "${port}" ]
    then
        port="${DEFAULT_PORT}"
    fi

    printf '%s' "${port}"
}

get_primary_ipv4()
{
    local ip_binary
    local address

    ip_binary="$(command -v ip 2>/dev/null || true)"

    if [ -n "${ip_binary}" ]
    then
        address="$(
            { "${ip_binary}" -4 route get 1.1.1.1 2>/dev/null || true; } |
            awk '
                {
                    for (i = 1; i <= NF; i++)
                    {
                        if ($i == "src" && (i + 1) <= NF)
                        {
                            print $(i + 1)
                            exit
                        }
                    }
                }
            '
        )"

        if [ -n "${address}" ]
        then
            printf '%s' "${address}"
            return 0
        fi

        address="$(
            { "${ip_binary}" -4 addr show scope global 2>/dev/null || true; } |
            awk '/inet / { split($2, parts, "/"); print parts[1]; exit }'
        )"

        if [ -n "${address}" ]
        then
            printf '%s' "${address}"
            return 0
        fi
    fi

    if command_exists hostname
    then
        address="$(
            { hostname -I 2>/dev/null || true; } |
            tr ' ' '\n' |
            awk '
                /^127\./ {
                    next
                }

                /^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$/ {
                    print
                    exit
                }
            '
        )"

        if [ -n "${address}" ]
        then
            printf '%s' "${address}"
            return 0
        fi
    fi

    return 1
}

get_primary_ipv4_subnet()
{
    local ip_binary
    local address
    local subnet

    ip_binary="$(command -v ip 2>/dev/null || true)"
    address="$(get_primary_ipv4 || true)"

    if [ -z "${ip_binary}" ] || [ -z "${address}" ]
    then
        return 1
    fi

    subnet="$(
        { "${ip_binary}" -4 route show scope link 2>/dev/null || true; } |
        awk -v address="${address}" '
            $0 ~ ("src " address "([[:space:]]|$)") &&
            $1 ~ /^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+\/[0-9]+$/ {
                print $1
                exit
            }
        '
    )"

    if [ -z "${subnet}" ]
    then
        return 1
    fi

    printf '%s' "${subnet}"
}

configure_ufw_firewall()
{
    local ufw_enabled
    local port
    local subnet

    if ! command_exists ufw
    then
        return 0
    fi

    ufw_enabled="$(
        sed -n 's/^ENABLED=//p' /etc/ufw/ufw.conf 2>/dev/null |
        tail -n 1
    )"

    if [ "${ufw_enabled,,}" != "yes" ]
    then
        return 0
    fi

    if [ "${TABLETCONTROL_NONINTERACTIVE_UPDATE:-0}" = "1" ]
    then
        info "UFW is active; keeping the existing firewall configuration during dashboard update."
        return 0
    fi

    port="$(get_configured_port)"
    subnet="$(get_primary_ipv4_subnet || true)"

    printf '\n'
    info "UFW firewall is active."

    if [ -z "${subnet}" ]
    then
        warn "Could not determine the local IPv4 subnet automatically."
        warn "TabletControl may be blocked from Android devices on the LAN."
        printf '  Allow TCP port %s from your local network in UFW, then try again.\n' "${port}" >&2
        printf '\n'
        return 0
    fi

    if ! command_exists sudo
    then
        warn "sudo was not found, so the UFW rule could not be added automatically."
        printf '  Run as root: ufw allow from %s to any port %s proto tcp\n' "${subnet}" "${port}" >&2
        printf '\n'
        return 0
    fi

    info "TabletControl needs LAN access on TCP port ${port}."
    info "Adding a UFW rule for local network ${subnet}. sudo may ask for your password."

    if sudo ufw allow from "${subnet}" to any port "${port}" proto tcp >/dev/null
    then
        success "UFW allows TabletControl from ${subnet} on TCP port ${port}"
    else
        warn "The UFW rule could not be added automatically."
        printf '  Run manually: sudo ufw allow from %s to any port %s proto tcp\n' "${subnet}" "${port}" >&2
    fi

    printf '\n'
}

show_result()
{
    local local_ip
    local port
    local require_auth

    port="$(get_configured_port)"
    local_ip="$(get_primary_ipv4 || true)"
    require_auth="$(get_configured_value TABLETCONTROL_REQUIRE_AUTH)"

    printf '\n'
    printf '========================================\n'
    printf '  TabletControl installed successfully\n'
    printf '========================================\n'
    printf '\n'

    printf 'Service:\n'
    printf '  %s\n' "${SERVICE_NAME}"
    printf '\n'

    printf 'Commands directory:\n'
    printf '  %s\n' "${COMMANDS_DIR}"
    printf '\n'

    printf 'Configuration:\n'
    printf '  %s\n' "${ENV_FILE}"
    printf '\n'

    printf 'PC dashboard:\n'
    printf '  http://127.0.0.1:%s\n' "${port}"
    printf '\n'

    printf 'Device pairing:\n'
    printf '  http://127.0.0.1:%s/pair\n' "${port}"
    printf '\n'

    if [ -n "${local_ip}" ]
    then
        printf 'Android connection:\n'
        printf '  IP:   %s\n' "${local_ip}"
        printf '  Port: %s\n' "${port}"
        printf '  URL:  http://%s:%s\n' "${local_ip}" "${port}"
        printf '\n'
    else
        warn "The local IPv4 address could not be determined automatically."
        printf '\n'
    fi

    if [ "${require_auth}" = "1" ] || [ "${require_auth,,}" = "true" ]
    then
        printf 'Security:\n'
        printf '  Pairing/authentication is enabled for LAN clients.\n'
        printf '  Open the local pairing page on this PC to pair Android devices.\n'
        printf '\n'
    else
        printf 'Security:\n'
        printf '  WARNING: LAN authentication is disabled in the configuration.\n'
        printf '\n'
    fi

    printf 'Useful commands:\n'
    printf '  systemctl --user status tabletcontrol.service\n'
    printf '  systemctl --user restart tabletcontrol.service\n'
    printf '  journalctl --user -u tabletcontrol.service -f\n'
    printf '  journalctl --user -u tabletcontrol-update.service -f\n'
    printf '\n'

    printf 'Note:\n'
    printf '  TabletControl uses local HTTP. Do not expose port %s directly\n' "${port}"
    printf '  to the public internet.\n'
    printf '\n'
}

main()
{
    print_header

    require_source_files
    require_commands
    check_venv_support

    stop_existing_service
    install_application_files
    create_virtual_environment
    install_python_dependencies
    create_commands_directory
    create_or_migrate_config
    create_session_helper
    create_systemd_service
    configure_ufw_firewall
    enable_service
    show_result
}

main "$@"
