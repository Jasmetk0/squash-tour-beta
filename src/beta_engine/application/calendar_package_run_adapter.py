"""Adapt persisted season calendars to canonical Run Package documents."""

from __future__ import annotations

import re
from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, Field

from beta_engine.application.season_calendar_service import SeasonCalendarService
from beta_engine.domain.run_packages import (
    CanonicalPackageDocument,
    PackageEntity,
    PackageType,
    RunPackageState,
    TECHNICAL_ID_PATTERN,
    canonical_hash,
)
from beta_engine.domain.tournaments.models import SeasonCalendar, SeasonCalendarEvent


CALENDAR_METADATA_ENTITY_ID = "calendar.metadata"
CALENDAR_METADATA_ENTITY_KIND = "calendar.metadata.v1"
CALENDAR_EVENT_ENTITY_KIND = "calendar.event.v1"
CALENDAR_SCOPE = "season_calendar"


class RunCalendarEventProvenance(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    event_id: str
    run_local_id: int = Field(ge=1)
    source_package_version: int = Field(ge=1)
    source_package_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    entity_content_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")


class RunCalendarProjection(BaseModel):
    """Typed Run-owned season Calendar derived only from Run Package state."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    package_id: str
    run_id: str
    branch_id: str
    run_package_state_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    season: str
    calendar: SeasonCalendar
    provenance: tuple[RunCalendarEventProvenance, ...]

    @property
    def content_fingerprint(self) -> str:
        return canonical_hash(
            {
                "package_id": self.package_id,
                "season": self.season,
                "calendar": self.calendar.model_dump(mode="json"),
                "provenance": [
                    item.model_dump(mode="json") for item in self.provenance
                ],
            }
        )

    @property
    def fingerprint(self) -> str:
        return canonical_hash(self.model_dump(mode="json"))


@dataclass(slots=True)
class CalendarPackageRunAdapter:
    calendar_service: SeasonCalendarService

    @staticmethod
    def package_id_for_season(season: str) -> str:
        package_id = f"calendar-{season.replace('/', '-')}"
        if re.fullmatch(TECHNICAL_ID_PATTERN, package_id) is None:
            raise ValueError(
                f"Season '{season}' cannot be mapped to a canonical Calendar package_id"
            )
        return package_id

    def build_document(
        self, season: str, *, source_version: int = 1
    ) -> CanonicalPackageDocument:
        result = self.calendar_service.get_calendar(season=season)
        calendar = result.calendar
        if calendar is None:
            raise KeyError(f"Season calendar '{season}' was not found")
        if calendar.validation_errors:
            raise ValueError(
                f"Season calendar '{season}' has validation errors and cannot be packaged"
            )

        package_id = self.package_id_for_season(season)
        metadata_payload = {
            "season": str(calendar.season),
            "metadata": (
                calendar.metadata.model_dump(mode="json")
                if calendar.metadata is not None
                else None
            ),
            "validation_warnings": [
                item.model_dump(mode="json") for item in calendar.validation_warnings
            ],
            "validation_errors": [
                item.model_dump(mode="json") for item in calendar.validation_errors
            ],
        }
        entities = [
            PackageEntity(
                source_entity_id=CALENDAR_METADATA_ENTITY_ID,
                entity_kind=CALENDAR_METADATA_ENTITY_KIND,
                entity_schema_version=1,
                scope=CALENDAR_SCOPE,
                payload=metadata_payload,
            )
        ]
        for event in sorted(calendar.events, key=lambda item: item.event_id):
            entities.append(
                PackageEntity(
                    source_entity_id=event.event_id,
                    entity_kind=CALENDAR_EVENT_ENTITY_KIND,
                    entity_schema_version=1,
                    scope=CALENDAR_SCOPE,
                    payload=event.model_dump(mode="json"),
                )
            )

        return CanonicalPackageDocument(
            package_type=PackageType.CALENDAR,
            package_id=package_id,
            source_version=source_version,
            provenance={
                "adapter": "persisted_season_calendar.v1",
                "source_season": season,
                "source_calendar_fingerprint": canonical_hash(
                    calendar.model_dump(mode="json")
                ),
            },
            explicit_scope=(CALENDAR_SCOPE,),
            entities=tuple(entities),
        )

    @staticmethod
    def project_calendar(
        state: RunPackageState, *, package_id: str
    ) -> RunCalendarProjection:
        versions = [
            version
            for version in state.package_versions
            if version.package_id == package_id
            and version.package_type == PackageType.CALENDAR
        ]
        if not versions:
            raise ValueError(
                f"Run Package state has no applied Calendar Package '{package_id}'"
            )

        metadata_entities = [
            entity
            for entity in state.entities
            if entity.source_package_id == package_id
            and entity.entity_kind == CALENDAR_METADATA_ENTITY_KIND
        ]
        if len(metadata_entities) != 1:
            raise ValueError(
                f"Run Calendar Package '{package_id}' must contain one metadata entity"
            )
        metadata_payload = metadata_entities[0].payload
        season = str(metadata_payload.get("season", ""))
        if not season:
            raise ValueError("Run Calendar metadata is missing season")

        events: list[SeasonCalendarEvent] = []
        provenance: list[RunCalendarEventProvenance] = []
        seen_ids: set[str] = set()
        for entity in sorted(state.entities, key=lambda item: item.run_local_id):
            if (
                entity.source_package_id != package_id
                or entity.entity_kind != CALENDAR_EVENT_ENTITY_KIND
            ):
                continue
            event = SeasonCalendarEvent.model_validate(entity.payload)
            if event.event_id != entity.source_entity_id:
                raise ValueError(
                    "Run Calendar event source identity does not match event_id"
                )
            if str(event.season) != season:
                raise ValueError(
                    f"Run Calendar event '{event.event_id}' has mismatched season"
                )
            if event.event_id in seen_ids:
                raise ValueError(
                    f"Run Calendar projection contains duplicate event '{event.event_id}'"
                )
            seen_ids.add(event.event_id)
            events.append(event)
            provenance.append(
                RunCalendarEventProvenance(
                    event_id=event.event_id,
                    run_local_id=entity.run_local_id,
                    source_package_version=entity.source_package_version,
                    source_package_fingerprint=entity.source_package_fingerprint,
                    entity_content_fingerprint=entity.content_fingerprint,
                )
            )

        calendar = SeasonCalendar.model_validate(
            {
                "season": season,
                "events": [
                    event.model_dump(mode="json")
                    for event in sorted(events, key=lambda item: item.event_id)
                ],
                "metadata": metadata_payload.get("metadata"),
                "validation_warnings": metadata_payload.get(
                    "validation_warnings", []
                ),
                "validation_errors": metadata_payload.get("validation_errors", []),
            }
        )
        return RunCalendarProjection(
            package_id=package_id,
            run_id=state.run_id,
            branch_id=state.branch_id,
            run_package_state_fingerprint=state.fingerprint,
            season=season,
            calendar=calendar,
            provenance=tuple(
                sorted(provenance, key=lambda item: item.event_id)
            ),
        )
