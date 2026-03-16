# Hearth Deployment Guide

[Chinese (Simplified)](deployment.zh-CN.md)

This document explains how to deploy Hearth in the environments the repository currently supports best.

Before discussing commands, remember the role of the software you are deploying:

- **Reticulum** is the network stack
- **Hearth** is the control plane around a Personal Reticulum Transport Node
- deployment means packaging that control plane so your node can run as real infrastructure, not just as a local development process

---

## Network attachment in a real deployment

When deploying Hearth, it helps to separate three layers clearly:

- **how operators reach the Hearth control plane**: Web, CLI, and API
- **how local nodes reach the node Hearth manages**: through local-facing interfaces
- **how that node reaches the wider Reticulum network**: through uplink, backbone, or radio-facing interfaces

So a real deployment is not only about setting `web.host` and `web.port`. It usually also means planning at least two interface classes:

- one **local-facing interface** for nearby client nodes
- one **upstream interface** so the node can actually reach the wider Reticulum network

If that relationship is still unclear, read [`network-model.md`](network-model.md) first.

## Deployment Modes

Hearth currently fits into four practical deployment modes:

1. **Local development run**
   - best for UI, API, and workflow evaluation
   - uses the built-in mock runtime backend

2. **Linux service deployment with systemd**
   - best for a Raspberry Pi, home server, or other always-on Linux host
   - closest to the intended long-running node model today

3. **Container deployment with Docker / Compose**
   - useful for controlled packaging and reproducible setup
   - requires extra care to keep the exposed port aligned with the config file

4. **Generated deployment artifacts**
   - use `hearth deploy ...` to render service and container assets
   - useful when building a deployment bundle for another system

---

## Prerequisites

For all deployment modes, you need:

- Python 3.12+
- a copy of this repository or a built package
- a Hearth configuration file
- a deliberate choice about local-only vs LAN vs WAN exposure

For Linux service deployment, you also want:

- a dedicated service user
- a stable working directory such as `/opt/hearth`
- a stable config path such as `/etc/hearth/hearth.toml`

---

## Configuration First

Hearth is controlled by a TOML file.

The simplest starting point is:

- `examples/hearth.toml`

Important deployment-sensitive values include:

- `web.host`
- `web.port`
- `web.auth_mode`
- `security.admin_token`
- `security.allow_lan`
- `security.allow_wan`
- `reticulum.backend`
- `reticulum.managed_command`
- `reticulum.render_managed_config`
- `system.data_dir`

If you are deploying on a real machine, change the example `admin_token` immediately.

If you plan to use fleet rollout, upgrades, or remote log sync across multiple Hearth nodes, also plan for a reachable management URL per node. In today's implementation that usually means storing a `dashboard_url` for the remote node, optionally with a token in the query string such as `?token=...`.

---

## Option 1: Local Development Run

This is the fastest way to bring up Hearth.

### Install

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .[dev]
```

On Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e .[dev]
```

### Prepare config

```bash
cp examples/hearth.toml ./hearth.toml
```

The repository example now defaults to `managed_rnsd`. If your machine does not yet have `rnsd` available, switch the backend to `mock_process` for evaluation first.

### Start

```bash
python -m hearth.cli.main serve --config hearth.toml
```

### Open the UI

```text
http://127.0.0.1:8480/login
```

### Best use case

Use this mode when you want to:

- explore the UI
- test CLI and API workflows
- validate config behavior
- understand Hearth before moving to a more persistent deployment

---

## Option 2: Linux Service Deployment with systemd

This is the most natural deployment model for Hearth today.

### Suggested layout

- application directory: `/opt/hearth`
- config directory: `/etc/hearth`
- config file: `/etc/hearth/hearth.toml`
- service user: `hearth`
- service group: `hearth`

### Basic steps

#### 1. Create user and directories

```bash
sudo useradd --system --home /opt/hearth --shell /usr/sbin/nologin hearth || true
sudo mkdir -p /opt/hearth /etc/hearth
sudo chown -R hearth:hearth /opt/hearth /etc/hearth
```

#### 2. Copy the repository

```bash
sudo rsync -a ./ /opt/hearth/
sudo chown -R hearth:hearth /opt/hearth
```

#### 3. Install Hearth in the target directory

The repository already includes `packaging/install.sh`:

```bash
cd /opt/hearth
sudo -u hearth sh packaging/install.sh
```

This script creates a virtual environment and installs the package in editable mode.

#### 4. Create config

```bash
sudo cp /opt/hearth/examples/hearth.toml /etc/hearth/hearth.toml
sudo chown hearth:hearth /etc/hearth/hearth.toml
```

Then edit at least:

- `security.admin_token`
- `web.host`
- `web.port`
- `security.allow_lan`
- `security.allow_wan`
- `system.data_dir`
- `reticulum.backend`
- `reticulum.managed_command`

