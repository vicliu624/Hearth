# Hearth Architecture v0.1

This document describes the current runtime architecture of Hearth as implemented in the repository today.

It focuses on the **control plane** around a Personal Reticulum Transport Node: how the application is wired, how data moves through the system, and where major operational responsibilities live.

Before discussing modules and services, it helps to place Hearth in context.

## Reticulum Context

Reticulum is a decentralized networking stack in which nodes can participate in communication over different kinds of transports and links. Within that broader network, some nodes behave mainly like clients, while others behave more like **transport or infrastructure nodes**.

Those infrastructure-oriented nodes matter because they can:

- remain online for long periods
- connect multiple interfaces together
- forward traffic
- propagate announces
- maintain path knowledge
- act as a stable local entry point for nearby devices

## Hearth's Role

Hearth is the software layer that helps such a node become operationally usable.

In other words:

- Reticulum provides the network stack
- Hearth provides the control plane around a node running in that stack

That is why the architecture described here is not centered only on packet transport. It is centered on the surrounding operational system:

- lifecycle management
- configuration
- observability
- persistence
- security
- recovery loops
- plugin, service, bridge, topology, and fleet foundations

So when you read this document, the right mental model is:

> **Hearth is the operating layer around a Personal Reticulum Transport Node.**

---

## Design Intent

Hearth is built as a **node operations system**, not as a replacement for Reticulum itself.

The current architecture is designed around a few guiding principles:

- Linux-first deployment
- single-node maturity first
- local-first administration
- clear separation between runtime/data-plane concerns and control-plane concerns
- observable, recoverable long-running operation
- extensibility through plugins, services, bridges, and future fleet features

---

## High-Level Layers

Hearth can be understood as five cooperating layers.

### 1. Entry surfaces

These are the operator-facing entrypoints:

- **Web UI** via FastAPI + Jinja templates
- **REST API** via FastAPI routers under `/api/*`
- **CLI** via Typer commands under `hearth`

All three surfaces are intentionally aligned so they operate on the same service model.

### 2. Application context and lifecycle

The `ApplicationContext` in `src/hearth/core/lifecycle.py` assembles the full runtime dependency graph.

It is responsible for creating:

- settings
- event bus
- async scheduler
- database access
- identity manager
- Reticulum adapter
- interface registry
- stores for peers, paths, and announces
- service-layer objects used by Web/API/CLI

The FastAPI app is then created in `src/hearth/api/main.py`, which attaches the context, installs security middleware, mounts routers, and exposes static assets.

### 3. Runtime and control-plane services

The runtime boundary is represented by `ManagedReticulumAdapter`.

Around that adapter, Hearth builds higher-level services for:

- node lifecycle management
- interface control
- observation synchronization
- peers, routes, and announces
- configuration and config revisions
- backup and restore
- plugins and bridge catalog
- maintenance, diagnostics, alerts, upgrades, and topology
- security, users, roles, and tokens
- fleet inventory and related views

### 4. Persistence and state

Hearth persists operational state through SQLite and runtime files stored under the configured `data_dir`.

Examples include:

- `hearth.db`
- runtime state snapshots
- runtime observation snapshots
- runtime stdout/stderr logs
- backups and exported archives

### 5. Background jobs and recovery loops

The scheduler is used to keep the node fresh and observable over time.

Current recurring jobs include:

- state refresh
- alerts refresh
- watchdog checks

These jobs turn Hearth from a request/response application into a continuously operating node-management system.

---

## Core Runtime Composition

At startup, Hearth builds a dependency graph centered on the application context.

### Core primitives

The context currently creates and owns:

- `EventBus`
- `AsyncScheduler`
- `Database`
- `IdentityManager`
- `ManagedReticulumAdapter`
- `InterfaceRegistry`
- `PeerStore`
- `PathSnapshotStore`
- `AnnounceStore`
- `HealthStatusEvaluator`
- `MetricsCollector`
- `LogService`

### Service layer

On top of those primitives, the context wires the operational services that power the product surface:

- `NodeService`
- `InterfaceService`
- `ObservationService`
- `PeerService`
- `RouteService`
- `AnnounceService`
- `ConfigService`
- `ConfigVersionService`
- `BackupService`
- `PluginService`
- `BridgeCatalogService`
- `SecurityService`
- `MaintenanceService`
- `DiagnosticsService`
- `AlertService`
- `ServiceHostService`
- `FleetService`
- `RolloutService`
- `RemoteLogService`
- `UpgradeService`
- `TopologyService`

This is the center of Hearth's architecture: a control-plane service graph built around one managed node.

---

## Startup Flow

A typical startup flow looks like this:

