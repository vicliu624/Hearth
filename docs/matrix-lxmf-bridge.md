# Matrix ↔ LXMF bridge

The optional `matrix_bridge` extra provides a separate worker connecting an existing
shared Reticulum instance to one encrypted Matrix room. It does not start a second
Reticulum daemon. Matrix-nio 0.26.0 (with its E2EE backend) and LXMF 1.1.1 are pinned.

## Chat

- Send `!lxmf <32-character LXMF address> <text>` to contact a recipient.
- Reply to a bridged LXMF message to answer its sender. Reply quotations are removed.
- `!address` returns the bridge's LXMF address; `!help` shows these instructions.
- Only configured Matrix `allowed_users` can issue messages or commands.
- Text is supported, up to 8192 UTF-8 bytes. Attachments are not forwarded.

Both Matrix and LXMF legs are encrypted. The bridge terminates encryption and
re-encrypts locally; it is a trusted endpoint, not end-to-end encryption across both
protocols. Matrix device encryption keys are accepted for room members without
marking those devices verified. Use a private, invite-only room with trusted members.

The service uses normal LXMF delivery announces, without geographic metadata or
Reticulum public interface-discovery advertisements. It does not change map privacy
settings or publish an entry in a public directory.

## Runtime and configuration

Install `.[matrix_bridge]` in `/opt/hearth/matrix-bridge-venv`, and adapt the user/group
in `packaging/systemd/hearth-matrix-bridge.service` to the installation's service user.
The worker imports the deployed source at `/opt/hearth/current/src`. Restart the
bridge service after deploying code changes; restarting the management service alone
does not interrupt the bridge.

Credentials are a separate JSON file, mode 0600, in a mode 0700 service directory:
`/var/lib/hearth/matrix-bridge/credentials.json`. Required fields are `homeserver`,
`user_id`, `device_id`, `access_token`, `room_id`, `allowed_users`, `started_at`
(first permitted Matrix event timestamp in milliseconds), and `reticulum_config`.
`hearth_config` may point to the active Hearth TOML; the worker then observes the
`matrix_bridge` plugin's enabled flag. Never put access tokens in plugin metadata:
that metadata is exposed to authorized management readers.

Declare a plugin named `matrix_bridge`, type `bridge`, with config `transport =
"matrix"` and `mode = "lxmf"`. Its public config may contain the homeserver URL and
room ID, but no credentials. The bridge page reads a live worker heartbeat, checks
process creation time, and shows the LXMF address and queue counts. Controls pause
or resume forwarding, enqueue an encrypted Matrix test, and retry failed messages.
A queued test is not reported as delivered until the worker confirms the Matrix send.

Pausing retains queued messages. A transfer already submitted to LXMF may finish.
Credentials, LXMF identity, encrypted-client key store, and SQLite queue are persistent.
Protect this entire service directory in backups; its queue contains local plaintext.
Do not rotate the LXMF identity or Matrix device ID on ordinary restarts.

## Delivery and recovery

The SQLite queue deduplicates incoming Matrix event IDs and LXMF message hashes.
Matrix retries reuse a stable transaction ID; LXMF retries reuse a stable payload
 timestamp. Pending jobs survive restart, as does the reply-to-sender mapping.
Failed sends retry with bounded backoff; after five attempts they remain visible as
failed and can be retried by an operator. A remote destination must become reachable
for delivery to complete. There is no global exactly-once guarantee across crashes
or different client implementations.

Matrix sync cursors advance only after callbacks enqueue work. Limited timelines
are backfilled, with a bounded history limit; a recovery error keeps the old cursor.
Encrypted events awaiting keys are retained and retried when keys become available.
No message text, access token, or password is included in the public heartbeat.

Validation includes queue/routing unit tests and an isolated live test with two
new Matrix accounts, an encrypted room and a separate local LXMF endpoint. It checks
both directions, reply routing, persistent identity and no replay after restart.
Validation accounts are deactivated afterwards. Do not run integration experiments
using an existing human account's credentials.
