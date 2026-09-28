"""Persistence for immutable Tournament Edition format authority."""

from __future__ import annotations

import hashlib
import json
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from beta_engine.application.calendar_package_run_adapter import (
    CALENDAR_EVENT_ENTITY_KIND,
    CalendarPackageRunAdapter,
)
from beta_engine.domain.run_packages import PackageType
from beta_engine.domain.tournaments.models import CalendarEvent
from beta_engine.infrastructure.db.run_package_state import get_run_package_state

from beta_engine.domain.tournaments.format_authority import (
    TournamentFormatAuthority,
    TournamentFormatKind,
    TournamentGroupCrossingMatch,
    TournamentGroupMatchBestOf,
    TournamentGroupSeedPlacement,
    TournamentGroupFormatConfiguration,
)
from beta_engine.infrastructure.db.models import (
    RunBranchModel,
    RunContainerModel,
    TournamentFormatAuthorityModel,
)
from beta_engine.infrastructure.db.tournament_entry_field import TournamentEntryFieldStore
from beta_engine.infrastructure.db.tournament_group_rules_policy import (
    TournamentGroupRulesPolicyStore,
)


class TournamentFormatAuthorityConflict(ValueError):
    """A format configuration conflicts with immutable Tournament Edition history."""


def _request_fingerprint(payload: dict) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


