"""Persistence, Saved publication and restore for the Run-calendar Tour adapter."""

import json

from beta_engine.domain.tournaments.calendar_tour import (
    CalendarTourState,
    calculate_tour_ranking,
    edition_results,
    effective_policy,
)
from beta_engine.infrastructure.db.models import CalendarTourAuthorityModel

COMPONENT_KEY = "calendar_tour_authority"


def require_exhibition_timeline(session, run_id, branch_id):
    if session.get(CalendarTourAuthorityModel, (run_id, branch_id)):
        raise ValueError(
            "Configured Tour owns this timeline; use its Edition and Week Transition commands"
        )


def load_tour(session, *, run_id, branch_id):
    row = session.get(CalendarTourAuthorityModel, (run_id, branch_id))
    if row is None:
        return None
    state = CalendarTourState.model_validate_json(row.payload_json)
    if (state.run_id, state.branch_id, state.fingerprint) != (
        run_id,
        branch_id,
        row.fingerprint,
    ):
        raise ValueError("Native Tour SQLite identity/hash mismatch")
    return state


def put_tour(session, state):
    state = CalendarTourState.model_validate_json(state.model_dump_json())
    row = session.get(CalendarTourAuthorityModel, (state.run_id, state.branch_id))
    if row is None:
        row = CalendarTourAuthorityModel(run_id=state.run_id, branch_id=state.branch_id)
        session.add(row)
    row.payload_json = state.model_dump_json()
    row.fingerprint = state.fingerprint
    session.flush()


