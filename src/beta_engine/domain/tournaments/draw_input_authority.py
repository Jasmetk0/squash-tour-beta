"""Run/Branch-owned immutable inputs for canonical tournament draw generation."""

from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import Field, model_validator

from beta_engine.domain.rankings.official import FrozenInput
from beta_engine.domain.tournaments.entry_field import TournamentEntryField
from beta_engine.domain.tournaments.ranking_snapshot_authority import (
    TournamentRankingSnapshotAuthority,
)


class TournamentDrawInputAuthority(FrozenInput):
    """Frozen canonical field/ranking inputs at the pre-draw commitment boundary.

    This object deliberately does not invent bracket placement, Wild Card selection,
    Lucky Loser, Final Commitment or Week Tournament Lock policy.  It freezes only
    inputs already resolved by earlier authoritative stages so a later bracket
    generator cannot fall back to mutable legacy Entry/Draw files.
    """

    schema_version: Literal["tournament_draw_input_authority.v1"] = (
        "tournament_draw_input_authority.v1"
    )
    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    event_id: str = Field(min_length=1)
    committed_by_command_id: str = Field(min_length=1, max_length=128)
    draw_seed: int
    main_seed_count: int = Field(ge=0)
    qualification_seed_count: int = Field(ge=0)
    field_sequence: int = Field(ge=1)
    tournament_ranking_authority_fingerprint: str = Field(
        pattern=r"^[0-9a-f]{64}$"
    )
    ranking_snapshot_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    entry_field_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    direct_main_player_ids: tuple[str, ...]
    qualification_player_ids: tuple[str, ...]
    qualifier_placeholder_ids: tuple[str, ...]
    withdrawn_player_ids: tuple[str, ...]
    main_seed_player_ids: tuple[str, ...]
    qualification_seed_player_ids: tuple[str, ...]
    bye_slots: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_structure(self) -> "TournamentDrawInputAuthority":
        if len(set(self.direct_main_player_ids)) != len(self.direct_main_player_ids):
            raise ValueError("Canonical Main field contains duplicate players")
        if len(set(self.qualification_player_ids)) != len(
            self.qualification_player_ids
        ):
            raise ValueError("Canonical Qualification field contains duplicate players")
        if set(self.direct_main_player_ids) & set(self.qualification_player_ids):
            raise ValueError("Player appears in both Main and Qualification field")
        active = set(self.direct_main_player_ids) | set(
            self.qualification_player_ids
        )
        if active & set(self.withdrawn_player_ids):
            raise ValueError("Withdrawn player remains in committed draw input")
        if len(self.main_seed_player_ids) != self.main_seed_count:
            raise ValueError("Main seed payload does not match requested seed count")
        if len(self.qualification_seed_player_ids) != self.qualification_seed_count:
            raise ValueError(
                "Qualification seed payload does not match requested seed count"
            )
        if not set(self.main_seed_player_ids).issubset(
            set(self.direct_main_player_ids)
        ):
            raise ValueError("Main seed is outside canonical direct Main field")
        if not set(self.qualification_seed_player_ids).issubset(
            set(self.qualification_player_ids)
        ):
            raise ValueError("Qualification seed is outside canonical Q field")
        expected_placeholders = tuple(
            f"Q{index}" for index in range(1, len(self.qualifier_placeholder_ids) + 1)
        )
        if self.qualifier_placeholder_ids != expected_placeholders:
            raise ValueError("Qualifier placeholder identities are not canonical")
        return self

    @property
    def fingerprint(self) -> str:
        return hashlib.sha256(
            json.dumps(
                self.model_dump(mode="json"),
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
        ).hexdigest()


class TournamentDrawInputAuthorityBuilder:
    """Build draw commitment inputs only from already-owned tournament authority."""

    @staticmethod
    def build(
        *,
        authority: TournamentRankingSnapshotAuthority,
        field: TournamentEntryField,
        field_sequence: int,
        command_id: str,
        draw_seed: int,
        main_seed_count: int,
        qualification_seed_count: int,
    ) -> TournamentDrawInputAuthority:
        if (field.run_id, field.branch_id, field.event_id) != (
            authority.run_id,
            authority.branch_id,
            authority.event_id,
        ):
            raise ValueError(
                "Tournament Entry Field scope differs from ranking authority"
            )
        if (
            field.tournament_ranking_authority_fingerprint != authority.fingerprint
            or field.ranking_snapshot_fingerprint
            != authority.ranking_snapshot_fingerprint
        ):
            raise ValueError(
                "Tournament Entry Field is not bound to the supplied ranking authority"
            )
        if field.capacity.wild_card_slots:
            raise ValueError(
                "Canonical draw input commitment requires resolved Wild Card authority"
            )
        if main_seed_count > len(field.direct_main_player_ids):
            raise ValueError("Main seed count exceeds canonical direct Main field")
        if qualification_seed_count > len(field.qualification_player_ids):
            raise ValueError(
                "Qualification seed count exceeds canonical Qualification field"
            )

        # TournamentEntryFieldResolver already orders each partition from the frozen
        # Tournament Ranking Snapshot (with its canonical NR fallback). Reusing that
        # order avoids consulting any newer/current ranking during draw commitment.
        main_seed_player_ids = field.direct_main_player_ids[:main_seed_count]
        qualification_seed_player_ids = field.qualification_player_ids[
            :qualification_seed_count
        ]
        qualifier_placeholder_ids = tuple(
            f"Q{index}"
            for index in range(1, field.capacity.qualifier_spots + 1)
        )
        return TournamentDrawInputAuthority(
            run_id=authority.run_id,
            branch_id=authority.branch_id,
            event_id=authority.event_id,
            committed_by_command_id=command_id,
            draw_seed=draw_seed,
            main_seed_count=main_seed_count,
            qualification_seed_count=qualification_seed_count,
            field_sequence=field_sequence,
            tournament_ranking_authority_fingerprint=authority.fingerprint,
            ranking_snapshot_fingerprint=authority.ranking_snapshot_fingerprint,
            entry_field_fingerprint=field.fingerprint,
            direct_main_player_ids=field.direct_main_player_ids,
            qualification_player_ids=field.qualification_player_ids,
            qualifier_placeholder_ids=qualifier_placeholder_ids,
            withdrawn_player_ids=field.withdrawn_player_ids,
            main_seed_player_ids=main_seed_player_ids,
            qualification_seed_player_ids=qualification_seed_player_ids,
            bye_slots=field.capacity.bye_slots,
        )
