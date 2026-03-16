# Hearth 配置参考

[Docs](README.zh-CN.md) / [English](config-reference.md)

Hearth 使用 TOML 配置文件。

最简单的起点是 `examples/hearth.toml`，它面向本地开发，默认使用 mock runtime backend。

这份文件不只是设置几个 Web 服务参数，它实际上定义了 Hearth 这个 **Personal Reticulum Transport Node 控制面** 如何运行，例如：

- 节点数据存放在哪里
- runtime 如何启动
- Web / API 控制面如何暴露
- 哪些安全规则会生效
- 监控、告警、接口、插件与插件源如何工作

如果你是第一次接触这个项目，最有帮助的理解方式是：

- **Reticulum** 是网络栈
- **Hearth** 是围绕这个网络栈的节点运维层
- 这份配置文件决定了 Hearth 如何运行并管理这个节点

---

## 加载行为

Hearth 的配置通过 `src/hearth/core/config.py` 中的 `load_settings()` 加载。

目前的重要行为包括：

- 如果没有提供配置路径，Hearth 会使用内建默认值
- 如果提供了路径但文件不存在，Hearth 仍然会返回默认配置，并记住这个路径以便后续保存
- 相对路径会相对于配置文件所在目录解析
- runtime 和 backup 目录会在需要时自动创建

这意味着在开发阶段，配置文件缺失默认不会直接导致启动失败。

---

## 顶层配置段

Hearth 目前识别以下顶层配置段：

- `[system]`
- `[reticulum]`
- `[web]`
- `[security]`
- `[monitor]`
- `[alerts]`
- `[[interfaces]]`
- `[[plugins]]`
- `[[plugin_sources]]`

根配置模型会忽略未知的顶层字段。

---

## `[system]`

通用的节点级设置。

### 字段

- `node_name` (`str`，默认：`"hearth-node"`)
  - 人类可读的节点名称，会显示在 UI 和状态输出中。

- `data_dir` (`Path`，默认：`"./.data"`)
  - 本地运行时文件、数据库、日志和备份的根目录。

- `log_level` (`str`，默认：`"INFO"`)
  - 启动 API 服务入口时使用的日志级别。

- `timezone` (`str`，默认：`"UTC"`)
  - 主要用于展示的时区标识符。

---

## `[reticulum]`

控制由 Hearth 托管的 Reticulum runtime 边界。

### 字段

- `enabled` (`bool`，默认：`true`)
  - 是否启用 runtime 层。

- `config_path` (`Path`，默认：`"./reticulum-config"`)
  - 存放 Reticulum 相关配置文件的目录。

- `identity_path` (`Path`，默认：`"./.data/identity"`)
  - 由 Hearth 管理的 identity 文件路径。

- `auto_start` (`bool`，默认：`true`)
  - 应用启动时是否自动启动 runtime。

- `backend` (`"mock_process" | "external_process" | "managed_rnsd"`，默认：`"mock_process"`)
  - 选择 runtime backend 的实现方式。

- `command` (`list[str]`，默认：`[]`)
  - 当 `backend = "external_process"` 时使用的外部命令。

- `transport_enabled` (`bool`，默认：`true`)
  - 在渲染托管 runtime 配置时，控制是否启用 Reticulum transport 模式。

- `shared_instance` (`bool`，默认：`true`)
  - 控制托管 runtime 配置中的 shared-instance 选项。

- `loglevel` (`int`，默认：`4`)
  - 在渲染托管 runtime 配置时写入的 Reticulum 日志级别。

- `render_managed_config` (`bool`，默认：`true`)
  - 启用后，Hearth 会在启动 `managed_rnsd` 之前自动写出托管 Reticulum 配置文件。

- `managed_command` (`str | null`，默认：`null`)
  - 给 `managed_rnsd` 使用的覆盖命令，例如 `rnsd` 或包装脚本。

- `heartbeat_interval_sec` (`int`，默认：`2`)
  - runtime 层预期的心跳间隔。

- `health_timeout_sec` (`int`，默认：`10`)
  - 健康状态评估逻辑使用的超时时间。

