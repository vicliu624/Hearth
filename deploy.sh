#!/usr/bin/env bash
set -Eeuo pipefail

IFS=$'\n\t'

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd -P)"
REPO_DIR="${REPO_DIR:-$SCRIPT_DIR}"

INSTALL_DIR="${INSTALL_DIR:-/opt/hearth}"
CONFIG_DIR="${CONFIG_DIR:-/etc/hearth}"
DATA_DIR="${DATA_DIR:-/var/lib/hearth}"

SERVICE_NAME="${SERVICE_NAME:-hearth}"
SERVICE_USER="${SERVICE_USER:-hearth}"
SERVICE_GROUP="${SERVICE_GROUP:-$SERVICE_USER}"
SERVICE_HOME=""

HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8480}"
TIMEZONE="${TIMEZONE:-Asia/Shanghai}"
NODE_NAME="${NODE_NAME:-$(hostname -s 2>/dev/null || hostname 2>/dev/null || echo hearth-node)}"

BACKEND="${RETICULUM_BACKEND:-auto}"
ADMIN_TOKEN="${ADMIN_TOKEN:-}"
PYTHON_BIN="${PYTHON_BIN:-}"

DEV_MODE=false
CONFIG_ONLY=false
OVERWRITE_CONFIG=false
NO_SUDO=false
SKIP_SYSTEM_DEPS=false
ENABLE_SERVICE=true
START_SERVICE=true

INSTALL_DIR_EXPLICIT=false
CONFIG_DIR_EXPLICIT=false
DATA_DIR_EXPLICIT=false
SERVICE_USER_EXPLICIT=false
SERVICE_GROUP_EXPLICIT=false

SYSTEMD_AVAILABLE=false
CONFIG_CREATED=false
CONFIG_FILE=""
VENV_DIR=""
VENV_PYTHON=""
VENV_HEARTH=""
SERVICE_FILE=""
RESOLVED_BACKEND=""
USE_SYSTEM_PYTHON_RUNTIME_DEPS=false
SUDO=()
STOPPED_RUNNING_SERVICE=false
STOPPED_LEGACY_RNSD_SERVICE=false
ADOPT_EXISTING_RETICULUM_USER=""
RETICULUM_CONFIG_DIR=""
RETICULUM_IMPORT_CONFIG=""
RETICULUM_MANAGED_COMMAND=""
INTEGRATE_LXMF=false
MASK_LEGACY_RNSD=false
INSTALL_SERVICE_ALIASES=false
CONFIG_BACKUP_FILE=""
LXMF_DROPIN_FILE="/etc/systemd/system/lxmd.service.d/hearth-reticulum.conf"
LEGACY_RNSD_BACKUP_FILE="/etc/systemd/system/rnsd.service.disabled-by-hearth"
SERVICE_ALIAS_RETICULUM_FILE="/etc/systemd/system/reticulum.service"
SERVICE_ALIAS_LXMF_FILE="/etc/systemd/system/lxmf.service"
LXMF_INTEGRATION_APPLIED=false
LEGACY_RNSD_MASKED=false
SERVICE_ALIASES_APPLIED=false

log_info() {
    printf '%b[INFO]%b %s\n' "$BLUE" "$NC" "$1"
}

log_success() {
    printf '%b[ OK ]%b %s\n' "$GREEN" "$NC" "$1"
}

log_warn() {
    printf '%b[WARN]%b %s\n' "$YELLOW" "$NC" "$1"
}

log_error() {
    printf '%b[FAIL]%b %s\n' "$RED" "$NC" "$1" >&2
}

die() {
    log_error "$1"
    exit 1
}

print_usage() {
    cat <<EOF
Hearth Linux deployment script

Usage:
  bash deploy.sh [options]

What it does:
  - installs Hearth from the current cloned repository
  - prepares a Python virtual environment
  - generates a Linux-ready hearth.toml with absolute paths
  - installs a systemd service when systemd is available

Options:
  --repo-dir PATH         Repository source to deploy. Default: script directory
  --install-dir PATH      Application install directory. Default: /opt/hearth
  --config-dir PATH       Config directory. Default: /etc/hearth
  --data-dir PATH         Persistent data directory. Default: /var/lib/hearth
  --host HOST             Web bind host. Default: 0.0.0.0
  --port PORT             Web bind port. Default: 8480
  --timezone TZ           Config timezone. Default: Asia/Shanghai
  --node-name NAME        Hearth node name. Default: current hostname
  --backend MODE          auto | mock_process | managed_rnsd. Default: auto
  --service-user USER     systemd service user. Default: hearth
  --service-group GROUP   systemd service group. Default: service user
  --reticulum-config-dir PATH
                          Managed Reticulum config directory
  --reticulum-import-config PATH
                          Import an existing Reticulum config into hearth.toml
  --reticulum-managed-command CMD
                          Explicit managed rnsd command or absolute path
  --integrate-lxmf        Wire lxmd.service to follow hearth.service
  --mask-legacy-rnsd      Mask standalone rnsd.service after cutover
  --install-service-aliases
                          Create reticulum.service and lxmf.service aliases
  --adopt-existing-reticulum USER
                          Import USER's ~/.reticulum and apply the cutover defaults
  --admin-token TOKEN     Admin token to write into the generated config
  --python PATH           Python interpreter to use. Must be Python 3.12+
  --overwrite-config      Rewrite an existing config file
  --config-only           Prepare files but do not enable or start the service
  --no-enable             Do not enable the systemd service on boot
  --no-start              Do not start the service after deployment
  --skip-system-deps      Skip apt/dnf/yum/pacman/zypper dependency installation
  --no-sudo               Never call sudo
  --dev                   Install in-place in the current repository without systemd
  -h, --help              Show this help

Examples:
  bash deploy.sh
  bash deploy.sh --backend mock_process
  bash deploy.sh --overwrite-config --admin-token my-secret-token
  bash deploy.sh --adopt-existing-reticulum vicliu
  bash deploy.sh --dev
EOF
}

