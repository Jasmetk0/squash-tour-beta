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
    development_seed: int | None = None,
    expected_saved_head: str | None = None,
    expected_checkpoint_fingerprint: str | None = None,
    expected_tour_fingerprint: str | None = None,
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
        if development_seed is not None:
            if type(development_seed) is not int:
                raise ValueError("Native sporting review requires an explicit integer seed")
            if state is None or state != _signed or checkpoint != _saved:
                raise ValueError("Native sporting review requires the exact Saved Tour and checkpoint")
            if (
                revision.saved_head_revision_id != expected_saved_head
                or checkpoint.fingerprint != expected_checkpoint_fingerprint
                or state.fingerprint != expected_tour_fingerprint
            ):
                raise ValueError("Native sporting review source HEAD or Tour changed since the request")
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
            from beta_engine.domain.players.calendar_prospect_birth import NATIVE_SOURCE_TYPE
            from beta_engine.domain.players.calendar_prospect_admission_bundle import (
                build_native_prospect_admission_bundle,
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
                next_position = checkpoint.week.calendar.position_at_ordinal(
                    checkpoint.week.ordinal + 1,
                )
                target = RunWeekPosition(
                    calendar=checkpoint.week.calendar,
                    season_index=next_position.season_index,
                    week=next_position.season_week,
                )
                bundle = build_native_prospect_admission_bundle(
                    predecessor=predecessor, checkpoint=checkpoint,
                    health=_health, source=snapshot, target=target,
                    world_package_id=world.world_package_id,
                    saved_head_revision_id=revision.saved_head_revision_id,
                    submissions=tuple(s for a in state.editions for s in a.submissions),
                )
                if len(bundle.event.births) != len(review["due"]):
                    raise ValueError("Native birth evidence differs from the verified due cohort")
                review["lifecycle_admission_projection"] = {
                    "schema_version": "native_tour_lifecycle_admission_projection.v1",
                    "birth_event_fingerprint": bundle.event.fingerprint,
                    "predecessor_lifecycle_fingerprint": predecessor.fingerprint,
                    "proposed_lifecycle_fingerprint": bundle.lifecycle.fingerprint,
                    "proposed_lifecycle_schema": bundle.lifecycle.schema_version,
                    "birth_count": len(bundle.event.births),
                    "projected_population_count": len(bundle.lifecycle.players),
                    "proposed_sporting_fingerprint": canonical_hash([
                        person.model_dump(mode="json") for person in bundle.sporting
                    ]),
                    "proposed_sporting_population_count": len(bundle.sporting),
                    "source_health_fingerprint": bundle.health.source_health_fingerprint,
                    "proposed_health_fingerprint": bundle.health.fingerprint,
                    "proposed_health_population_count": len(bundle.health.proposed_profiles),
                    "admission_bundle_fingerprint": bundle.fingerprint,
                    "ranking_and_entry_adoption_supported": False,
                    "sporting_health_saved_activation_supported": False,
                }
                if development_seed is not None:
                    from beta_engine.domain.players.calendar_native_sporting_intake import (
                        combine_signed_admission_with_sporting_week,
                    )
                    from beta_engine.domain.players.calendar_sporting_week import (
                        played_counts,
                    )
                    from beta_engine.domain.tournaments.calendar_tour import (
                        effective_policy,
                    )

                    # These are the actual, fully Signed completed-week matches.
                    # Never allow caller-provided fabricated play counts or policy.
                    counts = played_counts(
                        checkpoint, getattr(_evidence, "knockout", _evidence),
                    )
                    policy = effective_policy(state, checkpoint.week).development
                    proposed = combine_signed_admission_with_sporting_week(
                        admission=bundle, checkpoint=checkpoint,
                        predecessor=predecessor, seed=development_seed,
                        policy=policy, played_counts=counts,
                    )
                    sport = proposed.sporting_week
                    from beta_engine.domain.players.calendar_native_health_transition import (
                        prepare_native_health_history,
                    )
                    from beta_engine.infrastructure.db.player_health_state import load_saved_health
                    from beta_engine.infrastructure.db.player_lifecycle_state import load_saved_lifecycle

                    payload = revision.saved_revision.payload
                    saved_health = load_saved_health(payload, run_id=run_id, branch_id=branch_id)
                    signed_life = load_saved_lifecycle(payload, run_id=run_id, branch_id=branch_id)
                    if not signed_life or signed_life[-1] != predecessor:
                        raise ValueError("Native Health review requires exact current Signed lifecycle")
                    prepared_health = prepare_native_health_history(
                        saved_health=saved_health or (), signed_lifecycle=signed_life,
                        next_lifecycle=bundle.lifecycle,
                    )
                    target_health = prepared_health[-1]
                    if canonical_hash([p.model_dump(mode="json") for p in target_health.players]) != canonical_hash(
                        [p.model_dump(mode="json") for p in bundle.health.proposed_profiles]
                    ):
                        raise ValueError("Durable Health differs from the Signed admission population")
                    health_history_fingerprint = canonical_hash([
                        h.model_dump(mode="json") for h in prepared_health
                    ])
                    prepared_transition_fingerprint = canonical_hash({
                        "schema_version": "native_tour_prepared_birth_transition.v1",
                        "source_saved_head": revision.saved_head_revision_id,
                        "admission_week_fingerprint": proposed.fingerprint,
                        "health_history_fingerprint": health_history_fingerprint,
                        "target_health_fingerprint": target_health.fingerprint,
                    })
                    review["sporting_week_projection"] = {
                        "schema_version": "native_tour_sporting_week_preflight.v1",
                        "completed_week": sport.completed_week.model_dump(mode="json"),
                        "target_week": sport.target_week.model_dump(mode="json"),
                        "seed": sport.seed,
                        "development_policy": sport.policy.model_dump(mode="json"),
                        "played_counts_fingerprint": canonical_hash(sport.played_counts),
                        "played_player_count": sum(n > 0 for _, n in sport.played_counts),
                        "old_population_count": len(sport.completed_players),
                        "new_population_count": len(sport.target_players),
                        "developed_players_fingerprint": sport.developed_players_fingerprint,
                        "recovered_players_fingerprint": sport.recovered_players_fingerprint,
                        "target_players_fingerprint": sport.target_players_fingerprint,
                        "sporting_birth_advance_fingerprint": sport.fingerprint,
                        "signed_admission_week_fingerprint": proposed.fingerprint,
                        "source_saved_head": revision.saved_head_revision_id,
                        "durable_health": {
                            "schema_version": "native_tour_health_history_preflight.v1",
                            "target_health_schema": target_health.schema_version,
                            "source_health_head_fingerprint": saved_health[-1].fingerprint,
                            "source_health_week": saved_health[-1].week.model_dump(mode="json"),
                            "saved_state_count": len(saved_health),
                            "prepared_state_count": len(prepared_health),
                            "backfilled_week_count": len(prepared_health) - len(saved_health) - 1,
                            "target_health_fingerprint": target_health.fingerprint,
                            "health_history_fingerprint": health_history_fingerprint,
                            "prepared_transition_fingerprint": prepared_transition_fingerprint,
                        },
                        "signed_writer_supported": False,
                    }
                review.pop("preflight_fingerprint")
                review["preflight_fingerprint"] = canonical_hash(review)
        if development_seed is not None and "sporting_week_projection" not in review:
            raise ValueError(
                "Native sporting review requires one complete due, Signed birth cohort"
            )
        return review
