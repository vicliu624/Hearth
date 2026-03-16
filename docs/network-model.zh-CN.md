# Hearth 节点接入与网络接入模型

[Docs](README.zh-CN.md) / [English](network-model.md)

很多人第一次接触 Hearth 时，最容易混淆的一点就是：“接入 Hearth”到底是在说什么。

实际上，这里经常混在一起的是四件不同的事情：

1. **运维者接入 Hearth 控制面**
   - 通过浏览器、CLI 或 API 登录和管理 Hearth。

2. **本地客户端接入 Hearth 所管理的节点**
   - 这里的“客户端”不是浏览器，而是运行在手机、电脑、嵌入式设备上的 Reticulum 应用或节点。

3. **Hearth 所管理的 Reticulum Transport Node 接入更大的网络**
   - 也就是这个基础设施节点如何通过 uplink / backbone / radio 等接口，和更广泛的 Reticulum 网络互联。

4. **你到底应该先从哪种客户端和哪种网络形态开始**
   - 这关系到“推荐用什么”“Hearth 有没有内置”。

如果不把这几层分开，文档就很容易看起来像是在说“打开一个 Web 后台”，却没有说明真正的网络路径和实际生态。

---

## 先分清三层路径

可以把 Hearth 放进下面这个模型里理解：

```text
运维者浏览器 / CLI / API
            |
            v
      Hearth 控制面
            |
            v
Hearth 所管理的 Reticulum 节点
      |                      |
      |                      |
本地接入接口              上游 / 骨干接口
      |                      |
本地客户端节点          更大的 Reticulum 网络
```

这里最关键的一点是：

- **Hearth 本身是控制面**
- **真正承载 Reticulum 流量的是 Hearth 所管理的 runtime 和 interfaces**

换句话说，Hearth 不替代 Reticulum 数据面；它负责把这个数据面运行好、管起来、看得见、修得动。

---

## 1. 人是怎么接入 Hearth 的？

这是最容易理解的一层。

运维者通过以下方式接入 Hearth 控制面：

- 浏览器访问 Web UI，例如 `http://127.0.0.1:8480/login`
- CLI，例如 `hearth status --config hearth.toml`
- REST API，例如 `GET /api/node/status`

这一层的目的，是：

- 登录
- 查看状态
- 修改配置
- 启停 runtime 和 interfaces
- 查看 peers / routes / announces
- 执行备份、恢复、维护和安全管理

这一层**不是** Reticulum 流量的数据通路。

也就是说：

- 你的浏览器访问的是 Hearth 管理面
- 不是在用浏览器“加入 Reticulum 网络”

---

## 2. 本地客户端到底是什么？

这里必须把“本地客户端”说具体，否则“本地节点接入 Hearth”会显得非常抽象。

本地客户端指的是：

- 运行在手机上的 Reticulum 应用
- 运行在笔记本或台式机上的 Reticulum 应用
- 运行在嵌入式设备上的 Reticulum 节点程序
- 你自己开发的、基于 Reticulum 的上层应用

这些客户端本身也要理解或使用 Reticulum，它们不是普通浏览器标签页。

更准确的说法不是“客户端接入 Hearth 的网页”，而是：

> **本地客户端接入的是 Hearth 所管理的 Reticulum Transport Node。**

所以典型关系更像这样：

```text
手机 / 笔记本 / 嵌入式设备
            |
            v
本地 Reticulum 客户端或应用
            |
            v
Hearth 管理的本地接入接口
            |
            v
Hearth 管理的 Reticulum 节点
```

### 典型本地客户端示例

下面这些是目前 Reticulum 生态里最容易理解的例子：

- **Sideband**
  - 官方项目定位是一个面向 Android、Linux 和 macOS 的通信应用，适合从“真实用户设备”视角理解本地客户端是什么。
  - 文档 / 项目主页：<https://github.com/markqvist/Sideband>

- **Nomad Network**
  - 官方项目定位是一个基于 LXMF 和 LXMRouter 的通信平台，适合从“更偏网络原生 / 节点原生”的角度理解客户端和服务如何工作。
  - 文档 / 项目主页：<https://github.com/markqvist/NomadNet>

- **你自己的 Reticulum 应用**
  - 如果你不是在找现成客户端，而是在构建自己的工具、设备或服务，那么任何基于 Reticulum 的应用都可以成为这里所说的“本地客户端”。
  - Reticulum 项目主页：<https://github.com/markqvist/Reticulum>

### 对 Hearth 来说，这意味着什么？

Hearth 不是这些客户端本身。

Hearth 负责的是：

- 让本地客户端有一个稳定、可管理的节点可以接入
- 让你能看见这个节点当前有哪些 peers、routes、announces
- 让你能控制接口、配置、安全和恢复流程

