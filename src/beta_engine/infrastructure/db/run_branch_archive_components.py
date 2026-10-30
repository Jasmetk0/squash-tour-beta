"""Fixed component adapters for cold installation, never a generic SQL loader."""

from __future__ import annotations

from beta_engine.domain.run_branch_archive import decode, encode, fail
from beta_engine.infrastructure.db.application_validation_slots import (
    capture_saved_application_validation_slots,
    load_saved_application_validation_slots,
    restore_saved_application_validation_slots,
)
from beta_engine.infrastructure.db.calendar_standalone_match_state import (
    capture_saved_calendar_match,
    load_saved_calendar_sources,
    restore_saved_calendar_match,
)
from beta_engine.infrastructure.db.definitive_wild_card_assignments import (
    capture_saved_definitive_wild_card_assignments,
    load_saved_definitive_wild_card_assignments,
    restore_saved_definitive_wild_card_assignments,
)
from beta_engine.infrastructure.db.initial_world_state import (
    capture_saved_initial_world,
    load_saved_initial_world,
    put_initial_world,
)
from beta_engine.infrastructure.db.native_fork_runtime_state import load_runtime
from beta_engine.infrastructure.db.player_health_state import (
    capture_saved_health,
    load_saved_health,
    put_health,
)
from beta_engine.infrastructure.db.player_lifecycle_state import (
    capture_saved_lifecycle,
    load_saved_lifecycle,
    put_lifecycle,
)
from beta_engine.infrastructure.db.player_sporting_state import (
    capture_saved_sporting,
    load_saved_sporting_bundle,
    put_completed_context,
    put_sporting,
)
from beta_engine.infrastructure.db.player_tour_entry_triggers import (
    capture_saved_tour_entry_triggers,
    load_saved_tour_entry_triggers,
    restore_saved_tour_entry_triggers,
)
from beta_engine.infrastructure.db.run_entry_decision_slots import (
    capture_saved_run_entry_decision_slots,
    load_saved_run_entry_decision_slots,
    restore_saved_run_entry_decision_slots,
)
from beta_engine.infrastructure.db.run_package_state import (
    capture_saved_run_package_state,
    load_saved_run_package_state,
    put_run_package_state,
)
from beta_engine.infrastructure.db.run_prospect_source_state import (
    load_saved_run_prospect_source,
    validate_live_run_prospect_source_against_saved,
)
from beta_engine.infrastructure.db.simulation_slot_state import (
    capture_saved_simulation_slots,
    load_saved_simulation_slot_component,
    restore_saved_simulation_slots,
)
from beta_engine.infrastructure.db.tournament_application_submissions import (
    capture_saved_application_submissions,
    load_saved_application_submissions,
    restore_saved_application_submissions,
)

ENTRY_ADAPTERS = (
    (
        "run_entry_decision_slots",
        capture_saved_run_entry_decision_slots,
        load_saved_run_entry_decision_slots,
        restore_saved_run_entry_decision_slots,
    ),
    (
        "application_validation_slots",
        capture_saved_application_validation_slots,
        load_saved_application_validation_slots,
        restore_saved_application_validation_slots,
    ),
    (
        "tournament_application_submissions",
        capture_saved_application_submissions,
        load_saved_application_submissions,
        restore_saved_application_submissions,
    ),
    (
        "definitive_wild_card_assignments",
        capture_saved_definitive_wild_card_assignments,
        load_saved_definitive_wild_card_assignments,
        restore_saved_definitive_wild_card_assignments,
    ),
    (
        "player_tour_entry_triggers",
        capture_saved_tour_entry_triggers,
        load_saved_tour_entry_triggers,
        restore_saved_tour_entry_triggers,
    ),
)

CAPTURES = (
    capture_saved_initial_world,
    capture_saved_run_package_state,
    capture_saved_lifecycle,
    capture_saved_health,
    capture_saved_sporting,
    capture_saved_simulation_slots,
    capture_saved_calendar_match,
)


def validate_components(payload, *, run_id, branch_id):
    content = payload["content"]
    if "native_fork_runtime" in content:
        # Full physical source/owner/replay verification belongs to the repository.
        load_runtime(payload)
        return
    world = load_saved_initial_world(payload, run_id=run_id, branch_id=branch_id)
    runtime_keys = {
        "calendar_standalone_match",
        "calendar_player_sporting_checkpoint",
        "calendar_tour_authority",
    }
    nonempty_players = any(
        content.get(key, {}).get("states")
        for key in ("player_lifecycle", "player_health_state", "player_sporting_state")
    )
    slots = content.get("simulation_slot_match_state", {})
    if world is None and (
        runtime_keys & content.keys()
        or nonempty_players
        or slots.get("slots")
        or slots.get("groups")
    ):
        fail(
            "missing_runtime_dependency",
            "Saved sporting/player authority requires its original InitialWorld; unresolved Package references are a separate nonblocking condition",
        )
    load_saved_run_package_state(payload, run_id=run_id, branch_id=branch_id)
    load_saved_lifecycle(payload, run_id=run_id, branch_id=branch_id)
    load_saved_health(payload, run_id=run_id, branch_id=branch_id)
    load_saved_sporting_bundle(payload, run_id=run_id, branch_id=branch_id)
    load_saved_simulation_slot_component(payload, run_id=run_id, branch_id=branch_id)
    load_saved_calendar_sources(payload, run_id=run_id, branch_id=branch_id)
    load_saved_run_prospect_source(payload, run_id=run_id)
    for _, _, load, _ in ENTRY_ADAPTERS:
        load(payload, run_id=run_id, branch_id=branch_id)