- `shutdown_timeout_sec` (`int`，默认：`5`)
  - 优雅关闭 runtime 时等待的超时时间。

### 说明

- `mock_process` 仍然是只评估控制面时最轻量的方式。
- `external_process` 是监督任意外部 runtime 命令的通用方式。
- `managed_rnsd` 则是 Hearth 自动渲染配置并监督真实 `rnsd` 进程的产品化路径。

---

## `[web]`

控制内置的 API 与 Web 控制台。

### 字段

- `enabled` (`bool`，默认：`true`)
  - 是否启用 Web / API 服务。

- `host` (`str`，默认：`"127.0.0.1"`)
  - API 服务绑定的主机地址。

- `port` (`int`，默认：`8480`)
  - API 服务绑定的端口。

- `auth_mode` (`str`，默认：`"local_token"`)
  - 认证模式。当前代码里，除了 `"none"` 之外的值都会被视为启用认证。

### 建议

本地开发建议保持：

- `host = "127.0.0.1"`
- `auth_mode = "local_token"`

---

## `[security]`

控制对控制面的访问。

### 字段

- `admin_token` (`str`，默认：`"change-me"`)
  - 本地登录和已认证 API 访问使用的主管理员 Token。

- `allow_lan` (`bool`，默认：`true`)
  - 是否允许来自私有局域网地址的请求。

- `allow_wan` (`bool`，默认：`false`)
  - 是否允许来自公网地址的请求。

### 说明

- 回环地址访问始终允许。
- 在任何共享部署之前，都应该修改默认 `admin_token`。
- `allow_wan = true` 只能在你明确知道自己在做什么，并配合正确网络控制时再启用。

---

## `[monitor]`

控制健康检查、指标刷新和 watchdog 行为。

### 字段

- `health_check_interval_sec` (`int`，默认：`15`)
  - watchdog / 健康检查任务之间的间隔。

- `metrics_refresh_sec` (`int`，默认：`10`)
  - 周期性节点状态刷新的间隔。

- `watchdog_enabled` (`bool`，默认：`true`)
  - 是否启用 watchdog 后台任务。

- `auto_restart_runtime` (`bool`，默认：`true`)
  - 是否允许 watchdog 在 runtime 异常时自动重启它。

- `auto_restart_interface` (`bool`，默认：`true`)
  - 是否允许 watchdog 在接口不健康时自动重启接口。

- `restart_cooldown_sec` (`int`，默认：`30`)
  - 自动重启尝试之间的冷却时间。

---

## `[alerts]`

控制告警对外投递行为。

### 字段

- `webhook_enabled` (`bool`，默认：`false`)
  - 是否启用告警 Webhook 投递。

- `webhook_url` (`str | null`，默认：`null`)
  - 目标 Webhook 地址。

- `include_resolved` (`bool`，默认：`true`)
  - 在投递或同步流程中是否包含已恢复的告警。

- `delivery_timeout_sec` (`int`，默认：`5`)
  - Webhook 投递尝试的超时时间。

- `sync_interval_sec` (`int`，默认：`30`)
  - 告警刷新任务使用的同步间隔。

---

## `[[interfaces]]`

声明节点接口。

### 通用字段

- `name` (`str`，必填)
- `type` (`str`，必填)
- `enabled` (`bool`，默认：`true`)
- `role` (`str | null`，默认：`null`)

### 扩展字段

接口条目允许额外键值，它们会被原样透传给具体接口类型使用。

常见示例：

- 类 TCP 接口的 `host`、`port`
- 串口 / 无线电接口的 `device`、`baudrate`
- 本地网络接口的 `devices`、`discovery_port`、`data_port`
- 某个驱动自己的自定义字段

### 示例

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

声明已配置的插件。

### 通用字段

- `name` (`str`，必填)
- `enabled` (`bool`，默认：`false`)

### 扩展字段

插件条目同样允许额外键值，这样就可以在不改动根配置模型的前提下，为插件挂接自己的配置项。

