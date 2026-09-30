# Changelog

## Unreleased

- Add an interactive local topology graph with pan, zoom, connection filtering and path details; distinguish observed interface relationships from inferred forwarding relationships.
- Preserve distinct accepted TCP connections and count all paths in topology summaries instead of truncating at 300. Explain unsupported peer observation and link the peer page to the graph.

## 0.2.0 — 2026-09-30

### Runtime reliability

- Real backends no longer fall back to simulated peers, paths, or announces when collection fails or returns an empty result. Path snapshots are no longer presented as received announces. Collection failures and unsupported announce/peer observation are explicit.
- Interface operations on managed Reticulum apply the generated configuration, restart the node, and verify the actual interface state. Failed verification restores the previous interface configuration. Other real backends report unsupported control instead of changing an in-memory status.
- Persist the operator's desired node and interface states. Automatic recovery respects intentional stops, including after restarting the management service.
- Initialize the managed transport identity before launching observers, preventing first-start RPC authentication races between the daemon and status utilities.
- Serialize runtime, configuration, and backup operations across CLI and server processes. Check process identity as well as PID; handle Windows virtual-environment launchers and Linux zombie processes.
- Restarting the Web service leaves the managed runtime running. Systemd packaging uses `KillMode=process`; stop the node explicitly before host maintenance when forwarding must also stop.

### Configuration and recovery

- Separate saved drafts from active configuration. Add `GET /api/config/status`, `POST /api/config/apply`, and `hearth config apply`.
- Apply configuration by rebuilding the service graph, validating runtime health, and restoring the previous active configuration on failure. Other running contexts reload the active configuration.
- Role and plugin changes use explicit live-section updates and preserve unrelated pending configuration edits.
- Back up SQLite with its online backup API, including WAL contents. Restore validates archive entries, checksums, configuration, and database integrity before modifying the installation.
- Restore under an exclusive maintenance boundary with rollback on partial write failure. Preserve target-machine deployment paths and include the actual Reticulum transport identity when present.

### Performance

- Serve pages from background observations rather than running `rnstatus` and `rnpath` for each request. Coalesce concurrent cold reads and collect status and paths through a read-only shared-instance RPC observer that cannot start a competing Reticulum instance.
- Remove observation writes from read-only views and avoid rewriting unchanged path and announce snapshots. Add indexes for event and metric history queries.
- Keep failed scheduled jobs alive for subsequent retries. Prevent alerts from recursively generating alerts about their own transitions.
- Compress responses, split frontend vendor bundles, and ship local font subsets with an on-demand full-font fallback.

### Interface and localization

- Rebuild the console with Animal Island UI 2.0.0 and React 19, including data-driven overview, interface, metrics, health, configuration, and sign-in pages.
- Use the library's cards, ribbon titles, patterned backgrounds, controls, tables, tabs, drawers, game-style confirmation dialogs, notifications, progress indicators, image frames, and Naive Icons. Preserve existing management workflows and permission checks.
- Include official scene artwork and Nunito / Noto Sans SC fonts, responsive navigation, appearance preferences, and reduced-motion support.
- Review Chinese and English copy directly against product behavior. Repair 260 corrupted Chinese strings, replace untranslated template text, and share one localization catalog between Python and React.
- Standardize operational terms and distinguish saved configuration from active configuration, observation from online state, and path snapshots from announces. Add catalog, placeholder, and key-reference regression checks.
- Do not infer network failure or emit a topology score when peer observations are unsupported. Keep removed-interface history out of the current topology and exclude failed collections from traffic samples.
- Adapt upstream notification portals for React 19 and localize component-level labels and clock dates.
- Respect role and token permissions in native controls, present browser-friendly authentication errors, and support runtime interface names containing slashes.

### Dependencies and compatibility

- Update FastAPI, Jinja2, Pydantic, SQLAlchemy, Tomli-W, Typer, Uvicorn, HTTPX, and pytest; add psutil and the optional Reticulum 1.5.5 extra.
- The default Linux installer installs the Reticulum extra and uses the real backend for new auto-mode deployments. Explicit mock deployments and existing configuration remain available.
- Add Python dependency constraints and a frontend package lock for reproducible builds.
- Correct traffic counter names to `rx_bytes` / `tx_bytes` and speed fields to `rx_bytes_per_second` / `tx_bytes_per_second`. Prometheus names are now `hearth_interface_rx_bytes_total` / `hearth_interface_tx_bytes_total`. Existing SQLite column names are retained so historical data remains readable.
- Existing installations keep an adjacent `hearth.active.toml` containing the active configuration. Saving alone does not activate changes. Moving deployment paths or changing the listener requires an offline migration.

## 0.1.0

Initial control-plane implementation with runtime supervision, Web/API/CLI management,
configuration revisions, backups, security, and early fleet and extension workflows.
