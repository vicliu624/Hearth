# Hearth

> Personal Reticulum infrastructure for individuals, homes, and small communities.

[简体中文](README_CN.md) · [Docs](docs/README.md) · [Network Model](docs/network-model.md) · [Getting Started](docs/getting-started.md)

**Hearth** is a Linux-first control plane for running a **Personal Reticulum Transport Node** as something you can actually deploy, operate, observe, and recover.

If you only read one paragraph, read this:

> **Reticulum** is a decentralized networking stack that lets devices communicate over different kinds of links without depending entirely on centralized servers. In that world, **Hearth** is the software that helps you run your own stable infrastructure node - the kind of node that stays online, connects interfaces, forwards traffic, learns paths, and gives your devices a local entry point into the wider Reticulum network.

Hearth does not try to replace Reticulum, invent a new protocol, or become a client application. Instead, it focuses on the operational layer around a node: runtime supervision, interface management, discovery visibility, configuration workflows, backup and restore, Web/CLI/API access, and a path toward plugins, services, bridges, and fleet operations.

In short:

> **Hearth turns "a Reticulum node that can run" into "a Reticulum node system you can actually use and manage."**

---

## What Is Reticulum?

Reticulum is a **decentralized networking stack** built around the idea that communication infrastructure does not have to depend on remote centralized services.

At a practical level, it allows devices and software to participate in a distributed network across different kinds of transports, such as:

- IP networks
- serial links
- radio links
- LoRa / RNode-style interfaces
- other transport media supported by the runtime environment

In a Reticulum network, not every node plays the same role.

Some nodes are primarily **clients**:

- phones
- laptops
- embedded devices
- user-facing applications

Other nodes are more stable **transport or infrastructure nodes**. Those nodes help keep the network useful by doing things such as:

- forwarding traffic
- propagating announces
- maintaining path information
- linking multiple interfaces together
- acting as a stable local entry point for nearby devices

That second role is where Hearth lives.

---

## Where Hearth Fits in Reticulum

Hearth is not the Reticulum protocol itself, and it is not the chat or application layer built on top of Reticulum.

Hearth is the **control plane and operations layer** for running a long-lived Reticulum node well.

You can think about it like this:

```text
phones / laptops / local devices
            |
            v
         Hearth
            |
            v
    Reticulum network
```

In this model, Hearth is the thing that turns a Linux device into a **manageable Reticulum infrastructure node**.

More specifically, Hearth helps you run a node that can:

- stay online for long periods
- host one or more interfaces
- expose a local network anchor point
- participate in peer discovery and route learning
- be operated through a real admin surface instead of ad-hoc scripts

So the simplest definition is:

> **Hearth = software for running your own Personal Reticulum Transport Node.**

---

---

## How Do Local Nodes Attach to Hearth?

This is the point that is easiest to misunderstand.

The more accurate statement is not that local nodes "log into Hearth", but that:

> **local nodes attach to the Reticulum Transport Node managed by Hearth.**

So you need to separate two layers:

- **humans connect to the Hearth control plane** through the Web UI, CLI, and API
- **nodes connect to the network node Hearth manages** through local-facing interfaces

The relationship usually looks like this:

```text
operator browser / CLI / API
            |
            v
      Hearth control plane
            |
            v
Hearth-managed Reticulum node
            |
            v
 local-facing interfaces (TCP / serial / radio)
            |
            v
      local client nodes
```

So local phones, laptops, or embedded devices do not normally use `/login` or `/api/*` as their network path.
They run their own Reticulum client or node runtime and then attach through a local-facing interface managed by Hearth.

---

## How Does Hearth Reach the Wider Reticulum Network?

Hearth reaches the wider network not through the Web surface, but through the **uplink / backbone / radio interfaces** it manages.

A complete path usually looks like this:

```text
local client nodes
      |
      v
local-facing interface
      |
      v
Hearth-managed Reticulum node
      |
      v
uplink / backbone interface
      |
      v
wider Reticulum network
```

In that model:

