"""Server-owned ATP Tour reference Category/Series Setup for generic Run Packages.

The adapter stores *opaque historical source references* only. It does not
produce playable FAX Calendar editions, scoring rules or ranking-point awards.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from beta_engine.domain.run_packages import (
    CanonicalPackageDocument,
    PackageType,
)

ROOT = Path(__file__).resolve().parents[3]
ATP_SOURCE = ROOT / "config" / "reference_packages" / "atp_tour_1990_2026"
CATEGORY_ID = "atp_tour_1990_2026_category"
SERIES_ID = "atp_tour_1990_2026_series"
SETUP_ID = "atp_tour_1990_2026_reference_setup"
CATEGORY_KIND = "tennis.category.reference.v1"
SERIES_KIND = "tennis.series.reference.v1"
CATEGORY_SCOPE = "tennis.atp_tour.category.reference.1990_2026"
SERIES_SCOPE = "tennis.atp_tour.series.reference.1990_2026"


@dataclass(frozen=True, slots=True)
class ATPReferencePackageAdapter:
    """Read two fixed, repository-controlled sources; reject malformed bundles."""

    source_root: Path = ATP_SOURCE

    def _load(self, name: str, expected_type: PackageType, expected_id: str,
              expected_kind: str, expected_scope: str) -> CanonicalPackageDocument:
        # No user-controlled path or file name reaches this source loader.
        path = self.source_root / (name + ".json")
        raw = json.loads(path.read_text(encoding="utf-8"))
        document = CanonicalPackageDocument.model_validate(raw)
        if (document.package_type != expected_type
                or document.package_id != expected_id
                or document.source_version != 1
                or document.explicit_scope != (expected_scope,)
                or document.children
                or not document.entities):
            raise ValueError("Invalid ATP source Package identity or scope: " + name)
        if any(
            not entity.valid
            or entity.entity_kind != expected_kind
            or entity.entity_schema_version != 1
            or entity.scope != expected_scope
            or entity.payload.get("not_squash_rules") is not True
            for entity in document.entities
        ):
            raise ValueError("Invalid ATP source entity boundary: " + name)
        span = document.provenance.get("reference_span")
        if span != {"from": 1990, "to": 2026}:
            raise ValueError("Invalid ATP historical reference span: " + name)
        return document

    def build_document(self) -> CanonicalPackageDocument:
        """Freeze Category + Series together for one transactional preview/apply."""
        category = self._load("category", PackageType.CATEGORY, CATEGORY_ID,
                              CATEGORY_KIND, CATEGORY_SCOPE)
        series = self._load("series", PackageType.SERIES, SERIES_ID,
                            SERIES_KIND, SERIES_SCOPE)
        category_ids = {entity.source_entity_id for entity in category.entities}
        for entity in series.entities:
            periods = entity.payload.get("history_periods")
            if not isinstance(periods, list) or not periods:
                raise ValueError("ATP Series without dated Category history")
            expected = {period["category_id"] for period in periods}
            actual = {ref.source_entity_id for ref in entity.references}
            if actual != expected or not expected <= category_ids or any(
                ref.source_package_id != CATEGORY_ID
                or ref.expected_entity_kind != CATEGORY_KIND
                or ref.minimum_schema_version != 1
                for ref in entity.references
            ):
                raise ValueError("ATP Series has incompatible Category references")
        return CanonicalPackageDocument(
            package_type=PackageType.SETUP,
            package_id=SETUP_ID,
            source_version=1,
            provenance={
                "adapter": "server_atp_tour_historical_reference_setup.v1",
                "scope": "ATP Tour only, 1990-2026",
                "historical_2026_status": "provisional",
                "run_consumption": "opaque_reference_only_no_calendar_or_sporting_effects",
                "data_source": "repository_config/reference_packages",
            },
            explicit_scope=(CATEGORY_SCOPE, SERIES_SCOPE),
            children=(category, series),
        )

    def catalog(self) -> dict[str, object]:
        document = self.build_document()
        return {
            "package_id": document.package_id,
            "package_type": document.package_type.value,
            "source_version": document.source_version,
            "source_fingerprint": document.source_fingerprint,
            "reference_span": {"from": 1990, "to": 2026},
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
                for child in document.children
            ],
        }
