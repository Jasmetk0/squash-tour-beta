"""Native fork continuation using existing deterministic production Tour kernels."""

from types import SimpleNamespace

from beta_engine.application.calendar_tour_service import CalendarTourService
from beta_engine.domain.calendar.run_week_position import RunWeekPosition
from beta_engine.domain.native_fork_runtime import (
    ForkCompetitionView,
    ForkHealthRoot,
    ForkLifecycleRoot,
    ForkTourState,
    NativeForkRuntime,
)
from beta_engine.domain.players.calendar_health import CalendarHealthOrigin
from beta_engine.domain.players.calendar_initial_health import (
    CalendarInitialHealthState,
)
from beta_engine.domain.players.calendar_lifecycle import advance_calendar_lifecycle
from beta_engine.domain.players.calendar_native_competition import (
    play_native_tournament,
)
from beta_engine.domain.players.calendar_native_health_transition import (
    advance_native_health_week,
)
from beta_engine.domain.players.calendar_native_sporting_intake import (
    project_native_sporting_birth_advance,
)
from beta_engine.domain.players.calendar_prospect_birth import (
    advance_calendar_lifecycle_with_prospects,
    build_calendar_prospect_birth_event,
)
from beta_engine.domain.players.calendar_sporting_week import played_counts
from beta_engine.domain.rankings.calendar_official import (
    CalendarOfficialRankingSnapshot,
    CalendarRankingPlayer,
    calculate_calendar_official_ranking,
)
from beta_engine.domain.run_packages import canonical_hash
from beta_engine.domain.tournaments.calendar_tour import (
    CalendarTourTransition,
    edition_results,
    effective_policy,
    ranking_week,
)
from beta_engine.infrastructure.db.calendar_standalone_match_state import (
    decode_prevalidated_calendar_sources,
)
from beta_engine.infrastructure.db.initial_world_state import load_saved_initial_world
from beta_engine.infrastructure.db.player_health_state import load_saved_health
from beta_engine.infrastructure.db.player_lifecycle_state import load_saved_lifecycle
from beta_engine.infrastructure.db.run_prospect_source_state import (
    RunProspectSourceSnapshot,
    load_saved_run_prospect_source,
)


def source_inputs(source, repository=None, session=None):
    from beta_engine.infrastructure.db.native_fork_runtime_state import _proofs

    memo = _proofs.get()
    key = ("native_sources", source.run_id, source.revision_id, source.content_hash)
    if memo is not None and key in memo:
        return SimpleNamespace(**vars(memo[key]))
    if source.payload_schema_version == "native_fork_saved_root.v2":
        if repository is None or session is None:
            raise ValueError("Native descendant sources require actual-row resolution")
        from beta_engine.infrastructure.db.models import BranchSavedRevisionModel
        from beta_engine.infrastructure.db.native_fork_runtime_state import load_runtime

        runtime = load_runtime(source.payload)
        original = repository._validated_saved_revision_in_session(
            session=session,
            model=session.get(
                BranchSavedRevisionModel,
                runtime.baseline.source_binding.source.revision_id,
            ),
        )
        inherited = source_inputs(original, repository, session)
        result = SimpleNamespace(**vars(inherited))
        result.history_tours = (
            *getattr(inherited, "history_tours", ()),
            inherited.tour,
        )
        result.checkpoint = ForkCompetitionView(runtime, inherited.checkpoint)
        result.tour, result.health, result.lifecycle = (
            runtime.tour,
            runtime.health,
            runtime.lifecycle,
        )
        result.prospects = load_saved_run_prospect_source(
            source.payload, run_id=source.run_id
        )
        result.inherited_command_ids = getattr(
            inherited, "inherited_command_ids", set()
        ) | {r.command_id for r in inherited.tour.receipts}
    else:
        from beta_engine.infrastructure.db.native_fork_source_projection import (
            decoded_original_source,
        )

        result = decoded_original_source(repository, source, _decode_sources)
    if memo is not None:
        memo[key] = result
    return SimpleNamespace(**vars(result))


def _decode_sources(source):
    opening, cp, tour = decode_prevalidated_calendar_sources(
        source.payload, run_id=source.run_id, branch_id=source.branch_id
    )
    return SimpleNamespace(
        lifecycle=next(
            reversed(
                load_saved_lifecycle(
                    source.payload, run_id=source.run_id, branch_id=source.branch_id
                )
            ),
            None,
        ),
        checkpoint=cp,
        tour=tour,
        opening=getattr(opening, "knockout", opening),
        world=load_saved_initial_world(
            source.payload, run_id=source.run_id, branch_id=source.branch_id
        ),
        health=next(
            reversed(
                load_saved_health(
                    source.payload, run_id=source.run_id, branch_id=source.branch_id
                )
            ),
            None,
        ),
        prospects=load_saved_run_prospect_source(source.payload, run_id=source.run_id),
    )


