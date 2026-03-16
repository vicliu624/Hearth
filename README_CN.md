# Hearth

> 面向个人、家庭与小型社区的个人 Reticulum 基础设施节点系统。

[English](README.md) · [文档导航](docs/README.zh-CN.md) · [接入模型](docs/network-model.zh-CN.md) · [快速开始](docs/getting-started.zh-CN.md)

**Hearth** 是一个以 Linux 为优先目标的平台，用来把 **Personal Reticulum Transport Node（个人 Reticulum 传输节点）** 做成一个真正可以部署、管理、观察、恢复和长期运行的系统。

如果你只想先看懂一句话，那就是：

> **Reticulum** 是一个去中心化网络栈，目标是让设备可以通过不同类型的链路互联，而不必完全依赖中心化服务器；**Hearth** 则是帮助你把自己的 Reticulum 基础设施节点真正跑起来、管起来、看得见、修得动的那一层软件。

它不是要替代 Reticulum，也不是要发明新协议，更不是一个聊天客户端。Hearth 关注的是节点外围那一整层经常被忽视、但在实际运行中最关键的能力：运行时托管、接口管理、发现与路由可视化、配置工作流、备份恢复、Web/CLI/API 管理入口，以及插件、服务、桥接和多节点管理的扩展基础。

一句话概括：

> **Hearth 要解决的，不是“让一个节点能跑起来”，而是“让一个节点变成可长期使用的基础设施”。**

---

## Reticulum 是什么？

Reticulum 可以理解为一个 **去中心化网络栈**。

它背后的核心思想是：通信基础设施不应该完全依赖远端中心化服务，而应该允许每个人都运行自己的节点，让这些节点通过不同的链路互联，逐步形成更分布式的网络。

在实践层面上，Reticulum 可以工作在多种传输介质之上，例如：

- IP 网络
- 串口链路
- 无线电链路
- LoRa / RNode 一类的接口
- 其他由运行时支持的传输方式

在 Reticulum 网络中，不同节点承担的角色并不一样。

有些节点更像 **客户端节点**，例如：

- 手机
- 笔记本电脑
- 嵌入式设备
- 面向用户的终端应用

还有一些节点更像 **传输节点 / 基础设施节点**。这些节点的作用通常包括：

- 转发流量
- 传播 announces
- 维护 path 信息
- 连接多种接口
- 为附近设备提供稳定的本地接入点

而 Hearth 所关注的，正是第二类角色。

---

## Hearth 在 Reticulum 中扮演什么角色？

Hearth 不是 Reticulum 协议本身，也不是运行在 Reticulum 之上的聊天应用或上层业务。

Hearth 是一层 **控制面 / 运维层**，它的职责是把一个长期在线的 Reticulum 节点真正变成“可管理的节点系统”。

可以把它想象成这样：

```text
手机 / 笔记本 / 本地设备
           |
           v
        Hearth
           |
           v
   Reticulum 网络
```

在这个模型里，Hearth 做的事情是：把一台 Linux 设备变成一个 **可管理的 Reticulum 基础设施节点**。

更具体一点说，Hearth 帮你运行的是这样一种节点：

- 可以长期在线
- 可以承载一个或多个接口
- 可以成为本地网络锚点
- 可以参与 peer 发现和 route 学习
- 可以通过真正的管理界面来操作，而不是靠零散脚本临时维护

所以最简单的定义就是：

> **Hearth = 用来运行你自己的 Personal Reticulum Transport Node 的软件。**

---

## 本地节点怎么接入 Hearth？

这里最容易产生误解。

更准确的说法不是“本地节点接入 Hearth 的 Web 页面”，而是：

> **本地节点接入的是 Hearth 所管理的那个 Reticulum Transport Node。**

也就是说，要把本地设备真正接进网络，需要分清两层：

- **人接入 Hearth 控制面**：通过浏览器、CLI、API 登录和管理节点
- **节点接入 Hearth 管理的网络节点**：通过本地接口进入这个 Transport Node

典型关系如下：

```text
运维者浏览器 / CLI / API
            |
            v
      Hearth 控制面
            |
            v
Hearth 所管理的 Reticulum 节点
            |
            v
      本地接入接口（TCP / 串口 / 无线电）
            |
            v
      本地客户端节点
```

所以本地手机、笔记本或嵌入式节点，并不是去访问 `/login` 或 `/api/*` 来“加入网络”，
而是运行它们自己的 Reticulum 客户端 / 节点，再通过 Hearth 所管理的本地接口接入。

---

## Hearth 怎么接入更大一层的 Reticulum 网络？

