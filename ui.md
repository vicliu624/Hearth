# Hearth Web UI 页面结构（v0.1）

我建议 v0.1 的 UI 保持 **非常克制**，本质上是一个 **Node Control Panel**。

完整页面应该是这些：

```
Dashboard
Interfaces
Peers
Routes
Announcements
Logs
Configuration
Backup & Restore
API Docs
System
```

下面逐个解释。

---

# 1 Dashboard（节点概览）

这个页面是 **Hearth 打开后的默认页面**。

作用：

> 一眼看到节点健康状况。

展示内容：

* Node Status
* Health Status
* Uptime
* Interface Count
* Active Peers
* Route Count
* Announce Activity
* Recent Events

示例结构：

```
Node Status: Healthy
Uptime: 3d 12h

Interfaces: 3
Peers: 12
Routes: 42

Recent Events:
• Interface rnode_usb restarted
• New peer discovered
• Route updated
```

---

# 2 Interfaces

这个页面用于管理网络接口。

展示：

```
Interface Name
Type
Status
Health
RX/TX
Actions
```

例如：

```
tcp_backbone    TCP     Online     Healthy   12k / 9k
rnode_usb       RNode   Offline    Warning   0 / 0
lan_bridge      TCP     Online     Healthy   2k / 1k
```

操作：

* Start
* Stop
* Restart
* View Metrics

---

# 3 Peers

用于查看最近发现的节点。

展示：

```
Peer ID
Last Seen
Interface
Hop Count
```

例如：

```
ab3f91...    2 sec ago    tcp_backbone    2 hops
8c12ad...    1 min ago    rnode_usb       3 hops
```

用途：

* 观察网络活跃度
* 排查网络连接

---

# 4 Routes

用于查看 Reticulum 路由表。

展示：

```
Destination
Next Hop
Interface
Hops
Age
```

例如：

```
dest_2c1a   peer_ab3f91   tcp_backbone   2   45s
dest_991a   peer_8c12ad   rnode_usb      3   3m
```

这个页面主要是给 **高级用户 / 网络调试**。

---

# 5 Announcements

用于查看最近收到的 announce。

展示：

```
Source Node
Interface
Hop Count
Time
```

例如：

```
node_a31f   tcp_backbone   2   10 sec ago
node_8c11   rnode_usb      3   1 min ago
```

用途：

* 观察网络传播
* 调试 announce

---

# 6 Logs

系统日志查看。

支持：

* Level filter
* Module filter
* 时间过滤

例如：

```
INFO  reticulum.runtime started
WARN  interface rnode_usb timeout
INFO  peer ab3f91 discovered
```

---

# 7 Configuration

配置管理页面。

功能：

* 查看当前配置
* 编辑配置
* 校验配置
* 保存配置
* 重新加载

例如：

```
System
Reticulum
Interfaces
Security
Monitor
Plugins
```

保存配置后可以：

```
Apply changes
Restart node
```

---

# 8 Backup & Restore

节点备份。

可以导出：

```
Configuration
Node identity
Database
```

导出为：

```
hearth_backup_2026_03_10.tar.gz
```

恢复时：

* 上传备份
* 校验
* 恢复
* 重启节点

---

# 9 API Docs

自动生成的 API 文档。

因为后端使用 FastAPI，所以天然有：

```
/docs
```

这个页面主要是给：

* 开发者
* CLI 工具
* Conflux
* 其他应用

查看接口。

---

# 10 System（你刚刚没提到的）

这个页面是我建议加上的。

展示系统级信息：

```
Hearth Version
Reticulum Version
OS
CPU
Memory
Disk
```

以及：

```
Restart Service
Update Hearth
Check Updates
```

---

# 最终 UI 页面结构

所以完整结构应该是：

```
Dashboard
Interfaces
Peers
Routes
Announcements
Logs
Configuration
Backup & Restore
API Docs
System
```

---

# 你刚才提到的页面

你说的：

```
Dashboard
Logs
Config
Backup
API Docs
```

基本是 **管理功能页面**。

但你少说了 **三个很关键的网络页面**：

```
Interfaces
Peers
Routes
```

还有一个调试网络传播的重要页面：

```
Announcements
```

---

# 最关键的一点

Hearth 的 UI **绝对不能变成一个复杂系统管理后台**。

它的核心永远只有两件事：

1️⃣ **Node 状态可见**
2️⃣ **网络状态可见**

所以最核心的页面其实只有两个：

```
Dashboard
Interfaces
```

其它页面只是辅助。