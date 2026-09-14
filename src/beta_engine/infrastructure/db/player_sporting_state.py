"""Persistence, bootstrap, transition, and revision projection for sporting state."""

from __future__ import annotations

import hashlib
import json

from sqlalchemy import delete, select

from beta_engine.domain.players.attribute_catalog import ATTRIBUTE_GROUPS
from beta_engine.domain.players.sporting import (
    CompletedWeekSportingContext,
    PlayerDevelopmentPolicy,
    PlayerSportingRecord,
    PlayerSportingWeekState,
    between_week_state_update,
    weekly_player_development_update,
)
from beta_engine.domain.rankings.official import RankingWeek
from beta_engine.infrastructure.db.models import PlayerSportingWeekStateModel

PLAYER_SPORTING_COMPONENT_KEY = "player_sporting_state"


def _load(row, run_id, branch_id, week):
    state = PlayerSportingWeekState.model_validate_json(row.payload_json)
    if (state.run_id, state.branch_id, state.week.ordinal, state.fingerprint) != (
        run_id,
        branch_id,
        week.ordinal,
        row.fingerprint,
    ):
        raise ValueError("Player sporting identity, week, or fingerprint mismatch")
    return state


def get_sporting(session, *, run_id: str, branch_id: str, week: RankingWeek):
    row = session.get(PlayerSportingWeekStateModel, (run_id, branch_id, week.ordinal))
    return None if row is None else _load(row, run_id, branch_id, week)


def put_sporting(session, state: PlayerSportingWeekState):
    current = get_sporting(
        session, run_id=state.run_id, branch_id=state.branch_id, week=state.week
    )
    if current:
        if current.fingerprint == state.fingerprint:
            return current
        raise ValueError("Player sporting target week already has different state")
    session.add(
        PlayerSportingWeekStateModel(
            run_id=state.run_id,
            branch_id=state.branch_id,
            week_ordinal=state.week.ordinal,
            fingerprint=state.fingerprint,
            payload_json=state.model_dump_json(),
        )
    )
    session.flush()
    return state


def _legacy_group_value(player, group: str) -> int:
    values = player.attributes
    return {
        "Technical": values.technique,
        "Move": values.movement,
        "Tactics": round((values.technique + values.mental) / 2),
        "Mental": values.mental,
        "Physical": values.physical,
        "Creativity": round((values.technique + values.clutch) / 2),
    }[group]


def bootstrap_sporting(session, world, policy: PlayerDevelopmentPolicy | None = None):
    """Project only the already-owned InitialWorld through an explicit legacy adapter."""
    policy = policy or PlayerDevelopmentPolicy()
    players = []
    for player in world.players:
        attributes = {}
        for group, names in ATTRIBUTE_GROUPS.items():
            source = _legacy_group_value(player, group)
            for name in names:
                digest = hashlib.blake2b(
                    f"{policy.bootstrap_policy.policy_id}|{player.source_generation_fingerprint}|{name}".encode(),
                    digest_size=8,
                ).digest()
                width = policy.bootstrap_policy.deterministic_jitter
                jitter = int.from_bytes(digest, "big") % (width * 2 + 1) - width
                attributes[name] = min(
                    200,
                    max(
                        0,
                        round(
                            source
                            * policy.bootstrap_policy.scale_numerator
                            / policy.bootstrap_policy.scale_denominator
                        )
                        + jitter,
                    ),
                )
        growth = player.hidden_career_traits.growth_curve.lower()
        timing = (
            "Early Bloomer"
            if "early" in growth
            else "Late Bloomer"
            if "late" in growth
            else "Standard"
        )
        potential_payload = {
            "player_id": player.player_id,
            "source": player.source_generation_fingerprint,
            "legacy_potential": player.potential_ability,
            "bootstrap_policy": policy.bootstrap_policy.model_dump(mode="json"),
        }
        potential_provenance = json.dumps(
            potential_payload, sort_keys=True, separators=(",", ":")
        )
        players.append(
            PlayerSportingRecord(
                player_id=player.player_id,
                attributes=attributes,
                potential_ovr=min(200, round(player.potential_ability * 200 / 99)),
                potential_identity=hashlib.sha256(
                    potential_provenance.encode()
                ).hexdigest(),
                potential_provenance=potential_provenance,
                development_timing=timing,
                current_form=policy.bootstrap_policy.default_form,
                long_term_form_norm=policy.bootstrap_policy.default_form_norm,
                match_sharpness=policy.bootstrap_policy.default_match_sharpness,
                long_term_fatigue=policy.bootstrap_policy.default_fatigue,
            )
        )
    return put_sporting(
        session,
        PlayerSportingWeekState(
            run_id=world.run_id,
            branch_id=world.branch_id,
            week=RankingWeek(season_index=0, week=1),
            players=tuple(sorted(players, key=lambda p: p.player_id)),
            policy=policy,
            completed_context_fingerprint="bootstrap:not-a-completed-week",
            source_initial_world_fingerprint=world.fingerprint,
            stage_provenance=(
                f"{policy.bootstrap_policy.policy_id}:{policy.bootstrap_policy.provenance}"
            ),
        ),
    )


