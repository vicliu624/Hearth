#!/bin/bash
# Hearth Remote Deployment Script
# This script deploys Hearth as a systemd service on a Linux server
# 
# Usage: bash deploy.sh [options]
# Options:
#   --no-sudo       Skip sudo for local deployment (for containerized environments)
#   --config-only   Only create configuration files, don't start service
#   --dev           Development mode (don't use sudo, assume already in /opt/hearth)

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
INSTALL_DIR="${INSTALL_DIR:-/opt/hearth}"
CONFIG_DIR="${CONFIG_DIR:-/etc/hearth}"
DATA_DIR="${DATA_DIR:-${INSTALL_DIR}/data}"
SERVICE_NAME="hearth"
SERVICE_USER="hearth"
SERVICE_GROUP="hearth"
ADMIN_TOKEN="${ADMIN_TOKEN:-change-me-secure-token-12345}"

# Parse arguments
DEV_MODE=false
CONFIG_ONLY=false
USE_SUDO="sudo"

while [[ $# -gt 0 ]]; do
    case $1 in
        --dev)
            DEV_MODE=true
            USE_SUDO=""
            shift
            ;;
        --config-only)
            CONFIG_ONLY=true
            shift
            ;;
        --no-sudo)
            USE_SUDO=""
            shift
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[⚠]${NC} $1"
}

log_error() {
    echo -e "${RED}[✗]${NC} $1"
}

echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   Hearth - Reticulum Personal Transport Node Control   ║${NC}"
echo -e "${BLUE}║              Deployment Script                         ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}"
echo ""

# Step 1: Check system requirements
log_info "Checking system requirements..."
if ! command -v python3 &> /dev/null; then
    log_error "Python 3 is not installed"
    exit 1
fi

PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
log_success "Python $PYTHON_VERSION found"

if ! command -v git &> /dev/null; then
    log_warn "Git not found, some features may be limited"
fi

# Step 2: Create service user and directories (only if not in dev mode)
if [ "$DEV_MODE" = false ]; then
    log_info "Creating service user and directories..."
    $USE_SUDO useradd --system --home "$INSTALL_DIR" --shell /usr/sbin/nologin "$SERVICE_USER" 2>/dev/null || log_warn "User $SERVICE_USER already exists"
fi

log_info "Creating required directories..."
$USE_SUDO mkdir -p "$INSTALL_DIR" "$CONFIG_DIR" "$DATA_DIR"
$USE_SUDO mkdir -p "$INSTALL_DIR/reticulum-config"

if [ "$DEV_MODE" = false ]; then
    $USE_SUDO chown -R "$SERVICE_USER:$SERVICE_GROUP" "$INSTALL_DIR" "$CONFIG_DIR" "$DATA_DIR"
fi
log_success "Directories created/verified"

# Step 3: Install system dependencies
log_info "Checking/installing system dependencies..."
if command -v apt-get &> /dev/null; then
    log_info "Detected Debian/Ubuntu system"
    $USE_SUDO apt-get update -qq
    $USE_SUDO apt-get install -y -qq python3-pip python3-venv python3-dev git curl || true
elif command -v dnf &> /dev/null; then
    log_info "Detected Fedora/RHEL system"
    $USE_SUDO dnf install -y -q python3-pip python3-devel git curl || true
elif command -v yum &> /dev/null; then
    log_info "Detected CentOS/RHEL system"
    $USE_SUDO yum install -y -q python3-pip python3-devel git curl || true
fi
log_success "System dependencies ready"

# Step 4: Set up Python virtual environment
log_info "Setting up Python virtual environment..."
cd "$INSTALL_DIR"

if [ ! -d "venv" ]; then
    $USE_SUDO python3 -m venv venv
    log_success "Virtual environment created"
else
    log_warn "Virtual environment already exists"
fi

if [ "$DEV_MODE" = false ]; then
    $USE_SUDO chown -R "$SERVICE_USER:$SERVICE_GROUP" "$INSTALL_DIR/venv"
fi

# Step 5: Install Python packages
log_info "Installing Python packages..."
if [ "$DEV_MODE" = true ]; then
    . venv/bin/activate
    pip install --upgrade pip setuptools wheel 2>/dev/null || true
    pip install -e . 2>/dev/null || { log_warn "Some packages may need manual installation"; true; }
else
    $USE_SUDO bash -c "cd $INSTALL_DIR && source venv/bin/activate && pip install --upgrade pip setuptools wheel 2>/dev/null || true"
    $USE_SUDO bash -c "cd $INSTALL_DIR && source venv/bin/activate && pip install -e . 2>/dev/null || { echo 'Some packages may need manual installation'; true; }"
fi
log_success "Python packages installed"

# Step 6: Create configuration file
log_info "Creating Hearth configuration..."

