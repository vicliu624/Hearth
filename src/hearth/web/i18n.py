from __future__ import annotations



from urllib.parse import urlencode



from fastapi import Request





DEFAULT_LOCALE = "zh-CN"

LANG_COOKIE_NAME = "hearth_lang"

SUPPORTED_LOCALES = {

    "zh-CN": "简体中文",

    "en": "English",

    "ja": "日本語",

    "ko": "한국어",

    "es": "Español",

}

SUPPORTED_LOCALES = {

    "zh-CN": "简体中文",

    "en": "English",

    "ja": "日本語",

    "ko": "한국어",

    "es": "Español",

}

SUPPORTED_LOCALES = {

    "zh-CN": "简体中文",

    "en": "English",

    "ja": "日本語",

    "ko": "한국어",

    "es": "Español",

}

LOCALE_ALIASES = {

    "zh": "zh-CN",

    "zh-cn": "zh-CN",

    "zh-hans": "zh-CN",

    "en-us": "en",

    "en-gb": "en",

    "ja-jp": "ja",

    "ko-kr": "ko",

    "es-es": "es",

    "es-mx": "es",

}



TRANSLATIONS: dict[str, dict[str, str]] = {

    "zh-CN": {

        "app.tagline": "Personal Reticulum Transport Node 控制台",

        "nav.dashboard": "总览",

        "nav.logs": "日志",

        "nav.config": "配置",

        "nav.backup": "备份",

        "nav.docs": "API 文档",

        "locale.label": "语言",

        "page.dashboard": "Hearth 总览",

        "page.logs": "Hearth 日志",

        "page.config": "Hearth 配置",

        "page.backup": "Hearth 备份",

        "dashboard.node_status": "节点状态",

        "dashboard.stats": "统计",

        "dashboard.interfaces": "接口状态",

        "dashboard.peers": "最近节点",

        "dashboard.routes": "最近路由",

        "dashboard.announces": "最近广播",

        "dashboard.logs": "最近日志",

        "field.node": "节点",

        "field.peer": "节点",

        "field.runtime": "运行时",

        "field.health": "健康",

        "field.uptime": "在线时长",

        "field.pid": "进程号",

        "field.interfaces": "接口数",

        "field.peers": "节点数",

        "field.routes": "路由数",

        "field.announces": "广播数",

        "field.restarts": "重启次数",

        "field.name": "名称",

        "field.type": "类型",

        "field.status": "状态",

        "field.source": "来源",

        "field.level": "级别",

        "field.message": "消息",

        "field.time": "时间",

        "field.interface": "接口",

        "field.hops": "跳数",

        "field.destination": "目标",

        "field.next_hop": "下一跳",

        "field.summary": "摘要",

        "field.archive_path": "归档路径",

        "field.config": "配置文件",

        "field.database": "数据库",

        "field.identity": "身份文件",

        "field.backups_dir": "备份目录",

        "empty.interfaces": "当前没有已配置接口。",

        "empty.peers": "暂无节点数据。",

        "empty.routes": "暂无路由数据。",

        "empty.announces": "暂无广播数据。",

        "empty.logs": "暂无日志。",

        "empty.archives": "暂无备份归档。",

        "logs.title": "日志列表",

        "logs.event_type": "事件类型",

        "config.title": "配置文件",

        "config.current_path": "当前配置路径：{path}",

        "config.readonly_hint": "当前页面仅提供查看；编辑与保存请调用 API `POST /api/config/save-raw` 或 CLI `hearth config save-raw`。",

        "backup.title": "备份计划",

        "backup.archives": "已有归档",

        "backup.hint": "导出与导入可通过 API `/api/backup/export`、`/api/backup/import` 或 CLI `hearth backup export/import` 完成。",

        "auth.required": "需要管理员令牌。",

        "auth.invalid": "管理员令牌无效。",

        "network.denied": "当前来源地址不允许访问此服务。",

        "value.running": "运行中",

        "value.stopped": "已停止",

        "value.starting": "启动中",

        "value.crashed": "已崩溃",

        "value.healthy": "健康",

        "value.warning": "告警",

        "value.degraded": "降级",

        "value.critical": "严重",

        "value.error": "错误",

        "value.unknown": "未知",

        "value.disabled": "已禁用",

    },

    "en": {

        "app.tagline": "Personal Reticulum Transport Node control plane",

        "nav.dashboard": "Dashboard",

        "nav.logs": "Logs",

        "nav.config": "Config",

        "nav.backup": "Backup",

        "nav.docs": "API Docs",

        "locale.label": "Language",

        "page.dashboard": "Hearth Dashboard",

        "page.logs": "Hearth Logs",

        "page.config": "Hearth Config",

        "page.backup": "Hearth Backup",

        "dashboard.node_status": "Node Status",

        "dashboard.stats": "Statistics",

        "dashboard.interfaces": "Interfaces",

        "dashboard.peers": "Recent Peers",

        "dashboard.routes": "Recent Routes",

        "dashboard.announces": "Recent Announces",

        "dashboard.logs": "Recent Logs",

        "field.node": "Node",

        "field.peer": "Peer",

        "field.runtime": "Runtime",

        "field.health": "Health",

        "field.uptime": "Uptime",

        "field.pid": "PID",

        "field.interfaces": "Interfaces",

        "field.peers": "Peers",

        "field.routes": "Routes",

        "field.announces": "Announces",

        "field.restarts": "Restarts",

        "field.name": "Name",

        "field.type": "Type",

        "field.status": "Status",

        "field.source": "Source",

        "field.level": "Level",

        "field.message": "Message",

        "field.time": "Time",

        "field.interface": "Interface",

        "field.hops": "Hops",

        "field.destination": "Destination",

        "field.next_hop": "Next Hop",

        "field.summary": "Summary",

        "field.archive_path": "Archive Path",

        "field.config": "Config",

        "field.database": "Database",

        "field.identity": "Identity",

        "field.backups_dir": "Backups Dir",

        "empty.interfaces": "No interfaces are configured.",

        "empty.peers": "No peer data yet.",

        "empty.routes": "No route data yet.",

        "empty.announces": "No announce data yet.",

        "empty.logs": "No logs yet.",

        "empty.archives": "No backup archives yet.",

        "logs.title": "Log Entries",

        "logs.event_type": "Event Type",

        "config.title": "Configuration",

        "config.current_path": "Current config path: {path}",

        "config.readonly_hint": "This page is read-only. Edit and save through API `POST /api/config/save-raw` or CLI `hearth config save-raw`.",

        "backup.title": "Backup Plan",

        "backup.archives": "Available Archives",

        "backup.hint": "Export and import are available through API `/api/backup/export`, `/api/backup/import`, or CLI `hearth backup export/import`.",

        "auth.required": "Admin token is required.",

        "auth.invalid": "Admin token is invalid.",

        "network.denied": "This client address is not allowed to access the service.",

        "value.running": "Running",

        "value.stopped": "Stopped",

        "value.starting": "Starting",

        "value.crashed": "Crashed",

        "value.healthy": "Healthy",

        "value.warning": "Warning",

        "value.degraded": "Degraded",

        "value.critical": "Critical",

        "value.error": "Error",

        "value.unknown": "Unknown",

        "value.disabled": "Disabled",

    },

    "ja": {

        "app.tagline": "Personal Reticulum Transport Node の管理コンソール",

        "nav.dashboard": "ダッシュボード",

        "nav.logs": "ログ",

        "nav.config": "設定",

        "nav.backup": "バックアップ",

        "nav.docs": "API ドキュメント",

        "locale.label": "言語",

        "page.dashboard": "Hearth ダッシュボード",

        "page.logs": "Hearth ログ",

        "page.config": "Hearth 設定",

        "page.backup": "Hearth バックアップ",

        "dashboard.node_status": "ノード状態",

        "dashboard.stats": "統計",

        "dashboard.interfaces": "インターフェース",

        "dashboard.peers": "最近のピア",

        "dashboard.routes": "最近のルート",

        "dashboard.announces": "最近のアナウンス",

        "dashboard.logs": "最近のログ",

        "field.node": "ノード",

        "field.peer": "ピア",

        "field.runtime": "ランタイム",

        "field.health": "ヘルス",

        "field.uptime": "稼働時間",

        "field.pid": "PID",

        "field.interfaces": "インターフェース数",

        "field.peers": "ピア数",

        "field.routes": "ルート数",

        "field.announces": "アナウンス数",

        "field.restarts": "再起動回数",

        "field.name": "名前",

        "field.type": "種類",

        "field.status": "状態",

        "field.source": "ソース",

        "field.level": "レベル",

        "field.message": "メッセージ",

        "field.time": "時間",

        "field.interface": "インターフェース",

        "field.hops": "ホップ数",

        "field.destination": "宛先",

        "field.next_hop": "次ホップ",

        "field.summary": "概要",

        "field.archive_path": "アーカイブパス",

        "field.config": "設定ファイル",

        "field.database": "データベース",

        "field.identity": "ID ファイル",

        "field.backups_dir": "バックアップディレクトリ",

        "empty.interfaces": "設定済みインターフェースはありません。",

        "empty.peers": "ピアデータはまだありません。",

        "empty.routes": "ルートデータはまだありません。",

        "empty.announces": "アナウンスデータはまだありません。",

        "empty.logs": "ログはまだありません。",

        "empty.archives": "バックアップアーカイブはまだありません。",

        "logs.title": "ログ一覧",

        "logs.event_type": "イベント種別",

        "config.title": "設定ファイル",

        "config.current_path": "現在の設定パス: {path}",

        "config.readonly_hint": "このページは閲覧専用です。編集と保存は API `POST /api/config/save-raw` または CLI `hearth config save-raw` を使用してください。",

        "backup.title": "バックアップ計画",

        "backup.archives": "利用可能なアーカイブ",

        "backup.hint": "エクスポートとインポートは API `/api/backup/export`、`/api/backup/import` または CLI `hearth backup export/import` から実行できます。",

        "auth.required": "管理者トークンが必要です。",

        "auth.invalid": "管理者トークンが無効です。",

        "network.denied": "このクライアントアドレスからのアクセスは許可されていません。",

        "value.running": "稼働中",

        "value.stopped": "停止",

        "value.starting": "起動中",

        "value.crashed": "クラッシュ",

        "value.healthy": "正常",

        "value.warning": "警告",

        "value.degraded": "低下",

        "value.critical": "重大",

        "value.error": "エラー",

        "value.unknown": "不明",

        "value.disabled": "無効",

    },

    "ko": {

        "app.tagline": "Personal Reticulum Transport Node 제어 콘솔",

        "nav.dashboard": "대시보드",

        "nav.logs": "로그",

        "nav.config": "설정",

        "nav.backup": "백업",

        "nav.docs": "API 문서",

        "locale.label": "언어",

        "page.dashboard": "Hearth 대시보드",

        "page.logs": "Hearth 로그",

        "page.config": "Hearth 설정",

        "page.backup": "Hearth 백업",

        "dashboard.node_status": "노드 상태",

        "dashboard.stats": "통계",

        "dashboard.interfaces": "인터페이스",

        "dashboard.peers": "최근 피어",

        "dashboard.routes": "최근 경로",

        "dashboard.announces": "최근 어나운스",

        "dashboard.logs": "최근 로그",

        "field.node": "노드",

        "field.peer": "피어",

        "field.runtime": "런타임",

        "field.health": "상태",

        "field.uptime": "가동 시간",

        "field.pid": "PID",

        "field.interfaces": "인터페이스 수",

        "field.peers": "피어 수",

        "field.routes": "경로 수",

        "field.announces": "어나운스 수",

        "field.restarts": "재시작 횟수",

        "field.name": "이름",

        "field.type": "유형",

        "field.status": "상태",

        "field.source": "소스",

        "field.level": "레벨",

        "field.message": "메시지",

        "field.time": "시간",

        "field.interface": "인터페이스",

        "field.hops": "홉 수",

        "field.destination": "대상",

        "field.next_hop": "다음 홉",

        "field.summary": "요약",

        "field.archive_path": "아카이브 경로",

        "field.config": "설정 파일",

        "field.database": "데이터베이스",

        "field.identity": "ID 파일",

        "field.backups_dir": "백업 디렉터리",

        "empty.interfaces": "구성된 인터페이스가 없습니다.",

        "empty.peers": "피어 데이터가 없습니다.",

        "empty.routes": "경로 데이터가 없습니다.",

        "empty.announces": "어나운스 데이터가 없습니다.",

        "empty.logs": "로그가 없습니다.",

        "empty.archives": "백업 아카이브가 없습니다.",

        "logs.title": "로그 목록",

        "logs.event_type": "이벤트 유형",

        "config.title": "설정 파일",

        "config.current_path": "현재 설정 경로: {path}",

        "config.readonly_hint": "이 페이지는 읽기 전용입니다. 편집 및 저장은 API `POST /api/config/save-raw` 또는 CLI `hearth config save-raw`를 사용하세요.",

        "backup.title": "백업 계획",

        "backup.archives": "사용 가능한 아카이브",

        "backup.hint": "내보내기와 가져오기는 API `/api/backup/export`, `/api/backup/import` 또는 CLI `hearth backup export/import`로 수행할 수 있습니다.",

        "auth.required": "관리자 토큰이 필요합니다.",

        "auth.invalid": "관리자 토큰이 올바르지 않습니다.",

        "network.denied": "이 클라이언트 주소는 서비스에 접근할 수 없습니다.",

        "value.running": "실행 중",

        "value.stopped": "중지됨",

        "value.starting": "시작 중",

        "value.crashed": "충돌",

        "value.healthy": "정상",

        "value.warning": "경고",

        "value.degraded": "저하",

        "value.critical": "심각",

        "value.error": "오류",

        "value.unknown": "알 수 없음",

        "value.disabled": "비활성화",

    },

    "es": {

        "app.tagline": "Consola de control para Personal Reticulum Transport Node",

        "nav.dashboard": "Panel",

        "nav.logs": "Registros",

        "nav.config": "Configuración",

        "nav.backup": "Respaldo",

        "nav.docs": "Docs API",

        "locale.label": "Idioma",

        "page.dashboard": "Panel de Hearth",

        "page.logs": "Registros de Hearth",

        "page.config": "Configuración de Hearth",

        "page.backup": "Respaldo de Hearth",

        "dashboard.node_status": "Estado del nodo",

        "dashboard.stats": "Estadísticas",

        "dashboard.interfaces": "Interfaces",

        "dashboard.peers": "Peers recientes",

        "dashboard.routes": "Rutas recientes",

        "dashboard.announces": "Anuncios recientes",

        "dashboard.logs": "Registros recientes",

        "field.node": "Nodo",

        "field.peer": "Peer",

        "field.runtime": "Runtime",

        "field.health": "Salud",

        "field.uptime": "Tiempo activo",

        "field.pid": "PID",

        "field.interfaces": "Interfaces",

        "field.peers": "Peers",

        "field.routes": "Rutas",

        "field.announces": "Anuncios",

        "field.restarts": "Reinicios",

        "field.name": "Nombre",

        "field.type": "Tipo",

        "field.status": "Estado",

        "field.source": "Origen",

        "field.level": "Nivel",

        "field.message": "Mensaje",

        "field.time": "Hora",

        "field.interface": "Interfaz",

        "field.hops": "Saltos",

        "field.destination": "Destino",

        "field.next_hop": "Siguiente salto",

        "field.summary": "Resumen",

        "field.archive_path": "Ruta del archivo",

        "field.config": "Configuración",

        "field.database": "Base de datos",

        "field.identity": "Identidad",

        "field.backups_dir": "Directorio de respaldos",

        "empty.interfaces": "No hay interfaces configuradas.",

        "empty.peers": "Todavía no hay datos de peers.",

        "empty.routes": "Todavía no hay datos de rutas.",

        "empty.announces": "Todavía no hay anuncios.",

        "empty.logs": "Todavía no hay registros.",

        "empty.archives": "Todavía no hay archivos de respaldo.",

        "logs.title": "Lista de registros",

        "logs.event_type": "Tipo de evento",

        "config.title": "Archivo de configuración",

        "config.current_path": "Ruta actual de configuración: {path}",

        "config.readonly_hint": "Esta página es de solo lectura. Edita y guarda mediante la API `POST /api/config/save-raw` o la CLI `hearth config save-raw`.",

        "backup.title": "Plan de respaldo",

        "backup.archives": "Archivos disponibles",

        "backup.hint": "La exportación e importación están disponibles mediante la API `/api/backup/export`, `/api/backup/import` o la CLI `hearth backup export/import`.",

        "auth.required": "Se requiere un token de administrador.",

        "auth.invalid": "El token de administrador no es válido.",

        "network.denied": "Esta dirección de cliente no tiene permiso para acceder al servicio.",

        "value.running": "En ejecución",

        "value.stopped": "Detenido",

        "value.starting": "Iniciando",

        "value.crashed": "Falló",

        "value.healthy": "Saludable",

        "value.warning": "Advertencia",

        "value.degraded": "Degradado",

        "value.critical": "Crítico",

        "value.error": "Error",

        "value.unknown": "Desconocido",

        "value.disabled": "Deshabilitado",

    },

}