Hearth 接入更大网络的方式，也不是靠 Web 页面，而是靠它管理的 **uplink / backbone / radio 接口**。

一个完整路径通常会长这样：

```text
本地客户端节点
      |
      v
本地接入接口
      |
      v
Hearth 管理的 Reticulum 节点
      |
      v
uplink / backbone 接口
      |
      v
更大的 Reticulum 网络
```

在这里：

- **Reticulum runtime** 负责真正的 announce 传播、路径学习和流量转发
- **Hearth** 负责把这个 runtime 和这些 interfaces 管理起来，并把 peers、routes、announces 展示给你

当前仓库里的 `examples/hearth.toml` 已经给出了两个方向：

- `tcp_backbone`：一个 `role = "uplink"` 的上游 TCP 接口示例
- `rnode_usb`：一个无线电 / 串口风格接口示例

在真实部署里，你通常还会再加一个**面向本地客户端**的接口，这样你的设备才能先进入 Hearth 所管理的节点，再由这个节点连向更大的 Reticulum 网络。

如果你想专门看这一层的完整解释，请继续读：[`docs/network-model.zh-CN.md`](docs/network-model.zh-CN.md)。

---
## 用户通过 Hearth 能做什么？

如果你是用户、运维者，或者正在构建自己的网络基础设施，Hearth 能帮你做非常具体的事情：

- 在 Raspberry Pi、家庭服务器或小型 Linux 主机上运行你自己的常开 Reticulum 节点
- 在一个地方统一管理多个接口
- 通过 Web UI 或 API 查看 peers、routes、announces
- 启动、停止、重启并监督 runtime 和接口状态
- 校验、保存、审阅并恢复配置变更
- 导出和导入备份，让节点可以恢复或迁移
- 用登录、Token、用户、角色和权限来管理访问
- 通过插件、服务和桥接能力扩展节点
- 把这个节点作为你自己的设备、家庭网络或小社区的本地接入点

换句话说，Hearth 是把下面这件事：

```text
理论上能运行的 Reticulum 节点
```

变成下面这件事的工具：

```text
真正可部署、可观察、可控制、可依赖的 Reticulum 节点
```

---

## Hearth 是什么

Hearth 更适合被理解为一个 **节点基础设施产品**，而不是单一程序。

它适合运行在这些设备上：

- Raspberry Pi
- 小型 Linux 主机
- 家庭常开服务器
- 边缘设备或网关盒子
- 小型 x86 节点
- 未来的专用 appliance 设备

它试图提供统一的控制面，用来完成：

- 启动、停止、重启并监督 Reticulum runtime
- 统一管理多个网络接口
- 查看 peers、routes、announces 等网络状态
- 跟踪健康状态、指标、告警和诊断信息
- 编辑、校验、版本化并恢复配置
- 导出与导入备份
- 管理安全策略、用户、角色与 API Token
- 通过插件、服务和桥接能力扩展节点
- 从单节点逐步走向小规模 fleet 管理

Hearth **不是**：

- 聊天软件
- 社交平台
- Reticulum 协议或协议栈的替代品
- 默认依赖远程中心的云控制器

---

## 为什么会有 Hearth

Reticulum 最有价值的理念之一，是让每个人都能运行自己的网络节点，而不是把基础设施交给少量远端或中心化服务器。

但现实是，真正难的往往不是协议本身，而是协议周边的运维问题：

- 节点怎么长期稳定在线
- 接口怎么统一配置和检查
- peers、paths、announces 怎么观察
- 故障出现后怎么快速定位
- runtime 挂了以后怎么安全恢复
- 配置怎么修改、回滚和备份
- 如何给真实运维者提供可靠的管理界面

Hearth 就是为了解决这些问题而存在。

它希望把这个过程简化成：

1. 准备一台常开设备
2. 安装 Hearth
3. 完成基础配置
4. 启动节点
5. 用 Web、CLI、API 去持续管理它

---

## 当前状态
当前版本是 **v0.1.0**。

目前仓库已经包含一套相当完整的控制面实现：Web 控制台、CLI、REST API、存储层、配置工作流，以及覆盖较广的运维页面和服务模块。

同时也需要明确当前边界：