def initial_runtime(baseline, root_id, sources):
    # Current accepted Entry/draw adoption needs a separate source projection.
    # Never claim support by merely re-owning those immutable authorities.
    if any(a.submissions and not a.result_confirmed for a in sources.tour.editions):
        raise ValueError(
            "Finish the current submitted Edition before native branching, or choose an earlier Saved Revision"
        )
    life = ForkLifecycleRoot(
        run_id=baseline.run_id,
        branch_id=baseline.branch_id,
        week=baseline.week,
        players=baseline.lifecycle_players,
        policy=baseline.lifecycle_policy,
        source_initial_world_fingerprint=baseline.source_initial_world_fingerprint,
        source_baseline_fingerprint=baseline.fingerprint,
        source_lifecycle_fingerprint=baseline.source_lifecycle_fingerprint,
    )
    health = ForkHealthRoot(
        run_id=baseline.run_id,
        branch_id=baseline.branch_id,
        week=baseline.week,
        source_health_week=baseline.source_health_week,
        players=baseline.health_players,
        source_initial_world_fingerprint=baseline.source_initial_world_fingerprint,
        source_baseline_fingerprint=baseline.fingerprint,
        source_health_fingerprint=baseline.source_health_fingerprint,
        origin=CalendarHealthOrigin.from_baseline(sources.health)
        if isinstance(sources.health, CalendarInitialHealthState)
        else sources.health.origin,
        admin_edits=getattr(sources.health, "admin_edits", ()),
    )
    old = sources.tour.rankings[-1]
    if any(r.disciplinary_zeros for r in old.rows):
        raise ValueError("Native disciplinary fork source is unsupported")
    ranking = CalendarOfficialRankingSnapshot.model_validate_json(
        old.model_copy(
            update={
                "branch_id": baseline.branch_id,
                "previous_fingerprint": old.fingerprint,
                "input_fingerprint": canonical_hash(
                    {
                        "schema_version": "native_fork_current_ranking.v1",
                        "source": old.fingerprint,
                        "baseline": baseline.fingerprint,
                    }
                ),
            }
        ).model_dump_json()
    )
    tour = ForkTourState(
        run_id=baseline.run_id,
        branch_id=baseline.branch_id,
        week=baseline.week,
        checkpoint_fingerprint="0" * 64,
        lifecycle_fingerprint=life.fingerprint,
        slot_cursor=baseline.slot_cursor,
        policies=sources.tour.policies,
        editions=sources.tour.editions,
        rankings=(ranking,),
        transitions=sources.tour.transitions,
        source_tour_fingerprint=sources.tour.fingerprint,
        inherited_transition_count=len(sources.tour.transitions),
    )
    return cohere(
        NativeForkRuntime.model_construct(
            baseline=baseline,
            root_saved_revision_id=root_id,
            players=baseline.sporting_players,
            lifecycle=life,
            health=health,
            tour=tour,
        )
    )


def cohere(runtime, **changes):
    result = runtime.model_copy(update=changes)
    result = result.model_copy(
        update={
            "tour": result.tour.model_copy(
                update={
                    "week": result.week,
                    "checkpoint_fingerprint": result.checkpoint_fingerprint,
                    "lifecycle_fingerprint": result.lifecycle.fingerprint,
                }
            )
        }
    )
    return NativeForkRuntime.model_validate_json(result.model_dump_json())


def tour_fingerprint(runtime, version):
    return canonical_hash({"tour": runtime.tour.fingerprint, "draft_version": version})


class _Actor(CalendarTourService):
    def __init__(self, runtime, sources):
        super().__init__(None)
        self.runtime, self.sources, self.played = runtime, sources, None

    def _play_native(self, session, ctx, state, authority, command, **kwargs):
        event, successor = play_native_tournament(
            checkpoint=ctx[4],
            world=self.sources.world,
            lifecycle=self.runtime.lifecycle,
            health=self.runtime.health,
            source=self.sources.prospects.for_week(state.week.ordinal)
            if self.sources.prospects
            else SimpleNamespace(records=()),
            clock=state.week.calendar,
            authority=authority,
            command=command,
            knockout=self.sources.opening,
        )
        self.played = (event, successor)
        return {
            "fingerprint": event.fingerprint,
            "checkpoint_fingerprint": successor.fingerprint,
            "winner_player_id": event.matches[-1].result.winner_player_id,
            "prepared_awards": [
                a.model_dump(mode="json") for a in event.prepared_awards
            ],
            "tournament": event.model_dump(mode="json"),
            "participant_identities": {
                p.player_id: {"name": p.name, "country_code": p.nationality}
                for m in event.matches
                for p in m.canonical_projections
            },
        }