EXTRA_TRANSLATIONS: dict[str, dict[str, str]] = {

    "zh-CN": {

        "nav.interfaces": "接口",

        "nav.peers": "节点",

        "nav.routes": "路由",

        "nav.announces": "广播",

        "nav.system": "系统",

        "page.interfaces": "Hearth 接口",

        "page.peers": "Hearth 节点",

        "page.routes": "Hearth 路由",

        "page.announces": "Hearth 广播",

        "page.system": "Hearth 系统",

        "field.last_seen": "最后在线",

        "field.received": "接收时间",

        "field.age": "时效",

        "field.rx_tx": "RX/TX",

        "field.actions": "操作",

        "field.last_error": "最近错误",

        "field.limit": "数量",

        "field.backend": "后端",

        "field.python": "Python",

        "field.os": "操作系统",

        "field.cpu": "CPU",

        "field.memory": "内存",

        "field.disk": "磁盘",

        "field.free": "可用",

        "field.hearth_version": "Hearth 版本",

        "field.reticulum_version": "Reticulum 版本",

        "action.start": "启动",

        "action.stop": "停止",

        "action.restart": "重启",

        "action.view_metrics": "查看指标",

        "action.filter": "筛选",

        "action.clear": "清空",

        "action.validate": "校验",

        "action.save": "保存",

        "action.export": "导出",

        "action.import": "恢复",

        "action.restart_node": "重启节点",

        "section.metrics": "指标",

        "section.filters": "筛选器",

        "section.actions": "操作",

        "interfaces.metrics_for": "接口指标：{name}",

        "interfaces.last_error": "最近错误：{error}",

        "peers.title": "最近节点",

        "routes.title": "路由表",

        "announces.title": "最近广播",

        "system.title": "系统信息",

        "system.runtime": "运行状态",

        "system.environment": "环境",

        "system.storage": "存储",

        "system.quick_actions": "快捷操作",

        "system.memory_unknown": "无法获取",

        "system.reticulum_unknown": "未检测到",

        "logs.level_filter": "级别过滤",

        "logs.module_filter": "模块过滤",

        "logs.since_minutes": "最近分钟",

        "logs.limit": "条数限制",

        "config.editor": "配置编辑器",

        "config.validation_result": "校验结果",

        "config.operation_result": "操作结果",

        "config.restart_hint": "配置保存后如需立即生效，可执行重启节点。",

        "backup.export_title": "导出备份",

        "backup.import_title": "恢复备份",

        "backup.destination_path": "导出路径（可选）",

        "backup.import_path": "归档路径",

        "backup.operation_result": "备份结果",

        "backup.restart_hint": "恢复完成后建议重启节点。",

        "notice.interface_started": "接口已启动。",

        "notice.interface_stopped": "接口已停止。",

        "notice.interface_restarted": "接口已重启。",

        "notice.config_valid": "配置校验通过。",

        "notice.config_invalid": "配置校验未通过。",

        "notice.config_saved": "配置已保存。",

        "notice.backup_exported": "备份已导出。",

        "notice.backup_imported": "备份已恢复。",

        "notice.node_started": "节点已启动。",

        "notice.node_stopped": "节点已停止。",

        "notice.node_restarted": "节点已重启。",

        "dashboard.network_activity": "网络活动",

        "dashboard.recent_events": "最近事件",

        "dashboard.system_info": "系统信息",

        "dashboard.traffic_last_24h": "最近 24 小时记录流量",

        "dashboard.view_all": "查看全部",

        "dashboard.activity_rate": "接收包",

        "dashboard.traffic": "发送包",

        "dashboard.errors": "错误",

        "dashboard.connected_interfaces": "已连接接口",

        "dashboard.active_peers": "活跃节点",

        "dashboard.total_routes": "总路由",

        "dashboard.topology": "网络拓扑视图",

        "peers.nearby_title": "附近节点",

        "peers.nearby_subtitle": "附近可见节点",

        "peers.search_placeholder": "搜索节点",

        "peers.topology_view": "网络拓扑视图",

        "table.rows_per_page": "每页行数",

        "common.all": "全部",

        "notice.action_failed": "操作失败：{error}",

        "relative.just_now": "刚刚",

        "relative.seconds_ago": "{count} 秒前",

        "relative.minutes_ago": "{count} 分钟前",

        "relative.hours_ago": "{count} 小时前",

        "relative.days_ago": "{count} 天前"

    },

    "en": {

        "nav.interfaces": "Interfaces",

        "nav.peers": "Peers",

        "nav.routes": "Routes",

        "nav.announces": "Announcements",

        "nav.system": "System",

        "page.interfaces": "Hearth Interfaces",

        "page.peers": "Hearth Peers",

        "page.routes": "Hearth Routes",

        "page.announces": "Hearth Announcements",

        "page.system": "Hearth System",

        "field.last_seen": "Last Seen",

        "field.received": "Received",

        "field.age": "Age",

        "field.rx_tx": "RX/TX",

        "field.actions": "Actions",

        "field.last_error": "Last Error",

        "field.limit": "Limit",

        "field.backend": "Backend",

        "field.python": "Python",

        "field.os": "OS",

        "field.cpu": "CPU",

        "field.memory": "Memory",

        "field.disk": "Disk",

        "field.free": "Free",

        "field.hearth_version": "Hearth Version",

        "field.reticulum_version": "Reticulum Version",

        "action.start": "Start",

        "action.stop": "Stop",

        "action.restart": "Restart",

        "action.view_metrics": "View Metrics",

        "action.filter": "Filter",

        "action.clear": "Clear",

        "action.validate": "Validate",

        "action.save": "Save",

        "action.export": "Export",

        "action.import": "Restore",

        "action.restart_node": "Restart Node",

        "section.metrics": "Metrics",

        "section.filters": "Filters",

        "section.actions": "Actions",

        "interfaces.metrics_for": "Interface Metrics: {name}",

        "interfaces.last_error": "Last error: {error}",

        "peers.title": "Recent Peers",

        "routes.title": "Route Table",

        "announces.title": "Recent Announcements",

        "system.title": "System Information",

        "system.runtime": "Runtime",

        "system.environment": "Environment",

        "system.storage": "Storage",

        "system.quick_actions": "Quick Actions",

        "system.memory_unknown": "Unavailable",

        "system.reticulum_unknown": "Not detected",

        "logs.level_filter": "Level Filter",

        "logs.module_filter": "Module Filter",

        "logs.since_minutes": "Recent Minutes",

        "logs.limit": "Entry Limit",

        "config.editor": "Config Editor",

        "config.validation_result": "Validation Result",

        "config.operation_result": "Operation Result",

        "config.restart_hint": "Restart the node if you want changes to apply immediately.",

        "backup.export_title": "Export Backup",

        "backup.import_title": "Restore Backup",

        "backup.destination_path": "Destination Path (optional)",

        "backup.import_path": "Archive Path",

        "backup.operation_result": "Backup Result",

        "backup.restart_hint": "Restarting the node after restore is recommended.",

        "notice.interface_started": "Interface started.",

        "notice.interface_stopped": "Interface stopped.",

        "notice.interface_restarted": "Interface restarted.",

        "notice.config_valid": "Configuration is valid.",

        "notice.config_invalid": "Configuration is invalid.",

        "notice.config_saved": "Configuration saved.",

        "notice.backup_exported": "Backup exported.",

        "notice.backup_imported": "Backup restored.",

        "notice.node_started": "Node started.",

        "notice.node_stopped": "Node stopped.",

        "notice.node_restarted": "Node restarted.",

        "dashboard.network_activity": "Network Activity",

        "dashboard.recent_events": "Recent Events",

        "dashboard.system_info": "System Info",

        "dashboard.traffic_last_24h": "Recorded Traffic (Last 24 Hours)",

        "dashboard.view_all": "View All",

        "dashboard.activity_rate": "RX Packets",

        "dashboard.traffic": "TX Packets",

        "dashboard.errors": "Errors",

        "dashboard.connected_interfaces": "Connected Interfaces",

        "dashboard.active_peers": "Active Peers",

        "dashboard.total_routes": "Total Routes",

        "dashboard.topology": "Network Topology View",

        "peers.nearby_title": "Nearby Nodes",

        "peers.nearby_subtitle": "Nearby visible peers",

        "peers.search_placeholder": "Search peers",

        "peers.topology_view": "Network Topology View",

        "table.rows_per_page": "Rows per page",

        "common.all": "All",

        "notice.action_failed": "Action failed: {error}",

        "relative.just_now": "just now",

        "relative.seconds_ago": "{count}s ago",

        "relative.minutes_ago": "{count}m ago",

        "relative.hours_ago": "{count}h ago",

        "relative.days_ago": "{count}d ago"

    },

    "ja": {

        "nav.interfaces": "インターフェース",

        "nav.peers": "ピア",

        "nav.routes": "ルート",

        "nav.announces": "アナウンス",

        "nav.system": "システム",

        "page.interfaces": "Hearth インターフェース",

        "page.peers": "Hearth ピア",

        "page.routes": "Hearth ルート",

        "page.announces": "Hearth アナウンス",

        "page.system": "Hearth システム",

        "field.last_seen": "最終確認",

        "field.received": "受信時刻",

        "field.age": "経過時間",

        "field.rx_tx": "RX/TX",

        "field.actions": "操作",

        "field.last_error": "最終エラー",

        "field.limit": "件数",

        "field.backend": "バックエンド",

        "field.python": "Python",

        "field.os": "OS",

        "field.cpu": "CPU",

        "field.memory": "メモリ",

        "field.disk": "ディスク",

        "field.free": "空き容量",

        "field.hearth_version": "Hearth バージョン",

        "field.reticulum_version": "Reticulum バージョン",

        "action.start": "起動",

        "action.stop": "停止",

        "action.restart": "再起動",

        "action.view_metrics": "メトリクス表示",

        "action.filter": "絞り込み",

        "action.clear": "クリア",

        "action.validate": "検証",

        "action.save": "保存",

        "action.export": "エクスポート",

        "action.import": "復元",

        "action.restart_node": "ノードを再起動",

        "section.metrics": "メトリクス",

        "section.filters": "フィルター",

        "section.actions": "操作",

        "interfaces.metrics_for": "インターフェースメトリクス: {name}",

        "interfaces.last_error": "最終エラー: {error}",

        "peers.title": "最近のピア",

        "routes.title": "ルートテーブル",

        "announces.title": "最近のアナウンス",

        "system.title": "システム情報",

        "system.runtime": "稼働状況",

        "system.environment": "環境",

        "system.storage": "ストレージ",

        "system.quick_actions": "クイック操作",

        "system.memory_unknown": "取得不可",

        "system.reticulum_unknown": "未検出",

        "logs.level_filter": "レベルフィルター",

        "logs.module_filter": "モジュールフィルター",

        "logs.since_minutes": "直近の分数",

        "logs.limit": "件数上限",

        "config.editor": "設定エディター",

        "config.validation_result": "検証結果",

        "config.operation_result": "実行結果",

        "config.restart_hint": "変更をすぐ反映するにはノードを再起動してください。",

        "backup.export_title": "バックアップをエクスポート",

        "backup.import_title": "バックアップを復元",

        "backup.destination_path": "出力先パス（任意）",

        "backup.import_path": "アーカイブパス",

        "backup.operation_result": "バックアップ結果",

        "backup.restart_hint": "復元後はノードの再起動を推奨します。",

        "notice.interface_started": "インターフェースを起動しました。",

        "notice.interface_stopped": "インターフェースを停止しました。",

        "notice.interface_restarted": "インターフェースを再起動しました。",

        "notice.config_valid": "設定は有効です。",

        "notice.config_invalid": "設定が無効です。",

        "notice.config_saved": "設定を保存しました。",

        "notice.backup_exported": "バックアップをエクスポートしました。",

        "notice.backup_imported": "バックアップを復元しました。",

        "notice.node_started": "ノードを起動しました。",

        "notice.node_stopped": "ノードを停止しました。",

        "notice.node_restarted": "ノードを再起動しました。",

        "dashboard.network_activity": "ネットワークアクティビティ",

        "dashboard.recent_events": "最近のイベント",

        "dashboard.system_info": "システム情報",

        "dashboard.traffic_last_24h": "過去24時間の記録トラフィック",

        "dashboard.view_all": "すべて表示",

        "dashboard.activity_rate": "受信パケット",

        "dashboard.traffic": "送信パケット",

        "dashboard.errors": "エラー",

        "dashboard.connected_interfaces": "接続済みインターフェース",

        "dashboard.active_peers": "アクティブなピア",

        "dashboard.total_routes": "総ルート数",

        "dashboard.topology": "ネットワークトポロジー",

        "peers.nearby_title": "近隣ノード",

        "peers.nearby_subtitle": "近くで見えるピア",

        "peers.search_placeholder": "ピアを検索",

        "peers.topology_view": "ネットワークトポロジー",

        "table.rows_per_page": "1ページの行数",

        "common.all": "すべて",

        "notice.action_failed": "操作に失敗しました: {error}",

        "relative.just_now": "たった今",

        "relative.seconds_ago": "{count}秒前",

        "relative.minutes_ago": "{count}分前",

        "relative.hours_ago": "{count}時間前",

        "relative.days_ago": "{count}日前"

    },

    "ko": {

        "nav.interfaces": "인터페이스",

        "nav.peers": "피어",

        "nav.routes": "경로",

        "nav.announces": "공지",

        "nav.system": "시스템",

        "page.interfaces": "Hearth 인터페이스",

        "page.peers": "Hearth 피어",

        "page.routes": "Hearth 경로",

        "page.announces": "Hearth 공지",

        "page.system": "Hearth 시스템",

        "field.last_seen": "마지막 확인",

        "field.received": "수신 시각",

        "field.age": "경과 시간",

        "field.rx_tx": "RX/TX",

        "field.actions": "작업",

        "field.last_error": "최근 오류",

        "field.limit": "개수",

        "field.backend": "백엔드",

        "field.python": "Python",

        "field.os": "운영체제",

        "field.cpu": "CPU",

        "field.memory": "메모리",

        "field.disk": "디스크",

        "field.free": "여유 공간",

        "field.hearth_version": "Hearth 버전",

        "field.reticulum_version": "Reticulum 버전",

        "action.start": "시작",

        "action.stop": "중지",

        "action.restart": "재시작",

        "action.view_metrics": "지표 보기",

        "action.filter": "필터",

        "action.clear": "지우기",

        "action.validate": "검증",

        "action.save": "저장",

        "action.export": "내보내기",

        "action.import": "복원",

        "action.restart_node": "노드 재시작",

        "section.metrics": "지표",

        "section.filters": "필터",

        "section.actions": "작업",

        "interfaces.metrics_for": "인터페이스 지표: {name}",

        "interfaces.last_error": "최근 오류: {error}",

        "peers.title": "최근 피어",

        "routes.title": "경로 테이블",

        "announces.title": "최근 공지",

        "system.title": "시스템 정보",

        "system.runtime": "실행 상태",

        "system.environment": "환경",

        "system.storage": "저장소",

        "system.quick_actions": "빠른 작업",

        "system.memory_unknown": "확인 불가",

        "system.reticulum_unknown": "감지되지 않음",

        "logs.level_filter": "수준 필터",

        "logs.module_filter": "모듈 필터",

        "logs.since_minutes": "최근 분",

        "logs.limit": "항목 제한",

        "config.editor": "설정 편집기",

        "config.validation_result": "검증 결과",

        "config.operation_result": "작업 결과",

        "config.restart_hint": "변경 사항을 바로 적용하려면 노드를 재시작하세요.",

        "backup.export_title": "백업 내보내기",

        "backup.import_title": "백업 복원",

        "backup.destination_path": "대상 경로(선택)",

        "backup.import_path": "아카이브 경로",

        "backup.operation_result": "백업 결과",

        "backup.restart_hint": "복원 후 노드 재시작을 권장합니다.",

        "notice.interface_started": "인터페이스를 시작했습니다.",

        "notice.interface_stopped": "인터페이스를 중지했습니다.",

        "notice.interface_restarted": "인터페이스를 재시작했습니다.",

        "notice.config_valid": "설정이 유효합니다.",

        "notice.config_invalid": "설정이 올바르지 않습니다.",

        "notice.config_saved": "설정을 저장했습니다.",

        "notice.backup_exported": "백업을 내보냈습니다.",

        "notice.backup_imported": "백업을 복원했습니다.",

        "notice.node_started": "노드를 시작했습니다.",

        "notice.node_stopped": "노드를 중지했습니다.",

        "notice.node_restarted": "노드를 재시작했습니다.",

        "dashboard.network_activity": "네트워크 활동",

        "dashboard.recent_events": "최근 이벤트",

        "dashboard.system_info": "시스템 정보",

        "dashboard.traffic_last_24h": "최근 24시간 기록 트래픽",

        "dashboard.view_all": "모두 보기",

        "dashboard.activity_rate": "수신 패킷",

        "dashboard.traffic": "송신 패킷",

        "dashboard.errors": "오류",

        "dashboard.connected_interfaces": "연결된 인터페이스",

        "dashboard.active_peers": "활성 피어",

        "dashboard.total_routes": "전체 경로",

        "dashboard.topology": "네트워크 토폴로지 보기",

        "peers.nearby_title": "주변 노드",

        "peers.nearby_subtitle": "주변에서 보이는 피어",

        "peers.search_placeholder": "피어 검색",

        "peers.topology_view": "네트워크 토폴로지 보기",

        "table.rows_per_page": "페이지당 행 수",

        "common.all": "전체",

        "notice.action_failed": "작업 실패: {error}",

        "relative.just_now": "방금 전",

        "relative.seconds_ago": "{count}초 전",

        "relative.minutes_ago": "{count}분 전",

        "relative.hours_ago": "{count}시간 전",

        "relative.days_ago": "{count}일 전"

    },

    "es": {

        "nav.interfaces": "Interfaces",

        "nav.peers": "Peers",

        "nav.routes": "Rutas",

        "nav.announces": "Anuncios",

        "nav.system": "Sistema",

        "page.interfaces": "Interfaces de Hearth",

        "page.peers": "Peers de Hearth",

        "page.routes": "Rutas de Hearth",

        "page.announces": "Anuncios de Hearth",

        "page.system": "Sistema de Hearth",

        "field.last_seen": "Última vez",

        "field.received": "Recibido",

        "field.age": "Antigüedad",

        "field.rx_tx": "RX/TX",

        "field.actions": "Acciones",

        "field.last_error": "Último error",

        "field.limit": "Límite",

        "field.backend": "Backend",

        "field.python": "Python",

        "field.os": "SO",

        "field.cpu": "CPU",

        "field.memory": "Memoria",

        "field.disk": "Disco",

        "field.free": "Libre",

        "field.hearth_version": "Versión de Hearth",

        "field.reticulum_version": "Versión de Reticulum",

        "action.start": "Iniciar",

        "action.stop": "Detener",

        "action.restart": "Reiniciar",

        "action.view_metrics": "Ver métricas",

        "action.filter": "Filtrar",

        "action.clear": "Limpiar",

        "action.validate": "Validar",

        "action.save": "Guardar",

        "action.export": "Exportar",

        "action.import": "Restaurar",

        "action.restart_node": "Reiniciar nodo",

        "section.metrics": "Métricas",

        "section.filters": "Filtros",

        "section.actions": "Acciones",

        "interfaces.metrics_for": "Métricas de la interfaz: {name}",

        "interfaces.last_error": "Último error: {error}",

        "peers.title": "Peers recientes",

        "routes.title": "Tabla de rutas",

        "announces.title": "Anuncios recientes",

        "system.title": "Información del sistema",

        "system.runtime": "Tiempo de ejecución",

        "system.environment": "Entorno",

        "system.storage": "Almacenamiento",

        "system.quick_actions": "Acciones rápidas",

        "system.memory_unknown": "No disponible",

        "system.reticulum_unknown": "No detectado",

        "logs.level_filter": "Filtro por nivel",

        "logs.module_filter": "Filtro de módulo",

        "logs.since_minutes": "Últimos minutos",

        "logs.limit": "Límite de entradas",

        "config.editor": "Editor de configuración",

        "config.validation_result": "Resultado de validación",

        "config.operation_result": "Resultado de operación",

        "config.restart_hint": "Reinicia el nodo si quieres aplicar los cambios de inmediato.",

        "backup.export_title": "Exportar respaldo",

        "backup.import_title": "Restaurar respaldo",

        "backup.destination_path": "Ruta de destino (opcional)",

        "backup.import_path": "Ruta del archivo",

        "backup.operation_result": "Resultado del respaldo",

        "backup.restart_hint": "Se recomienda reiniciar el nodo después de restaurar.",

        "notice.interface_started": "Interfaz iniciada.",

        "notice.interface_stopped": "Interfaz detenida.",

        "notice.interface_restarted": "Interfaz reiniciada.",

        "notice.config_valid": "La configuración es válida.",

        "notice.config_invalid": "La configuración no es válida.",

        "notice.config_saved": "Configuración guardada.",

        "notice.backup_exported": "Respaldo exportado.",

        "notice.backup_imported": "Respaldo restaurado.",

        "notice.node_started": "Nodo iniciado.",

        "notice.node_stopped": "Nodo detenido.",

        "notice.node_restarted": "Nodo reiniciado.",

        "dashboard.network_activity": "Actividad de red",

        "dashboard.recent_events": "Eventos recientes",

        "dashboard.system_info": "Información del sistema",

        "dashboard.traffic_last_24h": "Tráfico registrado (últimas 24 horas)",

        "dashboard.view_all": "Ver todo",

        "dashboard.activity_rate": "Paquetes RX",

        "dashboard.traffic": "Paquetes TX",

        "dashboard.errors": "Errores",

        "dashboard.connected_interfaces": "Interfaces conectadas",

        "dashboard.active_peers": "Peers activos",

        "dashboard.total_routes": "Rutas totales",

        "dashboard.topology": "Vista de topología de red",

        "peers.nearby_title": "Nodos cercanos",

        "peers.nearby_subtitle": "Peers visibles cercanos",

        "peers.search_placeholder": "Buscar peers",

        "peers.topology_view": "Vista de topología de red",

        "table.rows_per_page": "Filas por página",

        "common.all": "Todo",

        "notice.action_failed": "Acción fallida: {error}",

        "relative.just_now": "justo ahora",

        "relative.seconds_ago": "hace {count} s",

        "relative.minutes_ago": "hace {count} min",

        "relative.hours_ago": "hace {count} h",

        "relative.days_ago": "hace {count} d"

    }

}



