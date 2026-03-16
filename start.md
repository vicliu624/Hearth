下面是一份 **《Hearth 1.x 功能分层表》**。
我把所有能力按三类分层：

* **核心（Core）**：1.x 必须完成，否则 Hearth 无法成为成熟节点平台
* **重要（Important）**：强烈建议 1.x 完成，但可以分阶段实现
* **延后（Later）**：1.x 可以预留接口，但不应该消耗太多精力

这张表的目标是 **避免项目失焦**，保证你始终优先建设真正重要的能力。

---

# Hearth 1.x 功能分层表

## 一、Node Runtime（节点运行能力）

| 功能                                 | 层级        | 作用                 |
| ---------------------------------- | --------- | ------------------ |
| Reticulum Runtime 生命周期管理           | Core      | 启动 / 停止 / 重启 RNS   |
| Interface 管理（TCP / Serial / Radio） | Core      | 管理多网络接口            |
| Interface Health Check             | Core      | 检测接口状态             |
| Watchdog 自动恢复                      | Core      | 自动重启异常组件           |
| 节点身份管理（Identity）                   | Core      | 初始化、备份、恢复 identity |
| 配置热更新                              | Important | 不必重启节点即可更新部分配置     |
| 启动前配置验证                            | Important | 防止错误配置导致节点不可用      |
| Runtime degradation 策略             | Important | 节点降级运行而非直接崩溃       |
| 节点迁移工具                             | Later     | 在新设备恢复节点           |

**核心目标：**

> 任何 Hearth 节点都必须能长期稳定运行。

---

# 二、Node Management（节点管理能力）

| 功能               | 层级   | 作用          |
| ---------------- | ---- | ----------- |
| Dashboard        | Core | 节点总体状态      |
| Interfaces 页面    | Core | 接口状态        |
| Peers 页面         | Core | 节点发现        |
| Routes 页面        | Core | 路由表         |
| Announcements 页面 | Core | announce 观察 |
| Logs 页面          | Core | 系统日志        |
| Configuration 页面 | Core | 配置管理        |
| Backup / Restore | Core | 节点备份恢复      |
| 系统信息页面           | Core | 版本、CPU、内存等  |

**核心目标：**

> 用户可以完全管理单个节点。

---

# 三、Security & Access（安全与权限）

| 功能                 | 层级        | 作用      |
| ------------------ | --------- | ------- |
| 管理员 Token          | Core      | 基本认证    |
| LAN / WAN 访问控制     | Core      | 管理界面安全  |
| RBAC 权限系统          | Important | 多用户管理   |
| 操作审计日志             | Important | 谁做了什么操作 |
| API Key / Token 管理 | Important | 外部系统调用  |
| 细粒度权限              | Later     | 接口级权限   |

**核心目标：**

> 节点可以被多人安全管理。

---

# 四、Observability（观测与监控）

| 功能                   | 层级        | 作用                 |
| -------------------- | --------- | ------------------ |
| 节点健康评分               | Core      | healthy / degraded |
| 接口统计                 | Core      | RX/TX / errors     |
| Peers 统计             | Core      | 活跃节点               |
| Routes 统计            | Core      | 路由数量               |
| 事件时间线                | Important | 网络事件               |
| 基础历史趋势               | Important | 节点变化               |
| Prometheus exporter  | Important | 外部监控               |
| Grafana dashboard 模板 | Later     | 运维可视化              |
| 自动告警                 | Later     | 节点异常通知             |

**核心原则：**

> Hearth 自己负责基础观测
> Prometheus 是外挂能力

---

# 五、Plugins（插件系统）

| 功能               | 层级        | 作用                    |
| ---------------- | --------- | --------------------- |
| 插件加载             | Core      | 扩展能力                  |
| 插件启停             | Core      | 管理插件                  |
| 插件元信息            | Core      | name / version        |
| 插件兼容性校验          | Important | 防止版本冲突                |
| 插件权限声明           | Important | 安全                    |
| 插件依赖声明           | Important | 自动加载依赖                |
| 插件源索引同步          | Important | 管理本地/远端插件源索引          |
| 插件源 Ed25519 签名校验 | Important | 校验插件源清单真实性与来源可信性     |
| 插件仓库索引           | Later     | 更完整的插件目录与生态入口         |
| 插件商店 UI          | Later     | 用户安装                  |

