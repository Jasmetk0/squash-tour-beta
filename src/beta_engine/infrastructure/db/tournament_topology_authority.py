"""Persistence and replay for immutable Tournament topology authority."""

from __future__ import annotations

import hashlib
import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from beta_engine.domain.tournaments.topology_authority import (
    TournamentTopologyAuthority,
    TournamentTopologyAuthorityBuilder,
)
from beta_engine.infrastructure.db.models import (
    RunBranchModel,
    RunContainerModel,
    TournamentTopologyAuthorityModel,
)
from beta_engine.infrastructure.db.tournament_draw_authority import (
    TournamentDrawAuthorityStore,
)
from beta_engine.infrastructure.db.tournament_entry_field import (
    TournamentEntryFieldStore,
)
from beta_engine.infrastructure.db.tournament_format_authority import (
    TournamentFormatAuthorityStore,
)
from beta_engine.infrastructure.db.tournament_ranking_snapshot_authority import (
    TournamentRankingSnapshotAuthorityStore,
)


class TournamentTopologyAuthorityConflict(ValueError):
    """A topology command conflicts with immutable Tournament Edition topology."""


def _request_fingerprint(payload: dict) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


class TournamentTopologyAuthorityStore:
    def __init__(self, session: Session):
        self.session = session

    def _scope(self, run_id: str, branch_id: str, *, writing: bool = False) -> None:
        run = self.session.get(RunContainerModel, run_id)
        branch = self.session.get(RunBranchModel, branch_id)
        if run is None or branch is None or branch.run_id != run_id:
            raise ValueError("Tournament Topology Run/Branch scope does not exist")
        if writing and (run.read_only or branch.read_only or branch.status == "archived"):
            raise ValueError("Tournament Topology scope is not writable")

    def _participant_order(self, *, field) -> tuple[str, ...]:
        if field.source_kind in {
            "finals_participant_selection",
            "finals_effective_participant_state",
        }:
            if not field.seed_order_player_ids:
                raise ValueError("Finals group topology requires frozen Race seed order")
            if set(field.seed_order_player_ids) != set(field.direct_main_player_ids):
                raise ValueError(
                    "Finals Race seed order differs from active Tournament Entry Field"
                )
            return field.seed_order_player_ids

        ranking = TournamentRankingSnapshotAuthorityStore(self.session).get(
            run_id=field.run_id,
            branch_id=field.branch_id,
            event_id=field.event_id,
        )
        if ranking is None:
            raise ValueError(
                "Ranking/Application group topology requires Tournament Ranking Snapshot authority"
            )
        rank_by_player = {
            row.player_id: row.rank for row in ranking.ranking_snapshot.rows
        }
        return tuple(
            sorted(
                field.direct_main_player_ids,
                key=lambda player_id: (
                    rank_by_player.get(player_id) is None,
                    rank_by_player.get(player_id) or 10**9,
                    player_id,
                ),
            )
        )

    @staticmethod
    def _request(
        *,
        format_authority_fingerprint: str,
        entry_field_fingerprint: str,
        format_kind: str,
        topology_seed: int | None,
        knockout_draw_fingerprint: str | None,
    ) -> dict:
        return {
            "format_authority_fingerprint": format_authority_fingerprint,
            "entry_field_fingerprint": entry_field_fingerprint,
            "format_kind": format_kind,
            "topology_seed": topology_seed,
            "knockout_draw_fingerprint": knockout_draw_fingerprint,
        }

    def _rebuild(
        self,
        *,
        format_authority,
        field,
        command_id: str,
        topology_seed: int | None,
    ) -> TournamentTopologyAuthority:
        if format_authority.format_kind == "knockout":
            draw = TournamentDrawAuthorityStore(self.session).get(
                run_id=field.run_id,
                branch_id=field.branch_id,
                event_id=field.event_id,
            )
            if draw is None:
                raise ValueError(
                    "Knockout topology requires canonical Draw authority"
                )
            return TournamentTopologyAuthorityBuilder.build_knockout_reference(
                format_authority=format_authority,
                entry_field=field,
                draw_fingerprint=draw.fingerprint,
                command_id=command_id,
                participant_order_player_ids=(),
            )

        if topology_seed is None:
            raise ValueError("Group topology generation requires deterministic topology seed")
        return TournamentTopologyAuthorityBuilder.build_groups(
            format_authority=format_authority,
            entry_field=field,
            participant_order_player_ids=self._participant_order(field=field),
            command_id=command_id,
            topology_seed=topology_seed,
        )

    def validate_row(
        self,
        row: TournamentTopologyAuthorityModel,
        *,
        format_authority,
        field,
    ) -> TournamentTopologyAuthority:
        authority = TournamentTopologyAuthority.model_validate_json(row.payload_json)
        if (
            authority.run_id,
            authority.branch_id,
            authority.event_id,
            authority.generated_by_command_id,
            authority.format_authority_fingerprint,
            authority.entry_field_fingerprint,
            authority.fingerprint,
        ) != (
            row.run_id,
            row.branch_id,
            row.event_id,
            row.command_id,
            row.format_authority_fingerprint,
            row.entry_field_fingerprint,
            row.authority_fingerprint,
        ):
            raise ValueError("Stored Tournament Topology authority is corrupt")
        if format_authority.fingerprint != row.format_authority_fingerprint:
            raise ValueError("Tournament Topology references stale Format authority")
        if field.fingerprint != row.entry_field_fingerprint:
            raise ValueError("Tournament Topology references stale Entry Field")

        rebuilt = self._rebuild(
            format_authority=format_authority,
            field=field,
            command_id=row.command_id,
            topology_seed=authority.topology_seed,
        )
        if rebuilt != authority:
            raise ValueError(
                "Tournament Topology authority does not replay from frozen dependencies"
            )
        request = self._request(
            format_authority_fingerprint=format_authority.fingerprint,
            entry_field_fingerprint=field.fingerprint,
            format_kind=format_authority.format_kind,
            topology_seed=authority.topology_seed,
            knockout_draw_fingerprint=authority.knockout_draw_fingerprint,
        )
        if row.request_fingerprint != _request_fingerprint(request):
            raise ValueError("Tournament Topology request fingerprint is corrupt")
        return authority

    def get(
        self, *, run_id: str, branch_id: str, event_id: str
    ) -> TournamentTopologyAuthority | None:
        self._scope(run_id, branch_id)
        row = self.session.get(
            TournamentTopologyAuthorityModel,
            (run_id, branch_id, event_id),
        )
        if row is None:
            return None
        format_authority = TournamentFormatAuthorityStore(self.session).get(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
        )
        if format_authority is None:
            raise ValueError(
                "Tournament Topology references missing Tournament Format authority"
            )
        history = TournamentEntryFieldStore(self.session).history(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
        )
        if not history:
            raise ValueError("Tournament Topology references missing Entry Field")
        return self.validate_row(
            row,
            format_authority=format_authority,
            field=history[-1],
        )

    def generate(
        self,
        *,
        run_id: str,
        branch_id: str,
        event_id: str,
        command_id: str,
        topology_seed: int | None = None,
    ) -> TournamentTopologyAuthority:
        self._scope(run_id, branch_id, writing=True)
        if not command_id.strip() or len(command_id) > 128:
            raise ValueError("Tournament Topology requires a valid command ID")

        format_authority = TournamentFormatAuthorityStore(self.session).get(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
        )
        if format_authority is None:
            raise ValueError(
                "Tournament Topology requires Tournament Format authority"
            )
        history = TournamentEntryFieldStore(self.session).history(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
        )
        if not history:
            raise ValueError("Tournament Topology requires canonical Entry Field")
        field = history[-1]

        proposed = self._rebuild(
            format_authority=format_authority,
            field=field,
            command_id=command_id,
            topology_seed=topology_seed,
        )
        request = self._request(
            format_authority_fingerprint=format_authority.fingerprint,
            entry_field_fingerprint=field.fingerprint,
            format_kind=format_authority.format_kind,
            topology_seed=proposed.topology_seed,
            knockout_draw_fingerprint=proposed.knockout_draw_fingerprint,
        )
        request_fp = _request_fingerprint(request)

        retry = self.session.scalar(
            select(TournamentTopologyAuthorityModel).where(
                TournamentTopologyAuthorityModel.run_id == run_id,
                TournamentTopologyAuthorityModel.branch_id == branch_id,
                TournamentTopologyAuthorityModel.command_id == command_id,
            )
        )
        if retry is not None:
            if retry.event_id != event_id or retry.request_fingerprint != request_fp:
                raise TournamentTopologyAuthorityConflict(
                    "Tournament Topology command ID already has a different request"
                )
            return self.validate_row(
                retry,
                format_authority=format_authority,
                field=field,
            )

        existing = self.session.get(
            TournamentTopologyAuthorityModel,
            (run_id, branch_id, event_id),
        )
        if existing is not None:
            raise TournamentTopologyAuthorityConflict(
                "Tournament Edition already has immutable Topology authority"
            )

        self.session.add(
            TournamentTopologyAuthorityModel(
                run_id=run_id,
                branch_id=branch_id,
                event_id=event_id,
                command_id=command_id,
                request_fingerprint=request_fp,
                authority_fingerprint=proposed.fingerprint,
                format_authority_fingerprint=format_authority.fingerprint,
                entry_field_fingerprint=field.fingerprint,
                payload_json=proposed.model_dump_json(),
            )
        )
        self.session.flush()
        return proposed