for locale, values in EXTRA_TRANSLATIONS.items():

    TRANSLATIONS[locale].update(values)







def normalize_locale(value: str | None) -> str:

    if not value:

        return DEFAULT_LOCALE



    candidate = value.strip()

    if not candidate:

        return DEFAULT_LOCALE



    alias = LOCALE_ALIASES.get(candidate.lower())

    if alias:

        return alias



    for locale in SUPPORTED_LOCALES:

        if locale.lower() == candidate.lower() or locale.split("-")[0].lower() == candidate.lower():

            return locale



    return DEFAULT_LOCALE





def resolve_locale(request: Request) -> str:

    query_locale = request.query_params.get("lang")

    if query_locale:

        return normalize_locale(query_locale)



    cookie_locale = request.cookies.get(LANG_COOKIE_NAME)

    if cookie_locale:

        return normalize_locale(cookie_locale)



    accept_language = request.headers.get("accept-language", "")

    for raw_part in accept_language.split(","):

        language = raw_part.split(";", 1)[0].strip()

        if language:

            return normalize_locale(language)



    return DEFAULT_LOCALE





def _translation_looks_corrupted(value: object, locale: str | None = None) -> bool:

    if not isinstance(value, str) or not value:

        return False

    if "�" in value or "??" in value:

        return True

    if "?" not in value:

        return False

    compact = value.strip()

    if compact and compact.replace("?", "") == "":

        return True

    if locale in {"zh-CN", "ja", "ko"}:

        return True

    stripped = value.rstrip()

    if stripped.endswith("?") and stripped.count("?") == 1:

        return False

    return True


def translate(locale: str, key: str, **kwargs: object) -> str:

    table = TRANSLATIONS.get(locale, TRANSLATIONS[DEFAULT_LOCALE])

    localized_template = table.get(key)

    english_template = TRANSLATIONS.get("en", {}).get(key)

    default_template = TRANSLATIONS[DEFAULT_LOCALE].get(key)

    template = localized_template or english_template or default_template or key

    if locale != "en" and _translation_looks_corrupted(template, locale):

        fallback_template = english_template or default_template or key

        if not _translation_looks_corrupted(fallback_template, "en"):

            template = fallback_template

    if not kwargs:

        return template

    try:

        return template.format(**kwargs)

    except (KeyError, ValueError):

        return template





def build_locale_options(current_locale: str, request: Request) -> list[dict[str, object]]:

    base_query = [(key, value) for key, value in request.query_params.multi_items() if key != "lang"]

    options: list[dict[str, object]] = []

    for code, label in SUPPORTED_LOCALES.items():

        query = urlencode([*base_query, ("lang", code)])

        href = request.url.path if not query else f"{request.url.path}?{query}"

        options.append(

            {

                "code": code,

                "label": label,

                "href": href,

                "active": code == current_locale,

            }

        )

    return options

ADDITIONAL_WEB_TRANSLATIONS: dict[str, dict[str, str]] = {'zh-CN': {'nav.health': '健康',
           'page.health': 'Hearth 健康',
           'page.login': 'Hearth 登录',
           'page.interface_detail': 'Hearth 接口详情',
           'field.score': '分数',
           'field.issue': '问题',
           'field.target': '目标',
           'field.reason': '原因',
           'field.token': '令牌',
           'field.last_check': '上次检查',
           'action.login': '登录',
           'action.logout': '退出',
           'health.current_issues': '当前问题',
           'health.runtime_overview': '运行时概览',
           'health.interface_overview': '接口健康',
           'health.recent_incidents': '最近事件',
           'health.restart_history': '重启历史',
           'health.no_issues': '暂无问题。',
           'health.no_incidents': '暂无事件。',
           'health.no_restarts': '暂无重启记录。',
           'health.status_score': '健康分数',
           'auth.login_title': '管理员登录',
           'auth.login_hint': '输入管理员令牌以访问受保护页面。',
           'auth.login_success': '登录成功。',
           'auth.login_failed': '令牌无效。',
           'auth.not_required': '当前未启用登录验证。',
           'auth.logout_success': '已退出登录。',
           'interfaces.detail_title': '接口详情',
           'interfaces.recent_traffic': '最近 24 小时流量',
           'interfaces.recent_restarts': '最近重启',
           'interfaces.back_to_list': '返回接口列表'},
 'en': {'nav.health': 'Health',
        'page.health': 'Hearth Health',
        'page.login': 'Hearth Login',
        'page.interface_detail': 'Hearth Interface Detail',
        'field.score': 'Score',
        'field.issue': 'Issue',
        'field.target': 'Target',
        'field.reason': 'Reason',
        'field.token': 'Token',
        'field.last_check': 'Last Check',
        'action.login': 'Sign In',
        'action.logout': 'Sign Out',
        'health.current_issues': 'Current Issues',
        'health.runtime_overview': 'Runtime Overview',
        'health.interface_overview': 'Interface Health',
        'health.recent_incidents': 'Recent Incidents',
        'health.restart_history': 'Restart History',
        'health.no_issues': 'No active issues.',
        'health.no_incidents': 'No recent incidents.',
        'health.no_restarts': 'No restart history.',
        'health.status_score': 'Health Score',
        'auth.login_title': 'Admin Login',
        'auth.login_hint': 'Enter the admin token to access protected pages.',
        'auth.login_success': 'Login successful.',
        'auth.login_failed': 'Invalid token.',
        'auth.not_required': 'Authentication is currently disabled.',
        'auth.logout_success': 'Logged out.',
        'interfaces.detail_title': 'Interface Details',
        'interfaces.recent_traffic': 'Recent 24h Traffic',
        'interfaces.recent_restarts': 'Recent Restarts',
        'interfaces.back_to_list': 'Back to Interfaces'},
 'ja': {'nav.health': 'ヘルス',
        'page.health': 'Hearth ヘルス',
        'page.login': 'Hearth ログイン',
        'page.interface_detail': 'Hearth インターフェース詳細',
        'field.score': 'スコア',
        'field.issue': '問題',
        'field.target': '対象',
        'field.reason': '理由',
        'field.token': 'トークン',
        'field.last_check': '最終確認',
        'action.login': 'ログイン',
        'action.logout': 'ログアウト',
        'health.current_issues': '現在の問題',
        'health.runtime_overview': 'ランタイム概要',
        'health.interface_overview': 'インターフェース健全性',
        'health.recent_incidents': '最近のインシデント',
        'health.restart_history': '再起動履歴',
        'health.no_issues': '問題はありません。',
        'health.no_incidents': '最近のインシデントはありません。',
        'health.no_restarts': '再起動履歴はありません。',
        'health.status_score': 'ヘルススコア',
        'auth.login_title': '管理者ログイン',
        'auth.login_hint': '保護されたページにアクセスするには管理者トークンを入力してください。',
        'auth.login_success': 'ログインしました。',
        'auth.login_failed': 'トークンが無効です。',
        'auth.not_required': '現在、認証は無効です。',
        'auth.logout_success': 'ログアウトしました。',
        'interfaces.detail_title': 'インターフェース詳細',
        'interfaces.recent_traffic': '直近24時間のトラフィック',
        'interfaces.recent_restarts': '最近の再起動',
        'interfaces.back_to_list': 'インターフェース一覧へ戻る'},
 'ko': {'nav.health': '상태',
        'page.health': 'Hearth 상태',
        'page.login': 'Hearth 로그인',
        'page.interface_detail': 'Hearth 인터페이스 상세',
        'field.score': '점수',
        'field.issue': '문제',
        'field.target': '대상',
        'field.reason': '이유',
        'field.token': '토큰',
        'field.last_check': '마지막 확인',
        'action.login': '로그인',
        'action.logout': '로그아웃',
        'health.current_issues': '현재 이슈',
        'health.runtime_overview': '런타임 개요',
        'health.interface_overview': '인터페이스 상태',
        'health.recent_incidents': '최근 이벤트',
        'health.restart_history': '재시작 기록',
        'health.no_issues': '활성 이슈가 없습니다.',
        'health.no_incidents': '최근 이벤트가 없습니다.',
        'health.no_restarts': '재시작 기록이 없습니다.',
        'health.status_score': '상태 점수',
        'auth.login_title': '관리자 로그인',
        'auth.login_hint': '보호된 페이지에 접근하려면 관리자 토큰을 입력하세요.',
        'auth.login_success': '로그인되었습니다.',
        'auth.login_failed': '토큰이 올바르지 않습니다.',
        'auth.not_required': '현재 인증이 비활성화되어 있습니다.',
        'auth.logout_success': '로그아웃되었습니다.',
        'interfaces.detail_title': '인터페이스 상세',
        'interfaces.recent_traffic': '최근 24시간 트래픽',
        'interfaces.recent_restarts': '최근 재시작',
        'interfaces.back_to_list': '인터페이스 목록으로'},
 'es': {'nav.health': 'Salud',
        'page.health': 'Hearth Salud',
        'page.login': 'Hearth Login',
        'page.interface_detail': 'Detalle de interfaz de Hearth',
        'field.score': 'Puntuación',
        'field.issue': 'Incidencia',
        'field.target': 'Objetivo',
        'field.reason': 'Motivo',
        'field.token': 'Token',
        'field.last_check': 'Última comprobación',
        'action.login': 'Iniciar sesión',
        'action.logout': 'Cerrar sesión',
        'health.current_issues': 'Problemas actuales',
        'health.runtime_overview': 'Estado del runtime',
        'health.interface_overview': 'Salud de interfaces',
        'health.recent_incidents': 'Incidentes recientes',
        'health.restart_history': 'Historial de reinicios',
        'health.no_issues': 'No hay problemas activos.',
        'health.no_incidents': 'No hay incidentes recientes.',
        'health.no_restarts': 'No hay historial de reinicios.',
        'health.status_score': 'Puntuación de salud',
        'auth.login_title': 'Acceso de administrador',
        'auth.login_hint': 'Introduce el token de administrador para acceder a las páginas protegidas.',
        'auth.login_success': 'Inicio de sesión correcto.',
        'auth.login_failed': 'Token no válido.',
        'auth.not_required': 'La autenticación está desactivada.',
        'auth.logout_success': 'Sesión cerrada.',
        'interfaces.detail_title': 'Detalles de interfaz',
        'interfaces.recent_traffic': 'Tráfico de las últimas 24 h',
        'interfaces.recent_restarts': 'Reinicios recientes',
        'interfaces.back_to_list': 'Volver a interfaces'}}

for locale, values in ADDITIONAL_WEB_TRANSLATIONS.items():
    TRANSLATIONS[locale].update(values)
DETAIL_PAGE_TRANSLATIONS: dict[str, dict[str, str]] = {'zh-CN': {'action.view_details': '查看详情',
           'page.peer_detail': 'Hearth 节点详情',
           'page.route_detail': 'Hearth 路由详情',
           'page.announce_detail': 'Hearth 广播详情',
           'field.first_seen': '首次发现',
           'field.expires': '过期时间',
           'field.metadata': '元数据',
           'peers.detail_title': '节点详情',
           'peers.recent_activity': '最近活动',
           'peers.interfaces_seen': '观测到的接口',
           'peers.route_links': '关联路由',
           'routes.detail_title': '路由详情',
           'routes.current_state': '当前状态',
           'routes.related_announces': '关联广播',
           'routes.related_peer': '关联节点',
           'announces.detail_title': '广播详情',
           'announces.metadata': '元数据',
           'announces.related_route': '关联路由',
           'announces.related_peer': '关联节点'},
 'en': {'action.view_details': 'View Details',
        'page.peer_detail': 'Hearth Peer Detail',
        'page.route_detail': 'Hearth Route Detail',
        'page.announce_detail': 'Hearth Announcement Detail',
        'field.first_seen': 'First Seen',
        'field.expires': 'Expires',
        'field.metadata': 'Metadata',
        'peers.detail_title': 'Peer Details',
        'peers.recent_activity': 'Recent Activity',
        'peers.interfaces_seen': 'Interfaces Seen',
        'peers.route_links': 'Related Routes',
        'routes.detail_title': 'Route Details',
        'routes.current_state': 'Current State',
        'routes.related_announces': 'Related Announcements',
        'routes.related_peer': 'Related Peer',
        'announces.detail_title': 'Announcement Details',
        'announces.metadata': 'Metadata',
        'announces.related_route': 'Related Route',
        'announces.related_peer': 'Related Peer'},
 'ja': {'action.view_details': '詳細を表示',
        'page.peer_detail': 'Hearth ピア詳細',
        'page.route_detail': 'Hearth ルート詳細',
        'page.announce_detail': 'Hearth アナウンス詳細',
        'field.first_seen': '初回確認',
        'field.expires': '有効期限',
        'field.metadata': 'メタデータ',
        'peers.detail_title': 'ピア詳細',
        'peers.recent_activity': '最近の活動',
        'peers.interfaces_seen': '確認したインターフェース',
        'peers.route_links': '関連ルート',
        'routes.detail_title': 'ルート詳細',
        'routes.current_state': '現在の状態',
        'routes.related_announces': '関連アナウンス',
        'routes.related_peer': '関連ピア',
        'announces.detail_title': 'アナウンス詳細',
        'announces.metadata': 'メタデータ',
        'announces.related_route': '関連ルート',
        'announces.related_peer': '関連ピア'},
 'ko': {'action.view_details': '상세 보기',
        'page.peer_detail': 'Hearth 피어 상세',
        'page.route_detail': 'Hearth 경로 상세',
        'page.announce_detail': 'Hearth 공지 상세',
        'field.first_seen': '처음 확인',
        'field.expires': '만료',
        'field.metadata': '메타데이터',
        'peers.detail_title': '피어 상세',
        'peers.recent_activity': '최근 활동',
        'peers.interfaces_seen': '확인된 인터페이스',
        'peers.route_links': '관련 경로',
        'routes.detail_title': '경로 상세',
        'routes.current_state': '현재 상태',
        'routes.related_announces': '관련 공지',
        'routes.related_peer': '관련 피어',
        'announces.detail_title': '공지 상세',
        'announces.metadata': '메타데이터',
        'announces.related_route': '관련 경로',
        'announces.related_peer': '관련 피어'},
 'es': {'action.view_details': 'Ver detalles',
        'page.peer_detail': 'Detalle de peer de Hearth',
        'page.route_detail': 'Detalle de ruta de Hearth',
        'page.announce_detail': 'Detalle de anuncio de Hearth',
        'field.first_seen': 'Primera vez visto',
        'field.expires': 'Expira',
        'field.metadata': 'Metadatos',
        'peers.detail_title': 'Detalles del peer',
        'peers.recent_activity': 'Actividad reciente',
        'peers.interfaces_seen': 'Interfaces observadas',
        'peers.route_links': 'Rutas relacionadas',
        'routes.detail_title': 'Detalles de la ruta',
        'routes.current_state': 'Estado actual',
        'routes.related_announces': 'Anuncios relacionados',
        'routes.related_peer': 'Peer relacionado',
        'announces.detail_title': 'Detalles del anuncio',
        'announces.metadata': 'Metadatos',
        'announces.related_route': 'Ruta relacionada',
        'announces.related_peer': 'Peer relacionado'}}

for locale, values in DETAIL_PAGE_TRANSLATIONS.items():
    TRANSLATIONS[locale].update(values)


