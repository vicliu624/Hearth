# Hearth Configuration Reference

[Chinese (Simplified)](config-reference.zh-CN.md)

Hearth uses a TOML configuration file.

The easiest starting point is `examples/hearth.toml`, which is designed for local development and uses the mock runtime backend.

This file does more than set a few web-server values. It defines how Hearth operates as a **Personal Reticulum Transport Node control plane**, including:

- where node data is stored
- how the runtime is launched
- how the Web/API control surface is exposed
- what security rules apply
- how monitoring, alerts, interfaces, plugins, and plugin sources behave

If you are new to the project, the most useful mental model is:

- **Reticulum** is the networking stack
- **Hearth** is the node operations layer around that stack
- this config file tells Hearth how to run and manage that node

---

## Loading Behavior

Hearth configuration is loaded through `load_settings()` in `src/hearth/core/config.py`.

Important behaviors:

- if no path is provided, Hearth uses built-in defaults
- if a path is provided but the file does not exist, Hearth still returns defaults and remembers that path for future saves
- relative paths are resolved relative to the configuration file location
- runtime and backup directories are created automatically when needed

This means a missing config file is not automatically fatal during development.

---

## Top-Level Sections

Hearth currently recognizes these top-level sections:

- `[system]`
- `[reticulum]`
- `[web]`
- `[security]`
- `[monitor]`
- `[alerts]`
- `[[interfaces]]`
- `[[plugins]]`
- `[[plugin_sources]]`

Unknown top-level fields are ignored by the root settings model.

---

## `[system]`

General node-level settings.

### Fields

- `node_name` (`str`, default: `"hearth-node"`)
  - Human-readable node name shown across the UI and status outputs.

- `data_dir` (`Path`, default: `"./.data"`)
  - Root directory for local runtime files, database, logs, and backups.

- `log_level` (`str`, default: `"INFO"`)
  - Logging level used when launching the API server entrypoint.

- `timezone` (`str`, default: `"UTC"`)
  - Display-oriented timezone identifier.

---

## `[reticulum]`

Controls the managed Reticulum runtime boundary.

### Fields

- `enabled` (`bool`, default: `true`)
  - Enables the runtime layer.

- `config_path` (`Path`, default: `"./reticulum-config"`)
  - Directory holding Reticulum-related configuration files.

- `identity_path` (`Path`, default: `"./.data/identity"`)
  - Path to the identity file managed by Hearth.

- `auto_start` (`bool`, default: `true`)
  - Starts the runtime automatically during app startup.

- `backend` (`"mock_process" | "external_process" | "managed_rnsd"`, default: `"mock_process"`)
  - Selects the runtime backend implementation.

- `command` (`list[str]`, default: `[]`)
  - Command used when `backend = "external_process"`.

- `transport_enabled` (`bool`, default: `true`)
  - Enables Reticulum transport mode when rendering a managed runtime config.

- `shared_instance` (`bool`, default: `true`)
  - Controls the shared-instance flag in the managed runtime config.

- `loglevel` (`int`, default: `4`)
  - Reticulum-side log level used when the managed runtime config is rendered.

- `render_managed_config` (`bool`, default: `true`)
  - When enabled, Hearth writes a managed Reticulum config file before starting `managed_rnsd`.

- `managed_command` (`str | null`, default: `null`)
  - Override command used for `managed_rnsd`, for example `rnsd` or a wrapper script.

- `heartbeat_interval_sec` (`int`, default: `2`)
  - Heartbeat interval expected from the runtime layer.

- `health_timeout_sec` (`int`, default: `10`)
  - Timeout used by health evaluation logic.

- `shutdown_timeout_sec` (`int`, default: `5`)
  - Graceful stop timeout for runtime shutdown.

### Notes

- `mock_process` is still the easiest path when you only want to evaluate the control plane.
- `external_process` is the generic path toward supervising an arbitrary runtime command.
- `managed_rnsd` is the productized path for letting Hearth render config and supervise a real `rnsd` process.

---

## `[web]`