- 当前仓库内置的示例配置已经切到 **`managed_rnsd`**，也就是 Hearth 可以直接监督真实 `rnsd` 进程，并自动渲染它使用的运行时配置
- 如果你现在只是想先体验控制面，而本机还没有 Reticulum / `rnsd`，仍然可以切回 **mock runtime backend** 进行本地评估
- runtime 层已经补上 **Runtime Config Bridge** 与 **degradation policy engine**，可以对 runtime 重启、接口重启、接口隔离进行策略决策
- 管理、可观测性、安全、插件、桥接、拓扑、fleet 等大量功能已经有产品面和数据模型
- 当前 Fleet 的 rollout / upgrade 远程执行能力，仍依赖每个被管节点暴露可达的 `dashboard_url` 管理入口

所以 Hearth 现在已经是一个可以本地运行、可以体验、也可以继续演化的节点控制平面，但它还不是最终成品 appliance。

---

## 现在已经具备的核心能力

### 节点生命周期管理

- 启动、停止、重启节点 runtime
- 查看运行时状态、uptime、健康状态
- 通过 Web、API、CLI 从多个入口操作节点
- 支持 `mock_process`、`external_process` 和 **`managed_rnsd`** 三种 runtime backend
- 通过 runtime config bridge 把 Hearth 的接口配置渲染成托管的 Reticulum 配置

### 接口管理

- 以统一模型管理多种接口
- 查看接口状态和指标
- 单独启动、停止、重启某个接口
- 支持 uplink、local、radio 等角色语义
- 内置 `tcp`、`serial`、`rnode`、`local`、`custom` 等接口驱动

### 发现与路由可视化

- 查看 peers、routes、announces
- 查看单个 peer 和 route 的详情
- 提供 network map、route heatmap、critical nodes、path changes 等页面
- 让节点的网络状态不再像黑盒

### 健康、监控与维护

- 健康检查和诊断页面
- 指标面板与 Prometheus 风格 metrics 导出
- 告警与 maintenance 工作流
- 远程日志、升级、rollout 等运维页面
- 面向长期运行的 watchdog / service 化思路
- 基于 degradation policy 的 runtime 恢复、接口重启与隔离决策

### 配置与备份恢复

- 查看并校验结构化配置
- 编辑原始 TOML 配置
- 保存配置修订版本并查看差异
- 回滚到旧的配置版本
- 导出/导入备份，支持节点迁移和恢复
- 创建备份快照、按保留策略清理快照，并生成灾难恢复操作清单

### 安全与访问控制

- Web 登录流程
- 管理员 Token
- 用户、角色、权限、API Token
- 审计事件记录
- `allow_lan` / `allow_wan` 等本地优先暴露策略
- 支持直接通过配置、API、CLI、Web UI 创建 / 编辑 / 删除 **自定义 RBAC 角色**

### 插件、服务与桥接

- 插件目录和插件详情页
- 插件源管理与信任元数据
- 对签名插件源 manifest 的 **Ed25519 公钥签名校验**
- 插件目录安装 / 更新 / 卸载工作流、依赖解析，以及最近操作历史
- 插件 sandbox boundary 元数据，帮助操作者在启用前理解文件系统 / 网络边界要求
- 服务目录与服务详情页
- Bridge 列表与详情页，包含控制、健康检查、最近操作历史与投递测试

### Fleet 与拓扑方向

- 节点 inventory、分组、标签、模板、健康视图
- fleet 概览与事件页
- 通过各节点管理入口分发 rollout 与 upgrade
- 面向多节点运维的远程日志拉取 / 推送聚合能力
- topology / network intelligence 风格页面，为多节点与网络理解打基础

---

## Web 控制台

Hearth 的 Web 界面不是普通后台，而是一个 **节点运维控制台**。

当前的重要页面大致包括：

- **Dashboard**：节点总览、健康状态、runtime 状态、快速操作
- **Interfaces / Peers / Routes / Announces**：网络运行面的核心可视化
- **Logs / Alerts / Diagnostics / Metrics**：观察与排障
- **Configuration / Config History / Backup**：配置管理与恢复能力
- **System / Maintenance / Upgrade / Rollout**：节点系统级运维
- **Users / Roles / Tokens / Security / Audit**：安全与权限管理、自定义 RBAC 角色维护、审计追踪
- **Plugins / Plugin Sources / Services / Bridges**：签名目录、插件安装/更新/卸载、来源信任、上层服务宿主能力
- **Backup / Remote Logs**：快照保留、灾备清单、Fleet 远程日志同步
- **Fleet / Topology / Network Map / Path Changes**：多节点与网络结构理解

当前前端也已经具备多语言渲染和翻译回退机制，即使某些翻译项损坏，也不会把整页渲染成大量问号乱码。

---

## CLI 与 API

Hearth 希望 Web、CLI、API 是同一套系统的不同入口，而不是彼此割裂的工具。

### CLI