OPERATIONS_PAGE_TRANSLATIONS = {
  "zh-CN": {
    "nav.profile": "????",
    "nav.security": "????",
    "nav.audit": "????",
    "page.profile": "Hearth ????",
    "page.security": "Hearth ????",
    "page.audit": "Hearth ????",
    "profile.identity": "????",
    "profile.security_posture": "????",
    "profile.quick_links": "????",
    "security.access_policy": "????",
    "security.network_policy": "????",
    "security.browser_protection": "?????",
    "security.watchdog_policy": "?????",
    "security.findings": "????",
    "security.no_findings": "??????????",
    "security.metrics_endpoint": "????",
    "security.allow_lan": "???????",
    "security.allow_wan": "???????",
    "security.watchdog_enabled": "?????",
    "security.auto_restart_runtime": "???? Runtime",
    "security.auto_restart_interface": "??????",
    "security.restart_cooldown": "????",
    "security.default_token_warning": "?????????????????",
    "security.wan_warning": "??? WAN ??????????????????",
    "security.auth_disabled_warning": "???????????????????????",
    "audit.filters": "??",
    "audit.search": "??",
    "audit.no_records": "??????????",
    "audit.total_records": "???",
    "action.reset": "??",
    "field.user": "??",
    "field.role": "??",
    "field.auth_mode": "????",
    "field.client": "???",
    "field.client_zone": "?????",
    "field.session": "??",
    "field.access": "??",
    "field.header": "???",
    "field.value": "?",
    "field.headers": "???",
    "field.payload": "??",
    "field.limit": "??",
    "value.authenticated": "???",
    "value.not_authenticated": "???",
    "value.administrator": "???",
    "value.token_session": "????",
    "value.enabled": "???",
    "value.local_token": "????",
    "value.protected": "???",
    "value.open": "??",
    "value.loopback": "????",
    "value.lan": "???",
    "value.public": "??",
    "value.all": "??"
  },
  "en": {
    "nav.profile": "Profile",
    "nav.security": "Security",
    "nav.audit": "Audit",
    "page.profile": "Hearth Profile",
    "page.security": "Hearth Security",
    "page.audit": "Hearth Audit Log",
    "profile.identity": "Current Identity",
    "profile.security_posture": "Security Posture",
    "profile.quick_links": "Quick Links",
    "security.access_policy": "Access Policy",
    "security.network_policy": "Network Policy",
    "security.browser_protection": "Browser Protection",
    "security.watchdog_policy": "Watchdog Policy",
    "security.findings": "Findings",
    "security.no_findings": "No obvious risks detected.",
    "security.metrics_endpoint": "Metrics Endpoint",
    "security.allow_lan": "Allow LAN Access",
    "security.allow_wan": "Allow WAN Access",
    "security.watchdog_enabled": "Watchdog Enabled",
    "security.auto_restart_runtime": "Auto-Restart Runtime",
    "security.auto_restart_interface": "Auto-Restart Interfaces",
    "security.restart_cooldown": "Restart Cooldown",
    "security.default_token_warning": "The admin token is still the default value. Change it immediately.",
    "security.wan_warning": "WAN access is enabled. Confirm token strength and reverse-proxy protections.",
    "security.auth_disabled_warning": "Authentication is disabled, so management pages are open to allowed network sources.",
    "audit.filters": "Filters",
    "audit.search": "Search",
    "audit.no_records": "No matching audit records.",
    "audit.total_records": "records",
    "action.reset": "Reset",
    "field.user": "User",
    "field.role": "Role",
    "field.auth_mode": "Auth Mode",
    "field.client": "Client",
    "field.client_zone": "Client Zone",
    "field.session": "Session",
    "field.access": "Access",
    "field.header": "Header",
    "field.value": "Value",
    "field.headers": "Headers",
    "field.payload": "Payload",
    "field.limit": "Limit",
    "value.authenticated": "Authenticated",
    "value.not_authenticated": "Not Authenticated",
    "value.administrator": "Administrator",
    "value.token_session": "Token Session",
    "value.enabled": "Enabled",
    "value.local_token": "Local Token",
    "value.protected": "Protected",
    "value.open": "Open",
    "value.loopback": "Loopback",
    "value.lan": "LAN",
    "value.public": "Public",
    "value.all": "All"
  },
  "ja": {
    "nav.profile": "??????",
    "nav.security": "??????",
    "nav.audit": "????",
    "page.profile": "Hearth ??????",
    "page.security": "Hearth ??????",
    "page.audit": "Hearth ????",
    "profile.identity": "?????",
    "profile.security_posture": "????????",
    "profile.quick_links": "???????",
    "security.access_policy": "??????",
    "security.network_policy": "????????",
    "security.browser_protection": "??????",
    "security.watchdog_policy": "?????????",
    "security.findings": "????",
    "security.no_findings": "?????????????????",
    "security.metrics_endpoint": "????????????",
    "security.allow_lan": "LAN ???????",
    "security.allow_wan": "WAN ???????",
    "security.watchdog_enabled": "?????????",
    "security.auto_restart_runtime": "Runtime ?????",
    "security.auto_restart_interface": "?????????????",
    "security.restart_cooldown": "?????????",
    "security.default_token_warning": "????????????????????????????",
    "security.wan_warning": "WAN ?????????????????????????????????????",
    "security.auth_disabled_warning": "???????????????????????????????????????",
    "audit.filters": "?????",
    "audit.search": "??",
    "audit.no_records": "???????????????",
    "audit.total_records": "?",
    "action.reset": "????",
    "field.user": "????",
    "field.role": "??",
    "field.auth_mode": "?????",
    "field.client": "??????",
    "field.client_zone": "?????????",
    "field.session": "?????",
    "field.access": "????",
    "field.header": "????",
    "field.value": "?",
    "field.headers": "????",
    "field.payload": "?????",
    "field.limit": "??",
    "value.authenticated": "????",
    "value.not_authenticated": "???",
    "value.administrator": "???",
    "value.token_session": "?????????",
    "value.enabled": "??",
    "value.local_token": "????????",
    "value.protected": "????",
    "value.open": "??",
    "value.loopback": "??????",
    "value.lan": "LAN",
    "value.public": "????????",
    "value.all": "???"
  },
  "ko": {
    "nav.profile": "???",
    "nav.security": "??",
    "nav.audit": "?? ??",
    "page.profile": "Hearth ???",
    "page.security": "Hearth ??",
    "page.audit": "Hearth ?? ??",
    "profile.identity": "?? ??",
    "profile.security_posture": "?? ??",
    "profile.quick_links": "?? ??",
    "security.access_policy": "?? ??",
    "security.network_policy": "???? ??",
    "security.browser_protection": "???? ??",
    "security.watchdog_policy": "??? ??",
    "security.findings": "?? ??",
    "security.no_findings": "??? ??? ???? ?????.",
    "security.metrics_endpoint": "??? ?????",
    "security.allow_lan": "LAN ?? ??",
    "security.allow_wan": "WAN ?? ??",
    "security.watchdog_enabled": "??? ??",
    "security.auto_restart_runtime": "Runtime ?? ???",
    "security.auto_restart_interface": "????? ?? ???",
    "security.restart_cooldown": "??? ???",
    "security.default_token_warning": "??? ??? ??????. ?? ?????.",
    "security.wan_warning": "WAN ??? ????????. ?? ??? ??? ??? ?????.",
    "security.auth_disabled_warning": "??? ?????? ??? ?????? ?? ???? ?? ??? ? ????.",
    "audit.filters": "??",
    "audit.search": "??",
    "audit.no_records": "???? ?? ??? ????.",
    "audit.total_records": "? ???",
    "action.reset": "???",
    "field.user": "???",
    "field.role": "??",
    "field.auth_mode": "?? ??",
    "field.client": "?????",
    "field.client_zone": "????? ??",
    "field.session": "??",
    "field.access": "??",
    "field.header": "??",
    "field.value": "?",
    "field.headers": "??",
    "field.payload": "????",
    "field.limit": "??",
    "value.authenticated": "???",
    "value.not_authenticated": "???",
    "value.administrator": "???",
    "value.token_session": "?? ??",
    "value.enabled": "???",
    "value.local_token": "?? ??",
    "value.protected": "???",
    "value.open": "??",
    "value.loopback": "???",
    "value.lan": "LAN",
    "value.public": "?? ????",
    "value.all": "??"
  },
  "es": {
    "nav.profile": "Perfil",
    "nav.security": "Seguridad",
    "nav.audit": "Auditor?a",
    "page.profile": "Perfil de Hearth",
    "page.security": "Seguridad de Hearth",
    "page.audit": "Registro de auditor?a de Hearth",
    "profile.identity": "Identidad actual",
    "profile.security_posture": "Postura de seguridad",
    "profile.quick_links": "Accesos r?pidos",
    "security.access_policy": "Pol?tica de acceso",
    "security.network_policy": "Pol?tica de red",
    "security.browser_protection": "Protecci?n del navegador",
    "security.watchdog_policy": "Pol?tica del watchdog",
    "security.findings": "Hallazgos",
    "security.no_findings": "No se detectaron riesgos evidentes.",
    "security.metrics_endpoint": "Endpoint de m?tricas",
    "security.allow_lan": "Permitir acceso LAN",
    "security.allow_wan": "Permitir acceso WAN",
    "security.watchdog_enabled": "Watchdog habilitado",
    "security.auto_restart_runtime": "Reinicio autom?tico de Runtime",
    "security.auto_restart_interface": "Reinicio autom?tico de interfaces",
    "security.restart_cooldown": "Enfriamiento de reinicio",
    "security.default_token_warning": "El token de administrador sigue con el valor por defecto. C?mbialo de inmediato.",
    "security.wan_warning": "El acceso WAN est? habilitado. Confirma la fortaleza del token y la protecci?n del proxy inverso.",
    "security.auth_disabled_warning": "La autenticaci?n est? deshabilitada, as? que las p?ginas de administraci?n quedan abiertas para los or?genes de red permitidos.",
    "audit.filters": "Filtros",
    "audit.search": "Buscar",
    "audit.no_records": "No hay registros de auditor?a coincidentes.",
    "audit.total_records": "registros",
    "action.reset": "Restablecer",
    "field.user": "Usuario",
    "field.role": "Rol",
    "field.auth_mode": "Modo de autenticaci?n",
    "field.client": "Cliente",
    "field.client_zone": "Zona del cliente",
    "field.session": "Sesi?n",
    "field.access": "Acceso",
    "field.header": "Cabecera",
    "field.value": "Valor",
    "field.headers": "Cabeceras",
    "field.payload": "Carga",
    "field.limit": "L?mite",
    "value.authenticated": "Autenticado",
    "value.not_authenticated": "No autenticado",
    "value.administrator": "Administrador",
    "value.token_session": "Sesi?n con token",
    "value.enabled": "Habilitado",
    "value.local_token": "Token local",
    "value.protected": "Protegido",
    "value.open": "Abierto",
    "value.loopback": "Loopback",
    "value.lan": "LAN",
    "value.public": "P?blica",
    "value.all": "Todos"
  }
}

for locale, values in OPERATIONS_PAGE_TRANSLATIONS.items():
    TRANSLATIONS[locale].update(values)

ADMIN_EXTENSION_TRANSLATIONS = {
    "zh-CN": {
        "nav.maintenance": "维护模式",
        "nav.users": "用户",
        "nav.roles": "角色与权限",
        "nav.tokens": "API 令牌",
        "page.maintenance": "Hearth 维护模式",
        "page.users": "Hearth 用户",
        "page.roles": "Hearth 角色与权限",
        "page.tokens": "Hearth API 令牌",
        "maintenance.subtitle": "暂停自动恢复，安全执行升级、调试和网络调整。",
        "maintenance.watchdog_pause": "启用后将暂停看门狗自动恢复。",
        "maintenance.reason_hint": "说明本次维护窗口的用途。",
        "maintenance.current_state": "当前状态",
        "maintenance.controls": "维护控制",
        "maintenance.until_hours": "持续小时数",
        "maintenance.enable": "启用维护模式",
        "maintenance.disable": "关闭维护模式",
        "users.total": "个用户",
        "users.display_name": "显示名称",
        "users.create": "创建用户",
        "users.actions": "操作",
        "users.builtin": "内置",
        "users.change_role": "修改角色",
        "users.disable": "禁用",
        "users.enable": "启用",
        "roles.subtitle": "内置角色矩阵，用于规划 1.x 的权限边界。",
        "tokens.total": "个令牌",
        "tokens.copy_now": "新令牌只会显示这一次，请立即复制保存。",
        "tokens.name": "令牌名称",
        "tokens.scopes": "作用域",
        "tokens.expires_days": "过期天数",
        "tokens.create": "创建令牌",
        "tokens.actions": "操作",
        "tokens.builtin": "内置",
        "tokens.disable": "停用",
        "tokens.enable": "启用",
        "notice.maintenance_enabled": "维护模式已启用。",
        "notice.maintenance_disabled": "维护模式已关闭。",
        "notice.user_created": "用户已创建。",
        "notice.user_updated": "用户已更新。",
        "notice.token_created": "API 令牌已创建。",
        "notice.token_updated": "API 令牌已更新。",
        "value.owner": "所有者",
        "value.admin": "管理员",
        "value.operator": "操作员",
        "value.viewer": "只读",
        "value.service_manager": "服务管理者",
    },
    "en": {
        "nav.maintenance": "Maintenance",
        "nav.users": "Users",
        "nav.roles": "Roles",
        "nav.tokens": "API Tokens",
        "page.maintenance": "Hearth Maintenance",
        "page.users": "Hearth Users",
        "page.roles": "Hearth Roles & Permissions",
        "page.tokens": "Hearth API Tokens",
        "maintenance.subtitle": "Pause auto-recovery so upgrades, debugging, and network work stay safe.",
        "maintenance.watchdog_pause": "When enabled, watchdog auto-recovery is paused.",
        "maintenance.reason_hint": "Describe what this maintenance window is for.",
        "maintenance.current_state": "Current State",
        "maintenance.controls": "Maintenance Controls",
        "maintenance.until_hours": "Duration Hours",
        "maintenance.enable": "Enable Maintenance",
        "maintenance.disable": "Disable Maintenance",
        "users.total": "users",
        "users.display_name": "Display Name",
        "users.create": "Create User",
        "users.actions": "Actions",
        "users.builtin": "Built-in",
        "users.change_role": "Change Role",
        "users.disable": "Disable",
        "users.enable": "Enable",
        "roles.subtitle": "Built-in role matrix for the 1.x permission boundary.",
        "tokens.total": "tokens",
        "tokens.copy_now": "A new token is shown only once. Copy and store it now.",
        "tokens.name": "Token Name",
        "tokens.scopes": "Scopes",
        "tokens.expires_days": "Expires In Days",
        "tokens.create": "Create Token",
        "tokens.actions": "Actions",
        "tokens.builtin": "Built-in",
        "tokens.disable": "Disable",
        "tokens.enable": "Enable",
        "notice.maintenance_enabled": "Maintenance mode enabled.",
        "notice.maintenance_disabled": "Maintenance mode disabled.",
        "notice.user_created": "User created.",
        "notice.user_updated": "User updated.",
        "notice.token_created": "API token created.",
        "notice.token_updated": "API token updated.",
        "value.owner": "Owner",
        "value.admin": "Admin",
        "value.operator": "Operator",
        "value.viewer": "Viewer",
        "value.service_manager": "Service Manager",
    },
    "ja": {
        "nav.maintenance": "メンテナンス",
        "nav.users": "ユーザー",
        "nav.roles": "ロール",
        "nav.tokens": "API トークン",
        "page.maintenance": "Hearth メンテナンス",
        "page.users": "Hearth ユーザー",
        "page.roles": "Hearth ロールと権限",
        "page.tokens": "Hearth API トークン",
        "maintenance.enable": "メンテナンスを有効化",
        "maintenance.disable": "メンテナンスを解除",
        "users.create": "ユーザー作成",
        "users.change_role": "ロール変更",
        "tokens.create": "トークン作成",
        "tokens.disable": "無効化",
        "tokens.enable": "有効化",
        "value.owner": "オーナー",
        "value.admin": "管理者",
        "value.operator": "オペレーター",
        "value.viewer": "閲覧者",
        "value.service_manager": "サービス管理者",
    },
    "ko": {
        "nav.maintenance": "유지보수",
        "nav.users": "사용자",
        "nav.roles": "역할",
        "nav.tokens": "API 토큰",
        "page.maintenance": "Hearth 유지보수",
        "page.users": "Hearth 사용자",
        "page.roles": "Hearth 역할 및 권한",
        "page.tokens": "Hearth API 토큰",
        "maintenance.enable": "유지보수 켜기",
        "maintenance.disable": "유지보수 끄기",
        "users.create": "사용자 생성",
        "users.change_role": "역할 변경",
        "tokens.create": "토큰 생성",
        "tokens.disable": "비활성화",
        "tokens.enable": "활성화",
        "value.owner": "소유자",
        "value.admin": "관리자",
        "value.operator": "운영자",
        "value.viewer": "조회자",
        "value.service_manager": "서비스 관리자",
    },
    "es": {
        "nav.maintenance": "Mantenimiento",
        "nav.users": "Usuarios",
        "nav.roles": "Roles",
        "nav.tokens": "Tokens API",
        "page.maintenance": "Mantenimiento de Hearth",
        "page.users": "Usuarios de Hearth",
        "page.roles": "Roles y permisos de Hearth",
        "page.tokens": "Tokens API de Hearth",
        "maintenance.enable": "Activar mantenimiento",
        "maintenance.disable": "Desactivar mantenimiento",
        "users.create": "Crear usuario",
        "users.change_role": "Cambiar rol",
        "tokens.create": "Crear token",
        "tokens.disable": "Desactivar",
        "tokens.enable": "Activar",
        "value.owner": "Propietario",
        "value.admin": "Administrador",
        "value.operator": "Operador",
        "value.viewer": "Solo lectura",
        "value.service_manager": "Gestor de servicios",
    },
}

for locale, values in ADMIN_EXTENSION_TRANSLATIONS.items():
    TRANSLATIONS[locale].update(values)

PLUGIN_SERVICE_TRANSLATIONS = {
    "zh-CN": {
        "auth.forbidden": "当前令牌没有执行此操作的权限。",
        "nav.plugins": "插件",
        "nav.services": "服务",
        "page.plugins": "Hearth 插件",
        "page.plugin_detail": "Hearth 插件详情",
        "page.services": "Hearth 服务",
        "page.service_detail": "Hearth 服务详情",
        "plugins.total": "个插件",
        "plugins.empty": "当前没有配置插件。",
        "plugins.detail": "插件详情",
        "plugins.controls": "插件控制",
        "plugins.permissions": "权限声明",
        "plugins.config": "插件配置",
        "plugins.version": "版本",
        "plugins.compatibility": "兼容性",
        "plugins.enable": "启用插件",
        "plugins.disable": "停用插件",
        "plugins.back": "返回插件列表",
        "services.total": "个服务",
        "services.category": "分类",
        "services.detail": "服务详情",
        "services.controls": "服务控制",
        "services.back": "返回服务列表",
        "notice.plugin_updated": "插件状态已更新。",
        "notice.service_updated": "服务操作已执行。",
        "value.ready": "就绪",
        "value.idle": "空闲",
        "value.paused": "暂停",
    },
    "en": {
        "auth.forbidden": "This token does not have permission to perform the action.",
        "nav.plugins": "Plugins",
        "nav.services": "Services",
        "page.plugins": "Hearth Plugins",
        "page.plugin_detail": "Hearth Plugin Detail",
        "page.services": "Hearth Services",
        "page.service_detail": "Hearth Service Detail",
        "plugins.total": "plugins",
        "plugins.empty": "No plugins are configured.",
        "plugins.detail": "Plugin Details",
        "plugins.controls": "Plugin Controls",
        "plugins.permissions": "Permission Declarations",
        "plugins.config": "Plugin Config",
        "plugins.version": "Version",
        "plugins.compatibility": "Compatibility",
        "plugins.enable": "Enable Plugin",
        "plugins.disable": "Disable Plugin",
        "plugins.back": "Back to Plugins",
        "services.total": "services",
        "services.category": "Category",
        "services.detail": "Service Details",
        "services.controls": "Service Controls",
        "services.back": "Back to Services",
        "notice.plugin_updated": "Plugin state updated.",
        "notice.service_updated": "Service action completed.",
        "value.ready": "Ready",
        "value.idle": "Idle",
        "value.paused": "Paused",
    },
    "ja": {
        "nav.plugins": "プラグイン",
        "nav.services": "サービス",
        "page.plugins": "Hearth プラグイン",
        "page.services": "Hearth サービス",
    },
    "ko": {
        "nav.plugins": "플러그인",
        "nav.services": "서비스",
        "page.plugins": "Hearth 플러그인",
        "page.services": "Hearth 서비스",
    },
    "es": {
        "nav.plugins": "Plugins",
        "nav.services": "Servicios",
        "page.plugins": "Plugins de Hearth",
        "page.services": "Servicios de Hearth",
    },
}