def transition_blockers(runtime, *, season=False, calendar=None):
    week = runtime.week
    clock = calendar or week.calendar
    out = []
    if season and week.week != clock.weeks_per_year:
        out.append("season_transition_requires_last_week")
    if not season and week.week == clock.weeks_per_year:
        out.append("season_transition_required")
    if week.ordinal + 1 >= clock.season_count * clock.weeks_per_year:
        out.append("run_horizon_exhausted")
    out += [
        "edition_not_terminal:" + a.edition.edition_id
        for a in runtime.tour.editions
        if a.edition.week.ordinal <= week.ordinal and not a.result_confirmed
    ]
    if any(
        any(r.lifecycle != "Recovered" for r in p.records) or p.permanent_consequences
        for p in runtime.health.players
    ):
        out.append("health_healing_or_permanent_effect_authority_unsupported")
    return out


def _advance(runtime, command, sources):
    blockers = transition_blockers(
        runtime,
        season=command.action == "season-transition",
        calendar=getattr(sources, "execution_calendar", None),
    )
    if blockers:
        raise ValueError("Transition blocked: " + ", ".join(blockers))
    clock = getattr(sources, "execution_calendar", runtime.week.calendar)
    p = clock.position_at_ordinal(runtime.week.ordinal + 1)
    target = RunWeekPosition(
        calendar=clock, season_index=p.season_index, week=p.season_week
    )
    source = sources.prospects or RunProspectSourceSnapshot(
        "run_prospect_source.v1", runtime.run_id, (), canonical_hash([])
    )
    birth = build_calendar_prospect_birth_event(
        predecessor=runtime.lifecycle,
        target=target,
        source=source.for_week(target.ordinal),
        world_package_id=sources.world.world_package_id,
    )
    submissions = tuple(
        SimpleNamespace(
            run_id=runtime.run_id,
            branch_id=runtime.branch_id,
            player_id=s.player_id,
            submission_week=s.submission_week,
            decision_position=s.decision_position,
            nr_tie_break_token=s.nr_tie_break_token,
            source=s,
        )
        for a in runtime.tour.editions
        for s in a.submissions
    )
    life = (
        advance_calendar_lifecycle_with_prospects(runtime.lifecycle, birth, submissions)
        if birth.births
        else advance_calendar_lifecycle(runtime.lifecycle, target, submissions)
    )
    health = advance_native_health_week(
        previous_health=runtime.health,
        previous_lifecycle=runtime.lifecycle,
        next_lifecycle=life,
    )
    cp = ForkCompetitionView(runtime, sources.checkpoint)
    advance = project_native_sporting_birth_advance(
        checkpoint=cp,
        predecessor=runtime.lifecycle,
        birth_event=birth,
        seed=command.seed,
        policy=effective_policy(runtime.tour, runtime.week).development,
        played_counts=played_counts(cp, sources.opening),
    )
    events = {t.tournament_id: t for t in cp.tournaments}
    results = tuple(
        r
        for a in runtime.tour.editions
        if a.result_confirmed and a.edition.week.ordinal < target.ordinal
        for r in edition_results(a, events[a.edition.edition_id])
    )
    players = tuple(
        CalendarRankingPlayer(
            player_id=p.player_id,
            tie_break_token=p.tie_break_token,
            tour_entry_week=ranking_week(p.tour_entry_week),
            retired=p.status == "retired",
        )
        for p in life.players
        if p.tour_entry_week is not None
    )
    ranking = calculate_calendar_official_ranking(
        run_id=runtime.run_id,
        branch_id=runtime.branch_id,
        run_calendar=clock,
        week=ranking_week(target),
        policy=effective_policy(runtime.tour, target).ranking,
        players=players,
        results=results,
        previous=runtime.tour.rankings[-1],
    )
    public = {
        "kind": "season_transition_completed"
        if command.action == "season-transition"
        else "week_transition_completed",
        "week": target.model_dump(mode="json"),
        "ranking_fingerprint": ranking.fingerprint,
        "source_command_id": command.command_id,
        "announced_edition_ids": [
            a.edition.edition_id
            for a in runtime.tour.editions
            if a.edition.announcement_week.ordinal == target.ordinal
        ],
    }
    transition = CalendarTourTransition(
        command_id=command.command_id,
        completed_week=runtime.week,
        target_week=target,
        sporting_advance_fingerprint=advance.fingerprint,
        ranking_fingerprint=ranking.fingerprint,
        health_fingerprint=health.fingerprint,
        ages=tuple((p.player_id, p.age) for p in life.players),
        retired_player_ids=tuple(
            p.player_id for p in life.players if p.status == "retired"
        ),
        public_event=public,
    )
    tour = runtime.tour.model_copy(
        update={
            "week": target,
            "slot_cursor": 0,
            "rankings": runtime.tour.rankings + (ranking,),
            "transitions": runtime.tour.transitions + (transition,),
        }
    )
    result = {
        "command_id": command.command_id,
        "action": command.action,
        "manual_save_required": True,
        "impact": {
            "completed_week": runtime.week.model_dump(mode="json"),
            "target_week": target.model_dump(mode="json"),
            "ranking": ranking.model_dump(mode="json"),
            "ranking_fingerprint": ranking.fingerprint,
            "lifecycle": life.model_dump(mode="json"),
            "health_fingerprint": health.fingerprint,
            "admitted_player_ids": [b.player_id for b in birth.births],
            "native_transition": True,
        },
    }
    return cohere(
        runtime,
        players=advance.target_players,
        lifecycle=life,
        health=health,
        tour=tour,
        advances=runtime.advances + (advance,),
    ), result


