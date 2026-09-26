"""Authoritative Simulation Slot bridge for true persisted Next Rally commands."""

from __future__ import annotations

import json

from sqlalchemy import select

from beta_engine.domain.matches import (
    MatchContext,
    MatchInputSnapshot,
    MatchParticipantContext,
    RallyCalibrationProfile,
    official_match_format_snapshot,
)
from beta_engine.domain.matches.models import MatchResult
from beta_engine.domain.simulation_slots import (
    AuthoritativeMatchInput,
    CanonicalMatchInputProjectionPolicy,
    MatchSportingEffectsPolicy,
    calculate_match_effects,
    fingerprint,
    project_player,
    projected_engine_player,
)
from beta_engine.application.authoritative_slot_matches import (
    AuthoritativeGroupResult,
    AuthoritativeSlotMatchExecutor,
    MATCH_ENGINE_VERSION,
)
from beta_engine.infrastructure.db.initial_world_state import get_initial_world
from beta_engine.infrastructure.db.live_match_state import PersistedLiveMatchStore
from beta_engine.infrastructure.db.models import (
    AuthoritativeLiveMatchModel,
    LiveMatchWorkingModel,
    SimulationEventGroupModel,
)
from beta_engine.infrastructure.db.player_lifecycle_state import get_lifecycle


