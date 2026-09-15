"""Run/Branch-owned orchestration over the authoritative Simulation Slot ledger.

This intentionally supports only the persisted four-player Main Draw bridge.  It
does not mutate, or use as execution state, the legacy match/result/award files.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Literal

from pydantic import Field
from sqlalchemy import select, text
from sqlalchemy.orm import Session, sessionmaker

from beta_engine.application.authoritative_slot_matches import (
    AuthoritativeFourPlayerTournamentResult,
    AuthoritativeSlotMatchExecutor,
    build_authoritative_tournament_ranking_packages,
)
from beta_engine.application.ranking_tournament_ingestion import (
    TournamentRankingBinding,
    prepare_tournament_ranking_sources,
)
from beta_engine.application.season_match_service import SeasonMatchService
from beta_engine.application.season_point_awards_service import SeasonPointAwardsService
from beta_engine.domain.rankings.official import FrozenInput, RankingWeek
from beta_engine.domain.rankings.tournament_source import OwnedTournamentRankingSource
from beta_engine.domain.simulation_slots import SimulationMatchEventPlan, fingerprint
from beta_engine.infrastructure.db.models import (
    AuthoritativeSimulationCommandModel,
    AuthoritativeWorldStateModel,
    PlayerSportingWeekStateModel,
    RunBranchModel,
    SimulationEventGroupModel,
    SimulationSlotModel,
)
from beta_engine.infrastructure.db.owned_tournament_sources import (
    OwnedTournamentRankingSourceStore,
)


class AuthoritativeSimulationCommand(FrozenInput):
    command_id: str = Field(min_length=1, max_length=128)
    run_id: str
    branch_id: str
    expected_week: RankingWeek
    expected_position_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    expected_revision_id: str = Field(min_length=1)
    group_id: str | None = None

    @property
    def fingerprint(self) -> str:
        return fingerprint(self.model_dump(mode="json"))


class AuthoritativeSimulationPosition(FrozenInput):
    run_id: str
    branch_id: str
    current_week: RankingWeek
    current_slot_id: str | None
    slot_ordinal: int | None
    unresolved_group_ids: tuple[str, ...]
    eligible_match_ids: tuple[str, ...]
    blocked_match_ids: tuple[str, ...]
    current_slot_complete: bool
    supported_tournament_complete: bool
    week_ready_for_transition: bool
    terminal_sporting_fingerprint: str | None
    position_fingerprint: str


@dataclass(slots=True)
class AuthoritativeRunSimulationDriver:
    factory: sessionmaker[Session]
    match_service: SeasonMatchService
    awards_service: SeasonPointAwardsService

    def position(
        self, *, run_id: str, branch_id: str
    ) -> AuthoritativeSimulationPosition:
        with self.factory() as session:
            return self._position(session, run_id, branch_id)

    def simulate_next_match(self, command: AuthoritativeSimulationCommand):
        return self._mutate(command, mode="match")

    def simulate_next_slot(
        self, command: AuthoritativeSimulationCommand, *, fault_at: str | None = None
    ):
        return self._mutate(command, mode="slot", fault_at=fault_at)

    def _mutate(self, command, *, mode: Literal["match", "slot"], fault_at=None):
        request_fp = fingerprint(
            {"mode": mode, "command": command.model_dump(mode="json")}
        )
        with self.factory.begin() as session:
            session.execute(text("BEGIN IMMEDIATE"))
            key = (command.run_id, command.branch_id, command.command_id)
            receipt = session.get(AuthoritativeSimulationCommandModel, key)
            if receipt:
                if receipt.request_fingerprint != request_fp:
                    raise ValueError(
                        "simulation command ID already has a different request"
                    )
                return json.loads(receipt.result_json)
            before = self._position(session, command.run_id, command.branch_id)
            if before.current_week != command.expected_week:
                raise ValueError("expected current week is stale")
            if before.position_fingerprint != command.expected_position_fingerprint:
                raise ValueError("simulation position is stale")
            branch = session.get(RunBranchModel, command.branch_id)
            if (
                branch is None
                or branch.run_id != command.run_id
                or branch.saved_head_revision_id != command.expected_revision_id
            ):
                raise ValueError("expected Branch head is stale")
            package = self._package(before.current_week)
            self._ensure_current_slot(session, command, package)
            position = self._position(session, command.run_id, command.branch_id)
            eligible_groups = self._eligible_groups(session, position, package)
            if mode == "match":
                if command.group_id is None:
                    if len(eligible_groups) != 1:
                        raise ValueError(
                            "an explicit current-slot group_id is required"
                        )
                    targets = eligible_groups
                elif command.group_id not in eligible_groups:
                    raise ValueError(
                        "target is completed, blocked, or outside the current slot"
                    )
                else:
                    targets = (command.group_id,)
            else:
                if command.group_id is not None:
                    raise ValueError("Simulate Next Slot does not accept group_id")
                targets = eligible_groups
            if not targets:
                raise ValueError("current slot has no unresolved eligible match")
            for index, group_id in enumerate(targets):
                if fault_at == "before_second_group" and index == 1:
                    raise RuntimeError("fault before second group")
                self._execute_group(session, command, package, group_id)
                if fault_at == "after_first_group" and index == 0:
                    # This exception rolls back the current transaction. Production callers
                    # commit each group through separate commands when partial progress matters.
                    raise RuntimeError("fault after first group")
            self._advance_or_close(session, command, package, fault_at=fault_at)
            after = self._position(session, command.run_id, command.branch_id)
            payload = after.model_dump(mode="json")
            session.add(
                AuthoritativeSimulationCommandModel(
                    run_id=command.run_id,
                    branch_id=command.branch_id,
                    command_id=command.command_id,
                    request_fingerprint=request_fp,
                    result_json=json.dumps(
                        payload, sort_keys=True, separators=(",", ":")
                    ),
                )
            )
            if fault_at == "after_source_staging_before_receipt":
                raise RuntimeError(
                    "fault after ranking source staging before command receipt"
                )
            session.flush()
            return payload

    def _current_week(self, session, run_id, branch_id):
        world = session.get(AuthoritativeWorldStateModel, (run_id, branch_id))
        if world:
            return RankingWeek(
                season_index=world.current_ordinal // 61,
                week=world.current_ordinal % 61 + 1,
            )
        rows = session.execute(
            select(PlayerSportingWeekStateModel.week_ordinal)
            .where(
                PlayerSportingWeekStateModel.run_id == run_id,
                PlayerSportingWeekStateModel.branch_id == branch_id,
            )
            .order_by(PlayerSportingWeekStateModel.week_ordinal.desc())
        ).first()
        if not rows:
            raise ValueError("authoritative sporting week state is missing")
        ordinal = rows[0]
        return RankingWeek(season_index=ordinal // 61, week=ordinal % 61 + 1)

    def _package(self, week):
        candidates = [
            p
            for p in self.match_service._load_registry().matches_by_event_id.values()
            if p.season_week == week.week and len(p.main_draw_matches) == 3
        ]
        if len(candidates) != 1:
            raise ValueError(
                "current week requires exactly one supported persisted four-player Main Draw"
            )
        package = candidates[0].model_copy(deep=True)
        # Qualification is deliberately outside this bridge.  It is not execution
        # state and is never written back to the legacy registry.
        package.qualification_matches = []
        return package

    def _position(self, session, run_id, branch_id):
        week = self._current_week(session, run_id, branch_id)
        package = self._package(week)
        slots = session.scalars(
            select(SimulationSlotModel)
            .where(
                SimulationSlotModel.run_id == run_id,
                SimulationSlotModel.branch_id == branch_id,
                SimulationSlotModel.week_ordinal == week.ordinal,
            )
            .order_by(SimulationSlotModel.slot_ordinal)
        ).all()
        current = next((s for s in slots if s.status != "complete"), None)
        executor = AuthoritativeSlotMatchExecutor(session)
        groups = session.scalars(
            select(SimulationEventGroupModel).where(
                SimulationEventGroupModel.run_id == run_id,
                SimulationEventGroupModel.branch_id == branch_id,
                SimulationEventGroupModel.week_ordinal == week.ordinal,
            )
        ).all()
        done = {g.group_id for g in groups}
        matches = sorted(
            package.main_draw_matches,
            key=lambda m: (m.round_number, m.bracket_position),
        )
        sf_ids = tuple(m.match_id for m in matches[:2])
        final_id = matches[2].match_id
        if current:
            plan = executor._load_plan(current)
            unresolved = tuple(g for g in plan.group_ids if g not in done)
            eligible = tuple(
                e.match_id
                for e in plan.match_events
                if e.group_id in unresolved and set(e.feeder_group_ids or ()) <= done
            )
            blocked = tuple(
                e.match_id
                for e in plan.match_events
                if e.group_id in unresolved
                and not set(e.feeder_group_ids or ()) <= done
            )
            if current.slot_ordinal == 1:
                blocked += (final_id,)
        elif not slots:
            unresolved, eligible, blocked = sf_ids, sf_ids, (final_id,)
        elif len(slots) == 1 and slots[0].status == "complete":
            unresolved, eligible, blocked = (final_id,), (final_id,), ()
        else:
            unresolved = eligible = blocked = ()
        owned = OwnedTournamentRankingSourceStore(session).get(
            run_id=run_id, branch_id=branch_id, edition_id=package.event_id
        )
        terminal = (
            executor.terminal_checkpoint(run_id=run_id, branch_id=branch_id, week=week)
            if slots and all(s.status == "complete" for s in slots)
            else None
        )
        ready = bool(owned and terminal and not unresolved)
        body = {
            "scope": [run_id, branch_id, week.ordinal],
            "slots": [
                (s.slot_id, s.status, s.plan_fingerprint, s.terminal_checkpoint_json)
                for s in slots
            ],
            "groups": [
                (g.group_id, g.command_fingerprint, g.result_fingerprint)
                for g in sorted(groups, key=lambda x: x.group_id)
            ],
            "owned": owned.fingerprint if owned else None,
        }
        return AuthoritativeSimulationPosition(
            run_id=run_id,
            branch_id=branch_id,
            current_week=week,
            current_slot_id=current.slot_id
            if current
            else (f"{package.event_id}:slot:{len(slots) + 1}" if not ready else None),
            slot_ordinal=current.slot_ordinal
            if current
            else (len(slots) + 1 if not ready else None),
            unresolved_group_ids=unresolved,
            eligible_match_ids=eligible,
            blocked_match_ids=blocked,
            current_slot_complete=not unresolved,
            supported_tournament_complete=owned is not None,
            week_ready_for_transition=ready,
            terminal_sporting_fingerprint=terminal.fingerprint if terminal else None,
            position_fingerprint=fingerprint(body),
        )

    def _ensure_current_slot(self, session, command, package):
        pos = self._position(session, command.run_id, command.branch_id)
        if any(
            s.status != "complete"
            for s in session.scalars(
                select(SimulationSlotModel).where(
                    SimulationSlotModel.run_id == command.run_id,
                    SimulationSlotModel.branch_id == command.branch_id,
                    SimulationSlotModel.week_ordinal == command.expected_week.ordinal,
                )
            ).all()
        ):
            return
        matches = sorted(
            package.main_draw_matches,
            key=lambda m: (m.round_number, m.bracket_position),
        )
        executor = AuthoritativeSlotMatchExecutor(session)
        if pos.current_slot_id is None:
            raise ValueError("there is no current slot to materialize")
        if pos.slot_ordinal == 1:
            plans = tuple(
                SimulationMatchEventPlan(
                    group_id=m.match_id,
                    event_id=package.event_id,
                    match_id=m.match_id,
                    direct_player_ids=(m.top_player_id, m.bottom_player_id),
                )
                for m in matches[:2]
            )
            executor.create_slot(
                run_id=command.run_id,
                branch_id=command.branch_id,
                week=command.expected_week,
                slot_id=pos.current_slot_id,
                ordinal=1,
                group_ids=tuple(p.group_id for p in plans),
                match_events=plans,
                provenance=f"adopted-draw:{package.metadata.build_fingerprint}",
            )
        elif pos.slot_ordinal == 2:
            feeders = tuple(m.match_id for m in matches[:2])
            p = SimulationMatchEventPlan(
                group_id=matches[2].match_id,
                event_id=package.event_id,
                match_id=matches[2].match_id,
                feeder_group_ids=feeders,
            )
            executor.create_slot(
                run_id=command.run_id,
                branch_id=command.branch_id,
                week=command.expected_week,
                slot_id=pos.current_slot_id,
                ordinal=2,
                group_ids=(p.group_id,),
                match_events=(p,),
                dependency_ids=feeders,
                provenance=f"adopted-draw:{package.metadata.build_fingerprint}",
            )

    def _eligible_groups(self, session, position, package):
        slot = session.get(
            SimulationSlotModel,
            (
                position.run_id,
                position.branch_id,
                position.current_week.ordinal,
                position.current_slot_id,
            ),
        )
        plan = AuthoritativeSlotMatchExecutor._load_plan(slot)
        return tuple(
            e.group_id
            for e in plan.match_events
            if e.match_id in position.eligible_match_ids
        )

    def _execute_group(self, session, command, package, group_id):
        slot = session.get(
            SimulationSlotModel,
            (
                command.run_id,
                command.branch_id,
                command.expected_week.ordinal,
                self._position(
                    session, command.run_id, command.branch_id
                ).current_slot_id,
            ),
        )
        plan = AuthoritativeSlotMatchExecutor._load_plan(slot)
        event = next(e for e in plan.match_events if e.group_id == group_id)
        if event.direct_player_ids:
            players = event.direct_player_ids
        else:
            if event.feeder_group_ids is None:
                raise ValueError("dependent match has no feeder plan")
            players = tuple(
                AuthoritativeSlotMatchExecutor._load_group(
                    session.scalar(
                        select(SimulationEventGroupModel).where(
                            SimulationEventGroupModel.run_id == command.run_id,
                            SimulationEventGroupModel.branch_id == command.branch_id,
                            SimulationEventGroupModel.week_ordinal
                            == command.expected_week.ordinal,
                            SimulationEventGroupModel.group_id == f,
                        )
                    )
                ).result.winner_player_id
                for f in event.feeder_group_ids
            )
        seed = int(
            hashlib.sha256(
                f"{command.run_id}|{command.branch_id}|{command.expected_week.ordinal}|{package.metadata.build_fingerprint}|{group_id}".encode()
            ).hexdigest()[:15],
            16,
        )
        AuthoritativeSlotMatchExecutor(session).execute_match_group(
            run_id=command.run_id,
            branch_id=command.branch_id,
            week=command.expected_week,
            slot_id=slot.slot_id,
            group_id=group_id,
            event_id=package.event_id,
            match_id=event.match_id,
            player_a_id=players[0],
            player_b_id=players[1],
            seed=seed,
            expected_slot_start_fingerprint=plan.slot_start_fingerprint,
        )

    def _advance_or_close(self, session, command, package, *, fault_at=None):
        pos = self._position(session, command.run_id, command.branch_id)
        if pos.unresolved_group_ids:
            return
        slots = session.scalars(
            select(SimulationSlotModel)
            .where(
                SimulationSlotModel.run_id == command.run_id,
                SimulationSlotModel.branch_id == command.branch_id,
                SimulationSlotModel.week_ordinal == command.expected_week.ordinal,
            )
            .order_by(SimulationSlotModel.slot_ordinal)
        ).all()
        if len(slots) == 1:
            return
        executor = AuthoritativeSlotMatchExecutor(session)
        matches = sorted(
            package.main_draw_matches,
            key=lambda m: (m.round_number, m.bracket_position),
        )
        loaded = {
            g.group_id: executor._load_group(g)
            for g in session.scalars(
                select(SimulationEventGroupModel).where(
                    SimulationEventGroupModel.run_id == command.run_id,
                    SimulationEventGroupModel.branch_id == command.branch_id,
                    SimulationEventGroupModel.week_ordinal
                    == command.expected_week.ordinal,
                )
            ).all()
        }
        auth = AuthoritativeFourPlayerTournamentResult(
            event_id=package.event_id,
            semifinal_groups=(loaded[matches[0].match_id], loaded[matches[1].match_id]),
            final_group=loaded[matches[2].match_id],
            champion_player_id=loaded[matches[2].match_id].result.winner_player_id,
            match_result_fingerprints=(
                loaded[matches[0].match_id].result_fingerprint,
                loaded[matches[1].match_id].result_fingerprint,
                loaded[matches[2].match_id].result_fingerprint,
            ),
        )
        if fault_at == "after_final_before_source":
            raise RuntimeError(
                "fault after tournament final before ranking source persistence"
            )
        _, result, awards = build_authoritative_tournament_ranking_packages(
            self.awards_service,
            package=package,
            authoritative=auth,
            result_seed=self._stable_seed(package, "result"),
            award_seed=self._stable_seed(package, "awards"),
        )
        binding = TournamentRankingBinding(
            run_id=command.run_id,
            branch_id=command.branch_id,
            edition_id=package.event_id,
            event_id=package.event_id,
            completed_week=command.expected_week,
            first_publication_week=RankingWeek(
                season_index=command.expected_week.season_index,
                week=command.expected_week.week + 1,
            ),
            validity_weeks=61,
            ranking_status="ranked",
            expected_result_fingerprint=result.metadata.build_fingerprint,
            expected_award_fingerprint=awards.metadata.build_fingerprint,
        )
        prepare_tournament_ranking_sources(binding, result, awards)
        OwnedTournamentRankingSourceStore(session).append(
            OwnedTournamentRankingSource(
                binding=binding,
                result=result,
                awards=awards,
                adopted_by_command_id=command.command_id,
            )
        )

    @staticmethod
    def _stable_seed(package, suffix):
        return int(
            hashlib.sha256(
                f"{package.metadata.build_fingerprint}|{suffix}".encode()
            ).hexdigest()[:15],
            16,
        )