def transition_sporting(
    session,
    *,
    run_id,
    branch_id,
    completed,
    target,
    lifecycle,
    context: CompletedWeekSportingContext | None = None,
    stage_hook=None,
):
    predecessor = get_sporting(
        session, run_id=run_id, branch_id=branch_id, week=completed
    )
    if predecessor is None:
        raise ValueError(
            "Authoritative predecessor player sporting snapshot is missing"
        )
    context = context or CompletedWeekSportingContext()
    ages = {player.player_id: player.age for player in lifecycle.players}
    if set(ages) != {player.player_id for player in predecessor.players}:
        raise ValueError("Player sporting and lifecycle predecessor rosters differ")
    developed = weekly_player_development_update(
        predecessor, target=target, player_ages=ages, context=context
    )
    if stage_hook is not None:
        stage_hook("after_sporting_development_staging")
    result = put_sporting(
        session, between_week_state_update(developed, context=context)
    )
    if stage_hook is not None:
        stage_hook("after_between_week_staging")
    return result


def _component(states):
    body = [state.model_dump(mode="json") for state in states]
    return {
        "fingerprint": hashlib.sha256(
            json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
        "states": body,
    }


def capture_saved_sporting(session, payload, *, run_id, branch_id):
    rows = session.scalars(
        select(PlayerSportingWeekStateModel)
        .where(
            PlayerSportingWeekStateModel.run_id == run_id,
            PlayerSportingWeekStateModel.branch_id == branch_id,
        )
        .order_by(PlayerSportingWeekStateModel.week_ordinal)
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
        payload["content"][PLAYER_SPORTING_COMPONENT_KEY] = _component(states)


def load_saved_sporting(payload, *, run_id, branch_id):
    component = payload.get("content", {}).get(PLAYER_SPORTING_COMPONENT_KEY)
    if component is None:
        return None
    if not isinstance(component, dict) or set(component) != {"fingerprint", "states"}:
        raise ValueError("Invalid Saved Revision player-sporting component")
    states = tuple(
        PlayerSportingWeekState.model_validate_json(json.dumps(state))
        for state in component["states"]
    )
    if _component(states)["fingerprint"] != component["fingerprint"] or any(
        (state.run_id, state.branch_id) != (run_id, branch_id) for state in states
    ):
        raise ValueError("Saved player-sporting identity or fingerprint mismatch")
    for predecessor, target in zip(states, states[1:], strict=False):
        if target.week.ordinal != predecessor.week.ordinal + 1 or (
            target.predecessor_fingerprint != predecessor.fingerprint
            or target.source_initial_world_fingerprint
            != predecessor.source_initial_world_fingerprint
        ):
            raise ValueError("Saved player-sporting predecessor chain is corrupt")
    return states


def restore_saved_sporting(
    session, *, current_payload, target_payload, run_id, branch_id
):
    expected = load_saved_sporting(current_payload, run_id=run_id, branch_id=branch_id)
    target = load_saved_sporting(target_payload, run_id=run_id, branch_id=branch_id)
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
        ranking = load_saved_ranking_component(
            target_payload, run_id=run_id, branch_id=branch_id
        )
        transition = ranking.authoritative_transition_state if ranking else None
        clock = transition.get("world") if transition else None
        if (target_world is None and ranking is not None) or (
            clock is not None and clock["current_ordinal"] > 0
        ):
            raise ValueError(
                "Legacy Saved Revision has no sporting component and cannot be reconstructed unambiguously"
            )
    rows = session.scalars(
        select(PlayerSportingWeekStateModel)
        .where(
            PlayerSportingWeekStateModel.run_id == run_id,
            PlayerSportingWeekStateModel.branch_id == branch_id,
        )
        .order_by(PlayerSportingWeekStateModel.week_ordinal)
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
        raise ValueError("Live player sporting state differs from saved head")
    session.execute(
        delete(PlayerSportingWeekStateModel).where(
            PlayerSportingWeekStateModel.run_id == run_id,
            PlayerSportingWeekStateModel.branch_id == branch_id,
        )
    )
    for state in target or ():
        put_sporting(session, state)
    if target is None and target_world is not None:
        from beta_engine.infrastructure.db.initial_world_state import get_initial_world

        world = get_initial_world(session, run_id=run_id, branch_id=branch_id)
        if world is None:
            raise ValueError(
                "Target InitialWorldState is unavailable for sporting backfill"
            )
        bootstrap_sporting(session, world)
