# Hearth 部署指南

[Docs](README.zh-CN.md) / [English](deployment.md)

这篇文档说明如何把 Hearth 部署到当前仓库最适合支持的几种环境中。

先记住你正在部署的到底是什么：

- **Reticulum** 是底层网络栈
- **Hearth** 是围绕 Personal Reticulum Transport Node 的控制面
- 所谓部署，不只是把一个 Web 服务启动起来，而是把这个节点控制面包装成一个可长期运行的基础设施组件

---

## 真实网络中的接入关系

部署 Hearth 时，最好先把三层关系想清楚：

- **运维者如何接入 Hearth 控制面**：Web、CLI、API
- **本地节点如何接入 Hearth 管理的节点**：通过本地接口进入这个 Transport Node
- **该节点如何接入更大的 Reticulum 网络**：通过 uplink / backbone / radio 接口连出去

所以一个真实部署，通常不只是把 `web.host` 和 `web.port` 配好，还要至少规划两类接口：

- 一个**本地接入接口**，给附近客户端节点使用
- 一个**上游接口**，让这个节点能接到更大的 Reticulum 网络

如果这层关系还不够清楚，请先看 [`network-model.zh-CN.md`](network-model.zh-CN.md)。

## 当前适合的部署方式

Hearth 目前最适合以下四种部署模式：

1. **本地开发运行**
   - 最适合 UI、API、CLI 和工作流体验
   - 使用内置的 mock runtime backend

2. **Linux + systemd 常驻部署**
   - 最适合 Raspberry Pi、家庭服务器或常开 Linux 主机
   - 也是 Hearth 当前最接近真实节点形态的部署方式

3. **Docker / Compose 容器部署**
   - 适合需要可复现打包方式的场景
   - 但要特别注意端口与配置文件的对齐

4. **通过 CLI 生成部署产物**
   - 适合为别的机器或别的环境生成部署模板

---

## 部署前准备

无论哪种方式，至少都需要：

- Python 3.12+
- 仓库本地副本或可安装包
- 一份 Hearth 配置文件
- 对访问范围有明确判断：只本机、局域网，还是更大范围

如果是 Linux 常驻部署，还建议准备：

- 专用服务用户
- 稳定的工作目录，例如 `/opt/hearth`
- 稳定的配置目录，例如 `/etc/hearth/hearth.toml`

---

## 先准备配置

Hearth 的行为由 TOML 配置文件控制。

最简单的起点是：

- `examples/hearth.toml`

部署时最需要关注的字段包括：

- `web.host`
- `web.port`
- `web.auth_mode`
- `security.admin_token`
- `security.allow_lan`
- `security.allow_wan`
- `reticulum.backend`
- `reticulum.managed_command`
- `reticulum.render_managed_config`
- `system.data_dir`

如果你准备在真实机器上运行，第一步就应该先改掉默认的 `security.admin_token`。

如果你计划在多台 Hearth 节点之间使用 rollout、upgrade、remote log sync 等能力，也要提前规划每个节点的管理地址。当前实现里通常意味着为远端节点登记一个可达的 `dashboard_url`，必要时还会把 token 放到查询串里，例如 `?token=...`。

---

## 方式一：本地开发运行

这是最快把 Hearth 跑起来的方式。

### 安装

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .[dev]
```

Windows PowerShell：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e .[dev]
```

### 准备配置

```bash
cp examples/hearth.toml ./hearth.toml
```

当前仓库自带的示例配置已经默认切到 `managed_rnsd`。如果你本机暂时还没有安装 `rnsd`，请先改回 `mock_process` 来做控制面评估。

### 启动

```bash
python -m hearth.cli.main serve --config hearth.toml
```

### 打开界面

```text
http://127.0.0.1:8480/login
```

### 适合什么时候用

适合你想做这些事时：

- 先看 UI 长什么样
- 先试 API / CLI
- 先验证配置流转
- 在没有真实 Reticulum 环境时先理解 Hearth 的工作方式

---

## 方式二：Linux + systemd 常驻部署

这是 Hearth 当前最自然、也最推荐的长期运行方式。

### 推荐目录结构

- 应用目录：`/opt/hearth`
- 配置目录：`/etc/hearth`
- 配置文件：`/etc/hearth/hearth.toml`
- 服务用户：`hearth`
- 服务组：`hearth`

### 基本步骤

#### 1. 创建用户和目录

```bash
sudo useradd --system --home /opt/hearth --shell /usr/sbin/nologin hearth || true
sudo mkdir -p /opt/hearth /etc/hearth
sudo chown -R hearth:hearth /opt/hearth /etc/hearth
```

#### 2. 拷贝仓库内容

```bash
sudo rsync -a ./ /opt/hearth/
sudo chown -R hearth:hearth /opt/hearth
```

#### 3. 安装 Hearth

仓库已经自带 `packaging/install.sh`：

```bash
cd /opt/hearth
sudo -u hearth sh packaging/install.sh
```

这个脚本会创建虚拟环境，并以 editable 模式安装包。

#### 4. 创建配置文件

```bash
sudo cp /opt/hearth/examples/hearth.toml /etc/hearth/hearth.toml
sudo chown hearth:hearth /etc/hearth/hearth.toml
```

至少要检查并修改：

- `security.admin_token`
- `web.host`
- `web.port`
- `security.allow_lan`
- `security.allow_wan`
- `system.data_dir`

