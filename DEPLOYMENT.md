# Hearth Deployment Guide

This guide describes the supported Linux deployment flow for this repository.

## Quick Start

On a Linux host:

```bash
git clone https://github.com/vicliu624/Hearth.git
cd Hearth
bash deploy.sh
```

The script will:

- install system dependencies when it can detect a supported package manager
- copy the cloned repository into the managed install directory
- create a Python virtual environment and install Hearth
- generate `/etc/hearth/hearth.toml` if it does not already exist
- create and start a `systemd` service when `systemd` is available

## Default Layout

By default, `deploy.sh` uses:

- install directory: `/opt/hearth`
- config directory: `/etc/hearth`
- data directory: `/var/lib/hearth`
- service name: `hearth`
- web address: `http://<server-ip>:8480/login`

The generated config uses absolute paths so the service does not depend on where the repository was cloned.

## Backend Selection

The deployment script defaults to:

```text
--backend auto
```

That means:

- if `rnsd` or `RNS.Utilities.rnsd` is available, the config uses `managed_rnsd`
- otherwise the config falls back to `mock_process`

This makes the Web console come up reliably even on hosts that do not yet have Reticulum installed.

If you want to force a real Reticulum runtime, install Reticulum first and then run:

```bash
bash deploy.sh --overwrite-config --backend managed_rnsd
```

If you only want the control plane UI to come up, this is enough:

```bash
bash deploy.sh --backend mock_process
```

## Useful Options

```bash
# Rewrite an existing config file
bash deploy.sh --overwrite-config

# Set a custom admin token instead of generating one
bash deploy.sh --admin-token your-token-here

# Skip auto-start after installation
bash deploy.sh --no-start

# Skip enable on boot
bash deploy.sh --no-enable

# In-place local install without systemd
bash deploy.sh --dev
```

Run `bash deploy.sh --help` for the complete option list.

## Verify Deployment

On a `systemd` host:

```bash
sudo systemctl status hearth
sudo journalctl -u hearth -f
```

To inspect the active config:

```bash
sudo cat /etc/hearth/hearth.toml
```

The script prints the generated admin token once at the end of deployment. If you preserved an existing config, use the token already stored in `/etc/hearth/hearth.toml`.

## Important Paths

After a default deployment:

```text
/opt/hearth/              application checkout and virtual environment
/opt/hearth/.venv/        Python virtual environment
/etc/hearth/hearth.toml   Hearth config
/var/lib/hearth/          runtime data, database, generated runtime files
```

## Manual Start Without systemd

If the target host does not use `systemd`, the script still installs Hearth but skips service setup.

Start it manually with:

```bash
HEARTH_CONFIG=/etc/hearth/hearth.toml /opt/hearth/.venv/bin/hearth-api
```

For local development-style installs:

```bash
bash deploy.sh --dev
HEARTH_CONFIG=./hearth.toml ./.venv/bin/hearth-api
```

## Troubleshooting

### Python version is too old

Hearth requires Python `3.12+`.

Install Python `3.12+` first, or pass an explicit interpreter:

```bash
bash deploy.sh --python /usr/bin/python3.12
```

### The service does not start

Inspect the service and logs:

```bash
sudo systemctl status hearth
sudo journalctl -u hearth -n 100 --no-pager
```

### `managed_rnsd` is configured but `rnsd` is missing

Either install Reticulum, or switch back to the safe default:

```bash
bash deploy.sh --overwrite-config --backend mock_process
```

### Port `8480` is already in use

Deploy on a different port:

```bash
bash deploy.sh --overwrite-config --port 8481
```

### You want to keep the existing config

Just re-run the script without `--overwrite-config`.

It will reuse `/etc/hearth/hearth.toml` and only refresh the application install.

## Security Notes

- change the admin token if you used a temporary one
- keep `allow_wan = false` unless you intentionally want remote access
- put a reverse proxy in front of Hearth before exposing it to the public Internet