def verify_tour(state, checkpoint, world=None):
    if state is None:
        if checkpoint and (
            any(e.schema_version.endswith(".v2") for e in checkpoint.weekly_advances)
            or any(
                e.schema_version == "calendar_followup_knockout.v5"
                for e in checkpoint.tournaments
            )
        ):
            raise ValueError("Official native sporting advance lacks Tour authority")
        return
    if checkpoint is None or (
        state.run_id,
        state.branch_id,
        state.week.ordinal,
        state.checkpoint_fingerprint,
    ) != (
        checkpoint.run_id,
        checkpoint.branch_id,
        checkpoint.week.ordinal,
        checkpoint.fingerprint,
    ):
        raise ValueError(
            "Tour authority differs from its actual population sporting owner"
        )
    events = {e.tournament_id: e for e in checkpoint.tournaments}
    sources = {a.edition.edition_id: a for a in state.editions}
    for receipt in state.receipts:
        command = receipt.request.get("command", {})
        if not isinstance(command, dict):
            raise TypeError("Malformed Tour command receipt")
        if (
            (command.get("command_id"), command.get("action"))
            != (receipt.command_id, receipt.result.get("action"))
            or receipt.result.get("command_id") != receipt.command_id
            or receipt.request.get("explicit_confirmation") is not True
        ):
            raise ValueError("Tour command receipt identity/confirmation is corrupt")
        if command.get("action") == "play":
            event = events.get(command.get("edition_id"))
            expected = (
                {
                    "fingerprint": event.fingerprint,
                    "winner_player_id": event.matches[-1].result.winner_player_id,
                    "prepared_awards": [
                        a.model_dump(mode="json") for a in event.prepared_awards
                    ],
                    "match_ids": [m.match_id for m in event.matches],
                }
                if event
                else None
            )
            played = receipt.result.get("played")
            if not isinstance(played, dict):
                raise ValueError("Tour play receipt lacks played evidence")
            actual = played.copy()
            actual.pop("checkpoint_fingerprint", None)
            if actual != expected:
                raise ValueError(
                    "Tour play receipt differs from actual MatchEngine results"
                )
        action = command.get("action")
        authority = sources.get(command.get("edition_id"))
        if action == "approve" and (
            authority is None
            or authority.field is None
            or receipt.result.get("approved_field")
            != authority.field.model_dump(mode="json")
        ):
            raise ValueError("Tour approval receipt differs from canonical Entry field")
        if action == "draw" and (
            authority is None
            or authority.draw is None
            or receipt.result.get("draw") != authority.draw.model_dump(mode="json")
            or command.get("seed") != authority.draw_seed
            or receipt.command_id != authority.draw_command_id
        ):
            raise ValueError("Tour draw receipt differs from canonical injected draw")
    for authority in state.editions:
        if (
            authority.edition.week.calendar.weeks_per_year,
            authority.edition.week.calendar.start_year,
            authority.edition.week.calendar.season_start_year_week,
        ) != (
            state.week.calendar.weeks_per_year,
            state.week.calendar.start_year,
            state.week.calendar.season_start_year_week,
        ):
            raise ValueError("Edition has a foreign Run calendar")
        if any(
            (s.run_id, s.branch_id) != (state.run_id, state.branch_id)
            for s in authority.submissions
        ):
            raise ValueError("Edition has foreign Entry sources")
        if authority.tournament_fingerprint:
            event = events.get(authority.edition.edition_id)
            if event is None or event.source_saved_head != authority.played_saved_head:
                raise ValueError(
                    "Edition lacks authentic played event and Saved origin"
                )
            edition_results(authority, event)
    advances = {e.command_id: e for e in checkpoint.weekly_advances}
    if {
        e.command_id
        for e in checkpoint.weekly_advances
        if e.schema_version.endswith(".v2")
    } != {t.command_id for t in state.transitions}:
        raise ValueError(
            "Official sporting advances and Week Transition receipts differ"
        )
    for i, transition in enumerate(state.transitions):
        receipt = next(
            (r for r in state.receipts if r.command_id == transition.command_id), None
        )
        impact = receipt.result.get("impact") if receipt else None
        if not isinstance(impact, dict):
            raise TypeError("Tour transition receipt lacks its authoritative impact")
        if (
            receipt is None
            or receipt.result.get("impact", {}).get("ranking")
            != state.rankings[i + 1].model_dump(mode="json")
            or receipt.result.get("impact", {}).get("ranking_fingerprint")
            != transition.ranking_fingerprint
            or receipt.result.get("impact", {}).get("target_week")
            != transition.target_week.model_dump(mode="json")
        ):
            raise ValueError(
                "Tour transition receipt differs from authoritative publication"
            )
        expected_public = {
            "kind": "week_transition_completed",
            "week": transition.target_week.model_dump(mode="json"),
            "ranking_fingerprint": transition.ranking_fingerprint,
            "source_command_id": transition.command_id,
            "announced_edition_ids": [
                a.edition.edition_id
                for a in state.editions
                if a.edition.announcement_week.ordinal == transition.target_week.ordinal
            ],
        }
        if transition.public_event != expected_public:
            raise ValueError(
                "Public Week Transition event differs from effective announcements/ranking"
            )
        event = advances.get(transition.command_id)
        if (
            event is None
            or event.schema_version != "calendar_sporting_week_advance.v2"
            or event.fingerprint != transition.sporting_advance_fingerprint
            or event.target_week != transition.target_week
            or event.policy
            != effective_policy(state, transition.completed_week).development
        ):
            raise ValueError("Official transition lacks coupled development evidence")
        sporting = impact.get("sporting")
        if (
            not isinstance(sporting, dict)
            or sporting.get("advance") != event.model_dump(mode="json")
            or sporting.get("advance_fingerprint") != event.fingerprint
        ):
            raise ValueError(
                "Tour transition receipt differs from actual sporting development"
            )
        if world is not None:
            from beta_engine.domain.players.calendar_sporting_week import (
                age_in_run_years,
            )

            ages = tuple(
                sorted(
                    (p.player_id, int(age_in_run_years(p, transition.target_week)))
                    for p in world.players
                )
            )
            retired = tuple(
                pid
                for pid, age in ages
                if age >= world.lifecycle_policy.automatic_retirement_age
            )
            if (transition.ages, transition.retired_player_ids) != (ages, retired):
                raise ValueError(
                    "Transition lifecycle differs from authentic birth identities/policy"
                )
        # Rebuild each publication from actual immutable point sources and the
        # then-effective policy. Never take stored snapshot totals as inputs.
        prefix = state.model_copy(update={"rankings": state.rankings[: i + 1]})
        expected = calculate_tour_ranking(
            prefix,
            checkpoint,
            target=transition.target_week,
            retired=transition.retired_player_ids,
        )
        if expected != state.rankings[i + 1]:
            raise ValueError(
                "Official ranking does not rebuild from authoritative Edition results"
            )


def saved_tour(payload, *, run_id, branch_id, checkpoint=None):
    component = payload.get("content", {}).get(COMPONENT_KEY)
    if component is None:
        verify_tour(None, checkpoint)
        return None
    if not isinstance(component, dict) or set(component) != {"state", "fingerprint"}:
        raise ValueError("Malformed Saved native Tour component")
    state = CalendarTourState.model_validate_json(json.dumps(component["state"]))
    if (state.run_id, state.branch_id, state.fingerprint) != (
        run_id,
        branch_id,
        component["fingerprint"],
    ):
        raise ValueError("Saved native Tour identity/hash mismatch")
    if checkpoint is None:
        from beta_engine.domain.players.calendar_sporting_checkpoint import (
            CalendarSportingCheckpoint,
        )

        raw = payload.get("content", {}).get("calendar_player_sporting_checkpoint")
        if raw is None:
            raise ValueError("Saved Tour lacks sporting checkpoint")
        checkpoint = CalendarSportingCheckpoint.model_validate_json(
            json.dumps(raw["state"])
        )
        if checkpoint.fingerprint != raw["fingerprint"]:
            raise ValueError("Saved sporting owner fingerprint mismatch")
    from beta_engine.infrastructure.db.initial_world_state import (
        load_saved_initial_world,
    )

    verify_tour(
        state,
        checkpoint,
        load_saved_initial_world(payload, run_id=run_id, branch_id=branch_id),
    )
    from beta_engine.infrastructure.db.player_lifecycle_state import (
        load_saved_lifecycle,
    )

    life = load_saved_lifecycle(payload, run_id=run_id, branch_id=branch_id)
    if not life or (life[-1].week.ordinal, life[-1].fingerprint) != (
        state.week.ordinal,
        state.lifecycle_fingerprint,
    ):
        raise ValueError("Saved native Tour lacks its coupled lifecycle owner")
    return state


