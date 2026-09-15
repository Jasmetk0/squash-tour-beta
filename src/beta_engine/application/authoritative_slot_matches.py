"""Transaction-ready executor for the supported authoritative tournament slice."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import cast

from sqlalchemy import select

from beta_engine.core import DeterministicRng
from beta_engine.domain.matches import (
    MatchContext,
    MatchEngine,
    MatchInputSnapshot,
    MatchParticipantContext,
    RallyCalibrationProfile,
    official_match_format_snapshot,
)
from beta_engine.domain.matches.models import MatchResult
from beta_engine.domain.rankings.official import RankingWeek
from beta_engine.domain.simulation_slots import (
    AuthoritativeMatchInput,
    CanonicalMatchInputProjectionPolicy,
    MatchSportingEffectsPolicy,
    PlayerMatchSportingEffect,
    PlayerSportingCheckpoint,
    SimulationSlotPlan,
    SimulationMatchEventPlan,
    calculate_match_effects,
    fingerprint,
    project_player,
    projected_engine_player,
)
from beta_engine.infrastructure.db.models import (
    SimulationEventGroupModel,
    SimulationSlotModel,
)
from beta_engine.infrastructure.db.player_sporting_state import get_sporting
from beta_engine.infrastructure.db.initial_world_state import get_initial_world
from beta_engine.infrastructure.db.player_lifecycle_state import get_lifecycle

MATCH_ENGINE_VERSION = "match_engine_v9"


@dataclass(frozen=True)
class AuthoritativeGroupResult:
    authoritative_input: AuthoritativeMatchInput
    result: MatchResult
    result_fingerprint: str
    effects: tuple[PlayerMatchSportingEffect, PlayerMatchSportingEffect]
    terminal_checkpoint: PlayerSportingCheckpoint
    exact_retry: bool = False


@dataclass(frozen=True)
class AuthoritativeFourPlayerTournamentResult:
    event_id: str
    semifinal_groups: tuple[AuthoritativeGroupResult, AuthoritativeGroupResult]
    final_group: AuthoritativeGroupResult
    champion_player_id: str
    match_result_fingerprints: tuple[str, str, str]


def execute_supported_four_player_tournament(
    session,
    *,
    run_id: str,
    branch_id: str,
    week: RankingWeek,
    event_id: str,
    ordered_player_ids: tuple[str, str, str, str],
    seed: int,
) -> AuthoritativeFourPlayerTournamentResult:
    """Production application path for the deliberately narrow four-player draw."""
    executor = AuthoritativeSlotMatchExecutor(session)
    semifinal_plans = (
        SimulationMatchEventPlan(
            group_id=f"{event_id}:sf1",
            event_id=event_id,
            match_id=f"{event_id}:sf1",
            direct_player_ids=ordered_player_ids[:2],
        ),
        SimulationMatchEventPlan(
            group_id=f"{event_id}:sf2",
            event_id=event_id,
            match_id=f"{event_id}:sf2",
            direct_player_ids=ordered_player_ids[2:],
        ),
    )
    first = executor.create_slot(
        run_id=run_id,
        branch_id=branch_id,
        week=week,
        slot_id=f"{event_id}:slot:1",
        ordinal=1,
        group_ids=tuple(item.group_id for item in semifinal_plans),
        match_events=semifinal_plans,
    )
    semifinal_one = executor.execute_match_group(
        run_id=run_id,
        branch_id=branch_id,
        week=week,
        slot_id=first.slot_id,
        group_id=semifinal_plans[0].group_id,
        event_id=event_id,
        match_id=semifinal_plans[0].match_id,
        player_a_id=ordered_player_ids[0],
        player_b_id=ordered_player_ids[1],
        seed=seed + 1,
        expected_slot_start_fingerprint=first.slot_start_fingerprint,
    )
    semifinal_two = executor.execute_match_group(
        run_id=run_id,
        branch_id=branch_id,
        week=week,
        slot_id=first.slot_id,
        group_id=semifinal_plans[1].group_id,
        event_id=event_id,
        match_id=semifinal_plans[1].match_id,
        player_a_id=ordered_player_ids[2],
        player_b_id=ordered_player_ids[3],
        seed=seed + 2,
        expected_slot_start_fingerprint=first.slot_start_fingerprint,
    )
    semifinal_groups = (semifinal_one, semifinal_two)
    feeder_ids = (semifinal_plans[0].group_id, semifinal_plans[1].group_id)
    final_plan = SimulationMatchEventPlan(
        group_id=f"{event_id}:final",
        event_id=event_id,
        match_id=f"{event_id}:final",
        feeder_group_ids=feeder_ids,
    )
    second = executor.create_slot(
        run_id=run_id,
        branch_id=branch_id,
        week=week,
        slot_id=f"{event_id}:slot:2",
        ordinal=2,
        group_ids=(final_plan.group_id,),
        match_events=(final_plan,),
        dependency_ids=feeder_ids,
    )
    finalists = (
        semifinal_one.result.winner_player_id,
        semifinal_two.result.winner_player_id,
    )
    final = executor.execute_match_group(
        run_id=run_id,
        branch_id=branch_id,
        week=week,
        slot_id=second.slot_id,
        group_id=final_plan.group_id,
        event_id=event_id,
        match_id=final_plan.match_id,
        player_a_id=finalists[0],
        player_b_id=finalists[1],
        seed=seed + 3,
        expected_slot_start_fingerprint=second.slot_start_fingerprint,
    )
    return AuthoritativeFourPlayerTournamentResult(
        event_id=event_id,
        semifinal_groups=semifinal_groups,
        final_group=final,
        champion_player_id=final.result.winner_player_id,
        match_result_fingerprints=(
            semifinal_one.result_fingerprint,
            semifinal_two.result_fingerprint,
            final.result_fingerprint,
        ),
    )


class AuthoritativeSlotMatchExecutor:
    """Owns slot snapshots and atomic event-group commits in the caller transaction."""

    def __init__(self, session):
        self.session = session

    def create_slot(
        self,
        *,
        run_id: str,
        branch_id: str,
        week: RankingWeek,
        slot_id: str,
        ordinal: int,
        group_ids: tuple[str, ...],
        match_events: tuple[SimulationMatchEventPlan, ...],
        dependency_ids: tuple[str, ...] = (),
    ) -> SimulationSlotPlan:
        key = (run_id, branch_id, week.ordinal, slot_id)
        current = self.session.get(SimulationSlotModel, key)
        if current:
            return self._load_plan(current)
        prior = self.session.scalar(
            select(SimulationSlotModel).where(
                SimulationSlotModel.run_id == run_id,
                SimulationSlotModel.branch_id == branch_id,
                SimulationSlotModel.week_ordinal == week.ordinal,
                SimulationSlotModel.slot_ordinal == ordinal - 1,
            )
        )
        if ordinal > 1 and (prior is None or prior.status != "complete"):
            raise ValueError(
                "dependent later slot requires a complete predecessor slot"
            )
        feeder_ids = tuple(
            feeder
            for event in match_events
            for feeder in (event.feeder_group_ids or ())
        )
        if tuple(dependency_ids) != feeder_ids:
            raise ValueError(
                "slot dependencies must exactly match planned feeder groups"
            )
        if feeder_ids:
            prior_group_ids = set(
                self.session.scalars(
                    select(SimulationEventGroupModel.group_id).where(
                        SimulationEventGroupModel.run_id == run_id,
                        SimulationEventGroupModel.branch_id == branch_id,
                        SimulationEventGroupModel.week_ordinal == week.ordinal,
                    )
                ).all()
            )
            if not set(feeder_ids) <= prior_group_ids:
                raise ValueError("slot feeder dependencies are not committed")
        if prior is None:
            opening = get_sporting(
                self.session, run_id=run_id, branch_id=branch_id, week=week
            )
            if opening is None:
                raise ValueError("opening authoritative sporting week state is missing")
            players = opening.players
            opening_fingerprint = opening.fingerprint
            predecessor = None
        else:
            checkpoint = self._load_checkpoint(prior)
            players = checkpoint.players
            opening_fingerprint = checkpoint.opening_week_fingerprint
            predecessor = checkpoint.fingerprint
        slot_start = fingerprint(
            {
                "run_id": run_id,
                "branch_id": branch_id,
                "week": week.model_dump(mode="json"),
                "ordinal": ordinal,
                "predecessor": predecessor,
                "players": [p.model_dump(mode="json") for p in players],
            }
        )
        plan = SimulationSlotPlan(
            run_id=run_id,
            branch_id=branch_id,
            week=week,
            slot_id=slot_id,
            ordinal=ordinal,
            ordered_dependency_ids=dependency_ids,
            group_ids=tuple(sorted(group_ids)),
            match_events=tuple(sorted(match_events, key=lambda item: item.group_id)),
            slot_start_fingerprint=slot_start,
            provenance="topological tournament-match scheduler; slot is not a draw position",
        )
        initial = PlayerSportingCheckpoint(
            run_id=run_id,
            branch_id=branch_id,
            week=week,
            slot_id=slot_id,
            slot_ordinal=ordinal,
            opening_week_fingerprint=opening_fingerprint,
            slot_start_fingerprint=slot_start,
            predecessor_checkpoint_fingerprint=predecessor,
            applied_effect_fingerprints=(),
            players=players,
        )
        self.session.add(
            SimulationSlotModel(
                run_id=run_id,
                branch_id=branch_id,
                week_ordinal=week.ordinal,
                slot_id=slot_id,
                slot_ordinal=ordinal,
                plan_fingerprint=plan.fingerprint,
                slot_start_fingerprint=slot_start,
                status="pending",
                payload_json=plan.model_dump_json(),
                slot_start_checkpoint_json=initial.model_dump_json(),
                terminal_checkpoint_json=initial.model_dump_json(),
            )
        )
        self.session.flush()
        return plan

    def execute_match_group(
        self,
        *,
        run_id: str,
        branch_id: str,
        week: RankingWeek,
        slot_id: str,
        group_id: str,
        event_id: str,
        match_id: str,
        player_a_id: str,
        player_b_id: str,
        seed: int,
        expected_slot_start_fingerprint: str,
        projection_policy: CanonicalMatchInputProjectionPolicy | None = None,
        effects_policy: MatchSportingEffectsPolicy | None = None,
        fault_at: str | None = None,
    ) -> AuthoritativeGroupResult:
        projection_policy = projection_policy or CanonicalMatchInputProjectionPolicy()
        effects_policy = effects_policy or MatchSportingEffectsPolicy()
        slot = self._get_slot(run_id, branch_id, week, slot_id)
        plan = self._load_plan(slot)
        if group_id not in plan.group_ids:
            raise ValueError("event group is not included in the slot plan")
        event_plan = next(
            item for item in plan.match_events if item.group_id == group_id
        )
        if (event_id, match_id) != (event_plan.event_id, event_plan.match_id):
            raise ValueError("execution event/match identity differs from slot plan")
        if event_plan.direct_player_ids is not None:
            expected_players = event_plan.direct_player_ids
        else:
            feeder_rows = [
                self.session.scalar(
                    select(SimulationEventGroupModel).where(
                        SimulationEventGroupModel.run_id == run_id,
                        SimulationEventGroupModel.branch_id == branch_id,
                        SimulationEventGroupModel.week_ordinal == week.ordinal,
                        SimulationEventGroupModel.group_id == feeder_id,
                    )
                )
                for feeder_id in event_plan.feeder_group_ids or ()
            ]
            if len(feeder_rows) != 2 or any(row is None for row in feeder_rows):
                raise ValueError("planned feeder groups are incomplete")
            expected_players = tuple(
                self._load_group(row).result.winner_player_id for row in feeder_rows
            )
        if (player_a_id, player_b_id) != expected_players:
            raise ValueError(
                "execution participants differ from authoritative match plan"
            )
        if expected_slot_start_fingerprint != plan.slot_start_fingerprint:
            raise ValueError("slot-start fingerprint changed; retry conflicts")
        command = fingerprint(
            {
                "scope": [run_id, branch_id, week.ordinal, slot_id, group_id, match_id],
                "slot_start": expected_slot_start_fingerprint,
                "event_id": event_id,
                "players": [player_a_id, player_b_id],
                "seed": seed,
                "engine": MATCH_ENGINE_VERSION,
                "projection": projection_policy.fingerprint,
                "effects": effects_policy.fingerprint,
            }
        )
        existing = self.session.get(
            SimulationEventGroupModel,
            (run_id, branch_id, week.ordinal, slot_id, group_id),
        )
        if existing:
            if existing.command_fingerprint != command:
                raise ValueError(
                    "completed event group command conflicts with exact receipt"
                )
            return self._load_group(existing, exact_retry=True)
        frozen = self._load_slot_start(slot)
        players = {p.player_id: p for p in frozen.players}
        world = get_initial_world(self.session, run_id=run_id, branch_id=branch_id)
        lifecycle = get_lifecycle(
            self.session, run_id=run_id, branch_id=branch_id, week=week
        )
        if world is None or lifecycle is None:
            raise ValueError(
                "authoritative InitialWorld profile and lifecycle sources are required"
            )
        profiles = {player.player_id: player for player in world.players}
        lifecycle_players = {player.player_id: player for player in lifecycle.players}
        try:
            a, b = players[player_a_id], players[player_b_id]
        except KeyError as exc:
            raise ValueError(
                "match participant is absent from frozen slot-start state"
            ) from exc

        def projection(record):
            try:
                profile = profiles[record.player_id]
                life = lifecycle_players[record.player_id]
            except KeyError as exc:
                raise ValueError(
                    "match participant lacks owned profile or lifecycle truth"
                ) from exc
            return project_player(
                record,
                source_sporting_fingerprint=plan.slot_start_fingerprint,
                policy=projection_policy,
                profile_source_fingerprint=profile.source_generation_fingerprint,
                profile_provenance=(
                    f"owned InitialWorld {world.fingerprint}; career-style evolution unsupported"
                ),
                age=life.age,
                name=profile.name,
                nationality=profile.nationality,
                play_style=profile.play_style,
                archetype=profile.archetype,
                hidden_career_traits=profile.hidden_career_traits,
            )

        projections = (projection(a), projection(b))
        engine_players = tuple(projected_engine_player(p) for p in projections)
        context = MatchContext(
            match_id=match_id,
            player_a=MatchParticipantContext(
                player=engine_players[0],
                form_modifier=projections[0].form_modifier,
                sharpness_modifier=projections[0].sharpness_modifier,
                fatigue_modifier=projections[0].fatigue_modifier,
            ),
            player_b=MatchParticipantContext(
                player=engine_players[1],
                form_modifier=projections[1].form_modifier,
                sharpness_modifier=projections[1].sharpness_modifier,
                fatigue_modifier=projections[1].fatigue_modifier,
            ),
        )
        engine_input = MatchInputSnapshot.create(
            context=context,
            effective_match_format=official_match_format_snapshot(),
            simulation_seed=seed,
            match_engine_version=MATCH_ENGINE_VERSION,
            rally_calibration_profile=RallyCalibrationProfile(),
        )
        protected = AuthoritativeMatchInput(
            run_id=run_id,
            branch_id=branch_id,
            week=week,
            slot_id=slot_id,
            slot_start_fingerprint=plan.slot_start_fingerprint,
            group_id=group_id,
            event_id=event_id,
            match_id=match_id,
            player_projections=projections,
            engine_input=engine_input,
        )
        result = MatchEngine(rng=DeterministicRng(seed)).simulate(
            engine_input.context,
            log_anchor_hash=engine_input.snapshot_hash,
            effective_match_timing=engine_input.effective_match_timing,
            effective_match_stamina=engine_input.effective_match_stamina,
            rally_calibration_profile=engine_input.rally_calibration_profile,
            effective_match_gameplans=engine_input.effective_match_gameplans,
            effective_rally_rules=engine_input.effective_rally_rules,
        )
        result_fp = fingerprint(
            {"input": protected.fingerprint, "result": result.model_dump(mode="json")}
        )
        if fault_at == "after_match_staging":
            raise RuntimeError("fault after match staging")
        effects = calculate_match_effects(
            protected, result, result_fingerprint=result_fp, policy=effects_policy
        )
        if fault_at == "after_effect_staging":
            raise RuntimeError("fault after effect staging")
        payload = {
            "authoritative_input": protected.model_dump(mode="json"),
            "result": result.model_dump(mode="json"),
            "result_fingerprint": result_fp,
            "effects": [effect.model_dump(mode="json") for effect in effects],
            "effects_policy": effects_policy.model_dump(mode="json"),
        }
        row = SimulationEventGroupModel(
            run_id=run_id,
            branch_id=branch_id,
            week_ordinal=week.ordinal,
            slot_id=slot_id,
            group_id=group_id,
            command_fingerprint=command,
            match_id=match_id,
            match_input_fingerprint=protected.fingerprint,
            result_fingerprint=result_fp,
            payload_json=json.dumps(payload, sort_keys=True, separators=(",", ":")),
        )
        if fault_at == "before_group_commit":
            raise RuntimeError("fault before group commit")
        self.session.add(row)
        self.session.flush()
        terminal = self._rebuild_terminal(slot)
        return AuthoritativeGroupResult(protected, result, result_fp, effects, terminal)

    def replay(
        self,
        *,
        run_id: str,
        branch_id: str,
        week: RankingWeek,
        slot_id: str,
        group_id: str,
    ):
        row = self.session.get(
            SimulationEventGroupModel,
            (run_id, branch_id, week.ordinal, slot_id, group_id),
        )
        if row is None:
            raise ValueError("authoritative event group was not found")
        return self._load_group(row)

    def terminal_checkpoint(self, *, run_id: str, branch_id: str, week: RankingWeek):
        slots = self.session.scalars(
            select(SimulationSlotModel)
            .where(
                SimulationSlotModel.run_id == run_id,
                SimulationSlotModel.branch_id == branch_id,
                SimulationSlotModel.week_ordinal == week.ordinal,
            )
            .order_by(SimulationSlotModel.slot_ordinal)
        ).all()
        if not slots:
            return None
        if any(slot.status != "complete" for slot in slots):
            raise ValueError(
                "completed week requires every planned slot to be complete"
            )
        return self._load_checkpoint(slots[-1])

    def _rebuild_terminal(self, slot: SimulationSlotModel) -> PlayerSportingCheckpoint:
        initial = self._load_slot_start(slot)
        rows = self.session.scalars(
            select(SimulationEventGroupModel)
            .where(
                SimulationEventGroupModel.run_id == slot.run_id,
                SimulationEventGroupModel.branch_id == slot.branch_id,
                SimulationEventGroupModel.week_ordinal == slot.week_ordinal,
                SimulationEventGroupModel.slot_id == slot.slot_id,
            )
            .order_by(SimulationEventGroupModel.group_id)
        ).all()
        effects = []
        for row in rows:
            effects.extend(self._load_group(row).effects)
        by_player = {p.player_id: p for p in initial.players}
        for effect in sorted(effects, key=lambda item: (item.player_id, item.group_id)):
            player = by_player[effect.player_id]
            if (
                player.current_form,
                player.match_sharpness,
                player.long_term_fatigue,
            ) != (
                effect.form_before,
                effect.sharpness_before,
                effect.fatigue_before,
            ):
                raise ValueError(
                    "same-slot groups conflict on one player's frozen sporting input"
                )
            by_player[effect.player_id] = player.model_copy(
                update={
                    "current_form": effect.form_after,
                    "match_sharpness": effect.sharpness_after,
                    "long_term_fatigue": effect.fatigue_after,
                }
            )
        terminal = initial.model_copy(
            update={
                "applied_effect_fingerprints": tuple(
                    sorted(e.fingerprint for e in effects)
                ),
                "players": tuple(
                    by_player[player_id] for player_id in sorted(by_player)
                ),
            }
        )
        slot.terminal_checkpoint_json = terminal.model_dump_json()
        plan = self._load_plan(slot)
        slot.status = (
            "complete"
            if {row.group_id for row in rows} == set(plan.group_ids)
            else "in_progress"
        )
        self.session.flush()
        return terminal

    @staticmethod
    def _load_group(row, exact_retry: bool = False) -> AuthoritativeGroupResult:
        payload = json.loads(row.payload_json)
        protected = AuthoritativeMatchInput.model_validate_json(
            json.dumps(payload["authoritative_input"])
        )
        result = MatchResult.model_validate(payload["result"])
        effects = tuple(
            PlayerMatchSportingEffect.model_validate_json(json.dumps(value))
            for value in payload["effects"]
        )
        if len(effects) != 2:
            raise ValueError("authoritative competitive match requires two effects")
        paired_effects = cast(
            tuple[PlayerMatchSportingEffect, PlayerMatchSportingEffect], effects
        )
        recomputed_result_fingerprint = fingerprint(
            {
                "input": protected.fingerprint,
                "result": result.model_dump(mode="json"),
            }
        )
        if (
            protected.fingerprint != row.match_input_fingerprint
            or payload["result_fingerprint"] != row.result_fingerprint
            or recomputed_result_fingerprint != row.result_fingerprint
        ):
            raise ValueError("persisted match input/result fingerprint mismatch")
        if (
            protected.run_id,
            protected.branch_id,
            protected.week.ordinal,
            protected.slot_id,
            protected.group_id,
            protected.match_id,
        ) != (
            row.run_id,
            row.branch_id,
            row.week_ordinal,
            row.slot_id,
            row.group_id,
            row.match_id,
        ) or result.match_id != protected.match_id:
            raise ValueError("persisted authoritative group scope or match mismatch")
        if any(
            effect.match_input_fingerprint != protected.fingerprint
            or effect.authoritative_result_fingerprint != row.result_fingerprint
            for effect in paired_effects
        ):
            raise ValueError("persisted match/effect evidence mismatch")
        projections = {item.player_id: item for item in protected.player_projections}
        try:
            policy = MatchSportingEffectsPolicy.model_validate_json(
                json.dumps(payload["effects_policy"])
            )
        except (KeyError, ValueError) as exc:
            raise ValueError(
                "persisted match effects policy is missing or corrupt"
            ) from exc
        if any(
            effect.player_id not in projections
            or effect.pre_match_sporting_fingerprint != protected.slot_start_fingerprint
            or effect.policy_id != policy.policy_id
            or effect.policy_fingerprint != policy.fingerprint
            or (
                effect.form_before,
                effect.sharpness_before,
                effect.fatigue_before,
            )
            != (
                projections[effect.player_id].current_form,
                projections[effect.player_id].match_sharpness,
                projections[effect.player_id].long_term_fatigue,
            )
            or effect.form_after
            != min(
                policy.form_max,
                max(policy.form_min, effect.form_before + effect.form_delta),
            )
            or effect.sharpness_after
            != min(
                policy.sharpness_max,
                max(
                    policy.sharpness_min,
                    effect.sharpness_before + effect.sharpness_delta,
                ),
            )
            or effect.fatigue_after
            != min(
                policy.fatigue_max,
                max(policy.fatigue_min, effect.fatigue_before + effect.fatigue_delta),
            )
            for effect in paired_effects
        ):
            raise ValueError("persisted match effect semantics are corrupt")
        # The caller reads the current validated slot head separately; replay never reads player state.
        terminal = PlayerSportingCheckpoint(
            run_id=protected.run_id,
            branch_id=protected.branch_id,
            week=protected.week,
            slot_id=protected.slot_id,
            slot_ordinal=0,
            opening_week_fingerprint=protected.slot_start_fingerprint,
            slot_start_fingerprint=protected.slot_start_fingerprint,
            predecessor_checkpoint_fingerprint=None,
            applied_effect_fingerprints=tuple(
                sorted(e.fingerprint for e in paired_effects)
            ),
            players=(),
        )
        return AuthoritativeGroupResult(
            protected,
            result,
            row.result_fingerprint,
            paired_effects,
            terminal,
            exact_retry,
        )

    def _get_slot(self, run_id, branch_id, week, slot_id):
        row = self.session.get(
            SimulationSlotModel, (run_id, branch_id, week.ordinal, slot_id)
        )
        if row is None:
            raise ValueError("simulation slot was not found")
        return row

    @staticmethod
    def _load_plan(row):
        plan = SimulationSlotPlan.model_validate_json(row.payload_json)
        if (
            plan.fingerprint != row.plan_fingerprint
            or plan.slot_start_fingerprint != row.slot_start_fingerprint
        ):
            raise ValueError("simulation slot plan fingerprint mismatch")
        return plan

    @staticmethod
    def _load_checkpoint(row):
        if row.terminal_checkpoint_json is None:
            raise ValueError("simulation slot sporting checkpoint is missing")
        return PlayerSportingCheckpoint.model_validate_json(
            row.terminal_checkpoint_json
        )

    @staticmethod
    def _load_slot_start(row):
        checkpoint = PlayerSportingCheckpoint.model_validate_json(
            row.slot_start_checkpoint_json
        )
        if checkpoint.slot_start_fingerprint != row.slot_start_fingerprint:
            raise ValueError("simulation slot-start checkpoint fingerprint mismatch")
        return checkpoint
