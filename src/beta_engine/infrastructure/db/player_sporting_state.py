"""Persistence, bootstrap, transition, and revision projection for sporting state."""

from __future__ import annotations

import hashlib
import json

from sqlalchemy import delete, select

from beta_engine.domain.players.attribute_catalog import ATTRIBUTE_GROUPS
from beta_engine.domain.players.sporting import (
    CompletedWeekSportingContext,
    CompetitiveMatchCount,
    PlayerDevelopmentPolicy,
    PlayerSportingRecord,
    PlayerSportingWeekState,
    between_week_state_update,
    weekly_player_development_update,
)
from beta_engine.domain.rankings.official import RankingWeek
from beta_engine.infrastructure.db.models import (
    CompletedWeekSportingContextModel,
    PlayerSportingWeekStateModel,
)

PLAYER_SPORTING_COMPONENT_KEY = "player_sporting_state"


def put_completed_context(session, context: CompletedWeekSportingContext):
    key = (context.run_id, context.branch_id, context.completed_week.ordinal)
    current = session.get(CompletedWeekSportingContextModel, key)
    if current is not None:
        if current.fingerprint == context.fingerprint:
            return context
        raise ValueError(
            "Completed-week sporting context already has different evidence"
        )
    session.add(
        CompletedWeekSportingContextModel(
            run_id=context.run_id,
            branch_id=context.branch_id,
            week_ordinal=context.completed_week.ordinal,
            fingerprint=context.fingerprint,
            payload_json=context.model_dump_json(),
        )
    )
    session.flush()
    return context


def get_completed_context(session, *, run_id, branch_id, completed_week):
    row = session.get(
        CompletedWeekSportingContextModel,
        (run_id, branch_id, completed_week.ordinal),
    )
    if row is None:
        raise ValueError(
            "Authoritative completed-week sporting context is missing; zero matches cannot be inferred"
        )
    context = CompletedWeekSportingContext.model_validate_json(row.payload_json)
    if (
        context.run_id,
        context.branch_id,
        context.completed_week,
        context.fingerprint,
    ) != (run_id, branch_id, completed_week, row.fingerprint):
        raise ValueError(
            "Completed-week sporting context identity or fingerprint mismatch"
        )
    return context


def resolve_completed_context_from_owned_sources(
    session, *, run_id, branch_id, completed_week, player_ids, source_ids=None
):
    """Resolve a closed, explicitly enumerated set of owned completed event sources."""
    from beta_engine.infrastructure.db.owned_tournament_sources import (
        OwnedTournamentRankingSourceStore,
    )

    store = OwnedTournamentRankingSourceStore(session)
    history = store.history(run_id=run_id, branch_id=branch_id)
    if any(source is None for source in history):
        raise ValueError("Owned sporting source history contains a missing source")
    owned_sources = tuple(source for source in history if source is not None)
    universe = tuple(
        source
        for source in owned_sources
        if source.binding.completed_week == completed_week
    )
    universe_ids = tuple(sorted(source.binding.edition_id for source in universe))
    if source_ids is not None and tuple(sorted(set(source_ids))) != universe_ids:
        raise ValueError(
            "Completed sporting source manifest differs from the complete owned source universe"
        )
    if not universe:
        raise ValueError("Zero-match context requires explicit authoritative evidence")
    counts = {player_id: 0 for player_id in player_ids}
    fingerprints = []
    for source in universe:
        if source.result.completion_status != "complete" or not source.result.persisted:
            raise ValueError(
                "Completed sporting source is not authoritative and complete"
            )
        fingerprints.append(source.fingerprint)
        for match in source.result.match_result_refs:
            if not match.result_fingerprint:
                raise ValueError(
                    "Completed sporting source contains an unverified match"
                )
            scoreline = (match.scoreline or "").upper()
            if not scoreline or "W/O" in scoreline or "WALKOVER" in scoreline:
                raise ValueError(
                    "Completed sporting source cannot prove a competitive played match"
                )
            if match.winner_player_id in counts:
                counts[match.winner_player_id] += 1
            if match.loser_player_id in counts:
                counts[match.loser_player_id] += 1
    return put_completed_context(
        session,
        CompletedWeekSportingContext(
            run_id=run_id,
            branch_id=branch_id,
            completed_week=completed_week,
            competitive_match_counts=tuple(
                CompetitiveMatchCount(player_id=player_id, count=count)
                for player_id, count in sorted(counts.items())
            ),
            source_fingerprints=tuple(sorted(fingerprints)),
            provenance="complete explicit manifest of Run/Branch-owned tournament result sources",
        ),
    )


