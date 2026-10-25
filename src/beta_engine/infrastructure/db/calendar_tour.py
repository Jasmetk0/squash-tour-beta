"""Persistence, Saved publication and restore for the Run-calendar Tour adapter."""

import hashlib
import json

from beta_engine.domain.tournaments.calendar_tour import (
    CalendarEditionAuthority,
    calculate_tour_ranking,
    edition_results,
    effective_policy,
    parse_tour_json,
)
from beta_engine.infrastructure.db.models import CalendarTourAuthorityModel

COMPONENT_KEY = "calendar_tour_authority"


def require_exhibition_timeline(session, run_id, branch_id):
    if session.get(CalendarTourAuthorityModel, (run_id, branch_id)):
        raise ValueError(
            "Configured Tour owns this timeline; use its Edition and Week Transition commands"
        )


def load_tour(session, *, run_id, branch_id, _repository=None):
    row = session.get(CalendarTourAuthorityModel, (run_id, branch_id))
    if row is None:
        return None
    from beta_engine.infrastructure.db.native_fork_source_projection import decoded_live_calendar_component
    state, fingerprint = decoded_live_calendar_component(_repository, run_id=run_id, branch_id=branch_id,
        kind=COMPONENT_KEY, raw=row.payload_json, parse=parse_tour_json, _with_fingerprint=True)
    if (state.run_id, state.branch_id, fingerprint) != (
        run_id,
        branch_id,
        row.fingerprint,
    ):
        raise ValueError("Native Tour SQLite identity/hash mismatch")
    return state


def put_tour(session, state):
    state = parse_tour_json(state.model_dump_json())
    row = session.get(CalendarTourAuthorityModel, (state.run_id, state.branch_id))
    if row is None:
        row = CalendarTourAuthorityModel(run_id=state.run_id, branch_id=state.branch_id)
        session.add(row)
    row.payload_json = state.model_dump_json()
    row.fingerprint = state.fingerprint
    session.flush()