for locale, values in PLUGIN_SERVICE_TRANSLATIONS.items():
    TRANSLATIONS[locale].update(values)


PLUGIN_SERVICE_UI_FIXES = {
    "zh-CN": {
        "auth.forbidden": "???????????????",
        "nav.plugins": "??",
        "nav.services": "??",
        "page.plugins": "Hearth ??",
        "page.plugin_detail": "Hearth ????",
        "page.plugin_sources": "????",
        "page.services": "Hearth ??",
        "page.service_detail": "Hearth ????",
        "plugins.total": "???",
        "plugins.sources_total": "???",
        "plugins.empty": "?????????",
        "plugins.detail": "????",
        "plugins.controls": "????",
        "plugins.permissions": "????",
        "plugins.dependencies": "????",
        "plugins.diagnostics": "????",
        "plugins.config": "????",
        "plugins.version": "??",
        "plugins.compatibility": "???",
        "plugins.trusted": "????",
        "plugins.sync_state": "????",
        "plugins.plugin_count": "????",
        "plugins.enabled_count": "?????",
        "plugins.enable": "????",
        "plugins.disable": "????",
        "plugins.back": "??????",
        "plugins.not_found": "????????",
        "services.total": "???",
        "services.category": "??",
        "services.detail": "????",
        "services.controls": "????",
        "services.back": "??????",
        "services.dependencies": "????",
        "services.health_checks": "????",
        "services.logs": "????",
        "services.resources": "????",
        "services.not_found": "????????",
        "notice.plugin_updated": "????????",
        "notice.service_updated": "????????",
        "value.ready": "??",
        "value.idle": "??",
        "value.paused": "??",
    },
    "en": {
        "auth.forbidden": "This token does not have permission to perform the action.",
        "nav.plugins": "Plugins",
        "nav.services": "Services",
        "page.plugins": "Hearth Plugins",
        "page.plugin_detail": "Hearth Plugin Detail",
        "page.plugin_sources": "Plugin Sources",
        "page.services": "Hearth Services",
        "page.service_detail": "Hearth Service Detail",
        "plugins.total": "plugins",
        "plugins.sources_total": "sources",
        "plugins.empty": "No plugins are configured.",
        "plugins.detail": "Plugin Details",
        "plugins.controls": "Plugin Controls",
        "plugins.permissions": "Permission Declarations",
        "plugins.dependencies": "Dependencies",
        "plugins.diagnostics": "Diagnostics",
        "plugins.config": "Plugin Config",
        "plugins.version": "Version",
        "plugins.compatibility": "Compatibility",
        "plugins.trusted": "Trusted Source",
        "plugins.sync_state": "Sync State",
        "plugins.plugin_count": "Plugin Count",
        "plugins.enabled_count": "Enabled",
        "plugins.enable": "Enable Plugin",
        "plugins.disable": "Disable Plugin",
        "plugins.back": "Back to Plugins",
        "plugins.not_found": "The requested plugin was not found.",
        "services.total": "services",
        "services.category": "Category",
        "services.detail": "Service Details",
        "services.controls": "Service Controls",
        "services.back": "Back to Services",
        "services.dependencies": "Dependencies",
        "services.health_checks": "Health Checks",
        "services.logs": "Recent Logs",
        "services.resources": "Resource Summary",
        "services.not_found": "The requested service was not found.",
        "notice.plugin_updated": "Plugin state updated.",
        "notice.service_updated": "Service action completed.",
        "value.ready": "Ready",
        "value.idle": "Idle",
        "value.paused": "Paused",
    },
    "ja": {
        "nav.plugins": "?????",
        "nav.services": "????",
        "page.plugins": "Hearth ?????",
        "page.plugin_detail": "Hearth ???????",
        "page.plugin_sources": "????????",
        "page.services": "Hearth ????",
        "page.service_detail": "Hearth ??????",
        "plugins.dependencies": "????",
        "plugins.diagnostics": "??",
        "plugins.trusted": "???????",
        "plugins.sync_state": "????",
        "plugins.plugin_count": "??????",
        "plugins.enabled_count": "???",
        "plugins.not_found": "??????????????",
        "services.dependencies": "????",
        "services.health_checks": "???????",
        "services.logs": "?????",
        "services.resources": "??????",
        "services.not_found": "?????????????",
        "value.ready": "????",
        "value.idle": "???",
        "value.paused": "????",
    },
    "ko": {
        "nav.plugins": "????",
        "nav.services": "???",
        "page.plugins": "Hearth ????",
        "page.plugin_detail": "Hearth ???? ??",
        "page.plugin_sources": "???? ??",
        "page.services": "Hearth ???",
        "page.service_detail": "Hearth ??? ??",
        "plugins.dependencies": "???",
        "plugins.diagnostics": "??",
        "plugins.trusted": "??? ??",
        "plugins.sync_state": "??? ??",
        "plugins.plugin_count": "???? ?",
        "plugins.enabled_count": "?? ?",
        "plugins.not_found": "????? ?? ? ????.",
        "services.dependencies": "???",
        "services.health_checks": "?? ??",
        "services.logs": "?? ??",
        "services.resources": "??? ??",
        "services.not_found": "???? ?? ? ????.",
        "value.ready": "???",
        "value.idle": "??",
        "value.paused": "?? ??",
    },
    "es": {
        "nav.plugins": "Plugins",
        "nav.services": "Servicios",
        "page.plugins": "Plugins de Hearth",
        "page.plugin_detail": "Detalle del plugin",
        "page.plugin_sources": "Fuentes de plugins",
        "page.services": "Servicios de Hearth",
        "page.service_detail": "Detalle del servicio",
        "plugins.dependencies": "Dependencias",
        "plugins.diagnostics": "Diagn?stico",
        "plugins.trusted": "Fuente confiable",
        "plugins.sync_state": "Estado de sincronizaci?n",
        "plugins.plugin_count": "Cantidad de plugins",
        "plugins.enabled_count": "Habilitados",
        "plugins.not_found": "No se encontr? el plugin solicitado.",
        "services.dependencies": "Dependencias",
        "services.health_checks": "Comprobaciones de salud",
        "services.logs": "Registros recientes",
        "services.resources": "Resumen de recursos",
        "services.not_found": "No se encontr? el servicio solicitado.",
        "value.ready": "Listo",
        "value.idle": "Inactivo",
        "value.paused": "Pausado",
    },
}

for locale, values in PLUGIN_SERVICE_UI_FIXES.items():
    TRANSLATIONS[locale].update(values)


SECOND_PRIORITY_UI_FIXES = {
    "zh-CN": {
        "nav.fleet": "????",
        "page.fleet": "Fleet ??",
        "page.fleet_nodes": "????",
        "page.fleet_groups": "????",
        "page.templates": "????",
        "fleet.total_nodes": "???",
        "fleet.online": "??",
        "fleet.offline": "??",
        "fleet.degraded": "??",
        "fleet.critical": "??",
        "fleet.recent_alerts": "????",
        "fleet.version_distribution": "????",
        "fleet.group_summary": "????",
        "fleet.groups_total": "???",
        "fleet.templates_total": "???",
        "fleet.register_node": "????",
        "fleet.create_group": "????",
        "fleet.group_type": "????",
        "fleet.create_template": "????",
        "fleet.target_nodes": "????",
        "fleet.applied_nodes": "????",
        "field.version": "??",
        "field.group": "??",
        "field.tags": "??",
        "field.region": "??",
        "field.description": "??",
        "field.template": "??",
        "config.revisions": "??????",
        "config.revision_id": "???",
        "config.compare_summary": "????",
        "config.changed_lines": "????",
        "config.no_revisions": "????????????",
        "config.select_revision_hint": "?????????????????????????????",
        "notice.fleet_node_saved": "????????",
        "notice.group_saved": "????????",
        "notice.template_saved": "????????",
    },
    "en": {
        "nav.fleet": "Fleet",
        "page.fleet": "Fleet Dashboard",
        "page.fleet_nodes": "Nodes Inventory",
        "page.fleet_groups": "Node Groups",
        "page.templates": "Templates",
        "fleet.total_nodes": "nodes",
        "fleet.online": "Online",
        "fleet.offline": "Offline",
        "fleet.degraded": "Degraded",
        "fleet.critical": "Critical",
        "fleet.recent_alerts": "Recent Alerts",
        "fleet.version_distribution": "Version Distribution",
        "fleet.group_summary": "Group Summary",
        "fleet.groups_total": "groups",
        "fleet.templates_total": "templates",
        "fleet.register_node": "Register Node",
        "fleet.create_group": "Create Group",
        "fleet.group_type": "Group Type",
        "fleet.create_template": "Create Template",
        "fleet.target_nodes": "Target Nodes",
        "fleet.applied_nodes": "Applied Nodes",
        "field.version": "Version",
        "field.group": "Group",
        "field.tags": "Tags",
        "field.region": "Region",
        "field.description": "Description",
        "field.template": "Template",
        "config.revisions": "Revision History",
        "config.revision_id": "Revision",
        "config.compare_summary": "Compare Summary",
        "config.changed_lines": "Changed Lines",
        "config.no_revisions": "No config revisions have been recorded yet.",
        "config.select_revision_hint": "Select a revision to load it into the editor and inspect the current diff.",
        "notice.fleet_node_saved": "Fleet inventory updated.",
        "notice.group_saved": "Node group saved.",
        "notice.template_saved": "Config template saved.",
    },
    "ja": {
        "nav.fleet": "????",
        "page.fleet": "???????????",
        "page.fleet_nodes": "?????",
        "page.fleet_groups": "???????",
        "page.templates": "??????",
        "config.revisions": "????",
    },
    "ko": {
        "nav.fleet": "??",
        "page.fleet": "?? ????",
        "page.fleet_nodes": "?? ????",
        "page.fleet_groups": "?? ??",
        "page.templates": "???",
        "config.revisions": "?? ??",
    },
    "es": {
        "nav.fleet": "Flota",
        "page.fleet": "Panel de flota",
        "page.fleet_nodes": "Inventario de nodos",
        "page.fleet_groups": "Grupos de nodos",
        "page.templates": "Plantillas",
        "config.revisions": "Historial de revisiones",
    },
}

for locale, values in SECOND_PRIORITY_UI_FIXES.items():
    TRANSLATIONS[locale].update(values)


THIRD_PRIORITY_UI_FIXES = {
    "zh-CN": {
        "nav.bridges": "??",
        "nav.metrics": "??",
        "nav.alerts": "??",
        "nav.diagnostics": "??",
        "page.bridges": "????",
        "page.metrics": "????",
        "page.alerts": "????",
        "page.diagnostics": "?????",
        "bridges.total": "???",
        "bridges.configured_total": "???",
        "bridges.enabled_total": "???",
        "bridges.running_total": "???",
        "bridges.catalog": "????",
        "bridges.catalog_help": "??????????????????",
        "metrics.prometheus_endpoint": "Prometheus ??",
        "metrics.summary_api": "?? API",
        "metrics.export_targets": "????",
        "metrics.interface_counters": "?????",
        "metrics.traffic_window": "?? 24 ??????",
        "alerts.total": "???",
        "alerts.critical": "??",
        "alerts.warning": "??",
        "alerts.healthy": "??",
        "alerts.security_findings": "????",
        "alerts.no_active": "?????????",
        "alerts.feed": "?????",
        "diagnostics.runtime_snapshot": "?????",
        "diagnostics.environment": "????",
        "diagnostics.paths": "????",
        "diagnostics.scheduler": "???",
        "diagnostics.task_list": "????",
        "diagnostics.latest_revision": "??????",
        "diagnostics.plugin_diagnostics": "????",
        "diagnostics.service_diagnostics": "????",
        "diagnostics.recent_events": "????",
        "diagnostics.restart_history": "????",
        "diagnostics.no_tasks": "???????",
        "diagnostics.no_restarts": "???????",
        "field.transport": "??",
        "field.endpoint": "??",
        "field.mode": "??",
        "field.configured": "???",
        "field.path": "??",
        "field.value": "?",
        "field.platform": "??",
    },
    "en": {
        "nav.bridges": "Bridges",
        "nav.metrics": "Metrics",
        "nav.alerts": "Alerts",
        "nav.diagnostics": "Diagnostics",
        "page.bridges": "Bridge Services",
        "page.metrics": "Metrics Dashboard",
        "page.alerts": "Active Alerts",
        "page.diagnostics": "Developer Diagnostics",
        "bridges.total": "bridges",
        "bridges.configured_total": "Configured",
        "bridges.enabled_total": "Enabled",
        "bridges.running_total": "Running",
        "bridges.catalog": "Bridge Catalog",
        "bridges.catalog_help": "Shows built-in bridge slots and loaded bridge plugins.",
        "metrics.prometheus_endpoint": "Prometheus Endpoint",
        "metrics.summary_api": "Summary API",
        "metrics.export_targets": "Export Targets",
        "metrics.interface_counters": "Interface Counters",
        "metrics.traffic_window": "Recorded Traffic (Last 24 Hours)",
        "alerts.total": "alerts",
        "alerts.critical": "Critical",
        "alerts.warning": "Warning",
        "alerts.healthy": "Healthy",
        "alerts.security_findings": "Security Findings",
        "alerts.no_active": "No active alerts at the moment.",
        "alerts.feed": "Recent Alert Feed",
        "diagnostics.runtime_snapshot": "Runtime Snapshot",
        "diagnostics.environment": "Environment",
        "diagnostics.paths": "Paths",
        "diagnostics.scheduler": "Scheduler",
        "diagnostics.task_list": "Task List",
        "diagnostics.latest_revision": "Latest Config Revision",
        "diagnostics.plugin_diagnostics": "Plugin Diagnostics",
        "diagnostics.service_diagnostics": "Service Diagnostics",
        "diagnostics.recent_events": "Recent Events",
        "diagnostics.restart_history": "Restart History",
        "diagnostics.no_tasks": "No scheduled tasks.",
        "diagnostics.no_restarts": "No restart history yet.",
        "field.transport": "Transport",
        "field.endpoint": "Endpoint",
        "field.mode": "Mode",
        "field.configured": "Configured",
        "field.path": "Path",
        "field.value": "Value",
        "field.platform": "Platform",
    },
    "ja": {
        "nav.bridges": "????",
        "nav.metrics": "?????",
        "nav.alerts": "????",
        "nav.diagnostics": "??",
        "page.bridges": "????????",
        "page.metrics": "????????????",
        "page.alerts": "?????????",
        "page.diagnostics": "???????",
        "bridges.total": "??????",
        "bridges.configured_total": "????",
        "bridges.enabled_total": "??",
        "bridges.running_total": "???",
        "bridges.catalog": "??????",
        "bridges.catalog_help": "????????????????????????????????",
        "metrics.prometheus_endpoint": "Prometheus ???????",
        "metrics.summary_api": "???? API",
        "metrics.export_targets": "???????",
        "metrics.interface_counters": "????????????",
        "metrics.traffic_window": "?? 24 ???????????",
        "alerts.total": "??????",
        "alerts.critical": "??",
        "alerts.warning": "??",
        "alerts.healthy": "??",
        "alerts.security_findings": "????????",
        "alerts.no_active": "???????????????????",
        "alerts.feed": "??????????",
        "diagnostics.runtime_snapshot": "?????????????",
        "diagnostics.environment": "????",
        "diagnostics.paths": "????",
        "diagnostics.scheduler": "??????",
        "diagnostics.task_list": "??????",
        "diagnostics.latest_revision": "?????????",
        "diagnostics.plugin_diagnostics": "???????",
        "diagnostics.service_diagnostics": "??????",
        "diagnostics.recent_events": "???????",
        "diagnostics.restart_history": "?????",
        "diagnostics.no_tasks": "??????????????????",
        "diagnostics.no_restarts": "??????????????",
        "field.transport": "????",
        "field.endpoint": "???????",
        "field.mode": "???",
        "field.configured": "????",
        "field.path": "??",
        "field.value": "?",
        "field.platform": "????????",
    },
    "ko": {
        "nav.bridges": "???",
        "nav.metrics": "???",
        "nav.alerts": "??",
        "nav.diagnostics": "??",
        "page.bridges": "??? ???",
        "page.metrics": "??? ????",
        "page.alerts": "?? ??",
        "page.diagnostics": "??? ??",
        "bridges.total": "???",
        "bridges.configured_total": "???",
        "bridges.enabled_total": "????",
        "bridges.running_total": "?? ?",
        "bridges.catalog": "??? ????",
        "bridges.catalog_help": "?? ??? ??? ??? ??? ????? ?????.",
        "metrics.prometheus_endpoint": "Prometheus ?????",
        "metrics.summary_api": "?? API",
        "metrics.export_targets": "???? ??",
        "metrics.interface_counters": "????? ???",
        "metrics.traffic_window": "?? 24?? ?? ???",
        "alerts.total": "? ??",
        "alerts.critical": "???",
        "alerts.warning": "??",
        "alerts.healthy": "??",
        "alerts.security_findings": "?? ??",
        "alerts.no_active": "?? ?? ??? ????.",
        "alerts.feed": "?? ?? ??",
        "diagnostics.runtime_snapshot": "??? ???",
        "diagnostics.environment": "?? ??",
        "diagnostics.paths": "?? ??",
        "diagnostics.scheduler": "????",
        "diagnostics.task_list": "?? ??",
        "diagnostics.latest_revision": "?? ?? ???",
        "diagnostics.plugin_diagnostics": "???? ??",
        "diagnostics.service_diagnostics": "??? ??",
        "diagnostics.recent_events": "?? ???",
        "diagnostics.restart_history": "??? ??",
        "diagnostics.no_tasks": "??? ??? ????.",
        "diagnostics.no_restarts": "??? ??? ?? ????.",
        "field.transport": "??",
        "field.endpoint": "?????",
        "field.mode": "??",
        "field.configured": "???",
        "field.path": "??",
        "field.value": "?",
        "field.platform": "???",
    },
    "es": {
        "nav.bridges": "Puentes",
        "nav.metrics": "M?tricas",
        "nav.alerts": "Alertas",
        "nav.diagnostics": "Diagn?stico",
        "page.bridges": "Servicios de puente",
        "page.metrics": "Panel de m?tricas",
        "page.alerts": "Alertas activas",
        "page.diagnostics": "Diagn?stico para desarrolladores",
        "bridges.total": "puentes",
        "bridges.configured_total": "Configurados",
        "bridges.enabled_total": "Habilitados",
        "bridges.running_total": "En ejecuci?n",
        "bridges.catalog": "Cat?logo de puentes",
        "bridges.catalog_help": "Muestra los puentes integrados y los plugins de puente cargados.",
        "metrics.prometheus_endpoint": "Endpoint de Prometheus",
        "metrics.summary_api": "API de resumen",
        "metrics.export_targets": "Destinos de exportaci?n",
        "metrics.interface_counters": "Contadores de interfaz",
        "metrics.traffic_window": "Tr?fico registrado (?ltimas 24 horas)",
        "alerts.total": "alertas",
        "alerts.critical": "Cr?tica",
        "alerts.warning": "Advertencia",
        "alerts.healthy": "Saludable",
        "alerts.security_findings": "Hallazgos de seguridad",
        "alerts.no_active": "No hay alertas activas en este momento.",
        "alerts.feed": "Flujo reciente de alertas",
        "diagnostics.runtime_snapshot": "Instant?nea del runtime",
        "diagnostics.environment": "Entorno",
        "diagnostics.paths": "Rutas",
        "diagnostics.scheduler": "Programador",
        "diagnostics.task_list": "Lista de tareas",
        "diagnostics.latest_revision": "?ltima revisi?n de configuraci?n",
        "diagnostics.plugin_diagnostics": "Diagn?stico de plugins",
        "diagnostics.service_diagnostics": "Diagn?stico de servicios",
        "diagnostics.recent_events": "Eventos recientes",
        "diagnostics.restart_history": "Historial de reinicios",
        "diagnostics.no_tasks": "No hay tareas programadas.",
        "diagnostics.no_restarts": "Todav?a no hay historial de reinicios.",
        "field.transport": "Transporte",
        "field.endpoint": "Endpoint",
        "field.mode": "Modo",
        "field.configured": "Configurado",
        "field.path": "Ruta",
        "field.value": "Valor",
        "field.platform": "Plataforma",
    },
}

