#!/usr/bin/env bash

set -Eeuo pipefail

#
# TabletControl installer
#
# Installs the Linux PC Agent for the current user.
# No root privileges are required.
#

APP_NAME="TabletControl"
SERVICE_NAME="tabletcontrol.service"

SCRIPT_DIR="$(
    cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1
    pwd -P
)"

SOURCE_DIR="${SCRIPT_DIR}/PC"

INSTALL_DIR="${HOME}/.local/share/tabletcontrol"
VENV_DIR="${INSTALL_DIR}/.venv"

CONFIG_DIR="${HOME}/.config/tabletcontrol"
ENV_FILE="${CONFIG_DIR}/tabletcontrol.env"

SYSTEMD_DIR="${HOME}/.config/systemd/user"
SERVICE_FILE="${SYSTEMD_DIR}/${SERVICE_NAME}"

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
        fail "PC source directory not found: ${SOURCE_DIR}"

    [ -d "${SOURCE_DIR}/tabletcontrol" ] ||
        fail "Python package not found: ${SOURCE_DIR}/tabletcontrol"

    [ -f "${SOURCE_DIR}/tabletcontrol/main.py" ] ||
        fail "Missing: ${SOURCE_DIR}/tabletcontrol/main.py"

    [ -f "${SOURCE_DIR}/index.html" ] ||
        fail "Missing: ${SOURCE_DIR}/index.html"

    [ -f "${SOURCE_DIR}/style.css" ] ||
        fail "Missing: ${SOURCE_DIR}/style.css"
}


require_commands()
{
    command_exists python3 ||
        fail "Python 3 is required but was not found."

    command_exists systemctl ||
        fail "systemctl was not found. TabletControl currently requires a systemd-based Linux system."

    if ! systemctl --user show-environment >/dev/null 2>&1
    then
        fail "The systemd user manager is not available for this user."
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

    #
    # Preserve the virtual environment across upgrades, but replace
    # the application source and web files.
    #
    rm -rf "${INSTALL_DIR}/tabletcontrol"

    cp -R \
        "${SOURCE_DIR}/tabletcontrol" \
        "${INSTALL_DIR}/tabletcontrol"

    install -m 0644 \
        "${SOURCE_DIR}/index.html" \
        "${INSTALL_DIR}/index.html"

    install -m 0644 \
        "${SOURCE_DIR}/style.css" \
        "${INSTALL_DIR}/style.css"

    success "PC Agent files installed"
}


create_virtual_environment()
{
    if [ ! -x "${VENV_DIR}/bin/python" ]
    then
        info "Creating Python virtual environment..."

        rm -rf "${VENV_DIR}"

        python3 -m venv "${VENV_DIR}"

        success "Python virtual environment created"
    else
        success "Existing Python virtual environment found"
    fi
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


create_default_config()
{
    mkdir -p "${CONFIG_DIR}"

    if [ ! -f "${ENV_FILE}" ]
    then
        cat > "${ENV_FILE}" <<EOF
# TabletControl PC Agent configuration
#
# This file is loaded by the systemd user service.
# Restart the service after changing values:
#
#   systemctl --user restart tabletcontrol.service

TABLETCONTROL_HOST=${DEFAULT_HOST}
TABLETCONTROL_PORT=${DEFAULT_PORT}
TABLETCONTROL_COMMANDS_DIR=${COMMANDS_DIR}

# Leave empty until Android pairing/authentication is enabled.
TABLETCONTROL_AUTH_TOKEN=
EOF

        chmod 0600 "${ENV_FILE}"

        success "Configuration created: ${ENV_FILE}"
    else
        success "Existing configuration preserved: ${ENV_FILE}"
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

    systemctl --user enable \
        "${SERVICE_NAME}" \
        >/dev/null

    systemctl --user restart \
        "${SERVICE_NAME}"

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
            -n 20 \
            --no-pager \
            >&2 || true

        exit 1
    fi
}


get_configured_port()
{
    local port

    port="$(
        sed -n \
            's/^TABLETCONTROL_PORT=//p' \
            "${ENV_FILE}" \
            2>/dev/null |
        tail -n 1
    )"

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
            "${ip_binary}" \
                -4 route get 1.1.1.1 \
                2>/dev/null |
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
    fi

    if command_exists hostname
    then
        address="$(
            hostname -I 2>/dev/null |
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


show_result()
{
    local local_ip
    local port

    port="$(get_configured_port)"
    local_ip="$(get_primary_ipv4 || true)"

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

    if [ -n "${local_ip}" ]
    then
        printf 'PC address:\n'
        printf '  http://%s:%s\n' "${local_ip}" "${port}"
        printf '\n'

        printf 'Android app:\n'
        printf '  Enter: %s\n' "${local_ip}"
        printf '\n'
    else
        warn "The local IPv4 address could not be determined automatically."
        printf '\n'
        printf 'The TabletControl service is running on port %s.\n' "${port}"
        printf '\n'
    fi

    printf 'Useful commands:\n'
    printf '  systemctl --user status tabletcontrol.service\n'
    printf '  systemctl --user restart tabletcontrol.service\n'
    printf '  journalctl --user -u tabletcontrol.service -f\n'
    printf '\n'

    printf 'Security:\n'
    printf '  TabletControl currently has authentication disabled by default.\n'
    printf '  Use it only on a trusted local network and do not expose port %s\n' "${port}"
    printf '  directly to the public internet.\n'
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
    create_default_config
    create_systemd_service
    enable_service
    show_result
}


main "$@"