def verify_tour(state, checkpoint, world=None, *, _native_payload=None):
    if (
        checkpoint is not None
        and checkpoint.schema_version in {"calendar_sporting_checkpoint.v12", "calendar_sporting_checkpoint.v13"}
    ):
        if _native_payload is None:
            raise ValueError("Native competition requires its complete Signed payload")
        from beta_engine.infrastructure.db.calendar_native_competition import (
            verify_competition_payload,
        )

        component = _native_payload.get("content", {}).get(COMPONENT_KEY, {})
        if (
            state is None
            or state.checkpoint_fingerprint != checkpoint.fingerprint
            or state.fingerprint != component.get("fingerprint")
            or state.model_dump(mode="json") != component.get("state")
        ):
            raise ValueError("Native competition lacks its coupled Tour owner")
        verify_competition_payload(_native_payload, checkpoint)
        return
    if (
        checkpoint is not None
        and checkpoint.schema_version == "calendar_sporting_checkpoint.v11"
    ):
        if _native_payload is None:
            raise ValueError(
                "Native birth checkpoint requires coupled Tour transition receipt authority"
            )
        from beta_engine.infrastructure.db.calendar_native_tour import (
            verify_native_tour,
        )

        verify_native_tour(state, checkpoint, world, payload=_native_payload)
        return
    if state is None:
        if checkpoint and (
            any(e.schema_version.endswith(".v2") for e in checkpoint.weekly_advances)
            or any(
                e.schema_version == "calendar_followup_knockout.v5"
                for e in checkpoint.tournaments
            )
        ):
            raise ValueError("Official native sporting advance lacks Tour authority")
        return
    if checkpoint is None or (
        state.run_id,
        state.branch_id,
        state.week.ordinal,
        state.checkpoint_fingerprint,
    ) != (
        checkpoint.run_id,
        checkpoint.branch_id,
        checkpoint.week.ordinal,
        checkpoint.fingerprint,
    ):
        raise ValueError(
            "Tour authority differs from its actual population sporting owner"
        )
    events = {e.tournament_id: e for e in checkpoint.tournaments}
    sources = {a.edition.edition_id: a for a in state.editions}
    confirmations = {}
    for receipt in state.receipts:
        command = receipt.request.get("command", {})
        if not isinstance(command, dict):
            raise TypeError("Malformed Tour command receipt")
        if (
            (command.get("command_id"), command.get("action"))
            != (receipt.command_id, receipt.result.get("action"))
            or receipt.result.get("command_id") != receipt.command_id
            or receipt.request.get("explicit_confirmation") is not True
        ):
            raise ValueError("Tour command receipt identity/confirmation is corrupt")
        if command.get("action") == "play":
            event = events.get(command.get("edition_id"))
            expected = (
                {
                    "fingerprint": event.fingerprint,
                    "winner_player_id": event.matches[-1].result.winner_player_id,
                    "prepared_awards": [
                        a.model_dump(mode="json") for a in event.prepared_awards
                    ],
                    "match_ids": [m.match_id for m in event.matches],
                }
                if event
                else None
            )
            played = receipt.result.get("played")
            if not isinstance(played, dict):
                raise ValueError("Tour play receipt lacks played evidence")
            actual = played.copy()
            actual.pop("checkpoint_fingerprint", None)
            if actual != expected:
                raise ValueError(
                    "Tour play receipt differs from actual MatchEngine results"
                )
        action = command.get("action")
        authority = sources.get(command.get("edition_id"))
        if action == "confirm-result":
            confirmations.setdefault(command.get("edition_id"), []).append(receipt)
        if action == "approve" and (
            authority is None
            or authority.field is None
            or receipt.result.get("approved_field")
            != authority.field.model_dump(mode="json")
        ):
            raise ValueError("Tour approval receipt differs from canonical Entry field")
        if action == "draw" and (
            authority is None
            or authority.draw is None
            or receipt.result.get("draw") != authority.draw.model_dump(mode="json")
            or command.get("seed") != authority.draw_seed
            or receipt.command_id != authority.draw_command_id
        ):
            raise ValueError("Tour draw receipt differs from canonical injected draw")
    for authority in state.editions:
        if (
            authority.edition.week.calendar.weeks_per_year,
            authority.edition.week.calendar.start_year,
            authority.edition.week.calendar.season_start_year_week,
        ) != (
            state.week.calendar.weeks_per_year,
            state.week.calendar.start_year,
            state.week.calendar.season_start_year_week,
        ):
            raise ValueError("Edition has a foreign Run calendar")
        if any(
            (s.run_id, s.branch_id) != (state.run_id, state.branch_id)
            for s in authority.submissions
        ):
            raise ValueError("Edition has foreign Entry sources")
        if authority.tournament_fingerprint:
            event = events.get(authority.edition.edition_id)
            if event is None or event.source_saved_head != authority.played_saved_head:
                raise ValueError(
                    "Edition lacks authentic played event and Saved origin"
                )
            results = edition_results(authority, event)
            if results and getattr(results[0], "schema_version", None) in {"calendar_terminal_edition_result.v1", "calendar_terminal_edition_result.v2"}:
                receipts = confirmations.get(authority.edition.edition_id, [])
                if authority.result_confirmed != bool(receipts) or len(receipts) > 1 or (
                    receipts and receipts[0].result.get("results") != [r.model_dump(mode="json") for r in results]
                ):
                    raise ValueError("Terminal confirmation differs from actual Edition results")
    advances = {e.command_id: e for e in checkpoint.weekly_advances}
    if {
        e.command_id
        for e in checkpoint.weekly_advances
        if e.schema_version
        in {
            "calendar_sporting_week_advance.v2",
            "calendar_sporting_week_advance.v3",
        }
    } != {t.command_id for t in state.transitions}:
        raise ValueError(
            "Official sporting advances and Week Transition receipts differ"
        )
    for i, transition in enumerate(state.transitions):
        receipt = next(
            (r for r in state.receipts if r.command_id == transition.command_id), None
        )
        impact = receipt.result.get("impact") if receipt else None
        if not isinstance(impact, dict):
            raise TypeError("Tour transition receipt lacks its authoritative impact")
        if (
            receipt is None
            or receipt.result.get("impact", {}).get("ranking")
            != state.rankings[i + 1].model_dump(mode="json")
            or receipt.result.get("impact", {}).get("ranking_fingerprint")
            != transition.ranking_fingerprint
            or receipt.result.get("impact", {}).get("target_week")
            != transition.target_week.model_dump(mode="json")
        ):
            raise ValueError(
                "Tour transition receipt differs from authoritative publication"
            )
        expected_public = {
            "kind": (
                "season_transition_completed"
                if transition.completed_week.season_index
                != transition.target_week.season_index
                else "week_transition_completed"
            ),
            "week": transition.target_week.model_dump(mode="json"),
            "ranking_fingerprint": transition.ranking_fingerprint,
            "source_command_id": transition.command_id,
            "announced_edition_ids": [
                a.edition.edition_id
                for a in state.editions
                if a.edition.announcement_week.ordinal == transition.target_week.ordinal
            ],
        }
        if transition.public_event != expected_public:
            raise ValueError(
                "Public Week Transition event differs from effective announcements/ranking"
            )
        event = advances.get(transition.command_id)
        if (
            event is None
            or event.schema_version
            != (
                "calendar_sporting_week_advance.v3"
                if transition.completed_week.season_index
                != transition.target_week.season_index
                else "calendar_sporting_week_advance.v2"
            )
            or event.fingerprint != transition.sporting_advance_fingerprint
            or event.target_week != transition.target_week
            or event.policy
            != effective_policy(state, transition.completed_week).development
        ):
            raise ValueError("Official transition lacks coupled development evidence")
        sporting = impact.get("sporting")
        if (
            not isinstance(sporting, dict)
            or sporting.get("advance") != event.model_dump(mode="json")
            or sporting.get("advance_fingerprint") != event.fingerprint
        ):
            raise ValueError(
                "Tour transition receipt differs from actual sporting development"
            )
        if world is not None:
            from beta_engine.domain.players.calendar_sporting_week import (
                age_in_run_years,
            )

            ages = tuple(
                sorted(
                    (p.player_id, int(age_in_run_years(p, transition.target_week)))
                    for p in world.players
                )
            )
            retired = tuple(
                pid
                for pid, age in ages
                if age >= world.lifecycle_policy.automatic_retirement_age
            )
            if (transition.ages, transition.retired_player_ids) != (ages, retired):
                raise ValueError(
                    "Transition lifecycle differs from authentic birth identities/policy"
                )
        # Rebuild each publication from actual immutable point sources and the
        # then-effective policy. Never take stored snapshot totals as inputs.
        prefix = state.model_copy(update={"rankings": state.rankings[: i + 1]})
        expected = calculate_tour_ranking(
            prefix,
            checkpoint,
            target=transition.target_week,
            retired=transition.retired_player_ids,
        )
        if expected != state.rankings[i + 1]:
            raise ValueError(
                "Official ranking does not rebuild from authoritative Edition results"
            )


