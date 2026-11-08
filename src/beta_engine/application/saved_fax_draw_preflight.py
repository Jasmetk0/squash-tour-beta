"""Read-only point coverage for an authenticated Saved FAX Draw."""

from typing import Literal

from pydantic import BaseModel

from beta_engine.application.saved_fax_knockout_feeders import (
    SavedFaxKnockoutFeederService,
)
from beta_engine.domain.rankings.points import is_valid_ranking_point
from beta_engine.domain.tournaments.fax_reference_bracket_topology import (
    build_fax_reference_bracket_topology,
)
from beta_engine.infrastructure.db.repositories import SimulationPersistenceRepository


class SavedFaxDrawPreflight(BaseModel):
    saved_revision_id: str
    source_plan_fingerprint: str
    draw_fingerprint: str
    ranking_status: Literal["ranked", "unranked"]
    point_table_status: Literal["complete", "incomplete", "not_required"]
    required_point_stages: tuple[str, ...]
    missing_point_stages: tuple[str, ...]
    invalid_point_stages: tuple[str, ...]
    native_execution_status: Literal[
        "ranked_not_supported", "requires_adoption_preview"
    ]


def inspect_saved_fax_draw_preflight(
    repository: SimulationPersistenceRepository,
    *,
    run_id: str,
    branch_id: str,
    event_id: str,
    season: str,
    expected_saved_revision_id: str,
) -> SavedFaxDrawPreflight:
    plan = SavedFaxKnockoutFeederService(repository).prepare(
        run_id=run_id,
        branch_id=branch_id,
        event_id=event_id,
        season=season,
        expected_saved_revision_id=expected_saved_revision_id,
    )
    # The feeder validates that the actual Saved Draw has the exact source
    # geometry. Reuse the audit's canonical stage mapping, including BYE rules.
    event = plan.source.source_event
    ranked = event.ranking_status == "ranked"
    required = (
        build_fax_reference_bracket_topology(event).ranked_point_stages
        if ranked
        else ()
    )
    table = event.ranking_points_table
    missing = tuple(stage for stage in required if stage not in table)
    invalid = tuple(
        stage
        for stage in required
        if stage in table and not is_valid_ranking_point(table[stage])
    )
    status: Literal["complete", "incomplete", "not_required"] = "not_required"
    if ranked:
        status = "incomplete" if missing or invalid else "complete"
    return SavedFaxDrawPreflight(
        saved_revision_id=plan.source_saved_revision_id,
        source_plan_fingerprint=plan.fingerprint,
        draw_fingerprint=plan.source.draw.fingerprint,
        ranking_status="ranked" if ranked else "unranked",
        point_table_status=status,
        required_point_stages=required,
        missing_point_stages=missing,
        invalid_point_stages=invalid,
        native_execution_status="ranked_not_supported"
        if ranked
        else "requires_adoption_preview",
    )