def resolve_completed_context_from_authoritative_matches(
    session, *, run_id, branch_id, completed_week, player_ids
):
    """Prefer the Run/Branch slot ledger when authoritative matches exist."""
    from beta_engine.application.authoritative_slot_matches import (
        AuthoritativeSlotMatchExecutor,
    )
    from beta_engine.infrastructure.db.models import (
        SimulationEventGroupModel,
        SimulationSlotModel,
    )

    slots = session.scalars(
        select(SimulationSlotModel).where(
            SimulationSlotModel.run_id == run_id,
            SimulationSlotModel.branch_id == branch_id,
            SimulationSlotModel.week_ordinal == completed_week.ordinal,
        )
    ).all()
    if not slots:
        raise ValueError(
            "No authoritative Run/Branch Simulation Slot exists for completed week"
        )
    if any(slot.status != "complete" for slot in slots):
        raise ValueError(
            "Authoritative Simulation Slot ledger owns the week but is incomplete"
        )

    rows = session.scalars(
        select(SimulationEventGroupModel)
        .where(
            SimulationEventGroupModel.run_id == run_id,
            SimulationEventGroupModel.branch_id == branch_id,
            SimulationEventGroupModel.week_ordinal == completed_week.ordinal,
        )
        .order_by(SimulationEventGroupModel.slot_id, SimulationEventGroupModel.group_id)
    ).all()
    if not rows:
        raise ValueError("Completed authoritative slots contain no committed groups")
    executor = AuthoritativeSlotMatchExecutor(session)
    terminal = executor.terminal_checkpoint(
        run_id=run_id, branch_id=branch_id, week=completed_week
    )
    if terminal is None:
        raise ValueError("Authoritative completed week has no terminal sporting head")
    counts = {player_id: 0 for player_id in player_ids}
    effect_fingerprints = []
    source_fingerprints = []
    for row in rows:
        group = executor._load_group(row)
        source_fingerprints.append(row.result_fingerprint)
        for effect in group.effects:
            effect_fingerprints.append(effect.fingerprint)
            if effect.player_id in counts:
                counts[effect.player_id] += 1
    return put_completed_context(
        session,
        CompletedWeekSportingContext(
            schema_version="completed_week_sporting_context.v2",
            run_id=run_id,
            branch_id=branch_id,
            completed_week=completed_week,
            competitive_match_counts=tuple(
                CompetitiveMatchCount(player_id=player_id, count=count)
                for player_id, count in sorted(counts.items())
            ),
            source_fingerprints=tuple(sorted(source_fingerprints)),
            terminal_sporting_fingerprint=terminal.fingerprint,
            match_effect_fingerprints=tuple(sorted(effect_fingerprints)),
            provenance="authoritative Run/Branch Simulation Slot match/effect ledger",
        ),
    )


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
                attributes=tuple(attributes.items()),
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
            effective_development_policy=policy,
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
    target_effective_development_policy: PlayerDevelopmentPolicy | None = None,
    stage_hook=None,
):
    predecessor = get_sporting(
        session, run_id=run_id, branch_id=branch_id, week=completed
    )
    if predecessor is None:
        raise ValueError(
            "Authoritative predecessor player sporting snapshot is missing"
        )
    context = get_completed_context(
        session, run_id=run_id, branch_id=branch_id, completed_week=completed
    )
    if context.terminal_sporting_fingerprint:
        from beta_engine.application.authoritative_slot_matches import (
            AuthoritativeSlotMatchExecutor,
        )

        terminal = AuthoritativeSlotMatchExecutor(session).terminal_checkpoint(
            run_id=run_id, branch_id=branch_id, week=completed
        )
        if (
            terminal is None
            or terminal.fingerprint != context.terminal_sporting_fingerprint
        ):
            raise ValueError("Completed sporting context terminal head mismatch")
        predecessor = predecessor.model_copy(update={"players": terminal.players})
    target_effective_development_policy = (
        target_effective_development_policy or predecessor.effective_development_policy
    )
    ages = {player.player_id: player.age for player in lifecycle.players}
    if set(ages) != {player.player_id for player in predecessor.players}:
        raise ValueError("Player sporting and lifecycle predecessor rosters differ")
    if {item.player_id for item in context.competitive_match_counts} != set(ages):
        raise ValueError(
            "Completed sporting context must contain exactly the predecessor roster"
        )
    developed = weekly_player_development_update(
        predecessor, target=target, player_ages=ages, context=context
    )
    if stage_hook is not None:
        stage_hook("after_sporting_development_staging")
    result = put_sporting(
        session,
        between_week_state_update(
            developed,
            context=context,
            target_effective_development_policy=target_effective_development_policy,
        ),
    )
    if stage_hook is not None:
        stage_hook("after_between_week_staging")
    return result


