# Hearth 文档导航

[English](README.md)

如果你已经看完 `README_CN.md`，并准备进一步理解、部署或集成 Hearth，可以从这里进入不同主题的文档。

先用一句话统一上下文：

- **Reticulum** 是去中心化网络栈
- **Hearth** 是运行和管理个人 Reticulum 基础设施节点的控制面
- 这个目录中的文档，解释的是如何启动、部署、配置、保护并理解这个节点控制面

## 文档列表

- [`getting-started.zh-CN.md`](getting-started.zh-CN.md)
  - 中文版本地快速开始，适合第一次把 Hearth 跑起来，并了解当前新增的角色、插件、备份、远程日志等运维页面。

- [`network-model.zh-CN.md`](network-model.zh-CN.md)
  - 专门解释“本地节点如何接入 Hearth 管理的节点”以及“该节点如何接入更大的 Reticulum 网络”。

- [`deployment.zh-CN.md`](deployment.zh-CN.md)
  - 中文部署指南，覆盖本地运行、systemd、Docker / Compose、部署产物生成、托管 `rnsd` 与多节点管理地址规划。

- [`security.zh-CN.md`](security.zh-CN.md)
  - 中文安全指南，说明认证、权限、Token、访问暴露、浏览器安全头，以及插件源签名信任模型。

- [`config-reference.zh-CN.md`](config-reference.zh-CN.md)
  - 中文配置参考，说明 TOML 配置模型、托管 runtime、监控、接口、插件、插件源、自定义角色与派生路径。

- [`api-reference.zh-CN.md`](api-reference.zh-CN.md)
  - 中文 API 参考，说明认证方式、权限模型和当前主要接口分组，包括插件生命周期、备份快照、远程日志同步、升级执行等接口。

- [`architecture-v0.1.md`](architecture-v0.1.md)
  - 当前架构说明，重点是控制面、运行时边界、服务图与数据流。

## 建议阅读顺序

如果你是第一次接触 Hearth：

1. 先看 [`../README_CN.md`](../README_CN.md)
2. 如果你还不清楚“节点怎么接进来、网络怎么连出去”，先看 [`network-model.zh-CN.md`](network-model.zh-CN.md)
3. 然后看 [`getting-started.zh-CN.md`](getting-started.zh-CN.md)
4. 如果要长期运行，再看 [`deployment.zh-CN.md`](deployment.zh-CN.md)
5. 在暴露到 localhost / 可信 LAN 之外前，先看 [`security.zh-CN.md`](security.zh-CN.md)
6. 需要改配置时看 [`config-reference.zh-CN.md`](config-reference.zh-CN.md)
7. 需要接 API 时看 [`api-reference.zh-CN.md`](api-reference.zh-CN.md)
8. 需要理解内部结构时，再看 [`architecture-v0.1.md`](architecture-v0.1.md)

## 说明

当前最常用的使用路径已经有完整中文文档，包括：

- 快速开始
- 接入模型
- 部署
- 安全
- 配置参考
- API 参考

目前仍以英文为主的，主要是更偏内部实现的架构说明文档。
