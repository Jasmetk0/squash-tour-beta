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
from beta_engine.domain.tournaments.wild_card_authority import (
    TournamentWildCardAuthority,
)


DrawInputSchemaVersion = Literal[
    "tournament_draw_input_authority.v1",
    "tournament_draw_input_authority.v2",
    "tournament_draw_input_authority.v3",
    "tournament_draw_input_authority.v4",
    "tournament_draw_input_authority.v5",
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
    wild_card_authority_fingerprint: str | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{64}$",
        exclude_if=lambda value: value is None,
    )
    post_draw_wild_card_repair_fingerprints: tuple[str, ...] = Field(
        default=(),
        exclude_if=lambda value: not value,
    )
    direct_main_player_ids: tuple[str, ...]
    wild_card_player_ids: tuple[str, ...] = Field(
        default=(),
        exclude_if=lambda value: not value,
    )
    qualification_player_ids: tuple[str, ...]
    qualifier_placeholder_ids: tuple[str, ...]
    withdrawn_player_ids: tuple[str, ...]
    main_seed_player_ids: tuple[str, ...]
    qualification_seed_player_ids: tuple[str, ...]
    main_seed_vacancy_numbers: tuple[int, ...] = Field(
        default=(),
        exclude_if=lambda value: not value,
    )
    qualification_seed_vacancy_numbers: tuple[int, ...] = Field(
        default=(),
        exclude_if=lambda value: not value,
    )

    @model_validator(mode="after")
    def validate_structure(self) -> "TournamentDrawInputAuthority":
        if len(set(self.direct_main_player_ids)) != len(self.direct_main_player_ids):
            raise ValueError("Canonical Main field contains duplicate players")
        if len(set(self.qualification_player_ids)) != len(
            self.qualification_player_ids
        ):
            raise ValueError("Canonical Qualification field contains duplicate players")
        if len(set(self.wild_card_player_ids)) != len(self.wild_card_player_ids):
            raise ValueError("Canonical WC field contains duplicate players")
        main_players = set(self.direct_main_player_ids) | set(self.wild_card_player_ids)
        if len(main_players) != len(self.direct_main_player_ids) + len(self.wild_card_player_ids):
            raise ValueError("Player appears in both Direct Main and WC field")
        if main_players & set(self.qualification_player_ids):
            raise ValueError("Player appears in both Main and Qualification field")
        active = main_players | set(self.qualification_player_ids)
        if active & set(self.withdrawn_player_ids):
            raise ValueError("Withdrawn player remains in committed draw input")
        if self.schema_version == "tournament_draw_input_authority.v5":
            if (
                len(self.main_seed_player_ids)
                + len(self.main_seed_vacancy_numbers)
                != self.main_seed_count
            ):
                raise ValueError(
                    "Main active seeds plus frozen vacancies must match seed count"
                )
            if (
                len(self.qualification_seed_player_ids)
                + len(self.qualification_seed_vacancy_numbers)
                != self.qualification_seed_count
            ):
                raise ValueError(
                    "Qualification active seeds plus frozen vacancies must match seed count"
                )
            if tuple(sorted(set(self.main_seed_vacancy_numbers))) != (
                self.main_seed_vacancy_numbers
            ):
                raise ValueError("Main frozen seed vacancies must be sorted and unique")
            if tuple(sorted(set(self.qualification_seed_vacancy_numbers))) != (
                self.qualification_seed_vacancy_numbers
            ):
                raise ValueError(
                    "Qualification frozen seed vacancies must be sorted and unique"
                )
            if any(
                number < 1 or number > self.main_seed_count
                for number in self.main_seed_vacancy_numbers
            ):
                raise ValueError("Main frozen seed vacancy number is outside seed pool")
            if any(
                number < 1 or number > self.qualification_seed_count
                for number in self.qualification_seed_vacancy_numbers
            ):
                raise ValueError(
                    "Qualification frozen seed vacancy number is outside seed pool"
                )
            if not (
                self.main_seed_vacancy_numbers
                or self.qualification_seed_vacancy_numbers
            ):
                raise ValueError("Draw Input v5 requires frozen seed-vacancy evidence")
        else:
            if len(self.main_seed_player_ids) != self.main_seed_count:
                raise ValueError("Main seed payload does not match requested seed count")
            if len(self.qualification_seed_player_ids) != self.qualification_seed_count:
                raise ValueError(
                    "Qualification seed payload does not match requested seed count"
                )
            if (
                self.main_seed_vacancy_numbers
                or self.qualification_seed_vacancy_numbers
            ):
                raise ValueError(
                    "Historical Draw Input cannot carry frozen seed vacancies"
                )
        if not set(self.main_seed_player_ids).issubset(
            set(self.direct_main_player_ids) | set(self.wild_card_player_ids)
        ):
            raise ValueError("Main seed is outside canonical Main field")
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
        if self.schema_version in {
            "tournament_draw_input_authority.v2",
            "tournament_draw_input_authority.v3",
            "tournament_draw_input_authority.v4",
            "tournament_draw_input_authority.v5",
        }:
            expected_main_seeds = canonical_classic_seed_count(
                bracket_capacity=self.capacity.main_draw_size,
                actual_player_count=(
                    len(self.direct_main_player_ids)
                    + len(self.wild_card_player_ids)
                ),
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
                    "Canonical v2/v3 Qualification seed count differs from Master §15.2/15.6"
                )
        if self.schema_version in {
            "tournament_draw_input_authority.v3",
            "tournament_draw_input_authority.v4",
            "tournament_draw_input_authority.v5",
        }:
            if self.capacity.wild_card_slots != len(self.wild_card_player_ids):
                raise ValueError(
                    "Canonical WC Draw Input requires every WC slot to be resolved"
                )
            if self.capacity.wild_card_slots and self.wild_card_authority_fingerprint is None:
                raise ValueError("Canonical WC field lacks WC authority fingerprint")
            if self.schema_version in {
                "tournament_draw_input_authority.v4",
                "tournament_draw_input_authority.v5",
            }:
                if not self.post_draw_wild_card_repair_fingerprints:
                    raise ValueError(
                        "Post-draw WC Draw Input requires repair evidence"
                    )
            elif self.post_draw_wild_card_repair_fingerprints:
                raise ValueError(
                    "Pre-repair WC Draw Input cannot carry post-draw repair evidence"
                )
        elif (
            self.wild_card_player_ids
            or self.wild_card_authority_fingerprint is not None
            or self.post_draw_wild_card_repair_fingerprints
        ):
            raise ValueError("Historical Draw Input cannot carry canonical WC authority")
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
    def build_post_draw_wild_card_repair(
        *,
        previous: TournamentDrawInputAuthority,
        command_id: str,
        withdrawn_player_id: str,
        replacement_player_id: str,
        repair_authority_fingerprint: str,
        qualification_replacement_player_id: str | None = None,
        qualification_backfill_player_id: str | None = None,
        main_vacated_seed_number: int | None = None,
        qualification_vacated_seed_number: int | None = None,
    ) -> TournamentDrawInputAuthority:
        if previous.schema_version not in {
            "tournament_draw_input_authority.v3",
            "tournament_draw_input_authority.v4",
            "tournament_draw_input_authority.v5",
        }:
            raise ValueError("Post-draw WC repair requires canonical WC Draw Input")
        if previous.wild_card_player_ids.count(withdrawn_player_id) != 1:
            raise ValueError("Post-draw WC repair withdrawal is not active in WC field")
        withdrawn_was_seeded = withdrawn_player_id in previous.main_seed_player_ids
        if withdrawn_was_seeded != (main_vacated_seed_number is not None):
            raise ValueError(
                "Main frozen seed-vacancy evidence does not match withdrawn WC seed status"
            )
        active_main = (
            set(previous.direct_main_player_ids)
            | set(previous.wild_card_player_ids)
        )
        replacement_in_q = replacement_player_id in set(
            previous.qualification_player_ids
        )
        if replacement_player_id in active_main:
            raise ValueError("Post-draw WC replacement player is already active in Main")
        if replacement_in_q:
            if qualification_replacement_player_id != replacement_player_id:
                raise ValueError(
                    "Qualification RWC promotion requires matching Q replacement identity"
                )
            if not qualification_backfill_player_id:
                raise ValueError(
                    "Qualification RWC promotion requires Q backfill identity"
                )
            q_replacement_was_seeded = (
                replacement_player_id in previous.qualification_seed_player_ids
            )
            if q_replacement_was_seeded != (
                qualification_vacated_seed_number is not None
            ):
                raise ValueError(
                    "Qualification frozen seed-vacancy evidence does not match RWC seed status"
                )
        elif (
            qualification_replacement_player_id is not None
            or qualification_backfill_player_id is not None
        ):
            raise ValueError(
                "External RWC repair cannot carry Qualification replacement evidence"
            )

        main_seed_players = list(previous.main_seed_player_ids)
        qualification_seed_players = list(previous.qualification_seed_player_ids)
        main_seed_vacancies = set(previous.main_seed_vacancy_numbers)
        qualification_seed_vacancies = set(
            previous.qualification_seed_vacancy_numbers
        )
        if withdrawn_was_seeded:
            main_seed_players.remove(withdrawn_player_id)
            main_seed_vacancies.add(main_vacated_seed_number)
        if replacement_in_q and qualification_vacated_seed_number is not None:
            qualification_seed_players.remove(replacement_player_id)
            qualification_seed_vacancies.add(
                qualification_vacated_seed_number
            )

        qualification_players = list(previous.qualification_player_ids)
        if replacement_in_q:
            if qualification_backfill_player_id in (
                active_main
                | set(previous.wild_card_player_ids)
                | set(previous.qualification_player_ids)
            ):
                raise ValueError("Qualification RWC backfill player is already active")
            qualification_players.remove(replacement_player_id)
            qualification_players.append(qualification_backfill_player_id)

        wc_players = list(previous.wild_card_player_ids)
        wc_players[wc_players.index(withdrawn_player_id)] = replacement_player_id
        repairs = (
            *previous.post_draw_wild_card_repair_fingerprints,
            repair_authority_fingerprint,
        )
        withdrawn = tuple(
            sorted(set((*previous.withdrawn_player_ids, withdrawn_player_id)))
        )
        has_seed_vacancy = bool(
            main_seed_vacancies or qualification_seed_vacancies
        )
        return TournamentDrawInputAuthority(
            schema_version=(
                "tournament_draw_input_authority.v5"
                if has_seed_vacancy
                else "tournament_draw_input_authority.v4"
            ),
            run_id=previous.run_id,
            branch_id=previous.branch_id,
            event_id=previous.event_id,
            committed_by_command_id=command_id,
            draw_seed=previous.draw_seed,
            main_seed_count=previous.main_seed_count,
            qualification_seed_count=previous.qualification_seed_count,
            field_sequence=previous.field_sequence,
            capacity=previous.capacity,
            tournament_ranking_authority_fingerprint=(
                previous.tournament_ranking_authority_fingerprint
            ),
            ranking_snapshot_fingerprint=previous.ranking_snapshot_fingerprint,
            entry_field_fingerprint=previous.entry_field_fingerprint,
            wild_card_authority_fingerprint=previous.wild_card_authority_fingerprint,
            post_draw_wild_card_repair_fingerprints=repairs,
            direct_main_player_ids=previous.direct_main_player_ids,
            wild_card_player_ids=tuple(wc_players),
            qualification_player_ids=tuple(qualification_players),
            qualifier_placeholder_ids=previous.qualifier_placeholder_ids,
            withdrawn_player_ids=withdrawn,
            main_seed_player_ids=tuple(main_seed_players),
            qualification_seed_player_ids=tuple(qualification_seed_players),
            main_seed_vacancy_numbers=tuple(sorted(main_seed_vacancies)),
            qualification_seed_vacancy_numbers=tuple(
                sorted(qualification_seed_vacancies)
            ),
        )

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
        wild_card_authority: TournamentWildCardAuthority | None = None,
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
            if wild_card_authority is None:
                raise ValueError(
                    "Canonical draw input commitment requires resolved Wild Card authority"
                )
            if (
                wild_card_authority.run_id,
                wild_card_authority.branch_id,
                wild_card_authority.event_id,
                wild_card_authority.entry_field_fingerprint,
                wild_card_authority.field_sequence,
            ) != (
                field.run_id,
                field.branch_id,
                field.event_id,
                field.fingerprint,
                field_sequence,
            ):
                raise ValueError("Wild Card authority is stale for committed Entry Field")
            if len(wild_card_authority.active_wild_card_player_ids) != field.capacity.wild_card_slots:
                raise ValueError("All reserved Wild Card slots must be resolved before Draw Input")
        elif wild_card_authority is not None:
            raise ValueError("Wild Card authority supplied for event without WC capacity")

        wc_players = (
            wild_card_authority.active_wild_card_player_ids
            if wild_card_authority is not None
            else ()
        )
        qualification_players = (
            wild_card_authority.adjusted_qualification_player_ids
            if wild_card_authority is not None
            else field.qualification_player_ids
        )

        if schema_version in {
            "tournament_draw_input_authority.v2",
            "tournament_draw_input_authority.v3",
        }:
            canonical_main = canonical_classic_seed_count(
                bracket_capacity=field.capacity.main_draw_size,
                actual_player_count=len(field.direct_main_player_ids) + len(wc_players),
            )
            canonical_qualification = canonical_qualification_seed_count(
                capacity=field.capacity,
                actual_player_count=len(qualification_players),
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

        if main_seed_count > len(field.direct_main_player_ids) + len(wc_players):
            raise ValueError("Main seed count exceeds canonical Main field")
        if qualification_seed_count > len(qualification_players):
            raise ValueError(
                "Qualification seed count exceeds canonical Qualification field"
            )

        # TournamentEntryFieldResolver already orders each partition from the frozen
        # Tournament Ranking Snapshot (with its canonical NR fallback). Reusing that
        # order avoids consulting any newer/current ranking during draw commitment.
        rank_by_player = {
            row.player_id: row.rank for row in authority.ranking_snapshot.rows
        }
        main_players = tuple(
            sorted(
                (*field.direct_main_player_ids, *wc_players),
                key=lambda player_id: (
                    rank_by_player.get(player_id) is None,
                    rank_by_player.get(player_id) or 10**9,
                    player_id,
                ),
            )
        )
        main_seed_player_ids = main_players[:main_seed_count]
        qualification_seed_player_ids = qualification_players[
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
            wild_card_authority_fingerprint=(
                wild_card_authority.fingerprint
                if wild_card_authority is not None
                else None
            ),
            direct_main_player_ids=field.direct_main_player_ids,
            wild_card_player_ids=wc_players,
            qualification_player_ids=qualification_players,
            qualifier_placeholder_ids=qualifier_placeholder_ids,
            withdrawn_player_ids=field.withdrawn_player_ids,
            main_seed_player_ids=main_seed_player_ids,
            qualification_seed_player_ids=qualification_seed_player_ids,
        )