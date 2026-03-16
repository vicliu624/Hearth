# Hearth API 参考

[Docs](README.zh-CN.md) / [English](api-reference.md)

这份文档总结了 Hearth 当前已经暴露出来的 API 面。

API 基于 FastAPI 实现，并与 Web 控制台挂载在同一个应用里。

它不是一个普通的后台管理 API，而是一个用于操作 **Personal Reticulum Transport Node** 的 **控制面 API**。

这意味着，一个节点运维者可以通过它去做这些事情：

- 检查 runtime 与接口状态
- 查看 peers、routes 和 announces
- 管理配置与备份
- 控制安全、用户和 Token
- 查看插件、服务、桥接、拓扑和 fleet 数据

放在整体上下文里理解：

- **Reticulum** 是网络栈
- **Hearth** 是这个网络栈中某个节点外侧的管理层
- 这个 API 则是这层管理面的程序化入口

---

## 基本行为

### API 与 Web 在同一个应用中

Hearth 会同时提供：

- Web 页面，例如 `/`、`/interfaces`、`/plugins`、`/bridges` 等
- `/api/*` 下的 JSON API
- `/metrics` 下的指标输出

### 认证方式

当认证启用时，Hearth 支持通过以下方式传递 Token：

- `Authorization: Bearer <token>`
- `X-Hearth-Token: <token>`
- 查询参数 `?token=<token>`
- `hearth_token` Cookie

### 认证开关

只要不是下面这个配置，Hearth 都会视为启用认证：

- `web.auth_mode = "none"`

### 主机访问过滤

在真正进入路由处理前，请求会先根据以下配置做访问过滤：

- `security.allow_lan`
- `security.allow_wan`

回环地址访问始终允许。

### 安全响应头

Hearth 会在控制面统一应用浏览器安全响应头，包括 CSP、禁止 iframe 嵌套、Referrer Policy 等相关保护。

---

## 权限模型

当前的路由级权限使用以下能力词汇：

- `read`
- `operate`
- `configure`
- `security`
- `tokens`
- `maintenance`

一般来说：

- 只读状态查看使用 `read`
- 节点和接口操作使用 `operate`
- 配置、插件、fleet 变更使用 `configure`
- 用户和角色管理使用 `security`
- API Token 管理使用 `tokens`
- 维护模式变更使用 `maintenance`

当前实现里，仍有少量基础只读接口没有显式绑定权限依赖；但在启用认证时，它们仍应被视为受保护的控制面接口。

---

## Node

### `GET /api/node/status`

返回节点状态摘要。

### `POST /api/node/start`

权限：`operate`

启动受管 runtime。

### `POST /api/node/stop`

权限：`operate`

停止受管 runtime。

### `POST /api/node/restart`

权限：`operate`

重启受管 runtime。

---

## Interfaces

### `GET /api/interfaces`

列出已配置接口。

### `GET /api/interfaces/{name}`

返回单个接口详情。

### `POST /api/interfaces/{name}/start`

权限：`operate`

### `POST /api/interfaces/{name}/stop`

权限：`operate`

### `POST /api/interfaces/{name}/restart`

权限：`operate`

### `GET /api/interfaces/{name}/metrics`

返回接口指标。

---

## Peers

### `GET /api/peers`

列出 peers。

### `GET /api/peers/recent`

列出最近发现的 peers。

### `GET /api/peers/{peer_hash}`

根据 hash 返回 peer 详情。

---

## Routes

### `GET /api/routes`

列出 routes。

### `GET /api/routes/summary`

返回 route 摘要数据。

### `GET /api/routes/{destination_hash}`

返回 route 详情。

---

## Announces

### `GET /api/announces`

列出 announces。

### `GET /api/announces/recent`

列出最近的 announces。

### `GET /api/announces/{announce_id}`

返回 announce 详情。

---

## Logs

### `GET /api/logs`

返回日志条目。

### `GET /api/logs/timeline`

返回面向时间线的日志 / 事件数据。

---

## Diagnostics、Alerts、Audit 与 Maintenance

### `GET /api/diagnostics`

权限：`read`

返回诊断摘要数据。

### `GET /api/alerts`

权限：`read`

返回当前告警。

### `GET /api/alerts/history`

权限：`read`

返回告警历史。

### `GET /api/audit`

权限：`read`

返回审计 / 事件记录。

### `GET /api/maintenance`

权限：`read`

返回维护模式状态。

### `POST /api/maintenance`

权限：`maintenance`

变更维护模式状态或相关工作流设置。

---

## Configuration

所有配置相关路由都挂载在 `/api/config` 下，并在 router 层统一要求 `configure` 权限。

### 读取 / 查看

- `GET /api/config`
- `GET /api/config/raw`

### 校验

- `POST /api/config/validate`
- `POST /api/config/validate-raw`

### 保存

- `POST /api/config/save`
- `POST /api/config/save-raw`

### 历史版本

- `GET /api/config/revisions`
- `GET /api/config/revisions/{revision_id}`
- `GET /api/config/revisions/{revision_id}/compare`
- `POST /api/config/revisions/{revision_id}/restore`

这些端点支撑结构化配置工作流、原始 TOML 工作流，以及历史版本恢复操作。

---

## Backups

所有备份路由都挂载在 `/api/backup` 下，并统一要求 `configure` 权限。

### 端点

- `GET /api/backup`
- `GET /api/backup/detail`
- `POST /api/backup/export`
- `POST /api/backup/snapshot`
- `POST /api/backup/import`
- `GET /api/backup/snapshots`
- `POST /api/backup/prune`
- `GET /api/backup/dr`