def capture_content(session, payload, *, run_id, branch_id):
    """Capture actual live components with their normal production validators."""
    from copy import deepcopy

    result = deepcopy(payload)
    result["content"] = {}
    for capture in CAPTURES:
        capture(session, result, run_id=run_id, branch_id=branch_id)
    for key, capture, _, _ in ENTRY_ADAPTERS:
        capture(session, result, run_id=run_id, branch_id=branch_id)
        # Initial empty Run creation predates these explicit empty projections.
        # Absence is legitimate only when the actual production projection has
        # no rows. Nonempty uncaptured data remains a mismatch/blocker.
        component = result["content"].get(key, {})
        values = [v for k, v in component.items() if k != "fingerprint"]
        if key not in payload["content"] and values and all(v == [] for v in values):
            result["content"].pop(key, None)
    # Prospect sources are immutable Run-shared references, not a new current
    # source selection. Verify the exact historical selection against live rows.
    validate_live_run_prospect_source_against_saved(session, payload, run_id=run_id)
    if "run_prospect_source" in payload["content"]:
        result["content"]["run_prospect_source"] = payload["content"][
            "run_prospect_source"
        ]
    return result["content"]


def install_components(session, payload, *, run_id, branch_id):
    """Install into empty component families; original identities remain intact."""
    if "native_fork_runtime" in payload["content"]:
        # The Saved aggregate IS the existing native runtime authority. Its clean
        # draft points to it; no live process/task or import-only state is created.
        return
    for load, put in (
        (load_saved_initial_world, put_initial_world),
        (load_saved_run_package_state, put_run_package_state),
    ):
        state = load(payload, run_id=run_id, branch_id=branch_id)
        if state is not None:
            put(session, state)
    for load, put in (
        (load_saved_lifecycle, put_lifecycle),
        (load_saved_health, put_health),
    ):
        for state in load(payload, run_id=run_id, branch_id=branch_id) or ():
            put(session, state)
    states, contexts = load_saved_sporting_bundle(
        payload, run_id=run_id, branch_id=branch_id
    ) or ((), ())
    for state in states or ():
        put_sporting(session, state)
    for context in contexts or ():
        put_completed_context(session, context)
    empty = {"content": {}}
    for key, _, _, restore in ENTRY_ADAPTERS:
        if key in payload["content"]:
            restore(
                session,
                current_payload=empty,
                target_payload=payload,
                run_id=run_id,
                branch_id=branch_id,
            )
    if "simulation_slot_match_state" in payload["content"]:
        restore_saved_simulation_slots(
            session,
            current_payload=empty,
            target_payload=payload,
            run_id=run_id,
            branch_id=branch_id,
        )
    if any(
        k in payload["content"]
        for k in (
            "calendar_standalone_match",
            "calendar_player_sporting_checkpoint",
            "calendar_tour_authority",
        )
    ):
        restore_saved_calendar_match(
            session,
            current_payload=empty,
            target_payload=payload,
            run_id=run_id,
            branch_id=branch_id,
        )


def prospect_records(revisions):
    """Union only historically Signed immutable catalogs, preserving each epoch."""
    records = {}
    for revision in revisions:
        source = load_saved_run_prospect_source(
            decode(revision.payload_json), run_id=revision.run_id
        )
        for record in source.records if source else ():
            key = record["prospect_id"]
            if key in records and encode(records[key]) != encode(record):
                fail(
                    "conflicting_source",
                    "Historical prospect sources disagree about an original identity",
                )
            records[key] = record
    return records


def install_prospects(session, *, run_id, records):
    """Inverse of the existing fixed Saved prospect projection, no live registry."""
    from beta_engine.infrastructure.db.models import RunProspectModel
    from beta_engine.infrastructure.db.run_prospect_source_state import _record_payload

    json_fields = {
        "profile": "profile_json",
        "development": "development_json",
        "potential": "potential_json",
        "traits": "trait_json",
    }
    scalar_fields = {
        "prospect_id",
        "world_id",
        "season_start_year",
        "season_label",
        "season_week",
        "calendar_year",
        "year_week",
        "birth_year",
        "birth_year_week",
        "age",
        "country_code",
        "country_name",
        "status",
        "source_type",
        "cohort_policy_version",
        "profile_version",
        "first_name",
        "last_name",
        "display_name",
        "short_name",
        "identity_seed",
        "profile_seed",
        "development_seed",
        "potential_seed",
        "trait_seed",
    }
    for record in records.values():
        if set(record) != scalar_fields | json_fields.keys():
            fail(
                "unsupported_prospect_record",
                "Prospect source contains missing or unknown fields",
            )
        row = RunProspectModel(
            run_id=run_id,
            **{k: record[k] for k in scalar_fields},
            **{
                target: encode(record[key]).decode()
                for key, target in json_fields.items()
            },
        )
        session.add(row)
        session.flush()
        if encode(_record_payload(row)) != encode(record):
            fail(
                "invalid_prospect_installation",
                "Installed prospect differs from its original Signed source",
            )
