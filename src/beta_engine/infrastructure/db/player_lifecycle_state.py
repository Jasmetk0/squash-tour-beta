"""Persistence, bootstrap, transition and Saved Revision projection for lifecycle state."""

import hashlib
import json
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from beta_engine.application.initial_world import InitialWorldState
from beta_engine.domain.players.lifecycle import (
    PlayerLifecycleIdentity,
    PlayerLifecycleWeekState,
    PlayerLifecyclePolicy,
    advance_lifecycle,
)
from beta_engine.domain.players.tour_entry_projection import (
    project_lifecycle_tour_entries,
)
from beta_engine.domain.rankings.official import RankingWeek
from beta_engine.domain.calendar.season_weeks import (
    age_at_calendar_position,
    season_week_to_calendar_position,
)
from beta_engine.infrastructure.db.models import (
    PlayerLifecycleWeekStateModel,
    RunProspectModel,
)
from beta_engine.infrastructure.db.player_tour_entry_triggers import (
    PlayerTourEntryTriggerStore,
)

PLAYER_LIFECYCLE_COMPONENT_KEY = "player_lifecycle"


def _load(row, run_id, branch_id, week):
    state = PlayerLifecycleWeekState.model_validate_json(row.payload_json)
    if (state.run_id, state.branch_id, state.week.ordinal, state.fingerprint) != (
        run_id,
        branch_id,
        week.ordinal,
        row.fingerprint,
    ):
        raise ValueError("Player lifecycle identity, week, or fingerprint mismatch")
    return state


def get_lifecycle(session: Session, *, run_id: str, branch_id: str, week: RankingWeek):
    row = session.get(PlayerLifecycleWeekStateModel, (run_id, branch_id, week.ordinal))
    return None if row is None else _load(row, run_id, branch_id, week)


def put_lifecycle(
    session: Session, state: PlayerLifecycleWeekState
) -> PlayerLifecycleWeekState:
    current = get_lifecycle(
        session, run_id=state.run_id, branch_id=state.branch_id, week=state.week
    )
    if current:
        if current.fingerprint == state.fingerprint:
            return current
        raise ValueError(
            "Player lifecycle target week already has different authoritative state"
        )
    session.add(
        PlayerLifecycleWeekStateModel(
            run_id=state.run_id,
            branch_id=state.branch_id,
            week_ordinal=state.week.ordinal,
            fingerprint=state.fingerprint,
            payload_json=state.model_dump_json(),
        )
    )
    session.flush()
    installed = get_lifecycle(
        session, run_id=state.run_id, branch_id=state.branch_id, week=state.week
    )
    if installed is None:  # pragma: no cover - flush/read invariant
        raise ValueError("Player lifecycle write could not be verified")
    return installed


