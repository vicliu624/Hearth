# Hearth Deployment Guide

This guide explains how to deploy Hearth to a remote Linux server using the provided deployment script.

## Quick Start (Recommended)

### On the Remote Server (192.168.31.99)

```bash
# Clone the repository
git clone https://github.com/vicliu624/Hearth.git
cd Hearth

# Run the deployment script
bash deploy.sh
```

The script will:
1. Check system requirements
2. Create service user `hearth`
3. Install system dependencies
4. Set up Python virtual environment
5. Install Python packages
6. Create configuration files
7. Install systemd service

### Verify Deployment

```bash
# Check service status
sudo systemctl status hearth

# View logs
sudo journalctl -u hearth -f

# Test the API
curl -H "X-Hearth-Token: change-me-secure-token-12345" http://localhost:8480/api/node/status
```

## Access Hearth

Open your browser and visit:
```
http://192.168.31.99:8480/login
```

Login with the admin token from `/etc/hearth/hearth.toml`:
```
change-me-secure-token-12345
```

## Deployment Script Options

### Standard Deployment (Production)
```bash
bash deploy.sh
```

### Development Mode (No sudo required)
```bash
bash deploy.sh --dev
```

### Configuration Only
```bash
bash deploy.sh --config-only
```

### Without sudo (Container environments)
```bash
bash deploy.sh --no-sudo
```

## Configuration

The main configuration file is located at `/etc/hearth/hearth.toml`

Key settings:
- **web.host**: Bind address (default: 0.0.0.0)
- **web.port**: Bind port (default: 8480)
- **security.admin_token**: Admin authentication token
- **reticulum.backend**: Runtime backend (managed_rnsd, external_process, mock_process)

### Change Admin Token

```bash
# Edit configuration
sudo nano /etc/hearth/hearth.toml

# Update the admin_token field
[security]
admin_token = "your-new-secure-token-here"

# Restart service
sudo systemctl restart hearth
```

## Managing Hearth Service

### Start the service
```bash
sudo systemctl start hearth
```

### Stop the service
```bash
sudo systemctl stop hearth
```

### Restart the service
```bash
sudo systemctl restart hearth
```

### Enable auto-start on boot
```bash
sudo systemctl enable hearth
```

### Disable auto-start
```bash
sudo systemctl disable hearth
```

### View service logs
```bash
# Last 100 lines
sudo journalctl -u hearth -n 100

# Follow logs in real-time
sudo journalctl -u hearth -f

# Last 1 hour
sudo journalctl -u hearth --since "1 hour ago"
```

## Directory Structure

After deployment:
```
/opt/hearth/                    # Application directory
  ├── venv/                     # Python virtual environment
  ├── src/                      # Source code
  ├── data/                     # Runtime data
  │   ├── identity              # Reticulum identity
  │   └── runtime/              # State and metrics
  └── reticulum-config/         # Reticulum configuration

/etc/hearth/                    # Configuration directory
  └── hearth.toml               # Main configuration file

/var/log/journalctl             # Systemd journal (logs visible via journalctl)
```

## Remote Deployment from Windows

### SSH into the server and run deployment

```powershell
# PowerShell on Windows
$RemoteUser = "vicliu"
$RemoteHost = "192.168.31.99"
$RemotePassword = "your-password"

# Set SSH password
$env:SSHPASS = $RemotePassword

# SSH and clone + deploy
sshpass -e ssh -o StrictHostKeyChecking=no "$RemoteUser@$RemoteHost" @"
git clone https://github.com/vicliu624/Hearth.git /tmp/hearth-deploy
cd /tmp/hearth-deploy
bash deploy.sh
"@
```

## Monitoring via Fleet

If you want to monitor multiple Hearth nodes, see [`docs/deployment.md`](docs/deployment.md) for fleet management.

## Troubleshooting

### Service won't start
```bash
# Check service status
sudo systemctl status hearth

# View error logs
sudo journalctl -u hearth -n 50 --no-pager
```

### Port 8480 already in use
```bash
# Find what's using the port
sudo lsof -i :8480

# Choose a different port in hearth.toml
[web]
port = 8481
```

### Can't connect to reticulum
Check if `rnsd` is installed:
```bash
which rnsd
rnsd --version

# Or check configuration
cat /etc/hearth/hearth.toml | grep backend
```

### Permission denied errors
Ensure the hearth user has proper permissions:
```bash
sudo chown -R hearth:hearth /opt/hearth /etc/hearth
sudo chmod 640 /etc/hearth/hearth.toml
```

## Security Recommendations

1. **Change admin token immediately**
   ```bash
   sudo nano /etc/hearth/hearth.toml
   # Update security.admin_token
   ```

2. **Configure firewall rules**
   ```bash
   # Only allow local network access
   sudo ufw allow from 192.168.31.0/24 to any port 8480
   ```

3. **Use HTTPS in production**
   - Configure a reverse proxy (nginx, caddy)
   - Use Let's Encrypt certificates

4. **Restrict WAN access**
   ```toml
   [security]
   allow_wan = false  # Keep disabled for local networks
   allow_lan = true
   ```

## Uninstall

To remove Hearth:

```bash
# Stop service
sudo systemctl stop hearth
sudo systemctl disable hearth

# Remove systemd service
sudo rm /etc/systemd/system/hearth.service
sudo systemctl daemon-reload

# Remove installation
sudo rm -rf /opt/hearth /etc/hearth

# Remove service user
sudo userdel hearth
```

## Support

For issues and questions, see:
- [API Reference](docs/api-reference.md)
- [Configuration Reference](docs/config-reference.md)
- [Network Model](docs/network-model.md)