**核心目标：**

> Hearth 是可扩展平台，而不是固定软件。

**补充说明：**

> 1.x 阶段建议把“插件源索引同步 + Ed25519 公钥签名校验”作为插件系统的默认安全基线，
> 这样第三方插件源至少具备可验证的来源真实性。

**推荐配置示例：**

```toml
[[plugin_sources]]
name = "community"
index_url = "https://example.net/hearth/community.json"
label = "Community Source"
public_key = "ed25519:0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
signature_algorithm = "ed25519"
signature_required = true
```

---

# 六、Services（上层服务）

| 功能                | 层级        | 作用           |
| ----------------- | --------- | ------------ |
| Service Plugin 框架 | Important | 服务宿主         |
| 服务生命周期管理          | Important | start/stop   |
| 服务日志              | Important | 调试           |
| 服务健康检查            | Important | watchdog     |
| 服务资源限制            | Later     | CPU / memory |
| 服务依赖管理            | Later     | 数据库 / cache  |
| IM 服务插件           | Later     | 聊天           |
| 文件中继服务            | Later     | 文件投递         |
| Bridge 服务         | Important | 协议桥接         |

**核心原则：**

> Hearth 先成为服务宿主，再慢慢增加服务。

---

# 七、Fleet Management（多节点管理）

| 功能           | 层级        | 作用       |
| ------------ | --------- | -------- |
| 节点注册         | Important | 多节点      |
| 节点 inventory | Important | 节点列表     |
| 节点标签         | Important | 分类       |
| 节点分组         | Important | 管理       |
| 健康聚合视图       | Important | 总览       |
| 远程状态查看       | Important | 多节点      |
| 远程日志查看       | Later     | 运维       |
| 批量升级         | Later     | fleet 运维 |
| 配置模板         | Later     | 快速部署     |

**核心目标：**

> 多台 Hearth 可以形成可管理的网络。

---

# 八、Topology & Network Intelligence（网络理解）

| 功能     | 层级        | 作用      |
| ------ | --------- | ------- |
| 拓扑可视化  | Important | 网络图     |
| 路径热图   | Later     | traffic |
| 关键节点识别 | Later     | relay   |
| 孤岛检测   | Later     | 网络断裂    |
| 路径变化分析 | Later     | 网络健康    |
| 连通性评分  | Later     | 网络质量    |

**核心目标：**

> 从“看到节点”升级到“理解网络”。

---

# 九、Packaging & Deployment（部署能力）

| 功能           | 层级        | 作用            |
| ------------ | --------- | ------------- |
| Linux 安装包    | Core      | Debian/Ubuntu |
| systemd 服务   | Core      | 自动运行          |
| 一键安装脚本       | Core      | 快速部署          |
| Docker Image | Important | 容器部署          |
| Helm / k8s   | Later     | 云环境           |
| OpenWrt 版本   | Later     | 路由器           |
| Appliance 镜像 | Important | 专用设备          |

---

# Hearth 1.x 最重要的 12 个功能

如果只看最核心能力，其实只有这些：

1. Reticulum runtime 管理
2. Interface 管理
3. Watchdog 自动恢复
4. Dashboard
5. Peers / Routes / Announces 可视化
6. Logs
7. Config 管理
8. Backup / Restore
9. 插件系统基础版
10. RBAC 基础权限
11. Prometheus exporter
12. Fleet 节点列表

做到这些，Hearth 就已经是 **成熟基础设施节点系统**。

---

# 1.x 结束时 Hearth 应该是什么样

到 **Hearth 1.x 完整形态**，系统应该是：

* 稳定运行 Reticulum
* 管理多种网络接口
* 支持插件扩展
* 支持多用户管理
* 支持多节点集中管理
* 能够理解网络状态
* 能够承载简单网络服务