def decode_authenticated_tour(payload, *, run_id, branch_id):
    """Project ONLY the exact payload already authenticated by the repository.

    Internal to repository projections/Save, after its full immutable
    lineage/component/physical-source gate. This is not an alternative validator
    for raw JSON, live state or new Save candidates. Return a freshly decoded
    value, never a shared mutable object or a cached physical-source proof.
    """
    component = payload.get("content", {}).get(COMPONENT_KEY)
    if component is None:
        return None
    if not isinstance(component, dict) or set(component) != {"state", "fingerprint"}:
        raise ValueError("Malformed authenticated Saved Tour projection")
    state = parse_tour_json(json.dumps(component["state"]))
    if (state.run_id, state.branch_id, state.fingerprint) != (
        run_id, branch_id, component["fingerprint"],
    ):
        raise ValueError("Authenticated Saved Tour projection identity/hash changed")
    return state


def saved_tour(
    payload, *, run_id, branch_id, checkpoint=None, _verified_competition=None
):
    component = payload.get("content", {}).get(COMPONENT_KEY)
    if component is None:
        verify_tour(None, checkpoint)
        return None
    if not isinstance(component, dict) or set(component) != {"state", "fingerprint"}:
        raise ValueError("Malformed Saved native Tour component")
    state = parse_tour_json(json.dumps(component["state"]))
    if (state.run_id, state.branch_id, state.fingerprint) != (
        run_id,
        branch_id,
        component["fingerprint"],
    ):
        raise ValueError("Saved native Tour identity/hash mismatch")
    if checkpoint is None:
        from beta_engine.infrastructure.db.calendar_sporting_checkpoint import (
            parse_checkpoint_json,
        )

        raw = payload.get("content", {}).get("calendar_player_sporting_checkpoint")
        if raw is None:
            raise ValueError("Saved Tour lacks sporting checkpoint")
        checkpoint = parse_checkpoint_json(json.dumps(raw["state"]))
        if checkpoint.fingerprint != raw["fingerprint"]:
            raise ValueError("Saved sporting owner fingerprint mismatch")
    from beta_engine.infrastructure.db.initial_world_state import (
        load_saved_initial_world,
    )

    if (
        checkpoint is not _verified_competition
        or checkpoint is None
        or checkpoint.schema_version not in {"calendar_sporting_checkpoint.v12", "calendar_sporting_checkpoint.v13"}
    ):
        verify_tour(
            state,
            checkpoint,
            load_saved_initial_world(payload, run_id=run_id, branch_id=branch_id),
            _native_payload=payload,
        )
    elif state.checkpoint_fingerprint != checkpoint.fingerprint:
        raise ValueError("Verified native competition differs from coupled Tour")
    from beta_engine.infrastructure.db.player_lifecycle_state import (
        load_saved_lifecycle,
    )

    life = load_saved_lifecycle(payload, run_id=run_id, branch_id=branch_id)
    if not life or (life[-1].week.ordinal, life[-1].fingerprint) != (
        state.week.ordinal,
        state.lifecycle_fingerprint,
    ):
        raise ValueError("Saved native Tour lacks its coupled lifecycle owner")
    return state