CLI 入口是 `hearth`。

示例：

```bash
hearth serve --config hearth.toml
hearth status --config hearth.toml
hearth interfaces list --config hearth.toml
hearth peers list --config hearth.toml
hearth routes list --config hearth.toml
hearth announces list --config hearth.toml
hearth backup export --config hearth.toml
hearth backup snapshot --config hearth.toml
hearth backup prune --config hearth.toml --keep 10 --max-age-days 30
hearth plugins catalog --config hearth.toml
hearth plugins install mesh_bridge --config hearth.toml
hearth security roles list --config hearth.toml
hearth remote-logs sync --config hearth.toml
hearth deploy preflight --config hearth.toml
hearth system diagnostics --config hearth.toml
```

### REST API

当前代表性接口包括：

- `/api/node/*`
- `/api/interfaces/*`
- `/api/peers/*`
- `/api/routes/*`
- `/api/announces/*`
- `/api/config/*`
- `/api/backup/*`
- `/api/security/*`
- `/api/plugins/*`
- `/api/services/*`
- `/api/bridges/*`
- `/api/fleet/*`
- `/api/topology/*`
- `/metrics`

---

## 快速开始

### 环境要求

- Python `3.12+`
- 推荐使用虚拟环境
- 部署目标以 Linux 为主，但本地开发在 Windows 上也可以完成

### 1. 创建虚拟环境

**Windows PowerShell**

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e .[dev]
```

如果 PowerShell 因执行策略不能激活环境，也可以直接继续使用 `.\.venv\Scripts\python.exe`。

**Linux / macOS**

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .[dev]
```

### 2. 准备配置文件

从示例配置开始：

**Windows**

```powershell
Copy-Item examples\hearth.toml .\hearth.toml
```

**Linux / macOS**

```bash
cp examples/hearth.toml ./hearth.toml
```

示例配置默认用于本地开发，关键项包括：

- `backend = "managed_rnsd"`
- `host = "127.0.0.1"`
- `port = 8480`
- `auth_mode = "local_token"`

如果你现在**还没有**安装 Reticulum / `rnsd`，只是想先体验控制面，请把：

- `reticulum.backend = "mock_process"`

如果保留默认的托管 runtime 配置，则要确保本机可以直接执行 `rnsd`，或者 `python -m RNS.Utilities.rnsd` 能正常运行。

如果不是只在本机测试，至少要先修改：

- `security.admin_token`
- `security.allow_wan`
- 示例接口里的地址和端口

### 3. 启动 Hearth

```bash
python -m hearth.cli.main serve --config hearth.toml
```

### 4. 打开 Web 控制台

访问：

```text
http://127.0.0.1:8480/login
```

使用 `hearth.toml` 里的管理员 Token 登录。

本地测试时，也可以通过请求头访问 API，例如：

```bash
curl -H "X-Hearth-Token: change-me" http://127.0.0.1:8480/api/node/status
```

### 5. 试几个命令

```bash
python -m hearth.cli.main status --config hearth.toml
python -m hearth.cli.main interfaces list --config hearth.toml
python -m hearth.cli.main peers list --config hearth.toml
python -m hearth.cli.main system info --config hearth.toml
```

---

## 配置模型

Hearth 使用 TOML 配置。

`examples/hearth.toml` 里已经展示了主要结构：

- `[system]`
- `[reticulum]`
- `[web]`
- `[security]`
- `[monitor]`
- `[[interfaces]]`
- `[[plugins]]`

几个重要设计点：

- runtime adapter 支持 `mock_process`、`external_process`、`managed_rnsd`
- `managed_rnsd` 会根据 Hearth 接口配置渲染托管的 Reticulum 配置，并监督该进程生命周期
- 系统运行数据会写入配置中的 `data_dir`
- 自定义 RBAC 角色定义在 `[[roles]]` 中
- 插件状态、远程日志、托管 runtime 文件、备份快照等也都会派生在 `data_dir` 之下
- 配置修改支持校验、版本化、审阅和恢复

---

## 安全模型

Hearth 的控制面是一个本地优先的管理入口。

当前已经具备的安全机制包括：

- 管理员 Token 认证
- Web 登录与 Cookie 会话
- 基于角色的权限控制，覆盖 `read`、`operate`、`configure`、`security`、`tokens`、`maintenance` 等权限
- 在内置角色之上继续叠加可编辑的自定义角色
- 用户与 Token 管理页面
- 审计事件记录
- `allow_lan` / `allow_wan` 暴露控制

内置角色目前包括：

