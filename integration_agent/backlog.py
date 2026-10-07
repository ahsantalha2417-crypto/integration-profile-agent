"""Prioritize the integration backlog and report pipeline metrics.

Backlog CSV columns:
  partner, docs_url, customer_requests, strategic_fit (1-5), est_effort (1-5)

Priority score rewards customer demand and strategic fit, penalizes effort,
and gets a bonus once the partner's profile shows it is ready to build.
"""
from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from statistics import median

from .schema import IntegrationProfile


@dataclass
class BacklogItem:
    partner: str
    docs_url: str
    customer_requests: int
    strategic_fit: int
    est_effort: int

    def score(self, profile: IntegrationProfile | None = None) -> float:
        s = 2.0 * self.customer_requests + 3.0 * self.strategic_fit - 2.0 * self.est_effort
        if profile is not None and profile.build_ready:
            s += 5.0
        return round(s, 1)


def load_backlog(path: str | Path) -> list[BacklogItem]:
    with open(path, newline="") as f:
        return [
            BacklogItem(
                partner=r["partner"].strip(),
                docs_url=r["docs_url"].strip(),
                customer_requests=int(r["customer_requests"]),
                strategic_fit=int(r["strategic_fit"]),
                est_effort=int(r["est_effort"]),
            )
            for r in csv.DictReader(f)
        ]


def slug(name: str) -> str:
    return "".join(c.lower() if c.isalnum() else "-" for c in name).strip("-")


def load_profiles(directory: str | Path) -> dict[str, IntegrationProfile]:
    profiles = {}
    for p in Path(directory).glob("*.json"):
        prof = IntegrationProfile.model_validate(json.loads(p.read_text()))
        profiles[slug(prof.partner)] = prof
    return profiles


def prioritize(items: list[BacklogItem], profiles: dict[str, IntegrationProfile]) -> list[tuple[BacklogItem, float, IntegrationProfile | None]]:
    ranked = [(i, i.score(profiles.get(slug(i.partner))), profiles.get(slug(i.partner))) for i in items]
    return sorted(ranked, key=lambda t: t[1], reverse=True)


def metrics(items: list[BacklogItem], profiles: dict[str, IntegrationProfile]) -> dict:
    profiled = [profiles[slug(i.partner)] for i in items if slug(i.partner) in profiles]
    days = [p.days_to_access for p in profiled if p.days_to_access is not None]
    return {
        "backlog_size": len(items),
        "profiled": len(profiled),
        "backlog_coverage_pct": round(100 * len(profiled) / len(items), 1) if items else 0.0,
        "build_ready": sum(p.build_ready for p in profiled),
        "median_days_to_access": median(days) if days else None,
        "open_questions": sum(len(p.open_questions) for p in profiled),
    }
