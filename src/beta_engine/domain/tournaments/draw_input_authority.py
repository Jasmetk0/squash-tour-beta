"""Run/Branch-owned immutable inputs for canonical tournament draw generation."""

from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import Field, model_validator

from beta_engine.domain.rankings.official import FrozenInput
from beta_engine.domain.tournaments.entry_field import (
    TournamentEntryField,
    TournamentEntryFieldCapacity,
)
from beta_engine.domain.tournaments.ranking_snapshot_authority import (
    TournamentRankingSnapshotAuthority,
)


DrawInputSchemaVersion = Literal[
    "tournament_draw_input_authority.v1",
    "tournament_draw_input_authority.v2",
]


def canonical_classic_seed_count(*, bracket_capacity: int, actual_player_count: int) -> int:
    """Master §15.2 seed-count rule for one classic elimination bracket."""

    if bracket_capacity < 2 or bracket_capacity & (bracket_capacity - 1):
        raise ValueError("Classic tournament bracket capacity must be a power of two")
    if actual_player_count < 0 or actual_player_count > bracket_capacity:
        raise ValueError("Actual player count must fit inside bracket capacity")
    return min(actual_player_count, max(1, bracket_capacity // 4))


def canonical_qualification_seed_count(
    *, capacity: TournamentEntryFieldCapacity, actual_player_count: int
) -> int:
    """Total global seed pool across equal Master §15.6 Qualification sections."""

    if capacity.qualification_draw_size == 0:
        if capacity.qualifier_spots != 0:
            raise ValueError(
                "Qualification qualifier spots require Qualification draw capacity"
            )
        return 0
    if capacity.qualifier_spots < 1:
        raise ValueError(
            "Qualification draw capacity requires at least one qualifier section"
        )
    if actual_player_count < capacity.qualifier_spots:
        raise ValueError(
            "Qualification requires at least one real player per Q section"
        )
    if capacity.qualification_draw_size % capacity.qualifier_spots:
        raise ValueError(
            "Qualification capacity must divide evenly across qualifier sections"
        )
    section_capacity = (
        capacity.qualification_draw_size // capacity.qualifier_spots
    )
    if section_capacity < 2 or section_capacity & (section_capacity - 1):
        raise ValueError(
            "Each classic Qualification section must have power-of-two capacity"
        )
    maximum_seed_pool = capacity.qualifier_spots * max(1, section_capacity // 4)
    return min(actual_player_count, maximum_seed_pool)


class TournamentDrawInputAuthority(FrozenInput):
    """Frozen canonical field/ranking inputs at the pre-draw commitment boundary.

    This object deliberately does not invent bracket placement, Wild Card selection,
    Lucky Loser, Final Commitment or Week Tournament Lock policy.  It freezes only
    inputs already resolved by earlier authoritative stages so a later bracket
    generator cannot fall back to mutable legacy Entry/Draw files.
    """

    schema_version: DrawInputSchemaVersion = "tournament_draw_input_authority.v1"
    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    event_id: str = Field(min_length=1)
    committed_by_command_id: str = Field(min_length=1, max_length=128)
    draw_seed: int
    main_seed_count: int = Field(ge=0)
    qualification_seed_count: int = Field(ge=0)
    field_sequence: int = Field(ge=1)
    capacity: TournamentEntryFieldCapacity
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
            f"Q{index}" for index in range(1, self.capacity.qualifier_spots + 1)
        )
        if self.qualifier_placeholder_ids != expected_placeholders:
            raise ValueError(
                "Qualifier placeholder identities/count differ from field capacity"
            )
        if self.schema_version == "tournament_draw_input_authority.v2":
            expected_main_seeds = canonical_classic_seed_count(
                bracket_capacity=self.capacity.main_draw_size,
                actual_player_count=len(self.direct_main_player_ids),
            )
            if self.main_seed_count != expected_main_seeds:
                raise ValueError(
                    "Canonical v2 Main seed count differs from Master §15.2"
                )
            expected_q_seeds = canonical_qualification_seed_count(
                capacity=self.capacity,
                actual_player_count=len(self.qualification_player_ids),
            )
            if self.qualification_seed_count != expected_q_seeds:
                raise ValueError(
                    "Canonical v2 Qualification seed count differs from Master §15.2/15.6"
                )
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
        main_seed_count: int | None,
        qualification_seed_count: int | None,
        schema_version: DrawInputSchemaVersion = "tournament_draw_input_authority.v1",
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

        if schema_version == "tournament_draw_input_authority.v2":
            canonical_main = canonical_classic_seed_count(
                bracket_capacity=field.capacity.main_draw_size,
                actual_player_count=len(field.direct_main_player_ids),
            )
            canonical_qualification = canonical_qualification_seed_count(
                capacity=field.capacity,
                actual_player_count=len(field.qualification_player_ids),
            )
            if main_seed_count is not None and main_seed_count != canonical_main:
                raise ValueError(
                    "Requested Main seed count differs from Master §15.2"
                )
            if (
                qualification_seed_count is not None
                and qualification_seed_count != canonical_qualification
            ):
                raise ValueError(
                    "Requested Qualification seed count differs from Master §15.2/15.6"
                )
            main_seed_count = canonical_main
            qualification_seed_count = canonical_qualification
        else:
            if main_seed_count is None or qualification_seed_count is None:
                raise ValueError(
                    "Historical Draw Input v1 requires explicit seed counts"
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
            schema_version=schema_version,
            run_id=authority.run_id,
            branch_id=authority.branch_id,
            event_id=authority.event_id,
            committed_by_command_id=command_id,
            draw_seed=draw_seed,
            main_seed_count=main_seed_count,
            qualification_seed_count=qualification_seed_count,
            field_sequence=field_sequence,
            capacity=field.capacity,
            tournament_ranking_authority_fingerprint=authority.fingerprint,
            ranking_snapshot_fingerprint=authority.ranking_snapshot_fingerprint,
            entry_field_fingerprint=field.fingerprint,
            direct_main_player_ids=field.direct_main_player_ids,
            qualification_player_ids=field.qualification_player_ids,
            qualifier_placeholder_ids=qualifier_placeholder_ids,
            withdrawn_player_ids=field.withdrawn_player_ids,
            main_seed_player_ids=main_seed_player_ids,
            qualification_seed_player_ids=qualification_seed_player_ids,
        )