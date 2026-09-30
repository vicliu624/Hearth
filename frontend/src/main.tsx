import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  Background,
  BackTop,
  Button,
  Card,
  Collapse,
  Divider,
  Drawer,
  Footer,
  Image,
  Input,
  Radio,
  Skeleton,
  Switch,
  Tabs,
  Tag,
  Title,
  Tooltip,
  notificationOpen,
} from "animal-island-ui";
import type { BackgroundType } from "animal-island-ui";
import {
  BellIcon,
  BookIcon,
  FlowerIcon,
  GlobeIcon,
  HeartIcon,
  HomeIcon,
  KeyIcon,
  LeafIcon,
  MapIcon,
  MenuIcon,
  PaintbrushIcon,
  SearchIcon,
  SettingsIcon,
  SunIcon,
  UserIcon,
  WifiIcon,
} from "naive-icons";
import "animal-island-ui/style";
import "./style.css";
import "./fonts.css";
import {
  Data,
  LiveContext,
  StateTag,
  go,
  href,
  page,
  request,
  scene,
  shell,
  t,
} from "./core";
import {
  ConfigPage,
  HealthPage,
  InterfacesPage,
  LoginPage,
  MetricsPage,
  OverviewPage,
} from "./pages";
import { RoutesPage } from "./routes";
import { TopologyPage } from "./topology";
import { ServerPage } from "./server-page";

