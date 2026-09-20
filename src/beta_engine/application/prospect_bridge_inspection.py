"""Read-only inspection of RunProspects blocking canonical Week Transition."""

from __future__ import annotations

import hashlib
import json

from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from beta_engine.domain.calendar.season_weeks import season_week_to_calendar_position
from beta_engine.domain.rankings.official import RankingWeek
from beta_engine.infrastructure.db.models import RunBranchModel, RunProspectModel
from beta_engine.infrastructure.db.official_rankings import OfficialRankingCandidateStore


class ProspectBridgeItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    prospect_id: str
    display_name: str
    country_code: str
    age: int
    status: str
    source_type: str
    cohort_policy_version: str
    profile_version: str
    profile_placeholder: bool
    development_placeholder: bool
    potential_placeholder: bool
    trait_placeholder: bool


class ProspectBridgeInspection(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = "prospect_bridge_inspection.v1"
    run_id: str
    branch_id: str
    completed_week: RankingWeek
    target_week: RankingWeek
    season_start_year: int
    calendar_year: int
    year_week: int
    run_scoped_source: bool = True
    bridge_supported: bool = False
    blocking_code: str
    unresolved_contracts: tuple[str, ...]
    prospects: tuple[ProspectBridgeItem, ...]
    inspection_fingerprint: str


def _json(raw: str) -> dict[str, object]:
    value = json.loads(raw)
    return value if isinstance(value, dict) else {}


def _placeholder(payload: dict[str, object], *keys: str) -> bool:
    return any(payload.get(key) is True for key in keys)


def inspect_prospect_bridge(
    session: Session,
    *,
    run_id: str,
    branch_id: str,
) -> ProspectBridgeInspection:
    branch = session.get(RunBranchModel, branch_id)
    if branch is None or branch.run_id != run_id:
        raise ValueError("Prospect Bridge Run/Branch scope is unavailable")

    history = OfficialRankingCandidateStore(session).history(
        run_id=run_id,
        branch_id=branch_id,
    )
    predecessor = history[-1] if history else None
    if predecessor is None:
        raise ValueError("Prospect Bridge predecessor Official Ranking is missing")
    completed_week = predecessor.week
    if completed_week.week == 61:
        raise ValueError(
            "Prospect Bridge inspection is not an ordinary Week Transition at Week 61"
        )
    target_week = RankingWeek(
        season_index=completed_week.season_index,
        week=completed_week.week + 1,
    )
    season_start_year = 2000 + target_week.season_index
    position = season_week_to_calendar_position(
        season_start_year,
        target_week.week,
    )

    rows = tuple(
        session.scalars(
            select(RunProspectModel)
            .where(
                RunProspectModel.run_id == run_id,
                RunProspectModel.season_start_year == season_start_year,
                RunProspectModel.season_week == target_week.week,
                RunProspectModel.calendar_year == position.calendar_year,
                RunProspectModel.year_week == position.year_week,
            )
            .order_by(RunProspectModel.prospect_id)
        )
    )

    prospects: list[ProspectBridgeItem] = []
    for row in rows:
        profile = _json(row.profile_json)
        development = _json(row.development_json)
        potential = _json(row.potential_json)
        traits = _json(row.trait_json)
        prospects.append(
            ProspectBridgeItem(
                prospect_id=row.prospect_id,
                display_name=row.display_name,
                country_code=row.country_code,
                age=row.age,
                status=row.status,
                source_type=row.source_type,
                cohort_policy_version=row.cohort_policy_version,
                profile_version=row.profile_version,
                profile_placeholder=_placeholder(
                    profile,
                    "reserved_for_future_attributes",
                ),
                development_placeholder=_placeholder(
                    development,
                    "reserved_for_future_development",
                ),
                potential_placeholder=_placeholder(
                    potential,
                    "reserved_for_future_potential",
                ),
                trait_placeholder=_placeholder(
                    traits,
                    "reserved_for_future_traits",
                ),
            )
        )

    payload = {
        "schema_version": "prospect_bridge_inspection.v1",
        "run_id": run_id,
        "branch_id": branch_id,
        "completed_week": completed_week.model_dump(mode="json"),
        "target_week": target_week.model_dump(mode="json"),
        "season_start_year": season_start_year,
        "calendar_year": position.calendar_year,
        "year_week": position.year_week,
        "run_scoped_source": True,
        "bridge_supported": False,
        "blocking_code": (
            "prospect_bridge_missing" if prospects else "no_target_week_prospects"
        ),
        "unresolved_contracts": (
            "canonical_sporting_profile",
        ),
        "prospects": [prospect.model_dump(mode="json") for prospect in prospects],
    }
    fingerprint = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return ProspectBridgeInspection(
        **payload,
        inspection_fingerprint=fingerprint,
    )
