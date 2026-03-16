# Hearth Security Guide

[Chinese (Simplified)](security.zh-CN.md)

This document explains the current security model of Hearth as implemented in the repository today.

The most important context is this:

- **Reticulum** is the underlying networking stack
- **Hearth** is the control plane around a Personal Reticulum Transport Node
- Hearth security therefore focuses on protecting the **management surface of the node**: Web, API, authentication, authorization, network exposure, and supply-chain trust for extensions

It does **not** attempt to replace every trust and security decision inside Reticulum itself.

---

## Security Goals

Hearth's current security model is designed to protect a node operator from common control-plane risks, especially in local-first or small-network deployments.

The main goals are:

- require authentication for sensitive control-plane access
- separate read access from operational and security-sensitive actions
- limit network exposure by default
- reduce browser attack surface with security headers
- support auditable user and token management
- apply trust checks to plugin source catalogs and signed manifests

---

## Current Security Layers

Hearth currently applies security in several layers.

### 1. Network exposure controls

Requests are classified by client address as:

- loopback
- LAN/private
- public

Access is then filtered by:

- `security.allow_lan`
- `security.allow_wan`

Loopback access is always allowed.

This means Hearth is local-first by design.

### 2. Authentication

When `web.auth_mode != "none"`, Hearth requires token-based authentication for protected routes.

Accepted token sources are:

- `Authorization: Bearer <token>`
- `X-Hearth-Token: <token>`
- `?token=<token>` query parameter
- `hearth_token` cookie

### 3. Authorization

Route protection is permission-based. Roles and token scopes determine whether the authenticated principal may perform the requested action.

### 4. Browser hardening

Hearth applies a set of security headers centrally, including:

- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Referrer-Policy: same-origin`
- `Permissions-Policy`
- a restrictive `Content-Security-Policy`

### 5. Supply-chain trust for plugin sources

Plugin source catalogs can carry trust metadata and can be validated with digest and **Ed25519 signature verification**.

---

## Authentication Model

### `admin_token`

The most important built-in credential is:

- `security.admin_token`

If the presented token matches this value exactly, Hearth authenticates the caller as the built-in `admin` subject with the `owner` role.

### Web login

The Web UI includes a token-based login form.

A successful login stores the token in the `hearth_token` cookie.

Current cookie characteristics:

- `HttpOnly`
- `SameSite=Strict`
- path `/`

### API tokens

In addition to the built-in admin token, Hearth supports database-backed API tokens.

Each API token can have:

- a token name
- an optional owner user
- a role
- optional scopes
- an enabled/disabled state
- an optional expiry

Raw token secrets are not stored in plaintext. Hearth stores a SHA-256 hash of the token secret in the database.

### Token expiration and owner checks

When a database-backed token is used:

- the token must be enabled
- the token must not be expired
- if it is bound to a user, that user must still exist and be enabled

---

## Roles and Permissions

Hearth currently includes these built-in roles:

- `owner`
- `admin`
- `operator`
- `viewer`
- `service_manager`

### Permission vocabulary

Current route-level permissions include:

- `read`
- `operate`
- `configure`
- `security`
- `tokens`
- `maintenance`

### Practical meaning

- `read`: inspect dashboards, logs, routes, peers, and related observability
- `operate`: start/stop/restart runtime, interfaces, bridges, and service actions
- `configure`: modify config, plugins, fleet state, and related operational settings
- `security`: manage users and roles
- `tokens`: manage API tokens
- `maintenance`: switch maintenance state and perform maintenance-oriented workflows

### Scopes

API tokens can also carry scopes.

Authorization currently works in two steps:

1. the principal's role must allow the requested permission
2. the token's scopes must either contain `*` or explicitly include that permission

This means scopes can be used to further restrict what a token may do, even when its role is broader.

---

## Users and Tokens

### Users

Hearth supports a user inventory managed through the security service and security API routes.

Users currently provide:

- username
- display name
- role
- enabled/disabled state
- token ownership relationship

The built-in `admin` user is special:

- it is always present conceptually
- it maps to the configured `admin_token`
- it cannot be disabled like a regular user

### Tokens

Token creation is designed for operator workflows.

A created token returns the raw secret once. After that, operators should treat it as a credential that must be stored securely.

---

## Network Exposure Model

### Default intent

The default security posture is:

- local or LAN-friendly
- not WAN-open by accident

### `allow_lan`

If enabled, clients from private/local network ranges may connect.

### `allow_wan`

If enabled, public network clients may connect.

This should be treated as a deliberate exposure decision.

### Important note about reverse proxies

Current host classification is based on the request client's actual socket address. If you deploy behind a reverse proxy, review your proxy design carefully and do not assume public exposure controls behave the same as a direct bind.

---

## Browser and Session Security

The Web UI is token-based rather than password-based.

### Strengths of the current model

- no password database for the Web UI itself
- login cookie is `HttpOnly`
- `SameSite=Strict` reduces cross-site cookie sending
- restrictive CSP and frame denial reduce browser abuse surface

### Current limitations

- the cookie is not marked `Secure` by default
- query-string token auth is accepted
- the current Web auth model is better suited to local-first or carefully proxied deployments than to casual direct Internet exposure

If you expose Hearth beyond localhost or a trusted LAN, prefer to place it behind HTTPS and a deliberate reverse-proxy policy.

---

## Audit and Security Events

Hearth records security-relevant events in the database, including examples such as:

- login succeeded
- login failed
- logout
- user created
- user updated
- token created
- token updated

This gives operators a basic audit trail for management actions.

---

## Plugin Source Trust and Signatures

Security in Hearth also includes extension trust.

### Built-in trust states

Plugin sources use signature states such as:

- `trusted`
- `verified`
- `invalid`
- `missing`
- `not_required`

### Supported trust inputs

A plugin source may include:

- `trusted`
- `expected_sha256`
- `public_key`
- `signature`
- `signature_algorithm`
- `signature_required`

### Ed25519 verification

Signed manifests can be validated with **Ed25519 public-key signatures**.

This is the stronger trust path and should be preferred over digest-only verification when available.

### Practical operator meaning

When using third-party plugin catalogs, do not treat all sources equally. Review:

- whether the source is trusted
- whether the manifest was verified
- whether a required signature is missing or invalid
- whether the configured public key matches the manifest's public key

---

## Recommended Hardening Checklist

Before exposing Hearth outside a development machine, do at least the following:

- change `security.admin_token`
- keep `web.auth_mode` enabled
- keep `allow_wan = false` unless intentionally required
- bind to the smallest necessary interface
- use HTTPS if traffic leaves localhost or a trusted private network
- create limited API tokens instead of reusing the built-in admin token everywhere
- use narrower scopes for automation tokens
- review plugin source trust before enabling external extensions
- verify filesystem permissions for config, identity, and `data_dir`
- review audit logs after security changes

---

## Current Security Boundaries

Hearth already includes meaningful control-plane security, but it is important to understand the present limits honestly.

### Implemented today

- token-based authentication
- role and scope authorization
- user and token management
- LAN/WAN exposure controls
- browser security headers
- audit events
- plugin source trust metadata and Ed25519 signature verification

### Still worth treating carefully

- direct public exposure without a reverse proxy or TLS
- long-term reuse of the built-in admin token
- relying on query-string token auth in shared environments
- assuming Hearth replaces deeper network-layer security decisions in Reticulum

---

## Summary

Hearth security is about protecting the node's management surface.

Today, that includes:

- who can reach the node
- how they authenticate
- what they are allowed to do
- what the browser may do
- whether extension sources are trusted

For most real deployments, the safest mindset is: keep Hearth local-first by default, expose it deliberately, and treat operator credentials and plugin trust with the same care you would give any infrastructure control plane.
