"""Durable Run/Branch-owned state for true rally-by-rally live match simulation."""

from __future__ import annotations

import json

from sqlalchemy import select

from beta_engine.core import DeterministicRng
from beta_engine.domain.matches import (
    MatchEngine,
    MatchInputSnapshot,
    MatchRallyWorkingState,
    MatchWorkingInput,
)
from beta_engine.domain.matches.models import MatchResult
from beta_engine.domain.simulation_slots import fingerprint
from beta_engine.infrastructure.db.models import (
    LiveMatchAlternativePathModel,
    LiveMatchRallyCommandModel,
    LiveMatchReturnPointModel,
    LiveMatchWorkingModel,
)


class PersistedLiveMatchStore:
    """Persist and advance one authoritative match without hidden future simulation."""

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
    ) -> tuple[str, str, int, str, str]:
        return run_id, branch_id, week_ordinal, slot_id, group_id

    def start_from_engine_input(
        self,
        *,
        run_id: str,
        branch_id: str,
        week_ordinal: int,
        slot_id: str,
        group_id: str,
        engine_input: MatchInputSnapshot,
    ) -> MatchRallyWorkingState:
        """Create or reopen the durable pre-next-rally state for one match.

        The immutable effective input comes from the already-frozen authoritative
        MatchInputSnapshot. Exact retries are no-ops; attempting to reuse the same
        Run/Branch/Week/Slot/Group identity with different frozen input fails closed.
        """

        key = self._key(
            run_id=run_id,
            branch_id=branch_id,
            week_ordinal=week_ordinal,
            slot_id=slot_id,
            group_id=group_id,
        )
        row = self.session.get(LiveMatchWorkingModel, key)
        engine = MatchEngine(rng=DeterministicRng(engine_input.simulation_seed))
        working_input, initial_state = engine.start_working_match(
            engine_input.context,
            log_anchor_hash=engine_input.snapshot_hash,
            effective_match_timing=engine_input.effective_match_timing,
            effective_match_stamina=engine_input.effective_match_stamina,
            rally_calibration_profile=engine_input.rally_calibration_profile,
            effective_match_gameplans=engine_input.effective_match_gameplans,
            effective_rally_rules=engine_input.effective_rally_rules,
        )
        if row is not None:
            if (
                row.match_id != engine_input.match_id
                or row.working_input_fingerprint != working_input.fingerprint
                or row.working_input_json != working_input.model_dump_json()
            ):
                raise ValueError(
                    "live-match identity already owns different frozen working input"
                )
            if row.status == "complete":
                raise ValueError("live match is already complete")
            if row.working_state_json is None:
                raise ValueError("active live match has no resumable working state")
            return MatchRallyWorkingState.model_validate_json(row.working_state_json)

        self.session.add(
            LiveMatchWorkingModel(
                run_id=run_id,
                branch_id=branch_id,
                week_ordinal=week_ordinal,
                slot_id=slot_id,
                group_id=group_id,
                match_id=engine_input.match_id,
                working_input_fingerprint=working_input.fingerprint,
                working_input_json=working_input.model_dump_json(),
                state_fingerprint=initial_state.fingerprint,
                working_state_json=initial_state.model_dump_json(),
                status="active",
                final_result_fingerprint=None,
                final_result_json=None,
            )
        )
        self.session.flush()
        return initial_state

    def inspect(
        self,
        *,
        run_id: str,
        branch_id: str,
        week_ordinal: int,
        slot_id: str,
        group_id: str,
    ) -> dict:
        row = self.session.get(
            LiveMatchWorkingModel,
            self._key(
                run_id=run_id,
                branch_id=branch_id,
                week_ordinal=week_ordinal,
                slot_id=slot_id,
                group_id=group_id,
            ),
        )
        if row is None:
            raise ValueError("live match has not been started")
        return self._response(row, idempotent_replay=False)

    @staticmethod
    def _return_point_id(source_command_id: str) -> str:
        return f"return:{source_command_id}"

    def ensure_return_point(
        self,
        *,
        run_id: str,
        branch_id: str,
        week_ordinal: int,
        slot_id: str,
        group_id: str,
        source_command_id: str,
        kind: str,
    ) -> dict:
        """Freeze the current active working state before a multi-rally operation."""

        if kind not in {"game", "rest_of_match"}:
            raise ValueError("return point kind must be game or rest_of_match")
        key = self._key(
            run_id=run_id,
            branch_id=branch_id,
            week_ordinal=week_ordinal,
            slot_id=slot_id,
            group_id=group_id,
        )
        row = self.session.get(LiveMatchWorkingModel, key)
        if row is None or row.status != "active" or row.working_state_json is None:
            raise ValueError("return points require an active live match")
        state = MatchRallyWorkingState.model_validate_json(row.working_state_json)
        if state.fingerprint != row.state_fingerprint:
            raise ValueError("live match state fingerprint is corrupt")

        return_point_id = self._return_point_id(source_command_id)
        point_key = (*key, return_point_id)
        existing = self.session.get(LiveMatchReturnPointModel, point_key)
        if existing is not None:
            if (
                existing.source_command_id != source_command_id
                or existing.kind != kind
                or existing.state_fingerprint != state.fingerprint
                or existing.working_state_json != row.working_state_json
            ):
                raise ValueError("return point identity conflicts with existing snapshot")
            return self._return_point_response(existing)

        point = LiveMatchReturnPointModel(
            run_id=run_id,
            branch_id=branch_id,
            week_ordinal=week_ordinal,
            slot_id=slot_id,
            group_id=group_id,
            return_point_id=return_point_id,
            source_command_id=source_command_id,
            kind=kind,
            state_fingerprint=state.fingerprint,
            working_state_json=row.working_state_json,
            created_from_rally_index=state.rally_index,
            created_from_set_number=state.set_number,
            created_from_games_a=state.games_a,
            created_from_games_b=state.games_b,
            status="available",
            metadata_json="{}",
        )
        self.session.add(point)
        self.session.flush()
        return self._return_point_response(point)

    def ensure_initial_return_point(
        self,
        *,
        run_id: str,
        branch_id: str,
        week_ordinal: int,
        slot_id: str,
        group_id: str,
        source_command_id: str,
        kind: str,
    ) -> dict:
        """Freeze the deterministic pre-first-rally state after live-match bootstrap."""

        if kind not in {"game", "rest_of_match"}:
            raise ValueError("return point kind must be game or rest_of_match")
        key = self._key(
            run_id=run_id,
            branch_id=branch_id,
            week_ordinal=week_ordinal,
            slot_id=slot_id,
            group_id=group_id,
        )
        row = self.session.get(LiveMatchWorkingModel, key)
        if row is None:
            raise ValueError("initial return point requires a bootstrapped live match")
        working_input = MatchWorkingInput.model_validate_json(row.working_input_json)
        engine = MatchEngine(rng=DeterministicRng(working_input.simulation_seed))
        rebuilt_input, initial = engine.start_working_match(
            working_input.context,
            log_anchor_hash=working_input.input_hash,
            effective_match_timing=working_input.timing,
            effective_match_stamina=working_input.stamina,
            rally_calibration_profile=working_input.rally_calibration,
            effective_match_gameplans=working_input.gameplans,
            effective_rally_rules=working_input.rules,
        )
        if rebuilt_input.fingerprint != working_input.fingerprint:
            raise ValueError("working input cannot reproduce initial live-match state")

        return_point_id = self._return_point_id(source_command_id)
        point_key = (*key, return_point_id)
        existing = self.session.get(LiveMatchReturnPointModel, point_key)
        if existing is not None:
            if (
                existing.source_command_id != source_command_id
                or existing.kind != kind
                or existing.state_fingerprint != initial.fingerprint
                or existing.working_state_json != initial.model_dump_json()
            ):
                raise ValueError("initial return point conflicts with existing snapshot")
            return self._return_point_response(existing)

        point = LiveMatchReturnPointModel(
            run_id=run_id,
            branch_id=branch_id,
            week_ordinal=week_ordinal,
            slot_id=slot_id,
            group_id=group_id,
            return_point_id=return_point_id,
            source_command_id=source_command_id,
            kind=kind,
            state_fingerprint=initial.fingerprint,
            working_state_json=initial.model_dump_json(),
            created_from_rally_index=initial.rally_index,
            created_from_set_number=initial.set_number,
            created_from_games_a=initial.games_a,
            created_from_games_b=initial.games_b,
            status="available",
            metadata_json='{"origin":"pre_first_rally"}',
        )
        self.session.add(point)
        self.session.flush()
        return self._return_point_response(point)

    def list_return_points(
        self,
        *,
        run_id: str,
        branch_id: str,
        week_ordinal: int,
        slot_id: str,
        group_id: str,
    ) -> dict:
        points = self.session.scalars(
            select(LiveMatchReturnPointModel).where(
                LiveMatchReturnPointModel.run_id == run_id,
                LiveMatchReturnPointModel.branch_id == branch_id,
                LiveMatchReturnPointModel.week_ordinal == week_ordinal,
                LiveMatchReturnPointModel.slot_id == slot_id,
                LiveMatchReturnPointModel.group_id == group_id,
            )
        ).all()
        alternatives = self.session.scalars(
            select(LiveMatchAlternativePathModel).where(
                LiveMatchAlternativePathModel.run_id == run_id,
                LiveMatchAlternativePathModel.branch_id == branch_id,
                LiveMatchAlternativePathModel.week_ordinal == week_ordinal,
                LiveMatchAlternativePathModel.slot_id == slot_id,
                LiveMatchAlternativePathModel.group_id == group_id,
            )
        ).all()
        return {
            "schema_version": "live_match_return_timeline.v1",
            "run_id": run_id,
            "branch_id": branch_id,
            "week_ordinal": week_ordinal,
            "slot_id": slot_id,
            "group_id": group_id,
            "return_points": [
                self._return_point_response(point)
                for point in sorted(points, key=lambda item: item.created_from_rally_index)
            ],
            "alternatives": [
                self._alternative_response(item)
                for item in sorted(alternatives, key=lambda item: item.archived_rally_index)
            ],
        }

    def restore_return_point(
        self,
        *,
        run_id: str,
        branch_id: str,
        week_ordinal: int,
        slot_id: str,
        group_id: str,
        return_point_id: str,
        restore_command_id: str,
        expected_state_fingerprint: str,
    ) -> dict:
        """Restore an active working snapshot while archiving the displaced path."""

        key = self._key(
            run_id=run_id,
            branch_id=branch_id,
            week_ordinal=week_ordinal,
            slot_id=slot_id,
            group_id=group_id,
        )
        row = self.session.get(LiveMatchWorkingModel, key)
        if row is None or row.status != "active" or row.working_state_json is None:
            raise ValueError(
                "only an uncommitted active live match can restore a return point"
            )
        if row.state_fingerprint != expected_state_fingerprint:
            raise ValueError("live match state changed before return-point restore")

        point = self.session.get(LiveMatchReturnPointModel, (*key, return_point_id))
        if point is None or point.status != "available":
            raise ValueError("live match return point is unavailable")

        current = MatchRallyWorkingState.model_validate_json(row.working_state_json)
        alternative_id = f"alternative:{restore_command_id}"
        alternative_key = (*key, alternative_id)
        existing_alt = self.session.get(LiveMatchAlternativePathModel, alternative_key)
        if existing_alt is None:
            self.session.add(
                LiveMatchAlternativePathModel(
                    run_id=run_id,
                    branch_id=branch_id,
                    week_ordinal=week_ordinal,
                    slot_id=slot_id,
                    group_id=group_id,
                    alternative_id=alternative_id,
                    return_point_id=return_point_id,
                    state_fingerprint=current.fingerprint,
                    working_state_json=row.working_state_json,
                    archived_rally_index=current.rally_index,
                    archived_set_number=current.set_number,
                    archived_games_a=current.games_a,
                    archived_games_b=current.games_b,
                    metadata_json="{}",
                )
            )
        elif (
            existing_alt.return_point_id != return_point_id
            or existing_alt.state_fingerprint != current.fingerprint
            or existing_alt.working_state_json != row.working_state_json
        ):
            raise ValueError("restore command identity conflicts with archived path")

        restored = MatchRallyWorkingState.model_validate_json(point.working_state_json)
        if restored.fingerprint != point.state_fingerprint:
            raise ValueError("return point state fingerprint is corrupt")
        row.working_state_json = point.working_state_json
        row.state_fingerprint = point.state_fingerprint
        self.session.flush()
        return {
            "schema_version": "live_match_return_restore.v1",
            "return_point": self._return_point_response(point),
            "archived_alternative_id": alternative_id,
            "restored_state": self._response(row, idempotent_replay=False),
        }

    @staticmethod
    def _return_point_response(point: LiveMatchReturnPointModel) -> dict:
        return {
            "return_point_id": point.return_point_id,
            "source_command_id": point.source_command_id,
            "kind": point.kind,
            "status": point.status,
            "state_fingerprint": point.state_fingerprint,
            "rally_index": point.created_from_rally_index,
            "set_number": point.created_from_set_number,
            "games_a": point.created_from_games_a,
            "games_b": point.created_from_games_b,
        }

    @staticmethod
    def _alternative_response(item: LiveMatchAlternativePathModel) -> dict:
        return {
            "alternative_id": item.alternative_id,
            "return_point_id": item.return_point_id,
            "state_fingerprint": item.state_fingerprint,
            "rally_index": item.archived_rally_index,
            "set_number": item.archived_set_number,
            "games_a": item.archived_games_a,
            "games_b": item.archived_games_b,
        }

    def simulate_next_rally(
        self,
        *,
        run_id: str,
        branch_id: str,
        week_ordinal: int,
        slot_id: str,
        group_id: str,
        command_id: str,
        expected_state_fingerprint: str,
    ) -> dict:
        """Advance exactly one rally and persist the resulting state atomically.

        command_id + request fingerprint makes network retries idempotent. A stale
        expected_state_fingerprint cannot advance the match.
        """

        if not command_id:
            raise ValueError("live next-rally command_id must be non-empty")
        key = self._key(
            run_id=run_id,
            branch_id=branch_id,
            week_ordinal=week_ordinal,
            slot_id=slot_id,
            group_id=group_id,
        )
        row = self.session.get(LiveMatchWorkingModel, key)
        if row is None:
            raise ValueError("live match has not been started")
        request_fingerprint = fingerprint(
            {
                "kind": "live_match_next_rally.v1",
                "scope": [run_id, branch_id, week_ordinal, slot_id, group_id],
                "command_id": command_id,
                "match_id": row.match_id,
                "working_input_fingerprint": row.working_input_fingerprint,
                "expected_state_fingerprint": expected_state_fingerprint,
            }
        )
        receipt_key = (*key, command_id)
        receipt = self.session.get(LiveMatchRallyCommandModel, receipt_key)
        if receipt is not None:
            if receipt.request_fingerprint != request_fingerprint:
                raise ValueError("live next-rally command_id reuse conflicts")
            response = json.loads(receipt.response_json)
            response["idempotent_replay"] = True
            return response

        if row.status == "complete":
            raise ValueError("live match is already complete")
        if row.state_fingerprint != expected_state_fingerprint:
            raise ValueError("live match state changed; retry against the current state")
        if row.working_state_json is None:
            raise ValueError("active live match has no resumable working state")

        working_input = MatchWorkingInput.model_validate_json(row.working_input_json)
        state = MatchRallyWorkingState.model_validate_json(row.working_state_json)
        if state.fingerprint != row.state_fingerprint:
            raise ValueError("persisted live match state fingerprint is corrupt")
        if working_input.fingerprint != row.working_input_fingerprint:
            raise ValueError("persisted live match input fingerprint is corrupt")

        outcome = MatchEngine(
            rng=DeterministicRng(working_input.simulation_seed)
        ).simulate_next_rally(working_input, state)

        if outcome.final_result is not None:
            final_result = outcome.final_result
            final_result_json = final_result.model_dump_json()
            row.status = "complete"
            row.working_state_json = None
            row.state_fingerprint = None
            row.final_result_json = final_result_json
            row.final_result_fingerprint = fingerprint(
                final_result.model_dump(mode="json")
            )
        else:
            if outcome.state is None:
                raise ValueError("live next-rally transition returned no resumable state")
            row.working_state_json = outcome.state.model_dump_json()
            row.state_fingerprint = outcome.state.fingerprint

        response = self._response(row, idempotent_replay=False)
        response["command_id"] = command_id
        response["request_fingerprint"] = request_fingerprint
        response["rally"] = (
            outcome.rally.model_dump(mode="json")
            if outcome.rally is not None
            else None
        )
        self.session.add(
            LiveMatchRallyCommandModel(
                run_id=run_id,
                branch_id=branch_id,
                week_ordinal=week_ordinal,
                slot_id=slot_id,
                group_id=group_id,
                command_id=command_id,
                request_fingerprint=request_fingerprint,
                response_json=json.dumps(
                    response, sort_keys=True, separators=(",", ":")
                ),
            )
        )
        self.session.flush()
        return response

    @staticmethod
    def _response(row: LiveMatchWorkingModel, *, idempotent_replay: bool) -> dict:
        state = (
            MatchRallyWorkingState.model_validate_json(row.working_state_json)
            if row.working_state_json is not None
            else None
        )
        result = (
            MatchResult.model_validate_json(row.final_result_json)
            if row.final_result_json is not None
            else None
        )
        return {
            "schema_version": "persisted_live_match_state.v1",
            "run_id": row.run_id,
            "branch_id": row.branch_id,
            "week_ordinal": row.week_ordinal,
            "slot_id": row.slot_id,
            "group_id": row.group_id,
            "match_id": row.match_id,
            "status": row.status,
            "working_input_fingerprint": row.working_input_fingerprint,
            "state_fingerprint": row.state_fingerprint,
            "rally_index": state.rally_index if state is not None else None,
            "set_number": state.set_number if state is not None else None,
            "games_a": state.games_a if state is not None else None,
            "games_b": state.games_b if state is not None else None,
            "final_result_fingerprint": row.final_result_fingerprint,
            "final_result": (
                result.model_dump(mode="json") if result is not None else None
            ),
            "idempotent_replay": idempotent_replay,
        }