- the **Reticulum runtime** performs announce propagation, path learning, and traffic forwarding
- **Hearth** launches and supervises that runtime, manages the interfaces, and shows you peers, routes, and announces

The current `examples/hearth.toml` already points in two useful directions:

- `tcp_backbone`: an upstream TCP example using `role = "uplink"`
- `rnode_usb`: a radio / serial-style interface example

In a real deployment you would usually add a **local-facing interface** as well, so nearby devices can enter through your Hearth-managed node before that node reaches outward into the wider Reticulum network.

For the full explanation, continue with [`docs/network-model.md`](docs/network-model.md).

## What You Can Do with Hearth

If you are a user, operator, or builder, Hearth lets you do concrete things:

- run your own always-on Reticulum node on a Raspberry Pi, home server, or small Linux host
- connect and manage multiple interfaces from one place
- inspect discovered peers, routes, and announces through the Web UI or API
- start, stop, restart, and supervise the runtime and interfaces
- validate, save, review, and restore configuration changes
- export and import backups so the node can be recovered or moved
- manage access with login, tokens, users, roles, and permissions
- extend the node with plugins, services, and bridge integrations
- use the node as a local network entry point for your own devices, home, or small community

In other words, Hearth is what you use when you want to move from:

```text
a Reticulum node that exists in theory
```

to:

```text
a Reticulum node that you can actually deploy, see, control, and rely on
```

---

## What Hearth Is

Hearth is best understood as a **node infrastructure product**.

It is designed for always-on or long-running environments such as:

- Raspberry Pi and small Linux hosts
- home servers and edge boxes
- compact x86 nodes
- community relay devices
- future appliance-style deployments

It aims to provide one consistent operational surface for:

- starting and supervising a Reticulum runtime
- managing multiple interfaces in one place
- observing peers, routes, and announces
- tracking health, metrics, alerts, and diagnostics
- editing, validating, versioning, and restoring configuration
- exporting and importing backups
- managing security, users, roles, and API tokens
- extending the node with plugins, services, and bridge-style integrations
- growing from a single node toward small fleet management

Hearth is **not**:

- a chat app
- a social platform
- a replacement for the Reticulum protocol or stack
- a cloud-first central controller that assumes remote authority

---

## Why Hearth Exists

Reticulum makes a powerful idea possible: people should be able to run their own infrastructure nodes instead of relying on a small number of remote or centralized systems.

In practice, however, operating a stable transport node is still difficult. The hard parts are rarely the protocol itself. The hard parts are everything around it:

- keeping the node online for long periods
- wiring and validating interfaces
- understanding peers, paths, and announces
- diagnosing faults quickly
- restarting safely after failure
- updating and backing up the node
- exposing a manageable control surface to real operators

Hearth exists to reduce that operational burden.

Its goal is to make this workflow normal:

1. Prepare a small always-on device
2. Install Hearth
3. Configure the node
4. Start the runtime
5. Operate it through a clear Web, CLI, and API surface

---

## Current Status
Hearth is currently at **v0.1.0**.

Today, the repository already includes a substantial control-plane implementation with a working Web UI, CLI, REST API, storage layer, configuration workflows, and a broad set of operational pages.

At the same time, this is still an early-stage project and you should understand the current boundary clearly:

- the shipped example config now targets **`managed_rnsd`**, which means Hearth can supervise a real `rnsd` process and render its runtime config automatically
- the **mock runtime backend still exists** and remains useful when you only want to evaluate the control plane without a real Reticulum installation
- the runtime layer now includes a **Runtime Config Bridge** and a **degradation policy engine** for runtime restart, interface restart, and interface quarantine decisions
- many management, observability, security, plugin, bridge, topology, and fleet workflows are present in the product surface
- the current fleet rollout/upgrade path depends on each managed node exposing a reachable management `dashboard_url`

So Hearth is already useful as a runnable prototype and architectural foundation, but it is not presented as a finished appliance yet.

---

## Core Capabilities

### Node lifecycle