If you are running a real Reticulum node through Hearth, make sure the service user can execute `rnsd` and write the generated managed config under the configured `data_dir`.

#### 5. Install the systemd unit

The repository includes a ready-made unit at `packaging/systemd/hearth.service`.

```bash
sudo cp /opt/hearth/packaging/systemd/hearth.service /etc/systemd/system/hearth.service
sudo systemctl daemon-reload
sudo systemctl enable hearth
sudo systemctl start hearth
```

#### 6. Verify service state

```bash
sudo systemctl status hearth
journalctl -u hearth -f
```

### Important notes

- The unit uses `HEARTH_CONFIG=/etc/hearth/hearth.toml`
- The service entrypoint is `hearth-api`
- The actual bind host and port come from the Hearth config, not from systemd itself
- If `web.host` is left at `127.0.0.1`, the service stays local-only even when systemd is running correctly

---

## Option 3: Docker / Compose Deployment

The repository includes:

- `packaging/docker/Dockerfile`
- `packaging/docker/docker-compose.yml`

### Build image manually

```bash
docker build -f packaging/docker/Dockerfile -t hearth:latest .
```

### Run with a mounted config directory

```bash
docker run --rm \
  -e HEARTH_CONFIG=/data/hearth.toml \
  -v $(pwd)/data:/data \
  -p 8480:8480 \
  hearth:latest
```

### Important port note

The generated Docker assets in this repository now default to port `8480`, which matches the example Hearth config and the app's default Web port.

That means you should do one of the following intentionally:

- Keep `web.port = 8480` in `hearth.toml` unless you intentionally want to run on another port.
- If you customize the container port, make sure the published port and the config file stay aligned.

The app always listens on whatever `web.port` says.

### Compose

The included `docker-compose.yml` is a starting point, not a fully self-configuring production deployment.

If you use it, make sure the mounted `/data/hearth.toml` matches the container port you expose.

---

## Option 4: Generate Deployment Assets with CLI

Hearth can render deployment files directly.

### systemd unit

```bash
python -m hearth.cli.main deploy systemd --output ./hearth.service
```

### Dockerfile

```bash
python -m hearth.cli.main deploy dockerfile --output ./Dockerfile
```

### Compose file

```bash
python -m hearth.cli.main deploy compose --output ./docker-compose.yml
```

### Additional deployment helpers

```bash
python -m hearth.cli.main deploy debian-control --output ./debian-control
python -m hearth.cli.main deploy appliance-manifest --output ./appliance.json
python -m hearth.cli.main deploy openwrt --output ./Makefile
python -m hearth.cli.main deploy migration-plan --output ./migration-plan.md
python -m hearth.cli.main deploy preflight --config hearth.toml
```

### Full bundle

```bash
python -m hearth.cli.main deploy bundle ./deploy-bundle
```

### When to use this

This is useful when:

- you want to customize workdir, config path, image, or ports
- you want to generate fresh deployment artifacts for another machine
- you want the deployment files to live outside the source tree

---

## Recommended Deployment Path Today

If you are evaluating Hearth:

1. run it locally with the example config
2. learn the UI, API, and CLI workflows
3. move to a Linux host with systemd
4. decide whether the node should stay on `mock_process` or move to a supervised `managed_rnsd` runtime
5. if you are operating multiple Hearth nodes, assign each node a reachable management `dashboard_url` before relying on rollout / upgrade / remote-log sync workflows

If you are aiming for a real always-on node right now, **systemd on Linux** is the most straightforward path.

---

## Operational Checklist

Before calling a deployment complete, verify at least these items:

- the admin token is no longer the default
- `allow_wan` is still disabled unless intentionally needed
- the service starts automatically after reboot
- the configured `data_dir` is writable
- backups can be exported
- the Web UI is reachable on the intended interface only
- the exposed host/port match your config file
- logs can be reviewed with system tooling or the UI
- if using `managed_rnsd`, the host can execute `rnsd` successfully
- if using fleet remote operations, remote nodes expose the expected management URL and token scheme

---

## Common Pitfalls

### The service starts but the UI is unreachable

Check:

- `web.host`
- `web.port`
- firewall rules
- whether you published the correct container port
- whether the systemd service is actually binding to loopback only

### Docker container starts but nothing answers on the published port

Most often this means the port in `hearth.toml` does not match the port mapping you published.

### The UI loads but writes fail

Check:

- filesystem permissions on `data_dir`
- service user ownership
- mounted volume permissions in Docker

### Authentication seems broken

Check:

- `security.admin_token`
- `web.auth_mode`
- whether you are using `Authorization`, `X-Hearth-Token`, query token, or Web login cookie consistently

---

## Summary

Hearth deployment is really about deploying a node control plane, not just starting a web server.

For most real use cases today, the best mental model is:

- local mode for learning
- systemd for a real host
- Docker when you intentionally manage config/port alignment
- generated deployment files when you need packaging flexibility
