"""Saved-verified, read-only next-week native Tour prospect intake preflight.

This never creates a player or weakens the real Tour's intake guard. Prospect
eligibility is based on the individual's 15th birthday in the Run's own W/O
calendar, not the legacy generation season, or an assumed 61 weeks.
"""
from __future__ import annotations

from beta_engine.domain.calendar.run_week_position import RunWeekPosition
from beta_engine.domain.players.prospect_sporting_profile import (
    validate_persisted_prospect_sporting_profile,
)
from beta_engine.domain.run_packages import canonical_hash


def preview_native_prospect_intake(
    *, current: RunWeekPosition, run_id: str, branch_id: str,
    saved_head_revision_id: str, checkpoint_fingerprint: str,
    world_package_id: str, source, initial_player_ids: set[str], current_player_ids: set[str],
) -> dict:
    """Plan the exact next transition from one immutable Saved source snapshot.

    `source` must have been authenticated against the Saved Revision and
    unchanged Run-owned SQLite rows by the caller. No future identity is sent
    to the Viewer; this is Admin-only.
    """
    clock = current.calendar
    target_ordinal = current.ordinal + 1
    if target_ordinal >= clock.season_count * clock.weeks_per_year:
        raise ValueError("Prospect intake preview is beyond the Run horizon")
    position = clock.position_at_ordinal(target_ordinal)
    target = RunWeekPosition(
        calendar=clock, season_index=position.season_index,
        week=position.season_week,
    )
    if current_player_ids - initial_player_ids:
        # Until versioned native lifecycle/sporting inclusion exists, no
        # branch may claim that a non-InitialWorld identity is supported.
        existing_extra = sorted(current_player_ids - initial_player_ids)
    else:
        existing_extra = []

    problems: list[dict[str, str]] = []
    due: list[dict] = []
    rows = source.records if source is not None else ()
    ids = [row.get("prospect_id") for row in rows]
    if any(type(pid) is not str or not pid for pid in ids) or ids != sorted(set(ids)):
        raise ValueError("Saved Run prospect identities are not canonical")

    for row in rows:
        pid = row["prospect_id"]
        birth_year, birth_week = row.get("birth_year"), row.get("birth_year_week")
        if (type(birth_year) is not int or type(birth_week) is not int
            or not 1 <= birth_week <= clock.weeks_per_year):
            problems.append({"prospect_id": pid, "code": "invalid_run_birth_week"})
            continue
        fifteenth_year = birth_year + 15
        birth_position = clock.calendar_to_season(fifteenth_year, birth_week)
        if birth_position is None:
            # The shared Run source may contain birthdays outside this Run's
            # horizon. They are not secretly admitted to its active timeline.
            continue
        if (
            row.get("calendar_year") != fifteenth_year
            or row.get("year_week") != birth_week
            or row.get("season_start_year") != clock.start_year + birth_position.season_index
            or row.get("season_week") != birth_position.season_week
            or row.get("age") != 15
        ):
            problems.append({"prospect_id": pid, "code": "source_calendar_disagreement"})
            continue
        if birth_position != position:
            continue
        if row.get("world_id") != world_package_id:
            problems.append({"prospect_id": pid, "code": "foreign_world_package"})
            continue
        if row.get("status") != "prospect":
            problems.append({"prospect_id": pid, "code": "unsupported_lifecycle_status"})
            continue
        if pid in initial_player_ids or pid in current_player_ids:
            problems.append({"prospect_id": pid, "code": "player_identity_collision"})
            continue
        if not isinstance(row.get("country_code"), str) or not (
            len(row["country_code"]) == 3 and row["country_code"].isascii()
            and row["country_code"].isalpha() and row["country_code"].isupper()
        ):
            problems.append({"prospect_id": pid, "code": "country_identity_invalid"})
            continue
        try:
            canonical = validate_persisted_prospect_sporting_profile(
                profile=row.get("profile", {}),
                development=row.get("development", {}),
                potential=row.get("potential", {}),
            )
            if canonical.player_id != pid:
                raise ValueError("foreign profile player id")
        except (ValueError, TypeError, AttributeError, KeyError):
            problems.append({"prospect_id": pid, "code": "prospect_sporting_profile_unready"})
            continue
        due.append({
            "player_id": pid,
            "display_name": row.get("display_name") or pid,
            "country_code": row["country_code"],
            "birth_year": birth_year,
            "birth_year_week": birth_week,
            "profile_fingerprint": canonical.fingerprint,
        })
    if existing_extra:
        problems.extend(
            {"prospect_id": pid, "code": "unknown_existing_sporting_identity"}
            for pid in existing_extra
        )
    due.sort(key=lambda row: row["player_id"])
    problems.sort(key=lambda row: (row["prospect_id"], row["code"]))
    result = {
        "schema_version": "native_tour_prospect_intake_preflight.v1",
        "run_id": run_id,
        "branch_id": branch_id,
        "saved_head_revision_id": saved_head_revision_id,
        "source_fingerprint": source.fingerprint if source is not None else None,
        "checkpoint_fingerprint": checkpoint_fingerprint,
        "current_week": current.model_dump(mode="json"),
        "target_week": target.model_dump(mode="json"),
        "due": due,
        "due_count": len(due),
        "problems": problems,
        "blocked": bool(problems or rows),
        "native_activation_supported": False,
        "manual_save_required_for_future_activation": True,
    }
    result["preflight_fingerprint"] = canonical_hash(result)
    return result


