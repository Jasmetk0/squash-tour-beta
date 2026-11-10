"""Read the actual first Tour Entry evidence for an authenticated Saved FAX Draw."""

from typing import Literal

from pydantic import Field

from beta_engine.application.saved_fax_knockout_feeders import (
    SavedFaxKnockoutFeederService,
)
from beta_engine.domain.players.tour_entry import PlayerTourEntryTrigger
from beta_engine.domain.rankings.official import FrozenInput
from beta_engine.domain.tournaments.definitive_wild_card_assignment import (
    DefinitiveWildCardAssignmentAuthority,
)
from beta_engine.domain.tournaments.wild_card_authority import (
    TournamentWildCardAuthority,
)
from beta_engine.infrastructure.db.definitive_wild_card_assignments import (
    load_saved_definitive_wild_card_assignments,
)
from beta_engine.infrastructure.db.player_tour_entry_triggers import (
    load_saved_tour_entry_triggers,
)
from beta_engine.infrastructure.db.repositories import SimulationPersistenceRepository
from beta_engine.infrastructure.db.simulation_slot_state import (
    load_saved_simulation_slot_component,
)
from beta_engine.infrastructure.db.tournament_application_submissions import (
    load_saved_application_submissions,
)

DrawRole = Literal["direct_main", "qualification", "wild_card"]


class SavedFaxEntrantEvidence(FrozenInput):
    player_id: str
    draw_role: DrawRole
    first_entry: PlayerTourEntryTrigger | None


class SavedFaxEntryEvidence(FrozenInput):
    saved_revision_id: str
    source_plan_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    event_id: str
    entrants: tuple[SavedFaxEntrantEvidence, ...]


def inspect_saved_fax_entry_evidence(
    repository: SimulationPersistenceRepository,
    *,
    run_id: str,
    branch_id: str,
    event_id: str,
    season: str,
    expected_saved_revision_id: str,
) -> SavedFaxEntryEvidence:
    """Bind evidence to one Saved owner; don't interpret it on a new clock."""
    scope = {"run_id": run_id, "branch_id": branch_id}
    plan, revision = SavedFaxKnockoutFeederService(repository).prepare_with_revision(
        **scope,
        event_id=event_id,
        season=season,
        expected_saved_revision_id=expected_saved_revision_id,
    )
    payload = revision.payload
    draw = plan.source.draw_input
    groups: tuple[tuple[DrawRole, tuple[str, ...]], ...] = (
        ("direct_main", draw.direct_main_player_ids),
        ("qualification", draw.qualification_player_ids),
        ("wild_card", draw.wild_card_player_ids),
    )
    roster = {player_id for _, players in groups for player_id in players}
    triggers = {
        t.player_id: t
        for t in (load_saved_tour_entry_triggers(payload, **scope) or ())
        if t.player_id in roster
    }
    submissions = {
        s.application_id: s
        for s in (load_saved_application_submissions(payload, **scope) or ())
        if s.player_id in roster
    }
    assignments = {
        a.source_evidence_id: a
        for a in (load_saved_definitive_wild_card_assignments(payload, **scope) or ())
        if a.player_id in roster
    }
    players_with_evidence = {
        e.player_id for e in (*submissions.values(), *assignments.values())
    }
    wild_cards = None
    entrants = []
    for role, players in groups:
        for player_id in players:
            trigger = triggers.get(player_id)
            if trigger is None:
                if player_id in players_with_evidence:
                    raise ValueError("Saved Entry authority has no first-Entry trigger")
            elif trigger.trigger_kind == "valid_tournament_application":
                submission = submissions.get(trigger.source_evidence_id)
                if submission is None or submission.to_tour_entry_trigger() != trigger:
                    raise ValueError(
                        "Saved first-Entry trigger differs from its valid application"
                    )
            else:
                assignment = assignments.get(trigger.source_evidence_id)
                if assignment is None or assignment.to_tour_entry_trigger() != trigger:
                    raise ValueError(
                        "Saved first-Entry trigger differs from its definitive Wild Card"
                    )
                if wild_cards is None:
                    component = (
                        load_saved_simulation_slot_component(payload, **scope) or {}
                    )
                    wild_cards = {
                        row["authority_fingerprint"]: row["payload_json"]
                        for row in component.get("wild_card_authorities", ())
                    }
                raw = wild_cards.get(assignment.source_wild_card_authority_fingerprint)
                if raw is None:
                    raise ValueError(
                        "Saved definitive Wild Card lacks its exact resolution"
                    )
                resolved = DefinitiveWildCardAssignmentAuthority.from_resolution(
                    authority=TournamentWildCardAuthority.model_validate_json(raw),
                    wildcard_index=assignment.wildcard_index,
                    assignment_week=assignment.assignment_week,
                    decision_slot_ordinal=assignment.decision_slot_ordinal,
                    provenance=assignment.provenance,
                )
                if resolved != assignment:
                    raise ValueError(
                        "Saved definitive Wild Card differs from its resolution"
                    )
            entrants.append(
                SavedFaxEntrantEvidence(
                    player_id=player_id,
                    draw_role=role,
                    first_entry=trigger,
                )
            )
    return SavedFaxEntryEvidence(
        saved_revision_id=revision.revision_id,
        source_plan_fingerprint=plan.fingerprint,
        event_id=event_id,
        entrants=tuple(entrants),
    )