for locale, values in THIRD_PRIORITY_UI_FIXES.items():
    TRANSLATIONS[locale].update(values)


TOPOLOGY_UI_FIXES = {
    "zh-CN": {
        "nav.topology": "??",
        "page.topology": "????",
        "page.network_map": "????",
        "page.route_heatmap": "????",
        "page.critical_nodes": "????",
        "page.network_insights": "????",
        "topology.generated_at": "????",
        "topology.nodes_total": "????",
        "topology.edges_total": "????",
        "topology.connected_segments": "????",
        "topology.average_hops": "????",
        "topology.quick_views": "????",
        "topology.interface_segments": "????",
        "topology.peer_links": "Peer ??",
        "topology.route_links": "????",
        "topology.connectivity": "???",
        "topology.nodes_table": "???",
        "topology.hop_distribution": "????",
        "topology.members": "???",
        "topology.destinations": "???",
        "topology.islands": "????",
        "topology.bridge_nodes": "????",
        "topology.heatmap_table": "???",
        "topology.intensity": "??",
        "topology.candidates": "????",
        "topology.critical_table": "??????",
        "topology.classification": "??",
        "topology.impact_score": "????",
        "topology.score": "????",
        "topology.findings": "????",
        "topology.recommendations": "??",
        "topology.no_findings": "???????",
        "value.connected": "???",
        "value.isolated": "??",
    },
    "en": {
        "nav.topology": "Topology",
        "page.topology": "Network Topology",
        "page.network_map": "Network Map",
        "page.route_heatmap": "Route Heatmap",
        "page.critical_nodes": "Critical Nodes",
        "page.network_insights": "Network Insights",
        "topology.generated_at": "Generated",
        "topology.nodes_total": "Nodes",
        "topology.edges_total": "Edges",
        "topology.connected_segments": "Active Segments",
        "topology.average_hops": "Average Hops",
        "topology.quick_views": "Quick Views",
        "topology.interface_segments": "Interface Segments",
        "topology.peer_links": "Peer Links",
        "topology.route_links": "Route Links",
        "topology.connectivity": "Connectivity",
        "topology.nodes_table": "Nodes Table",
        "topology.hop_distribution": "Hop Distribution",
        "topology.members": "Members",
        "topology.destinations": "Destinations",
        "topology.islands": "Network Islands",
        "topology.bridge_nodes": "Bridge Nodes",
        "topology.heatmap_table": "Heatmap Table",
        "topology.intensity": "Intensity",
        "topology.candidates": "candidates",
        "topology.critical_table": "Critical Node Ranking",
        "topology.classification": "Class",
        "topology.impact_score": "Impact Score",
        "topology.score": "Network Score",
        "topology.findings": "Findings",
        "topology.recommendations": "Recommendations",
        "topology.no_findings": "No issues detected.",
        "value.connected": "Connected",
        "value.isolated": "Isolated",
    },
    "ja": {
        "nav.topology": "?????",
        "page.topology": "???????????",
        "page.network_map": "?????????",
        "page.route_heatmap": "?????????",
        "page.critical_nodes": "?????",
        "page.network_insights": "????????",
        "topology.generated_at": "????",
        "topology.nodes_total": "????",
        "topology.edges_total": "???",
        "topology.connected_segments": "???????",
        "topology.average_hops": "??????",
        "topology.quick_views": "???????",
        "topology.interface_segments": "??????????",
        "topology.peer_links": "Peer ??",
        "topology.route_links": "?????",
        "topology.connectivity": "???",
        "topology.nodes_table": "?????",
        "topology.hop_distribution": "?????",
        "topology.members": "?????",
        "topology.destinations": "??",
        "topology.islands": "?????????",
        "topology.bridge_nodes": "???????",
        "topology.heatmap_table": "???????",
        "topology.intensity": "??",
        "topology.candidates": "??",
        "topology.critical_table": "???????",
        "topology.classification": "??",
        "topology.impact_score": "???",
        "topology.score": "?????????",
        "topology.findings": "??",
        "topology.recommendations": "????",
        "topology.no_findings": "??????????????",
        "value.connected": "????",
        "value.isolated": "??",
    },
    "ko": {
        "nav.topology": "????",
        "page.topology": "???? ????",
        "page.network_map": "???? ?",
        "page.route_heatmap": "?? ???",
        "page.critical_nodes": "?? ??",
        "page.network_insights": "???? ????",
        "topology.generated_at": "?? ??",
        "topology.nodes_total": "?? ?",
        "topology.edges_total": "?? ?",
        "topology.connected_segments": "?? ????",
        "topology.average_hops": "?? ? ?",
        "topology.quick_views": "?? ??",
        "topology.interface_segments": "????? ????",
        "topology.peer_links": "?? ??",
        "topology.route_links": "?? ??",
        "topology.connectivity": "???",
        "topology.nodes_table": "?? ?",
        "topology.hop_distribution": "? ??",
        "topology.members": "??? ?",
        "topology.destinations": "??",
        "topology.islands": "???? ?? ??",
        "topology.bridge_nodes": "??? ??",
        "topology.heatmap_table": "??? ?",
        "topology.intensity": "??",
        "topology.candidates": "??",
        "topology.critical_table": "?? ?? ??",
        "topology.classification": "??",
        "topology.impact_score": "?? ??",
        "topology.score": "???? ??",
        "topology.findings": "?? ??",
        "topology.recommendations": "?? ??",
        "topology.no_findings": "??? ??? ????.",
        "value.connected": "???",
        "value.isolated": "??",
    },
    "es": {
        "nav.topology": "Topolog?a",
        "page.topology": "Topolog?a de red",
        "page.network_map": "Mapa de red",
        "page.route_heatmap": "Mapa t?rmico de rutas",
        "page.critical_nodes": "Nodos cr?ticos",
        "page.network_insights": "Insights de red",
        "topology.generated_at": "Generado",
        "topology.nodes_total": "Nodos",
        "topology.edges_total": "Enlaces",
        "topology.connected_segments": "Segmentos activos",
        "topology.average_hops": "Saltos promedio",
        "topology.quick_views": "Vistas r?pidas",
        "topology.interface_segments": "Segmentos de interfaz",
        "topology.peer_links": "Enlaces peer",
        "topology.route_links": "Enlaces de ruta",
        "topology.connectivity": "Conectividad",
        "topology.nodes_table": "Tabla de nodos",
        "topology.hop_distribution": "Distribuci?n de saltos",
        "topology.members": "Miembros",
        "topology.destinations": "Destinos",
        "topology.islands": "Islas de red",
        "topology.bridge_nodes": "Nodos puente",
        "topology.heatmap_table": "Tabla t?rmica",
        "topology.intensity": "Intensidad",
        "topology.candidates": "candidatos",
        "topology.critical_table": "Ranking de nodos cr?ticos",
        "topology.classification": "Clase",
        "topology.impact_score": "Impacto",
        "topology.score": "Puntuaci?n de red",
        "topology.findings": "Hallazgos",
        "topology.recommendations": "Recomendaciones",
        "topology.no_findings": "No se detectaron problemas.",
        "value.connected": "Conectado",
        "value.isolated": "Aislado",
    },
}

for locale, values in TOPOLOGY_UI_FIXES.items():
    TRANSLATIONS[locale].update(values)


OPERATIONS_UI_FIXES = {
    "zh-CN": {
        "nav.rollout": "????",
        "nav.remote_logs": "????",
        "nav.upgrade": "??",
        "page.rollout": "????",
        "page.remote_logs": "????",
        "page.upgrade": "?????",
        "rollout.total": "?????",
        "rollout.create": "??????",
        "rollout.action_type": "????",
        "rollout.no_runs": "???????",
        "remote_logs.total_entries": "???",
        "remote_logs.node_filter": "????",
        "upgrade.operations": "?????",
        "upgrade.schedule": "??????",
        "upgrade.target_version": "????",
        "upgrade.enable_maintenance": "??????",
        "upgrade.recent_revisions": "??????",
        "upgrade.no_operations": "??????????",
        "field.actor": "???",
        "field.origin": "????",
        "field.targets": "????",
        "field.channel": "??",
        "field.notes": "??",
        "field.version": "??",
        "field.group": "??",
        "field.template": "??",
        "field.description": "??",
        "notice.rollout_created": "????????",
        "notice.upgrade_scheduled": "????????",
        "notice.rollback_scheduled": "????????",
        "value.planned": "???",
    },
    "en": {
        "nav.rollout": "Rollout",
        "nav.remote_logs": "Remote Logs",
        "nav.upgrade": "Upgrade",
        "page.rollout": "Batch Actions",
        "page.remote_logs": "Remote Logs",
        "page.upgrade": "Upgrade & Rollback",
        "rollout.total": "batch actions",
        "rollout.create": "Create Batch Action",
        "rollout.action_type": "Action",
        "rollout.no_runs": "No batch actions recorded yet.",
        "remote_logs.total_entries": "entries",
        "remote_logs.node_filter": "Node Filter",
        "upgrade.operations": "operations",
        "upgrade.schedule": "Schedule Operation",
        "upgrade.target_version": "Target Version",
        "upgrade.enable_maintenance": "Enable Maintenance",
        "upgrade.recent_revisions": "Recent Revisions",
        "upgrade.no_operations": "No upgrade or rollback operations yet.",
        "field.actor": "Actor",
        "field.origin": "Origin",
        "field.targets": "Targets",
        "field.channel": "Channel",
        "field.notes": "Notes",
        "field.version": "Version",
        "field.group": "Group",
        "field.template": "Template",
        "field.description": "Description",
        "notice.rollout_created": "Batch action recorded.",
        "notice.upgrade_scheduled": "Upgrade operation scheduled.",
        "notice.rollback_scheduled": "Rollback operation scheduled.",
        "value.planned": "Planned",
    },
    "ja": {
        "nav.rollout": "??????",
        "nav.remote_logs": "??????",
        "nav.upgrade": "???????",
        "page.rollout": "????",
        "page.remote_logs": "??????",
        "page.upgrade": "??????????????",
        "rollout.total": "??????",
        "rollout.create": "???????",
        "rollout.action_type": "????",
        "rollout.no_runs": "?????????????",
        "remote_logs.total_entries": "????",
        "remote_logs.node_filter": "???????",
        "upgrade.operations": "????",
        "upgrade.schedule": "?????????",
        "upgrade.target_version": "???????",
        "upgrade.enable_maintenance": "??????????",
        "upgrade.recent_revisions": "??????????",
        "upgrade.no_operations": "????????????????????????????",
        "field.actor": "???",
        "field.origin": "??",
        "field.targets": "?????",
        "field.channel": "????",
        "field.notes": "??",
        "field.version": "?????",
        "field.group": "????",
        "field.template": "??????",
        "field.description": "??",
        "notice.rollout_created": "????????????",
        "notice.upgrade_scheduled": "?????????????????",
        "notice.rollback_scheduled": "????????????????",
        "value.planned": "????",
    },
    "ko": {
        "nav.rollout": "???",
        "nav.remote_logs": "?? ??",
        "nav.upgrade": "?????",
        "page.rollout": "?? ??",
        "page.remote_logs": "?? ??",
        "page.upgrade": "????? ? ??",
        "rollout.total": "? ??",
        "rollout.create": "?? ?? ??",
        "rollout.action_type": "?? ??",
        "rollout.no_runs": "?? ??? ?? ??? ????.",
        "remote_logs.total_entries": "? ??",
        "remote_logs.node_filter": "?? ??",
        "upgrade.operations": "? ??",
        "upgrade.schedule": "?? ??",
        "upgrade.target_version": "?? ??",
        "upgrade.enable_maintenance": "???? ?? ???",
        "upgrade.recent_revisions": "?? ?? ???",
        "upgrade.no_operations": "?? ????? ?? ?? ??? ????.",
        "field.actor": "???",
        "field.origin": "??",
        "field.targets": "?? ??",
        "field.channel": "??",
        "field.notes": "??",
        "field.version": "??",
        "field.group": "??",
        "field.template": "???",
        "field.description": "??",
        "notice.rollout_created": "?? ??? ???????.",
        "notice.upgrade_scheduled": "????? ??? ???????.",
        "notice.rollback_scheduled": "?? ??? ???????.",
        "value.planned": "???",
    },
    "es": {
        "nav.rollout": "Despliegue",
        "nav.remote_logs": "Logs remotos",
        "nav.upgrade": "Actualizaci?n",
        "page.rollout": "Acciones por lotes",
        "page.remote_logs": "Logs remotos",
        "page.upgrade": "Actualizaci?n y rollback",
        "rollout.total": "acciones por lote",
        "rollout.create": "Crear acci?n por lote",
        "rollout.action_type": "Acci?n",
        "rollout.no_runs": "Todav?a no hay acciones por lote registradas.",
        "remote_logs.total_entries": "entradas",
        "remote_logs.node_filter": "Filtro de nodo",
        "upgrade.operations": "operaciones",
        "upgrade.schedule": "Programar operaci?n",
        "upgrade.target_version": "Versi?n objetivo",
        "upgrade.enable_maintenance": "Activar mantenimiento",
        "upgrade.recent_revisions": "Revisiones recientes",
        "upgrade.no_operations": "Todav?a no hay operaciones de actualizaci?n o rollback.",
        "field.actor": "Actor",
        "field.origin": "Origen",
        "field.targets": "Objetivos",
        "field.channel": "Canal",
        "field.notes": "Notas",
        "field.version": "Versi?n",
        "field.group": "Grupo",
        "field.template": "Plantilla",
        "field.description": "Descripci?n",
        "notice.rollout_created": "Acci?n por lote registrada.",
        "notice.upgrade_scheduled": "Operaci?n de actualizaci?n programada.",
        "notice.rollback_scheduled": "Operaci?n de rollback programada.",
        "value.planned": "Planificada",
    },
}

for locale, values in OPERATIONS_UI_FIXES.items():
    TRANSLATIONS[locale].update(values)


