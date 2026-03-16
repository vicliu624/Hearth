# Hearth 安全指南

[Docs](README.zh-CN.md) / [English](security.md)

这篇文档说明 Hearth 当前在仓库里已经实现的安全模型。

先把上下文说清楚：

- **Reticulum** 是底层网络栈
- **Hearth** 是围绕 Personal Reticulum Transport Node 的控制面
- 所以 Hearth 的安全重点，保护的是 **节点的管理面**：Web、API、认证、授权、访问暴露范围，以及插件源这类供应链信任问题

它**不是**在替代 Reticulum 内部所有更深层的网络安全决策。

---

## 安全目标

Hearth 当前的安全模型主要是为了在本地优先、小规模网络的使用场景中，保护节点运维者免受常见控制面风险影响。

主要目标包括：

- 对敏感控制面操作要求认证
- 把只读访问和高权限操作分开
- 默认尽量限制网络暴露范围
- 通过浏览器安全头减少前端攻击面
- 提供可审计的用户与 Token 管理能力
- 对插件源和签名 manifest 做信任校验

---

## 当前安全层次

### 1. 网络暴露控制

请求来源会被划分为：

- loopback
- 局域网 / 私网
- 公网

然后根据下面两个配置决定是否允许：

- `security.allow_lan`
- `security.allow_wan`

loopback 永远允许。

这意味着 Hearth 是一个天然 **local-first** 的系统。

### 2. 认证

只要 `web.auth_mode != "none"`，受保护的路由就要求基于 Token 的认证。

当前支持的 Token 来源包括：

- `Authorization: Bearer <token>`
- `X-Hearth-Token: <token>`
- `?token=<token>` 查询参数
- `hearth_token` Cookie

### 3. 授权

路由访问使用权限模型保护。用户的角色和 Token 的 scope 共同决定它能否执行某个操作。

### 4. 浏览器侧加固

Hearth 会统一下发一组安全头，包括：

- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Referrer-Policy: same-origin`
- `Permissions-Policy`
- 较严格的 `Content-Security-Policy`

### 5. 插件源供应链信任

插件源目录可以携带信任元数据，并支持 digest 校验与 **Ed25519 签名校验**。

---

## 认证模型

### `admin_token`

最重要的内置凭据是：

- `security.admin_token`

如果传入的 Token 与它完全匹配，Hearth 会把调用者识别为内置 `admin` 主体，并授予 `owner` 角色。

### Web 登录

Web 界面提供基于 Token 的登录表单。

登录成功后，Token 会被写入 `hearth_token` Cookie。

当前 Cookie 特性包括：

- `HttpOnly`
- `SameSite=Strict`
- path `/`

### API Token

除了内置的管理员 Token，Hearth 还支持数据库中保存的 API Token。

每个 Token 可以拥有：

- token 名称
- 可选的 owner user
- role
- 可选的 scopes
- 启用 / 禁用状态
- 可选的过期时间

原始 Token 明文不会以明文形式保存，系统会在数据库中保存它的 SHA-256 哈希。

### Token 过期与 owner 检查

使用数据库 Token 时，会额外检查：

- Token 是否启用
- Token 是否已经过期
- 如果 Token 绑定了某个用户，该用户是否仍存在且处于启用状态

---

## 角色与权限

Hearth 当前内置这些角色：

- `owner`
- `admin`
- `operator`
- `viewer`
- `service_manager`

### 权限集合

当前路由级权限包括：

- `read`
- `operate`
- `configure`
- `security`
- `tokens`
- `maintenance`

### 这些权限大致表示什么

- `read`：查看仪表盘、日志、routes、peers 以及其他可观测性数据
- `operate`：启动 / 停止 / 重启 runtime、接口、bridge 和服务动作
- `configure`：修改配置、插件状态、fleet 相关状态和其他运维配置
- `security`：管理用户和角色
- `tokens`：管理 API Token
- `maintenance`：切换维护模式以及相关维护工作流

### Scopes

API Token 还可以携带 scopes。

当前授权逻辑分成两步：

1. 角色本身必须允许对应权限
2. Token 的 scopes 必须包含 `*`，或明确包含对应权限

这意味着：即使某个角色本身比较宽，scope 仍然可以把 Token 权限再缩小一层。

---

## 用户与 Token

### 用户

Hearth 支持通过安全服务和安全 API 路由管理用户目录。

用户当前主要包含：

- username
- display name
- role
- 启用 / 禁用状态
- 与 Token 的所有权关系

内置 `admin` 用户是特殊的：

- 它在概念上始终存在
- 它对应配置里的 `admin_token`
- 它不像普通用户那样可以被直接禁用

### Token

Token 创建是面向运维工作流的。

新建 Token 时，原始密钥只会返回一次，之后就应该被当作正式凭据安全保存。

---

## 网络暴露模型

### 默认意图

Hearth 默认的安全姿态是：

- 偏向本机或局域网
- 不会无意间向公网开放

### `allow_lan`

启用后，来自私网 / 局域网的客户端可以访问。

### `allow_wan`

启用后，来自公网的客户端可以访问。

这应该被视为一个非常明确、需要认真考虑的暴露决定。

### 关于反向代理的一点提醒

当前主机来源分类基于请求的实际客户端地址。如果你把 Hearth 放在反向代理之后，请不要默认认为“公网暴露控制”与直接绑定场景完全一致，应该结合你的代理拓扑重新审视。

---

## 浏览器与会话安全

Web UI 当前使用的是基于 Token 的登录，而不是密码数据库型登录。

### 当前模型的优点

- Web UI 本身不维护一套密码数据库
- 登录 Cookie 是 `HttpOnly`
- `SameSite=Strict` 可以减少跨站场景下的 Cookie 发送
- 较严格的 CSP 与 frame denial 能减少浏览器侧攻击面

### 当前模型的边界

- Cookie 默认没有 `Secure` 标记
- 仍然接受查询参数 Token 认证
- 当前 Web 认证模型更适合 local-first 或经过谨慎代理的场景，而不是“直接裸暴露到公网”

如果你要把 Hearth 暴露到 localhost 或可信 LAN 之外，最好放在 HTTPS 和受控反向代理之后。

---

## 审计与安全事件

Hearth 会把一些与安全相关的事件写入数据库，例如：

- login succeeded
- login failed
- logout
- user created
- user updated
- token created
- token updated

这给节点运维者提供了一个基础审计线索。

---

## 插件源信任与签名

Hearth 的安全不只包括登录和权限，也包括扩展来源的信任问题。

### 当前使用的信任状态

插件源当前会使用这些签名状态：

- `trusted`
- `verified`
- `invalid`
- `missing`
- `not_required`

### 插件源可携带的信任字段

一个插件源可以声明：

- `trusted`
- `expected_sha256`
- `public_key`
- `signature`
- `signature_algorithm`
- `signature_required`

### Ed25519 校验

已签名的 manifest 可以通过 **Ed25519 公钥签名** 校验。

这比只校验 digest 更强，应该优先采用。

### 运维者实际要怎么理解

如果你在使用第三方插件源目录，不应该把所有来源都视为同等级信任。至少要检查：

- 这个来源是否被标记为 trusted
- manifest 是否真的被验证通过
- 必需签名是不是缺失或无效
- 配置的公钥是否与 manifest 自带公钥一致

---

## 推荐加固清单

在把 Hearth 暴露到开发环境之外之前，至少先完成这些事：

- 修改 `security.admin_token`
- 保持 `web.auth_mode` 处于启用状态
- 除非明确需要，否则保持 `allow_wan = false`
- 尽量只绑定到最小必要的网络接口
- 一旦流量离开 localhost 或可信私网，就使用 HTTPS
- 自动化脚本尽量使用权限更小的 API Token，而不是复用内置管理员 Token
- 为自动化 Token 使用更窄的 scopes
- 在启用外部插件源前先审查其信任状态
- 检查配置文件、identity 和 `data_dir` 的文件权限
- 改动安全设置后查看审计事件

---

## 当前安全边界

Hearth 已经具备比较实用的控制面安全能力，但仍然要诚实地看待当前边界。

### 今天已经实现的部分

- 基于 Token 的认证
- 基于角色与 scopes 的授权
- 用户与 Token 管理
- LAN / WAN 暴露控制
- 浏览器安全头
- 审计事件
- 插件源信任元数据与 Ed25519 签名校验

### 仍然需要谨慎对待的部分

- 不经过反向代理或 TLS 的直接公网暴露
- 长期复用内置管理员 Token
- 在共享环境里依赖查询参数 Token
- 误以为 Hearth 可以替代 Reticulum 更深层的网络安全策略

---

## 总结

Hearth 的安全重点，是保护节点的管理面。

今天它已经覆盖了这些问题：

- 谁能连上来
- 如何完成认证
- 认证后能做什么
- 浏览器侧能做什么
- 扩展来源是否可信

对大多数真实部署来说，最安全的思路仍然是：默认 local-first，谨慎暴露，认真对待运维凭据和插件源信任。
