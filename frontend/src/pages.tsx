import React, { useState } from "react";
import {
  Button,
  Card,
  CodeBlock,
  Collapse,
  Divider,
  Image,
  Input,
  Progress,
  Select,
  Table,
  Tabs,
  Tag,
  Time,
  Title,
  Tooltip,
  Typewriter,
  notificationOpen,
} from "animal-island-ui";
import {
  ArrowDownIcon,
  ArrowUpIcon,
  BellIcon,
  BookIcon,
  CheckIcon,
  ClockIcon,
  CloudIcon,
  FlowerIcon,
  GlobeIcon,
  HeartIcon,
  LeafIcon,
  LinkIcon,
  MapIcon,
  PlayIcon,
  RefreshIcon,
  SaveIcon,
  SearchIcon,
  SettingsIcon,
  StopIcon,
  WifiIcon,
} from "naive-icons";
import {
  Action,
  Board,
  Data,
  Empty,
  LinkButton,
  PageHeading,
  RefreshButton,
  StateTag,
  go,
  href,
  useView,
  request,
  scene,
  shell,
  useNode,
  t,
  formatTimestamp,
  catalogLabel,
} from "./core";

function MetricCards() {
  const { summary } = useNode();
  const rows = [
    {
      label: t("ui.runtime_state"),
      value: t(`value.${summary.runtime_status || "unknown"}`),
      note: summary.node_name,
      Icon: HeartIcon,
      color: "app-teal" as const,
    },
    {
      label: t("ui.running_interfaces"),
      value: `${summary.interface_summary?.online || 0} / ${summary.interface_summary?.total || 0}`,
      note: t("ui.running_configured"),
      Icon: WifiIcon,
      color: "app-blue" as const,
    },
    {
      label: t("ui.observed_peers"),
      value: summary.runtime?.details?.observation_capabilities?.peers === false ? "—" : summary.peer_count || 0,
      note: summary.runtime?.details?.observation_capabilities?.peers === false ? t("observation.peer_stream_unsupported") : t("ui.not_a_count_of_currently_online_peers"),
      Icon: GlobeIcon,
      color: "app-orange" as const,
    },
    {
      label: t("ui.learned_paths"),
      value: summary.route_count || 0,
      note: t("ui.paths_in_the_latest_observation"),
      Icon: MapIcon,
      color: "purple" as const,
    },
  ];
  return (
    <div className="stats-grid">
      {rows.map(({ label, value, note, Icon, color }) => (
        <Card key={label} color={color} pattern={color} className="stat-card">
          <div className="stat-top">
            <Tag color={color} variant="solid" size="small">
              {label}
            </Tag>
            <Icon size={32} color="var(--animal-text-color)" />
          </div>
          <strong>{value}</strong>
          <span>{note}</span>
        </Card>
      ))}
    </div>
  );
}
function Activity({ expanded = false }: { expanded?: boolean }) {
  const page = useView();
  const points: Data[] = page.activity_bars || [];
  const traffic = page.traffic_snapshot || {};
  const hasData = points.some(
    (point) => point.rx_height > 0 || point.tx_height > 0,
  );
  return (
    <Board
      title={t("ui.interface_traffic")}
      extra={
        <Tag color="app-blue" variant="outlined">
          {t("ui.last_24_hours")}
        </Tag>
      }
    >
      <div className="traffic-numbers">
        <div>
          <ArrowDownIcon color="var(--animal-primary-color)" size={21} />
          <span>{t("ui.bytes_received")}</span>
          <strong>{traffic.rx_bytes ?? 0}</strong>
        </div>
        <div>
          <ArrowUpIcon size={21} />
          <span>{t("ui.bytes_sent")}</span>
          <strong>{traffic.tx_bytes ?? 0}</strong>
        </div>
        <div>
          <BellIcon size={21} />
          <span>{t("ui.errors")}</span>
          <strong>{traffic.error_count ?? 0}</strong>
        </div>
      </div>
      {hasData ? (
        <div
          className={`activity-plot ${expanded ? "tall" : ""}`}
          role="img"
          aria-label={t("ui.observed_interface_traffic_history")}
        >
          {points.map((point, i) => (
            <Tooltip
              key={i}
              title={`${point.title}: RX ${point.rx_value}, TX ${point.tx_value}`}
            >
              <div className="bar-pair" tabIndex={0}>
                <span
                  className="rx"
                  style={{ height: `${point.rx_height}%` }}
                />
                <span
                  className="tx"
                  style={{ height: `${point.tx_height}%` }}
                />
                <small>{point.label}</small>
              </div>
            </Tooltip>
          ))}
        </div>
      ) : (
        <div className="waiting-activity">
          <CloudIcon size={42} color="var(--animal-primary-color)" />
          <div>
            <h3>{t("ui.no_traffic_recorded_in_this_time_range")}</h3>
            <p>{t("ui.the_chart_is_derived_from_interface_byte_counters")}</p>
          </div>
        </div>
      )}
      <Divider type="dashed-brown" />
      <div className="board-foot">
        <span>{t("ui.data_is_collected_periodically_in_the_background")}</span>
        <LinkButton to="/metrics-dashboard">{t("ui.view_metrics")}</LinkButton>
      </div>
    </Board>
  );
}
function Events({ rows: supplied }: { rows?: Data[] }) {
  const page = useView();
  const rows: Data[] = supplied || page.logs || page.incidents || [];
  return (
    <Board
      title={t("ui.recent_events")}
      color="app-yellow"
      extra={<BellIcon size={24} color="var(--animal-text-color)" />}
    >
      {rows.length ? (
        <div className="journal">
          {rows.slice(0, 5).map((row, i) => (
            <div className="journal-row" key={row.id || i}>
              <span className="journal-symbol">
                <LeafIcon size={19} />
              </span>
              <div>
                <p>{row.message}</p>
                <small>
                  {row.created_at ? formatTimestamp(row.created_at) : ""}
                </small>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <Empty title={t("ui.no_events_recorded")} art="21-owl-library" />
      )}
      <LinkButton to="/logs">{t("ui.view_all_logs")}</LinkButton>
    </Board>
  );
}
export function OverviewPage() {
  const page = useView();
  const { summary } = useNode();
  const interfaces: Data[] = summary.interfaces || [];
  const running = summary.runtime_status === "running";
  return (
    <>
      <div className="welcome-grid">
        <Card color="app-green" pattern="app-green" className="welcome-card">
          <Title color="app-teal" size="small">
            {t("ui.reticulum_node_management_2")}
          </Title>
          <h1>{t("ui.keep_track_of_your_node_s_connections")}</h1>
          <p>
            <Typewriter
              speed={24}
              autoPlay={!matchMedia("(prefers-reduced-motion: reduce)").matches}
            >
              {t(
                "ui.monitor_runtime_state_manage_network_interfaces_and_apply",
              )}
            </Typewriter>
          </p>
          <div className="actions">
            <Button
              type="primary"
              icon={<WifiIcon size={21} />}
              onClick={() => go("/interfaces")}
            >
              {t("ui.manage_interfaces")}
            </Button>
            <Button
              icon={<MapIcon size={21} />}
              onClick={() => go("/topology")}
            >
              {t("ui.view_network_topology")}
            </Button>
          </div>
          <div className="welcome-details">
            <StateTag state={summary.health_status || "unknown"} />
            <span>{summary.node_name}</span>
            <Tag variant="outlined" color="app-green">
              Reticulum
            </Tag>
          </div>
        </Card>
        <div className="welcome-postcard">
          <Image
            preview={false}
            src={scene("03-forest-grove")}
            alt={t("ui.animal_island_forest_pattern")}
            variant="stamp"
            stampYear="2026"
            width="100%"
          />
          <Time />
        </div>
      </div>
      <MetricCards />
      <div className="dashboard-columns">
        <div>
          <Activity />
          <Board
            title={t("ui.network_interfaces")}
            extra={
              <LinkButton to="/interfaces">
                {t("ui.manage_interfaces")}
              </LinkButton>
            }
          >
            {interfaces.length ? (
              <div className="connection-list">
                {interfaces.map((item) => (
                  <div className="connection" key={item.name}>
                    <span className="connection-icon">
                      <WifiIcon size={28} color="var(--animal-primary-color)" />
                    </span>
                    <div>
                      <h3>{item.name}</h3>
                      <p>
                        {catalogLabel("interface.type", item.type)} · {item.role ? catalogLabel("interface.role", item.role) : t("ui.role_not_assigned")}
                      </p>
                    </div>
                    <StateTag state={item.status} />
                    <Tooltip title={t("ui.open_interface_details")}>
                      <Button
                        type="text"
                        icon={<SettingsIcon size={20} />}
                        onClick={() =>
                          go(`/interfaces/${encodeURIComponent(item.name)}`)
                        }
                        aria-label={item.name}
                      />
                    </Tooltip>
                  </div>
                ))}
              </div>
            ) : (
              <Empty
                title={t("ui.no_network_interfaces_configured")}
                description={t("ui.add_a_tcp_local_network_or_radio_interface")}
                action={
                  <Button
                    type="primary"
                    onClick={() => go("/config")}
                    icon={<LinkIcon size={18} />}
                  >
                    {t("ui.open_configuration")}
                  </Button>
                }
              />
            )}
          </Board>
        </div>
        <div>
          <Events />
          <Board title={t("ui.node_controls")} color="app-blue">
            <div className="caretaker">
              <Image
                preview={false}
                src={scene("14-coffee-break")}
                alt=""
                width="100%"
                variant="bordered"
              />
              <p>
                {t("ui.stopping_the_node_persists_a_stopped_desired_state")}
              </p>
            </div>
            <div className="actions">
              {running ? (
                <Action
                  label={t("ui.stop_node")}
                  endpoint="/api/node/stop"
                  danger
                  icon={<StopIcon size={18} />}
                />
              ) : (
                <Action
                  label={t("ui.start_node")}
                  endpoint="/api/node/start"
                  icon={<PlayIcon size={18} />}
                />
              )}
              <Action
                label={t("ui.restart_node")}
                endpoint="/api/node/restart"
                danger
                icon={<RefreshIcon size={18} />}
              />
            </div>
            <Divider type="squiggle" />
            <small>
              {t("ui.current_uptime")} ·{" "}
              {Math.floor((summary.uptime_seconds || 0) / 60)} min
            </small>
          </Board>
        </div>
      </div>
    </>
  );
}
export function InterfacesPage() {
  const page = useView();
  const { summary } = useNode();
  const [query, setQuery] = useState(""),
    [filter, setFilter] = useState("all");
  const items: Data[] = summary.interfaces || page.interfaces || [];
  const rows = items.filter(
    (row) =>
      row.name.toLowerCase().includes(query.toLowerCase()) &&
      (filter === "all" || row.status === filter),
  );
  const selected = page.interface
    ? items.find((item) => item.name === page.interface.name) || page.interface
    : undefined;
  return (
    <>
      <PageHeading
        title={selected ? selected.name : t("ui.network_interfaces")}
        subtitle={t("ui.inspect_interface_state_start_or_stop_an_interface")}
      >
        <RefreshButton />
        <Button
          type="primary"
          icon={<SettingsIcon size={20} />}
          onClick={() => go("/config")}
        >
          {t("ui.edit_configuration")}
        </Button>
      </PageHeading>
      <MetricCards />
      <Board
        title={t("ui.interfaces")}
        extra={
          <Tag color="app-teal">
            {items.length} {t("ui.interfaces_2")}
          </Tag>
        }
      >
        <div className="filter-bar">
          <Input
            prefix={<SearchIcon size={21} />}
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder={t("ui.search_by_interface_name")}
            aria-label={t("ui.search_interfaces")}
            allowClear
          />
          <Select
            options={[
              { key: "all", label: t("ui.all_states") },
              { key: "running", label: t("ui.running") },
              { key: "stopped", label: t("ui.stopped") },
            ]}
            value={filter}
            onChange={setFilter}
            aria-label={t("ui.filter_by_state")}
          />
        </div>
        <Table
          rowKey="name"
          dataSource={selected ? [selected] : rows}
          scroll={{ x: "max-content" }}
          pagination={rows.length > 10 ? { pageSize: 10 } : false}
          emptyText={<Empty title={t("ui.no_matching_interfaces")} />}
          columns={[
            {
              title: t("ui.interface"),
              dataIndex: "name",
              render: (value, row) => (
                <Button
                  type="link"
                  onClick={() =>
                    go(`/interfaces/${encodeURIComponent(String(value))}`)
                  }
                  icon={<WifiIcon size={19} />}
                >
                  {String(value)}
                </Button>
              ),
            },
            {
              title: t("ui.type"),
              dataIndex: "type",
              render: (value) => (
                <Tag color="app-blue" variant="outlined">
                  {catalogLabel("interface.type", value)}
                </Tag>
              ),
            },
            {
              title: t("ui.state"),
              dataIndex: "status",
              render: (value) => <StateTag state={String(value)} />,
            },
            {
              title: t("ui.health"),
              dataIndex: "health_status",
              render: (value) => <StateTag state={String(value)} />,
            },
            {
              title: t("ui.received_sent_bytes"),
              render: (_, row) =>
                `${(row.metrics as Data)?.rx_bytes ?? "—"} / ${(row.metrics as Data)?.tx_bytes ?? "—"}`,
            },
            {
              title: t("ui.actions"),
              render: (_, row) => (
                <div className="actions compact">
                  <Action
                    label={
                      row.status === "running" ? t("ui.stop") : t("ui.start")
                    }
                    endpoint={`/api/interfaces/${encodeURIComponent(String(row.name))}/${row.status === "running" ? "stop" : "start"}`}
                    disabled={row.control_supported === false}
                    danger={row.status === "running"}
                    description={t(
                      "ui.controlling_a_real_interface_applies_configuration_by_restarting",
                    )}
                    icon={
                      row.status === "running" ? (
                        <StopIcon size={16} />
                      ) : (
                        <PlayIcon size={16} />
                      )
                    }
                  />
                </div>
              ),
            },
          ]}
        />
      </Board>
      <Collapse
        question={t("ui.why_is_an_interface_shown_as_unknown")}
        answer={t("ui.unknown_means_the_interface_s_runtime_state_has")}
      />
      {selected && (
        <Board title={t("ui.interface_observation")}>
          <CodeBlock code={JSON.stringify(selected, null, 2)} />
        </Board>
      )}
    </>
  );
}
export function MetricsPage() {
  const page = useView();
  const { summary } = useNode();
  const items: Data[] = summary.interfaces || [];
  return (
    <>
      <PageHeading
        title={t("ui.runtime_metrics")}
        subtitle={t(
          "ui.inspect_interface_traffic_counters_and_the_latest_runtime",
        )}
      >
        <RefreshButton />
        <Button icon={<BookIcon size={20} />} onClick={() => go("/metrics")}>
          {t("ui.prometheus_metrics")}
        </Button>
      </PageHeading>
      <MetricCards />
      <Tabs
        aria-label={t("ui.metric_views")}
        items={[
          {
            key: "traffic",
            label: t("ui.traffic"),
            children: <Activity expanded />,
          },
          {
            key: "interfaces",
            label: t("ui.interface_metrics"),
            children: (
              <Board title={t("ui.interface_metrics")}>
                <Table
                  rowKey="name"
                  dataSource={items}
                  emptyText={<Empty />}
                  columns={[
                    { title: t("ui.interface"), dataIndex: "name" },
                    {
                      title: t("ui.state"),
                      dataIndex: "status",
                      render: (value) => <StateTag state={String(value)} />,
                    },
                    {
                      title: "RX",
                      render: (_, row) =>
                        String((row.metrics as Data)?.rx_bytes ?? "—"),
                    },
                    {
                      title: "TX",
                      render: (_, row) =>
                        String((row.metrics as Data)?.tx_bytes ?? "—"),
                    },
                    {
                      title: t("ui.errors"),
                      render: (_, row) =>
                        String((row.metrics as Data)?.error_count || 0),
                    },
                  ]}
                />
              </Board>
            ),
          },
          {
            key: "raw",
            label: t("ui.raw_observation"),
            children: (
              <Board title={t("ui.raw_metrics")}>
                <CodeBlock
                  code={JSON.stringify(summary.metrics || {}, null, 2)}
                />
              </Board>
            ),
          },
        ]}
      />
      <div className="two-columns">
        <Board title={t("ui.share_of_interfaces_running")} color="app-green">
          <p>{t("ui.the_number_of_running_interfaces_divided_by_the")}</p>
          {items.length ? (
            <Progress
              variant="forest-grove"
              percent={
                items.length
                  ? Math.round(
                      (items.filter((item) => item.status === "running")
                        .length /
                        items.length) *
                        100,
                    )
                  : 0
              }
              size="large"
              aria-label={t("ui.share_of_interfaces_running")}
            />
          ) : (
            <p>{t("ui.no_network_interfaces_configured")}</p>
          )}
        </Board>
        <Board title={t("ui.about_the_data")} color="app-yellow">
          <p>
            {t(
              "ui.pages_read_background_observations_collection_failures_are_marked",
            )}
          </p>
        </Board>
      </div>
    </>
  );
}
export function HealthPage() {
  const page = useView();
  const { summary } = useNode();
  const score =
    summary.desired_state === "stopped" && summary.runtime_status === "stopped"
      ? null
      : Number(page.health_score ?? 0);
  return (
    <>
      <PageHeading
        title={t("ui.node_health")}
        subtitle={t(
          "ui.review_current_issues_interface_state_and_recovery_history",
        )}
      >
        <RefreshButton />
      </PageHeading>
      <div className="health-columns">
        <Board
          title={t("ui.current_health")}
          color="app-green"
          pattern="app-green"
        >
          <div className="health-score">
            <HeartIcon size={66} color="var(--animal-primary-color)" />
            <strong>
              {score ?? "—"}
              {score !== null && <small>/ 100</small>}
            </strong>
            <StateTag state={summary.health_status || "unknown"} />
          </div>
          {score !== null && (
            <Progress
              percent={score}
              variant="forest-grove"
              size="large"
              aria-label={t("ui.health_score")}
            />
          )}
          <Divider icon={<LeafIcon color="var(--animal-primary-color)" />} />
          <p>
            {summary.desired_state === "stopped"
              ? t(
                  "ui.the_node_is_intentionally_stopped_automatic_recovery_will",
                )
              : (summary.issues || []).join(" · ") ||
                t("ui.no_issues_need_attention")}
          </p>
        </Board>
        <Card color="app-blue" pattern="app-blue" className="scene-note">
          <Image
            preview={false}
            src={scene("30-starry-camp")}
            alt=""
            width="100%"
            variant="stamp"
          />
          <h3>{t("ui.automatic_recovery")}</h3>
          <p>{t("ui.when_the_desired_state_is_running_recovery_attempts")}</p>
          <Button
            onClick={() => go("/maintenance")}
            icon={<SettingsIcon size={19} />}
          >
            {t("ui.maintenance_settings")}
          </Button>
        </Card>
      </div>
      <Events rows={page.incidents || []} />
      <Collapse
        question={t("ui.inspect_runtime_diagnostics")}
        answer={
          <CodeBlock code={JSON.stringify(summary.runtime || {}, null, 2)} />
        }
      />
    </>
  );
}
export function ConfigPage() {
  const page = useView();
  const [raw, setRaw] = useState(String(page.raw || "")),
    [result, setResult] = useState<Data | null>(null),
    [busy, setBusy] = useState("");
  async function run(action: string) {
    setBusy(action);
    try {
      const data = await request(
        `/api/config/${action}`,
        action === "apply" ? {} : { raw },
      );
      setResult(data);
      notificationOpen({
        message:
          data.valid === false
            ? t("ui.configuration_validation_failed")
            : t("ui.operation_completed"),
        type: data.valid === false ? "warning" : "success",
        description:
          action === "save-raw"
            ? t("ui.configuration_draft_saved_changes_are_not_active_yet")
            : undefined,
      });
    } catch (error) {
      notificationOpen({
        message: t("ui.operation_failed"),
        description: String(error),
        type: "error",
      });
    } finally {
      setBusy("");
    }
  }
  return (
    <>
      <PageHeading
        title={t("ui.node_configuration")}
        subtitle={t("ui.validate_and_save_the_draft_then_apply_it")}
      >
        <Button
          icon={<BookIcon size={19} />}
          onClick={() => go("/config/history")}
        >
          {t("ui.configuration_history")}
        </Button>
      </PageHeading>
      <Card color="app-yellow" pattern="app-yellow" className="config-steps">
        {[t("ui.validate"), t("ui.save_draft"), t("ui.apply_and_verify")].map(
          (label, i) => (
            <div key={label}>
              <Tag color="app-orange" size="large">
                0{i + 1}
              </Tag>
              <strong>{label}</strong>
            </div>
          ),
        )}
      </Card>
      <Tabs
        aria-label={t("ui.configuration_editor")}
        items={[
          {
            key: "edit",
            label: t("ui.edit_configuration"),
            children: (
              <Board title={t("ui.configuration_content")}>
                <div className="config-path">{page.config_path}</div>
                <textarea
                  className="config-editor"
                  value={raw}
                  onChange={(event) => setRaw(event.target.value)}
                  aria-label={t("ui.toml_configuration")}
                  spellCheck={false}
                />
                <div className="actions config-actions">
                  <Button
                    icon={<CheckIcon size={20} />}
                    loading={busy === "validate-raw"}
                    onClick={() => run("validate-raw")}
                  >
                    {t("ui.validate_2")}
                  </Button>
                  <Button
                    icon={<SaveIcon size={20} />}
                    loading={busy === "save-raw"}
                    onClick={() => run("save-raw")}
                  >
                    {t("ui.save_draft")}
                  </Button>
                  <Action
                    label={t("ui.apply_saved_configuration")}
                    endpoint="/api/config/apply"
                    icon={<PlayIcon size={20} />}
                    description={t(
                      "ui.applying_reinitializes_the_affected_services_and_may_restart",
                    )}
                  />
                </div>
              </Board>
            ),
          },
          {
            key: "preview",
            label: t("ui.read_only_preview"),
            children: (
              <Board title={t("ui.configuration_preview")}>
                <CodeBlock code={raw} />
              </Board>
            ),
          },
          {
            key: "revisions",
            label: t("ui.recently_saved_revisions"),
            children: (
              <Board title={t("ui.configuration_history")}>
                <Table
                  rowKey="id"
                  dataSource={page.revisions || []}
                  emptyText={<Empty />}
                  columns={[
                    { title: "#", dataIndex: "id" },
                    { title: t("ui.source"), dataIndex: "source" },
                    { title: t("ui.summary"), dataIndex: "summary" },
                    {
                      title: t("ui.time"),
                      dataIndex: "created_at",
                      render: (value) => formatTimestamp(value),
                    },
                    {
                      title: t("ui.view"),
                      render: (_, row) => (
                        <Button
                          type="link"
                          onClick={() => go(`/config/review/${row.id}`)}
                        >
                          {t("ui.review")}
                        </Button>
                      ),
                    },
                  ]}
                />
              </Board>
            ),
          },
        ]}
      />
      {result && (
        <Collapse
          defaultExpanded
          question={t("ui.operation_result")}
          answer={<CodeBlock code={JSON.stringify(result, null, 2)} />}
        />
      )}
    </>
  );
}
export function LoginPage() {
  const page = useView();
  const [token, setToken] = useState("");
  return (
    <div className="login-layout">
      <div className="login-illustration">
        <Image
          preview={false}
          src={scene("22-sail-away")}
          alt=""
          variant="stamp"
          width="100%"
        />
        <Title color="app-teal">{t("ui.sign_in_to_manage_your_node")}</Title>
      </div>
      <Board
        title={t("ui.admin_sign_in")}
        color="app-yellow"
        pattern="app-yellow"
      >
        <div className="login-intro">
          <LeafIcon size={46} color="var(--animal-primary-color)" />
          <h1>{t("ui.sign_in_to_hearth")}</h1>
          <p>{t("ui.sign_in_with_your_admin_token_to_manage")}</p>
        </div>
        {page.notice && <p role="alert">{page.notice.message}</p>}
        <form action={href("/login")} method="post">
          <input
            type="hidden"
            name="next"
            value={new URLSearchParams(location.search).get("next") || "/"}
          />
          <label className="field-label" htmlFor="admin-token">
            {t("ui.admin_token")}
          </label>
          <Input
            id="admin-token"
            name="token"
            type="password"
            value={token}
            onChange={(event) => setToken(event.target.value)}
            placeholder={t("ui.enter_your_admin_token")}
            autoComplete="current-password"
            shadow
          />
          <div className="login-submit">
            <Button
              type="primary"
              block
              htmlType="submit"
              icon={<LeafIcon size={20} />}
            >
              {t("ui.sign_in")}
            </Button>
          </div>
        </form>
        <Divider type="squiggle" />
        <small>{t("ui.your_token_is_sent_only_to_this_hearth")}</small>
      </Board>
    </div>
  );
}
