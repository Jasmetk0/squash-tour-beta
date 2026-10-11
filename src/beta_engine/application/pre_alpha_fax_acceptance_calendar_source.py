"""Deterministic 80-Edition World Tour calendar source for pre-alpha release testing.

This is a release-test source, not FAX sporting canon. It instantiates existing
WORLD_TOUR template authorities repeatedly across the 61-week season so the long
acceptance can exercise production tournament orchestration at Master v72 scale.
"""

from __future__ import annotations

from dataclasses import dataclass

from beta_engine.application.calendar_package_run_adapter import (
    CALENDAR_EVENT_ENTITY_KIND,
    CALENDAR_METADATA_ENTITY_ID,
    CALENDAR_METADATA_ENTITY_KIND,
    CALENDAR_SCOPE,
    CalendarPackageRunAdapter,
)
from beta_engine.application.season_calendar_service import SeasonCalendarService
from beta_engine.application.tournament_templates_service import (
    TournamentTemplatesConfigService,
)
from beta_engine.domain.calendar.season_weeks import season_week_to_calendar_position
from beta_engine.domain.run_packages import (
    CanonicalPackageDocument,
    PackageEntity,
    PackageType,
    canonical_hash,
)
from beta_engine.domain.tournaments.models import (
    SeasonCalendar,
    SeasonCalendarEvent,
    SeasonCalendarMetadata,
    TournamentTemplate,
)

PRE_ALPHA_FAX_ACCEPTANCE_CALENDAR_SCHEMA = "pre_alpha_fax_acceptance_calendar.v1"
PRE_ALPHA_FAX_ACCEPTANCE_EDITION_COUNT = 80
PRE_ALPHA_FAX_ACCEPTANCE_SEASON = "2000/2001"
PRE_ALPHA_FAX_ACCEPTANCE_SEASON_WEEKS = 61


