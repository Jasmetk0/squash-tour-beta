"""Persistence, bootstrap, transition and Saved Revision projection for lifecycle state."""

from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from beta_engine.application.initial_world import InitialWorldState
from beta_engine.domain.calendar.run_week_position import RunWeekPosition
from beta_engine.domain.calendar.season_weeks import (
    age_at_calendar_position,
    season_week_to_calendar_position,
)
from beta_engine.domain.players.calendar_lifecycle import (
    CalendarPlayerLifecycleState, CalendarTourLifecycleState, calendar_lifecycle_history,
)
from beta_engine.domain.players.lifecycle import (
    PlayerLifecycleIdentity,
    PlayerLifecyclePolicy,
    PlayerLifecycleWeekState,
    advance_lifecycle,
)
from beta_engine.domain.players.tour_entry_projection import (
    project_lifecycle_tour_entries,
)
from beta_engine.domain.rankings.official import RankingWeek
from beta_engine.infrastructure.db.models import (
    PlayerLifecycleWeekStateModel,
    RunProspectModel,
)
from beta_engine.infrastructure.db.player_tour_entry_triggers import (
    PlayerTourEntryTriggerStore,
)

if TYPE_CHECKING:
    from beta_engine.application.calendar_initial_world import CalendarInitialWorldState

PLAYER_LIFECYCLE_COMPONENT_KEY = "player_lifecycle"


def _parse_lifecycle_json(raw):
    value = json.loads(raw)
    if isinstance(value, dict) and value.get("schema_version") == "player_lifecycle_calendar_state.v2":
        return CalendarPlayerLifecycleState.model_validate_json(raw)
    if isinstance(value, dict) and value.get("schema_version") == "player_lifecycle_calendar_state.v3":
        return CalendarTourLifecycleState.model_validate_json(raw)
    return PlayerLifecycleWeekState.model_validate_json(raw)


def decode_prevalidated_lifecycle(payload, *, run_id, branch_id):
    """Decode the immutable Saved lifecycle AFTER repository lineage validation.

    Only the calendar Tour request path calls this with its already signed and
    component-verified HEAD in the same transaction. The full Saved validator
    independently rebuilds the birth/Entry chain on cache misses. Here, recheck
    all serialized identities and the aggregate component hash, but do not
    recompute the same historical lifecycle chain on every Admin read/preview.
    A changed Signed payload invalidates the repository's byte-digest cache.
    Never use this shortcut for unknown snapshots, restore, or an unsaved Tour.
    """
    component = payload.get("content", {}).get(PLAYER_LIFECYCLE_COMPONENT_KEY)
    if component is None:
        return None
    if not isinstance(component, dict) or set(component) != {"fingerprint", "states"}:
        raise ValueError("Invalid prevalidated lifecycle component")
    raw = component["states"]
    if not isinstance(raw, list) or not raw:
        raise ValueError("Prevalidated lifecycle component has no states")
    states = tuple(_parse_lifecycle_json(json.dumps(s)) for s in raw)
    body = [s.model_dump(mode="json") for s in states]
    digest = hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    if digest != component["fingerprint"] or any(
        (s.run_id, s.branch_id) != (run_id, branch_id) for s in states
    ):
        raise ValueError("Prevalidated lifecycle identity/hash mismatch")
    return states


def _load(row, run_id, branch_id, week_ordinal):
    state = _parse_lifecycle_json(row.payload_json)
    if (state.run_id, state.branch_id, state.week.ordinal, state.fingerprint) != (
        run_id,
        branch_id,
        week_ordinal,
        row.fingerprint,
    ):
        raise ValueError("Player lifecycle identity, week, or fingerprint mismatch")
    return state


def get_lifecycle(session: Session, *, run_id: str, branch_id: str, week: RankingWeek | RunWeekPosition):
    row = session.get(PlayerLifecycleWeekStateModel, (run_id, branch_id, week.ordinal))
    if row is None:
        return None
    state = _load(row, run_id, branch_id, week.ordinal)
    if isinstance(state, (CalendarPlayerLifecycleState, CalendarTourLifecycleState)):
        if not isinstance(week, RunWeekPosition) or state.week != week:
            raise ValueError("Calendar lifecycle requires the matching Run-owned position")
    elif not isinstance(week, RankingWeek):
        raise ValueError("Legacy lifecycle requires its historical RankingWeek")  # noqa: TRY004 — domain/API conflict
    return state


def put_lifecycle(
    session: Session, state: PlayerLifecycleWeekState | CalendarPlayerLifecycleState
) -> PlayerLifecycleWeekState | CalendarPlayerLifecycleState:
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


