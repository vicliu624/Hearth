# Hearth Documentation

[简体中文](README.zh-CN.md)

This directory contains the primary project documentation for Hearth.

If you are arriving here for the first time and still are not sure what Hearth is, start with this framing:

- **Reticulum** is a decentralized networking stack
- **Hearth** is the software used to run and manage your own long-lived infrastructure node inside that network
- the documents in this directory explain how to run, configure, understand, and integrate that node control plane

## Documents

- [`getting-started.md`](getting-started.md)
  - Fastest path to run Hearth locally with either `managed_rnsd` or the fallback mock runtime, plus a first tour of the new operator pages.

- [`network-model.md`](network-model.md)
  - Explains how local nodes attach to the node Hearth manages, and how that node reaches the wider Reticulum network.

- [`getting-started.zh-CN.md`](getting-started.zh-CN.md)
  - Chinese quick-start guide for first-time local setup and bring-up.

- [`deployment.md`](deployment.md)
  - Practical deployment guide for local runs, systemd, Docker / Compose, generated deployment bundles, managed `rnsd`, and multi-node management URLs.

- [`deployment.zh-CN.md`](deployment.zh-CN.md)
  - Chinese deployment guide for local runs, systemd, Docker / Compose, and generated deployment bundles.

- [`security.md`](security.md)
  - Current authentication, authorization, token, exposure, browser, audit, and plugin-signature security model.

- [`security.zh-CN.md`](security.zh-CN.md)
  - Chinese security guide for the current control-plane protection model.

- [`config-reference.md`](config-reference.md)
  - Complete configuration reference for the TOML settings model, including managed runtime settings, security, monitoring, interfaces, plugins, plugin sources, and custom roles.

- [`config-reference.zh-CN.md`](config-reference.zh-CN.md)
  - Chinese configuration reference for the same TOML model.

- [`api-reference.md`](api-reference.md)
  - Current REST API surface, authentication methods, permissions, and endpoint groups, including plugin lifecycle, backup snapshot, remote-log sync, and upgrade execution routes.

- [`api-reference.zh-CN.md`](api-reference.zh-CN.md)
  - Chinese API reference for the current REST surface.

- [`architecture-v0.1.md`](architecture-v0.1.md)
  - Current control-plane architecture, service graph, startup flow, persistence, and runtime boundaries.

## Recommended Reading Order

If you are new to Hearth:

1. Start with [`../README.md`](../README.md) or [`../README_CN.md`](../README_CN.md)
2. If you are still unclear about how nodes attach and how the network path works, read [`network-model.md`](network-model.md) or [`network-model.zh-CN.md`](network-model.zh-CN.md)
3. Read [`getting-started.md`](getting-started.md) or [`getting-started.zh-CN.md`](getting-started.zh-CN.md) depending on your preferred language
4. Read [`deployment.md`](deployment.md) or [`deployment.zh-CN.md`](deployment.zh-CN.md) if you want to keep Hearth running beyond local evaluation
5. Read [`security.md`](security.md) or [`security.zh-CN.md`](security.zh-CN.md) before exposing Hearth beyond localhost or a trusted LAN
6. Review [`config-reference.md`](config-reference.md) or [`config-reference.zh-CN.md`](config-reference.zh-CN.md)
7. Use [`api-reference.md`](api-reference.md), [`api-reference.zh-CN.md`](api-reference.zh-CN.md), and [`architecture-v0.1.md`](architecture-v0.1.md) as deeper references

## Scope

These docs describe the current implementation in the repository today.

Hearth is still evolving, so some documents describe both:

- what is already implemented
- what the current architecture is clearly preparing for next