@dataclass(slots=True)
class PreAlphaFaxAcceptanceCalendarSource:
    template_service: TournamentTemplatesConfigService
    calendar_validation_service: SeasonCalendarService

    def _world_tour_templates(self) -> tuple[TournamentTemplate, ...]:
        templates = tuple(
            sorted(
                (
                    template
                    for template in self.template_service.list_templates()
                    if template.active and template.tour_level == "WORLD_TOUR"
                ),
                key=lambda item: (-item.prestige, item.category, item.template_id),
            )
        )
        if not templates:
            raise ValueError(
                "Pre-alpha FAX acceptance calendar requires at least one active WORLD_TOUR template"
            )
        return templates

    @staticmethod
    def _season_week(index: int) -> int:
        # Evenly map 80 zero-based Edition positions into SW1..SW61.
        return 1 + (index * PRE_ALPHA_FAX_ACCEPTANCE_SEASON_WEEKS) // (
            PRE_ALPHA_FAX_ACCEPTANCE_EDITION_COUNT
        )

    @staticmethod
    def _event(
        *,
        season: str,
        index: int,
        template: TournamentTemplate,
    ) -> SeasonCalendarEvent:
        season_week = PreAlphaFaxAcceptanceCalendarSource._season_week(index)
        duration = max(1, template.duration_in_season_weeks)
        if season_week + duration - 1 > PRE_ALPHA_FAX_ACCEPTANCE_SEASON_WEEKS:
            season_week = PRE_ALPHA_FAX_ACCEPTANCE_SEASON_WEEKS - duration + 1
        position = season_week_to_calendar_position(
            season=season,
            season_week=season_week,
        )
        template_payload = template.model_dump(mode="json")
        template_fingerprint = canonical_hash(template_payload)
        ordinal = index + 1
        return SeasonCalendarEvent(
            event_id=f"FAX-ACCEPT-WT-{ordinal:03d}",
            season=season,
            season_week=season_week,
            calendar_year=position.calendar_year,
            year_week=position.year_week,
            template_id=template.template_id,
            event_name=f"{template.event_name} [Acceptance {ordinal:03d}]",
            category=template.category,
            tour_level=template.tour_level,
            host_country=template.host_country,
            host_city=None,
            region=template.region,
            duration_in_season_weeks=duration,
            start_season_week=season_week,
            end_season_week=season_week + duration - 1,
            status="planned",
            main_draw_size=template.main_draw_size,
            qualification_draw_size=template.qualification_draw_size,
            seeds_count=template.seeds_count,
            qualifier_spots=template.qualifier_spots,
            wild_cards=template.wild_cards,
            byes=template.byes,
            point_distribution_ref=template.point_distribution_ref,
            point_distribution=template.point_distribution,
            ranking_status="ranked",
            ranking_points_table={},
            ranking_configuration_legacy=False,
            prize_money=template.prize_money,
            prize_money_currency=template.prize_money_currency,
            prize_money_table=dict(template.prize_money_table),
            prestige=template.prestige,
            event_level_overrides={
                "pre_alpha_release_fixture": True,
                "acceptance_ordinal": ordinal,
            },
            source_template_fingerprint=template_fingerprint,
            template_snapshot_fingerprint=template_fingerprint,
            template_snapshot=template_payload,
            is_world_tour=True,
            is_elite_tour=False,
            cluster_id=template.seasonal_grouping or "pre_alpha_acceptance",
            travel_group=template.region,
        )

    def build_calendar(
        self, season: str = PRE_ALPHA_FAX_ACCEPTANCE_SEASON
    ) -> SeasonCalendar:
        if season != PRE_ALPHA_FAX_ACCEPTANCE_SEASON:
            raise ValueError(
                "Pre-alpha FAX acceptance calendar V1 is defined only for 2000/2001"
            )
        templates = self._world_tour_templates()
        events = [
            self._event(
                season=season,
                index=index,
                template=templates[index % len(templates)],
            )
            for index in range(PRE_ALPHA_FAX_ACCEPTANCE_EDITION_COUNT)
        ]
        warnings, errors = self.calendar_validation_service.validate_calendar_events(
            events
        )
        if errors:
            details = "; ".join(f"{item.code}: {item.message}" for item in errors)
            raise ValueError(
                "Pre-alpha FAX acceptance calendar failed canonical validation: "
                + details
            )

        payload_for_fingerprint = {
            "schema_version": PRE_ALPHA_FAX_ACCEPTANCE_CALENDAR_SCHEMA,
            "season": season,
            "templates": [
                template.model_dump(mode="json") for template in templates
            ],
            "events": [event.model_dump(mode="json") for event in events],
        }
        build_fingerprint = canonical_hash(payload_for_fingerprint)
        metadata = SeasonCalendarMetadata(
            season=season,
            season_start_calendar_year=2000,
            season_start_year_week=37,
            total_season_weeks=PRE_ALPHA_FAX_ACCEPTANCE_SEASON_WEEKS,
            event_count=len(events),
            build_seed=None,
            build_fingerprint=build_fingerprint,
            source_template_count=len(templates),
            persistence_path=None,
            dry_run=True,
            overwrite_existing=False,
        )
        for event in events:
            event.calendar_fingerprint = build_fingerprint
        return SeasonCalendar(
            season=season,
            events=events,
            metadata=metadata,
            validation_warnings=warnings,
            validation_errors=[],
        )

    def build_document(
        self, season: str, *, source_version: int = 1
    ) -> CanonicalPackageDocument:
        calendar = self.build_calendar(season)
        package_id = CalendarPackageRunAdapter.package_id_for_season(season)
        metadata_payload = {
            "season": season,
            "metadata": calendar.metadata.model_dump(mode="json"),
            "validation_warnings": [
                item.model_dump(mode="json")
                for item in calendar.validation_warnings
            ],
            "validation_errors": [],
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
        entities.extend(
            PackageEntity(
                source_entity_id=event.event_id,
                entity_kind=CALENDAR_EVENT_ENTITY_KIND,
                entity_schema_version=1,
                scope=CALENDAR_SCOPE,
                payload=event.model_dump(mode="json"),
            )
            for event in sorted(calendar.events, key=lambda item: item.event_id)
        )
        return CanonicalPackageDocument(
            package_type=PackageType.CALENDAR,
            package_id=package_id,
            source_version=source_version,
            provenance={
                "adapter": PRE_ALPHA_FAX_ACCEPTANCE_CALENDAR_SCHEMA,
                "source_season": season,
                "source_calendar_fingerprint": canonical_hash(
                    calendar.model_dump(mode="json")
                ),
                "non_canonical_release_fixture": True,
            },
            explicit_scope=(CALENDAR_SCOPE,),
            entities=tuple(entities),
        )
