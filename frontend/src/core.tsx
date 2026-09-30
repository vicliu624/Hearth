import React, { createContext, useContext, useState } from "react";
import {
  Button,
  Card,
  Image,
  Modal,
  Tag,
  Title,
  Tooltip,
  notificationOpen,
} from "animal-island-ui";
import type { CardColor, TitleColor } from "animal-island-ui";
import { ArrowRightIcon, LeafIcon, RefreshIcon } from "naive-icons";
import chinese from "../../src/hearth/web/locales/zh-CN.json";
import english from "../../src/hearth/web/locales/en.json";

export type Data = Record<string, any>;
export type Nav = { href: string; label: string; active: boolean };
export type Shell = {
  locale: string;
  title: string;
  nav: Nav[];
  languages: { code: string; href: string; active: boolean }[];
  node: string;
  health: string;
  runtime: string;
  uptime: string;
  authenticated: boolean;
  authEnabled: boolean;
  permissions: string[];
  responseStatus: number;
  login: string;
  logout: string;
  sampledAt: string | null;
  observation: string | null;
  stale: boolean;
  version: string;
};
export const shell: Shell = JSON.parse(
  document.getElementById("hearth-shell")!.textContent!,
);
export const page: Data = JSON.parse(
  document.getElementById("hearth-page")!.textContent!,
);
export const originalContent =
  document.getElementById("server-content")!.innerHTML;
export const zh = shell.locale.startsWith("zh");
export function t(
  key: string,
  parameters: Record<string, string | number> = {},
): string {
  const table: Record<string, string> = zh ? chinese : english;
  const value = table[key] || (english as Record<string, string>)[key] || key;
  return value.replace(/\{(\w+)\}/g, (match, name) =>
    String(parameters[name] ?? match),
  );
}
export function formatTimestamp(value: unknown): string {
  if (!value) return "—";
  const raw = String(value);
  const utc = /Z$|[+-]\d\d:\d\d$/.test(raw) ? raw : `${raw}Z`;
  const date = new Date(utc);
  return Number.isNaN(date.getTime()) ? raw : date.toLocaleString(shell.locale);
}
export function catalogLabel(prefix:string, value:unknown):string {
  const key=`${prefix}.${String(value)}`;
  const label=t(key);
  return label===key?String(value):label;
}
export const scene = (name: string) => `/static/island/scenes/${name}.svg`;
export const href = (path: string) =>
  `${path}${path.includes("?") ? "&" : "?"}lang=${encodeURIComponent(shell.locale)}`;
