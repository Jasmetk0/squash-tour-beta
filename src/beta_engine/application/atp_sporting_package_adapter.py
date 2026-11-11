"""Load reviewed, explicitly adapted sporting profiles as a separate Category."""
import json

from beta_engine.application.atp_reference_package_adapter import ATP_SOURCE, CATEGORY_ID, CATEGORY_KIND
from beta_engine.application.atp_historical_calendar_source import CALENDAR_ID
from beta_engine.domain.run_packages import CanonicalPackageDocument, PackageEntity, PackageType, SourceReference
from beta_engine.domain.tournaments.atp_sporting_profile import ATPSportingProfile
from beta_engine.domain.tournaments.atp_knockout_profile import ATPKnockoutProfile

SPORTING_PACKAGE_ID = "atp_squash_sporting_profiles"
SPORTING_KIND = "atp.squash.sporting.profile.v1"
KNOCKOUT_KIND = "atp.squash.knockout.profile.v1"
SPORTING_SCOPE = "atp.squash.sporting.profiles"


def parse_sporting_profile(payload):
    models = {"atp_squash_group_profile.v1": ATPSportingProfile,
              "atp_squash_knockout_profile.v1": ATPKnockoutProfile}
    if payload.get("schema_version") not in models:
        raise ValueError("Unsupported ATP sporting profile schema")
    return models[payload['schema_version']].model_validate_json(json.dumps(payload))


def build_atp_sporting_package(source_root=ATP_SOURCE):
    raw = json.loads((source_root / "squash_sporting_profiles_v1.json").read_text(encoding="utf-8"))
    if (set(raw) != {"schema_version", "source_version", "profiles"}
            or raw["schema_version"] != 1 or not raw["profiles"]
            or type(raw["source_version"]) is not int or raw["source_version"] < 1):
        raise ValueError("Unsupported ATP sporting profiles source")
    profiles = [parse_sporting_profile(p) for p in raw["profiles"]]
    return CanonicalPackageDocument(
        package_type=PackageType.CATEGORY, package_id=SPORTING_PACKAGE_ID, source_version=raw["source_version"],
        explicit_scope=(SPORTING_SCOPE,),
        provenance={"adapter": "atp_squash_sporting_profiles.v1", "no_automatic_edition_creation": True},
        entities=tuple(PackageEntity(
            source_entity_id=p.occurrence_id, entity_kind=KNOCKOUT_KIND if isinstance(p, ATPKnockoutProfile) else SPORTING_KIND,
            entity_schema_version=1, scope=SPORTING_SCOPE, payload=p.model_dump(mode="json"),
            references=(
                SourceReference(source_package_id=CATEGORY_ID, source_entity_id=p.category_id,
                                expected_entity_kind=CATEGORY_KIND, minimum_schema_version=1),
                SourceReference(source_package_id=CALENDAR_ID, source_entity_id=p.occurrence_id,
                                expected_entity_kind="tennis.calendar.occurrence.reference.v1", minimum_schema_version=1),
            ),
        ) for p in profiles),
    )