def capture_tour(
    session, payload, *, run_id, branch_id, _defer_full_verification: bool = False,
    _authenticated_prefix=None, _repository=None,
):
    from beta_engine.infrastructure.db.calendar_sporting_checkpoint import (
        load_checkpoint,
    )

    state = load_tour(session, run_id=run_id, branch_id=branch_id, _repository=_repository)
    if state is not None and state.schema_version == 'calendar_tour_authority.v5':
        from beta_engine.infrastructure.db.tournament_application_submissions import TournamentApplicationSubmissionStore

        actual = {item.fingerprint for item in TournamentApplicationSubmissionStore(session).list(
            run_id=run_id, branch_id=branch_id,
        ) if item.schema_version.endswith('.v2')}
        expected = {item.fingerprint for authority in state.editions for item in authority.submissions}
        if actual != expected:
            raise ValueError('Tour Save submissions differ from actual production Entry authority')
    from beta_engine.infrastructure.db.initial_world_state import get_initial_world

    if not _defer_full_verification:
        verify_tour(
            state,
            load_checkpoint(session, run_id=run_id, branch_id=branch_id),
            get_initial_world(session, run_id=run_id, branch_id=branch_id),
        )
    # The standalone Saved component validator does not inspect pre-play
    # origin revisions. This independent live-origin guard is always required.
    prefix = (
        _authenticated_prefix if state is not None and _authenticated_prefix is not None
        and state.schema_version == _authenticated_prefix.schema_version == 'calendar_tour_authority.v5'
        else None
    )
    verify_tour_origins(session, state, _verified_global_prefix=prefix)
    if state:
        from beta_engine.domain.run_packages import canonical_hash
        body = state.model_dump(mode="json")
        payload["content"][COMPONENT_KEY] = {
            "fingerprint": canonical_hash(body),
            "state": body,
        }
        from beta_engine.infrastructure.db.player_lifecycle_state import (
            load_saved_lifecycle,
        )

        if not _defer_full_verification:
            life = load_saved_lifecycle(payload, run_id=run_id, branch_id=branch_id)
            if not life or life[-1].fingerprint != state.lifecycle_fingerprint:
                raise ValueError("Tour Save lacks its coupled current lifecycle")
    return state


def restore_tour(
    session,
    *,
    current_payload,
    target_payload,
    run_id,
    branch_id,
    _validated_states=None,
):
    if _validated_states is None:
        current = saved_tour(current_payload, run_id=run_id, branch_id=branch_id)
        target = saved_tour(target_payload, run_id=run_id, branch_id=branch_id)
    else:
        # Only accepted from the same transaction's authenticated Saved lineage.
        # The exact live Tour must still match its previously signed owner.
        current, target = _validated_states
    if load_tour(session, run_id=run_id, branch_id=branch_id) != current:
        raise ValueError("Live Tour differs from current Saved HEAD")
    row = session.get(CalendarTourAuthorityModel, (run_id, branch_id))
    if row:
        session.delete(row)
        session.flush()
    if target:
        put_tour(session, target)


