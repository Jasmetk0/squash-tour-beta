"""One data-driven Saved ATP profile -> ordinary native Tour preview path."""
import json

from sqlalchemy import text

from beta_engine.application.atp_earth_run_calendar_preview import preview_atp_earth_weeks_on_run
from beta_engine.application.atp_next_gen_edition import ATPNextGenEditionPreviewRequest
from beta_engine.application.atp_saved_snapshot_week_preview import audit_saved_atp_tour_bindings, build_saved_atp_reference_week_mapping
from beta_engine.application.atp_saved_tour_source import read_saved_atp_source
from beta_engine.application.atp_sporting_package_adapter import SPORTING_PACKAGE_ID, SPORTING_KIND, SPORTING_SCOPE
from beta_engine.application.calendar_tour_service import CalendarTourCommand, CalendarTourService
from beta_engine.domain.calendar.run_week_position import RunWeekPosition
from beta_engine.domain.run_packages import PackageType
from beta_engine.domain.tournaments.atp_sporting_profile import ATPSportingProfile


def saved_profiles(state, *, occurrence_id=None):
    versions = [v for v in state.package_versions if v.package_id == SPORTING_PACKAGE_ID]
    if len(versions) != 1 or versions[0].package_type != PackageType.CATEGORY:
        raise ValueError("Save the ATP sporting profiles Package before importing an Edition")
    version = versions[0]
    result = {}
    for entity in state.entities:
        if (entity.source_package_id != SPORTING_PACKAGE_ID
                or (occurrence_id is not None and entity.source_entity_id != occurrence_id)):
            continue
        if (entity.entity_kind != SPORTING_KIND or entity.entity_schema_version != 1
                or entity.scope != SPORTING_SCOPE or entity.provenance != "package"
                or entity.source_package_version != version.source_version
                or entity.source_package_fingerprint != version.source_fingerprint
                or entity.content_fingerprint != entity.source_baseline_fingerprint):
            raise ValueError("Saved ATP sporting profile was edited or has incompatible provenance")
        profile = ATPSportingProfile.model_validate_json(json.dumps(entity.payload))
        if profile.occurrence_id != entity.source_entity_id or profile.occurrence_id in result:
            raise ValueError("Saved ATP sporting profile identity mismatch")
        result[profile.occurrence_id] = (profile, entity.content_fingerprint)
    return result


def project_profile(calendar, state, mapping, profile):
    projected = preview_atp_earth_weeks_on_run(
        calendar=calendar, mapping=mapping, years=(int(profile.source_start_date[:4]),),
        occurrence_id=profile.occurrence_id, report_outside_horizon=True,
    )
    # Exact whole-event projection only. Never squeeze a two/three-week source
    # into the current single-week group executor.
    source = (projected["events"] + projected["outside_horizon"])[0]
    binding = audit_saved_atp_tour_bindings(
        state, selected_occurrences=frozenset({profile.occurrence_id}),
    )["selected_occurrences"][profile.occurrence_id]
    if (binding["category_id"] != profile.category_id
            or source["source_start_date"] != profile.source_start_date
            or source["source_end_date"] != profile.source_end_date):
        raise ValueError("Saved ATP sporting configuration disagrees with its Calendar/Category source")
    return source


def inspect_atp_sourced_editions(repository, *, run_id, branch_id):
    with repository._session_factory() as session:
        session.execute(text("BEGIN"))
        calendar, revision, state = read_saved_atp_source(session, run_id=run_id, branch_id=branch_id)
        profiles = saved_profiles(state)
        mapping = build_saved_atp_reference_week_mapping(state)
        entries = []
        for profile, fingerprint in sorted(profiles.values(), key=lambda pair: pair[0].occurrence_id):
            source = project_profile(calendar, state, mapping, profile)
            entries.append({"profile": profile.model_dump(mode="json"),
                            "profile_fingerprint": fingerprint, "calendar_projection": source})
        return {"run_id": run_id, "branch_id": branch_id, "saved_head_revision_id": revision.revision_id,
                "entries": entries}


def preview_atp_sourced_edition(repository, *, run_id: str, branch_id: str, occurrence_id: str,
                               request: ATPNextGenEditionPreviewRequest):
    with repository._session_factory() as session:
        session.execute(text("BEGIN"))
        calendar, revision, state = read_saved_atp_source(session, run_id=run_id, branch_id=branch_id)
        if request.expected_saved_head != revision.revision_id:
            raise ValueError("Saved ATP source changed; refresh the Tour")
        profiles = saved_profiles(state, occurrence_id=occurrence_id)
        if occurrence_id not in profiles:
            raise ValueError("No Saved sporting configuration for this ATP occurrence")
        profile, fingerprint = profiles[occurrence_id]
        mapping = build_saved_atp_reference_week_mapping(state)
        source = project_profile(calendar, state, mapping, profile)
    if "run_weeks" not in source:
        raise ValueError("ATP occurrence is outside the Run horizon")
    if len(source["run_weeks"]) != 1 or source["source_finish_after_mapped_occupancy"]:
        raise ValueError("ATP group import requires one complete source week")
    target = source["run_weeks"][0]
    ordinal = source["run_ordinals"][0]
    if ordinal < profile.native_announcement_lead_weeks:
        raise ValueError("ATP announcement week is outside the Run horizon")
    announcement = calendar.position_at_ordinal(ordinal - profile.native_announcement_lead_weeks)
    edition = profile.build_edition(
        run_id=run_id, branch_id=branch_id, command_id=request.command_id,
        week=RunWeekPosition(calendar=calendar, season_index=target["season_index"], week=target["season_week"]),
        announcement_week=RunWeekPosition(calendar=calendar, season_index=announcement.season_index, week=announcement.season_week),
        start_slot=request.start_slot, seed=request.seed,
    )
    command = CalendarTourCommand(
        action="create-edition", command_id=request.command_id,
        expected_saved_head=request.expected_saved_head,
        expected_checkpoint_fingerprint=request.expected_checkpoint_fingerprint,
        expected_tour_fingerprint=request.expected_tour_fingerprint,
        seed=request.seed, operator_label=request.operator_label,
        audit_reason=f"{request.audit_reason} [ATP profile {occurrence_id} {fingerprint}]",
        data=edition.model_dump(mode="json"),
    )
    return CalendarTourService(repository).preview(run_id=run_id, branch_id=branch_id, command=command)