CONFIG_FILE="$CONFIG_DIR/hearth.toml"
if [ -f "$CONFIG_FILE" ] && [ "$CONFIG_ONLY" = false ]; then
    log_warn "Configuration file already exists at $CONFIG_FILE, skipping"
else
    $USE_SUDO tee "$CONFIG_FILE" > /dev/null <<'CONFIG_EOF'
[system]
node_name = "hearth-node"
data_dir = "/opt/hearth/data"
log_level = "INFO"
timezone = "Asia/Shanghai"

[reticulum]
enabled = true
config_path = "/opt/hearth/reticulum-config"
identity_path = "/opt/hearth/data/identity"
auto_start = true
backend = "managed_rnsd"
managed_command = "rnsd"
render_managed_config = true
transport_enabled = true
shared_instance = true
loglevel = 4
heartbeat_interval_sec = 2
health_timeout_sec = 10
shutdown_timeout_sec = 5

[web]
enabled = true
host = "0.0.0.0"
port = 8480
auth_mode = "local_token"

[security]
admin_token = "change-me-secure-token-12345"
allow_lan = true
allow_wan = false

[monitor]
health_check_interval_sec = 15
metrics_refresh_sec = 10
watchdog_enabled = true
auto_restart_runtime = true
auto_restart_interface = true
restart_cooldown_sec = 30

[alerts]
webhook_enabled = false
include_resolved = true
delivery_timeout_sec = 5
sync_interval_sec = 30

# Local LAN interface for client nodes
[[interfaces]]
name = "local_lan"
type = "local"
enabled = true
role = "transport"
devices = ["eth0", "wlan0", "eno1", "enp0s31f6"]
discovery_port = 29716
data_port = 42671

# TCP backbone interface (disabled by default)
# [[interfaces]]
# name = "tcp_backbone"
# type = "tcp"
# enabled = false
# role = "uplink"
# host = "backbone.example.org"
# port = 4242

# RNode interface for LoRa (disabled by default)
# [[interfaces]]
# name = "rnode_lora"
# type = "rnode"
# enabled = false
# device = "/dev/ttyUSB0"
# baudrate = 115200
CONFIG_EOF
    
    if [ "$DEV_MODE" = false ]; then
        $USE_SUDO chown hearth:hearth "$CONFIG_FILE"
        $USE_SUDO chmod 640 "$CONFIG_FILE"
    fi
    log_success "Configuration file created at $CONFIG_FILE"
fi

# Step 7: Install systemd service
if [ "$DEV_MODE" = false ] && [ "$CONFIG_ONLY" = false ]; then
    log_info "Installing systemd service..."
    
    SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
    
    $USE_SUDO tee "$SERVICE_FILE" > /dev/null <<SERVICE_EOF
[Unit]
Description=Hearth - Reticulum Personal Transport Node Control Plane
Documentation=https://github.com/vicliu624/Hearth
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$SERVICE_USER
Group=$SERVICE_GROUP
WorkingDirectory=$INSTALL_DIR
ExecStart=$INSTALL_DIR/venv/bin/python -m hearth.cli.main serve --config $CONFIG_DIR/hearth.toml
Restart=on-failure
RestartSec=10

# Process management
KillMode=mixed
KillSignal=SIGTERM

# Security settings
NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=strict
ProtectHome=yes
ReadWritePaths=$INSTALL_DIR $CONFIG_DIR /var/log

# Resource limits
LimitNOFILE=65536
LimitNPROC=32768

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=$SERVICE_NAME

[Install]
WantedBy=multi-user.target
SERVICE_EOF
    
    $USE_SUDO systemctl daemon-reload
    $USE_SUDO systemctl enable "$SERVICE_NAME" 2>/dev/null || true
    log_success "Systemd service installed"
fi

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║            Deployment Completed Successfully!          ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════╝${NC}"
echo ""

log_success "Installation complete!"
echo ""
echo "Next steps:"
echo ""

if [ "$DEV_MODE" = true ]; then
    echo "  Development mode:"
    echo "    cd $INSTALL_DIR"
    echo "    source venv/bin/activate"
    echo "    python -m hearth.cli.main serve --config $CONFIG_DIR/hearth.toml"
else
    echo "  To start the Hearth service:"
    echo "    sudo systemctl start $SERVICE_NAME"
    echo ""
    echo "  To check service status:"
    echo "    sudo systemctl status $SERVICE_NAME"
    echo ""
    echo "  To view logs:"
    echo "    sudo journalctl -u $SERVICE_NAME -f"
fi

echo ""
echo "  Access the Web UI:"
echo "    http://$(hostname -I | awk '{print $1}'):8480/login"
echo ""
echo "  Default admin token:"
echo "    change-me-secure-token-12345"
echo ""
echo "  Important: Change the admin token in $CONFIG_FILE immediately!"
echo ""
