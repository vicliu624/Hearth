# Getting Started with Hearth

[Chinese (Simplified)](getting-started.zh-CN.md)

This guide is the fastest way to run Hearth locally and understand the current operator surface.

Before diving into commands, here is the context you need:

- **Reticulum** is a decentralized networking stack that allows nodes to communicate across different kinds of transports without depending entirely on centralized servers.
- **Hearth** is the control-plane software that helps you run one of those nodes as real infrastructure: something you can start, inspect, configure, secure, and recover.
- In this guide, you are not setting up a chat app or a generic dashboard. You are bringing up a **Personal Reticulum Transport Node control plane** on your own machine.

By the end of this guide, you will have:

- a local Hearth instance running
- a managed or mock-backed Reticulum node surface available in the Web UI
- working CLI and API access for inspecting and operating the node

The repository example now defaults to **`managed_rnsd`**. That is useful when you already have Reticulum installed locally and want Hearth to supervise a real `rnsd` process. If you do not have Reticulum installed yet, switch the backend to `mock_process` and continue with the rest of this guide unchanged.

## Separate control-plane access from network attachment

This quick start is mainly about attaching to the **Hearth control plane**, which means:

- bringing up the Web UI
- bringing up CLI and API access
- seeing the operational surface of a managed node

It is **not yet** a one-step guide for attaching your devices to the live wider Reticulum network.

Real network attachment still requires you to configure later:

- a real Reticulum runtime backend
- a local-facing interface for nearby client nodes
- an uplink or backbone interface toward the wider network

If you want that relationship explained first, read [`network-model.md`](network-model.md) before continuing.

## Requirements

- Python 3.12+
- A local checkout of this repository

## Install

### Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e .[dev]
```

### Linux / macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .[dev]
```

## Prepare a config

```bash
cp examples/hearth.toml ./hearth.toml
```

On Windows, use:

```powershell
Copy-Item examples\hearth.toml .\hearth.toml
```

The example config now uses:

- `reticulum.backend = "managed_rnsd"`
- `reticulum.managed_command = "rnsd"`
- `web.host = "127.0.0.1"`
- `web.port = 8480`

If `rnsd` is not available in your environment yet, change the config before startup:

```toml
[reticulum]
backend = "mock_process"
```

## Start the server

```bash
python -m hearth.cli.main serve --config hearth.toml
```

## Open the UI

Visit:

```text
http://127.0.0.1:8480/login
```

Use the admin token from `hearth.toml` to log in.

Once you are in, the most useful first pages are:

- `Roles` to see built-in RBAC and create your own custom roles
- `Plugins` and `Plugin Sources` to inspect catalog trust, Ed25519 verification state, install plans, and plugin history
- `Backup` to create exports, snapshots, retention-prune older snapshots, and generate a disaster-recovery checklist
- `Remote Logs` to aggregate local logs, pushed remote logs, and fleet sync results
- `Upgrade` and `Rollout` to understand how future multi-node operations are dispatched

## Try the API

```bash
curl -H "X-Hearth-Token: change-me" http://127.0.0.1:8480/api/node/status
```

## Try the CLI

```bash
python -m hearth.cli.main status --config hearth.toml
python -m hearth.cli.main interfaces list --config hearth.toml
python -m hearth.cli.main peers list --config hearth.toml
python -m hearth.cli.main plugins catalog --config hearth.toml
python -m hearth.cli.main backup snapshot --config hearth.toml
python -m hearth.cli.main remote-logs sync --config hearth.toml
python -m hearth.cli.main security roles list --config hearth.toml
```

## Important note

Before exposing Hearth beyond local development, change the default `security.admin_token`, review all network exposure settings, and decide whether your deployment should stay on `mock_process` or move to a real managed `rnsd` runtime.
