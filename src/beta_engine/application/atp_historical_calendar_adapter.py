"""Historical ATP references plus separate versioned squash sporting profiles.

Applying the Setup copies data only. Native Editions require a separate explicit
Tour preview/confirmation after Save. Original Calendar references stay at v1.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from beta_engine.application.atp_reference_package_adapter import (
    ATP_SOURCE, ATPReferencePackageAdapter, CATEGORY_SCOPE, SERIES_SCOPE,
)
from beta_engine.domain.run_packages import CanonicalPackageDocument, PackageType
from beta_engine.application.atp_historical_calendar_source import CALENDAR_ID, CALENDAR_SCOPE, build, canonical
from beta_engine.application.atp_sporting_package_adapter import build_atp_sporting_package, SPORTING_SCOPE


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
            or len(document.entities) < 37
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
        dated_count = sum(
            e.entity_kind == CALENDAR_OCCURRENCE_KIND for e in document.entities
        )
        coverage_count = sum(
            e.entity_kind == CALENDAR_COVERAGE_KIND for e in document.entities
        )
        if (
            len(ids) != len(document.entities)
            or coverage_count != 37
            or dated_count + coverage_count != len(document.entities)
            or document.provenance.get("dated_occurrences") != dated_count
        ):
            raise ValueError("Invalid ATP Calendar verified date inventory")
        return document

    def build_document(self) -> CanonicalPackageDocument:
        """Include Category and Series dependencies as frozen Setup children."""
        parent = ATPReferencePackageAdapter(self.source_root).build_document()
        calendar = self.build_calendar()
        return CanonicalPackageDocument(
            package_type=PackageType.SETUP,
            package_id=CALENDAR_SETUP_ID,
            source_version=2,
            provenance={
                "adapter": "server_atp_tour_calendar_reference_setup.v1",
                "historical_span": {"from": 1990, "to": 2026},
                "dated_years": list(calendar.provenance["date_coverage_years"]),
                "dated_2026": "provisional",
                "run_consumption": "reference_calendar_and_explicit_squash_profiles_no_auto_editions",
                "no_autosave": True,
            },
            explicit_scope=(CATEGORY_SCOPE, SERIES_SCOPE, CALENDAR_SCOPE, SPORTING_SCOPE),
            children=(*parent.children, calendar, build_atp_sporting_package(self.source_root)),
        )

    def catalog(self) -> dict[str, object]:
        doc = self.build_document()
        return {
            "package_id": doc.package_id,
            "package_type": doc.package_type.value,
            "source_version": doc.source_version,
            "source_fingerprint": doc.source_fingerprint,
            "reference_span": {"from": 1990, "to": 2026},
            "dated_years": list(doc.children[2].provenance["date_coverage_years"]),
            "undated_years": [
                y for y in range(1990, 2027)
                if y not in doc.children[2].provenance["date_coverage_years"]
            ],
            "provisional_years": [2026],
            "usage": "saved_reference_calendar_with_explicit_squash_sporting_profiles",
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