- start, stop, restart, and inspect node runtime state
- track uptime, health, and last known runtime signals
- operate the node from Web, API, or CLI
- support `mock_process`, `external_process`, and **`managed_rnsd`** runtime backends
- generate managed Reticulum config from Hearth interface definitions through the runtime config bridge

### Interface management

- manage multiple interfaces with a unified model
- inspect interface status and metrics
- start, stop, and restart individual interfaces
- support roles such as uplink, local, and radio-facing links
- include built-in `tcp`, `serial`, `rnode`, `local`, and `custom` interface drivers

### Discovery and routing visibility

- view peers, routes, and announces
- inspect details for individual peers and routes
- surface network-map, route-heatmap, critical-node, and path-change pages
- support snapshot-style operational understanding of node state

### Health, monitoring, and maintenance

- health checks and diagnostics views
- metrics dashboard and Prometheus-style metrics export
- alerts and maintenance workflows
- remote log aggregation views and upgrade/rollout pages
- watchdog-oriented service model for long-running operation
- degradation-policy decisions for runtime recovery, interface restart, and quarantine handling

### Configuration and backups

- read and validate structured configuration
- edit raw TOML configuration
- save revisions and review differences
- restore previous config revisions
- export/import backups for node portability and recovery
- create backup snapshots, prune retained snapshots, and generate disaster-recovery checklists

### Security and access control

- login flow for the Web UI
- administrator token support
- roles, permissions, users, and API tokens
- audit-style activity records
- LAN/WAN exposure switches and local-first deployment defaults
- create, edit, and delete **custom RBAC roles** directly from config, API, CLI, and Web UI

### Plugins, services, and bridges

- plugin catalog and plugin detail pages
- plugin source management with trust metadata
- **Ed25519 public-key signature verification** for signed plugin source manifests
- plugin catalog install / update / uninstall flows with dependency resolution and recorded operation history
- plugin sandbox-boundary metadata so operators can understand filesystem/network expectations before enabling an extension
- service inventory and service detail pages
- bridge catalog and bridge detail pages with controls, health checks, recent operations, and delivery tests

### Fleet and topology direction

- node inventory, groups, tags, templates, and health views
- fleet overview and event pages
- remote rollout and upgrade dispatch through each node's management endpoint
- remote log pull/push aggregation for fleet-style operations
- topology and network-intelligence style pages for broader node understanding

---

## Web Console

The Hearth Web console is not meant to be a generic admin panel. It is a **node operations console**.

Important page groups currently include:

- **Dashboard**: node summary, health, runtime, and quick actions
- **Interfaces / Peers / Routes / Announces**: visibility into the live network surface
- **Logs / Alerts / Diagnostics / Metrics**: operational observability
- **Configuration / Config History / Backup**: recovery and change management
- **System / Maintenance / Upgrade / Rollout**: node administration workflows
- **Users / Roles / Tokens / Security / Audit**: access management, custom RBAC role editing, and accountability
- **Plugins / Plugin Sources / Services / Bridges**: signed catalogs, install/update/uninstall flows, source trust, and service hosting
- **Backup / Remote Logs**: snapshot retention, disaster recovery guidance, and fleet log synchronization
- **Fleet / Topology / Network Map / Path Changes**: multi-node and network understanding views

The console also includes locale-aware rendering and translation fallback so a damaged translation entry does not break the page into unreadable placeholders.

---

## CLI and API

Hearth exposes the same operational model through multiple interfaces.

### CLI

The CLI entrypoint is `hearth`.

Examples:

```bash
hearth serve --config hearth.toml
hearth status --config hearth.toml
hearth interfaces list --config hearth.toml
hearth peers list --config hearth.toml
hearth routes list --config hearth.toml
hearth announces list --config hearth.toml
hearth backup export --config hearth.toml
hearth backup snapshot --config hearth.toml
hearth backup prune --config hearth.toml --keep 10 --max-age-days 30
hearth plugins catalog --config hearth.toml
hearth plugins install mesh_bridge --config hearth.toml
hearth security roles list --config hearth.toml
hearth remote-logs sync --config hearth.toml
hearth deploy preflight --config hearth.toml
hearth system diagnostics --config hearth.toml
```