#### 5. 安装 systemd 服务

仓库已经包含现成的 unit 文件：`packaging/systemd/hearth.service`

```bash
sudo cp /opt/hearth/packaging/systemd/hearth.service /etc/systemd/system/hearth.service
sudo systemctl daemon-reload
sudo systemctl enable hearth
sudo systemctl start hearth
```

#### 6. 检查服务状态

```bash
sudo systemctl status hearth
journalctl -u hearth -f
```

### 需要注意的点

- unit 文件里使用 `HEARTH_CONFIG=/etc/hearth/hearth.toml`
- 启动入口是 `hearth-api`
- 实际监听的 host 和 port 仍然来自 Hearth 配置文件，而不是 systemd 本身
- 如果 `web.host` 还是 `127.0.0.1`，即使服务已经跑起来，也仍然只能本机访问

---

## 方式三：Docker / Compose 部署

仓库里已经包含：

- `packaging/docker/Dockerfile`
- `packaging/docker/docker-compose.yml`

### 手动构建镜像

```bash
docker build -f packaging/docker/Dockerfile -t hearth:latest .
```

### 挂载配置目录运行

```bash
docker run --rm \
  -e HEARTH_CONFIG=/data/hearth.toml \
  -v $(pwd)/data:/data \
  -p 8480:8480 \
  hearth:latest
```

### 端口说明

当前仓库里的 Docker 相关默认端口已经统一为 `8480`，这和示例配置、应用默认 Web 端口保持一致。

也就是说：

- 默认情况下，保持 `web.port = 8480` 即可
- 如果你自定义了容器端口，就必须同步修改配置文件里的 `web.port`
- 应用实际监听的永远是配置文件中的 `web.port`

### Compose

仓库里的 `docker-compose.yml` 更适合作为起点模板，而不是完全自动化的生产部署。

如果你使用它，请确认挂载进去的 `/data/hearth.toml` 与映射出的端口保持一致。

---

## 方式四：通过 CLI 生成部署产物

Hearth 可以直接渲染部署文件。

### systemd unit

```bash
python -m hearth.cli.main deploy systemd --output ./hearth.service
```

### Dockerfile

```bash
python -m hearth.cli.main deploy dockerfile --output ./Dockerfile
```

### Compose 文件

```bash
python -m hearth.cli.main deploy compose --output ./docker-compose.yml
```

### 其他部署辅助文件

```bash
python -m hearth.cli.main deploy debian-control --output ./debian-control
python -m hearth.cli.main deploy appliance-manifest --output ./appliance.json
python -m hearth.cli.main deploy openwrt --output ./Makefile
python -m hearth.cli.main deploy migration-plan --output ./migration-plan.md
python -m hearth.cli.main deploy preflight --config hearth.toml
```

### 整体 bundle

```bash
python -m hearth.cli.main deploy bundle ./deploy-bundle
```

### 适合什么时候用

适合你想做这些事时：

- 自定义 workdir、config path、镜像名或端口
- 为另一台机器生成新的部署文件
- 把部署文件单独收集到 source tree 之外

---

## 当前推荐的部署路线

如果你现在只是评估 Hearth：

1. 先用示例配置在本地跑起来
2. 熟悉 UI、API 和 CLI 工作流
3. 再迁移到 Linux + systemd
4. 决定这个节点是继续停留在 `mock_process`，还是切换为受监督的 `managed_rnsd` runtime
5. 如果你要管理多台 Hearth 节点，在依赖 rollout / upgrade / remote-log sync 前，先给每个节点配置可达的 `dashboard_url`

如果你现在就想运行一个常在线节点，那么 **Linux + systemd** 是最直接的路径。

---

## 上线前检查清单

在你认为部署已经完成之前，至少确认这些事：

- 默认管理员 Token 已被替换
- 除非明确需要，否则 `allow_wan` 仍然关闭
- 重启机器后服务能自动启动
- `data_dir` 对运行用户可写
- 备份导出能正常执行
- Web UI 只暴露在你预期的网络接口上
- 暴露的 host / port 与配置文件一致
- 日志可以通过系统工具或 UI 正常查看
- 如果使用 `managed_rnsd`，宿主机能够成功执行 `rnsd`
- 如果使用 Fleet 远程运维能力，远端节点已经暴露正确的管理 URL 和 token 方案

---

## 常见问题

### 服务已经启动，但界面打不开

优先检查：

- `web.host`
- `web.port`
- 防火墙规则
- 容器端口映射是否正确
- systemd 服务是不是仍然只绑定到了 loopback

### Docker 容器启动了，但端口没有响应

最常见原因就是 `hearth.toml` 中的 `web.port` 与你发布出去的容器端口不一致。

### 界面能打开，但写入操作失败

检查：

- `data_dir` 的文件系统权限
- 服务用户的目录所有权
- Docker 挂载卷的权限

### 认证好像不工作

检查：

- `security.admin_token`
- `web.auth_mode`
- 你到底是在用 `Authorization`、`X-Hearth-Token`、查询参数 Token，还是 Web 登录 Cookie

---

## 总结

部署 Hearth，本质上是在部署一个节点控制面，而不是单纯部署一个 Web 服务。

当前最实用的理解方式是：

- 本地运行：适合理解和评估
- systemd：适合真实主机的长期运行
- Docker：适合刻意管理好的容器化环境
- CLI 生成部署产物：适合做打包和分发模板
