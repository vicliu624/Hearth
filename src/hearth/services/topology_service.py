from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from hearth.core.config import HearthSettings
from hearth.services.peer_service import PeerService
from hearth.services.route_service import RouteService
from hearth.storage.db import Database


class TopologyService:
    def __init__(
        self,
        settings: HearthSettings,
        database: Database,
        peer_service: PeerService,
        route_service: RouteService,
    ) -> None:
        self.settings = settings
        self.database = database
        self.peer_service = peer_service
        self.route_service = route_service

    def _now_iso(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _short_id(self, value: str | None) -> str:
        text = str(value or "-")
        return text if len(text) <= 12 else f"{text[:12]}..."

    def _peer_label(self, peer_hash: str | None, peers_by_hash: dict[str, dict[str, Any]]) -> str:
        if not peer_hash:
            return "-"
        peer = peers_by_hash.get(peer_hash)
        if peer:
            return str(peer.get("display_name") or peer.get("peer_hash") or peer_hash)
        return self._short_id(peer_hash)

    def _parse_timestamp(self, value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError:
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)

    def _route_event_type(self, event_type: str | None, payload: dict[str, Any]) -> str:
        change_type = str(payload.get("change_type") or "").strip().lower()
        if change_type in {"added", "changed", "removed"}:
            return change_type
        raw_type = str(event_type or "route.changed")
        return raw_type.split(".")[-1] if "." in raw_type else raw_type

    def _normalize_route_event(self, event: dict[str, Any], current_by_destination: dict[str, dict[str, Any]]) -> dict[str, Any]:
        payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
        current_payload = payload.get("current") if isinstance(payload.get("current"), dict) else {}
        previous_payload = payload.get("previous") if isinstance(payload.get("previous"), dict) else {}
        destination_hash = str(
            payload.get("destination_hash")
            or current_payload.get("destination_hash")
            or previous_payload.get("destination_hash")
            or ""
        )
        change_type = self._route_event_type(str(event.get("event_type") or ""), payload)
        current_route = current_by_destination.get(destination_hash)
        via_interface = (
            current_payload.get("via_interface")
            or payload.get("via_interface")
            or previous_payload.get("via_interface")
            or (current_route or {}).get("via_interface")
        )
        next_hop = (
            current_payload.get("next_hop")
            or payload.get("next_hop")
            or previous_payload.get("next_hop")
            or (current_route or {}).get("next_hop")
        )
        hop_count = current_payload.get("hop_count")
        if hop_count is None:
            hop_count = payload.get("hop_count")
        if hop_count is None:
            hop_count = previous_payload.get("hop_count")
        if hop_count is None and current_route is not None:
            hop_count = current_route.get("hop_count")
        return {
            "id": event.get("id"),
            "event_type": event.get("event_type"),
            "change_type": change_type,
            "created_at": event.get("created_at"),
            "severity": event.get("severity"),
            "source": event.get("source"),
            "message": event.get("message"),
            "payload": payload,
            "destination_hash": destination_hash,
            "destination_label": self._short_id(destination_hash),
            "via_interface": via_interface,
            "next_hop": next_hop,
            "hop_count": hop_count,
            "previous": previous_payload or None,
            "current": current_payload or current_route,
            "current_route": current_route,
        }

    async def _collect(self) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
        peers = await self.peer_service.list_recent(limit=300)
        routes = await self.route_service.list_routes(limit=300)
        interfaces = list(self.database.get_interface_runtimes().values())
        return peers, routes, interfaces

    async def snapshot(self) -> dict[str, Any]:
        peers, routes, interfaces = await self._collect()
        peers_by_hash = {str(peer.get("peer_hash") or ""): peer for peer in peers if peer.get("peer_hash")}
        local_node_id = f"local:{self.settings.system.node_name}"

        nodes: list[dict[str, Any]] = [
            {
                "id": local_node_id,
                "label": self.settings.system.node_name,
                "kind": "local",
                "interface_name": None,
                "hops": 0,
            }
        ]
        seen_node_ids = {local_node_id}
        edges: list[dict[str, Any]] = []

        for peer in peers:
            peer_hash = str(peer.get("peer_hash") or "")
            if not peer_hash:
                continue
            if peer_hash not in seen_node_ids:
                nodes.append(
                    {
                        "id": peer_hash,
                        "label": str(peer.get("display_name") or peer_hash),
                        "kind": "peer",
                        "interface_name": peer.get("interface_name"),
                        "hops": peer.get("hops"),
                    }
                )
                seen_node_ids.add(peer_hash)
            edges.append(
                {
                    "source": local_node_id,
                    "target": peer_hash,
                    "kind": "peer",
                    "via_interface": peer.get("interface_name"),
                    "hops": peer.get("hops"),
                }
            )

        for route in routes:
            destination_hash = str(route.get("destination_hash") or "")
            if not destination_hash:
                continue
            destination_id = f"dest:{destination_hash}"
            if destination_id not in seen_node_ids:
                nodes.append(
                    {
                        "id": destination_id,
                        "label": self._short_id(destination_hash),
                        "kind": "destination",
                        "interface_name": route.get("via_interface"),
                        "hops": route.get("hop_count"),
                    }
                )
                seen_node_ids.add(destination_id)
            next_hop = str(route.get("next_hop") or "")
            source_id = next_hop if next_hop in peers_by_hash else local_node_id
            if next_hop and next_hop in peers_by_hash and next_hop not in seen_node_ids:
                nodes.append(
                    {
                        "id": next_hop,
                        "label": self._peer_label(next_hop, peers_by_hash),
                        "kind": "peer",
                        "interface_name": route.get("via_interface"),
                        "hops": route.get("hop_count"),
                    }
                )
                seen_node_ids.add(next_hop)
            edges.append(
                {
                    "source": source_id,
                    "target": destination_id,
                    "kind": "route",
                    "via_interface": route.get("via_interface"),
                    "hops": route.get("hop_count"),
                    "next_hop": next_hop or None,
                }
            )

        hop_counts = [int(item.get("hop_count") or 0) for item in routes if item.get("hop_count") is not None]
        hop_distribution_map: dict[int, int] = defaultdict(int)
        for hop in hop_counts:
            hop_distribution_map[max(hop, 0)] += 1
        hop_distribution = [
            {"hops": hop, "count": count}
            for hop, count in sorted(hop_distribution_map.items(), key=lambda item: item[0])
        ]

        segment_map: dict[str, dict[str, Any]] = {}
        for interface in interfaces:
            name = str(interface.get("name") or "unknown")
            segment_map[name] = {
                "interface_name": name,
                "status": interface.get("status") or "unknown",
                "health_status": interface.get("health_status") or "unknown",
                "peer_count": 0,
                "route_count": 0,
                "next_hop_count": 0,
            }
        for peer in peers:
            name = str(peer.get("interface_name") or "unknown")
            segment = segment_map.setdefault(
                name,
                {
                    "interface_name": name,
                    "status": "unknown",
                    "health_status": "unknown",
                    "peer_count": 0,
                    "route_count": 0,
                    "next_hop_count": 0,
                },
            )
            segment["peer_count"] += 1
        for route in routes:
            name = str(route.get("via_interface") or "unknown")
            segment = segment_map.setdefault(
                name,
                {
                    "interface_name": name,
                    "status": "unknown",
                    "health_status": "unknown",
                    "peer_count": 0,
                    "route_count": 0,
                    "next_hop_count": 0,
                },
            )
            segment["route_count"] += 1
        for segment in segment_map.values():
            segment_routes = [route for route in routes if str(route.get("via_interface") or "unknown") == segment["interface_name"]]
            segment["next_hop_count"] = len({str(route.get("next_hop") or "") for route in segment_routes if route.get("next_hop")})
            segment["connectivity"] = "connected" if segment["peer_count"] or segment["route_count"] else "isolated"

        average_hops = round(sum(hop_counts) / len(hop_counts), 1) if hop_counts else 0.0
        overview = {
            "node_count": len(nodes),
            "edge_count": len(edges),
            "peer_count": len(peers),
            "route_count": len(routes),
            "interface_count": len(segment_map),
            "active_interfaces": sum(1 for item in interfaces if item.get("status") == "running"),
            "average_hops": average_hops,
        }
        return {
            "generated_at": self._now_iso(),
            "local_node": self.settings.system.node_name,
            "overview": overview,
            "nodes": nodes,
            "edges": edges,
            "segments": sorted(segment_map.values(), key=lambda item: str(item["interface_name"])),
            "hop_distribution": hop_distribution,
        }

    async def network_map(self) -> dict[str, Any]:
        snapshot = await self.snapshot()
        peers, routes, interfaces = await self._collect()
        peers_by_interface: dict[str, list[str]] = defaultdict(list)
        destinations_by_interface: dict[str, list[str]] = defaultdict(list)
        for peer in peers:
            peers_by_interface[str(peer.get("interface_name") or "unknown")].append(
                str(peer.get("display_name") or peer.get("peer_hash") or "peer")
            )
        for route in routes:
            destinations_by_interface[str(route.get("via_interface") or "unknown")].append(
                self._short_id(str(route.get("destination_hash") or ""))
            )

        segments: list[dict[str, Any]] = []
        for segment in snapshot["segments"]:
            name = str(segment.get("interface_name") or "unknown")
            segments.append(
                {
                    **segment,
                    "peer_labels": peers_by_interface.get(name, [])[:6],
                    "destinations": destinations_by_interface.get(name, [])[:6],
                    "member_count": 1 + int(segment.get("peer_count") or 0),
                }
            )

        islands = [
            {
                "name": segment["interface_name"],
                "connectivity": segment["connectivity"],
                "member_count": segment["member_count"],
                "route_count": segment["route_count"],
            }
            for segment in segments
        ]

        bridges = await self.critical_nodes(limit=5)
        return {
            "generated_at": self._now_iso(),
            "segments": segments,
            "islands": islands,
            "bridges": bridges,
            "interface_total": len(interfaces),
        }

    async def route_heatmap(self) -> dict[str, Any]:
        peers, routes, interfaces = await self._collect()
        runtime_by_name = {str(item.get("name") or "unknown"): item for item in interfaces}
        interface_names = sorted({*runtime_by_name.keys(), *[str(route.get("via_interface") or "unknown") for route in routes]})
        total_routes = max(len(routes), 1)
        rows: list[dict[str, Any]] = []
        for name in interface_names:
            interface_routes = [route for route in routes if str(route.get("via_interface") or "unknown") == name]
            hop_values = [int(route.get("hop_count") or 0) for route in interface_routes if route.get("hop_count") is not None]
            route_count = len(interface_routes)
            runtime = runtime_by_name.get(name, {})
            metrics = dict(runtime.get("metrics") or {})
            route_share = round(route_count / total_routes * 100, 1) if routes else 0.0
            traffic_total = int(metrics.get("rx_packets") or 0) + int(metrics.get("tx_packets") or 0)
            intensity = min(100, int(route_share) + min(traffic_total // 10, 60))
            rows.append(
                {
                    "interface_name": name,
                    "status": runtime.get("status") or "unknown",
                    "health_status": runtime.get("health_status") or "unknown",
                    "route_count": route_count,
                    "route_share": route_share,
                    "avg_hops": round(sum(hop_values) / len(hop_values), 1) if hop_values else 0.0,
                    "max_hops": max(hop_values) if hop_values else 0,
                    "rx_packets": int(metrics.get("rx_packets") or 0),
                    "tx_packets": int(metrics.get("tx_packets") or 0),
                    "error_count": int(metrics.get("error_count") or 0),
                    "traffic_total": traffic_total,
                    "intensity": intensity,
                }
            )
        rows.sort(key=lambda item: (int(item["route_count"]), int(item["traffic_total"])), reverse=True)
        return {
            "generated_at": self._now_iso(),
            "total_routes": len(routes),
            "rows": rows,
        }

    async def critical_nodes(self, limit: int = 10) -> list[dict[str, Any]]:
        peers, routes, _ = await self._collect()
        peers_by_hash = {str(peer.get("peer_hash") or ""): peer for peer in peers if peer.get("peer_hash")}
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for route in routes:
            key = str(route.get("next_hop") or route.get("destination_hash") or "unknown")
            grouped[key].append(route)

        total_routes = max(len(routes), 1)
        rows: list[dict[str, Any]] = []
        for node_id, items in grouped.items():
            hop_values = [int(item.get("hop_count") or 0) for item in items if item.get("hop_count") is not None]
            destinations = [self._short_id(str(item.get("destination_hash") or "")) for item in items][:5]
            interfaces = sorted({str(item.get("via_interface") or "unknown") for item in items})
            rows.append(
                {
                    "node_id": node_id,
                    "label": self._peer_label(node_id, peers_by_hash),
                    "classification": "relay" if node_id in peers_by_hash else "destination",
                    "route_count": len(items),
                    "impact_score": round(len(items) / total_routes * 100, 1),
                    "avg_hops": round(sum(hop_values) / len(hop_values), 1) if hop_values else 0.0,
                    "interfaces": interfaces,
                    "sample_destinations": destinations,
                }
            )
        rows.sort(key=lambda item: (float(item["impact_score"]), int(item["route_count"])), reverse=True)
        return rows[:limit]

    async def path_changes(self, recent_limit: int = 80, since_minutes: int = 10080) -> dict[str, Any]:
        current_routes = await self.route_service.list_routes(limit=500)
        current_by_destination = {
            str(item.get("destination_hash") or ""): item for item in current_routes if item.get("destination_hash")
        }
        route_events = [
            event
            for event in self.database.list_events(limit=None)
            if str(event.get("event_type") or "").startswith("route.")
        ]
        if since_minutes > 0:
            cutoff = datetime.now(timezone.utc).timestamp() - (since_minutes * 60)
            route_events = [
                item
                for item in route_events
                if (parsed := self._parse_timestamp(str(item.get("created_at") or ""))) is not None
                and parsed.timestamp() >= cutoff
            ]

        normalized_events = [
            self._normalize_route_event(event, current_by_destination)
            for event in route_events
            if str((event.get("payload") or {}).get("destination_hash") or event.get("message") or "").strip()
            or str(event.get("event_type") or "").startswith("route.")
        ]
        normalized_events.sort(
            key=lambda item: self._parse_timestamp(str(item.get("created_at") or "")) or datetime.min.replace(tzinfo=timezone.utc),
            reverse=True,
        )

        totals = {"added": 0, "changed": 0, "removed": 0}
        destinations: dict[str, dict[str, Any]] = {}
        interfaces: dict[str, dict[str, Any]] = {}

        for item in normalized_events:
            change_type = str(item.get("change_type") or "changed")
            if change_type not in totals:
                totals[change_type] = 0
            totals[change_type] += 1

            destination_hash = str(item.get("destination_hash") or "")
            if destination_hash:
                destination_row = destinations.setdefault(
                    destination_hash,
                    {
                        "destination_hash": destination_hash,
                        "destination_label": self._short_id(destination_hash),
                        "change_count": 0,
                        "added": 0,
                        "changed": 0,
                        "removed": 0,
                        "last_change_at": None,
                        "last_change_type": None,
                        "current_route": current_by_destination.get(destination_hash),
                    },
                )
                destination_row["change_count"] = int(destination_row["change_count"]) + 1
                destination_row[change_type] = int(destination_row.get(change_type) or 0) + 1
                if destination_row["last_change_at"] is None:
                    destination_row["last_change_at"] = item.get("created_at")
                    destination_row["last_change_type"] = change_type

            interface_name = str(item.get("via_interface") or "unknown")
            interface_row = interfaces.setdefault(
                interface_name,
                {
                    "interface_name": interface_name,
                    "change_count": 0,
                    "destinations": set(),
                    "added": 0,
                    "changed": 0,
                    "removed": 0,
                },
            )
            interface_row["change_count"] = int(interface_row["change_count"]) + 1
            interface_row[change_type] = int(interface_row.get(change_type) or 0) + 1
            if destination_hash:
                interface_row["destinations"].add(destination_hash)

        destination_rows: list[dict[str, Any]] = []
        for row in destinations.values():
            volatility_score = min(
                100,
                int(row["added"]) * 15 + int(row["changed"]) * 28 + int(row["removed"]) * 32,
            )
            destination_rows.append(
                {
                    **row,
                    "volatility_score": volatility_score,
                    "current_interface": (row.get("current_route") or {}).get("via_interface"),
                    "current_hops": (row.get("current_route") or {}).get("hop_count"),
                }
            )
        destination_rows.sort(
            key=lambda item: (int(item["volatility_score"]), int(item["change_count"])),
            reverse=True,
        )

        interface_rows = [
            {
                **row,
                "destination_count": len(row["destinations"]),
            }
            for row in interfaces.values()
        ]
        for row in interface_rows:
            row.pop("destinations", None)
        interface_rows.sort(key=lambda item: (int(item["change_count"]), item["interface_name"]), reverse=True)

        route_baseline = max(len(current_routes), len(destination_rows), 1)
        weighted_changes = totals.get("added", 0) + totals.get("changed", 0) * 2 + totals.get("removed", 0) * 2
        volatility_score = min(100, round(weighted_changes / route_baseline * 18 + min(len(destination_rows) * 4, 24)))

        return {
            "generated_at": self._now_iso(),
            "window_minutes": since_minutes,
            "current_route_count": len(current_routes),
            "tracked_destinations": len(destination_rows),
            "total_changes": len(normalized_events),
            "added": totals.get("added", 0),
            "changed": totals.get("changed", 0),
            "removed": totals.get("removed", 0),
            "volatility_score": volatility_score,
            "recent_changes": normalized_events[:recent_limit],
            "destinations": destination_rows[:20],
            "interfaces": interface_rows[:10],
        }

    async def insights(self) -> dict[str, Any]:
        snapshot = await self.snapshot()
        network_map = await self.network_map()
        heatmap = await self.route_heatmap()
        critical_nodes = await self.critical_nodes(limit=5)

        findings: list[dict[str, Any]] = []
        recommendations: list[str] = []
        score = 100

        if snapshot["overview"]["peer_count"] == 0:
            score -= 35
            findings.append(
                {
                    "severity": "critical",
                    "title": "No peers discovered",
                    "message": "The node has not observed any peers yet, so network reachability may be limited.",
                }
            )
            recommendations.append("Verify at least one interface has healthy connectivity and announce traffic.")

        if snapshot["overview"]["route_count"] == 0:
            score -= 30
            findings.append(
                {
                    "severity": "critical",
                    "title": "No learned routes",
                    "message": "The routing table is empty, which means the node is not forwarding beyond direct presence.",
                }
            )
            recommendations.append("Check interface configuration and allow time for path learning to stabilize.")

        if snapshot["overview"]["active_interfaces"] <= 1:
            score -= 12
            findings.append(
                {
                    "severity": "warning",
                    "title": "Single active interface dependency",
                    "message": "Only one interface is currently active, increasing dependence on a single uplink.",
                }
            )
            recommendations.append("Add or recover a second interface to improve resilience.")

        if critical_nodes and float(critical_nodes[0]["impact_score"]) >= 60 and snapshot["overview"]["route_count"] >= 2:
            score -= 10
            findings.append(
                {
                    "severity": "warning",
                    "title": "Route concentration detected",
                    "message": f"Top relay {critical_nodes[0]['label']} carries {critical_nodes[0]['impact_score']}% of known routes.",
                }
            )
            recommendations.append("Diversify upstream relays or add additional reachable neighbors.")

        long_path_rows = [row for row in heatmap["rows"] if float(row.get("avg_hops") or 0) >= 3]
        if long_path_rows:
            score -= 8
            findings.append(
                {
                    "severity": "info",
                    "title": "Longer path lengths observed",
                    "message": "Some interfaces are learning routes with average hop counts of three or more.",
                }
            )

        isolated_segments = [segment for segment in network_map["segments"] if segment.get("connectivity") == "isolated"]
        if isolated_segments:
            score -= min(5 * len(isolated_segments), 15)
            findings.append(
                {
                    "severity": "warning",
                    "title": "Isolated interface segments",
                    "message": f"{len(isolated_segments)} interface segment(s) show no peers or routes.",
                }
            )
            recommendations.append("Inspect isolated interfaces for device, link, or radio-level faults.")

        if not findings:
            findings.append(
                {
                    "severity": "healthy",
                    "title": "Topology looks stable",
                    "message": "Peers, routes, and interfaces are balanced with no obvious structural risks.",
                }
            )
            recommendations.append("Keep monitoring route diversity and interface health over time.")

        score = max(0, min(score, 100))
        return {
            "generated_at": self._now_iso(),
            "score": score,
            "overview": snapshot["overview"],
            "findings": findings,
            "recommendations": recommendations,
        }