1. Load configuration and resolve runtime paths
2. Initialize storage, eventing, runtime adapter, and service graph
3. Create the FastAPI application and attach context
4. Register built-in interface types and configure declared interfaces
5. Restore saved interface runtime states from the database
6. Start the Reticulum adapter if auto-start is enabled
7. Refresh node state and run an initial observation sync
8. Start scheduler jobs for refresh, alerts, and watchdog loops

This design ensures the node can surface meaningful state immediately after startup rather than waiting for the first user action.

---

## Runtime Backends

The current architecture supports two runtime backend modes:

- `mock_process`
- `external_process`

### `mock_process`

This is the default development backend used by the example configuration. It allows Hearth to be run locally without a full external Reticulum environment.

### `external_process`

This mode is the architectural bridge toward a real long-running runtime process managed by Hearth.

This separation is deliberate: it lets the control plane mature even while deeper protocol/runtime integration continues to evolve.

---

## Data Flow

Hearth's control plane is largely driven by a recurring data flow:

```text
Reticulum adapter
  -> observation sync
  -> peer / route / announce stores
  -> database snapshots and events
  -> service layer summaries
  -> Web / API / CLI output
```

More concretely:

- the adapter provides runtime state and observation data
- `ObservationService` translates runtime observations into structured stores
- peer, route, and announce services read from those stores and persist snapshots/events
- Web/API/CLI endpoints expose summaries and detail views built from those services

This keeps protocol-facing logic close to the adapter while presenting operators with a higher-level, productized model.

---

## Interface Management Model

Interfaces are managed through an `InterfaceRegistry` and an `InterfaceService`.

The current model provides:

- registration of built-in interface types
- validation and configuration of declared interfaces
- runtime state tracking
- per-interface start/stop/restart operations
- metrics and status summaries

This gives Hearth a single operational model across TCP, radio-style, serial, and custom interface definitions.

---

## Observability Model

Observability is a first-class part of the architecture.

The current implementation includes:

- node status summaries
- metrics collection
- health evaluation
- watchdog automation
- logs and audit records
- diagnostics views
- alerts views and alert refresh loops
- topology and network-insight style summaries

The Web UI is therefore not a thin skin over raw runtime data; it is a presentation layer built on top of deliberate observability services.

---

## Security Model in the Architecture

Security in Hearth is applied at the control-plane boundary.

Current architectural elements include:

- request host filtering through `allow_lan` / `allow_wan`
- security headers applied by middleware
- token-based authentication
- cookie-based Web login flow
- permission checks at route level
- roles, users, and API token management via `SecurityService`

The current permission vocabulary includes capabilities such as:

- `read`
- `operate`
- `configure`
- `security`
- `tokens`
- `maintenance`

This allows Hearth to distinguish read-only observability from operational or security-sensitive actions.

---

## Web, API, and CLI Relationship

Hearth intentionally avoids building three unrelated management surfaces.

Instead:

- the **service layer** is the operational core
- the **API** exposes those services programmatically
- the **Web UI** renders those services visually
- the **CLI** uses the same context and service graph for command-line workflows

This is an important architectural property because it reduces drift between interfaces and makes the system easier to reason about and test.

---

## Persistence Layout

Most node-local state resolves under the configured `data_dir`.

Important derived locations include:

- `hearth.db`
- `runtime/reticulum-state.json`
- `runtime/reticulum-observations.json`
- `runtime/reticulum.pid`
- `runtime/reticulum.stdout.log`
- `runtime/reticulum.stderr.log`
- `backups/`

These paths are derived from configuration rather than hard-coded globally, which keeps local development and deployment packaging flexible.

---

## Current Strengths

The current architecture is already strong in a few important ways:

- clear separation of concerns
- one central application context
- service-oriented control plane
- aligned Web/API/CLI model
- structured observability and recovery loops
- extensibility points for plugins, services, bridges, topology, and fleet features

---

## Current Boundaries

The architecture is still evolving, and it is important to understand the current limits:

- the default local experience is still mock-backed
- some advanced product surfaces are richer than the current depth of runtime integration beneath them
- fleet, topology, and service-host features are early platform foundations rather than finished enterprise-grade systems
- external process integration is structurally supported, but real-world hardening is still an ongoing direction

---

## Architectural Direction

The next architectural steps are naturally aligned with Hearth's product goals:

- deeper real Reticulum runtime integration
- richer observation fidelity for peers, paths, and announces
- stronger config apply/reload flows
- more mature plugin/service isolation and lifecycle control
- stronger fleet orchestration and multi-node coordination
- more advanced topology and network-intelligence analysis

---

## Summary

Hearth v0.1 is already a meaningful control-plane architecture for a Personal Reticulum Transport Node.

Its most important property is not that it can start a process, but that it provides a coherent operational system around that process: configuration, supervision, visibility, recovery, security, and extensibility.