FLEET_EXPANSION_TRANSLATIONS = {
    "zh-CN": {
        "page.fleet_node_detail": "????",
        "page.tags": "??",
        "page.fleet_health": "Fleet ??",
        "page.fleet_events": "Fleet ??",
        "page.api_docs": "API ??",
        "fleet.tags_total": "???",
        "fleet.events_total": "???",
        "fleet.health_summary": "????",
        "fleet.at_risk_nodes": "????",
        "fleet.no_tags": "????????",
        "fleet.no_group_health": "????????????",
        "fleet.node_not_found": "?????? Fleet ???",
        "docs.swagger": "Swagger UI",
        "docs.redoc": "ReDoc",
        "docs.openapi": "OpenAPI JSON",
        "docs.api_base": "API ????",
        "docs.examples": "????",
        "docs.auth_hint": "???? API ?? `X-Hearth-Token` ????????? Web ???????? Cookie?",
    },
    "en": {
        "page.fleet_node_detail": "Node Detail",
        "page.tags": "Tags",
        "page.fleet_health": "Fleet Health",
        "page.fleet_events": "Fleet Events",
        "page.api_docs": "API Docs",
        "fleet.tags_total": "tags",
        "fleet.events_total": "events",
        "fleet.health_summary": "Health Summary",
        "fleet.at_risk_nodes": "At-Risk Nodes",
        "fleet.no_tags": "No tags have been defined yet.",
        "fleet.no_group_health": "No group health summaries yet.",
        "fleet.node_not_found": "Requested fleet node was not found.",
        "docs.swagger": "Swagger UI",
        "docs.redoc": "ReDoc",
        "docs.openapi": "OpenAPI JSON",
        "docs.api_base": "API Base URL",
        "docs.examples": "Example Calls",
        "docs.auth_hint": "Protected API calls require the `X-Hearth-Token` header, or an admin cookie from the web console.",
    },
    "ja": {
        "page.fleet_node_detail": "?????",
        "page.tags": "??",
        "page.fleet_health": "Fleet ???",
        "page.fleet_events": "Fleet ????",
        "page.api_docs": "API ??????",
        "fleet.tags_total": "??",
        "fleet.events_total": "????",
        "fleet.health_summary": "?????",
        "fleet.at_risk_nodes": "??????",
        "fleet.no_tags": "???????????????",
        "fleet.no_group_health": "???????????????????",
        "fleet.node_not_found": "????? Fleet ????????????",
        "docs.swagger": "Swagger UI",
        "docs.redoc": "ReDoc",
        "docs.openapi": "OpenAPI JSON",
        "docs.api_base": "API ??? URL",
        "docs.examples": "?????",
        "docs.auth_hint": "????? API ??????? `X-Hearth-Token` ???????? Web ???????? Cookie ??????",
    },
    "ko": {
        "page.fleet_node_detail": "?? ??",
        "page.tags": "??",
        "page.fleet_health": "Fleet ??",
        "page.fleet_events": "Fleet ???",
        "page.api_docs": "API ??",
        "fleet.tags_total": "??",
        "fleet.events_total": "???",
        "fleet.health_summary": "?? ??",
        "fleet.at_risk_nodes": "?? ??",
        "fleet.no_tags": "?? ??? ??? ????.",
        "fleet.no_group_health": "?? ?? ??? ?? ????.",
        "fleet.node_not_found": "??? Fleet ??? ?? ? ????.",
        "docs.swagger": "Swagger UI",
        "docs.redoc": "ReDoc",
        "docs.openapi": "OpenAPI JSON",
        "docs.api_base": "API ?? URL",
        "docs.examples": "?? ??",
        "docs.auth_hint": "??? API ???? `X-Hearth-Token` ?? ?? ? ??? ??? ??? ?????.",
    },
    "es": {
        "page.fleet_node_detail": "Detalle del nodo",
        "page.tags": "Etiquetas",
        "page.fleet_health": "Salud de la flota",
        "page.fleet_events": "Eventos de la flota",
        "page.api_docs": "Documentaci?n API",
        "fleet.tags_total": "etiquetas",
        "fleet.events_total": "eventos",
        "fleet.health_summary": "Resumen de salud",
        "fleet.at_risk_nodes": "Nodos en riesgo",
        "fleet.no_tags": "A?n no hay etiquetas definidas.",
        "fleet.no_group_health": "Todav?a no hay res?menes de salud por grupo.",
        "fleet.node_not_found": "No se encontr? el nodo de flota solicitado.",
        "docs.swagger": "Swagger UI",
        "docs.redoc": "ReDoc",
        "docs.openapi": "OpenAPI JSON",
        "docs.api_base": "URL base de la API",
        "docs.examples": "Ejemplos de llamadas",
        "docs.auth_hint": "Las llamadas API protegidas requieren el encabezado `X-Hearth-Token` o una cookie de administrador del panel web.",
    },
}

for locale, values in FLEET_EXPANSION_TRANSLATIONS.items():
    TRANSLATIONS[locale].update(values)


TIMELINE_AND_PATH_TRANSLATIONS = {
    "zh-CN": {
        "nav.timeline": "\u65f6\u95f4\u7ebf",
        "nav.path_changes": "\u8def\u5f84\u53d8\u5316",
        "page.timeline": "\u4e8b\u4ef6\u65f6\u95f4\u7ebf",
        "page.path_changes": "\u8def\u5f84\u53d8\u5316",
        "timeline.total_events": "\u4e8b\u4ef6",
        "timeline.critical_events": "\u4e25\u91cd\u4e8b\u4ef6",
        "timeline.sources": "\u6765\u6e90",
        "timeline.time_buckets": "\u65f6\u95f4\u6876",
        "timeline.activity_buckets": "\u6d3b\u52a8\u6876",
        "timeline.recent_events": "\u6700\u65b0\u4e8b\u4ef6",
        "timeline.no_events": "\u5728\u9009\u5b9a\u7a97\u53e3\u5185\u6682\u65e0\u4e8b\u4ef6\u3002",
        "timeline.bucket_window": "\u6876\u7a97\u53e3\uff08\u5206\u949f\uff09",
        "topology.total_changes": "\u53d8\u66f4",
        "topology.volatility_score": "\u6ce2\u52a8\u5206\u6570",
        "topology.added_routes": "\u65b0\u589e\u8def\u5f84",
        "topology.changed_routes": "\u53d8\u66f4\u8def\u5f84",
        "topology.removed_routes": "\u79fb\u9664\u8def\u5f84",
        "topology.recent_changes": "\u6700\u65b0\u53d8\u66f4",
        "topology.most_volatile": "\u6ce2\u52a8\u6700\u9ad8\u7684\u76ee\u6807",
        "topology.no_path_changes": "\u6682\u65e0\u8def\u5f84\u53d8\u66f4\u8bb0\u5f55\u3002",
        "topology.interface_churn": "\u63a5\u53e3\u53d8\u52a8",
        "topology.destination_count": "\u76ee\u6807\u6570",
        "topology.change_type": "\u53d8\u66f4\u7c7b\u578b",
    },
    "en": {
        "nav.timeline": "Timeline",
        "nav.path_changes": "Path Changes",
        "page.timeline": "Event Timeline",
        "page.path_changes": "Path Changes",
        "timeline.total_events": "events",
        "timeline.critical_events": "Critical Events",
        "timeline.sources": "Sources",
        "timeline.time_buckets": "buckets",
        "timeline.activity_buckets": "Activity Buckets",
        "timeline.recent_events": "Recent Events",
        "timeline.no_events": "No events were recorded in the selected window.",
        "timeline.bucket_window": "Bucket Window",
        "topology.total_changes": "changes",
        "topology.volatility_score": "Volatility Score",
        "topology.added_routes": "Added Routes",
        "topology.changed_routes": "Changed Routes",
        "topology.removed_routes": "Removed Routes",
        "topology.recent_changes": "Recent Changes",
        "topology.most_volatile": "Most Volatile Destinations",
        "topology.no_path_changes": "No path changes have been recorded yet.",
        "topology.interface_churn": "Interface Churn",
        "topology.destination_count": "destinations",
        "topology.change_type": "Change Type",
    },
    "ja": {
        "nav.timeline": "\u30bf\u30a4\u30e0\u30e9\u30a4\u30f3",
        "nav.path_changes": "\u30d1\u30b9\u5909\u66f4",
        "page.timeline": "\u30a4\u30d9\u30f3\u30c8\u30bf\u30a4\u30e0\u30e9\u30a4\u30f3",
        "page.path_changes": "\u30d1\u30b9\u5909\u66f4",
        "timeline.total_events": "\u30a4\u30d9\u30f3\u30c8",
        "timeline.critical_events": "\u91cd\u8981\u30a4\u30d9\u30f3\u30c8",
        "timeline.sources": "\u30bd\u30fc\u30b9",
        "timeline.time_buckets": "\u30d0\u30b1\u30c3\u30c8",
        "timeline.activity_buckets": "\u30a2\u30af\u30c6\u30a3\u30d3\u30c6\u30a3\u30d0\u30b1\u30c3\u30c8",
        "timeline.recent_events": "\u6700\u65b0\u30a4\u30d9\u30f3\u30c8",
        "timeline.no_events": "\u9078\u629e\u3057\u305f\u671f\u9593\u306b\u30a4\u30d9\u30f3\u30c8\u306f\u3042\u308a\u307e\u305b\u3093\u3002",
        "timeline.bucket_window": "\u30d0\u30b1\u30c3\u30c8\u7a93\u53e3\uff08\u5206\uff09",
        "topology.total_changes": "\u5909\u66f4",
        "topology.volatility_score": "\u5909\u52d5\u30b9\u30b3\u30a2",
        "topology.added_routes": "\u8ffd\u52a0\u3055\u308c\u305f\u30eb\u30fc\u30c8",
        "topology.changed_routes": "\u5909\u66f4\u3055\u308c\u305f\u30eb\u30fc\u30c8",
        "topology.removed_routes": "\u524a\u9664\u3055\u308c\u305f\u30eb\u30fc\u30c8",
        "topology.recent_changes": "\u6700\u65b0\u306e\u5909\u66f4",
        "topology.most_volatile": "\u5909\u52d5\u304c\u5927\u304d\u3044\u5b9b\u5148",
        "topology.no_path_changes": "\u307e\u3060\u30d1\u30b9\u5909\u66f4\u306f\u8a18\u9332\u3055\u308c\u3066\u3044\u307e\u305b\u3093\u3002",
        "topology.interface_churn": "\u30a4\u30f3\u30bf\u30fc\u30d5\u30a7\u30fc\u30b9\u5909\u52d5",
        "topology.destination_count": "\u5b9b\u5148\u6570",
        "topology.change_type": "\u5909\u66f4\u7a2e\u5225",
    },
    "ko": {
        "nav.timeline": "\ud0c0\uc784\ub77c\uc778",
        "nav.path_changes": "\uacbd\ub85c \ubcc0\uacbd",
        "page.timeline": "\uc774\ubca4\ud2b8 \ud0c0\uc784\ub77c\uc778",
        "page.path_changes": "\uacbd\ub85c \ubcc0\uacbd",
        "timeline.total_events": "\uc774\ubca4\ud2b8",
        "timeline.critical_events": "\uc2ec\uac01 \uc774\ubca4\ud2b8",
        "timeline.sources": "\uc18c\uc2a4",
        "timeline.time_buckets": "\ubc84\ud0b7",
        "timeline.activity_buckets": "\ud65c\ub3d9 \ubc84\ud0b7",
        "timeline.recent_events": "\ucd5c\uc2e0 \uc774\ubca4\ud2b8",
        "timeline.no_events": "\uc120\ud0dd\ud55c \uc2dc\uac04 \ucc3d\uc5d0 \uc774\ubca4\ud2b8\uac00 \uc5c6\uc2b5\ub2c8\ub2e4.",
        "timeline.bucket_window": "\ubc84\ud0b7 \ucc3d(\ubd84)",
        "topology.total_changes": "\ubcc0\uacbd",
        "topology.volatility_score": "\ubcc0\ub3d9 \uc810\uc218",
        "topology.added_routes": "\ucd94\uac00\ub41c \uacbd\ub85c",
        "topology.changed_routes": "\ubcc0\uacbd\ub41c \uacbd\ub85c",
        "topology.removed_routes": "\uc81c\uac70\ub41c \uacbd\ub85c",
        "topology.recent_changes": "\ucd5c\uc2e0 \ubcc0\uacbd",
        "topology.most_volatile": "\ubcc0\ub3d9\uc774 \ud070 \ubaa9\uc801\uc9c0",
        "topology.no_path_changes": "\uc544\uc9c1 \uacbd\ub85c \ubcc0\uacbd \uae30\ub85d\uc774 \uc5c6\uc2b5\ub2c8\ub2e4.",
        "topology.interface_churn": "\uc778\ud130\ud398\uc774\uc2a4 \ubcc0\ub3d9",
        "topology.destination_count": "\ubaa9\uc801\uc9c0 \uc218",
        "topology.change_type": "\ubcc0\uacbd \uc720\ud615",
    },
    "es": {
        "nav.timeline": "L\u00ednea de tiempo",
        "nav.path_changes": "Cambios de ruta",
        "page.timeline": "L\u00ednea de tiempo de eventos",
        "page.path_changes": "Cambios de ruta",
        "timeline.total_events": "eventos",
        "timeline.critical_events": "Eventos cr\u00edticos",
        "timeline.sources": "Or\u00edgenes",
        "timeline.time_buckets": "bloques",
        "timeline.activity_buckets": "Bloques de actividad",
        "timeline.recent_events": "Eventos recientes",
        "timeline.no_events": "No se registraron eventos en la ventana seleccionada.",
        "timeline.bucket_window": "Ventana del bloque",
        "topology.total_changes": "cambios",
        "topology.volatility_score": "Puntuaci\u00f3n de volatilidad",
        "topology.added_routes": "Rutas agregadas",
        "topology.changed_routes": "Rutas cambiadas",
        "topology.removed_routes": "Rutas eliminadas",
        "topology.recent_changes": "Cambios recientes",
        "topology.most_volatile": "Destinos m\u00e1s vol\u00e1tiles",
        "topology.no_path_changes": "A\u00fan no se registraron cambios de ruta.",
        "topology.interface_churn": "Rotaci\u00f3n de interfaces",
        "topology.destination_count": "destinos",
        "topology.change_type": "Tipo de cambio",
    },
}

for locale, values in TIMELINE_AND_PATH_TRANSLATIONS.items():
    TRANSLATIONS[locale].update(values)


CONFIG_AND_BACKUP_EXPANSION_TRANSLATIONS = {
    "zh-CN": {
        "page.config_history": "\u914d\u7f6e\u5386\u53f2",
        "page.config_review": "\u914d\u7f6e\u5bf9\u6bd4\u5ba1\u6838",
        "page.backup_detail": "\u5907\u4efd\u8be6\u60c5",
        "config.restart_required": "\u9700\u8981\u91cd\u542f",
        "config.affected_modules": "\u5f71\u54cd\u6a21\u5757",
        "config.no_diff": "\u5f53\u524d\u6ca1\u6709\u53ef\u5c55\u793a\u7684\u5dee\u5f02\u3002",
        "backup.detail_title": "\u5907\u4efd\u6982\u8981",
        "backup.contents": "\u5305\u542b\u5185\u5bb9",
        "backup.manifest": "Manifest",
        "backup.no_manifest": "\u6b64\u5907\u4efd\u4e0d\u5305\u542b manifest \u4fe1\u606f\u3002",
        "backup.select_archive_hint": "\u8bf7\u4ece\u5907\u4efd\u5217\u8868\u4e2d\u9009\u62e9\u4e00\u4e2a\u5f52\u6863\u67e5\u770b\u8be6\u60c5\u3002",
        "field.size": "\u5927\u5c0f",
        "field.files": "\u6587\u4ef6\u6570",
        "action.restore": "\u6062\u590d",
        "notice.config_restored": "\u914d\u7f6e\u7248\u672c\u5df2\u6062\u590d\u3002",
    },
    "en": {
        "page.config_history": "Config History",
        "page.config_review": "Config Review",
        "page.backup_detail": "Backup Detail",
        "config.restart_required": "Restart Required",
        "config.affected_modules": "Affected Modules",
        "config.no_diff": "No diff is available for this revision.",
        "backup.detail_title": "Backup Summary",
        "backup.contents": "Included Files",
        "backup.manifest": "Manifest",
        "backup.no_manifest": "This archive does not include manifest metadata.",
        "backup.select_archive_hint": "Select an archive from the backup list to inspect its contents.",
        "field.size": "Size",
        "field.files": "Files",
        "action.restore": "Restore",
        "notice.config_restored": "Configuration revision restored.",
    },
    "ja": {
        "page.config_history": "\u8a2d\u5b9a\u5c65\u6b74",
        "page.config_review": "\u8a2d\u5b9a\u5dee\u5206\u30ec\u30d3\u30e5\u30fc",
        "page.backup_detail": "\u30d0\u30c3\u30af\u30a2\u30c3\u30d7\u8a73\u7d30",
        "config.restart_required": "\u518d\u8d77\u52d5\u304c\u5fc5\u8981",
        "config.affected_modules": "\u5f71\u97ff\u30e2\u30b8\u30e5\u30fc\u30eb",
        "config.no_diff": "\u3053\u306e\u30ea\u30d3\u30b8\u30e7\u30f3\u306b\u8868\u793a\u3067\u304d\u308b\u5dee\u5206\u306f\u3042\u308a\u307e\u305b\u3093\u3002",
        "backup.detail_title": "\u30d0\u30c3\u30af\u30a2\u30c3\u30d7\u6982\u8981",
        "backup.contents": "\u542b\u307e\u308c\u308b\u30d5\u30a1\u30a4\u30eb",
        "backup.manifest": "Manifest",
        "backup.no_manifest": "\u3053\u306e\u30a2\u30fc\u30ab\u30a4\u30d6\u306b manifest \u30e1\u30bf\u30c7\u30fc\u30bf\u306f\u3042\u308a\u307e\u305b\u3093\u3002",
        "backup.select_archive_hint": "\u30d0\u30c3\u30af\u30a2\u30c3\u30d7\u4e00\u89a7\u304b\u3089\u30a2\u30fc\u30ab\u30a4\u30d6\u3092\u9078\u3093\u3067\u8a73\u7d30\u3092\u78ba\u8a8d\u3057\u3066\u304f\u3060\u3055\u3044\u3002",
        "field.size": "\u30b5\u30a4\u30ba",
        "field.files": "\u30d5\u30a1\u30a4\u30eb\u6570",
        "action.restore": "\u5fa9\u5143",
        "notice.config_restored": "\u8a2d\u5b9a\u30ea\u30d3\u30b8\u30e7\u30f3\u3092\u5fa9\u5143\u3057\u307e\u3057\u305f\u3002",
    },
    "ko": {
        "page.config_history": "\uc124\uc815 \uc774\ub825",
        "page.config_review": "\uc124\uc815 \ube44\uad50 \uac80\ud1a0",
        "page.backup_detail": "\ubc31\uc5c5 \uc138\ubd80\uc815\ubcf4",
        "config.restart_required": "\uc7ac\uc2dc\uc791 \ud544\uc694",
        "config.affected_modules": "\uc601\ud5a5 \ubaa8\ub4c8",
        "config.no_diff": "\uc774 \ubc84\uc804\uc5d0 \ub300\ud55c diff \uc815\ubcf4\uac00 \uc5c6\uc2b5\ub2c8\ub2e4.",
        "backup.detail_title": "\ubc31\uc5c5 \uc694\uc57d",
        "backup.contents": "\ud3ec\ud568\ub41c \ud30c\uc77c",
        "backup.manifest": "Manifest",
        "backup.no_manifest": "\uc774 \uc544\uce74\uc774\ube0c\uc5d0\ub294 manifest \uba54\ud0c0\ub370\uc774\ud130\uac00 \uc5c6\uc2b5\ub2c8\ub2e4.",
        "backup.select_archive_hint": "\ubc31\uc5c5 \ubaa9\ub85d\uc5d0\uc11c \uc544\uce74\uc774\ube0c\ub97c \uc120\ud0dd\ud574 \ub0b4\uc6a9\uc744 \ud655\uc778\ud558\uc138\uc694.",
        "field.size": "\ud06c\uae30",
        "field.files": "\ud30c\uc77c \uc218",
        "action.restore": "\ubcf5\uc6d0",
        "notice.config_restored": "\uc124\uc815 \ubc84\uc804\uc774 \ubcf5\uc6d0\ub418\uc5c8\uc2b5\ub2c8\ub2e4.",
    },
    "es": {
        "page.config_history": "Historial de configuraci\u00f3n",
        "page.config_review": "Revisi\u00f3n de configuraci\u00f3n",
        "page.backup_detail": "Detalle del respaldo",
        "config.restart_required": "Reinicio requerido",
        "config.affected_modules": "M\u00f3dulos afectados",
        "config.no_diff": "No hay diff disponible para esta revisi\u00f3n.",
        "backup.detail_title": "Resumen del respaldo",
        "backup.contents": "Archivos incluidos",
        "backup.manifest": "Manifest",
        "backup.no_manifest": "Este archivo no incluye metadatos de manifest.",
        "backup.select_archive_hint": "Selecciona un archivo de la lista de respaldos para inspeccionar su contenido.",
        "field.size": "Tama\u00f1o",
        "field.files": "Archivos",
        "action.restore": "Restaurar",
        "notice.config_restored": "Se restaur\u00f3 la revisi\u00f3n de configuraci\u00f3n.",
    },
}

