# Hearth API Reference

[Chinese (Simplified)](api-reference.zh-CN.md)

This document summarizes the currently exposed API surface in Hearth.

The API is implemented with FastAPI and mounted together with the Web console in the same application.

This is not just a generic admin API. It is the **control-plane API** for operating a Personal Reticulum Transport Node.

That means the API exists so that an operator can do things such as:

- inspect runtime and interface state
- view peers, routes, and announces
- manage configuration and backups
- control security, users, and tokens
- inspect plugins, services, bridges, topology, and fleet data

In context:

- **Reticulum** is the network stack
- **Hearth** is the management layer around a node in that stack
- this API is the programmatic surface of that management layer

---

## Base Behavior

### API + Web in one app

Hearth serves:

- Web pages under routes such as `/`, `/interfaces`, `/plugins`, `/bridges`, etc.
- JSON APIs under `/api/*`
- metrics output under `/metrics`

### Authentication methods

When authentication is enabled, Hearth accepts tokens through the following mechanisms:

- `Authorization: Bearer <token>`
- `X-Hearth-Token: <token>`
- `?token=<token>` query parameter
- `hearth_token` cookie

### Authentication toggle

Authentication is considered enabled unless:

- `web.auth_mode = "none"`

### Host access filtering

Requests are filtered before route handling based on:

- `security.allow_lan`
- `security.allow_wan`

Loopback access is always allowed.

### Security headers

Hearth applies control-plane security headers centrally, including CSP, frame denial, referrer policy, and related browser protections.

---

## Permission Model

Current route-level permissions use the following capability vocabulary:

- `read`
- `operate`
- `configure`
- `security`
- `tokens`
- `maintenance`

In general:

- read-only state inspection uses `read`
- node and interface actions use `operate`
- config/plugin/fleet mutation uses `configure`
- user and role management uses `security`
- API token management uses `tokens`
- maintenance mode changes use `maintenance`

Some basic read endpoints remain accessible without an explicit permission dependency in the current implementation, but should still be considered part of the protected control plane when auth is enabled.

---

## Node

### `GET /api/node/status`

Returns a node status summary.

### `POST /api/node/start`

Permission: `operate`

Starts the managed runtime.

### `POST /api/node/stop`

Permission: `operate`

Stops the managed runtime.

### `POST /api/node/restart`

Permission: `operate`

Restarts the managed runtime.

---

## Interfaces

### `GET /api/interfaces`

Lists configured interfaces.

### `GET /api/interfaces/{name}`

Returns one interface.

### `POST /api/interfaces/{name}/start`

Permission: `operate`

### `POST /api/interfaces/{name}/stop`

Permission: `operate`

### `POST /api/interfaces/{name}/restart`

Permission: `operate`

### `GET /api/interfaces/{name}/metrics`

Returns interface metrics.

---

## Peers

### `GET /api/peers`

Lists peers.

### `GET /api/peers/recent`

Lists recent peers.

### `GET /api/peers/{peer_hash}`

Returns peer detail by hash.

---

## Routes

### `GET /api/routes`

Lists routes.

### `GET /api/routes/summary`

Returns route summary data.

### `GET /api/routes/{destination_hash}`

Returns route detail.

---

## Announces

### `GET /api/announces`

Lists announces.

### `GET /api/announces/recent`

Lists recent announces.

### `GET /api/announces/{announce_id}`

Returns announce detail.

---

## Logs

### `GET /api/logs`

Returns log entries.

### `GET /api/logs/timeline`

Returns timeline-oriented log/event data.

---

## Diagnostics, Alerts, Audit, and Maintenance

### `GET /api/diagnostics`

Permission: `read`

Returns diagnostic summary data.

### `GET /api/alerts`

Permission: `read`

Returns current alerts.

### `GET /api/alerts/history`

Permission: `read`

Returns alert history.

### `GET /api/audit`

Permission: `read`

Returns audit/event records.

### `GET /api/maintenance`

Permission: `read`

Returns maintenance state.

### `POST /api/maintenance`

Permission: `maintenance`

Changes maintenance state or related workflow settings.

---

## Configuration

All config routes are mounted under `/api/config` and protected at the router level with `configure` permission.

### Read / inspect

- `GET /api/config`
- `GET /api/config/raw`

### Validate

- `POST /api/config/validate`
- `POST /api/config/validate-raw`

### Save

- `POST /api/config/save`
- `POST /api/config/save-raw`

### Revision history

- `GET /api/config/revisions`
- `GET /api/config/revisions/{revision_id}`
- `GET /api/config/revisions/{revision_id}/compare`
- `POST /api/config/revisions/{revision_id}/restore`

These endpoints support structured config workflows, raw TOML workflows, and revision restore operations.

---

## Backups

All backup routes are mounted under `/api/backup` and protected with `configure` permission.

### Endpoints

- `GET /api/backup`
- `GET /api/backup/detail`
- `POST /api/backup/export`
- `POST /api/backup/snapshot`
- `POST /api/backup/import`
- `GET /api/backup/snapshots`
- `POST /api/backup/prune`
- `GET /api/backup/dr`

These are used to inspect backup state, create exports and snapshots, prune retained snapshots, generate disaster-recovery guidance, and import backup archives.