on_error() {
    local exit_code=$?
    log_error "Deployment failed while running: ${BASH_COMMAND}"
    exit "$exit_code"
}

trap on_error ERR

require_no_spaces() {
    local path_value="$1"
    local label="$2"
    if [[ "$path_value" == *" "* ]]; then
        die "$label does not support spaces: $path_value"
    fi
}

require_absolute_path() {
    local path_value="$1"
    local label="$2"
    [[ "$path_value" = /* ]] || die "$label must be an absolute path in production mode: $path_value"
}

command_exists() {
    command -v "$1" >/dev/null 2>&1
}

get_user_home() {
    local user_name="$1"

    getent passwd "$user_name" | awk -F: '{print $6}' | head -n 1
}

python_path_is_usable() {
    local candidate="$1"

    if [[ "$candidate" == */* ]]; then
        [[ -x "$candidate" ]] || return 1
    else
        command_exists "$candidate" || return 1
    fi

    "$candidate" - <<'PY' >/dev/null 2>&1
import sys
raise SystemExit(0 if sys.version_info >= (3, 12) else 1)
PY
}

python_realpath() {
    local input_path="$1"

    "$PYTHON_BIN" - "$input_path" <<'PY'
from pathlib import Path
import sys

print(Path(sys.argv[1]).expanduser().resolve())
PY
}

paths_are_same() {
    local left="$1"
    local right="$2"

    "$PYTHON_BIN" - "$left" "$right" <<'PY'
from pathlib import Path
import sys

left = Path(sys.argv[1]).expanduser().resolve()
right = Path(sys.argv[2]).expanduser().resolve()
raise SystemExit(0 if left == right else 1)
PY
}

validate_managed_install_dir() {
    local resolved_install

    resolved_install="$(python_realpath "$INSTALL_DIR")"
    case "$resolved_install" in
        /|/opt|/etc|/var|/usr|/home|/root)
            die "Refusing to manage an unsafe install directory: $resolved_install"
            ;;
    esac
}