def prepare_command(runtime, command, sources, *, saved_head, draft_version, is_saved):
    if (
        command.expected_saved_head,
        command.expected_checkpoint_fingerprint,
        command.expected_tour_fingerprint,
    ) != (
        saved_head,
        runtime.checkpoint_fingerprint,
        tour_fingerprint(runtime, draft_version),
    ):
        raise ValueError(
            "Source HEAD or sporting/Tour input changed; Save and review again"
        )
    if command.action in {"initialize", "policy"}:
        raise ValueError(
            "Native fork Tour is initialized; native policy edits are unsupported"
        )
    if (
        command.action in {"play", "confirm-result", "transition", "season-transition"}
        and not is_saved
    ):
        raise ValueError(
            "Manual Save of the configured Tour authority is required first"
        )
    cp = ForkCompetitionView(runtime, sources.checkpoint)
    reserved = (
        {r.command_id for t in (sources.tour, runtime.tour) for r in t.receipts}
        | {m.command_id for m in cp.played_continuations}
        | {sources.opening.command_id}
    )
    reserved.update(
        event.command_id for event in (*cp.week_events, *cp.continuations, *cp.closures)
    )
    reserved.update(getattr(sources, "inherited_command_ids", ()))
    if command.command_id in reserved:
        raise ValueError("Command ID collides with existing sporting history")
    authority = (
        next(
            (
                a
                for a in runtime.tour.editions
                if a.edition.edition_id == command.edition_id
            ),
            None,
        )
        if command.edition_id
        else None
    )
    if command.edition_id and authority is None:
        raise ValueError("Edition does not belong to this Run/Branch")
    offsets = {
        "submit": 0,
        "approve": 1,
        "draw": 2,
        "play": 3,
        "confirm-result": authority.edition.main_entrant_count + 2 if authority else 0,
    }
    if authority and command.action in offsets:
        if (
            authority.edition.start_slot + offsets[command.action]
            < runtime.tour.slot_cursor
        ):
            raise ValueError("Operation precedes current global Simulation Slot")
        if any(
            a.edition.week.ordinal == runtime.week.ordinal
            and a.edition.start_slot < authority.edition.start_slot
            and not a.result_confirmed
            for a in runtime.tour.editions
        ):
            raise ValueError("Complete the nearest earlier mandatory Edition first")
    if command.action in {"transition", "season-transition"}:
        if command.data or command.edition_id:
            raise ValueError("Unexpected transition inputs")
        candidate, result = _advance(runtime, command, sources)
    else:
        actor = _Actor(runtime, sources)
        ctx = (
            getattr(sources, "execution_calendar", runtime.week.calendar),
            None,
            sources.world,
            runtime.health,
            cp,
            cp,
            sources.opening,
        )
        tour, result = actor._apply(
            None,
            ctx,
            runtime.tour,
            authority,
            command,
            persist=False,
            _native_inputs=(runtime.lifecycle, sources.prospects),
        )
        updates = {"tour": tour}
        if actor.played:
            event, played = actor.played
            updates.update(
                players=played.players, tournaments=runtime.tournaments + (event,)
            )
        candidate = cohere(runtime, **updates)
    preview = {
        "schema_version": "calendar_tour_command_preview.v1",
        "run_id": runtime.run_id,
        "branch_id": runtime.branch_id,
        "command": command.model_dump(mode="json"),
        "week": runtime.week.model_dump(mode="json"),
        "edition": authority.model_dump(mode="json") if authority else None,
        "impact": result.get("impact", result),
    }
    preview["preview_fingerprint"] = canonical_hash(preview)
    return preview, candidate, result