def _origin_inputs(row, cache, *, with_health=False, _decode_tour=True):
    """Decode a narrow source projection, never a physical validation proof."""
    if cache is None:
        payload = json.loads(row.payload_json)
        component = payload.get('content', {}).get(COMPONENT_KEY, {})
        return payload, parse_tour_json(json.dumps(component['state'])) if component and _decode_tour else None
    key = (row.run_id, row.branch_id, row.revision_id,
        hashlib.sha256(row.payload_json.encode('utf-8')).digest(), with_health)
    known = cache.get(key)
    if known is not None:
        # Retain immutable JSON only. Each caller gets fresh values/models and
        # cannot mutate another source read or poison a subsequent cache hit.
        projection = json.loads(known[1])
        component = projection['content'].get(COMPONENT_KEY, {})
        origin = parse_tour_json(json.dumps(component['state'])) if component and _decode_tour else None
        return projection, origin
    payload = json.loads(row.payload_json)
    content = payload.get('content', {})
    component = content.get(COMPONENT_KEY, {})
    origin = parse_tour_json(json.dumps(component['state'])) if component and _decode_tour else None
    projection = {
        'run': payload.get('run'), 'branch': payload.get('branch'),
        'content': {
            COMPONENT_KEY: component,
            'calendar_player_sporting_checkpoint': {
                'fingerprint': content.get('calendar_player_sporting_checkpoint', {}).get('fingerprint')
            },
            **({k: content[k] for k in ('run_prospect_source',) if k in content}),
            **({k: content[k] for k in ('player_health_state', 'initial_world', 'player_lifecycle') if with_health and k in content}),
        },
    }
    encoded = json.dumps(projection)
    size = len(encoded.encode('utf-8'))
    if cache is not None and size <= 32 * 1024 * 1024:
        cache[key] = (size, encoded)
        while len(cache) > 128 or sum(v[0] for v in cache.values()) > 32 * 1024 * 1024:
            cache.pop(next(iter(cache)))
    return projection, origin


