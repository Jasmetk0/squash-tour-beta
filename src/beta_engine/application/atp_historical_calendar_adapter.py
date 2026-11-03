"""Fixed ATP historical reference Calendar + linked Category/Series Setup.

Non-playable tennis source data. Deliberately NEVER materialises native FAX
SeasonCalendarEvent, TournamentEdition, CalendarTourEdition or Ranking inputs.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from beta_engine.application.atp_reference_package_adapter import (
    ATP_SOURCE, ATPReferencePackageAdapter, CATEGORY_SCOPE, SERIES_SCOPE,
)
from beta_engine.domain.run_packages import CanonicalPackageDocument, PackageType
from scripts.build_atp_historical_calendar import CALENDAR_ID, CALENDAR_SCOPE, build, canonical


CALENDAR_SETUP_ID = "atp_tour_1990_2026_calendar_reference_setup"
CALENDAR_OCCURRENCE_KIND = "tennis.calendar.occurrence.reference.v1"
CALENDAR_COVERAGE_KIND = "tennis.calendar.coverage.reference.v1"


@dataclass(frozen=True, slots=True)
class ATPHistoricalCalendarAdapter:
    """Read fixed reviewed sources, recompute provenance, freeze them atomically."""

    source_root: Path = ATP_SOURCE

    def build_calendar(self) -> CanonicalPackageDocument:
        def load(name: str) -> dict:
            return json.loads(
                (self.source_root / name).read_text(encoding="utf-8")
            )

        source = (
            load("category.json"),
            load("series.json"),
            load("seasons_1990_2026.json"),
            load("calendar_dates_v1.json"),
        )
        stored = (self.source_root / "calendar.json").read_text(encoding="utf-8")
        expected = canonical(build(*source))
        if stored != expected:
            raise ValueError("ATP historical Calendar reference is stale or tampered")
        document = CanonicalPackageDocument.model_validate(json.loads(stored))
        if (
            document.package_type != PackageType.CALENDAR
            or document.package_id != CALENDAR_ID
            or document.source_version != 1
            or document.explicit_scope != (CALENDAR_SCOPE,)
            or document.children
            or len(document.entities) != 150
        ):
            raise ValueError("Invalid ATP Calendar reference Package shape")
        ids = {entity.source_entity_id for entity in document.entities}
        if any(
            not entity.valid
            or entity.scope != CALENDAR_SCOPE
            or entity.entity_kind not in {
                CALENDAR_OCCURRENCE_KIND, CALENDAR_COVERAGE_KIND
            }
            or entity.payload.get("not_squash_rules") is not True
            for entity in document.entities
        ):
            raise ValueError("Invalid ATP Calendar source reference boundary")
        if len(ids) != 150 or document.provenance.get("dated_occurrences") != 113:
            raise ValueError("Invalid ATP Calendar verified date inventory")
        return document

    def build_document(self) -> CanonicalPackageDocument:
        """Include Category and Series dependencies as frozen Setup children."""
        parent = ATPReferencePackageAdapter(self.source_root).build_document()
        calendar = self.build_calendar()
        return CanonicalPackageDocument(
            package_type=PackageType.SETUP,
            package_id=CALENDAR_SETUP_ID,
            source_version=1,
            provenance={
                "adapter": "server_atp_tour_calendar_reference_setup.v1",
                "historical_span": {"from": 1990, "to": 2026},
                "dated_years": [2025, 2026],
                "dated_2026": "provisional",
                "run_consumption": "opaque_reference_only_no_sporting_calendar",
                "no_autosave": True,
            },
            explicit_scope=(CATEGORY_SCOPE, SERIES_SCOPE, CALENDAR_SCOPE),
            children=(*parent.children, calendar),
        )

    def catalog(self) -> dict[str, object]:
        doc = self.build_document()
        return {
            "package_id": doc.package_id,
            "package_type": doc.package_type.value,
            "source_version": doc.source_version,
            "source_fingerprint": doc.source_fingerprint,
            "reference_span": {"from": 1990, "to": 2026},
            "dated_years": [2025, 2026],
            "undated_years": list(range(1990, 2025)),
            "provisional_years": [2026],
            "usage": "source_reference_only_no_playable_calendar",
            "children": [
                {
                    "package_id": child.package_id,
                    "package_type": child.package_type.value,
                    "source_version": child.source_version,
                    "source_fingerprint": child.source_fingerprint,
                    "entity_count": len(child.entities),
                }
                for child in doc.children
            ],
        }
