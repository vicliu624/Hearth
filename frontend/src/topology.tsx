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
};
export function TopologyPage() {
  const view = useView(),
    graph = view.topology || {};
  const [query, setQuery] = useState(""),
    [selected, setSelected] = useState<N | null>(null),
    [zoom, setZoom] = useState(1),
    [pan, setPan] = useState({ x: 0, y: 0 });
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
      label: name,
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
        label: b.next_hop ? b.next_hop.slice(0, 8) + "…" : "?",
        kind: "next",
        branch: b,
      };
      nodes.push(hop);
      edges.push({ a: n, b: hop, inferred: true });
      const d: N = {
        id: hop.id + ":dest",
        x: 500 + 405 * Math.cos(a),
        y: 390 + 355 * Math.sin(a),
        label: String(b.count),
        count: b.count,
        kind: "dest",
        branch: b,
      };
      nodes.push(d);
      edges.push({ a: hop, b: d, inferred: true });
    });
  });
  const choose = (n: N) => setSelected(n);
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
            {graph.overview?.route_count || 0} {t("topology.destinations")}
          </Tag>
        }
      >
        <div className="topology-tools">
          <Input
            value={query}
            aria-label={t("topology.filter")}
            placeholder={t("topology.filter")}
            onChange={(e) => {
              setQuery(e.target.value);
              setSelected(null);
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
        <p className="topology-legend">
          ● {t("topology.local_node")}　● {t("topology.connection")}　●{" "}
          {t("topology.next_hop")}　● {t("topology.destinations")} ·{" "}
          {t("topology.line_legend")}
        </p>
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
                role="button"
                tabIndex={0}
                aria-label={`${n.kind}: ${n.label}`}
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
                  r={n.kind === "local" ? 40 : 26}
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
                      ? "H"
                      : n.kind === "connection"
                        ? "↔"
                        : "↗"}
                </text>
                {(n.kind === "local" || n.kind === "connection") && (
                  <text
                    textAnchor="middle"
                    y={n.kind === "local" ? 60 : 46}
                    fontSize="12"
                    fill="#504838"
                  >
                    {n.kind === "connection"
                      ? n.label.split("/").slice(1).join("/") || n.label
                      : n.label}
                  </text>
                )}
              </g>
            ))}
          </g>
        </svg>
        <p>{t("topology.interaction")}</p>
        <p>{t("topology.local_explanation")}</p>
        {!branches.length && <p>{t("topology.no_matching_paths")}</p>}
      </Board>
      <Board title={selected?.label || t("topology.select_node")}>
        <p>{t("topology.peer_explanation")}</p>
        {selected?.branch && (
          <>
            <p>{selected.branch.interface}</p>
            <p>
              {t("topology.next_hop")}:{" "}
              <code>{selected.branch.next_hop || "—"}</code>
            </p>
            <p>
              {t("topology.hop_distribution")}:{" "}
              {Object.entries(selected.branch.hops)
                .map(([h, n]) => `${h}: ${n}`)
                .join(" · ")}
            </p>
            <p>{t("topology.sample_limit")}</p>
            <ul className="topology-destinations">
              {selected.branch.destinations.map((d: Data) => (
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