### REST API

Representative endpoints include:

- `/api/node/*`
- `/api/interfaces/*`
- `/api/peers/*`
- `/api/routes/*`
- `/api/announces/*`
- `/api/config/*`
- `/api/backup/*`
- `/api/security/*`
- `/api/plugins/*`
- `/api/services/*`
- `/api/bridges/*`
- `/api/fleet/*`
- `/api/topology/*`
- `/metrics`

The Web, CLI, and API are intentionally aligned so the product feels like one system rather than disconnected tools.

---

## Quick Start

### Requirements

- Python `3.12+`
- a local virtual environment is recommended
- Linux is the target deployment platform, but local development also works on Windows

### 1. Create a virtual environment

**Windows PowerShell**

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e .[dev]
```

If PowerShell activation is blocked by execution policy, you can keep using `.\.venv\Scripts\python.exe` directly.

**Linux / macOS**

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .[dev]
```

### 2. Prepare a config

Start from the example config:

**Windows**

```powershell
Copy-Item examples\hearth.toml .\hearth.toml
```

**Linux / macOS**

```bash
cp examples/hearth.toml ./hearth.toml
```

The example config is configured for local development and uses:

- `backend = "managed_rnsd"`
- `host = "127.0.0.1"`
- `port = 8480`
- `auth_mode = "local_token"`

If you do **not** have Reticulum / `rnsd` installed yet and only want to explore the control plane, switch:

- `reticulum.backend = "mock_process"`

If you keep the default managed runtime path, make sure `rnsd` is available on `PATH` or that `python -m RNS.Utilities.rnsd` works in your environment.

Before exposing the service beyond localhost, change at least:

- `security.admin_token`
- `security.allow_wan`
- any example interface endpoints

### 3. Start Hearth

```bash
python -m hearth.cli.main serve --config hearth.toml
```

### 4. Open the Web console

Visit:

```text
http://127.0.0.1:8480/login
```

Log in using the admin token from `hearth.toml`.

For local testing, token-based access also works in API requests, for example:

```bash
curl -H "X-Hearth-Token: change-me" http://127.0.0.1:8480/api/node/status
```

### 5. Try a few commands

```bash
python -m hearth.cli.main status --config hearth.toml
python -m hearth.cli.main interfaces list --config hearth.toml
python -m hearth.cli.main peers list --config hearth.toml
python -m hearth.cli.main system info --config hearth.toml
```

---

## Configuration Model

Hearth uses TOML configuration.

The example file at `examples/hearth.toml` demonstrates the main sections:

- `[system]`
- `[reticulum]`
- `[web]`
- `[security]`
- `[monitor]`
- `[[interfaces]]`
- `[[plugins]]`

Important design notes:

- the runtime adapter supports `mock_process`, `external_process`, and `managed_rnsd`
- `managed_rnsd` can render a managed Reticulum config from Hearth interfaces and supervise the resulting process lifecycle
- the project stores operational data under the configured `data_dir`
- custom RBAC roles live under `[[roles]]`
- plugin state, remote logs, managed runtime files, and backup snapshots are also derived beneath `data_dir`
- configuration changes can be validated, versioned, reviewed, and restored

---

## Security Model

Hearth is built as a local-first administrative surface.

Current security mechanisms include:

- admin-token based authentication
- Web login with cookie session flow
- role-based access control with permissions such as `read`, `operate`, `configure`, `security`, `tokens`, and `maintenance`
- editable custom roles layered on top of the built-in role set
- user and token management pages
- audit-oriented event recording
- network exposure controls through `allow_lan` and `allow_wan`

The included built-in roles currently cover operators such as:

- `owner`
- `admin`
- `operator`
- `viewer`
- `service_manager`

Security in Hearth is meant to protect the control plane around the node, not to replace network-level security decisions inside Reticulum itself.

---

## Plugins, Services, and Bridge Integrations

Hearth is designed to grow beyond a fixed built-in feature set.

### Plugin sources

Plugin sources can carry trust metadata and signature state. Signed manifests can be validated with **Ed25519 public-key signatures**, allowing Hearth to distinguish between trusted, verified, invalid, missing, and non-required signature states.