class TournamentFormatAuthorityStore:
    def __init__(self, session: Session):
        self.session = session

    def _scope(self, run_id: str, branch_id: str, *, writing: bool = False) -> None:
        run = self.session.get(RunContainerModel, run_id)
        branch = self.session.get(RunBranchModel, branch_id)
        if run is None or branch is None or branch.run_id != run_id:
            raise ValueError("Tournament Format Run/Branch scope does not exist")
        if writing and (run.read_only or branch.read_only or branch.status == "archived"):
            raise ValueError("Tournament Format scope is not writable")

    def _target_season_index(
        self, *, run_id: str, branch_id: str, event_id: str, field
    ) -> int:
        if field.source_kind == "finals_participant_selection":
            if field.finals_target_season_index is None:
                raise ValueError("Finals Entry Field is missing target season identity")
            return field.finals_target_season_index

        state = get_run_package_state(
            self.session,
            run_id=run_id,
            branch_id=branch_id,
        )
        if state is None:
            raise ValueError(
                "Tournament Format requires Run-owned Calendar Edition season"
            )
        candidates = [
            entity
            for entity in state.entities
            if entity.entity_kind == CALENDAR_EVENT_ENTITY_KIND
            and entity.source_entity_id == event_id
        ]
        if len(candidates) != 1:
            raise ValueError(
                "Tournament Format requires one unambiguous Run-owned Calendar Edition"
            )
        entity = candidates[0]
        event = CalendarEvent.model_validate(entity.payload)
        if event.event_id != event_id:
            raise ValueError("Tournament Format Calendar event identity mismatch")
        package_id = CalendarPackageRunAdapter.package_id_for_season(str(event.season))
        if entity.source_package_id != package_id:
            raise ValueError("Tournament Format Calendar Package identity mismatch")
        matching_versions = [
            version
            for version in state.package_versions
            if version.package_id == package_id
            and version.package_type == PackageType.CALENDAR
            and version.source_version == entity.source_package_version
            and version.source_fingerprint == entity.source_package_fingerprint
        ]
        if len(matching_versions) != 1:
            raise ValueError(
                "Tournament Format Calendar Edition provenance is inconsistent"
            )
        season_value = event.season
        if isinstance(season_value, int):
            start_year = season_value
        else:
            try:
                start_year = int(str(season_value).split("/", 1)[0])
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    "Tournament Format Calendar Edition season is invalid"
                ) from exc
        target = start_year - 2000
        if not 0 <= target <= 49:
            raise ValueError(
                "Tournament Format Calendar Edition season is outside Run timeline"
            )
        return target

    @staticmethod
    def _request(
        *,
        field_fingerprint: str,
        target_season_index: int,
        format_kind: TournamentFormatKind,
        group_count: int | None,
        group_size: int | None,
        seeded_slots_per_group: int,
        group_seed_placements: tuple[TournamentGroupSeedPlacement, ...],
        match_best_of_override: TournamentGroupMatchBestOf | None,
        advancing_per_group: int,
        knockout_crossings: tuple[TournamentGroupCrossingMatch, ...],
        group_rules_policy_fingerprint: str | None,
    ) -> dict:
        return {
            "field_fingerprint": field_fingerprint,
            "target_season_index": target_season_index,
            "format_kind": format_kind,
            "group_count": group_count,
            "group_size": group_size,
            "seeded_slots_per_group": seeded_slots_per_group,
            "group_seed_placements": [
                value.model_dump(mode="json") for value in group_seed_placements
            ],
            "match_best_of_override": match_best_of_override,
            "advancing_per_group": advancing_per_group,
            "knockout_crossings": [
                value.model_dump(mode="json") for value in knockout_crossings
            ],
            "group_rules_policy_fingerprint": group_rules_policy_fingerprint,
        }

    @staticmethod
    def validate_row(
        row: TournamentFormatAuthorityModel,
        *,
        field,
        group_rules_policy=None,
    ) -> TournamentFormatAuthority:
        authority = TournamentFormatAuthority.model_validate_json(row.payload_json)
        if (
            authority.run_id,
            authority.branch_id,
            authority.event_id,
            authority.configured_by_command_id,
            authority.entry_field_fingerprint,
            authority.fingerprint,
        ) != (
            row.run_id,
            row.branch_id,
            row.event_id,
            row.command_id,
            row.entry_field_fingerprint,
            row.authority_fingerprint,
        ):
            raise ValueError("Stored Tournament Format authority is corrupt")
        if field.fingerprint != row.entry_field_fingerprint:
            raise ValueError("Tournament Format authority references stale Entry Field")
        configured_policy_fp = (
            authority.group_configuration.group_rules_policy_fingerprint
            if authority.group_configuration is not None
            else None
        )
        if configured_policy_fp != row.group_rules_policy_fingerprint:
            raise ValueError("Tournament Format group-rules fingerprint row is corrupt")
        if configured_policy_fp is not None:
            if group_rules_policy is None:
                raise ValueError(
                    "Tournament Format authority references missing group-rules policy"
                )
            if group_rules_policy.fingerprint != configured_policy_fp:
                raise ValueError(
                    "Tournament Format authority group-rules policy is stale"
                )
            group = authority.group_configuration
            assert group is not None
            if (
                group.group_rules_effective_from_season_index
                != group_rules_policy.effective_from_season_index
            ):
                raise ValueError(
                    "Tournament Format authority group-rules season provenance is corrupt"
                )
            if (
                group.rules_source_kind == "season_policy"
                and group.match_best_of != group_rules_policy.default_match_best_of
            ):
                raise ValueError(
                    "Inherited Tournament group match format differs from season policy"
                )
        return authority

    def get(
        self, *, run_id: str, branch_id: str, event_id: str
    ) -> TournamentFormatAuthority | None:
        self._scope(run_id, branch_id)
        row = self.session.get(
            TournamentFormatAuthorityModel,
            (run_id, branch_id, event_id),
        )
        if row is None:
            return None
        history = TournamentEntryFieldStore(self.session).history(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
        )
        if not history:
            raise ValueError(
                "Tournament Format authority references missing Entry Field history"
            )
        field = history[-1]
        raw = TournamentFormatAuthority.model_validate_json(row.payload_json)
        policy = None
        if raw.group_configuration is not None:
            policy = TournamentGroupRulesPolicyStore(self.session).get_by_fingerprint(
                run_id=run_id,
                branch_id=branch_id,
                authority_fingerprint=(
                    raw.group_configuration.group_rules_policy_fingerprint
                ),
            )
        return self.validate_row(row, field=field, group_rules_policy=policy)

    def configure(
        self,
        *,
        run_id: str,
        branch_id: str,
        event_id: str,
        command_id: str,
        format_kind: TournamentFormatKind,
        group_count: int | None = None,
        group_size: int | None = None,
        seeded_slots_per_group: int = 0,
        group_seed_placements: Iterable[TournamentGroupSeedPlacement] = (),
        match_best_of_override: TournamentGroupMatchBestOf | None = None,
        advancing_per_group: int = 0,
        knockout_crossings: Iterable[TournamentGroupCrossingMatch] = (),
    ) -> TournamentFormatAuthority:
        self._scope(run_id, branch_id, writing=True)
        if not command_id.strip() or len(command_id) > 128:
            raise ValueError("Tournament Format requires a valid command ID")

        history = TournamentEntryFieldStore(self.session).history(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
        )
        if not history:
            raise ValueError("Tournament Format requires canonical Entry Field")
        field = history[-1]
        target_season_index = self._target_season_index(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
            field=field,
        )
        placements = tuple(group_seed_placements)
        crossings = tuple(knockout_crossings)

        policy = None
        group_configuration = None
        if format_kind in {"groups", "groups_knockout"}:
            if group_count is None or group_size is None:
                raise ValueError("Group-based Tournament Format requires group count and size")
            if group_count * group_size != len(field.direct_main_player_ids):
                raise ValueError(
                    "Group configuration must exactly partition the current participant field into equal groups"
                )
            if (
                field.qualification_player_ids
                or field.capacity.qualifier_spots
                or field.capacity.wild_card_slots
                or field.capacity.bye_slots
            ):
                raise ValueError(
                    "Group format currently requires a fully resolved participant field without Qualification/WC/BYE reservations"
                )
            policy = TournamentGroupRulesPolicyStore(self.session).resolve(
                run_id=run_id,
                branch_id=branch_id,
                target_season_index=target_season_index,
            )
            if policy is None:
                raise ValueError(
                    "Group-based Tournament Format requires an effective season group-rules policy"
                )
            match_best_of = (
                policy.default_match_best_of
                if match_best_of_override is None
                else match_best_of_override
            )
            group_configuration = TournamentGroupFormatConfiguration(
                group_count=group_count,
                group_size=group_size,
                seeded_slots_per_group=seeded_slots_per_group,
                group_seed_placements=placements,
                match_best_of=match_best_of,
                rules_source_kind=(
                    "season_policy"
                    if match_best_of_override is None
                    else "edition_override"
                ),
                group_rules_policy_fingerprint=policy.fingerprint,
                group_rules_effective_from_season_index=(
                    policy.effective_from_season_index
                ),
                advancing_per_group=advancing_per_group,
                knockout_crossings=crossings,
            )
        else:
            if any(
                (
                    group_count is not None,
                    group_size is not None,
                    seeded_slots_per_group,
                    placements,
                    match_best_of_override is not None,
                    advancing_per_group,
                    crossings,
                )
            ):
                raise ValueError(
                    "Knockout Tournament Format cannot carry group configuration"
                )

        proposed = TournamentFormatAuthority(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
            target_season_index=target_season_index,
            configured_by_command_id=command_id,
            entry_field_fingerprint=field.fingerprint,
            format_kind=format_kind,
            group_configuration=group_configuration,
        )
        request = self._request(
            field_fingerprint=field.fingerprint,
            target_season_index=target_season_index,
            format_kind=format_kind,
            group_count=group_count,
            group_size=group_size,
            seeded_slots_per_group=seeded_slots_per_group,
            group_seed_placements=placements,
            match_best_of_override=match_best_of_override,
            advancing_per_group=advancing_per_group,
            knockout_crossings=crossings,
            group_rules_policy_fingerprint=(
                policy.fingerprint if policy is not None else None
            ),
        )
        request_fp = _request_fingerprint(request)

        retry = self.session.scalar(
            select(TournamentFormatAuthorityModel).where(
                TournamentFormatAuthorityModel.run_id == run_id,
                TournamentFormatAuthorityModel.branch_id == branch_id,
                TournamentFormatAuthorityModel.command_id == command_id,
            )
        )
        if retry is not None:
            if (
                retry.event_id != event_id
                or retry.request_fingerprint != request_fp
            ):
                raise TournamentFormatAuthorityConflict(
                    "Tournament Format command ID already has a different request"
                )
            return self.validate_row(
                retry,
                field=field,
                group_rules_policy=policy,
            )

        existing = self.session.get(
            TournamentFormatAuthorityModel,
            (run_id, branch_id, event_id),
        )
        if existing is not None:
            raise TournamentFormatAuthorityConflict(
                "Tournament Edition already has immutable Format authority"
            )

        self.session.add(
            TournamentFormatAuthorityModel(
                run_id=run_id,
                branch_id=branch_id,
                event_id=event_id,
                command_id=command_id,
                request_fingerprint=request_fp,
                authority_fingerprint=proposed.fingerprint,
                entry_field_fingerprint=field.fingerprint,
                group_rules_policy_fingerprint=(
                    policy.fingerprint if policy is not None else None
                ),
                payload_json=proposed.model_dump_json(),
            )
        )
        self.session.flush()
        return proposed
