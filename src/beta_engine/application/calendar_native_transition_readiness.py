"""Read-only runtime capability, distinct from older component-only proposals."""

from sqlalchemy import text

from beta_engine.domain.calendar.run_week_position import RunWeekPosition
from beta_engine.domain.players.calendar_prospect_birth import (
    build_calendar_prospect_birth_event,
)
from beta_engine.domain.run_packages import canonical_hash
from beta_engine.infrastructure.db.player_lifecycle_state import get_lifecycle
from beta_engine.infrastructure.db.run_prospect_source_state import (
    validate_live_run_prospect_source_against_saved,
)


def inspect_native_transition_readiness(repository, *, run_id, branch_id):
    from beta_engine.application.calendar_tour_service import CalendarTourService

    service = CalendarTourService(repository)
    with repository._session_factory() as session:
        session.execute(text("BEGIN"))
        ctx, state, signed = service._context(session, run_id, branch_id)
        clock, revision, world, health, checkpoint, saved, _ = ctx
        if checkpoint is None:
            raise ValueError("Transition readiness requires a sporting checkpoint")
        season = checkpoint.week.week == clock.weeks_per_year
        action = "season-transition" if season else "transition"
        blockers = (
            service._transition_blockers(state, ctx, session, season=season)
            if state
            else ["tour_authority_missing"]
        )
        source = validate_live_run_prospect_source_against_saved(
            session, revision.saved_revision.payload, run_id=run_id
        )
        unsaved = checkpoint != saved or state != signed
        if unsaved:
            blockers.append("manual_save_required")
        target = None
        due = []
        problems = []
        if checkpoint.week.ordinal + 1 < clock.season_count * clock.weeks_per_year:
            position = clock.position_at_ordinal(checkpoint.week.ordinal + 1)
            target = RunWeekPosition(
                calendar=clock,
                season_index=position.season_index,
                week=position.season_week,
            )
            if source is not None and state is not None:
                life = get_lifecycle(
                    session, run_id=run_id, branch_id=branch_id, week=state.week
                )
                try:
                    event = build_calendar_prospect_birth_event(
                        predecessor=life,
                        target=target,
                        source=source.for_week(target.ordinal),
                        world_package_id=world.world_package_id,
                    )
                    names = {
                        r["prospect_id"]: r.get("display_name") or r["prospect_id"]
                        for r in source.records
                    }
                    due = [
                        {
                            "player_id": b.player_id,
                            "display_name": names[b.player_id],
                            "country_code": b.country_code,
                        }
                        for b in event.births
                    ]
                except (ValueError, TypeError) as exc:
                    problems.append(str(exc))
                    blockers.append(
                        "intake_source_requires_native_calendar_materialization"
                    )
        else:
            blockers.append("run_horizon_exhausted")
        native = checkpoint.schema_version in {"calendar_sporting_checkpoint.v11", "calendar_sporting_checkpoint.v12"}
        body = {
            "schema_version": "native_tour_transition_readiness.v2",
            "run_id": run_id,
            "branch_id": branch_id,
            "saved_head_revision_id": revision.saved_head_revision_id,
            "checkpoint_fingerprint": checkpoint.fingerprint,
            "tour_fingerprint": state.fingerprint if state else None,
            "source_fingerprint": source.fingerprint if source else None,
            "health_fingerprint": health.fingerprint if health else None,
            "run_calendar": clock.to_metadata(),
            "completed_week": checkpoint.week.model_dump(mode="json"),
            "target_week": target.model_dump(mode="json") if target else None,
            "action": action,
            "can_preview_transition": not blockers,
            "blockers": sorted(set(blockers)),
            "source_problems": problems,
            "due": due,
            "due_count": len(due),
            "admitted_population_count": len(checkpoint.players) - len(world.players),
            "current_scope": "native_competition"
            if native
            else "configured_tour",
            "target_scope": "native_competition"
            if native or due
            else "configured_tour",
            "post_birth_competition_supported": True,
            "source_epoch_changes_supported": False,
            "command_preview_required": True,
            "explicit_confirmation_required": True,
            "manual_save_required": True,
            "simulation_started": False,
        }
        body["readiness_fingerprint"] = canonical_hash(body)
        return body
