#!/usr/bin/env bash
set -euo pipefail

# Install a tested source archive into a versioned release directory. Existing
# configuration, credentials, identities and databases are never regenerated.
archive=${1:?usage: release-install.sh SOURCE_ARCHIVE VERSION SERVICE_USER}
version=${2:?version required}
service_user=${3:?service user required}
[[ "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+([.-][A-Za-z0-9.-]+)?$ ]] || exit 2
[[ "$service_user" =~ ^[a-z_][a-z0-9_-]*$ ]] || exit 2
service_group=$(id -gn "$service_user")
release="/opt/hearth/releases/$version"
current="/opt/hearth/current"
config="/etc/hearth/hearth.toml"

python3 -c 'import sys; assert sys.version_info >= (3, 12), "Python 3.12 or newer is required"'
sudo -n install -d -o "$service_user" -g "$service_group" -m 0755 /opt/hearth /opt/hearth/releases "$release"
sudo -n install -d -o "$service_user" -g "$service_group" -m 0750 /etc/hearth /var/lib/hearth
[[ ! -e "$release/.installed" ]] || { echo "Release already installed: $release" >&2; exit 2; }
[[ ! -e "$current" || -L "$current" ]] || { echo "Current installation is not a managed symlink" >&2; exit 2; }

python3 - "$archive" "$release" <<'PY'
import sys, tarfile
with tarfile.open(sys.argv[1], "r:gz") as archive:
    archive.extractall(sys.argv[2], filter="data")
PY
python3 -m venv "$release/.venv"
"$release/.venv/bin/python" -m pip install -c "$release/requirements-lock.txt" "$release[reticulum]"
"$release/.venv/bin/python" -m pip check

if [[ ! -f "$config" ]]; then
    lan_device=$(ip -o route show default | awk 'NR==1 { print $5 }')
    "$release/.venv/bin/python" - "$config" "$lan_device" <<'PY'
import os, secrets, sys
from pathlib import Path
from hearth.core.config import HearthSettings, dump_settings

os.umask(0o077)
interfaces = [{"name": "LAN TCP", "type": "tcp", "enabled": True,
               "role": "local", "discoverable": False, "listen_ip": "0.0.0.0", "listen_port": 4242}]
if sys.argv[2]:
    interfaces.insert(0, {"name": "LAN discovery", "type": "local", "enabled": True,
                          "role": "discovery", "discoverable": False, "devices": [sys.argv[2]]})
settings = HearthSettings.model_validate({
    "system": {"node_name": "Hearth-LAN", "data_dir": "/var/lib/hearth", "timezone": "Asia/Shanghai"},
    "reticulum": {"backend": "managed_rnsd", "auto_start": True,
                  "config_path": "/var/lib/hearth/reticulum",
                  "identity_path": "/var/lib/hearth/reticulum/storage/transport_identity",
                  "managed_command": "/opt/hearth/current/.venv/bin/python -m RNS.Utilities.rnsd",
                  "instance_name": "hearth", "transport_enabled": True},
    "web": {"host": "0.0.0.0", "port": 8480},
    "security": {"admin_token": secrets.token_urlsafe(32), "allow_lan": True, "allow_wan": False},
    "interfaces": interfaces,
})
Path(sys.argv[1]).write_text(dump_settings(settings), encoding="utf-8")
print("Created configuration with a unique admin token; token is stored in", sys.argv[1])
PY
fi

previous=$(readlink "$current" || true)
ln -sfn "$release" /opt/hearth/current.next
mv -Tf /opt/hearth/current.next "$current"
sudo -n tee /etc/systemd/system/hearth.service >/dev/null <<UNIT
[Unit]
Description=Hearth Reticulum node management
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$service_user
Group=$service_group
WorkingDirectory=$current
Environment=PYTHONUNBUFFERED=1
Environment=HEARTH_CONFIG=$config
ExecStart=$current/.venv/bin/hearth-api
Restart=on-failure
RestartSec=5
KillMode=process
TimeoutStopSec=30
UMask=0077
NoNewPrivileges=yes

[Install]
WantedBy=multi-user.target
UNIT
sudo -n systemctl daemon-reload
sudo -n systemctl enable hearth.service
sudo -n systemctl restart hearth.service

if ! "$release/.venv/bin/python" - "$config" <<'PY'
import json, sys, time, tomllib, urllib.request
with open(sys.argv[1], "rb") as stream:
    config = tomllib.load(stream)
url = f"http://127.0.0.1:{config['web']['port']}/api/node/status"
request = urllib.request.Request(url, headers={"X-Hearth-Token": config['security']['admin_token']})
last = None
for _ in range(45):
    try:
        with urllib.request.urlopen(request, timeout=3) as response:
            last = json.load(response)
        if last['runtime_status'] == 'running' and last['health_status'] == 'healthy':
            print(json.dumps({"runtime": last['runtime_status'], "health": last['health_status'],
                              "interfaces": last['interface_summary']}))
            break
    except Exception as error:
        last = str(error)
    time.sleep(1)
else:
    print("Health verification failed:", last, file=sys.stderr)
    raise SystemExit(1)
PY
then
    if [[ -n "$previous" ]]; then
        ln -sfn "$previous" /opt/hearth/current.next
        mv -Tf /opt/hearth/current.next "$current"
        sudo -n systemctl restart hearth.service
    fi
    echo "Deployment verification failed; inspect the service journal" >&2
    exit 1
fi
date -u +%FT%TZ > "$release/.installed"
printf 'Installed Hearth %s at %s\n' "$version" "$release"