也就是说，Hearth 更像是这些本地客户端背后的“家庭节点 / 社区节点控制面”。

---

## 3. 本地客户端是通过什么接进来的？

这一步不是通过 Web 登录，而是通过**接口**。

这些本地接入接口，在 Reticulum 官方文档和部署模型里，通常可能是：

- 局域网内自动发现或本地链路接口
  - 官方接口文档：AutoInterface
  - <https://reticulum.network/manual/interfaces.html#the-autointerface>

- 局域网或本地 IP 网络里的 TCP 接口
  - 官方接口文档：TCPServerInterface / TCPClientInterface
  - <https://reticulum.network/manual/interfaces.html#the-tcpserverinterface>
  - <https://reticulum.network/manual/interfaces.html#the-tcpclientinterface>

- 串口或无线电接口
  - 官方接口文档：RNodeInterface
  - <https://reticulum.network/manual/interfaces.html#the-rnodeinterface>

也就是说，“接入 Hearth 管理的节点”本质上是在接入这些接口背后的那个 Transport Node。

在 Hearth 当前仓库的实现里，接口管理层已经内置了 `serial` 和 `rnode` 类型驱动；更广义的本地接入和上游接入模型，则仍然要结合你实际使用的 Reticulum runtime 来落地。

---

## 4. “更大网络”到底是什么？

“更大网络”不是一个名叫 “Hearth Cloud” 的单一官方网络，也不是 Hearth 自己内置的一张默认公网。

对 Reticulum 来说，更大网络可能是下面任何一种：

- **你自己的家庭 / 局域网网络段**
  - 几台设备通过本地链路或局域网互联
- **你自己的社区网络**
  - 一组固定节点通过有线、无线电或混合链路互联
- **基于 Internet 的更远端互联**
  - 通过 TCP/IP 把节点连到更远的基础设施节点
- **无线电网络**
  - 通过 RNode / LoRa 等无线链路连到本地或区域性网络
- **匿名覆盖网络中的 Reticulum 拓扑**
  - 通过 I2P 等方式建立更隐蔽的网络连接

理解“更大网络”的最好官方入口是 Reticulum 的网络理解文档：

- **Building Networks**
  - <https://reticulum.network/manual/understanding.html>

### 常见的“更大网络”接入方式

如果你想把 Hearth 节点真正接出本机和本地小范围，常见方式包括：

- **TCP 上游 / backbone**
  - 用于把节点接到其他基础设施节点或更远的 IP 网络
  - 文档：<https://reticulum.network/manual/interfaces.html#the-tcpclientinterface>

- **本地提供 TCP / IP 入口，同时再向外 uplink**
  - 适合家庭节点或社区入口节点
  - 文档：<https://reticulum.network/manual/interfaces.html#the-tcpserverinterface>

- **RNode / 无线电上游或边缘接入**
  - 适合无线电链路、野外节点或社区无线网络
  - 文档：<https://reticulum.network/manual/interfaces.html#the-rnodeinterface>

- **I2P 覆盖网络**
  - 适合需要更隐蔽或更特殊网络条件的场景
  - 文档：<https://reticulum.network/manual/interfaces.html#the-i2pinterface>

所以 Hearth 接入更大网络的方式，本质上不是“自己变成一个新协议”，而是通过它所管理的节点接口，把这个节点接进更大的 Reticulum 拓扑里。

---

## 5. 两个最典型的部署例子

### 例子一：家庭常驻节点

```text
手机 / 笔记本 / 家庭设备
        |
        v
本地 LAN / TCP 接口
        |
        v
Hearth 节点
        |
        v
TCP uplink
        |
        v
更大的 Reticulum 网络
```

这个模型里：

- Hearth 节点是家里的本地锚点
- 家里的设备优先接入自己的节点
- 节点再通过 uplink 接入更广泛的网络

### 例子二：无线电混合节点

```text
野外节点 / 手持节点
        |
        v
无线电链路
        |
        v
Hearth 主机上的 RNode / Serial 接口
        |
        v
Hearth 管理的 Reticulum 节点
        |
        v
TCP uplink / 社区骨干
        |
        v
更大的 Reticulum 网络
```

这个模型里：

- Hearth 处在“本地无线电网络”和“更大 IP / 社区网络”之间
- 它不只是控制台，也是在运行一个实际的桥接型基础设施节点

---

## 6. 有没有推荐的起步方式？

下面这些是**基于官方生态和当前 Hearth 仓库状态的建议**，属于工程推荐，不是 Hearth 当前仓库内置的默认值。

### 如果你想先找“本地客户端”

我更推荐从下面两个里选一个开始：

- **Sideband**
  - 更接近“真实用户设备上的客户端应用”
  - 适合先理解“手机 / 笔记本通过自己的节点进入网络”这件事
  - <https://github.com/markqvist/Sideband>