def bootstrap_lifecycle(
    session: Session,
    world: InitialWorldState,
    policy: PlayerLifecyclePolicy | None = None,
):
    week = RankingWeek(season_index=0, week=1)
    players = []
    for p in world.players:
        provenance = json.dumps(
            {
                "player_id": p.player_id,
                "birth_year": p.birth_year,
                "birth_year_week": p.birth_year_week,
                "source": p.source_generation_fingerprint,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        players.append(
            PlayerLifecycleIdentity(
                player_id=p.player_id,
                birth_year=p.birth_year,
                birth_year_week=p.birth_year_week,
                tie_break_token=hashlib.sha256(provenance.encode()).hexdigest(),
                tie_break_provenance=provenance,
                tour_entry_week=week,
                age=age_at_calendar_position(
                    birth_year=p.birth_year,
                    birth_year_week=p.birth_year_week,
                    calendar_year=season_week_to_calendar_position(
                        2000, 1
                    ).calendar_year,
                    year_week=season_week_to_calendar_position(2000, 1).year_week,
                ),
                status="active",
                origin=f"initial_world:{world.fingerprint}",
            )
        )
    return put_lifecycle(
        session,
        PlayerLifecycleWeekState(
            run_id=world.run_id,
            branch_id=world.branch_id,
            week=week,
            players=tuple(players),
            source_initial_world_fingerprint=world.fingerprint,
            policy=policy or PlayerLifecycleWeekState.model_fields["policy"].default,
        ),
    )


def target_week_prospect_rows(
    session: Session,
    *,
    run_id: str,
    target: RankingWeek,
):
    season_start_year = 2000 + target.season_index
    position = season_week_to_calendar_position(season_start_year, target.week)
    return tuple(
        session.scalars(
            select(RunProspectModel)
            .where(
                RunProspectModel.run_id == run_id,
                RunProspectModel.season_start_year == season_start_year,
                RunProspectModel.season_week == target.week,
                RunProspectModel.calendar_year == position.calendar_year,
                RunProspectModel.year_week == position.year_week,
            )
            .order_by(RunProspectModel.prospect_id)
        )
    )


def prospect_lifecycle_identity(row, *, target: RankingWeek) -> PlayerLifecycleIdentity:
    season_start_year = 2000 + target.season_index
    position = season_week_to_calendar_position(season_start_year, target.week)
    if row.age != 15:
        raise ValueError("Birth-week Run prospect must materialize at age 15")
    if (row.birth_year_week, row.calendar_year, row.year_week) != (
        position.year_week,
        position.calendar_year,
        position.year_week,
    ):
        raise ValueError("Run prospect birth identity differs from target calendar week")
    expected_age = age_at_calendar_position(
        birth_year=row.birth_year,
        birth_year_week=row.birth_year_week,
        calendar_year=position.calendar_year,
        year_week=position.year_week,
    )
    if expected_age != 15:
        raise ValueError("Run prospect birth identity does not resolve to age 15")
    if row.status != "prospect":
        raise ValueError("Birth-week Run prospect has unsupported lifecycle status")

    provenance = json.dumps(
        {
            "kind": "run_prospect_birth_week",
            "run_id": row.run_id,
            "prospect_id": row.prospect_id,
            "birth_year": row.birth_year,
            "birth_year_week": row.birth_year_week,
            "identity_seed": row.identity_seed,
            "source_type": row.source_type,
            "cohort_policy_version": row.cohort_policy_version,
            "profile_version": row.profile_version,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return PlayerLifecycleIdentity(
        player_id=row.prospect_id,
        birth_year=row.birth_year,
        birth_year_week=row.birth_year_week,
        tie_break_token=hashlib.sha256(provenance.encode()).hexdigest(),
        tie_break_provenance=provenance,
        tour_entry_week=None,
        age=15,
        status="active",
        retirement_effective_week=None,
        origin=f"run_prospect:{row.source_type}:{row.profile_version}",
    )


def advance_lifecycle_with_prospects(
    session: Session,
    *,
    predecessor: PlayerLifecycleWeekState,
    target: RankingWeek,
) -> PlayerLifecycleWeekState:
    """Advance lifecycle and activate exactly the prospects born in the target week.

    Materialized future prospects are technical seed records only. They become part of
    branch-owned canonical lifecycle at their birth week, with no implied Tour entry.
    Sporting state is staged independently from the same validated birth-week source.
    """

    advanced = advance_lifecycle(predecessor, target)
    existing_ids = {player.player_id for player in advanced.players}
    additions = []
    for row in target_week_prospect_rows(
        session,
        run_id=predecessor.run_id,
        target=target,
    ):
        if row.prospect_id in existing_ids:
            raise ValueError("Run prospect identity already exists in predecessor lifecycle")
        additions.append(prospect_lifecycle_identity(row, target=target))
        existing_ids.add(row.prospect_id)

    return PlayerLifecycleWeekState(
        run_id=advanced.run_id,
        branch_id=advanced.branch_id,
        week=advanced.week,
        players=tuple(
            sorted((*advanced.players, *additions), key=lambda player: player.player_id)
        ),
        source_initial_world_fingerprint=advanced.source_initial_world_fingerprint,
        predecessor_fingerprint=advanced.predecessor_fingerprint,
        policy=advanced.policy,
    )


def project_lifecycle_tour_entries_through_week(
    session: Session,
    state: PlayerLifecycleWeekState,
    *,
    through_week: RankingWeek,
) -> PlayerLifecycleWeekState:
    """Overlay only Tour-entry history completed by the requested boundary.

    The lifecycle state may represent a later target week. Filtering before the pure
    projection prevents a trigger occurring inside that target week from being sealed
    into its immutable week-opening snapshot.
    """

    if through_week.ordinal > state.week.ordinal:
        raise ValueError("Tour-entry projection boundary cannot be after lifecycle week")
    triggers = PlayerTourEntryTriggerStore(session).list(
        run_id=state.run_id,
        branch_id=state.branch_id,
    )
    completed = tuple(
        trigger
        for trigger in triggers
        if trigger.trigger_week.ordinal <= through_week.ordinal
    )
    return project_lifecycle_tour_entries(state, completed)


def advance_lifecycle_with_completed_tour_entries(
    session: Session,
    *,
    predecessor: PlayerLifecycleWeekState,
    target: RankingWeek,
) -> PlayerLifecycleWeekState:
    """Advance one week and seal Tour entries completed during the predecessor week."""

    advanced = advance_lifecycle_with_prospects(
        session,
        predecessor=predecessor,
        target=target,
    )
    return project_lifecycle_tour_entries_through_week(
        session,
        advanced,
        through_week=predecessor.week,
    )


def transition_lifecycle(
    session: Session,
    *,
    run_id: str,
    branch_id: str,
    completed: RankingWeek,
    target: RankingWeek,
):
    predecessor = get_lifecycle(
        session, run_id=run_id, branch_id=branch_id, week=completed
    )
    if predecessor is None:
        raise ValueError(
            "Authoritative predecessor player lifecycle snapshot is missing"
        )
    return put_lifecycle(
        session,
        advance_lifecycle_with_completed_tour_entries(
            session,
            predecessor=predecessor,
            target=target,
        ),
    )


def capture_saved_lifecycle(session, payload, *, run_id, branch_id):
    rows = session.scalars(
        select(PlayerLifecycleWeekStateModel)
        .where(
            PlayerLifecycleWeekStateModel.run_id == run_id,
            PlayerLifecycleWeekStateModel.branch_id == branch_id,
        )
        .order_by(PlayerLifecycleWeekStateModel.week_ordinal)
    ).all()
    if rows:
        states = [
            _load(
                r,
                run_id,
                branch_id,
                RankingWeek(
                    season_index=r.week_ordinal // 61, week=r.week_ordinal % 61 + 1
                ),
            )
            for r in rows
        ]
        body = [s.model_dump(mode="json") for s in states]
        fingerprint = hashlib.sha256(
            json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        payload["content"][PLAYER_LIFECYCLE_COMPONENT_KEY] = {
            "fingerprint": fingerprint,
            "states": body,
        }


def load_saved_lifecycle(payload, *, run_id, branch_id):
    component = payload.get("content", {}).get(PLAYER_LIFECYCLE_COMPONENT_KEY)
    if component is None:
        return None
    if not isinstance(component, dict) or set(component) != {"fingerprint", "states"}:
        raise ValueError("Invalid Saved Revision player-lifecycle component")
    states = tuple(
        PlayerLifecycleWeekState.model_validate_json(json.dumps(s))
        for s in component["states"]
    )
    body = [s.model_dump(mode="json") for s in states]
    fp = hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    if fp != component["fingerprint"] or any(
        (s.run_id, s.branch_id) != (run_id, branch_id) for s in states
    ):
        raise ValueError("Saved player-lifecycle identity or fingerprint mismatch")
    for predecessor, target in zip(states, states[1:], strict=False):
        if (
            target.week.ordinal != predecessor.week.ordinal + 1
            or target.predecessor_fingerprint != predecessor.fingerprint
            or target.source_initial_world_fingerprint
            != predecessor.source_initial_world_fingerprint
        ):
            raise ValueError("Saved player-lifecycle predecessor chain is corrupt")
    return states


def restore_saved_lifecycle(
    session, *, current_payload, target_payload, run_id, branch_id
):
    expected = load_saved_lifecycle(current_payload, run_id=run_id, branch_id=branch_id)
    target = load_saved_lifecycle(target_payload, run_id=run_id, branch_id=branch_id)
    target_world = None
    if target is None:
        from beta_engine.infrastructure.db.initial_world_state import (
            load_saved_initial_world,
        )
        from beta_engine.infrastructure.db.saved_revision_rankings import (
            load_saved_ranking_component,
        )

        target_world = load_saved_initial_world(
            target_payload, run_id=run_id, branch_id=branch_id
        )
        target_ranking = load_saved_ranking_component(
            target_payload, run_id=run_id, branch_id=branch_id
        )
        authoritative = (
            target_ranking.authoritative_transition_state if target_ranking else None
        )
        world_clock = authoritative.get("world") if authoritative else None
        if (target_world is None and target_ranking is not None) or (
            world_clock is not None and world_clock["current_ordinal"] > 0
        ):
            raise ValueError(
                "Legacy Saved Revision has no lifecycle component and cannot be "
                "reconstructed unambiguously from its owned target state"
            )
    rows = session.scalars(
        select(PlayerLifecycleWeekStateModel)
        .where(
            PlayerLifecycleWeekStateModel.run_id == run_id,
            PlayerLifecycleWeekStateModel.branch_id == branch_id,
        )
        .order_by(PlayerLifecycleWeekStateModel.week_ordinal)
    ).all()
    live = tuple(
        _load(
            r,
            run_id,
            branch_id,
            RankingWeek(
                season_index=r.week_ordinal // 61, week=r.week_ordinal % 61 + 1
            ),
        )
        for r in rows
    )
    if tuple(s.fingerprint for s in live) != tuple(
        s.fingerprint for s in (expected or ())
    ):
        raise ValueError("Live player lifecycle differs from saved head")
    session.execute(
        delete(PlayerLifecycleWeekStateModel).where(
            PlayerLifecycleWeekStateModel.run_id == run_id,
            PlayerLifecycleWeekStateModel.branch_id == branch_id,
        )
    )
    for state in target or ():
        put_lifecycle(session, state)
    if target is None and target_world is not None:
        from beta_engine.infrastructure.db.initial_world_state import get_initial_world

        world = get_initial_world(session, run_id=run_id, branch_id=branch_id)
        if world is None:  # transaction ordering/integrity guard
            raise ValueError(
                "Target InitialWorldState is unavailable for lifecycle backfill"
            )
        bootstrap_lifecycle(session, world)