export const go = (path: string) => location.assign(href(path));
export const LiveContext = createContext<{
  summary: Data;
  view: Data;
  refresh: () => Promise<void>;
  refreshing: boolean;
}>({ summary: {}, view: page, refresh: async () => {}, refreshing: false });
export const useNode = () => useContext(LiveContext);
export const useView = () => useContext(LiveContext).view;
export async function request(path: string, body?: Data) {
  const response = await fetch(path, {
    method: body === undefined ? "GET" : "POST",
    credentials: "same-origin",
    headers: body === undefined ? {} : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const result = await response.json();
  if (
    !response.ok ||
    (result.applied === false && result.valid === false) ||
    result.saved === false
  )
    throw new Error(result.error || result.detail || JSON.stringify(result));
  return result;
}
export function StateTag({ state }: { state: string }) {
  const healthy = ["running", "healthy", "enabled", "verified", "ok"].includes(
    state,
  );
  const bad = ["critical", "error", "crashed", "degraded", "failed"].includes(
    state,
  );
  const label = t(`value.${state}`);
  return (
    <Tag
      color={healthy ? "app-teal" : bad ? "app-red" : "app-orange"}
      variant="soft"
      size="small"
    >
      {label.startsWith("value.") ? state : label}
    </Tag>
  );
}
export function Board({
  title,
  children,
  color = "default",
  pattern,
  extra,
  className = "",
}: {
  title?: React.ReactNode;
  children: React.ReactNode;
  color?: CardColor;
  pattern?: CardColor;
  extra?: React.ReactNode;
  className?: string;
}) {
  return (
    <Card
      color={color}
      pattern={pattern || (color === "default" ? "none" : color)}
      className={`board ${className}`}
    >
      {title && (
        <div className="board-heading">
          <Title size="small" color={color as TitleColor}>
            {title}
          </Title>
          {extra}
        </div>
      )}
      {children}
    </Card>
  );
}
export function Empty({
  title = t("ui.no_data_available"),
  description = t("ui.data_will_appear_here_after_it_is_collected"),
  art = "22-sail-away",
  action,
}: {
  title?: string;
  description?: string;
  art?: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="empty-island">
      <Image src={scene(art)} alt="" variant="stamp" width={168} lazy preview={false} />
      <h3>
        {title.trim() === "-" || !title.trim()
          ? t("ui.no_data_available")
          : title}
      </h3>
      <p>{description}</p>
      {action}
    </div>
  );
}
export function Action({
  label,
  endpoint,
  payload = {},
  danger = false,
  description,
  icon,
  disabled = false,
}: {
  label: string;
  endpoint: string;
  payload?: Data;
  danger?: boolean;
  description?: string;
  icon?: React.ReactNode;
  disabled?: boolean;
}) {
  const [open, setOpen] = useState(false),
    [busy, setBusy] = useState(false);
  const { refresh } = useNode();
  const authorized = shell.permissions?.includes(endpoint.startsWith("/api/config/") ? "configure" : "operate") || false;
  async function execute() {
    setBusy(true);
    try {
      await request(endpoint, payload);
      await refresh();
      setOpen(false);
      notificationOpen({
        message: t("ui.operation_completed"),
        description: label,
        type: "success",
      });
    } catch (error) {
      notificationOpen({
        message: t("ui.operation_failed"),
        description: String(error),
        type: "error",
        duration: 8,
      });
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <Tooltip
        title={
          !authorized
            ? shell.authenticated ? t("auth.forbidden") : t("ui.sign_in_to_operate_the_node")
            : disabled
              ? t("interfaces.control_unsupported")
              : label
        }
        variant="island"
      >
        <Button
          type={danger ? "default" : "primary"}
          danger={danger}
          disabled={disabled || !authorized}
          icon={icon}
          onClick={() => setOpen(true)}
        >
          {label}
        </Button>
      </Tooltip>
      <Modal
        variant="game"
        typewriter={false}
        open={open}
        onClose={() => !busy && setOpen(false)}
        title={label}
        footer={
          <div className="actions">
            <Button onClick={() => setOpen(false)} disabled={busy}>
              {t("ui.cancel")}
            </Button>
            <Button
              type="primary"
              danger={danger}
              loading={busy}
              onClick={execute}
            >
              {t("ui.confirm_operation")}
            </Button>
          </div>
        }
      >
        <div className="confirmation-art">
          <LeafIcon size={44} color="var(--animal-primary-color)" />
        </div>
        <p>
          {description ||
            t("ui.this_operation_changes_the_node_s_runtime_state")}
        </p>
      </Modal>
    </>
  );
}
export function RefreshButton() {
  const { refresh, refreshing } = useNode();
  return (
    <Button
      icon={<RefreshIcon size={18} />}
      loading={refreshing}
      onClick={() => refresh()}
    >
      {t("ui.refresh_view")}
    </Button>
  );
}
export function LinkButton({
  to,
  children,
}: {
  to: string;
  children: React.ReactNode;
}) {
  return (
    <Button
      type="text"
      icon={<ArrowRightIcon size={17} />}
      onClick={() => go(to)}
    >
      {children}
    </Button>
  );
}
export function PageHeading({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle?: string;
  children?: React.ReactNode;
}) {
  return (
    <header className="page-heading">
      <div>
        <div className="eyebrow">HEARTH / {shell.node}</div>
        <h1>{title}</h1>
        {subtitle && <p>{subtitle}</p>}
      </div>
      <div className="actions">{children}</div>
    </header>
  );
}