def _component(states, contexts=()):
    state_body = [state.model_dump(mode="json") for state in states]
    context_body = [context.model_dump(mode="json") for context in contexts]
    body = {"states": state_body, "contexts": context_body}
    return {
        "fingerprint": hashlib.sha256(
            json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
        **body,
    }


def _validate_state_context_chain(states, contexts):
    state_ordinals = tuple(state.week.ordinal for state in states)
    context_ordinals = tuple(context.completed_week.ordinal for context in contexts)
    if state_ordinals != tuple(sorted(set(state_ordinals))):
        raise ValueError("Player sporting state weeks are not unique and canonical")
    if context_ordinals != tuple(sorted(set(context_ordinals))):
        raise ValueError(
            "Completed sporting context weeks are not unique and canonical"
        )
    by_week = {context.completed_week.ordinal: context for context in contexts}
    for index, state in enumerate(states):
        if index == 0 and state.week.ordinal == 0:
            if state.completed_context_fingerprint != "bootstrap:not-a-completed-week":
                raise ValueError(
                    "Bootstrap sporting state has an invalid context marker"
                )
            continue
        context = by_week.get(state.week.ordinal - 1)
        if (
            context is None
            or context.fingerprint != state.completed_context_fingerprint
        ):
            raise ValueError(
                "Player sporting state has a missing or mismatched predecessor-week context"
            )
        if (context.run_id, context.branch_id) != (state.run_id, state.branch_id):
            raise ValueError("Player sporting state context scope differs")
    if states:
        referenced = {state.week.ordinal - 1 for state in states[1:]}
        allowed_pending = states[-1].week.ordinal
        if any(
            ordinal not in referenced and ordinal != allowed_pending
            for ordinal in context_ordinals
        ):
            raise ValueError(
                "Saved sporting context is not linked to its proper week boundary"
            )


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
        context_rows = session.scalars(
            select(CompletedWeekSportingContextModel)
            .where(
                CompletedWeekSportingContextModel.run_id == run_id,
                CompletedWeekSportingContextModel.branch_id == branch_id,
            )
            .order_by(CompletedWeekSportingContextModel.week_ordinal)
        ).all()
        contexts = tuple(
            get_completed_context(
                session,
                run_id=run_id,
                branch_id=branch_id,
                completed_week=RankingWeek(
                    season_index=row.week_ordinal // 61,
                    week=row.week_ordinal % 61 + 1,
                ),
            )
            for row in context_rows
        )
        _validate_state_context_chain(states, contexts)
        payload["content"][PLAYER_SPORTING_COMPONENT_KEY] = _component(states, contexts)


def load_saved_sporting(payload, *, run_id, branch_id):
    component = payload.get("content", {}).get(PLAYER_SPORTING_COMPONENT_KEY)
    if component is None:
        return None
    if not isinstance(component, dict) or set(component) != {
        "fingerprint",
        "states",
        "contexts",
    }:
        raise ValueError("Invalid Saved Revision player-sporting component")
    states = tuple(
        PlayerSportingWeekState.model_validate_json(json.dumps(state))
        for state in component["states"]
    )
    contexts = tuple(
        CompletedWeekSportingContext.model_validate_json(json.dumps(context))
        for context in component["contexts"]
    )
    _validate_state_context_chain(states, contexts)
    if _component(states, contexts)["fingerprint"] != component["fingerprint"] or any(
        (state.run_id, state.branch_id) != (run_id, branch_id) for state in states
    ):
        raise ValueError("Saved player-sporting identity or fingerprint mismatch")
    if any(
        (context.run_id, context.branch_id) != (run_id, branch_id)
        for context in contexts
    ):
        raise ValueError("Saved completed sporting context identity mismatch")
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
    expected_component = current_payload.get("content", {}).get(
        PLAYER_SPORTING_COMPONENT_KEY
    )
    target_component = target_payload.get("content", {}).get(
        PLAYER_SPORTING_COMPONENT_KEY
    )
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
    live_context_rows = session.scalars(
        select(CompletedWeekSportingContextModel)
        .where(
            CompletedWeekSportingContextModel.run_id == run_id,
            CompletedWeekSportingContextModel.branch_id == branch_id,
        )
        .order_by(CompletedWeekSportingContextModel.week_ordinal)
    ).all()
    live_context_fingerprints = tuple(row.fingerprint for row in live_context_rows)
    expected_context_fingerprints = tuple(
        CompletedWeekSportingContext.model_validate_json(json.dumps(value)).fingerprint
        for value in (expected_component or {}).get("contexts", [])
    )
    if live_context_fingerprints != expected_context_fingerprints:
        raise ValueError("Live completed sporting contexts differ from saved head")
    session.execute(
        delete(PlayerSportingWeekStateModel).where(
            PlayerSportingWeekStateModel.run_id == run_id,
            PlayerSportingWeekStateModel.branch_id == branch_id,
        )
    )
    session.execute(
        delete(CompletedWeekSportingContextModel).where(
            CompletedWeekSportingContextModel.run_id == run_id,
            CompletedWeekSportingContextModel.branch_id == branch_id,
        )
    )
    for state in target or ():
        put_sporting(session, state)
    for value in (target_component or {}).get("contexts", []):
        put_completed_context(
            session, CompletedWeekSportingContext.model_validate_json(json.dumps(value))
        )
    if target is None and target_world is not None:
        from beta_engine.infrastructure.db.initial_world_state import get_initial_world

        world = get_initial_world(session, run_id=run_id, branch_id=branch_id)
        if world is None:
            raise ValueError(
                "Target InitialWorldState is unavailable for sporting backfill"
            )
        bootstrap_sporting(session, world)