Controls the built-in API and Web console.

### Fields

- `enabled` (`bool`, default: `true`)
  - Enables Web/API serving.

- `host` (`str`, default: `"127.0.0.1"`)
  - Bind host used by the API server.

- `port` (`int`, default: `8480`)
  - Bind port used by the API server.

- `auth_mode` (`str`, default: `"local_token"`)
  - Authentication mode. Current code treats any value other than `"none"` as auth enabled.

### Recommendation

For local development, keep:

- `host = "127.0.0.1"`
- `auth_mode = "local_token"`

---

## `[security]`

Controls access to the control plane.

### Fields

- `admin_token` (`str`, default: `"change-me"`)
  - Primary administrative token used for local login and authenticated API access.

- `allow_lan` (`bool`, default: `true`)
  - Allows requests from private LAN addresses.

- `allow_wan` (`bool`, default: `false`)
  - Allows requests from public network addresses.

### Notes

- Loopback access is always allowed.
- Before any shared deployment, change the default `admin_token`.
- `allow_wan = true` should only be enabled intentionally and with proper network controls.

---

## `[monitor]`

Controls health checks, metrics refresh, and watchdog behavior.

### Fields

- `health_check_interval_sec` (`int`, default: `15`)
  - Interval between watchdog/health runs.

- `metrics_refresh_sec` (`int`, default: `10`)
  - Interval for periodic node state refresh.

- `watchdog_enabled` (`bool`, default: `true`)
  - Enables the watchdog background job.

- `auto_restart_runtime` (`bool`, default: `true`)
  - Allows watchdog logic to restart the runtime automatically.

- `auto_restart_interface` (`bool`, default: `true`)
  - Allows watchdog logic to restart unhealthy interfaces automatically.

- `restart_cooldown_sec` (`int`, default: `30`)
  - Cooldown between automated restart attempts.

---

## `[alerts]`

Controls outbound alert delivery behavior.

### Fields

- `webhook_enabled` (`bool`, default: `false`)
  - Enables alert webhook delivery.

- `webhook_url` (`str | null`, default: `null`)
  - Outbound webhook URL.

- `include_resolved` (`bool`, default: `true`)
  - Includes resolved alerts in delivery/sync flows.

- `delivery_timeout_sec` (`int`, default: `5`)
  - Timeout for webhook delivery attempts.

- `sync_interval_sec` (`int`, default: `30`)
  - Interval used by the alert refresh job.

---

## `[[interfaces]]`

Declares node interfaces.

### Common fields

- `name` (`str`, required)
- `type` (`str`, required)
- `enabled` (`bool`, default: `true`)
- `role` (`str | null`, default: `null`)

### Extra fields

Interface entries allow extra keys, which are passed through for type-specific behavior.

Examples:

- TCP-style fields such as `host` and `port`
- serial/radio fields such as `device` and `baudrate`
- local-network fields such as `devices`, `discovery_port`, and `data_port`
- custom per-driver extensions

### Example

```toml
[[interfaces]]
name = "tcp_backbone"
type = "tcp"
enabled = true
role = "uplink"
host = "backbone.example.org"
port = 4242
```

---

## `[[plugins]]`

Declares configured plugins.

### Common fields

- `name` (`str`, required)
- `enabled` (`bool`, default: `false`)

### Extra fields

Plugin entries also allow extra keys so plugin-specific options can be attached without changing the root config schema.

Current operator-facing plugin fields commonly include:

- `source`
- `version`
- `type`
- `compatibility`
- `description`
- `permissions`
- `depends_on`
- `config`
- `sandbox_boundary`

### Example

```toml
[[plugins]]
name = "example_plugin"
enabled = false
source = "community"
version = "1.0.0"
type = "bridge"
permissions = ["read", "operate"]
depends_on = ["metrics_exporter"]
```

---

## `[[roles]]`

Declares custom RBAC roles that extend the built-in role set.

### Fields

- `name` (`str`, required)
- `label` (`str | null`)
- `description` (`str | null`)
- `permissions` (`list[str]`, required)

