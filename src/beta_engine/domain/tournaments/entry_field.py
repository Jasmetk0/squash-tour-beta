"""Canonical ranking-snapshot field cuts and pre-draw withdrawal repair."""

from __future__ import annotations

import hashlib
import json
from typing import Iterable, Literal

from pydantic import Field, model_validator

from beta_engine.domain.rankings.official import FrozenInput
from beta_engine.domain.tournaments.bracket_diagnostics import (
    TournamentBracketDiagnostic,
    main_bracket_diagnostics,
)
from beta_engine.domain.tournaments.ranking_snapshot_authority import (
    TournamentRankingSnapshotAuthority,
)


EntryWindow = Literal["main", "qualification"]
FieldResolutionMode = Literal["initial", "pre_draw_repair"]
EntryFieldGeometry = Literal["classic_bracket", "fixed_participant_field"]
EntryFieldSourceKind = Literal["ranking_applications", "finals_participant_selection"]


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
    decision_slot_ordinal: int = Field(ge=1)
    nr_tie_break_token: str = Field(min_length=1)
    eligible: bool = True


class TournamentEntryFieldCapacity(FrozenInput):
    geometry_kind: EntryFieldGeometry = "classic_bracket"
    main_draw_size: int = Field(ge=1, le=128)
    qualification_draw_size: int = Field(default=0, ge=0)
    qualifier_spots: int = Field(default=0, ge=0)
    wild_card_slots: int = Field(default=0, ge=0)
    bye_slots: int = Field(default=0, ge=0)

    @classmethod
    def for_main_entrant_count(
        cls,
        *,
        main_entrant_count: int,
        qualification_draw_size: int = 0,
        qualifier_spots: int = 0,
        wild_card_slots: int = 0,
    ) -> "TournamentEntryFieldCapacity":
        """Derive classic Main bracket capacity and explicit BYEs from entrants."""

        if main_entrant_count < 2:
            raise ValueError("Classic Main Draw requires at least two entrants")
        if main_entrant_count > 128:
            raise ValueError(
                "Classic Main Draw supports at most 128 entrants in the current version"
            )
        reserved_non_bye = qualifier_spots + wild_card_slots
        if reserved_non_bye > main_entrant_count:
            raise ValueError(
                "Qualifier and Wild Card slots exceed requested Main entrants"
            )
        bracket_capacity = 1 << (main_entrant_count - 1).bit_length()
        return cls(
            main_draw_size=bracket_capacity,
            qualification_draw_size=qualification_draw_size,
            qualifier_spots=qualifier_spots,
            wild_card_slots=wild_card_slots,
            bye_slots=bracket_capacity - main_entrant_count,
        )

    @model_validator(mode="after")
    def validate_capacity(self) -> "TournamentEntryFieldCapacity":
        reserved = self.qualifier_spots + self.wild_card_slots + self.bye_slots
        if reserved > self.main_draw_size:
            raise ValueError("Reserved Main Draw slots exceed Main Draw capacity")
        if self.geometry_kind == "classic_bracket":
            if self.main_draw_size < 2 or self.main_draw_size & (self.main_draw_size - 1):
                raise ValueError(
                    "Classic Main Draw capacity must be one of 2, 4, 8, 16, 32, 64, 128"
                )
        else:
            if (
                self.qualification_draw_size
                or self.qualifier_spots
                or self.wild_card_slots
                or self.bye_slots
            ):
                raise ValueError(
                    "Fixed participant field cannot reserve Qualification, Wild Card or BYE slots"
                )
        return self

    @property
    def main_diagnostics(self) -> tuple[TournamentBracketDiagnostic, ...]:
        """Derived Admin diagnostics; not persisted and not part of field identity."""

        if self.geometry_kind != "classic_bracket":
            return ()
        entrant_count = self.main_draw_size - self.bye_slots
        return main_bracket_diagnostics(
            entrant_count=entrant_count,
            bracket_capacity=self.main_draw_size,
            bye_count=self.bye_slots,
        )

    @property
    def direct_main_slots(self) -> int:
        return (
            self.main_draw_size
            - self.qualifier_spots
            - self.wild_card_slots
            - self.bye_slots
        )