def inspect_native_prospect_intake(
    repository, *, run_id: str, branch_id: str,
) -> dict:
    """Authenticate Run/Branch HEAD, live sporting owner, and shared source.

    This makes no SQLite or Working Draft mutations. It must use the same
    transaction for the saved-head proof and live Run-scoped source check.
    """
    from sqlalchemy import text

    from beta_engine.application.calendar_tour_service import CalendarTourService
    from beta_engine.infrastructure.db.run_prospect_source_state import (
        validate_live_run_prospect_source_against_saved,
    )

    with repository._session_factory() as session:
        session.execute(text("BEGIN"))
        context, state, _signed = CalendarTourService(repository)._context(
            session, run_id, branch_id,
        )
        clock, revision, world, _health, checkpoint, _saved, _evidence = context
        if checkpoint is None or world is None:
            raise ValueError("Native prospect intake requires a sporting checkpoint")
        if (checkpoint.week.calendar.weeks_per_year,
            checkpoint.week.calendar.season_start_year_week,
            checkpoint.week.calendar.start_year) != (
            clock.weeks_per_year, clock.season_start_year_week, clock.start_year
        ):
            raise ValueError("Sporting checkpoint has a foreign Run calendar")
        snapshot = validate_live_run_prospect_source_against_saved(
            session, revision.saved_revision.payload, run_id=run_id,
        )
        review = preview_native_prospect_intake(
            current=checkpoint.week, run_id=run_id, branch_id=branch_id,
            saved_head_revision_id=revision.saved_head_revision_id,
            checkpoint_fingerprint=checkpoint.fingerprint,
            world_package_id=world.world_package_id,
            source=snapshot,
            initial_player_ids={p.player_id for p in world.players},
            current_player_ids={p.player_id for p in checkpoint.players},
        )
        # The real Tour still blocks native source activation. Stage a complete
        # versioned birth+57-attribute lifecycle successor only when the source
        # is Saved/verified, the Tour owns this week and the due cohort is clean.
        # No new player, lifecycle row, sporting or Health state is persisted.
        if snapshot is not None and state is not None and review["due"] and not review["problems"]:
            from beta_engine.domain.players.calendar_prospect_birth import (
                NATIVE_SOURCE_TYPE, advance_calendar_lifecycle_with_prospects,
                build_calendar_prospect_birth_event, project_native_birth_sporting_roster,
            )
            from beta_engine.infrastructure.db.player_lifecycle_state import get_lifecycle

            due_ids = {item["player_id"] for item in review["due"]}
            due_rows = [row for row in snapshot.records if row["prospect_id"] in due_ids]
            if all(row.get("source_type") == NATIVE_SOURCE_TYPE for row in due_rows):
                if state.week != checkpoint.week:
                    raise ValueError("Tour week differs from native intake sporting owner")
                predecessor = get_lifecycle(
                    session, run_id=run_id, branch_id=branch_id, week=state.week,
                )
                if predecessor is None:
                    raise ValueError("Native intake lifecycle predecessor is missing")
                target = RunWeekPosition.model_validate(review["target_week"])
                event = build_calendar_prospect_birth_event(
                    predecessor=predecessor, target=target, source=snapshot,
                    world_package_id=world.world_package_id,
                )
                proposed = advance_calendar_lifecycle_with_prospects(
                    predecessor, event,
                    tuple(s for a in state.editions for s in a.submissions),
                )
                if len(event.births) != len(review["due"]):
                    raise ValueError("Native birth evidence differs from the verified due cohort")
                sporting_roster = project_native_birth_sporting_roster(
                    predecessor=predecessor, checkpoint=checkpoint, event=event,
                )
                if len(sporting_roster) != len(proposed.players):
                    raise ValueError("Native birth sporting proposal differs from lifecycle")
                review["lifecycle_admission_projection"] = {
                    "schema_version": "native_tour_lifecycle_admission_projection.v1",
                    "birth_event_fingerprint": event.fingerprint,
                    "predecessor_lifecycle_fingerprint": predecessor.fingerprint,
                    "proposed_lifecycle_fingerprint": proposed.fingerprint,
                    "proposed_lifecycle_schema": proposed.schema_version,
                    "birth_count": len(event.births),
                    "projected_population_count": len(proposed.players),
                    "proposed_sporting_fingerprint": canonical_hash([
                        person.model_dump(mode="json") for person in sporting_roster
                    ]),
                    "proposed_sporting_population_count": len(sporting_roster),
                    "sporting_health_saved_activation_supported": False,
                }
                review.pop("preflight_fingerprint")
                review["preflight_fingerprint"] = canonical_hash(review)
        return review