### Notes

- Built-in roles such as `owner`, `admin`, `operator`, `viewer`, and `service_manager` still exist automatically.
- Custom roles are persisted back into the main Hearth config when created through the Web UI, CLI, or API.

### Example

```toml
[[roles]]
name = "field_ops"
label = "Field Ops"
description = "Operate interfaces and maintenance windows"
permissions = ["read", "operate", "maintenance"]
```

---

## `[[plugin_sources]]`

Declares plugin source catalogs and trust metadata.

### Fields

- `name` (`str`, required)
- `index_url` (`str`, required)
- `label` (`str | null`)
- `description` (`str | null`)
- `trusted` (`bool`, default: `false`)
- `expected_sha256` (`str | null`)
- `public_key` (`str | null`)
- `signature` (`str | null`)
- `signature_algorithm` (`str | null`)
- `signature_required` (`bool`, default: `false`)

### Notes

- Hearth currently supports trust metadata for plugin catalogs.
- Signed plugin source manifests can be verified with **Ed25519 public-key signatures**.
- `expected_sha256` can still be stored as metadata, but signature verification is the stronger trust mechanism.

### Example

```toml
[[plugin_sources]]
name = "community"
index_url = "https://example.org/hearth/plugins/index.json"
label = "Community Catalog"
description = "Community-maintained plugins and bridge integrations"
trusted = true
public_key = "ed25519:0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
signature = "ed25519:abcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdef"
signature_algorithm = "ed25519"
signature_required = true
```

---

## Derived Paths

Several important runtime paths are derived automatically from configuration:

- database: `data_dir/hearth.db`
- runtime dir: `data_dir/runtime/`
- runtime state: `data_dir/runtime/reticulum-state.json`
- runtime observations: `data_dir/runtime/reticulum-observations.json`
- managed runtime config: `data_dir/runtime/reticulum-generated.conf`
- runtime pid: `data_dir/runtime/reticulum.pid`
- runtime stdout log: `data_dir/runtime/reticulum.stdout.log`
- runtime stderr log: `data_dir/runtime/reticulum.stderr.log`
- plugin runtime dir: `data_dir/plugins/`
- plugin state file: `data_dir/plugins/installed-plugins.json`
- remote logs dir: `data_dir/remote-logs/`
- backups dir: `data_dir/backups/`
- backup snapshot index: `data_dir/backups/snapshots.json`

These are not set directly in the TOML file; they are derived from `data_dir` and other base settings.

---

## Validation and Editing Workflows

Hearth includes config-management workflows in both Web and API surfaces.

Current API endpoints include:

- `GET /api/config`
- `GET /api/config/raw`
- `POST /api/config/validate`
- `POST /api/config/validate-raw`
- `POST /api/config/save`
- `POST /api/config/save-raw`
- `GET /api/config/revisions`
- `GET /api/config/revisions/{revision_id}`
- `GET /api/config/revisions/{revision_id}/compare`
- `POST /api/config/revisions/{revision_id}/restore`

This allows configuration to function as an operator workflow rather than only a local file-editing task.

---

## Example Development Config

The repository includes a minimal local development config at `examples/hearth.toml`.

It is suitable for:

- local UI development
- CLI exploration
- API exploration
- validating the Hearth control plane without a real external runtime first

It is **not** suitable to expose unchanged on a shared or public network.

---

## Operational Recommendations

For safe local development:

- keep `host = "127.0.0.1"`
- keep `auth_mode = "local_token"`
- change `admin_token`
- review all example interface endpoints
- keep `allow_wan = false` unless you explicitly intend remote exposure

For packaging or production-style deployment:

- set stable absolute paths where appropriate
- manage the config file location intentionally
- back up `data_dir`, the database, and identity material together
- test restore workflows before relying on the node operationally

---

## Summary

Hearth configuration is intentionally simple at the top level, but it drives a wide operational surface: runtime control, Web/API access, watchdog behavior, alert delivery, plugin trust, and persistent node state.
