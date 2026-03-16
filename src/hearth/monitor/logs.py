from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone

from hearth.storage.db import Database


class LogService:
    def __init__(self, database: Database) -> None:
        self.database = database

    def list_entries(self, limit: int = 100, severity: str | None = None, source: str | None = None) -> list[dict]:
        return self.database.list_events(limit=limit, severity=severity, source=source)

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

    def timeline(
        self,
        *,
        limit: int = 300,
        severity: str | None = None,
        source: str | None = None,
        since_minutes: int = 1440,
        bucket_minutes: int = 120,
    ) -> dict[str, object]:
        events = self.list_entries(limit=limit, severity=severity, source=source)
        if since_minutes > 0:
            cutoff = datetime.now(timezone.utc).astimezone(timezone.utc)
            cutoff = cutoff.timestamp() - (since_minutes * 60)
            filtered_events = []
            for item in events:
                parsed = self._parse_timestamp(str(item.get("created_at") or ""))
                if parsed and parsed.timestamp() >= cutoff:
                    filtered_events.append(item)
            events = filtered_events

        severity_totals: dict[str, int] = defaultdict(int)
        source_totals: dict[str, int] = defaultdict(int)
        bucket_totals: dict[str, dict[str, object]] = {}
        peak_count = 0
        critical_total = 0
        bucket_window = max(bucket_minutes, 1) * 60

        for item in events:
            severity_key = str(item.get("severity") or "info")
            source_key = str(item.get("source") or "system")
            severity_totals[severity_key] += 1
            source_totals[source_key] += 1
            if severity_key == "critical":
                critical_total += 1

            parsed = self._parse_timestamp(str(item.get("created_at") or ""))
            if parsed is None:
                continue
            bucket_start_ts = int(parsed.timestamp() // bucket_window * bucket_window)
            bucket_start = datetime.fromtimestamp(bucket_start_ts, tz=timezone.utc)
            bucket_key = bucket_start.isoformat()
            if bucket_key not in bucket_totals:
                bucket_totals[bucket_key] = {
                    "start_at": bucket_key,
                    "label": bucket_start.strftime("%m-%d %H:%M"),
                    "count": 0,
                    "critical": 0,
                }
            bucket = bucket_totals[bucket_key]
            bucket["count"] = int(bucket["count"]) + 1
            if severity_key == "critical":
                bucket["critical"] = int(bucket["critical"]) + 1
            peak_count = max(peak_count, int(bucket["count"]))

        buckets = [bucket_totals[key] for key in sorted(bucket_totals.keys())]
        sources = [
            {"source": key, "count": value}
            for key, value in sorted(source_totals.items(), key=lambda item: (-item[1], item[0]))
        ]
        severities = [
            {"severity": key, "count": value}
            for key, value in sorted(severity_totals.items(), key=lambda item: (-item[1], item[0]))
        ]
        return {
            "total": len(events),
            "critical_total": critical_total,
            "sources_total": len(sources),
            "bucket_count": len(buckets),
            "bucket_minutes": max(bucket_minutes, 1),
            "peak_count": peak_count,
            "sources": sources,
            "severities": severities,
            "time_buckets": buckets,
            "events": events,
        }