for locale, values in CONFIG_AND_BACKUP_EXPANSION_TRANSLATIONS.items():
    TRANSLATIONS[locale].update(values)


ALERT_HOOK_TRANSLATIONS = {
    "zh-CN": {
        "alerts.rule_sources": "规则来源",
        "alerts.no_rules": "暂无规则来源信息。",
        "alerts.hook_status": "Hook 状态",
        "alerts.webhook_url": "Webhook 地址",
        "alerts.include_resolved": "包含已恢复告警",
        "alerts.delivery_timeout": "投递超时",
        "alerts.last_delivery": "最近投递",
        "alerts.history": "告警历史",
        "alerts.no_history": "暂无告警历史。",
        "value.enabled": "已启用",
    },
    "en": {
        "alerts.rule_sources": "Rule Sources",
        "alerts.no_rules": "No rule sources are currently active.",
        "alerts.hook_status": "Hook Status",
        "alerts.webhook_url": "Webhook URL",
        "alerts.include_resolved": "Include Resolved Alerts",
        "alerts.delivery_timeout": "Delivery Timeout",
        "alerts.last_delivery": "Last Delivery",
        "alerts.history": "Alert History",
        "alerts.no_history": "No alert history has been recorded yet.",
        "value.enabled": "Enabled",
    },
    "ja": {
        "alerts.rule_sources": "ルールソース",
        "alerts.no_rules": "現在有効なルールソースはありません。",
        "alerts.hook_status": "Hook 状態",
        "alerts.webhook_url": "Webhook URL",
        "alerts.include_resolved": "解消済みアラートを含める",
        "alerts.delivery_timeout": "配信タイムアウト",
        "alerts.last_delivery": "直近の配信",
        "alerts.history": "アラート履歴",
        "alerts.no_history": "まだアラート履歴は記録されていません。",
        "value.enabled": "有効",
    },
    "ko": {
        "alerts.rule_sources": "규칙 소스",
        "alerts.no_rules": "현재 활성 규칙 소스가 없습니다.",
        "alerts.hook_status": "Hook 상태",
        "alerts.webhook_url": "Webhook URL",
        "alerts.include_resolved": "해결된 경보 포함",
        "alerts.delivery_timeout": "전송 제한 시간",
        "alerts.last_delivery": "마지막 전송",
        "alerts.history": "경보 이력",
        "alerts.no_history": "아직 기록된 경보 이력이 없습니다.",
        "value.enabled": "활성화",
    },
    "es": {
        "alerts.rule_sources": "Fuentes de reglas",
        "alerts.no_rules": "No hay fuentes de reglas activas en este momento.",
        "alerts.hook_status": "Estado del hook",
        "alerts.webhook_url": "URL del webhook",
        "alerts.include_resolved": "Incluir alertas resueltas",
        "alerts.delivery_timeout": "Tiempo de espera de entrega",
        "alerts.last_delivery": "Última entrega",
        "alerts.history": "Historial de alertas",
        "alerts.no_history": "Todavía no se registró historial de alertas.",
        "value.enabled": "Habilitado",
    },
}

for locale, values in ALERT_HOOK_TRANSLATIONS.items():
    TRANSLATIONS[locale].update(values)

PLUGIN_SOURCE_REFRESH_TRANSLATIONS = {
    "zh-CN": {
        "nav.plugins": "插件",
        "page.plugin_sources": "插件源",
        "plugins.sources_total": "个源",
        "plugins.empty": "当前没有可用的插件源。",
        "plugins.trusted": "可信源",
        "plugins.sync_state": "同步状态",
        "plugins.plugin_count": "已安装插件",
        "plugins.enabled_count": "已启用",
        "plugins.back": "返回插件列表",
        "plugins.refresh_sources": "刷新插件源",
        "plugins.available_count": "可用插件",
        "plugins.index_url": "索引地址",
        "plugins.last_sync": "最近同步",
        "plugins.description": "说明",
        "plugins.index_path": "索引路径",
        "notice.plugin_sources_refreshed": "插件源已刷新。",
        "value.ready": "就绪",
        "value.idle": "空闲",
        "value.paused": "已暂停",
        "value.enabled": "已启用",
    },
    "en": {
        "nav.plugins": "Plugins",
        "page.plugin_sources": "Plugin Sources",
        "plugins.sources_total": "sources",
        "plugins.empty": "No plugin sources are currently available.",
        "plugins.trusted": "Trusted Source",
        "plugins.sync_state": "Sync State",
        "plugins.plugin_count": "Installed Plugins",
        "plugins.enabled_count": "Enabled",
        "plugins.back": "Back to Plugins",
        "plugins.refresh_sources": "Refresh Sources",
        "plugins.available_count": "Available Plugins",
        "plugins.index_url": "Index URL",
        "plugins.last_sync": "Last Sync",
        "plugins.description": "Description",
        "plugins.index_path": "Index Path",
        "notice.plugin_sources_refreshed": "Plugin sources refreshed.",
        "value.ready": "Ready",
        "value.idle": "Idle",
        "value.paused": "Paused",
        "value.enabled": "Enabled",
    },
    "ja": {
        "nav.plugins": "プラグイン",
        "page.plugin_sources": "プラグインソース",
        "plugins.sources_total": "ソース",
        "plugins.empty": "利用可能なプラグインソースはまだありません。",
        "plugins.trusted": "信頼済みソース",
        "plugins.sync_state": "同期状態",
        "plugins.plugin_count": "インストール済みプラグイン",
        "plugins.enabled_count": "有効",
        "plugins.back": "プラグインに戻る",
        "plugins.refresh_sources": "ソースを更新",
        "plugins.available_count": "利用可能なプラグイン",
        "plugins.index_url": "インデックス URL",
        "plugins.last_sync": "最終同期",
        "plugins.description": "説明",
        "plugins.index_path": "インデックスパス",
        "notice.plugin_sources_refreshed": "プラグインソースを更新しました。",
        "value.ready": "準備完了",
        "value.idle": "待機中",
        "value.paused": "一時停止",
        "value.enabled": "有効",
    },
    "ko": {
        "nav.plugins": "플러그인",
        "page.plugin_sources": "플러그인 소스",
        "plugins.sources_total": "소스",
        "plugins.empty": "현재 사용 가능한 플러그인 소스가 없습니다.",
        "plugins.trusted": "신뢰할 수 있는 소스",
        "plugins.sync_state": "동기화 상태",
        "plugins.plugin_count": "설치된 플러그인",
        "plugins.enabled_count": "활성화됨",
        "plugins.back": "플러그인으로 돌아가기",
        "plugins.refresh_sources": "소스 새로고침",
        "plugins.available_count": "사용 가능한 플러그인",
        "plugins.index_url": "인덱스 URL",
        "plugins.last_sync": "마지막 동기화",
        "plugins.description": "설명",
        "plugins.index_path": "인덱스 경로",
        "notice.plugin_sources_refreshed": "플러그인 소스를 새로고침했습니다.",
        "value.ready": "준비 완료",
        "value.idle": "유휴",
        "value.paused": "일시 중지",
        "value.enabled": "활성화됨",
    },
    "es": {
        "nav.plugins": "Plugins",
        "page.plugin_sources": "Fuentes de plugins",
        "plugins.sources_total": "fuentes",
        "plugins.empty": "No hay fuentes de plugins disponibles actualmente.",
        "plugins.trusted": "Fuente confiable",
        "plugins.sync_state": "Estado de sincronización",
        "plugins.plugin_count": "Plugins instalados",
        "plugins.enabled_count": "Habilitados",
        "plugins.back": "Volver a plugins",
        "plugins.refresh_sources": "Actualizar fuentes",
        "plugins.available_count": "Plugins disponibles",
        "plugins.index_url": "URL del índice",
        "plugins.last_sync": "Última sincronización",
        "plugins.description": "Descripción",
        "plugins.index_path": "Ruta del índice",
        "notice.plugin_sources_refreshed": "Fuentes de plugins actualizadas.",
        "value.ready": "Listo",
        "value.idle": "Inactivo",
        "value.paused": "Pausado",
        "value.enabled": "Habilitado",
    },
}

for locale, values in PLUGIN_SOURCE_REFRESH_TRANSLATIONS.items():
    TRANSLATIONS[locale].update(values)

PLUGIN_SOURCE_CLIENT_TRANSLATIONS = {
    "zh-CN": {
        "plugins.sync_error": "????",
    },
    "en": {
        "plugins.sync_error": "Sync Error",
    },
    "ja": {
        "plugins.sync_error": "?????",
    },
    "ko": {
        "plugins.sync_error": "??? ??",
    },
    "es": {
        "plugins.sync_error": "Error de sincronizaci?n",
    },
}

for locale, values in PLUGIN_SOURCE_CLIENT_TRANSLATIONS.items():
    TRANSLATIONS[locale].update(values)

BRIDGE_DETAIL_AND_SIGNATURE_TRANSLATIONS = {
    "zh-CN": {
        "page.bridge_detail": "????",
        "bridges.detail": "????",
        "bridges.controls": "????",
        "bridges.back": "??????",
        "bridges.dependencies": "??",
        "bridges.permissions": "??",
        "bridges.plugin": "??",
        "bridges.source_security": "????",
        "bridges.action_enable": "????",
        "bridges.action_disable": "????",
        "bridges.action_sync": "????",
        "bridges.action_test_delivery": "????",
        "bridges.open_plugin": "????",
        "bridges.not_found": "???????????",
        "bridges.recent_operations": "??????",
        "bridges.health_checks": "????",
        "bridges.delivery_test": "????",
        "bridges.delivery_test_hint": "??????????????Webhook ?????????????????",
        "bridges.no_recent_operations": "?????????",
        "bridges.check_plugin_enabled": "??????",
        "bridges.check_runtime_ready": "?????",
        "bridges.check_source_trust": "????",
        "bridges.check_endpoint_configured": "????",
        "bridges.check_transport_config": "????",
        "notice.bridge_updated": "????????",
        "plugins.signature_status": "????",
        "plugins.manifest_sha256": "?? SHA256",
        "plugins.signature_algorithm": "????",
        "plugins.public_key": "??",
        "field.result": "??",
        "value.trusted": "???",
        "value.verified": "???",
        "value.invalid": "??",
        "value.missing": "??",
        "value.not_required": "???",
    },
    "en": {
        "page.bridge_detail": "Bridge Detail",
        "bridges.detail": "Bridge Details",
        "bridges.controls": "Bridge Controls",
        "bridges.back": "Back to Bridges",
        "bridges.dependencies": "Dependencies",
        "bridges.permissions": "Permissions",
        "bridges.plugin": "Plugin",
        "bridges.source_security": "Source Security",
        "bridges.action_enable": "Enable Bridge",
        "bridges.action_disable": "Disable Bridge",
        "bridges.action_sync": "Sync Source",
        "bridges.action_test_delivery": "Test Delivery",
        "bridges.open_plugin": "Open Plugin",
        "bridges.not_found": "The requested bridge was not found.",
        "bridges.recent_operations": "Recent Operations",
        "bridges.health_checks": "Health Checks",
        "bridges.delivery_test": "Delivery Test",
        "bridges.delivery_test_hint": "Run a bridge delivery test. Webhook bridges send a live request; other transports currently run a simulated check.",
        "bridges.no_recent_operations": "No recent bridge operations recorded.",
        "bridges.check_plugin_enabled": "Plugin Enabled",
        "bridges.check_runtime_ready": "Runtime Ready",
        "bridges.check_source_trust": "Source Trust",
        "bridges.check_endpoint_configured": "Endpoint Configured",
        "bridges.check_transport_config": "Transport Configuration",
        "notice.bridge_updated": "Bridge action completed.",
        "plugins.signature_status": "Signature Status",
        "plugins.manifest_sha256": "Manifest SHA256",
        "plugins.signature_algorithm": "Signature Algorithm",
        "plugins.public_key": "Public Key",
        "field.result": "Result",
        "value.trusted": "Trusted",
        "value.verified": "Verified",
        "value.invalid": "Invalid",
        "value.missing": "Missing",
        "value.not_required": "Not Required",
    },
    "ja": {
        "page.bridge_detail": "??????",
        "bridges.detail": "??????",
        "bridges.controls": "??????",
        "bridges.back": "?????????",
        "bridges.dependencies": "????",
        "bridges.permissions": "??",
        "bridges.plugin": "?????",
        "bridges.source_security": "???????",
        "bridges.action_enable": "????????",
        "bridges.action_disable": "????????",
        "bridges.action_sync": "??????",
        "bridges.action_test_delivery": "?????",
        "bridges.open_plugin": "????????",
        "bridges.not_found": "?????????????????????",
        "bridges.recent_operations": "???????",
        "bridges.health_checks": "???????",
        "bridges.delivery_test": "?????",
        "bridges.delivery_test_hint": "????????????????????Webhook ???????????????????????????",
        "bridges.no_recent_operations": "????????????????",
        "bridges.check_plugin_enabled": "?????????",
        "bridges.check_runtime_ready": "???????",
        "bridges.check_source_trust": "??????",
        "bridges.check_endpoint_configured": "?????????",
        "bridges.check_transport_config": "????",
        "notice.bridge_updated": "??????????????",
        "plugins.signature_status": "????",
        "plugins.manifest_sha256": "?????? SHA256",
        "plugins.signature_algorithm": "????????",
        "plugins.public_key": "???",
        "field.result": "??",
        "value.trusted": "????",
        "value.verified": "????",
        "value.invalid": "??",
        "value.missing": "??",
        "value.not_required": "??",
    },
    "ko": {
        "page.bridge_detail": "??? ??",
        "bridges.detail": "??? ??",
        "bridges.controls": "??? ??",
        "bridges.back": "??? ????",
        "bridges.dependencies": "???",
        "bridges.permissions": "??",
        "bridges.plugin": "????",
        "bridges.source_security": "?? ??",
        "bridges.action_enable": "??? ???",
        "bridges.action_disable": "??? ????",
        "bridges.action_sync": "?? ???",
        "bridges.action_test_delivery": "?? ???",
        "bridges.open_plugin": "???? ??",
        "bridges.not_found": "??? ???? ?? ? ????.",
        "bridges.recent_operations": "?? ?? ??",
        "bridges.health_checks": "?? ??",
        "bridges.delivery_test": "?? ???",
        "bridges.delivery_test_hint": "?? ???? ?? ??? ??? ?????. Webhook? ?? ??? ???, ?? ??? ????? ??? ?????.",
        "bridges.no_recent_operations": "?? ??? ?? ??? ????.",
        "bridges.check_plugin_enabled": "???? ?? ??",
        "bridges.check_runtime_ready": "??? ??",
        "bridges.check_source_trust": "?? ??",
        "bridges.check_endpoint_configured": "?? ?????",
        "bridges.check_transport_config": "?? ??",
        "notice.bridge_updated": "??? ??? ???????.",
        "plugins.signature_status": "?? ??",
        "plugins.manifest_sha256": "????? SHA256",
        "plugins.signature_algorithm": "?? ????",
        "plugins.public_key": "?? ?",
        "field.result": "??",
        "value.trusted": "???",
        "value.verified": "???",
        "value.invalid": "???? ??",
        "value.missing": "???",
        "value.not_required": "?? ??",
    },
    "es": {
        "page.bridge_detail": "Detalle del puente",
        "bridges.detail": "Detalles del puente",
        "bridges.controls": "Controles del puente",
        "bridges.back": "Volver a puentes",
        "bridges.dependencies": "Dependencias",
        "bridges.permissions": "Permisos",
        "bridges.plugin": "Plugin",
        "bridges.source_security": "Seguridad de la fuente",
        "bridges.action_enable": "Habilitar puente",
        "bridges.action_disable": "Deshabilitar puente",
        "bridges.action_sync": "Sincronizar fuente",
        "bridges.action_test_delivery": "Probar entrega",
        "bridges.open_plugin": "Abrir plugin",
        "bridges.not_found": "No se encontr? el puente solicitado.",
        "bridges.recent_operations": "Operaciones recientes",
        "bridges.health_checks": "Comprobaciones de salud",
        "bridges.delivery_test": "Prueba de entrega",
        "bridges.delivery_test_hint": "Ejecuta una prueba de entrega del puente. Los webhooks env?an una solicitud real; los dem?s transportes usan una comprobaci?n simulada por ahora.",
        "bridges.no_recent_operations": "No hay operaciones recientes del puente.",
        "bridges.check_plugin_enabled": "Plugin habilitado",
        "bridges.check_runtime_ready": "Runtime listo",
        "bridges.check_source_trust": "Confianza de la fuente",
        "bridges.check_endpoint_configured": "Endpoint configurado",
        "bridges.check_transport_config": "Configuraci?n del transporte",
        "notice.bridge_updated": "La acci?n del puente se complet?.",
        "plugins.signature_status": "Estado de firma",
        "plugins.manifest_sha256": "SHA256 del manifiesto",
        "plugins.signature_algorithm": "Algoritmo de firma",
        "plugins.public_key": "Clave p?blica",
        "field.result": "Resultado",
        "value.trusted": "Confiable",
        "value.verified": "Verificado",
        "value.invalid": "Inv?lido",
        "value.missing": "Faltante",
        "value.not_required": "No requerido",
    },
}

for locale, values in BRIDGE_DETAIL_AND_SIGNATURE_TRANSLATIONS.items():
    TRANSLATIONS[locale].update(values)
