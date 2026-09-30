import React, { useState } from "react";
import { Button, Input, Tag } from "animal-island-ui";
import { Board, PageHeading, LinkButton, useView, t, Data, href } from "./core";
type N = {
  id: string;
  x: number;
  y: number;
  label: string;
  kind: string;
  branch?: Data;
  count?: number;
  address?: string;
  hops?: number;
};
export function TopologyPage() {
  const view = useView(),
    graph = view.topology || {};
  const [query, setQuery] = useState(
      new URLSearchParams(location.search).get("connection") || "",
    ),
    [selected, setSelected] = useState<N | null>(null),
    [zoom, setZoom] = useState(1),
    [pan, setPan] = useState({ x: 0, y: 0 });
  const [trail, setTrail] = useState<N[]>([]);
  const [childPage, setChildPage] = useState(0);
  const drag = React.useRef<{
    x: number;
    y: number;
    px: number;
    py: number;
  } | null>(null);
  const branches: Data[] = (graph.branches || []).filter((b: Data) =>
    `${b.interface} ${b.next_hop}`.toLowerCase().includes(query.toLowerCase()),
  );
  const interfaces = [...new Set<string>(branches.map((b) => b.interface))];
  const nodes: N[] = [
      {
        id: "local",
        x: 500,
        y: 390,
        label: graph.local_node || "Hearth",
        kind: "local",
      },
    ],
    edges: { a: N; b: N; inferred: boolean }[] = [];
  interfaces.forEach((name, i) => {
    const angle =
      (2 * Math.PI * i) / Math.max(interfaces.length, 1) - Math.PI / 2;
    const n: N = {
      id: name,
      x: 500 + 180 * Math.cos(angle),
      y: 390 + 180 * Math.sin(angle),
      label: t("topology.connection_label", { number: i + 1 }),
      kind: "connection",
    };
    nodes.push(n);
    edges.push({ a: nodes[0], b: n, inferred: false });
    const group = branches.filter((b) => b.interface === name);
    group.forEach((b, j) => {
      const a = angle + (j - (group.length - 1) / 2) * 0.34;
      const hop: N = {
        id: `${name}:${b.next_hop}`,
        x: 500 + 300 * Math.cos(a),
        y: 390 + 300 * Math.sin(a),
        label: t("topology.forward_label"),
        kind: "next",
        branch: b,
      };
      nodes.push(hop);
      edges.push({ a: n, b: hop, inferred: true });
      const d: N = {
        id: hop.id + ":dest",
        x: 500 + 405 * Math.cos(a),
        y: 390 + 355 * Math.sin(a),
        label: `${b.count} ${t("topology.address_unit")}`,
        count: b.count,
        kind: "dest",
        branch: b,
      };
      nodes.push(d);
      edges.push({ a: hop, b: d, inferred: true });
    });
  });
  const focus = trail.at(-1);
  let childCount = 0;
  if (focus) {
    const center = { ...focus, x: 500, y: 390 };
    const currentBranch =
      (graph.branches || []).find(
        (b: Data) =>
          b.interface === focus.branch?.interface &&
          b.next_hop === focus.branch?.next_hop,
      ) || focus.branch;
    let children: N[] = [];
    if (
      focus.kind === "connection" ||
      focus.kind === "next" ||
      focus.kind === "local"
    ) {
      children = edges.filter((e) => e.a.id === focus.id).map((e) => e.b);
    } else if (focus.kind === "dest" && currentBranch) {
      children = currentBranch.destinations.map((d: Data) => ({
        id: `address:${d.hash}`,
        x: 0,
        y: 0,
        label: d.hash.slice(0, 8) + "…",
        kind: "address",
        address: d.hash,
        hops: d.hops,
        branch: currentBranch,
      }));
      center.count = currentBranch.count;
    } else if (focus.kind === "address") {
      children = [
        {
          id: "info:hops",
          x: 0,
          y: 0,
          label: `${focus.hops ?? "?"} ${t("topology.hop_unit")}`,
          kind: "info",
        },
        {
          id: "info:connection",
          x: 0,
          y: 0,
          label:
            focus.branch?.interface.split("/").slice(1).join("/") ||
            focus.branch?.interface ||
            "—",
          kind: "info",
        },
        {
          id: "info:id",
          x: 0,
          y: 0,
          label: t("topology.application_address"),
          kind: "info",
        },
      ];
    }
    childCount = children.length;
    const start =
      Math.min(childPage, Math.max(0, Math.ceil(childCount / 12) - 1)) * 12;
    const visible = children.slice(start, start + 12);
    nodes.splice(0, nodes.length, center);
    edges.splice(0, edges.length);
    visible.forEach((child, i) => {
      const angle = (2 * Math.PI * i) / visible.length - Math.PI / 2;
      const positioned = {
        ...child,
        x: 500 + 300 * Math.cos(angle),
        y: 390 + 270 * Math.sin(angle),
      };
      nodes.push(positioned);
      edges.push({
        a: center,
        b: positioned,
        inferred: focus.kind !== "local",
      });
    });
  }
  const choose = (n: N) => {
    if (n.kind === "info") return;
    setSelected(n);
    if (n.id !== focus?.id) setTrail((history) => [...history, n]);
    setChildPage(0);
    setZoom(1);
    setPan({ x: 0, y: 0 });
  };
  const back = () => {
    const history = trail.slice(0, -1);
    setTrail(history);
    setSelected(history.at(-1) || null);
    setChildPage(0);
    setZoom(1);
    setPan({ x: 0, y: 0 });
  };
  const overview = () => {
    setTrail([]);
    setSelected(null);
    setChildPage(0);
    setQuery("");
    setZoom(1);
    setPan({ x: 0, y: 0 });
  };
  const selectedInterface =
    selected?.branch?.interface ||
    (selected?.kind === "connection" ? selected.id : "");
  const relatedPaths = `/routes?interface=${encodeURIComponent(selectedInterface)}${selected?.branch ? `&via=${encodeURIComponent(selected.branch.next_hop)}` : ""}`;
  return (
    <>
      <PageHeading
        title={t("topology.local_view")}
        subtitle={t("topology.local_explanation")}
      />
      <Board
        title={t("topology.connection_graph")}
        extra={
          <Tag>
            {branches.reduce((total, branch) => total + branch.count, 0)}{" "}
            {t("topology.destinations")}
          </Tag>
        }
      >
        <div className="topology-tools">
          <Button disabled={!trail.length} onClick={back}>
            {t("topology.back_level")}
          </Button>
          <Button onClick={overview}>{t("topology.full_graph")}</Button>
          <Input
            value={query}
            aria-label={t("topology.filter")}
            placeholder={t("topology.filter")}
            onChange={(e) => {
              setQuery(e.target.value);
              setSelected(null);
              setTrail([]);
              setChildPage(0);
            }}
          />
          <Button onClick={() => setZoom((z) => Math.min(3, z * 1.25))}>
            ＋
          </Button>
          <Button onClick={() => setZoom((z) => Math.max(0.4, z / 1.25))}>
            −
          </Button>
          <Button
            onClick={() => {
              setZoom(1);
              setPan({ x: 0, y: 0 });
            }}
          >
            {t("topology.reset")}
          </Button>
        </div>
        <div className="topology-legend">
          {[
            ["#78af9e", "local_node"],
            ["#b9dfef", "connection"],
            ["#e3d0ef", "forward_label"],
            ["#f3dfad", "address_unit"],
          ].map(([color, key]) => (
            <span key={key} style={{ marginRight: 16 }}>
              <span
                aria-hidden="true"
                style={{
                  display: "inline-block",
                  background: color,
                  width: 14,
                  height: 14,
                  borderRadius: "50%",
                  marginRight: 6,
                }}
              />
              {t(`topology.${key}`)}
            </span>
          ))}
        </div>
        <p>{t("topology.guide")}</p>
        {focus && (
          <div className="topology-tools" aria-live="polite">
            <strong>
              {t("topology.centered_on")}: {focus.label}
            </strong>
            <span>
              {childCount} {t("topology.items")}
            </span>
            {childCount > 12 && (
              <>
                <Button
                  disabled={childPage === 0}
                  onClick={() => setChildPage((p) => p - 1)}
                >
                  {t("routes.previous")}
                </Button>
                <span>
                  {childPage + 1} / {Math.ceil(childCount / 12)}
                </span>
                <Button
                  disabled={(childPage + 1) * 12 >= childCount}
                  onClick={() => setChildPage((p) => p + 1)}
                >
                  {t("routes.next")}
                </Button>
              </>
            )}
          </div>
        )}
        {focus?.kind === "address" && (
          <div className="topology-tools">
            <code style={{ overflowWrap: "anywhere" }}>{focus.address}</code>
            <LinkButton to={`/routes/${focus.address}`}>
              {t("routes.open_details")}
            </LinkButton>
          </div>
        )}
        <svg
          className="topology-canvas"
          viewBox="0 0 1000 780"
          role="group"
          aria-label={t("topology.connection_graph")}
          onPointerDown={(e) => {
            if (e.target !== e.currentTarget) return;
            const r = e.currentTarget.getBoundingClientRect();
            drag.current = { x: e.clientX, y: e.clientY, px: pan.x, py: pan.y };
            e.currentTarget.setPointerCapture(e.pointerId);
          }}
          onPointerMove={(e) => {
            if (!drag.current) return;
            const r = e.currentTarget.getBoundingClientRect();
            setPan({
              x:
                drag.current.px +
                ((e.clientX - drag.current.x) * 1000) / r.width,
              y:
                drag.current.py +
                ((e.clientY - drag.current.y) * 780) / r.height,
            });
          }}
          onPointerUp={() => {
            drag.current = null;
          }}
          onPointerCancel={() => {
            drag.current = null;
          }}
        >
          <g
            transform={`translate(${500 + pan.x} ${390 + pan.y}) scale(${zoom}) translate(-500 -390)`}
          >
            {edges.map((e, i) => (
              <line
                key={i}
                x1={e.a.x}
                y1={e.a.y}
                x2={e.b.x}
                y2={e.b.y}
                stroke={e.inferred ? "#aa9c82" : "#78af9e"}
                strokeWidth={e.inferred ? 2 : 3}
                strokeDasharray={e.inferred ? "6 5" : undefined}
                pointerEvents="none"
              />
            ))}
            {nodes.map((n) => (
              <g
                key={n.id}
                transform={`translate(${n.x} ${n.y})`}
                role={n.kind === "info" ? "note" : "button"}
                tabIndex={n.kind === "info" ? -1 : 0}
                aria-label={n.label}
                onClick={() => choose(n)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    choose(n);
                  }
                }}
                className="topology-node"
              >
                <title>{n.label}</title>
                <circle
                  r={n.id === focus?.id ? 48 : n.kind === "local" ? 40 : 26}
                  fill={
                    n.kind === "local"
                      ? "#78af9e"
                      : n.kind === "connection"
                        ? "#b9dfef"
                        : n.kind === "next"
                          ? "#e3d0ef"
                          : "#f3dfad"
                  }
                  stroke={selected?.id === n.id ? "#584a38" : "#fffdf4"}
                  strokeWidth={selected?.id === n.id ? 4 : 3}
                />
                <text textAnchor="middle" dy="5" fontSize="14" fill="#504838">
                  {n.kind === "dest"
                    ? n.count
                    : n.kind === "local"
                      ? t("topology.local_short")
                      : n.kind === "connection"
                        ? n.label
                        : n.kind === "address"
                          ? "◎"
                          : n.kind === "info"
                            ? "i"
                            : t("topology.forward_short")}
                </text>
                {(n.kind === "local" ||
                  n.kind === "connection" ||
                  n.kind === "address" ||
                  n.kind === "info") && (
                  <text
                    textAnchor="middle"
                    y={n.id === focus?.id ? 70 : n.kind === "local" ? 60 : 46}
                    fontSize="12"
                    fill="#504838"
                  >
                    {n.kind === "connection"
                      ? n.id.split("/").slice(1).join("/") || n.id
                      : n.label}
                  </text>
                )}
              </g>
            ))}
          </g>
        </svg>
        <p>
          {focus?.kind === "address"
            ? t("topology.address_properties")
            : t("topology.interaction")}
        </p>
        <p>{t("topology.line_legend")}</p>
        <p>{t("topology.limit_note")}</p>
        {!branches.length && <p>{t("topology.no_matching_paths")}</p>}
      </Board>
      <Board title={selected?.label || t("topology.select_node")}>
        <p>
          {selected
            ? selected.kind === "local"
              ? t("topology.local_detail")
              : selected.kind === "connection"
                ? t("topology.connection_detail")
                : selected.kind === "dest"
                  ? t("topology.count_detail", { count: selected.count || 0 })
                  : t("topology.forward_detail")
            : t("topology.guide")}
        </p>
        {selectedInterface && (
          <div className="topology-tools">
            <Button
              onClick={() => {
                setQuery(selectedInterface);
                setZoom(1);
                setPan({ x: 0, y: 0 });
              }}
            >
              {t("topology.focus_connection")}
            </Button>
            <LinkButton to={relatedPaths}>
              {t("topology.browse_paths")}
            </LinkButton>
            <LinkButton
              to={`/interfaces/${encodeURIComponent(selectedInterface)}`}
            >
              {t("topology.inspect_connection")}
            </LinkButton>
          </div>
        )}
        {selected?.kind === "connection" && <code>{selected.id}</code>}
        {selected?.branch && (
          <>
            <p>{selected.branch.interface}</p>
            <details>
              <summary>{t("topology.raw_id")}</summary>
              {t("topology.next_hop")}:{" "}
              <code>{selected.branch.next_hop || "—"}</code>
            </details>
            <p>
              {t("topology.hop_distribution")}:{" "}
              {Object.entries(selected.branch.hops)
                .map(([h, n]) =>
                  t("topology.hop_sentence", { hops: h, count: String(n) }),
                )
                .join(" · ")}
            </p>
            <p>{t("topology.sample_limit")}</p>
            <ul className="topology-destinations">
              {selected.branch.destinations.slice(0, 30).map((d: Data) => (
                <li key={d.hash}>
                  <a href={href(`/routes/${d.hash}`)}>
                    <code>{d.hash}</code>
                  </a>{" "}
                  · {d.hops ?? "?"} {t("topology.hop_unit")}
                </li>
              ))}
            </ul>
          </>
        )}
        <LinkButton to="/routes">{t("nav.routes")}</LinkButton>
        <p>{t("topology.no_geography")}</p>
      </Board>
    </>
  );
}
