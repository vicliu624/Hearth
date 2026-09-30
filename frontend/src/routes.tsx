import React, { useState } from "react";
import { Button, Input, Select } from "animal-island-ui";
import {
  Board,
  PageHeading,
  LinkButton,
  useView,
  t,
  Data,
  formatTimestamp,
} from "./core";
function Copy({ value }: { value: string }) {
  const [result, setResult] = useState("");
  async function copy() {
    try {
      if (navigator.clipboard && window.isSecureContext)
        await navigator.clipboard.writeText(value);
      else {
        const field = document.createElement("textarea");
        field.value = value;
        field.style.position = "fixed";
        field.style.opacity = "0";
        document.body.appendChild(field);
        field.select();
        const ok = document.execCommand("copy");
        field.remove();
        if (!ok) throw new Error("copy");
      }
      setResult(t("routes.copied"));
    } catch {
      setResult(t("routes.copy_failed"));
    }
  }
  return (
    <>
      <Button onClick={copy}>{t("routes.copy_address")}</Button>
      <span role="status">{result}</span>
    </>
  );
}
export function RoutesPage() {
  const view = useView(),
    route: Data | undefined = view.route;
  const params = new URLSearchParams(location.search);
  const [query, setQuery] = useState(""),
    [connection, setConnection] = useState(params.get("interface") || ""),
    [via, setVia] = useState(params.get("via") || ""),
    [hops, setHops] = useState(""),
    [index, setIndex] = useState(0);
  const all: Data[] = view.routes || [];
  const rows = all.filter(
    (r) =>
      (!connection || r.via_interface === connection) &&
      (!via || r.next_hop === via) &&
      (!hops || String(r.hop_count) === hops) &&
      r.destination_hash.includes(query.trim().toLowerCase()),
  );
  const options = (values: string[]) => [
    { label: t("common.all"), key: "" },
    ...values.map((value) => ({ label: value, key: value })),
  ];
  const back = `/topology?lang=${params.get("lang") || "zh-CN"}`;
  if (route)
    return (
      <>
        <PageHeading
          title={t("routes.address_detail")}
          subtitle={t("routes.address_explanation")}
        />
        <Board title={t("field.destination")}>
          <p>
            <code style={{ overflowWrap: "anywhere" }}>
              {route.destination_hash}
            </code>
          </p>
          <div className="topology-tools">
            <Copy value={route.destination_hash} />
            <LinkButton
              to={`/topology?connection=${encodeURIComponent(route.via_interface || "")}`}
            >
              {t("routes.show_on_graph")}
            </LinkButton>
            <LinkButton
              to={`/routes?interface=${encodeURIComponent(route.via_interface || "")}&via=${encodeURIComponent(route.next_hop || "")}`}
            >
              {t("routes.same_direction")}
            </LinkButton>
            <LinkButton
              to={`/interfaces/${encodeURIComponent(route.via_interface || "")}`}
            >
              {t("topology.inspect_connection")}
            </LinkButton>
          </div>
        </Board>
        <Board title={t("routes.how_to_reach")}>
          <p>
            {t("routes.via_connection")}:{" "}
            <strong>{route.via_interface || "—"}</strong>
          </p>
          <p>
            {t("routes.hop_count_plain", { count: route.hop_count ?? "?" })}
          </p>
          <p>
            {t("routes.record_time")}: {formatTimestamp(route.last_updated_at)}
          </p>
          <p>
            {t("field.expires")}: {formatTimestamp(route.expires_at)}
          </p>
          <details>
            <summary>{t("topology.raw_id")}</summary>
            <code>{route.next_hop || "—"}</code>
          </details>
          <p>{t("routes.no_probe")}</p>
          <Button onClick={() => location.reload()}>
            {t("routes.refresh_record")}
          </Button>
        </Board>
      </>
    );
  return (
    <>
      <PageHeading
        title={t("routes.explore")}
        subtitle={t("routes.explore_hint")}
      />
      <Board
        title={`${rows.length} ${t("topology.address_unit")}`}
        extra={<LinkButton to={back}>{t("routes.show_on_graph")}</LinkButton>}
      >
        <div className="topology-tools">
          <Input
            aria-label={t("routes.search_address")}
            placeholder={t("routes.search_address")}
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setIndex(0);
            }}
          />
          <span>{t("topology.connection")}</span><Select
            aria-label={t("topology.connection")}
            value={connection}
            options={options(
              [
                ...new Set<string>(all.map((r) => r.via_interface || "")),
              ].filter(Boolean),
            )}
            onChange={(v) => {
              setConnection(String(v));
              setVia("");
              setIndex(0);
            }}
          />
          <span>{t("field.hops")}</span><Select
            aria-label={t("field.hops")}
            value={hops}
            options={options(
              [...new Set<string>(all.map((r) => String(r.hop_count)))].sort(
                (a, b) => Number(a) - Number(b),
              ),
            )}
            onChange={(v) => {
              setHops(String(v));
              setIndex(0);
            }}
          />
          <Button
            onClick={() => {
              setQuery("");
              setConnection("");
              setVia("");
              setHops("");
              setIndex(0);
            }}
          >
            {t("routes.clear_filters")}
          </Button>
        </div>
        {via && (
          <p>
            {t("topology.next_hop")}: <code>{via}</code>
          </p>
        )}
        <ul className="route-explorer">
          {rows.slice(index * 30, index * 30 + 30).map((r) => (
            <li key={r.destination_hash}>
              <div>
                <code>{r.destination_hash}</code>
                <p>
                  {r.via_interface} · {r.hop_count ?? "?"}{" "}
                  {t("topology.hop_unit")}
                </p>
              </div>
              <LinkButton to={`/routes/${r.destination_hash}`}>
                {t("routes.open_details")}
              </LinkButton>
              <Copy value={r.destination_hash} />
            </li>
          ))}
        </ul>
        {!rows.length && <p>{t("topology.no_matching_paths")}</p>}
        <div className="topology-tools">
          <Button disabled={!index} onClick={() => setIndex((i) => i - 1)}>
            {t("routes.previous")}
          </Button>
          <span>
            {index + 1} / {Math.max(1, Math.ceil(rows.length / 30))}
          </span>
          <Button
            disabled={(index + 1) * 30 >= rows.length}
            onClick={() => setIndex((i) => i + 1)}
          >
            {t("routes.next")}
          </Button>
        </div>
      </Board>
    </>
  );
}
