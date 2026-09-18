"""Canonical ranking-snapshot field cuts and pre-draw withdrawal repair."""

from __future__ import annotations

import hashlib
import json
from typing import Iterable, Literal

from pydantic import Field, model_validator

from beta_engine.domain.rankings.official import FrozenInput
from beta_engine.domain.tournaments.ranking_snapshot_authority import (
    TournamentRankingSnapshotAuthority,
)


EntryWindow = Literal["main", "qualification"]
FieldResolutionMode = Literal["initial", "pre_draw_repair"]


class TournamentEntryApplication(FrozenInput):
    """Caller-resolved active application evidence for one Tournament Edition.

    This model deliberately does not decide application eligibility, deadlines,
    commitments or AI behavior. Those are upstream authorities. It only preserves
    the facts needed by the canonical ranking cut, including the Main-vs-
    Qualification entry window and the stable NR ordering evidence required by
    the Master Vision.
    """

    application_id: str = Field(min_length=1)
    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    event_id: str = Field(min_length=1)
    player_id: str = Field(min_length=1)
    entry_window: EntryWindow
    decision_slot_ordinal: int = Field(ge=0)
    nr_tie_break_token: str = Field(min_length=1)
    eligible: bool = True


class TournamentEntryFieldCapacity(FrozenInput):
    main_draw_size: int = Field(ge=1)
    qualification_draw_size: int = Field(default=0, ge=0)
    qualifier_spots: int = Field(default=0, ge=0)
    wild_card_slots: int = Field(default=0, ge=0)
    bye_slots: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def validate_reserved_main_slots(self) -> "TournamentEntryFieldCapacity":
        reserved = self.qualifier_spots + self.wild_card_slots + self.bye_slots
        if reserved > self.main_draw_size:
            raise ValueError("Reserved Main Draw slots exceed Main Draw capacity")
        return self

    @property
    def direct_main_slots(self) -> int:
        return (
            self.main_draw_size
            - self.qualifier_spots
            - self.wild_card_slots
            - self.bye_slots
        )


class TournamentEntryField(FrozenInput):
    schema_version: Literal["tournament_entry_field.v1"] = "tournament_entry_field.v1"
    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    event_id: str = Field(min_length=1)
    mode: FieldResolutionMode
    capacity: TournamentEntryFieldCapacity
    tournament_ranking_authority_fingerprint: str = Field(
        pattern=r"^[0-9a-f]{64}$"
    )
    ranking_snapshot_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    applications_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    direct_main_player_ids: tuple[str, ...] = ()
    qualification_player_ids: tuple[str, ...] = ()
    below_qualification_cut_player_ids: tuple[str, ...] = ()
    withdrawn_player_ids: tuple[str, ...] = ()
    base_field_fingerprint: str | None = Field(
        default=None, pattern=r"^[0-9a-f]{64}$"
    )

    @model_validator(mode="after")
    def validate_partition(self) -> "TournamentEntryField":
        partitions = (
            self.direct_main_player_ids,
            self.qualification_player_ids,
            self.below_qualification_cut_player_ids,
        )
        ids = [player_id for group in partitions for player_id in group]
        if len(ids) != len(set(ids)):
            raise ValueError("Tournament field contains a player more than once")
        if set(ids) & set(self.withdrawn_player_ids):
            raise ValueError("Withdrawn player remains in active tournament field")
        if len(set(self.withdrawn_player_ids)) != len(self.withdrawn_player_ids):
            raise ValueError("Withdrawn player identities must be unique")
        if len(self.direct_main_player_ids) > self.capacity.direct_main_slots:
            raise ValueError("Direct Main Draw field exceeds capacity")
        if len(self.qualification_player_ids) > self.capacity.qualification_draw_size:
            raise ValueError("Qualification field exceeds capacity")
        if self.mode == "initial" and self.base_field_fingerprint is not None:
            raise ValueError("Initial field cannot reference a predecessor field")
        if self.mode == "pre_draw_repair" and self.base_field_fingerprint is None:
            raise ValueError("Pre-draw repair requires predecessor field identity")
        return self

    @property
    def fingerprint(self) -> str:
        return _fingerprint(self.model_dump(mode="json"))


