#!/usr/bin/env bash

set -Eeuo pipefail

APP_NAME="TabletControl"
REMOTE_NAME="origin"

SCRIPT_DIR="$(
    cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1
    pwd -P
)"

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

print_header()
{
    printf '\n'
    printf '========================================\n'
    printf '  %s Updater\n' "${APP_NAME}"
    printf '========================================\n'
    printf '\n'
}

require_repository()
{
    command_exists git ||
        fail "Git is required but was not found."

    [ -d "${SCRIPT_DIR}/.git" ] ||
        fail "This updater must be run from a Git clone of TabletControl."

    [ -f "${SCRIPT_DIR}/install.sh" ] ||
        fail "install.sh was not found in ${SCRIPT_DIR}."

    if ! git -C "${SCRIPT_DIR}" remote get-url "${REMOTE_NAME}" >/dev/null 2>&1
    then
        fail "Git remote '${REMOTE_NAME}' was not found."
    fi
}

get_current_branch()
{
    git -C "${SCRIPT_DIR}" symbolic-ref --quiet --short HEAD 2>/dev/null || true
}

require_clean_worktree()
{
    local changes

    changes="$(git -C "${SCRIPT_DIR}" status --porcelain --untracked-files=normal)"

    if [ -n "${changes}" ]
    then
        printf '\n' >&2
        warn "Local repository changes were found."
        printf '%s\n' "${changes}" >&2
        printf '\n' >&2
        printf 'Commit, stash, or remove these changes before updating.\n' >&2
        printf 'The updater will not overwrite local work.\n' >&2
        printf '\n' >&2
        exit 1
    fi
}

update_repository()
{
    local branch="$1"
    local old_commit
    local new_commit

    old_commit="$(git -C "${SCRIPT_DIR}" rev-parse HEAD)"

    info "Checking GitHub for updates..."

    if ! git -C "${SCRIPT_DIR}" fetch --prune "${REMOTE_NAME}" "${branch}"
    then
        fail "Unable to fetch updates from GitHub. Check your internet connection and Git remote."
    fi

    new_commit="$(git -C "${SCRIPT_DIR}" rev-parse FETCH_HEAD)"

    if [ "${old_commit}" = "${new_commit}" ]
    then
        success "Repository is already up to date"
        return 0
    fi

    if ! git -C "${SCRIPT_DIR}" merge-base --is-ancestor "${old_commit}" "${new_commit}"
    then
        fail "Local and remote history have diverged. Update manually with Git before running this updater."
    fi

    info "Downloading TabletControl update..."

    if ! git -C "${SCRIPT_DIR}" merge --ff-only "${new_commit}"
    then
        fail "Unable to apply the update safely."
    fi

    success "Source updated"

    printf '\n'
    git -C "${SCRIPT_DIR}" log \
        --oneline \
        --no-decorate \
        "${old_commit}..${new_commit}" || true
    printf '\n'
}

run_installer()
{
    info "Updating the installed PC Agent..."
    printf '\n'

    if ! TABLETCONTROL_NONINTERACTIVE_UPDATE=1 bash "${SCRIPT_DIR}/install.sh"
    then
        fail "The source was updated, but install.sh did not complete successfully."
    fi
}

main()
{
    local branch

    print_header
    require_repository
    require_clean_worktree

    branch="$(get_current_branch)"

    if [ -z "${branch}" ]
    then
        fail "The repository is in detached HEAD state. Check out the main branch before updating."
    fi

    info "Repository: ${SCRIPT_DIR}"
    info "Branch: ${branch}"
    printf '\n'

    update_repository "${branch}"
    run_installer

    printf '\n'
    success "TabletControl update completed"
    printf '\n'
}

main "$@"