The Web UI, CLI, and API now expose the full operator loop around those catalogs:

- view catalog entries and source trust state
- resolve dependencies before install
- install, update, enable/disable, and uninstall plugins
- inspect recent plugin operation history and sandbox-boundary metadata

### Services

The project includes service-host style inventory and control surfaces for operational sub-systems such as runtime supervision, observation sync, backup management, and related workflows.

### Bridges

Bridge catalog pages expose a more productized integration model. Current bridge workflows include:

- bridge list and detail pages
- action controls
- source trust and signature information
- health checks
- recent operation history
- delivery tests

This creates a path toward protocol bridges, relays, webhook-style integrations, and future upper-layer infrastructure services.

---

## Deployment Direction

Hearth is **Linux-first** and already includes packaging-oriented assets such as:

- `packaging/systemd/hearth.service`
- `packaging/docker/Dockerfile`
- `packaging/docker/docker-compose.yml`
- `packaging/install.sh`

The CLI can also render deployment artifacts through `hearth deploy ...` commands.

For real Linux cutovers, `deploy.sh` now also supports adopting an existing user-owned Reticulum node in one step:

```bash
bash deploy.sh --adopt-existing-reticulum vicliu
```

That mode imports the user's existing `.reticulum/config`, rewires `lxmd`, masks the old standalone `rnsd.service`, and installs the friendlier `reticulum.service` / `lxmf.service` aliases described in `DEPLOYMENT.md`.

Current deployment helpers include:

- `hearth deploy systemd`
- `hearth deploy dockerfile`
- `hearth deploy compose`
- `hearth deploy debian-control`
- `hearth deploy appliance-manifest`
- `hearth deploy openwrt`
- `hearth deploy migration-plan`
- `hearth deploy preflight`

Typical target deployment shapes include:

- a Raspberry Pi home node
- a compact always-on x86 node
- a mixed Internet + radio node
- a small community anchor node
- a future appliance-style personal infrastructure box

---

## Repository Layout

```text
src/hearth/
  api/           FastAPI routes
  cli/           Typer command-line interface
  core/          app wiring, config, lifecycle, context
  crypto/        Ed25519 primitives used by trust workflows
  discovery/     discovery-oriented helpers
  interfaces/    interface abstractions and validation
  monitor/       health, watchdog, metrics, diagnostics
  plugins/       plugin manifests and loading helpers
  reticulum/     runtime adapter layer
  services/      node, config, backup, security, fleet, topology, bridges, etc.
  storage/       persistence and database access
  system/        system-level helpers
  web/           Jinja templates, i18n, and Web views
examples/
  hearth.toml    local development config
packaging/
  docker/        container assets
  systemd/       service unit
tests/
  unit and integration-oriented test coverage
```

---

## What Hearth Is Trying to Become

Hearth is trying to become the thing that the Reticulum ecosystem still needs in practical day-to-day operation:

> **a dependable, user-operated, personal infrastructure node system**

That means:

- not only a runtime, but an operational product
- not only a node that starts, but a node that can be managed
- not only a dashboard, but a recoverable system
- not only a local experiment, but a foundation for homes and communities

---

## Development Notes

Useful commands during development:

```bash
python -m pytest -q
python -m hearth.cli.main --help
python -m hearth.cli.main serve --config hearth.toml
```

If you are evaluating the UI locally, the example config is the fastest path because it brings up a self-contained mock-backed node surface without requiring a real Reticulum deployment first.

---

## Project Boundaries

To keep Hearth healthy, its scope stays intentionally focused.

Hearth should prioritize:

- transport-node operations
- observability and recovery
- configuration and lifecycle management
- local-first administration
- extensibility through plugins and services

Hearth should avoid becoming:

- a heavyweight social layer
- a replacement for all client apps
- an over-centralized cloud platform
- a kitchen-sink product that weakens the node core

---

## Summary

**Hearth is a deployable, manageable, observable, and recoverable Personal Reticulum Transport Node system.**