class TournamentEntryFieldResolver:
    """Resolve ranking-derived field positions without inventing lifecycle policy."""

    @classmethod
    def build_initial(
        cls,
        *,
        authority: TournamentRankingSnapshotAuthority,
        applications: Iterable[TournamentEntryApplication],
        capacity: TournamentEntryFieldCapacity,
    ) -> TournamentEntryField:
        apps = cls._canonical_applications(authority, applications)
        applications_fp = cls._applications_fingerprint(apps)
        eligible = tuple(app for app in apps if app.eligible)
        cls._validate_nr_tokens(authority, eligible)

        main_window = tuple(
            app for app in eligible if app.entry_window == "main"
        )
        qualification_window = tuple(
            app for app in eligible if app.entry_window == "qualification"
        )
        ordered_main = cls._ranked(authority, main_window)
        direct = ordered_main[: capacity.direct_main_slots]
        remaining_main = ordered_main[capacity.direct_main_slots :]

        qualification_pool = cls._ranked(
            authority, (*remaining_main, *qualification_window)
        )
        qualification = qualification_pool[: capacity.qualification_draw_size]
        below_qualification_cut = qualification_pool[capacity.qualification_draw_size :]

        return TournamentEntryField(
            run_id=authority.run_id,
            branch_id=authority.branch_id,
            event_id=authority.event_id,
            mode="initial",
            capacity=capacity,
            tournament_ranking_authority_fingerprint=authority.fingerprint,
            ranking_snapshot_fingerprint=authority.ranking_snapshot_fingerprint,
            applications_fingerprint=applications_fp,
            direct_main_player_ids=tuple(app.player_id for app in direct),
            qualification_player_ids=tuple(
                app.player_id for app in qualification
            ),
            below_qualification_cut_player_ids=tuple(
                app.player_id for app in below_qualification_cut
            ),
        )

    @classmethod
    def repair_pre_draw(
        cls,
        *,
        authority: TournamentRankingSnapshotAuthority,
        applications: Iterable[TournamentEntryApplication],
        previous: TournamentEntryField,
        withdrawn_player_ids: Iterable[str],
    ) -> TournamentEntryField:
        apps = cls._canonical_applications(authority, applications)
        applications_fp = cls._applications_fingerprint(apps)
        cls._validate_previous(
            authority=authority,
            previous=previous,
            applications_fingerprint=applications_fp,
        )
        eligible = tuple(app for app in apps if app.eligible)
        cls._validate_nr_tokens(authority, eligible)
        apps_by_player = {app.player_id: app for app in eligible}

        active_before = set(
            previous.direct_main_player_ids
            + previous.qualification_player_ids
            + previous.below_qualification_cut_player_ids
        )
        requested = tuple(sorted(set(withdrawn_player_ids)))
        unknown = [player_id for player_id in requested if player_id not in active_before]
        if unknown:
            raise ValueError(
                "Pre-draw withdrawal references player outside predecessor field: "
                + ", ".join(unknown)
            )

        withdrawn = set(previous.withdrawn_player_ids) | set(requested)
        withdrawn_from_main = sum(
            player_id in set(previous.direct_main_player_ids)
            for player_id in requested
        )
        surviving_main = [
            apps_by_player[player_id]
            for player_id in previous.direct_main_player_ids
            if player_id not in withdrawn
        ]
        candidate_pool = cls._ranked(
            authority,
            tuple(
                apps_by_player[player_id]
                for player_id in (
                    previous.qualification_player_ids
                    + previous.below_qualification_cut_player_ids
                )
                if player_id not in withdrawn
            ),
        )

        promoted = candidate_pool[:withdrawn_from_main]
        remaining = candidate_pool[withdrawn_from_main:]
        qualification_target = len(previous.qualification_player_ids)
        qualification = remaining[:qualification_target]
        below_qualification_cut = remaining[qualification_target:]

        direct = cls._ranked(authority, (*surviving_main, *promoted))
        return TournamentEntryField(
            run_id=authority.run_id,
            branch_id=authority.branch_id,
            event_id=authority.event_id,
            mode="pre_draw_repair",
            capacity=previous.capacity,
            tournament_ranking_authority_fingerprint=authority.fingerprint,
            ranking_snapshot_fingerprint=authority.ranking_snapshot_fingerprint,
            applications_fingerprint=applications_fp,
            direct_main_player_ids=tuple(app.player_id for app in direct),
            qualification_player_ids=tuple(
                app.player_id for app in qualification
            ),
            below_qualification_cut_player_ids=tuple(
                app.player_id for app in below_qualification_cut
            ),
            withdrawn_player_ids=tuple(sorted(withdrawn)),
            base_field_fingerprint=previous.fingerprint,
        )

    @staticmethod
    def _canonical_applications(
        authority: TournamentRankingSnapshotAuthority,
        applications: Iterable[TournamentEntryApplication],
    ) -> tuple[TournamentEntryApplication, ...]:
        apps = tuple(
            TournamentEntryApplication.model_validate_json(app.model_dump_json())
            for app in applications
        )
        application_ids = [app.application_id for app in apps]
        player_ids = [app.player_id for app in apps]
        if len(application_ids) != len(set(application_ids)):
            raise ValueError("Duplicate Tournament Entry/Application identity")
        if len(player_ids) != len(set(player_ids)):
            raise ValueError("More than one active application exists for one player")
        for app in apps:
            if (app.run_id, app.branch_id, app.event_id) != (
                authority.run_id,
                authority.branch_id,
                authority.event_id,
            ):
                raise ValueError("Tournament application scope differs from ranking authority")
        return tuple(sorted(apps, key=lambda app: app.application_id))

    @classmethod
    def _ranked(
        cls,
        authority: TournamentRankingSnapshotAuthority,
        applications: Iterable[TournamentEntryApplication],
    ) -> tuple[TournamentEntryApplication, ...]:
        rank_by_player = {
            row.player_id: row.rank
            for row in authority.ranking_snapshot.rows
        }

        def key(app: TournamentEntryApplication):
            rank = rank_by_player.get(app.player_id)
            if rank is not None:
                return (0, rank, 0, "")
            return (
                1,
                app.decision_slot_ordinal,
                0,
                app.nr_tie_break_token,
            )

        return tuple(sorted(applications, key=key))

    @staticmethod
    def _validate_nr_tokens(
        authority: TournamentRankingSnapshotAuthority,
        applications: Iterable[TournamentEntryApplication],
    ) -> None:
        ranked = {
            row.player_id for row in authority.ranking_snapshot.rows
        }
        nr_tokens = [
            app.nr_tie_break_token
            for app in applications
            if app.player_id not in ranked
        ]
        if len(nr_tokens) != len(set(nr_tokens)):
            raise ValueError(
                "NR Tournament Entry/Application tie-break tokens must be unique"
            )

    @staticmethod
    def _applications_fingerprint(
        applications: tuple[TournamentEntryApplication, ...],
    ) -> str:
        return _fingerprint(
            [app.model_dump(mode="json") for app in applications]
        )

    @staticmethod
    def _validate_previous(
        *,
        authority: TournamentRankingSnapshotAuthority,
        previous: TournamentEntryField,
        applications_fingerprint: str,
    ) -> None:
        if (previous.run_id, previous.branch_id, previous.event_id) != (
            authority.run_id,
            authority.branch_id,
            authority.event_id,
        ):
            raise ValueError("Predecessor tournament field scope differs")
        if (
            previous.tournament_ranking_authority_fingerprint
            != authority.fingerprint
            or previous.ranking_snapshot_fingerprint
            != authority.ranking_snapshot_fingerprint
        ):
            raise ValueError("Predecessor tournament field ranking authority changed")
        if previous.applications_fingerprint != applications_fingerprint:
            raise ValueError(
                "Pre-draw repair application set changed; rebuild the field explicitly"
            )


def _fingerprint(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()