- **Nomad Network**
  - 更适合已经开始理解节点、消息路由和网络原生工作方式的人
  - <https://github.com/markqvist/NomadNet>

### 如果你想先把 Hearth 节点接进更大网络

我更推荐从下面两种拓扑里选一个开始：

- **家庭 / 实验室起步**
  - 一个本地接入接口
  - 一个 TCP 上游接口
  - 原因是最容易调试、最容易看 peers / routes / announces 是否开始出现

- **无线电起步**
  - 一个 RNode / Serial 接口
  - 如果需要更大范围，再叠加一个 TCP 上游
  - 适合你已经有无线电硬件或社区无线链路的场景

### 不太推荐的起步方式

- 一开始就假设存在一个“Hearth 自带的默认公网”
- 一开始就跳过本地客户端和接口建模，只看 Web 页面
- 一开始就把 mock backend 当成真实网络接入完成

---

## 7. Hearth 有没有内置这些？

这一点必须说清楚。

### Hearth **没有**内置的东西

Hearth 当前仓库**没有**内置：

- Sideband 这类客户端应用
- Nomad Network 这类上层网络应用
- 一张默认可直接加入的公开 Reticulum 网络名单
- 一个自动帮你连出去的官方 backbone 配置

也就是说：

> **Hearth 不会替你自动选择“接哪个客户端、连哪张公网、用哪个社区骨干”。**

这些都需要你根据自己的部署目标来选。

### Hearth 当前**有**的内置能力

Hearth 当前仓库已经内置的，主要是控制面能力：

- Web / CLI / API 管理面
- `mock_process` 与 `external_process` 两种 runtime backend 入口
- 基础的接口管理框架
- 当前仓库内置的 `serial` 与 `rnode` 接口驱动
- 配置、备份、监控、安全、插件、服务、桥接等运维能力

### 这意味着什么？

这意味着 Hearth 现在更像：

- **你的节点控制中心**
- **你的基础设施节点运维层**

而不是：

- 一个已经把整个 Reticulum 生态打包进来的“一体化客户端”
- 一个自带默认公网入口的托管平台

---

## 8. 当前仓库已经做到哪里？

这是理解项目当前阶段时非常重要的一点。

当前仓库里：

- 本地快速开始默认使用 `reticulum.backend = "mock_process"`
- 这非常适合先把 UI、API、配置和工作流跑通
- 但它**不是**一个已经接入真实更大 Reticulum 网络的完整演示

可以把当前状态理解成：

- **控制面已经基本成型**
- **真实网络数据面的接入方式已经有清晰模型**
- **真实接入需要你在部署时配置真正的 runtime 和接口**

向真实网络接入迈进的关键配置方向包括：

- 把 runtime 从 mock backend 切换到真实 backend，例如 `external_process`
- 配置真实的本地接入接口
- 配置真实的 uplink / backbone 接口
- 在运行后检查 peers、routes、announces 是否正常出现

---

## 9. 如果你想把节点真正接进网络，至少要做什么？

一个最小但真实的思路通常是：

1. 准备一台常开 Linux 主机
2. 在上面部署 Hearth
3. 配置安全项，例如 `admin_token`、`allow_lan`、`allow_wan`
4. 配置一个真实 Reticulum runtime backend
5. 选择一个本地客户端方向，例如 Sideband 或 Nomad Network
6. 配置至少一个本地接入接口
7. 配置至少一个 uplink / backbone / radio 接口
8. 启动节点并检查：
   - interfaces 是否在线
   - peers 是否开始出现
   - routes 是否被学习到
   - announces 是否能观察到

这一步完成以后，Hearth 才真正从“一个本地控制台演示”进入“一个实际网络节点系统”的阶段。

---

## 10. 推荐继续阅读

如果你现在最关心的是“怎么把节点真正接入起来”，建议按这个顺序继续看：

1. [`getting-started.zh-CN.md`](getting-started.zh-CN.md)
   - 先把控制面跑起来，理解基本工作流。
2. [`deployment.zh-CN.md`](deployment.zh-CN.md)
   - 再把它放到适合长期运行的机器上。
3. [`config-reference.zh-CN.md`](config-reference.zh-CN.md)
   - 然后理解 `reticulum`、`web`、`security` 与 `[[interfaces]]` 配置。
4. [`security.zh-CN.md`](security.zh-CN.md)
   - 在你让别的设备真正接入前，先把暴露范围和认证模型搞清楚。

---

## 总结

最容易记住的一句话是：

> **Hearth 不是客户端节点直接“登录进去”的网络本身；Hearth 是用来运行和管理那个网络节点的控制面，而本地客户端与更大网络，都是通过它所管理的接口进入和连出的。**