def capture_tour(session, payload, *, run_id, branch_id):
    from beta_engine.infrastructure.db.calendar_sporting_checkpoint import (
        load_checkpoint,
    )

    state = load_tour(session, run_id=run_id, branch_id=branch_id)
    from beta_engine.infrastructure.db.initial_world_state import get_initial_world

    verify_tour(
        state,
        load_checkpoint(session, run_id=run_id, branch_id=branch_id),
        get_initial_world(session, run_id=run_id, branch_id=branch_id),
    )
    verify_tour_origins(session, state)
    if state:
        payload["content"][COMPONENT_KEY] = {
            "fingerprint": state.fingerprint,
            "state": state.model_dump(mode="json"),
        }
        from beta_engine.infrastructure.db.player_lifecycle_state import (
            load_saved_lifecycle,
        )

        life = load_saved_lifecycle(payload, run_id=run_id, branch_id=branch_id)
        if not life or life[-1].fingerprint != state.lifecycle_fingerprint:
            raise ValueError("Tour Save lacks its coupled current lifecycle")


def restore_tour(session, *, current_payload, target_payload, run_id, branch_id):
    current = saved_tour(current_payload, run_id=run_id, branch_id=branch_id)
    target = saved_tour(target_payload, run_id=run_id, branch_id=branch_id)
    if load_tour(session, run_id=run_id, branch_id=branch_id) != current:
        raise ValueError("Live Tour differs from current Saved HEAD")
    row = session.get(CalendarTourAuthorityModel, (run_id, branch_id))
    if row:
        session.delete(row)
        session.flush()
    if target:
        put_tour(session, target)


def verify_tour_origins(session, state):
    """Each played event must reference a Signed revision already owning its draw."""
    if state is None:
        return
    from beta_engine.infrastructure.db.models import (
        BranchSavedRevisionModel,
        RunBranchModel,
    )

    branch = session.get(RunBranchModel, state.branch_id)
    revision_id = (
        branch.saved_head_revision_id
        if branch and branch.run_id == state.run_id
        else None
    )
    reachable = set()
    while revision_id:
        if revision_id in reachable:
            raise ValueError("Tour source Saved lineage contains a cycle")
        reachable.add(revision_id)
        row = session.get(BranchSavedRevisionModel, revision_id)
        if row is None or row.run_id != state.run_id:
            raise ValueError("Tour source Saved lineage is missing or foreign")
        revision_id = row.parent_revision_id

    for authority in state.editions:
        if not authority.played_saved_head:
            continue
        row = session.get(BranchSavedRevisionModel, authority.played_saved_head)
        if (
            row is None
            or authority.played_saved_head not in reachable
            or (row.run_id, row.branch_id)
            != (
                state.run_id,
                state.branch_id,
            )
        ):
            raise ValueError("Edition played origin is missing or foreign")
        component = json.loads(row.payload_json).get("content", {}).get(COMPONENT_KEY)
        origin = (
            CalendarTourState.model_validate_json(json.dumps(component["state"]))
            if component
            else None
        )
        frozen = (
            next(
                (
                    a
                    for a in origin.editions
                    if a.edition.edition_id == authority.edition.edition_id
                ),
                None,
            )
            if origin
            else None
        )
        if (
            frozen is None
            or frozen.tournament_fingerprint is not None
            or frozen.edition != authority.edition
            or frozen.submissions != authority.submissions
            or frozen.field != authority.field
            or frozen.draw != authority.draw
            # All immutable pre-play provenance, including the exact frozen
            # ranking binding and creation source, must remain identical.
            # It is not enough that the seeded draw happens to look equal.
            or frozen.execution_fingerprint != authority.execution_fingerprint
            or frozen.draw_seed != authority.draw_seed
            or frozen.draw_command_id != authority.draw_command_id
        ):
            raise ValueError(
                "Edition/draw authority did not exist in the pre-play Saved revision"
            )
