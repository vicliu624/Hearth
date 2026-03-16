# Hearth 快速开始

[Docs](README.zh-CN.md) / [English](getting-started.md)

这篇文档的目标，是让你用最短路径在本地把 Hearth 跑起来，并看到一个可用的节点控制面。

在开始输入命令之前，先把上下文说清楚：

- **Reticulum** 是一个去中心化网络栈，允许节点通过不同类型的传输方式互联，而不必完全依赖中心化服务器。
- **Hearth** 是围绕这个网络栈之上的节点控制面软件，用来把一个 Personal Reticulum Transport Node 真正运行成可管理、可观察、可恢复的基础设施节点。
- 所以这篇文档不是在教你启动一个普通后台，也不是在教你安装一个聊天应用，而是在带你启动一个 **Personal Reticulum Transport Node 控制面**。

完成这篇文档后，你将拥有：

- 一个已经运行起来的本地 Hearth 实例
- 一个由托管 `rnsd` 或 mock runtime 驱动、可在 Web UI 里查看的 Reticulum 节点界面
- 可正常使用的 CLI 和 API 入口，用来查看和操作这个节点

当前仓库里的示例配置已经默认切到 **`managed_rnsd`**。如果你的本机已经安装了 Reticulum，这样可以直接让 Hearth 监督真实 `rnsd` 进程；如果你暂时还没有安装 Reticulum，也没关系，把 backend 改成 `mock_process`，其余步骤不变。

## 先分清“接入控制面”和“接入网络”

这篇快速开始主要是在带你接入 **Hearth 控制面**，也就是：

- 跑起 Web UI
- 跑起 CLI / API
- 看见一个受管节点的状态界面

它**不是**在一步之内把你的设备接进真实更大的 Reticulum 网络。

真实的网络接入还需要你后续配置：

- 一个真实的 Reticulum runtime backend
- 一个面向本地客户端的接口
- 一个面向更大网络的 uplink / backbone 接口

如果你想先把这一层关系搞清楚，再继续往下做，请先看 [`network-model.zh-CN.md`](network-model.zh-CN.md)。

## 环境要求

- Python 3.12+
- 当前仓库的一份本地副本

## 安装

### Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e .[dev]
```

### Linux / macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .[dev]
```

## 准备配置文件

```bash
cp examples/hearth.toml ./hearth.toml
```

在 Windows 上使用：

```powershell
Copy-Item examples\hearth.toml .\hearth.toml
```

示例配置当前默认使用：

- `reticulum.backend = "managed_rnsd"`
- `reticulum.managed_command = "rnsd"`
- `web.host = "127.0.0.1"`
- `web.port = 8480`

如果你的环境里还没有 `rnsd`，先改成：

```toml
[reticulum]
backend = "mock_process"
```

## 启动服务

```bash
python -m hearth.cli.main serve --config hearth.toml
```

## 打开 Web 界面

访问：

```text
http://127.0.0.1:8480/login
```

使用 `hearth.toml` 里的管理员 Token 登录。

登录后，建议优先点开这几个页面：

- `Roles`：查看内置 RBAC，并创建自定义角色
- `Plugins` / `Plugin Sources`：查看插件目录信任状态、Ed25519 校验结果、依赖安装计划和插件历史
- `Backup`：创建备份、快照、执行快照清理、查看灾难恢复清单
- `Remote Logs`：聚合本地日志、远端推送日志和 Fleet 拉取同步结果
- `Upgrade` / `Rollout`：理解多节点运维动作如何被调度

## 试一下 API

```bash
curl -H "X-Hearth-Token: change-me" http://127.0.0.1:8480/api/node/status
```

## 试一下 CLI

```bash
python -m hearth.cli.main status --config hearth.toml
python -m hearth.cli.main interfaces list --config hearth.toml
python -m hearth.cli.main peers list --config hearth.toml
python -m hearth.cli.main plugins catalog --config hearth.toml
python -m hearth.cli.main backup snapshot --config hearth.toml
python -m hearth.cli.main remote-logs sync --config hearth.toml
python -m hearth.cli.main security roles list --config hearth.toml
```

## 重要提醒

在把 Hearth 暴露到本地开发环境之外之前，请至少先完成下面几件事：

- 修改默认的 `security.admin_token`
- 检查 `security.allow_lan` 和 `security.allow_wan`
- 确认 `web.host` 与 `web.port` 是否符合你的部署目标
- 决定这个节点是继续停留在 `mock_process`，还是切换为真实托管的 `managed_rnsd`
- 不要直接把示例配置原样暴露到公网