它们用于查看备份状态、创建导出包和快照、清理保留快照、生成灾难恢复指引，以及导入备份归档。

---

## Plugins

### `GET /api/plugins`

权限：`read`

列出已配置插件和插件元数据。

### `GET /api/plugins/catalog`

权限：`read`

列出从插件源合并而来的可安装目录条目。

### `GET /api/plugins/history`

权限：`read`

返回最近的插件操作历史。

### `GET /api/plugins/sources`

权限：`read`

列出插件源目录以及其信任 / 签名元数据。

### `POST /api/plugins/sources/refresh`

权限：`configure`

刷新插件源目录。

### `GET /api/plugins/{name}`

权限：`read`

返回插件详情。

### `POST /api/plugins/install`

权限：`configure`

从插件目录安装插件，并先解析依赖关系。

### `POST /api/plugins/{name}`

权限：`configure`

更新插件状态，通常用于启用 / 禁用等操作。

### `POST /api/plugins/{name}/refresh`

权限：`configure`

用当前目录元数据刷新已安装插件。

### `DELETE /api/plugins/{name}`

权限：`configure`

卸载插件，并可选地同时移除依赖它的插件。

---

## Services

### `GET /api/services`

权限：`read`

列出 service-host 风格的运行服务。

### `GET /api/services/{name}`

权限：`read`

返回服务详情。

### `POST /api/services/{name}`

权限：`operate`

执行某个服务动作。

---

## Bridges

### `GET /api/bridges`

权限：`read`

列出桥接集成。

### `GET /api/bridges/{name}`

权限：`read`

返回桥接详情，其中包括源信任信息、健康检查和最近操作记录。

### `POST /api/bridges/{name}`

权限：`operate`

执行桥接动作，例如运行控制或投递测试。

---

## Fleet

Fleet 路由位于 `/api/fleet` 下。

### 只读端点

权限：`read`

- `GET /api/fleet/overview`
- `GET /api/fleet/nodes`
- `GET /api/fleet/nodes/{node_name}`
- `GET /api/fleet/groups`
- `GET /api/fleet/templates`
- `GET /api/fleet/tags`
- `GET /api/fleet/health`
- `GET /api/fleet/events`

### 变更端点

权限：`configure`

- `POST /api/fleet/nodes`
- `POST /api/fleet/groups`
- `POST /api/fleet/templates`

这些接口支撑了 Hearth 早期的多节点清单、分组和模板模型。

---

## Security

安全相关路由位于 `/api/security` 下。

### 角色与用户

权限：`security`

- `GET /api/security/roles`
- `POST /api/security/roles`
- `POST /api/security/roles/{role_name}`
- `DELETE /api/security/roles/{role_name}`
- `GET /api/security/users`
- `POST /api/security/users`
- `POST /api/security/users/{username}`

### API Token

权限：`tokens`

- `GET /api/security/tokens`
- `POST /api/security/tokens`
- `POST /api/security/tokens/{token_name}`

这些接口管理控制面对外的用户、角色和 Token 模型。

---

## Metrics

### `GET /metrics`

返回 Prometheus 风格的纯文本指标。

### `GET /api/metrics/summary`

权限：`read`

返回供 Web / API 面使用的指标摘要数据。

---

## Topology 与 Network Intelligence

拓扑相关路由位于 `/api/topology` 下。

权限：`read`

### 端点

- `GET /api/topology`
- `GET /api/topology/network-map`
- `GET /api/topology/route-heatmap`
- `GET /api/topology/critical-nodes`
- `GET /api/topology/insights`
- `GET /api/topology/path-changes`

这些路由支撑了 Web 控制台中的拓扑和网络理解页面。

---

## Rollouts、Remote Logs 与 Upgrades

### Rollouts

- `GET /api/rollouts` — 权限：`read`
- `POST /api/rollouts` — 权限：`configure`

### Remote logs

- `GET /api/remote-logs` — 权限：`read`
- `POST /api/remote-logs/ingest` — 权限：`operate`
- `POST /api/remote-logs/sync` — 权限：`operate`

### Upgrades

- `GET /api/upgrades` — 权限：`read`
- `POST /api/upgrades` — 权限：`operate`
- `POST /api/upgrades/execute` — 权限：`operate`

这些接口支撑了超出基础 runtime 生命周期之外的运维工作流。

---

## Web 页面概览

除了 JSON API 之外，Hearth 还暴露了大量 Web 页面，包括：

- dashboard
- interfaces
- peers
- routes
- announces
- logs
- config 与 config history
- backup
- system 与 maintenance
- users、roles、tokens、security 与 audit
- plugins 与 plugin sources
- services 与 bridges
- fleet 与 topology 页面
- metrics、diagnostics、alerts、rollout、upgrade 与 remote logs

这些页面和 API 共用同一套应用上下文与后端服务。

---

## 实用示例

### 示例：已认证的节点状态请求

```bash
curl -H "X-Hearth-Token: <token>" http://127.0.0.1:8480/api/node/status
```

### 示例：列出插件

```bash
curl -H "Authorization: Bearer <token>" http://127.0.0.1:8480/api/plugins
```

### 示例：获取拓扑摘要

```bash
curl -H "X-Hearth-Token: <token>" http://127.0.0.1:8480/api/topology
```

---

## 总结

Hearth 的 API 不只是薄薄一层状态接口，它是一个更大范围节点控制面的程序化入口，覆盖 runtime 运维、配置、恢复、安全、扩展以及早期多节点工作流。