当前比较常见的插件扩展字段包括：

- `source`
- `version`
- `type`
- `compatibility`
- `description`
- `permissions`
- `depends_on`
- `config`
- `sandbox_boundary`

### 示例

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

用于声明自定义 RBAC 角色，作为内置角色集的扩展。

### 字段

- `name` (`str`，必填)
- `label` (`str | null`)
- `description` (`str | null`)
- `permissions` (`list[str]`，必填)

### 说明

- `owner`、`admin`、`operator`、`viewer`、`service_manager` 等内置角色仍然会自动存在。
- 通过 Web UI、CLI、API 创建的自定义角色，最终都会回写到主 Hearth 配置文件里。

### 示例

```toml
[[roles]]
name = "field_ops"
label = "Field Ops"
description = "Operate interfaces and maintenance windows"
permissions = ["read", "operate", "maintenance"]
```

---

## `[[plugin_sources]]`

声明插件源目录和其信任元数据。

### 字段

- `name` (`str`，必填)
- `index_url` (`str`，必填)
- `label` (`str | null`)
- `description` (`str | null`)
- `trusted` (`bool`，默认：`false`)
- `expected_sha256` (`str | null`)
- `public_key` (`str | null`)
- `signature` (`str | null`)
- `signature_algorithm` (`str | null`)
- `signature_required` (`bool`，默认：`false`)

### 说明

- Hearth 当前已经支持为插件目录保存信任元数据。
- 已签名的插件源 manifest 可以通过 **Ed25519 公钥签名** 做校验。
- `expected_sha256` 仍然可以作为元数据保存，但真正更强的信任机制是签名校验。

### 示例

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

## 派生路径

一些重要的运行时路径会根据配置自动推导：

- 数据库：`data_dir/hearth.db`
- runtime 目录：`data_dir/runtime/`
- runtime 状态：`data_dir/runtime/reticulum-state.json`
- runtime 观测数据：`data_dir/runtime/reticulum-observations.json`
- 托管 runtime 配置：`data_dir/runtime/reticulum-generated.conf`
- runtime pid：`data_dir/runtime/reticulum.pid`
- runtime stdout 日志：`data_dir/runtime/reticulum.stdout.log`
- runtime stderr 日志：`data_dir/runtime/reticulum.stderr.log`
- 插件运行目录：`data_dir/plugins/`
- 插件状态文件：`data_dir/plugins/installed-plugins.json`
- 远程日志目录：`data_dir/remote-logs/`
- 备份目录：`data_dir/backups/`
- 备份快照索引：`data_dir/backups/snapshots.json`

这些路径不需要直接写进 TOML，而是从 `data_dir` 等基础设置派生出来的。

---

## 校验与编辑工作流

Hearth 在 Web 和 API 两个层面都提供了配置管理工作流。

当前 API 端点包括：

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

这意味着配置不只是一个“手工改本地文件”的动作，而是一个可校验、可审计、可回滚的运维工作流。

---

## 开发环境示例配置

仓库里提供了一个最小可用的本地开发配置：`examples/hearth.toml`。

它适合：

- 本地 UI 开发
- CLI 体验
- API 调试
- 在还没有真实外部 runtime 之前先验证 Hearth 控制面本身

它**不适合**原样暴露到共享网络或公网环境。

---

## 运维建议

对于安全的本地开发：

- 保持 `host = "127.0.0.1"`
- 保持 `auth_mode = "local_token"`
- 修改 `admin_token`
- 检查示例接口配置是否仍然符合你的环境
- 除非你明确要远程暴露，否则保持 `allow_wan = false`

对于打包或接近生产的部署：

- 在合适的地方使用稳定的绝对路径
- 有意识地管理配置文件所在位置
- 把 `data_dir`、数据库和 identity 材料一起备份
- 在真正依赖这个节点前先测试恢复流程

---

## 总结

Hearth 的顶层配置模型看起来很简单，但它实际上驱动着一个很大的运维面：runtime 控制、Web / API 暴露、watchdog 行为、告警投递、插件信任与持久化节点状态。
