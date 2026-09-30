# Hearth 界面术语与文案约定

中文和英文界面由维护者根据实际行为编写，不使用外部翻译接口。
文案保存在 `src/hearth/web/locales/`，Python 模板和 React 共用。

| 概念 | 中文 | English | 使用边界 |
| --- | --- | --- | --- |
| node | 节点 | node | 运行 Reticulum 的设备或进程所代表的节点 |
| peer | 对端节点 | peer | 已观测到的其他节点；不能仅凭历史记录声称在线 |
| interface | 网络接口；短标签用接口 | interface | TCP、本地网络、串口或无线电链路的接入接口 |
| path / route record | 路径 | path | 本机学习的目的地可达路径；API `/routes` 保持兼容 |
| announce | 通告 | announce | Reticulum 的目的地通告；不写成“广播消息”，也不等同于路径快照 |
| runtime | 运行时 | runtime | 被管理的 Reticulum 进程；面向用户的操作写“启动／停止／重启节点” |
| observation | 采集结果／采集数据 | observation | 本次获取的运行信息；与配置中期望的状态分开 |
| stale | 数据已过期 | stale data | 超出刷新时限；不能直接等同于离线 |
| desired state | 期望状态 | desired state | 用户要求的运行或停止状态；重启管理服务不得改写 |
| saved configuration | 已保存配置／配置草稿 | saved configuration / configuration draft | 已写入文件，但尚未应用 |
| active configuration | 生效配置 | active configuration | 当前服务图和运行时使用的配置 |
| apply | 应用配置 | apply configuration | 切换生效配置，并核验运行结果；保存、重启不是同义词 |
| watchdog | 自动恢复；详细说明可用看门狗 | automatic recovery / watchdog | 根据期望状态恢复故障；主动停止不是故障 |
| fleet | 多节点管理 | fleet management | 节点清单、分组、健康汇总和远程管理 |
| rollout | 批量操作 | batch operation | 记录、计划、执行、完成必须分别表达 |
| snapshot | 快照 | snapshot | 某个时间点保存的数据或备份；不得暗示持续同步 |

## 约定

- 按钮直接写动作：停止节点、保存草稿、应用配置。视觉风格不改变操作含义。
- 不用“小岛休息”“节点配方”“数据微风”等隐喻命名功能或状态。
- 有数据来源和时间才能描述“在线”“活跃”；历史发现用“已观测到”。
- 采集失败、没有数据、数值为零是三种不同情况。
- 区分接收／发送字节数、数据包数和速率。单位必须与运行时字段一致。
- 模板关联不等于远程配置已应用；操作已登记不等于操作已完成。
- 保留协议名、API 路径、命令、配置键、哈希及用户输入的名称；不翻译机器标识符。
- 说明应写明影响和下一步；错误信息不能只写“出错了”。
- 中文不夹杂可正常表达的普通英文。英文说明同样要准确，不逐字对应中文语序。
- 中英文占位符必须一致；新增界面文案必须同时补齐两种语言。