run_root() {
    if [[ ${#SUDO[@]} -gt 0 ]]; then
        "${SUDO[@]}" \
            --preserve-env=PIP_INDEX_URL,PIP_EXTRA_INDEX_URL,PIP_DEFAULT_TIMEOUT,PIP_RETRIES,PIP_TRUSTED_HOST,PIP_DISABLE_PIP_VERSION_CHECK \
            "$@"
    else
        "$@"
    fi
}

run_with_retry() {
    local attempts="$1"
    local delay_seconds="$2"
    shift 2

    local attempt=1
    while true; do
        if "$@"; then
            return 0
        fi

        if (( attempt >= attempts )); then
            return 1
        fi

        log_warn "Command failed on attempt ${attempt}/${attempts}; retrying in ${delay_seconds}s"
        sleep "$delay_seconds"
        attempt=$((attempt + 1))
    done
}

parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --repo-dir)
                [[ $# -ge 2 ]] || die "--repo-dir requires a value"
                REPO_DIR="$2"
                shift 2
                ;;
            --install-dir)
                [[ $# -ge 2 ]] || die "--install-dir requires a value"
                INSTALL_DIR="$2"
                INSTALL_DIR_EXPLICIT=true
                shift 2
                ;;
            --config-dir)
                [[ $# -ge 2 ]] || die "--config-dir requires a value"
                CONFIG_DIR="$2"
                CONFIG_DIR_EXPLICIT=true
                shift 2
                ;;
            --data-dir)
                [[ $# -ge 2 ]] || die "--data-dir requires a value"
                DATA_DIR="$2"
                DATA_DIR_EXPLICIT=true
                shift 2
                ;;
            --host)
                [[ $# -ge 2 ]] || die "--host requires a value"
                HOST="$2"
                shift 2
                ;;
            --port)
                [[ $# -ge 2 ]] || die "--port requires a value"
                PORT="$2"
                shift 2
                ;;
            --timezone)
                [[ $# -ge 2 ]] || die "--timezone requires a value"
                TIMEZONE="$2"
                shift 2
                ;;
            --node-name)
                [[ $# -ge 2 ]] || die "--node-name requires a value"
                NODE_NAME="$2"
                shift 2
                ;;
            --backend)
                [[ $# -ge 2 ]] || die "--backend requires a value"
                BACKEND="$2"
                shift 2
                ;;
            --service-user)
                [[ $# -ge 2 ]] || die "--service-user requires a value"
                SERVICE_USER="$2"
                SERVICE_USER_EXPLICIT=true
                shift 2
                ;;
            --service-group)
                [[ $# -ge 2 ]] || die "--service-group requires a value"
                SERVICE_GROUP="$2"
                SERVICE_GROUP_EXPLICIT=true
                shift 2
                ;;
            --reticulum-config-dir)
                [[ $# -ge 2 ]] || die "--reticulum-config-dir requires a value"
                RETICULUM_CONFIG_DIR="$2"
                shift 2
                ;;
            --reticulum-import-config)
                [[ $# -ge 2 ]] || die "--reticulum-import-config requires a value"
                RETICULUM_IMPORT_CONFIG="$2"
                shift 2
                ;;
            --reticulum-managed-command)
                [[ $# -ge 2 ]] || die "--reticulum-managed-command requires a value"
                RETICULUM_MANAGED_COMMAND="$2"
                shift 2
                ;;
            --integrate-lxmf)
                INTEGRATE_LXMF=true
                shift
                ;;
            --mask-legacy-rnsd)
                MASK_LEGACY_RNSD=true
                shift
                ;;
            --install-service-aliases)
                INSTALL_SERVICE_ALIASES=true
                shift
                ;;
            --adopt-existing-reticulum)
                [[ $# -ge 2 ]] || die "--adopt-existing-reticulum requires a user name"
                ADOPT_EXISTING_RETICULUM_USER="$2"
                shift 2
                ;;
            --admin-token)
                [[ $# -ge 2 ]] || die "--admin-token requires a value"
                ADMIN_TOKEN="$2"
                shift 2
                ;;
            --python)
                [[ $# -ge 2 ]] || die "--python requires a value"
                PYTHON_BIN="$2"
                shift 2
                ;;
            --overwrite-config)
                OVERWRITE_CONFIG=true
                shift
                ;;
            --config-only)
                CONFIG_ONLY=true
                ENABLE_SERVICE=false
                START_SERVICE=false
                shift
                ;;
            --no-enable)
                ENABLE_SERVICE=false
                shift
                ;;
            --no-start)
                START_SERVICE=false
                shift
                ;;
            --skip-system-deps)
                SKIP_SYSTEM_DEPS=true
                shift
                ;;
            --no-sudo)
                NO_SUDO=true
                shift
                ;;
            --dev)
                DEV_MODE=true
                ENABLE_SERVICE=false
                START_SERVICE=false
                shift
                ;;
            -h|--help)
                print_usage
                exit 0
                ;;
            *)
                die "Unknown option: $1"
                ;;
        esac
    done
}

apply_mode_defaults() {
    if [[ "$DEV_MODE" == true ]]; then
        NO_SUDO=true
        if [[ "$INSTALL_DIR_EXPLICIT" == false ]]; then
            INSTALL_DIR="$REPO_DIR"
        fi
        if [[ "$CONFIG_DIR_EXPLICIT" == false ]]; then
            CONFIG_DIR="$REPO_DIR"
        fi
        if [[ "$DATA_DIR_EXPLICIT" == false ]]; then
            DATA_DIR="$REPO_DIR/.data"
        fi
    fi
}

apply_option_defaults() {
    local adopt_home=""

    if [[ "$SERVICE_USER_EXPLICIT" == true && "$SERVICE_GROUP_EXPLICIT" == false ]]; then
        SERVICE_GROUP="$SERVICE_USER"
    fi

    if [[ -z "$ADOPT_EXISTING_RETICULUM_USER" ]]; then
        return
    fi

    if ! id -u "$ADOPT_EXISTING_RETICULUM_USER" >/dev/null 2>&1; then
        die "Adoption target user does not exist: $ADOPT_EXISTING_RETICULUM_USER"
    fi

    if [[ "$SERVICE_USER_EXPLICIT" == true && "$SERVICE_USER" != "$ADOPT_EXISTING_RETICULUM_USER" ]]; then
        die "--service-user conflicts with --adopt-existing-reticulum"
    fi

    adopt_home="$(get_user_home "$ADOPT_EXISTING_RETICULUM_USER")"
    [[ -n "$adopt_home" ]] || die "Could not resolve home directory for $ADOPT_EXISTING_RETICULUM_USER"

    SERVICE_USER="$ADOPT_EXISTING_RETICULUM_USER"
    if [[ "$SERVICE_GROUP_EXPLICIT" == false ]]; then
        SERVICE_GROUP="$ADOPT_EXISTING_RETICULUM_USER"
    fi

    if [[ -z "$RETICULUM_CONFIG_DIR" ]]; then
        RETICULUM_CONFIG_DIR="$adopt_home/.reticulum"
    fi
    if [[ -z "$RETICULUM_IMPORT_CONFIG" ]]; then
        RETICULUM_IMPORT_CONFIG="$RETICULUM_CONFIG_DIR/config"
    fi
    if [[ -z "$RETICULUM_MANAGED_COMMAND" ]]; then
        if [[ -x "$adopt_home/.local/reticulum-venv/bin/rnsd" ]]; then
            RETICULUM_MANAGED_COMMAND="$adopt_home/.local/reticulum-venv/bin/rnsd"
        else
            RETICULUM_MANAGED_COMMAND="rnsd"
        fi
    fi

    BACKEND="managed_rnsd"
    OVERWRITE_CONFIG=true
    INTEGRATE_LXMF=true
    MASK_LEGACY_RNSD=true
    INSTALL_SERVICE_ALIASES=true
}

validate_inputs() {
    case "$BACKEND" in
        auto|mock_process|managed_rnsd)
            ;;
        *)
            die "--backend must be one of: auto, mock_process, managed_rnsd"
            ;;
    esac

    [[ "$PORT" =~ ^[0-9]+$ ]] || die "--port must be a number"
    (( PORT >= 1 && PORT <= 65535 )) || die "--port must be between 1 and 65535"

    require_no_spaces "$REPO_DIR" "Repository path"
    require_no_spaces "$INSTALL_DIR" "Install directory"
    require_no_spaces "$CONFIG_DIR" "Config directory"
    require_no_spaces "$DATA_DIR" "Data directory"
    if [[ -n "$RETICULUM_CONFIG_DIR" ]]; then
        require_no_spaces "$RETICULUM_CONFIG_DIR" "Reticulum config directory"
    fi
    if [[ -n "$RETICULUM_IMPORT_CONFIG" ]]; then
        require_no_spaces "$RETICULUM_IMPORT_CONFIG" "Reticulum import config"
    fi

    [[ -d "$REPO_DIR" ]] || die "Repository directory does not exist: $REPO_DIR"
    [[ -f "$REPO_DIR/pyproject.toml" ]] || die "Repository directory does not look like the Hearth project: $REPO_DIR"

    if [[ "$DEV_MODE" == false ]]; then
        require_absolute_path "$INSTALL_DIR" "Install directory"
        require_absolute_path "$CONFIG_DIR" "Config directory"
        require_absolute_path "$DATA_DIR" "Data directory"
        if [[ -n "$RETICULUM_CONFIG_DIR" ]]; then
            require_absolute_path "$RETICULUM_CONFIG_DIR" "Reticulum config directory"
        fi
        if [[ -n "$RETICULUM_IMPORT_CONFIG" ]]; then
            require_absolute_path "$RETICULUM_IMPORT_CONFIG" "Reticulum import config"
        fi
    fi

    if [[ -n "$RETICULUM_IMPORT_CONFIG" && ! -f "$RETICULUM_IMPORT_CONFIG" ]]; then
        die "Reticulum import config does not exist: $RETICULUM_IMPORT_CONFIG"
    fi
}

detect_systemd() {
    if command_exists systemctl && [[ -d /run/systemd/system ]]; then
        SYSTEMD_AVAILABLE=true
    fi
}

configure_privileges() {
    if [[ "$NO_SUDO" == true ]]; then
        SUDO=()
        return
    fi

    if [[ "${EUID:-$(id -u)}" -eq 0 ]]; then
        SUDO=()
        return
    fi

    command_exists sudo || die "sudo is required for production deployment. Re-run as root, use --no-sudo, or use --dev."
    SUDO=(sudo)
}

install_system_packages() {
    if [[ "$SKIP_SYSTEM_DEPS" == true ]]; then
        log_warn "Skipping system dependency installation as requested"
        return
    fi

    log_info "Installing system dependencies if the package manager supports it"

    if command_exists apt-get; then
        USE_SYSTEM_PYTHON_RUNTIME_DEPS=true
        run_root apt-get update
        run_root apt-get install -y \
            python3 python3-venv python3-pip git rsync curl ca-certificates \
            python3-fastapi python3-jinja2 python3-pydantic python3-sqlalchemy \
            python3-sqlalchemy-ext python3-greenlet python3-tomli-w python3-typer python3-uvicorn
    elif command_exists dnf; then
        run_root dnf install -y python3 python3-pip git rsync curl ca-certificates
    elif command_exists yum; then
        run_root yum install -y python3 python3-pip git rsync curl ca-certificates
    elif command_exists pacman; then
        run_root pacman -Sy --noconfirm python python-pip git rsync curl ca-certificates
    elif command_exists zypper; then
        run_root zypper --non-interactive install python3 python3-pip git rsync curl ca-certificates
    else
        log_warn "No supported package manager detected. Please ensure Python 3.12+, venv, git, and rsync or tar are installed."
    fi
}

venv_uses_system_site_packages() {
    local cfg_file="$VENV_DIR/pyvenv.cfg"

    [[ -f "$cfg_file" ]] || return 1
    grep -Eiq '^include-system-site-packages *= *true$' "$cfg_file"
}

select_python() {
    local candidates=()
    local candidate=""

    if [[ -n "$PYTHON_BIN" ]]; then
        candidates+=("$PYTHON_BIN")
    fi
    candidates+=(python3.13 python3.12 python3 python)

    for candidate in "${candidates[@]}"; do
        if python_path_is_usable "$candidate"; then
            if [[ "$candidate" == */* ]]; then
                PYTHON_BIN="$candidate"
            else
                PYTHON_BIN="$(command -v "$candidate")"
            fi
            log_success "Using Python interpreter: $PYTHON_BIN"
            return
        fi
    done

    die "Python 3.12+ is required. Install it first or pass --python /path/to/python3.12"
}

prepare_paths() {
    REPO_DIR="$(python_realpath "$REPO_DIR")"
    INSTALL_DIR="$(python_realpath "$INSTALL_DIR")"
    CONFIG_DIR="$(python_realpath "$CONFIG_DIR")"
    DATA_DIR="$(python_realpath "$DATA_DIR")"
    if [[ -n "$RETICULUM_CONFIG_DIR" ]]; then
        RETICULUM_CONFIG_DIR="$(python_realpath "$RETICULUM_CONFIG_DIR")"
    fi
    if [[ -n "$RETICULUM_IMPORT_CONFIG" ]]; then
        RETICULUM_IMPORT_CONFIG="$(python_realpath "$RETICULUM_IMPORT_CONFIG")"
    fi

    CONFIG_FILE="$CONFIG_DIR/hearth.toml"
    VENV_DIR="$INSTALL_DIR/.venv"
    VENV_PYTHON="$VENV_DIR/bin/python"
    VENV_HEARTH="$VENV_DIR/bin/hearth"
    SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
}

find_nologin_shell() {
    local candidate=""

    for candidate in /usr/sbin/nologin /sbin/nologin /bin/false; do
        if [[ -x "$candidate" ]]; then
            printf '%s\n' "$candidate"
            return
        fi
    done

    printf '/bin/false\n'
}

create_service_account() {
    local nologin_shell=""

    if [[ "$DEV_MODE" == true ]]; then
        return
    fi

    nologin_shell="$(find_nologin_shell)"

    if ! getent group "$SERVICE_GROUP" >/dev/null 2>&1; then
        log_info "Creating service group: $SERVICE_GROUP"
        run_root groupadd --system "$SERVICE_GROUP"
    fi

    if ! id -u "$SERVICE_USER" >/dev/null 2>&1; then
        log_info "Creating service user: $SERVICE_USER"
        run_root useradd --system --gid "$SERVICE_GROUP" --home-dir "$INSTALL_DIR" --shell "$nologin_shell" "$SERVICE_USER"
    fi
}

resolve_service_home() {
    if [[ "$DEV_MODE" == true ]]; then
        SERVICE_HOME="$INSTALL_DIR"
        return
    fi

    SERVICE_HOME="$(get_user_home "$SERVICE_USER")"
    if [[ -z "$SERVICE_HOME" ]]; then
        SERVICE_HOME="$INSTALL_DIR"
    fi
}

stop_running_service_if_needed() {
    if [[ "$DEV_MODE" == true || "$SYSTEMD_AVAILABLE" == false ]]; then
        return
    fi

    if [[ ! -f "$SERVICE_FILE" ]]; then
        return
    fi

    if run_root systemctl is-active --quiet "$SERVICE_NAME"; then
        log_info "Stopping running systemd service before deployment"
        run_root systemctl stop "$SERVICE_NAME"
        STOPPED_RUNNING_SERVICE=true
    fi
}

sync_source_tree() {
    validate_managed_install_dir

    if paths_are_same "$REPO_DIR" "$INSTALL_DIR"; then
        log_info "Repository is already the install directory; skipping source sync"
        return
    fi

    log_info "Synchronizing repository into $INSTALL_DIR"
    run_root mkdir -p "$INSTALL_DIR"

    if command_exists rsync; then
        run_root rsync -a --delete \
            --exclude '.git/' \
            --exclude '.venv/' \
            --exclude '.pytest_cache/' \
            --exclude '.mypy_cache/' \
            --exclude '.ruff_cache/' \
            --exclude '__pycache__/' \
            --exclude '.data/' \
            --exclude 'data/' \
            --exclude 'tmp-debug/' \
            "$REPO_DIR"/ "$INSTALL_DIR"/
    else
        log_warn "rsync not found, falling back to tar copy without deletion of removed files"
        (
            cd "$REPO_DIR"
            tar \
                --exclude='.git' \
                --exclude='.venv' \
                --exclude='.pytest_cache' \
                --exclude='.mypy_cache' \
                --exclude='.ruff_cache' \
                --exclude='__pycache__' \
                --exclude='.data' \
                --exclude='data' \
                --exclude='tmp-debug' \
                -cf - .
        ) | run_root tar -xf - -C "$INSTALL_DIR"
    fi

    log_success "Source sync completed"
}

prepare_directories() {
    log_info "Preparing config and data directories"

    run_root mkdir -p "$CONFIG_DIR" "$DATA_DIR"
    run_root mkdir -p \
        "$DATA_DIR/runtime" \
        "$DATA_DIR/backups" \
        "$DATA_DIR/plugins" \
        "$DATA_DIR/remote-logs" \
        "$DATA_DIR/remote-actions" \
        "$DATA_DIR/reticulum-config"

    if [[ "$DEV_MODE" == false ]]; then
        run_root chown -R "$SERVICE_USER:$SERVICE_GROUP" "$CONFIG_DIR" "$DATA_DIR"
        run_root chmod 750 "$CONFIG_DIR" "$DATA_DIR"
    fi

    log_success "Filesystem layout prepared"
}

ensure_virtualenv() {
    log_info "Preparing Python virtual environment"

    if [[ "$USE_SYSTEM_PYTHON_RUNTIME_DEPS" == true && -x "$VENV_PYTHON" ]] && ! venv_uses_system_site_packages; then
        log_warn "Recreating virtual environment so it can reuse system Python packages"
        run_root rm -rf "$VENV_DIR"
    fi

    if [[ ! -x "$VENV_PYTHON" ]]; then
        if [[ "$USE_SYSTEM_PYTHON_RUNTIME_DEPS" == true ]]; then
            run_root "$PYTHON_BIN" -m venv --system-site-packages "$VENV_DIR"
        else
            run_root "$PYTHON_BIN" -m venv "$VENV_DIR"
        fi
        log_success "Created virtual environment at $VENV_DIR"
    else
        log_info "Reusing existing virtual environment at $VENV_DIR"
    fi
}

install_hearth() {
    log_info "Installing Hearth into the virtual environment"
    run_with_retry 3 5 run_root "$VENV_PYTHON" -m pip install --upgrade pip setuptools wheel hatchling
    if [[ "$USE_SYSTEM_PYTHON_RUNTIME_DEPS" == true ]]; then
        run_with_retry 3 5 run_root "$VENV_PYTHON" -m pip install --no-build-isolation --no-deps --upgrade "$INSTALL_DIR"
    else
        run_with_retry 3 5 run_root "$VENV_PYTHON" -m pip install --no-build-isolation --upgrade "$INSTALL_DIR"
    fi
    log_success "Hearth Python package installed"
}

venv_has_rnsd_module() {
    "$VENV_PYTHON" - <<'PY' >/dev/null 2>&1
import importlib.util

raise SystemExit(0 if importlib.util.find_spec("RNS.Utilities.rnsd") is not None else 1)
PY
}

managed_command_is_usable() {
    local configured_command="${1:-}"

    [[ -n "$configured_command" ]] || return 1

    "$VENV_PYTHON" - "$configured_command" <<'PY' >/dev/null 2>&1
import importlib.util
import shlex
import shutil
import sys
from pathlib import Path

parts = shlex.split(sys.argv[1])
if not parts:
    raise SystemExit(1)

if len(parts) >= 3 and parts[1] == "-m" and parts[2] == "RNS.Utilities.rnsd":
    raise SystemExit(0 if importlib.util.find_spec("RNS.Utilities.rnsd") is not None else 1)

candidate = Path(parts[0]).expanduser()
if candidate.is_absolute():
    raise SystemExit(0 if candidate.exists() and candidate.is_file() and candidate.stat().st_mode & 0o111 else 1)

raise SystemExit(0 if shutil.which(parts[0]) else 1)
PY
}

resolve_backend() {
    if [[ "$BACKEND" == "auto" ]]; then
        if [[ -n "$RETICULUM_IMPORT_CONFIG" || -n "$RETICULUM_MANAGED_COMMAND" ]]; then
            RESOLVED_BACKEND="managed_rnsd"
        elif command_exists rnsd || venv_has_rnsd_module; then
            RESOLVED_BACKEND="managed_rnsd"
        else
            RESOLVED_BACKEND="mock_process"
        fi
    else
        RESOLVED_BACKEND="$BACKEND"
    fi

    if [[ "$RESOLVED_BACKEND" == "managed_rnsd" ]] \
        && ! managed_command_is_usable "$RETICULUM_MANAGED_COMMAND" \
        && ! command_exists rnsd \
        && ! venv_has_rnsd_module; then
        die "managed_rnsd was requested, but no usable rnsd command was found. Install Reticulum first, pass --reticulum-managed-command, or use --backend mock_process."
    fi

    log_success "Reticulum backend selected: $RESOLVED_BACKEND"
}

generate_admin_token_if_needed() {
    if [[ -n "$ADMIN_TOKEN" ]]; then
        return
    fi

    if command_exists openssl; then
        ADMIN_TOKEN="$(openssl rand -hex 24)"
        return
    fi

    ADMIN_TOKEN="$("$PYTHON_BIN" - <<'PY'
import secrets

print(secrets.token_hex(24))
PY
)"
}

write_config_file() {
    local temp_config=""
    local managed_command_value=""

    if [[ -f "$CONFIG_FILE" && "$OVERWRITE_CONFIG" == false ]]; then
        log_warn "Existing config preserved at $CONFIG_FILE"
        return
    fi

    log_info "Generating Hearth config at $CONFIG_FILE"
    generate_admin_token_if_needed
    temp_config="$(mktemp)"
    managed_command_value="${RETICULUM_MANAGED_COMMAND:-}"

    if [[ -f "$CONFIG_FILE" ]]; then
        CONFIG_BACKUP_FILE="${CONFIG_FILE}.bak.$(date +%Y%m%d-%H%M%S)"
        log_info "Backing up existing config to $CONFIG_BACKUP_FILE"
        run_root install -m 640 "$CONFIG_FILE" "$CONFIG_BACKUP_FILE"
    fi

    "$VENV_PYTHON" - "$temp_config" "$DATA_DIR" "$HOST" "$PORT" "$ADMIN_TOKEN" "$TIMEZONE" "$NODE_NAME" "$RESOLVED_BACKEND" "$RETICULUM_IMPORT_CONFIG" "$RETICULUM_CONFIG_DIR" "$managed_command_value" <<'PY'
from pathlib import Path
import sys

import tomli_w
from hearth.system.reticulum_import import build_deployment_payload

output = Path(sys.argv[1])
data_dir = Path(sys.argv[2])
host = sys.argv[3]
port = int(sys.argv[4])
admin_token = sys.argv[5]
timezone = sys.argv[6]
node_name = sys.argv[7]
backend = sys.argv[8]
import_path = Path(sys.argv[9]) if sys.argv[9] else None
reticulum_config_dir = Path(sys.argv[10]) if sys.argv[10] else None
managed_command = sys.argv[11] or None

payload = build_deployment_payload(
    data_dir=data_dir,
    host=host,
    port=port,
    admin_token=admin_token,
    timezone=timezone,
    node_name=node_name,
    backend=backend,
    import_path=import_path,
    reticulum_config_dir=reticulum_config_dir,
    managed_command=managed_command,
)

output.write_text(tomli_w.dumps(payload), encoding="utf-8")
PY

    run_root install -m 640 "$temp_config" "$CONFIG_FILE"
    rm -f "$temp_config"

    if [[ "$DEV_MODE" == false ]]; then
        run_root chown "$SERVICE_USER:$SERVICE_GROUP" "$CONFIG_FILE"
    fi

    CONFIG_CREATED=true
    log_success "Config written to $CONFIG_FILE"
}

read_config_field() {
    local field_name="$1"

    run_root "$VENV_PYTHON" - "$CONFIG_FILE" "$field_name" <<'PY'
from pathlib import Path
import sys
import tomllib

config_path = Path(sys.argv[1])
field_name = sys.argv[2]

with config_path.open("rb") as handle:
    payload = tomllib.load(handle)

mapping = {
    "backend": payload.get("reticulum", {}).get("backend", ""),
    "managed_command": payload.get("reticulum", {}).get("managed_command", ""),
    "host": payload.get("web", {}).get("host", ""),
    "port": payload.get("web", {}).get("port", ""),
}

print(mapping[field_name])
PY
}

validate_effective_backend() {
    local effective_backend=""
    local effective_managed_command=""

    effective_backend="$(read_config_field backend)"
    if [[ "$effective_backend" != "managed_rnsd" ]]; then
        return
    fi

    effective_managed_command="$(read_config_field managed_command)"

    if managed_command_is_usable "$effective_managed_command" || command_exists rnsd || venv_has_rnsd_module; then
        return
    fi

    if [[ "$CONFIG_CREATED" == true ]]; then
        die "Generated config selected managed_rnsd, but no usable rnsd command was found. Re-run with --backend mock_process or set --reticulum-managed-command."
    fi

    if [[ "$START_SERVICE" == true ]]; then
        die "Existing config uses managed_rnsd, but no usable rnsd command was found. Install Reticulum, update managed_command, or re-run with --overwrite-config --backend mock_process."
    fi

    log_warn "Existing config uses managed_rnsd, but no usable rnsd command was found. Service start was skipped, so deployment continues."
}

verify_hearth_cli() {
    log_info "Running a lightweight Hearth verification"
    run_root "$VENV_HEARTH" status --config "$CONFIG_FILE" >/dev/null
    log_success "Hearth CLI can load the generated deployment"
}

run_preflight_check() {
    local preflight_json=""

    log_info "Running deployment preflight"
    preflight_json="$(run_root "$VENV_HEARTH" deploy preflight --config "$CONFIG_FILE")"

    if ! PREFLIGHT_JSON="$preflight_json" "$VENV_PYTHON" - <<'PY'
import json
import os

payload = json.loads(os.environ["PREFLIGHT_JSON"])
raise SystemExit(0 if payload.get("ok") else 1)
PY
    then
        printf '%s\n' "$preflight_json"
        die "Hearth preflight reported failed checks"
    fi

    log_success "Preflight checks passed"
}

restore_service_ownership() {
    if [[ "$DEV_MODE" == true ]]; then
        return
    fi

    log_info "Restoring ownership for runtime paths"
    run_root chown -R "$SERVICE_USER:$SERVICE_GROUP" "$CONFIG_DIR" "$DATA_DIR"
    log_success "Runtime paths are owned by $SERVICE_USER:$SERVICE_GROUP"
}

systemd_unit_exists() {
    local unit_name="$1"
    local load_state=""

    load_state="$(run_root systemctl show -P LoadState "$unit_name" 2>/dev/null || true)"
    [[ -n "$load_state" && "$load_state" != "not-found" ]]
}

get_unit_fragment_path() {
    local unit_name="$1"

    run_root systemctl show -P FragmentPath "$unit_name" 2>/dev/null || true
}

path_requires_home_access() {
    local candidate="$1"

    case "$candidate" in
        /home/*|/root/*)
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

write_systemd_service() {
    local temp_service=""
    local service_path=""
    local read_write_paths=""
    local protect_home="true"
    local managed_command_dir=""

    if [[ "$DEV_MODE" == true || "$SYSTEMD_AVAILABLE" == false ]]; then
        return
    fi

    log_info "Writing systemd service to $SERVICE_FILE"
    temp_service="$(mktemp)"
    service_path="$VENV_DIR/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
    read_write_paths="$DATA_DIR $CONFIG_DIR"

    if [[ -n "$RETICULUM_CONFIG_DIR" ]]; then
        read_write_paths="$read_write_paths $RETICULUM_CONFIG_DIR"
    fi

    if [[ -n "$RETICULUM_MANAGED_COMMAND" ]]; then
        managed_command_dir="$("$VENV_PYTHON" - "$RETICULUM_MANAGED_COMMAND" <<'PY'
import shlex
import sys
from pathlib import Path

parts = shlex.split(sys.argv[1])
if not parts:
    raise SystemExit(0)

candidate = Path(parts[0]).expanduser()
if candidate.is_absolute():
    print(candidate.parent)
PY
)"
        if [[ -n "$managed_command_dir" ]]; then
            service_path="$service_path:$managed_command_dir"
        fi
    fi

    if path_requires_home_access "$SERVICE_HOME" \
        || path_requires_home_access "$RETICULUM_CONFIG_DIR" \
        || path_requires_home_access "$RETICULUM_MANAGED_COMMAND"; then
        protect_home="false"
    fi

    cat >"$temp_service" <<EOF
[Unit]
Description=Hearth Personal Reticulum Node
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$SERVICE_USER
Group=$SERVICE_GROUP
WorkingDirectory=$INSTALL_DIR
Environment=PYTHONUNBUFFERED=1
Environment=PYTHONDONTWRITEBYTECODE=1
Environment=HOME=$SERVICE_HOME
Environment=HEARTH_CONFIG=$CONFIG_FILE
Environment=PATH=$service_path
ExecStart=$VENV_DIR/bin/hearth-api
Restart=on-failure
RestartSec=5
TimeoutStopSec=20
UMask=0027
NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=full
ProtectHome=$protect_home
ReadWritePaths=$read_write_paths

[Install]
WantedBy=multi-user.target
EOF

    run_root install -m 644 "$temp_service" "$SERVICE_FILE"
    rm -f "$temp_service"
    log_success "systemd unit installed"
}

configure_lxmf_integration() {
    local temp_dropin=""

    if [[ "$DEV_MODE" == true || "$SYSTEMD_AVAILABLE" == false || "$INTEGRATE_LXMF" == false ]]; then
        return
    fi

    if ! systemd_unit_exists lxmd.service; then
        log_warn "Requested LXMF integration, but lxmd.service was not found"
        return
    fi

    log_info "Writing lxmd.service drop-in so LXMF follows Hearth"
    temp_dropin="$(mktemp)"
    cat >"$temp_dropin" <<EOF
[Unit]
After=hearth.service
Requires=hearth.service
PartOf=hearth.service
EOF

    run_root mkdir -p "$(dirname "$LXMF_DROPIN_FILE")"
    run_root install -m 644 "$temp_dropin" "$LXMF_DROPIN_FILE"
    rm -f "$temp_dropin"
    LXMF_INTEGRATION_APPLIED=true
    log_success "LXMF integration drop-in installed"
}

stop_legacy_rnsd_service_if_needed() {
    if [[ "$DEV_MODE" == true || "$SYSTEMD_AVAILABLE" == false || "$MASK_LEGACY_RNSD" == false ]]; then
        return
    fi

    if systemd_unit_exists rnsd.service && run_root systemctl is-active --quiet rnsd.service; then
        log_info "Stopping standalone rnsd.service before Hearth takes over"
        run_root systemctl stop rnsd.service
        STOPPED_LEGACY_RNSD_SERVICE=true
    fi
}

mask_legacy_rnsd_service() {
    if [[ "$DEV_MODE" == true || "$SYSTEMD_AVAILABLE" == false || "$MASK_LEGACY_RNSD" == false ]]; then
        return
    fi

    if [[ -f /etc/systemd/system/rnsd.service && ! -L /etc/systemd/system/rnsd.service && ! -f "$LEGACY_RNSD_BACKUP_FILE" ]]; then
        log_info "Preserving existing rnsd.service at $LEGACY_RNSD_BACKUP_FILE"
        run_root mv /etc/systemd/system/rnsd.service "$LEGACY_RNSD_BACKUP_FILE"
    fi

    log_info "Masking standalone rnsd.service"
    run_root systemctl mask rnsd.service >/dev/null 2>&1 || run_root ln -sfn /dev/null /etc/systemd/system/rnsd.service
    LEGACY_RNSD_MASKED=true
    log_success "Standalone rnsd.service is masked"
}

install_service_aliases() {
    local lxmd_fragment=""

    if [[ "$DEV_MODE" == true || "$SYSTEMD_AVAILABLE" == false || "$INSTALL_SERVICE_ALIASES" == false ]]; then
        return
    fi

    log_info "Installing service aliases"
    run_root ln -sfn "$SERVICE_FILE" "$SERVICE_ALIAS_RETICULUM_FILE"
    SERVICE_ALIASES_APPLIED=true

    if [[ "$INTEGRATE_LXMF" == true ]] && systemd_unit_exists lxmd.service; then
        lxmd_fragment="$(get_unit_fragment_path lxmd.service)"
        if [[ -n "$lxmd_fragment" ]]; then
            run_root ln -sfn "$lxmd_fragment" "$SERVICE_ALIAS_LXMF_FILE"
        fi
    fi

    log_success "Service aliases installed"
}

reload_systemd_units() {
    if [[ "$DEV_MODE" == true || "$SYSTEMD_AVAILABLE" == false ]]; then
        return
    fi

    run_root systemctl daemon-reload
}

manage_lxmf_service() {
    local action="${1:-start}"

    if [[ "$DEV_MODE" == true || "$SYSTEMD_AVAILABLE" == false || "$INTEGRATE_LXMF" == false ]]; then
        return
    fi

    if ! systemd_unit_exists lxmd.service; then
        return
    fi

    if [[ "$action" == "enable" && "$ENABLE_SERVICE" == true ]]; then
        log_info "Enabling lxmd.service"
        run_root systemctl enable lxmd.service >/dev/null 2>&1 || true
    fi

    if [[ "$action" == "start" && "$START_SERVICE" == true ]]; then
        log_info "Restarting lxmd.service"
        run_root systemctl restart lxmd.service
        run_root systemctl is-active --quiet lxmd.service
        log_success "LXMF service is active"
    fi
}

manage_service() {
    if [[ "$DEV_MODE" == true ]]; then
        return
    fi

    if [[ "$SYSTEMD_AVAILABLE" == false ]]; then
        log_warn "systemd is not available on this host. Skipping service installation/start."
        return
    fi

    if [[ "$ENABLE_SERVICE" == true ]]; then
        log_info "Enabling systemd service"
        run_root systemctl enable "$SERVICE_NAME"
        manage_lxmf_service enable
    else
        log_info "Skipping systemd enable step"
    fi

    if [[ "$START_SERVICE" == true ]]; then
        log_info "Starting systemd service"
        run_root systemctl restart "$SERVICE_NAME"
        run_root systemctl is-active --quiet "$SERVICE_NAME"
        log_success "Hearth service is active"
        manage_lxmf_service start
    else
        if [[ "$STOPPED_RUNNING_SERVICE" == true ]]; then
            log_warn "A running Hearth service was stopped for deployment and was not restarted because --no-start was used"
        elif [[ "$STOPPED_LEGACY_RNSD_SERVICE" == true ]]; then
            log_warn "standalone rnsd.service was stopped for cutover and was not restarted because --no-start was used"
        else
            log_info "Skipping service start"
        fi
    fi
}

detect_access_host() {
    local effective_host="$1"
    local detected_ip=""

    if [[ "$effective_host" == "0.0.0.0" || "$effective_host" == "::" ]]; then
        detected_ip="$(hostname -I 2>/dev/null | awk '{print $1}')"
        if [[ -n "$detected_ip" ]]; then
            printf '%s\n' "$detected_ip"
            return
        fi
        printf '<server-ip>\n'
        return
    fi

    printf '%s\n' "$effective_host"
}

print_summary() {
    local effective_backend=""
    local effective_host=""
    local effective_port=""
    local access_host=""

    effective_backend="$(read_config_field backend)"
    effective_host="$(read_config_field host)"
    effective_port="$(read_config_field port)"
    access_host="$(detect_access_host "$effective_host")"

    printf '\n'
    log_success "Deployment finished"
    printf '  Repo source : %s\n' "$REPO_DIR"
    printf '  Install dir : %s\n' "$INSTALL_DIR"
    printf '  Config file : %s\n' "$CONFIG_FILE"
    printf '  Data dir    : %s\n' "$DATA_DIR"
    printf '  Service user: %s\n' "$SERVICE_USER"
    printf '  Backend     : %s\n' "$effective_backend"
    printf '  Web URL     : http://%s:%s/login\n' "$access_host" "$effective_port"
    if [[ -n "$RETICULUM_CONFIG_DIR" ]]; then
        printf '  RNS config  : %s\n' "$RETICULUM_CONFIG_DIR"
    fi
    if [[ -n "$CONFIG_BACKUP_FILE" ]]; then
        printf '  Config backup: %s\n' "$CONFIG_BACKUP_FILE"
    fi

    if [[ "$CONFIG_CREATED" == true ]]; then
        printf '  Admin token : %s\n' "$ADMIN_TOKEN"
    else
        printf '  Admin token : existing config preserved; see %s\n' "$CONFIG_FILE"
    fi

    if [[ "$DEV_MODE" == true ]]; then
        printf '\n'
        printf 'Run manually:\n'
        printf '  HEARTH_CONFIG=%s %s/bin/hearth-api\n' "$CONFIG_FILE" "$VENV_DIR"
        return
    fi

    if [[ "$SYSTEMD_AVAILABLE" == true ]]; then
        printf '\n'
        printf 'Useful commands:\n'
        if [[ "$SERVICE_ALIASES_APPLIED" == true ]]; then
            printf '  sudo systemctl status reticulum'
            if [[ "$INTEGRATE_LXMF" == true ]]; then
                printf ' lxmf'
            fi
            printf '\n'
        fi
        printf '  sudo systemctl status %s\n' "$SERVICE_NAME"
        if [[ "$INTEGRATE_LXMF" == true ]]; then
            printf '  sudo systemctl status lxmd\n'
            printf '  sudo journalctl -u %s -u lxmd -f\n' "$SERVICE_NAME"
        else
            printf '  sudo journalctl -u %s -f\n' "$SERVICE_NAME"
        fi
    else
        printf '\n'
        printf 'systemd was not detected, so start Hearth manually with:\n'
        printf '  HEARTH_CONFIG=%s %s/bin/hearth-api\n' "$CONFIG_FILE" "$VENV_DIR"
    fi
}

main() {
    parse_args "$@"
    apply_mode_defaults
    apply_option_defaults
    validate_inputs

    if [[ "$(uname -s)" != "Linux" ]]; then
        die "This deployment script only supports Linux hosts. Use --help on non-Linux systems for usage information."
    fi

    configure_privileges
    detect_systemd
    install_system_packages
    select_python
    prepare_paths
    validate_managed_install_dir
    create_service_account
    resolve_service_home
    stop_running_service_if_needed
    sync_source_tree
    prepare_directories
    ensure_virtualenv
    install_hearth
    resolve_backend
    write_config_file
    validate_effective_backend
    verify_hearth_cli
    run_preflight_check
    restore_service_ownership
    write_systemd_service
    configure_lxmf_integration
    stop_legacy_rnsd_service_if_needed
    mask_legacy_rnsd_service
    install_service_aliases
    reload_systemd_units
    manage_service
    print_summary
}

main "$@"
