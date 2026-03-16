from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class PluginManifest:
    name: str
    version: str
    type: str
    entrypoint: str