def verify_tour_origins(session, state, *, _reachable_revision_ids=None, _origin_cache=None,
                        _verified_global_prefix=None):
    """Each played event must reference a Signed revision already owning its draw."""
    if state is None:
        return
    from beta_engine.infrastructure.db.models import (
        BranchSavedRevisionModel,
        RunBranchModel,
    )
    from beta_engine.infrastructure.db.native_fork_runtime_state import actual_saved_revision_reference

    branch = session.get(RunBranchModel, state.branch_id)
    revision_id = (
        branch.saved_head_revision_id
        if branch and branch.run_id == state.run_id
        else None
    )
    reachable = set()
    while revision_id:
        if revision_id in reachable:
            raise ValueError("Tour source Saved lineage contains a cycle")
        reachable.add(revision_id)
        row = actual_saved_revision_reference(session, state.run_id, revision_id)
        if row is None or row[1] != state.run_id:
            raise ValueError("Tour source Saved lineage is missing or foreign")
        revision_id = row[4]

    if _reachable_revision_ids is not None:
        # A historical fork may only inherit authorities already present at its
        # selected Saved boundary, even when the original Branch has moved on.
        reachable.intersection_update(_reachable_revision_ids)

    if state.schema_version == "calendar_tour_authority.v3":
        first_source = None
        for index, receipt in enumerate(
            state.receipts[len(state.native_root_tour.receipts) :]
        ):
            command = receipt.request.get("command", {})
            source_id = command.get("expected_saved_head")
            row = session.get(BranchSavedRevisionModel, source_id)
            if (
                source_id not in reachable
                or row is None
                or (row.run_id, row.branch_id) != (state.run_id, state.branch_id)
            ):
                raise ValueError("Native transition Saved origin is missing or foreign")
            payload, _ = _origin_inputs(row, _origin_cache, with_health=True)
            content = payload.get("content", {})
            tour = content.get(COMPONENT_KEY, {})
            cp = content.get("calendar_player_sporting_checkpoint", {})
            if tour.get("fingerprint") != command.get(
                "expected_tour_fingerprint"
            ) or cp.get("fingerprint") != command.get(
                "expected_checkpoint_fingerprint"
            ):
                raise ValueError(
                    "Native command does not own its actual Saved Tour/checkpoint"
                )
            from beta_engine.infrastructure.db.run_prospect_source_state import (
                load_saved_run_prospect_source,
                validate_run_prospect_source_extension,
            )

            source = load_saved_run_prospect_source(payload, run_id=state.run_id)
            if source is None:
                raise ValueError(
                    "Native transition Saved origin lacks its prospect source"
                )
            if index == 0:
                from beta_engine.infrastructure.db.player_health_state import (
                    load_saved_health,
                )

                first_source = source
                if (
                    source_id != state.native_root_saved_head
                    or parse_tour_json(json.dumps(tour["state"]))
                    != state.native_root_tour
                    or len(
                        load_saved_health(
                            payload, run_id=state.run_id, branch_id=state.branch_id
                        )
                    )
                    != state.native_root_health_state_count
                ):
                    raise ValueError(
                        "Native root differs from its actual immutable Saved authority"
                    )
            else:
                validate_run_prospect_source_extension(first_source, source)
                first_source = source

    if state.schema_version in {"calendar_tour_authority.v4", "calendar_tour_authority.v5"}:
        prefix = _verified_global_prefix
        if prefix is not None and (
            state.schema_version != "calendar_tour_authority.v5"
            or prefix.schema_version != state.schema_version
            or (prefix.run_id, prefix.branch_id) != (state.run_id, state.branch_id)
            or prefix.competition_root_tour != state.competition_root_tour
            or prefix.competition_root_saved_head != state.competition_root_saved_head
            or state.receipts[:len(prefix.receipts)] != prefix.receipts
        ):
            raise ValueError("Verified global origin prefix differs from current history")
        if prefix is None:
            verify_tour_origins(
                session, state.competition_root_tour,
                _reachable_revision_ids=_reachable_revision_ids,
                _origin_cache=_origin_cache,
            )
        root_count = len(state.competition_root_tour.receipts)
        start = len(prefix.receipts) if prefix is not None else root_count
        expected_receipts = [receipt.model_dump(mode='json') for receipt in state.receipts]
        previous_source = None
        if start > root_count:
            previous_id = state.receipts[start - 1].request["command"]["expected_saved_head"]
            previous_row = session.get(BranchSavedRevisionModel, previous_id)
            if previous_id not in reachable or previous_row is None or (
                previous_row.run_id, previous_row.branch_id
            ) != (state.run_id, state.branch_id):
                raise ValueError("Verified global prefix source is missing or foreign")
            from beta_engine.infrastructure.db.run_prospect_source_state import load_saved_run_prospect_source
            previous_payload, _ = _origin_inputs(previous_row, _origin_cache, _decode_tour=False)
            previous_source = load_saved_run_prospect_source(previous_payload, run_id=state.run_id)
        for index, receipt in enumerate(state.receipts[start:], start=start - root_count):
            command = receipt.request["command"]
            source_id = command["expected_saved_head"]
            row = session.get(BranchSavedRevisionModel, source_id)
            if (
                source_id not in reachable
                or row is None
                or (row.run_id, row.branch_id) != (state.run_id, state.branch_id)
            ):
                raise ValueError(
                    "Native competition Saved origin is missing or foreign"
                )
            payload, origin = _origin_inputs(row, _origin_cache, _decode_tour=index == 0)
            content = payload.get("content", {})
            raw = content.get(COMPONENT_KEY, {})
            cp = content.get("calendar_player_sporting_checkpoint", {})
            from beta_engine.domain.calendar.run_calendar import RunCalendar

            source_clock = RunCalendar.from_metadata(payload["run"]["run_calendar"])
            if (
                command["action"] == "create-edition"
                and command["data"]["week"]["calendar"] != source_clock.to_metadata()
            ):
                raise ValueError(
                    "Native Edition calendar did not exist in its actual Saved origin"
                )
            if (
                command["action"] in {"transition", "season-transition"}
                and receipt.result["impact"]["target_week"]["calendar"]
                != source_clock.to_metadata()
            ):
                raise ValueError(
                    "Native transition horizon did not exist in its actual Saved origin"
                )
            if command["action"] not in {"next-slot", "next-match"} and cp.get("fingerprint") != command["expected_checkpoint_fingerprint"]:
                raise ValueError(
                    "Native competition does not own its actual Saved checkpoint"
                )
            if (
                command["action"]
                in {"play", "confirm-result", "transition", "season-transition"}
                and raw.get("fingerprint") != command["expected_tour_fingerprint"]
            ):
                raise ValueError(
                    "Native competition requires its actual Saved Tour authority"
                )
            # Configuration may share one Working Draft, but its Saved base must
            # already own a prefix of the actual confirmed predecessor receipts.
            # Physical source/component gates already authenticated this row.
            # Compare its actual receipt values; do not decode every unrelated
            # ranking snapshot again merely to inspect one immutable prefix.
            previous_receipts = expected_receipts[:root_count + index]
            actual_receipts = raw.get('state', {}).get('receipts')
            if (not isinstance(actual_receipts, list)
                or actual_receipts != previous_receipts[:len(actual_receipts)]):
                raise ValueError(
                    "Native competition Saved origin is not its preceding history"
                )
            from beta_engine.infrastructure.db.run_prospect_source_state import (
                load_saved_run_prospect_source,
                validate_run_prospect_source_extension,
            )

            source = load_saved_run_prospect_source(payload, run_id=state.run_id)
            if index == 0:
                previous_source = source
                if (
                    source_id != state.competition_root_saved_head
                    or origin != state.competition_root_tour
                ):
                    raise ValueError(
                        "Native competition root differs from actual Saved origin"
                    )
            else:
                if previous_source is not None or source is not None:
                    validate_run_prospect_source_extension(previous_source, source)
                previous_source = source

    terminal_clocks = {}
    for receipt in state.receipts:
        if receipt.request.get("command", {}).get("action") == "confirm-result":
            for result in receipt.result.get("results", []):
                if result.get("schema_version") in {"calendar_terminal_edition_result.v1", "calendar_terminal_edition_result.v2"}:
                    terminal_clocks.setdefault(result["edition_id"], []).append(result["completed_week"]["calendar"])
    for authority in state.editions:
        if not authority.played_saved_head:
            continue
        row = session.get(BranchSavedRevisionModel, authority.played_saved_head)
        if (
            row is None
            or authority.played_saved_head not in reachable
            or (row.run_id, row.branch_id)
            != (
                state.run_id,
                state.branch_id,
            )
        ):
            raise ValueError("Edition played origin is missing or foreign")
        origin_payload, _ = _origin_inputs(row, _origin_cache, _decode_tour=False)
        # The terminal record's clock must have existed at actual play. An
        # extension/rehashed event cannot retroactively create publication time.
        if any(clock != origin_payload["run"]["run_calendar"] for clock in terminal_clocks.get(authority.edition.edition_id, ())):
            raise ValueError("Terminal result calendar did not exist in its actual played Saved origin")
        body = origin_payload.get('content', {}).get(COMPONENT_KEY, {}).get('state', {})
        edition = next((a for a in body.get('editions', [])
            if a.get('edition', {}).get('edition_id') == authority.edition.edition_id), None)
        # The complete source is independently authenticated; strictly decode
        # the one pre-play authority needed here, retaining all original checks.
        frozen = CalendarEditionAuthority.model_validate_json(json.dumps(edition)) if edition else None
        if (
            frozen is None
            or frozen.tournament_fingerprint is not None
            or frozen.edition != authority.edition
            or frozen.submissions != authority.submissions
            or frozen.field != authority.field
            or frozen.draw != authority.draw
            # All immutable pre-play provenance, including the exact frozen
            # ranking binding and creation source, must remain identical.
            # It is not enough that the seeded draw happens to look equal.
            or frozen.execution_fingerprint != authority.execution_fingerprint
            or frozen.draw_seed != authority.draw_seed
            or frozen.draw_command_id != authority.draw_command_id
        ):
            raise ValueError(
                "Edition/draw authority did not exist in the pre-play Saved revision"
            )