const groups = [
  {
    label: t("ui.node_operations"),
    paths: [
      "/",
      "/interfaces",
      "/peers",
      "/routes",
      "/announces",
      "/health",
      "/metrics-dashboard",
    ],
  },
  {
    label: t("ui.network_and_extensions"),
    paths: [
      "/topology",
      "/fleet",
      "/path-changes",
      "/bridges",
      "/services",
      "/plugins",
    ],
  },
  { label: t("ui.administration"), paths: [] },
];
function NavIcon({ path }: { path: string }) {
  const Icon =
    path === "/"
      ? HomeIcon
      : path.includes("interface")
        ? WifiIcon
        : path.includes("health")
          ? HeartIcon
          : path.includes("route") || path.includes("topology")
            ? MapIcon
            : path.includes("peer") || path.includes("fleet")
              ? GlobeIcon
              : path.includes("log") || path.includes("audit")
                ? BookIcon
                : path.includes("user") || path.includes("profile")
                  ? UserIcon
                  : path.includes("token") || path.includes("security")
                    ? KeyIcon
                    : path.includes("alert") || path.includes("announce")
                      ? BellIcon
                      : SettingsIcon;
  return <Icon size={22} color="currentColor" />;
}
function Navigation({ close }: { close?: () => void }) {
  const [query, setQuery] = useState("");
  const known = new Set(groups.flatMap((group) => group.paths));
  return (
    <>
      <a className="brand" href={href("/")}>
        <span>
          <LeafIcon size={34} color="var(--animal-primary-color)" />
        </span>
        <div>
          Hearth<small>RETICULUM CONTROL PANEL</small>
        </div>
      </a>
      <div className="nav-search">
        <Input
          prefix={<SearchIcon size={20} />}
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder={t("ui.find_a_page")}
          aria-label={t("ui.search_navigation")}
          allowClear
        />
      </div>
      <nav aria-label={t("ui.main_navigation")}>
        {groups.map((group, index) => (
          <div className="nav-group" key={group.label}>
            <small>{group.label}</small>
            {shell.nav
              .filter((item) => {
                const path = new URL(item.href, location.origin).pathname;
                return (
                  (index < 2 ? group.paths.includes(path) : !known.has(path)) &&
                  item.label.toLowerCase().includes(query.toLowerCase())
                );
              })
              .map((item) => (
                <a
                  key={item.href}
                  className={`nav-link ${item.active ? "active" : ""}`}
                  aria-current={item.active ? "page" : undefined}
                  href={item.href}
                  onClick={close}
                >
                  <NavIcon
                    path={new URL(item.href, location.origin).pathname}
                  />
                  <span>{item.label}</span>
                  {item.active && <LeafIcon size={17} color="currentColor" />}
                </a>
              ))}
          </div>
        ))}
      </nav>
      <Divider
        icon={<FlowerIcon color="var(--animal-primary-color)" />}
        iconGap={15}
      />
      <div className="sidebar-bottom">
        <Tag variant="dashed" color="app-teal">
          v{shell.version}
        </Tag>
        <small>{t("ui.reticulum_node_management")}</small>
      </div>
    </>
  );
}
function App() {
  const [view, setView] = useState<Data>(page);
  const [summary, setSummary] = useState<Data>(
      page.summary || page.shell_summary || {},
    ),
    [refreshing, setRefreshing] = useState(false);
  const [drawer, setDrawer] = useState("");
  const [theme, setTheme] = useState(
    () => localStorage.getItem("hearth-theme") || "default",
  );
  const [motion, setMotion] = useState(
    () => localStorage.getItem("hearth-motion") !== "off",
  );
  async function refresh() {
    setRefreshing(true);
    try {
      const response = await fetch(location.href, {
        credentials: "same-origin",
        headers: { Accept: "application/vnd.hearth.page+json" },
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const payload = await response.json();
      setView(payload.page);
      setSummary(
        payload.page.summary ||
          payload.page.shell_summary ||
          (await request("/api/node/status")),
      );
    } catch (error) {
      notificationOpen({
        type: "error",
        message: t("ui.node_status_is_unavailable"),
        description: String(error),
      });
    } finally {
      setRefreshing(false);
    }
  }
  useEffect(() => {
    if (shell.responseStatus >= 400) return;
    if (page.notice)
      notificationOpen({
        message: page.notice.message,
        type:
          page.notice.kind === "error"
            ? "error"
            : page.notice.kind === "info"
              ? "info"
              : page.notice.kind === "warning"
                ? "warning"
                : "success",
      });
  }, []);
  const path = location.pathname;
  useEffect(() => {
    if (!(
      path === "/" ||
      path.startsWith("/interfaces") ||
      path === "/metrics-dashboard" ||
      path === "/health" || path === "/topology"
    ))
      return;
    if (shell.responseStatus >= 400) return;
    const timer = window.setInterval(() => {
      if (document.visibilityState === "visible") void refresh();
    }, 15000);
    return () => window.clearInterval(timer);
  }, []);
  const sampleTime = summary.observed_at || shell.sampledAt;
  const sampleStale = summary.observation_stale ?? shell.stale;
  const content =
    shell.responseStatus >= 400 ? <ServerPage/> : path === "/" ? (
      <OverviewPage />
    ) : path.startsWith("/interfaces") ? (
      <InterfacesPage />
    ) : path === "/metrics-dashboard" ? (
      <MetricsPage />
    ) : path === "/routes" || path.startsWith("/routes/") ? (
      <RoutesPage />
    ) : path === "/topology" ? (
      <TopologyPage />
    ) : path === "/health" ? (
      <HealthPage />
    ) : path === "/config" ? (
      <ConfigPage />
    ) : path === "/login" ? (
      <LoginPage />
    ) : (
      <ServerPage />
    );
  return (
    <LiveContext.Provider value={{ summary, view, refresh, refreshing }}>
      <Background
        type={theme as BackgroundType}
        className={`hearth-background ${motion ? "" : "reduced-motion"}`}
      >
        <div className="hearth-layout">
          <a className="skip-link" href="#main-content">
            {t("ui.skip_to_content")}
          </a>
          <aside className="sidebar">
            <Navigation />
          </aside>
          <div className="workspace">
            <header className="topbar">
              <div className="location">
                <Button
                  className="mobile-menu"
                  type="text"
                  icon={<MenuIcon size={24} />}
                  onClick={() => setDrawer("nav")}
                  aria-label={t("ui.open_navigation")}
                />
                <LeafIcon size={20} color="var(--animal-primary-color)" />
                <span>{shell.node}</span>
                <Tag size="small" variant="outlined" color="app-teal">
                  {t("ui.local_node")}
                </Tag>
              </div>
              <div className="actions">
                <Tooltip variant="island" title={t("ui.customize_appearance")}>
                  <Button
                    type="text"
                    icon={<PaintbrushIcon size={23} />}
                    onClick={() => setDrawer("appearance")}
                    aria-label={t("ui.appearance")}
                  />
                </Tooltip>
                <Tooltip variant="island" title={t("ui.user_guide")}>
                  <Button
                    type="text"
                    icon={<BookIcon size={23} />}
                    onClick={() => setDrawer("help")}
                    aria-label={t("ui.help")}
                  />
                </Tooltip>
                <div className="language-picker">
                  {shell.languages
                    .filter((lang) => ["zh-CN", "en"].includes(lang.code))
                    .map((lang) => (
                      <a
                        href={lang.href}
                        key={lang.code}
                        aria-current={lang.active ? "true" : undefined}
                      >
                        {lang.code === "en" ? "EN" : "中文"}
                      </a>
                    ))}
                </div>
                {!shell.authEnabled ? <Tag color="app-orange">{t("diagnostic.authentication_is_disabled")}</Tag> : shell.authenticated ? (
                  <form action={shell.logout} method="post">
                    <Button
                      htmlType="submit"
                      size="small"
                      icon={<UserIcon size={18} />}
                    >
                      {t("ui.sign_out")}
                    </Button>
                  </form>
                ) : (
                  <Button
                    type="primary"
                    size="small"
                    icon={<KeyIcon size={18} />}
                    onClick={() => location.assign(shell.login)}
                  >
                    {t("ui.sign_in")}
                  </Button>
                )}
              </div>
            </header>
            <main id="main-content" className="content">
              <div className="observation-strip">
                <span>
                  <SunIcon size={17} color="var(--animal-warning-color)" />
                  {t("ui.node_status_overview")}
                </span>
                <div>
                  <Tag
                    color={sampleStale ? "app-orange" : "app-teal"}
                    size="small"
                    variant="soft"
                  >
                    {sampleStale
                      ? t("ui.observation_is_stale")
                      : t("ui.collected_in_the_background")}
                  </Tag>
                  {sampleTime && (
                    <time dateTime={sampleTime}>
                      {new Date(sampleTime).toLocaleTimeString(shell.locale)}
                    </time>
                  )}
                  {shell.observation === "mock" && (
                    <Tag color="app-orange" size="small">
                      {t("ui.simulation_mode")}
                    </Tag>
                  )}
                </div>
              </div>
              {refreshing && (
                <div role="status" className="refresh-indicator">
                  <Skeleton heightValue={8} variant="rect" />
                </div>
              )}
              {content}
              <div className="footer-wrap">
                <Divider
                  icon={<LeafIcon color="var(--animal-primary-color)" />}
                  iconGap={28}
                />
                <Footer
                  text={`Hearth ${shell.version} · Reticulum · Animal Island UI`}
                />
              </div>
            </main>
          </div>
        </div>
        <Drawer
          open={drawer === "nav"}
          placement="left"
          width={280}
          title="Hearth"
          pushBackground={false}
          onClose={() => setDrawer("")}
        >
          <Navigation close={() => setDrawer("")} />
        </Drawer>
        <Drawer
          open={drawer === "appearance" || drawer === "help"}
          width={440}
          title={
            drawer === "appearance" ? t("ui.appearance_2") : t("ui.user_guide")
          }
          onClose={() => setDrawer("")}
        >
          {drawer === "appearance" ? (
            <div className="drawer-content">
              <Image
                preview={false}
                src={scene("01-sky-drift")}
                alt=""
                width="100%"
                variant="stamp"
              />
              <Title size="small" color="app-teal">
                {t("ui.choose_a_background")}
              </Title>
              <Radio
                direction="vertical"
                value={theme}
                onChange={(value) => {
                  setTheme(String(value));
                  localStorage.setItem("hearth-theme", String(value));
                }}
                options={[
                  { value: "default", label: t("ui.cream_paper") },
                  { value: "dots-green", label: t("ui.green_dots") },
                  { value: "dots-blue", label: t("ui.blue_dots") },
                  { value: "sprinkles", label: t("ui.confetti") },
                ]}
              />
              <Divider type="squiggle" />
              <div className="setting-row">
                <span>{t("ui.interface_animations")}</span>
                <Switch
                  checked={motion}
                  onChange={(value) => {
                    setMotion(value);
                    localStorage.setItem("hearth-motion", value ? "on" : "off");
                  }}
                  aria-label={t("ui.interface_animations")}
                />
              </div>
              <p>
                {t("ui.these_preferences_affect_only_this_browser_not_your")}
              </p>
            </div>
          ) : (
            <div className="drawer-content">
              <Image
                preview={false}
                src={scene("21-owl-library")}
                alt=""
                width="100%"
                variant="stamp"
              />
              <Tabs
                aria-label={t("ui.help_topics")}
                items={[
                  {
                    key: "start",
                    label: t("ui.getting_started"),
                    children: (
                      <>
                        <Collapse
                          question={t("ui.how_do_i_connect_a_device")}
                          answer={t(
                            "ui.configure_a_local_network_or_tcp_server_interface",
                          )}
                        />
                        <Collapse
                          question={t(
                            "ui.why_do_saved_changes_not_take_effect_immediately",
                          )}
                          answer={t(
                            "ui.saving_updates_the_configuration_draft_use_apply_saved",
                          )}
                        />
                      </>
                    ),
                  },
                  {
                    key: "health",
                    label: t("ui.operation_and_recovery"),
                    children: (
                      <>
                        <Collapse
                          question={t(
                            "ui.will_an_intentionally_stopped_node_restart_automatically",
                          )}
                          answer={t(
                            "ui.no_an_intentional_stop_is_persisted_automatic_recovery",
                          )}
                        />
                        <Collapse
                          question={t("ui.what_happens_if_collection_fails")}
                          answer={t(
                            "ui.the_interface_marks_collection_as_unavailable_or_data",
                          )}
                        />
                      </>
                    ),
                  },
                ]}
              />
            </div>
          )}
        </Drawer>
        <BackTop />
      </Background>
    </LiveContext.Provider>
  );
}
createRoot(document.getElementById("hearth-app")!).render(<App />);