class AuthoritativeLiveMatchService:
    """Start/advance one canonical Simulation Slot match one rally at a time."""

    def __init__(self, session):
        self.session = session

    @staticmethod
    def _key(
        *,
        run_id: str,
        branch_id: str,
        week_ordinal: int,
        slot_id: str,
        group_id: str,
    ):
        return run_id, branch_id, week_ordinal, slot_id, group_id

    def ensure_started(
        self,
        *,
        run_id: str,
        branch_id: str,
        week,
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
    ) -> dict:
        """Freeze the exact authoritative input used by the normal full-match path."""

        projection_policy = projection_policy or CanonicalMatchInputProjectionPolicy()
        effects_policy = effects_policy or MatchSportingEffectsPolicy()
        executor = AuthoritativeSlotMatchExecutor(self.session)
        slot = executor._get_slot(run_id, branch_id, week, slot_id)
        plan = executor._load_plan(slot)
        if expected_slot_start_fingerprint != plan.slot_start_fingerprint:
            raise ValueError("slot-start fingerprint changed; live retry conflicts")
        if group_id not in plan.group_ids:
            raise ValueError("event group is not included in the slot plan")
        event_plan = next(item for item in plan.match_events if item.group_id == group_id)
        if (event_id, match_id) != (event_plan.event_id, event_plan.match_id):
            raise ValueError("live event/match identity differs from slot plan")

        frozen = executor._load_slot_start(slot)
        players = {p.player_id: p for p in frozen.players}
        try:
            a, b = players[player_a_id], players[player_b_id]
        except KeyError as exc:
            raise ValueError("live match participant is absent from frozen slot-start state") from exc

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

        def projection(record):
            try:
                profile = profiles[record.player_id]
                life = lifecycle_players[record.player_id]
            except KeyError as exc:
                raise ValueError(
                    "live match participant lacks owned profile or lifecycle truth"
                ) from exc
            if life.status != "active":
                raise ValueError("supported competitive match requires active lifecycle players")
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
        execution_fp = fingerprint(
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

        key = self._key(
            run_id=run_id,
            branch_id=branch_id,
            week_ordinal=week.ordinal,
            slot_id=slot_id,
            group_id=group_id,
        )
        existing = self.session.get(AuthoritativeLiveMatchModel, key)
        if existing is not None:
            if (
                existing.match_id != match_id
                or existing.authoritative_input_fingerprint != protected.fingerprint
                or existing.authoritative_input_json != protected.model_dump_json()
                or existing.execution_command_fingerprint != execution_fp
                or existing.effects_policy_json != effects_policy.model_dump_json()
            ):
                raise ValueError("live authoritative match identity conflicts with frozen input")
        else:
            self.session.add(
                AuthoritativeLiveMatchModel(
                    run_id=run_id,
                    branch_id=branch_id,
                    week_ordinal=week.ordinal,
                    slot_id=slot_id,
                    group_id=group_id,
                    match_id=match_id,
                    authoritative_input_fingerprint=protected.fingerprint,
                    authoritative_input_json=protected.model_dump_json(),
                    execution_command_fingerprint=execution_fp,
                    effects_policy_json=effects_policy.model_dump_json(),
                )
            )
            self.session.flush()

        working_row = self.session.get(LiveMatchWorkingModel, key)
        if working_row is not None and working_row.status == "complete":
            return {
                "authoritative_input_fingerprint": protected.fingerprint,
                "state_fingerprint": None,
                "match_id": match_id,
                "complete": True,
            }

        state = PersistedLiveMatchStore(self.session).start_from_engine_input(
            run_id=run_id,
            branch_id=branch_id,
            week_ordinal=week.ordinal,
            slot_id=slot_id,
            group_id=group_id,
            engine_input=engine_input,
        )
        return {
            "authoritative_input_fingerprint": protected.fingerprint,
            "state_fingerprint": state.fingerprint,
            "match_id": match_id,
            "complete": False,
        }

    def simulate_next_rally(
        self,
        *,
        run_id: str,
        branch_id: str,
        week,
        slot_id: str,
        group_id: str,
        command_id: str,
        expected_state_fingerprint: str,
    ) -> dict:
        key = self._key(
            run_id=run_id,
            branch_id=branch_id,
            week_ordinal=week.ordinal,
            slot_id=slot_id,
            group_id=group_id,
        )
        authority = self.session.get(AuthoritativeLiveMatchModel, key)
        if authority is None:
            raise ValueError("authoritative live match has not been started")

        step = PersistedLiveMatchStore(self.session).simulate_next_rally(
            run_id=run_id,
            branch_id=branch_id,
            week_ordinal=week.ordinal,
            slot_id=slot_id,
            group_id=group_id,
            command_id=command_id,
            expected_state_fingerprint=expected_state_fingerprint,
        )
        if step["status"] != "complete":
            return {**step, "authoritative_group_committed": False}

        existing_group = self.session.get(
            SimulationEventGroupModel,
            (run_id, branch_id, week.ordinal, slot_id, group_id),
        )
        if existing_group is not None:
            if existing_group.command_fingerprint != authority.execution_command_fingerprint:
                raise ValueError("completed live group conflicts with stored execution authority")
            return {
                **step,
                "authoritative_group_committed": True,
                "authoritative_result_fingerprint": existing_group.result_fingerprint,
            }

        protected = AuthoritativeMatchInput.model_validate_json(
            authority.authoritative_input_json
        )
        if protected.fingerprint != authority.authoritative_input_fingerprint:
            raise ValueError("persisted authoritative live input fingerprint is corrupt")
        effects_policy = MatchSportingEffectsPolicy.model_validate_json(
            authority.effects_policy_json
        )
        result = MatchResult.model_validate(step["final_result"])
        result_fp = fingerprint(
            {"input": protected.fingerprint, "result": result.model_dump(mode="json")}
        )
        effects = calculate_match_effects(
            protected, result, result_fingerprint=result_fp, policy=effects_policy
        )
        payload = {
            "authoritative_input": protected.model_dump(mode="json"),
            "result": result.model_dump(mode="json"),
            "result_fingerprint": result_fp,
            "effects": [effect.model_dump(mode="json") for effect in effects],
            "effects_policy": effects_policy.model_dump(mode="json"),
        }
        self.session.add(
            SimulationEventGroupModel(
                run_id=run_id,
                branch_id=branch_id,
                week_ordinal=week.ordinal,
                slot_id=slot_id,
                group_id=group_id,
                command_fingerprint=authority.execution_command_fingerprint,
                match_id=protected.match_id,
                match_input_fingerprint=protected.fingerprint,
                result_fingerprint=result_fp,
                payload_json=json.dumps(payload, sort_keys=True, separators=(",", ":")),
            )
        )
        self.session.flush()
        terminal = AuthoritativeSlotMatchExecutor(self.session)._rebuild_terminal(
            AuthoritativeSlotMatchExecutor(self.session)._get_slot(
                run_id, branch_id, week, slot_id
            )
        )
        return {
            **step,
            "authoritative_group_committed": True,
            "authoritative_result_fingerprint": result_fp,
            "terminal_checkpoint_fingerprint": terminal.fingerprint,
        }

    def inspect(
        self,
        *,
        run_id: str,
        branch_id: str,
        week,
        slot_id: str,
        group_id: str,
    ) -> dict:
        key = self._key(
            run_id=run_id,
            branch_id=branch_id,
            week_ordinal=week.ordinal,
            slot_id=slot_id,
            group_id=group_id,
        )
        authority = self.session.get(AuthoritativeLiveMatchModel, key)
        if authority is None:
            raise ValueError("authoritative live match has not been started")
        working = PersistedLiveMatchStore(self.session).inspect(
            run_id=run_id,
            branch_id=branch_id,
            week_ordinal=week.ordinal,
            slot_id=slot_id,
            group_id=group_id,
        )
        group = self.session.get(
            SimulationEventGroupModel,
            (run_id, branch_id, week.ordinal, slot_id, group_id),
        )
        return {
            **working,
            "authoritative_input_fingerprint": authority.authoritative_input_fingerprint,
            "authoritative_group_committed": group is not None,
            "authoritative_result_fingerprint": (
                group.result_fingerprint if group is not None else None
            ),
        }
