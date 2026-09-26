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
    LiveMatchRallyCommandModel,
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