- `owner`
- `admin`
- `operator`
- `viewer`
- `service_manager`

需要注意的是，Hearth 保护的是节点的控制面与运维面，不是替代 Reticulum 内部所有网络层安全策略。

---

## 插件、服务与 Bridge 集成

Hearth 不希望永远停留在一个完全固定的内建功能集合上。

### 插件源

插件源可以携带信任元数据与签名状态。对已签名的插件源 manifest，Hearth 支持 **Ed25519 公钥签名校验**，因此可以区分 trusted、verified、invalid、missing、not_required 等不同状态。

围绕这些目录，Web UI、CLI、API 现在已经补上完整的操作者闭环：

- 查看目录条目与来源信任状态
- 在安装前解析依赖关系
- 安装、更新、启用/禁用、卸载插件
- 查看最近插件操作历史和 sandbox boundary 元数据

### Services

系统已经具备 service-host 风格的目录与控制面，可以承载 runtime supervision、observation sync、backup manager 等运维子系统。

### Bridges

Bridge 目录是 Hearth 未来上层集成能力的一个重要方向。当前已经具备：

- bridge 列表与详情页
- 动作控制入口
- 来源信任与签名信息
- 健康检查
- 最近操作历史
- 投递测试

这为 webhook、协议桥、消息中继和未来更复杂的上层服务留下了清晰的演进路径。

---

## 部署方向

Hearth 是 **Linux-first** 的项目，仓库里已经包含一些部署相关资产：

- `packaging/systemd/hearth.service`
- `packaging/docker/Dockerfile`
- `packaging/docker/docker-compose.yml`
- `packaging/install.sh`

CLI 也支持通过 `hearth deploy ...` 渲染部署产物。

当前已经补上的部署辅助命令包括：

- `hearth deploy systemd`
- `hearth deploy dockerfile`
- `hearth deploy compose`
- `hearth deploy debian-control`
- `hearth deploy appliance-manifest`
- `hearth deploy openwrt`
- `hearth deploy migration-plan`
- `hearth deploy preflight`

典型部署模型包括：

- 家庭 Raspberry Pi 节点
- 小型常开 x86 节点
- Internet + Radio 的混合节点
- 小社区锚点节点
- 未来的 appliance 形态个人基础设施设备

---

## 仓库结构

```text
src/hearth/
  api/           FastAPI 路由
  cli/           Typer 命令行入口
  core/          应用装配、配置、生命周期、上下文
  crypto/        Ed25519 等信任校验相关能力
  discovery/     发现相关辅助模块
  interfaces/    接口抽象与校验
  monitor/       健康、watchdog、指标、诊断
  plugins/       插件 manifest 与加载辅助
  reticulum/     runtime adapter 层
  services/      node、config、backup、security、fleet、topology、bridges 等服务
  storage/       持久化与数据库访问
  system/        系统级辅助能力
  web/           Jinja 模板、i18n、Web 视图
examples/
  hearth.toml    本地开发配置
packaging/
  docker/        容器部署资产
  systemd/       系统服务文件
tests/
  单元测试与集成方向测试
```

---

## Hearth 想成为怎样的系统

Hearth 想补上的，是 Reticulum 生态中非常关键、但常常缺位的一层：

> **一个由用户自己掌控、可长期运行、可管理、可恢复的个人基础设施节点系统。**

也就是说，它希望做到：

- 不只是一个 runtime，而是一个运维产品
- 不只是能启动，而是真正可管理
- 不只是一个 dashboard，而是可恢复的系统
- 不只是本地实验，而是家庭和小社区可以长期依赖的基础设施基础

---

## 开发说明

开发时常用命令：

```bash
python -m pytest -q
python -m hearth.cli.main --help
python -m hearth.cli.main serve --config hearth.toml
```

如果你只是想先把界面跑起来、验证工作流、理解系统结构，那么示例配置是最直接的入口，因为它可以在没有真实 Reticulum 部署的情况下先提供一个完整的 mock-backed 节点界面。

---

## 项目边界

为了让项目持续健康，Hearth 需要保持边界清晰。

它应该优先做好：

- 传输节点运行与管理
- 可观测性与恢复能力
- 配置、生命周期与运维工作流
- 本地优先的控制面
- 通过插件和服务进行扩展

它不应该优先变成：

- 一个重量级社交平台
- 所有客户端应用的替代品
- 高度中心化的云控制器
- 一个什么都想塞进去、最终削弱节点核心的“大杂烩”

---

## 总结

**Hearth 是一个可部署、可管理、可观测、可恢复的 Personal Reticulum Transport Node 系统。**