def derive_bootstrap_lifecycle(
    world: InitialWorldState | CalendarInitialWorldState,
    policy: PlayerLifecyclePolicy | None = None,
) -> PlayerLifecycleWeekState | CalendarPlayerLifecycleState:
    """Pure Week-1 projection used for pristine-source checks and installation."""
    from beta_engine.application.calendar_initial_world import (
        CalendarInitialWorldState,
        derive_calendar_bootstrap_lifecycle,
    )

    if isinstance(world, CalendarInitialWorldState):
        if policy is not None and policy != world.lifecycle_policy:
            raise ValueError("Calendar lifecycle policy differs from the adopted world")
        return derive_calendar_bootstrap_lifecycle(world)
    week = RankingWeek(season_index=0, week=1)
    world_fingerprint = world.fingerprint
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
                origin=f"initial_world:{world_fingerprint}",
            )
        )
    return PlayerLifecycleWeekState(
        run_id=world.run_id,
        branch_id=world.branch_id,
        week=week,
        players=tuple(players),
        source_initial_world_fingerprint=world_fingerprint,
        policy=policy or PlayerLifecycleWeekState.model_fields["policy"].default,
    )


def bootstrap_lifecycle(
    session: Session,
    world: InitialWorldState | CalendarInitialWorldState,
    policy: PlayerLifecyclePolicy | None = None,
):
    return put_lifecycle(session, derive_bootstrap_lifecycle(world, policy))


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
                r.week_ordinal,
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
        _parse_lifecycle_json(json.dumps(s))
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
    if any(isinstance(s, CalendarPlayerLifecycleState) for s in states):
        if not isinstance(states[0], CalendarPlayerLifecycleState) or any(
            not isinstance(s, CalendarTourLifecycleState) for s in states[1:]
        ):
            raise ValueError("Calendar population lifecycle cannot contain a mixed legacy chain")
        from beta_engine.infrastructure.db.initial_world_state import (
            load_saved_initial_world,
        )

        world = load_saved_initial_world(payload, run_id=run_id, branch_id=branch_id)
        state = states[0]
        if world is None or world.schema_version != "initial_world_state.v2" or state.week.calendar != world.run_calendar:
            raise ValueError("Saved calendar lifecycle differs from its InitialWorld clock")
        if (state.policy != world.lifecycle_policy or
            tuple((p.player_id, p.birth_year, p.birth_year_week, p.age, p.source_generation_fingerprint) for p in state.players) !=
            tuple((p.player_id, p.birth_year, p.birth_year_week, p.age_years_at_season_start, p.source_generation_fingerprint) for p in world.players)):
            raise ValueError("Saved calendar lifecycle differs from its InitialWorld players")
        if len(states)>1:
            from beta_engine.domain.tournaments.calendar_tour import CalendarTourState, lifecycle_calendars
            tour_component=payload.get('content',{}).get('calendar_tour_authority')
            if not tour_component:
                raise ValueError('Native lifecycle progression requires its Tour owner')
            tour=CalendarTourState.model_validate_json(json.dumps(tour_component['state']))
            expected=calendar_lifecycle_history(state,tour.week,tuple(s for a in tour.editions for s in a.submissions),
                effective_calendars=lifecycle_calendars(tour))
            if states!=expected or states[-1].fingerprint!=tour.lifecycle_fingerprint:
                raise ValueError('Native lifecycle history differs from actual births, policy or Tour entry')
    elif any(isinstance(s,CalendarTourLifecycleState) for s in states):
        raise ValueError('Native lifecycle history lacks its v2 population bootstrap')
    for predecessor, target in zip(states, states[1:], strict=False):
        if (
            target.week.ordinal != predecessor.week.ordinal + 1
            or target.predecessor_fingerprint != predecessor.fingerprint
            or target.source_initial_world_fingerprint
            != predecessor.source_initial_world_fingerprint
        ):
            raise ValueError("Saved player-lifecycle predecessor chain is corrupt")
    return states



def remap_saved_lifecycle_component(
    payload,
    *,
    run_id: str,
    source_branch_id: str,
    target_branch_id: str,
):
    """Rebuild a complete Saved Revision lifecycle chain for a forked Branch."""
    source = load_saved_lifecycle(
        payload,
        run_id=run_id,
        branch_id=source_branch_id,
    )
    if source is None:
        return None

    remapped = []
    previous = None
    for state in source:
        target = _parse_lifecycle_json(
            state.model_copy(
                update={
                    "branch_id": target_branch_id,
                    "predecessor_fingerprint": (
                        previous.fingerprint if previous is not None else None
                    ),
                }
            ).model_dump_json()
        )
        remapped.append(target)
        previous = target

    body = [state.model_dump(mode="json") for state in remapped]
    fingerprint = hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return {
        "fingerprint": fingerprint,
        "states": body,
    }



def restore_saved_lifecycle(
    session, *, current_payload, target_payload, run_id, branch_id,
    _validated_states=None,
):
    if _validated_states is None:
        expected = load_saved_lifecycle(current_payload, run_id=run_id, branch_id=branch_id)
        target = load_saved_lifecycle(target_payload, run_id=run_id, branch_id=branch_id)
    else:
        # Used solely for both Tour-bearing revisions authenticated by the
        # repository's Signed ancestry gate in this same restore transaction.
        # The original validator fully rebuilt each exact Saved Tour lifecycle.
        # The live SQLite rows are still loaded/checked below, and newly
        # captured restored state is independently verified before commit.
        expected, target = _validated_states
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
            r.week_ordinal,
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
