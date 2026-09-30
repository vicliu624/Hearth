# Installing and operating v0.2

## Installation

Python 3.12 or newer is required. The wheel contains the built web console and
local assets; Node.js is needed only when rebuilding the frontend from source.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -c requirements-lock.txt '.[reticulum]'
```

`requirements-lock.txt` is a constraints file. Use `-c`, not `-r`, so development
and platform-specific packages are only installed when their extras require them.

Keep node configuration and data outside the application release directory. Set
`HEARTH_CONFIG` to the absolute configuration path. Generate a unique admin token
for a new installation; never replace an existing installation's credentials as
part of an application upgrade.

## Configuration workflow

The configured TOML file is the saved draft. The adjacent `hearth.active.toml`
records the active version. Saving through the console, API, or CLI does not
partially change the running services.

```sh
hearth config save-raw candidate.toml --config /etc/hearth/hearth.toml
hearth config apply --config /etc/hearth/hearth.toml
```

The API equivalents are `POST /api/config/save-raw` and `POST /api/config/apply`.
`GET /api/config/status` returns saved and active versions plus the pending flag.
An apply rebuilds the affected services and verifies runtime health. Failure
restores the previous active configuration.

Deployment paths and the Web listener are not moved by live apply. To migrate
those, stop the node and management service, back up configuration and data, move
the deployment explicitly, and update both saved and active configuration before
starting the service at its new location.

## Runtime ownership

Web/API and CLI commands share an OS-backed operation lock. Stale controllers
cannot restart the runtime using an old active configuration. An explicit node
stop persists across management-service restarts and watchdog checks.

Systemd uses `KillMode=process`, and the Web lifespan does not stop Reticulum.
Consequently, `systemctl restart hearth` restarts management only. To stop
forwarding as well, stop the node explicitly before stopping the service:

```sh
hearth stop --config /etc/hearth/hearth.toml
sudo systemctl stop hearth
```

Managed interface start/stop/restart currently applies configuration by restarting
the entire Reticulum runtime. The console explains this interruption before the
operation. External backends without verified control report unsupported.

## Backup and restore

Backups contain saved and active configuration, a consistent SQLite snapshot,
identity data, interface desired states, and the actual Reticulum transport
identity when present. Process ownership/PIDs are never restored from an archive.
Restore keeps the target deployment paths and the target's previous desired node
state, validates inputs before writes, and rolls back partial restoration or
service-activation failure.

## Observability and compatibility

Real backends do not generate mock data to fill a collection failure. The current
`rnstatus` / `rnpath` integration provides interfaces and paths, but does not yet
subscribe to live announces or provide genuine peer discovery. Those limitations
are explicit in the console.

Traffic counters and Prometheus metric names now use bytes instead of the
incorrect packet terminology. Update consumers of `rx_packets` / `tx_packets` to
`rx_bytes` / `tx_bytes`, and use `hearth_interface_rx_bytes_total` /
`hearth_interface_tx_bytes_total` in Prometheus queries. Historical SQLite column
names are retained internally so existing databases remain readable.