class TournamentEntryField(FrozenInput):
    schema_version: Literal[
        "tournament_entry_field.v1",
        "tournament_entry_field.v2",
    ] = "tournament_entry_field.v1"
    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    event_id: str = Field(min_length=1)
    mode: FieldResolutionMode
    capacity: TournamentEntryFieldCapacity
    source_kind: EntryFieldSourceKind = "ranking_applications"
    tournament_ranking_authority_fingerprint: str | None = Field(
        default=None, pattern=r"^[0-9a-f]{64}$"
    )
    ranking_snapshot_fingerprint: str | None = Field(
        default=None, pattern=r"^[0-9a-f]{64}$"
    )
    finals_participant_selection_fingerprint: str | None = Field(
        default=None, pattern=r"^[0-9a-f]{64}$"
    )
    finals_race_snapshot_fingerprint: str | None = Field(
        default=None, pattern=r"^[0-9a-f]{64}$"
    )
    finals_target_season_index: int | None = Field(default=None, ge=0, le=49)
    seed_order_player_ids: tuple[str, ...] = ()
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

        if self.source_kind == "ranking_applications":
            if (
                self.tournament_ranking_authority_fingerprint is None
                or self.ranking_snapshot_fingerprint is None
            ):
                raise ValueError(
                    "Ranking/Application Entry Field requires Ranking Snapshot authority"
                )
            if (
                self.finals_participant_selection_fingerprint is not None
                or self.finals_race_snapshot_fingerprint is not None
                or self.finals_target_season_index is not None
                or self.seed_order_player_ids
            ):
                raise ValueError(
                    "Ranking/Application Entry Field cannot carry Finals selection authority"
                )
        else:
            if self.schema_version != "tournament_entry_field.v2":
                raise ValueError(
                    "Finals participant Entry Field requires tournament_entry_field.v2"
                )
            if (
                self.tournament_ranking_authority_fingerprint is not None
                or self.ranking_snapshot_fingerprint is not None
            ):
                raise ValueError(
                    "Finals participant Entry Field cannot depend on Official Ranking authority"
                )
            if (
                self.finals_participant_selection_fingerprint is None
                or self.finals_race_snapshot_fingerprint is None
                or self.finals_target_season_index is None
            ):
                raise ValueError(
                    "Finals participant Entry Field requires frozen participant/Race authority"
                )
            if self.capacity.geometry_kind != "fixed_participant_field":
                raise ValueError(
                    "Finals participant Entry Field requires fixed participant geometry"
                )
            if self.mode != "initial":
                raise ValueError(
                    "Finals participant Entry Field repairs use the separate replacement authority"
                )
            if (
                self.qualification_player_ids
                or self.below_qualification_cut_player_ids
                or self.withdrawn_player_ids
            ):
                raise ValueError(
                    "Initial Finals participant Entry Field contains only selected participants"
                )
            if self.seed_order_player_ids != self.direct_main_player_ids:
                raise ValueError(
                    "Finals Entry Field seed order must equal frozen Race-selected participant order"
                )
            if len(self.direct_main_player_ids) != self.capacity.main_draw_size:
                raise ValueError(
                    "Finals Entry Field must exactly fill configured participant capacity"
                )
            if self.applications_fingerprint != _fingerprint([]):
                raise ValueError(
                    "Finals participant Entry Field cannot fabricate application evidence"
                )
        return self

    @property
    def source_authority_fingerprint(self) -> str:
        if self.source_kind == "ranking_applications":
            assert self.tournament_ranking_authority_fingerprint is not None
            return self.tournament_ranking_authority_fingerprint
        assert self.finals_participant_selection_fingerprint is not None
        return self.finals_participant_selection_fingerprint

    @property
    def active_main_entrant_count(self) -> int:
        """Current non-BYE Main entrants represented by this field.

        Direct players are materialized identities. Qualification and Wild Card
        capacity remains reserved as future Main entrants until those authorities
        resolve the exact identities.
        """

        return (
            len(self.direct_main_player_ids)
            + self.capacity.qualifier_spots
            + self.capacity.wild_card_slots
        )

    @property
    def effective_main_bye_count(self) -> int:
        """Current Main vacancies that will be represented as BYEs if unresolved."""

        return self.capacity.main_draw_size - self.active_main_entrant_count

    @property
    def main_diagnostics(self) -> tuple[TournamentBracketDiagnostic, ...]:
        """Derived Admin warnings for the *current* field, never persisted."""

        if self.capacity.geometry_kind != "classic_bracket":
            return ()
        entrant_count = self.active_main_entrant_count
        if entrant_count < 2:
            # The bracket itself cannot execute below two entrants. Keep inspection
            # readable; hard validity remains owned by the draw-generation boundary.
            return ()
        return main_bracket_diagnostics(
            entrant_count=entrant_count,
            bracket_capacity=self.capacity.main_draw_size,
            bye_count=self.effective_main_bye_count,
        )

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
    def build_from_finals_participant_selection(
        cls,
        *,
        selection,
    ) -> TournamentEntryField:
        """Materialize the frozen Finals selected field without inventing applications.

        Participant order is already authoritative Race order from the Finals selection
        snapshot. This adapter deliberately does not consult Official Ranking and does not
        choose a tournament format; it only feeds the selected identities/order into the
        shared Tournament Preparation Entry Field boundary.
        """

        player_ids = tuple(player.player_id for player in selection.participants)
        if len(player_ids) != selection.participant_capacity:
            raise ValueError(
                "Finals participant selection does not exactly fill configured capacity"
            )
        if tuple(player.seed for player in selection.participants) != tuple(
            range(1, len(selection.participants) + 1)
        ):
            raise ValueError("Finals participant selection seed order is not canonical")
        return TournamentEntryField(
            schema_version="tournament_entry_field.v2",
            run_id=selection.run_id,
            branch_id=selection.branch_id,
            event_id=selection.finals_event_id,
            mode="initial",
            capacity=TournamentEntryFieldCapacity(
                geometry_kind="fixed_participant_field",
                main_draw_size=selection.participant_capacity,
            ),
            source_kind="finals_participant_selection",
            finals_participant_selection_fingerprint=selection.fingerprint,
            finals_race_snapshot_fingerprint=selection.race_snapshot_fingerprint,
            finals_target_season_index=selection.target_season_index,
            seed_order_player_ids=player_ids,
            applications_fingerprint=_fingerprint([]),
            direct_main_player_ids=player_ids,
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
        already_withdrawn = set(previous.withdrawn_player_ids)
        requested = tuple(sorted(set(withdrawn_player_ids)))
        unknown = [
            player_id
            for player_id in requested
            if player_id not in active_before and player_id not in already_withdrawn
        ]
        if unknown:
            raise ValueError(
                "Pre-draw withdrawal references player outside predecessor field: "
                + ", ".join(unknown)
            )
        newly_withdrawn = tuple(
            player_id for player_id in requested if player_id not in already_withdrawn
        )
        if not newly_withdrawn:
            return previous

        withdrawn = already_withdrawn | set(newly_withdrawn)
        previous_main = set(previous.direct_main_player_ids)
        withdrawn_from_main = sum(
            player_id in previous_main for player_id in newly_withdrawn
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