---

## Plugins

### `GET /api/plugins`

Permission: `read`

Lists configured plugins and plugin metadata.

### `GET /api/plugins/catalog`

Permission: `read`

Lists installable catalog entries merged from plugin sources.

### `GET /api/plugins/history`

Permission: `read`

Returns recent plugin operation history.

### `GET /api/plugins/sources`

Permission: `read`

Lists plugin source catalogs and trust/signature metadata.

### `POST /api/plugins/sources/refresh`

Permission: `configure`

Refreshes plugin source catalogs.

### `GET /api/plugins/{name}`

Permission: `read`

Returns plugin detail.

### `POST /api/plugins/install`

Permission: `configure`

Installs a plugin from the catalog, resolving dependencies first.

### `POST /api/plugins/{name}`

Permission: `configure`

Updates plugin state, typically enable/disable style operations.

### `POST /api/plugins/{name}/refresh`

Permission: `configure`

Refreshes an installed plugin from the current catalog metadata.

### `DELETE /api/plugins/{name}`

Permission: `configure`

Uninstalls a plugin, optionally removing dependents.

---

## Services

### `GET /api/services`

Permission: `read`

Lists service-host style operational services.

### `GET /api/services/{name}`

Permission: `read`

Returns service detail.

### `POST /api/services/{name}`

Permission: `operate`

Runs a service action.

---

## Bridges

### `GET /api/bridges`

Permission: `read`

Lists bridge integrations.

### `GET /api/bridges/{name}`

Permission: `read`

Returns bridge detail including source trust, health checks, and recent operations.

### `POST /api/bridges/{name}`

Permission: `operate`

Runs a bridge action such as operational control or delivery testing.

---

## Fleet

Fleet routes live under `/api/fleet`.

### Read endpoints

Permission: `read`

- `GET /api/fleet/overview`
- `GET /api/fleet/nodes`
- `GET /api/fleet/nodes/{node_name}`
- `GET /api/fleet/groups`
- `GET /api/fleet/templates`
- `GET /api/fleet/tags`
- `GET /api/fleet/health`
- `GET /api/fleet/events`

### Mutating endpoints

Permission: `configure`

- `POST /api/fleet/nodes`
- `POST /api/fleet/groups`
- `POST /api/fleet/templates`

These endpoints support the early fleet inventory and grouping model in Hearth.

---

## Security

Security routes live under `/api/security`.

### Roles and users

Permission: `security`

- `GET /api/security/roles`
- `POST /api/security/roles`
- `POST /api/security/roles/{role_name}`
- `DELETE /api/security/roles/{role_name}`
- `GET /api/security/users`
- `POST /api/security/users`
- `POST /api/security/users/{username}`

### API tokens

Permission: `tokens`

- `GET /api/security/tokens`
- `POST /api/security/tokens`
- `POST /api/security/tokens/{token_name}`

These endpoints manage the operator-facing user, role, and token model used by the control plane.

---

## Metrics

### `GET /metrics`

Returns Prometheus-style plaintext metrics.

### `GET /api/metrics/summary`

Permission: `read`

Returns metric summary data for the Web/API surface.

---

## Topology and Network Intelligence

Topology routes live under `/api/topology`.

Permission: `read`

### Endpoints

- `GET /api/topology`
- `GET /api/topology/network-map`
- `GET /api/topology/route-heatmap`
- `GET /api/topology/critical-nodes`
- `GET /api/topology/insights`
- `GET /api/topology/path-changes`

These routes back the topology and network-understanding pages in the Web console.

---

## Rollouts, Remote Logs, and Upgrades

### Rollouts

- `GET /api/rollouts` — permission: `read`
- `POST /api/rollouts` — permission: `configure`

### Remote logs

- `GET /api/remote-logs` — permission: `read`
- `POST /api/remote-logs/ingest` — permission: `operate`
- `POST /api/remote-logs/sync` — permission: `operate`

### Upgrades

- `GET /api/upgrades` — permission: `read`
- `POST /api/upgrades` — permission: `operate`
- `POST /api/upgrades/execute` — permission: `operate`

These endpoints support operational workflows that go beyond the base runtime lifecycle.

---

## Web Surface Summary

In addition to the JSON API, Hearth exposes a large Web surface with pages including:

- dashboard
- interfaces
- peers
- routes
- announces
- logs
- config and config history
- backup
- system and maintenance
- users, roles, tokens, security, and audit
- plugins and plugin sources
- services and bridges
- fleet and topology pages
- metrics, diagnostics, alerts, rollout, upgrade, and remote logs

The Web surface is backed by the same application context and services as the API.

---

## Practical Examples

### Example: authenticated node status request

```bash
curl -H "X-Hearth-Token: <token>" http://127.0.0.1:8480/api/node/status
```

### Example: list plugins

```bash
curl -H "Authorization: Bearer <token>" http://127.0.0.1:8480/api/plugins
```

### Example: fetch topology summary

```bash
curl -H "X-Hearth-Token: <token>" http://127.0.0.1:8480/api/topology
```

---

## Summary

Hearth's API is not just a thin status endpoint layer. It is the programmatic surface of a broader node control plane covering runtime operations, configuration, recovery, security, extensions, and early multi-node workflows.
