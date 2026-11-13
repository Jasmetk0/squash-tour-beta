"""Read-only native player career: overview, timeline and factual milestones.

Pure projection over an already authenticated Saved native Tour (the caller proves the
Saved Revision, lineage and Branch first, exactly as for ``signed_tour_records``). It
reads only facts that are effective at or before the requested ``as_of`` week, so a
past view contains no future title and a Branch never sees a sibling's results: the
Tour state belongs to exactly one Run/Branch.

Every entry carries the identity of the immutable source it is derived from. What the
sources do not cover stays explicitly unavailable instead of being guessed:

* the coverage starts where the Run's recorded history starts, so the first recorded
  title / Top-100 entry is a *first recorded* fact, never a lifetime first;
* injuries and returns have no supported source yet;
* all numeric thresholds (Top 100) are provisional catalog values.

This module creates no events, Saves or sport, and does not influence the simulation.
"""

from __future__ import annotations

from beta_engine.application.calendar_tour_season_summary import native_tour_identities
from beta_engine.domain.tournaments.calendar_tour import tour_turn_pro_decisions

SCHEMA = "native_player_career.v1"
# Provisional milestone catalog; kinds are stable ids, thresholds are calibration.
TOP_RANK_THRESHOLD = 100
UNSUPPORTED = ("injury", "return_from_injury")


def _week(week):
    return week.model_dump(mode="json") if hasattr(week, "model_dump") else week


def _ordinal(snapshot):
    from beta_engine.domain.calendar.run_calendar import RunCalendar

    calendar = RunCalendar.from_metadata(snapshot.run_calendar)
    return calendar.ordinal(snapshot.week.season_index, snapshot.week.week)


def _played_by_edition(state):
    played = {
        r.request.get("command", {}).get("edition_id"): r.result["played"]
        for r in state.receipts
        if r.request.get("command", {}).get("action") == "play"
    }
    for receipt in state.receipts:
        played.update(receipt.result.get("completed_editions", {}))
    return played


def _turn_pro(state, world, player_id, as_of):
    """(week, source) of the player's entry among professionals, or None."""
    if world.initial_turn_pro is not None:
        if player_id in world.initial_turn_pro.professional_player_ids:
            return None, {
                "kind": "opening_population",
                "fingerprint": world.fingerprint,
            }, True
        decision = next(
            (d for d in tour_turn_pro_decisions(state) if d.player_id == player_id), None
        )
        if decision is not None and decision.effective_week.ordinal <= as_of:
            return decision.effective_week, {
                "kind": "player_ai_decision",
                "fingerprint": decision.fingerprint,
                "has_recorded_evidence": decision.evidence is not None,
            }, False
        return None, None, False
    # Historical rule: the first valid application is the entry.
    firsts = [
        s for a in state.editions for s in a.submissions if s.player_id == player_id
    ]
    if not firsts:
        return None, None, False
    first = min(firsts, key=lambda s: (s.submission_week.ordinal, s.application_id))
    if first.submission_week.ordinal > as_of:
        return None, None, False
    return first.submission_week, {
        "kind": "first_application", "fingerprint": first.application_id,
    }, False


def native_player_career(state, world, player_id, *, as_of_ordinal=None):
    if (state.run_id, state.branch_id) != (world.run_id, world.branch_id):
        raise ValueError("Player career requires the same Saved Run/Branch world")
    as_of = state.week.ordinal if as_of_ordinal is None else as_of_ordinal
    if type(as_of) is not int or not 0 <= as_of <= state.week.ordinal:
        raise ValueError("Career view cannot be later than the Saved Tour or negative")
    identities = native_tour_identities(state, world)
    profile = identities.get(player_id)
    if profile is None:
        raise KeyError("Player does not belong to this Run/Branch")
    if as_of < getattr(world, "career_birth_ordinals", {}).get(player_id, 0):
        raise KeyError("Player has no recorded identity at this historical week")

    events = []
    entry_week, entry_source, opening_pro = _turn_pro(state, world, player_id, as_of)
    if opening_pro:
        events.append({
            "kind": "turn_pro", "effective_week": None, "sort": (-1, 0),
            "detail": {"opening_professional": True},
            "source": entry_source,
        })
    elif entry_week is not None:
        events.append({
            "kind": "turn_pro", "effective_week": _week(entry_week),
            "sort": (entry_week.ordinal, 0), "detail": {},
            "source": entry_source,
        })

    # Edition results: only confirmed, authenticated, already played Editions.
    played = _played_by_edition(state)
    titles = finals = appearances = 0
    first_title = None
    for authority in sorted(state.editions, key=lambda a: (a.edition.week.ordinal, a.edition.edition_id)):
        item = authority.edition
        if not authority.result_confirmed or item.week.ordinal > as_of:
            continue
        record = played.get(item.edition_id)
        if not record or record.get("fingerprint") != authority.tournament_fingerprint:
            raise ValueError("Career Edition lacks authenticated played evidence")
        award = next((a for a in record["prepared_awards"] if a["player_id"] == player_id), None)
        if award is None:
            continue
        appearances += 1
        stage = award["reached_stage"]
        entry = {
            "kind": "edition_result", "effective_week": _week(item.week),
            "sort": (item.week.ordinal, 1),
            "detail": {
                "edition_id": item.edition_id, "name": item.name,
                "reached_stage": stage, "awarded_points": award["main_points"],
            },
            "source": {
                "kind": "played_edition",
                "fingerprint": authority.tournament_fingerprint,
                "edition_id": item.edition_id,
            },
        }
        events.append(entry)
        if stage == "finalist":
            finals += 1
        if stage == "champion":
            titles += 1
            if first_title is None:
                first_title = entry

    # Published rankings: only snapshots that exist at or before the requested week.
    best = None
    first_top = None
    current = None
    career_highs = []
    for snapshot in state.rankings:
        ordinal = _ordinal(snapshot)
        if ordinal > as_of:
            continue
        row = next((r for r in snapshot.rows if r.player_id == player_id), None)
        # "Current" belongs to the latest publication, even when it omits this player.
        current = None if row is None else (snapshot, row)
        if row is None:
            continue
        if first_top is None and row.rank <= TOP_RANK_THRESHOLD:
            first_top = (snapshot, row, ordinal)
        if best is None or row.rank < best[1].rank:
            best = (snapshot, row, ordinal)
            career_highs.append(best)

    first_ranking = state.rankings[0]
    covered_from = _ordinal(first_ranking)

    def ranking_event(kind, found):
        snapshot, row, ordinal = found
        return {
            "kind": kind, "effective_week": _week(snapshot.week), "sort": (ordinal, 2),
            "detail": {
                "rank": row.rank, "points": row.points,
                "threshold": TOP_RANK_THRESHOLD if kind == "first_top_rank" else None,
                "first_recorded_ranking_week": ordinal == covered_from,
            },
            "source": {"kind": "published_ranking", "fingerprint": snapshot.fingerprint},
        }

    if first_top is not None:
        events.append(ranking_event("first_top_rank", first_top))
    # Each improved personal record remains an immutable historical fact.
    for improvement in career_highs:
        events.append(ranking_event("career_high_ranking", improvement))

    # Retirement from the first signed transition that retires the player.
    retired = next(
        (t for t in (*getattr(getattr(state, "pre_tour_turn_pro", None), "weeks", ()), *state.transitions)
         if player_id in t.retired_player_ids and t.target_week.ordinal <= as_of),
        None,
    )
    turn_pro_rule = getattr(world, "initial_turn_pro", None) is not None
    never_entered = entry_week is None and not opening_pro
    if retired is not None:
        events.append({
            "kind": "retirement", "effective_week": _week(retired.target_week),
            "sort": (retired.target_week.ordinal, 3),
            # Under the historical rule there is no Turn Pro event, so the honest fact is
            # that the player never entered the Tour; Master v87 names the exception.
            "detail": (
                {"without_turn_pro": never_entered} if turn_pro_rule
                else {"without_tour_entry": never_entered}
            ),
            "source": {"kind": "week_transition", "fingerprint": retired.sporting_advance_fingerprint,
                       "command_id": retired.command_id},
        })

    events.sort(key=lambda e: e["sort"])
    timeline = [{k: v for k, v in e.items() if k != "sort"} for e in events]
    milestone_kinds = {"turn_pro", "first_top_rank", "career_high_ranking", "retirement"}
    milestones = [e for e in timeline if e["kind"] in milestone_kinds]
    if first_title is not None:
        milestones.append({
            **{k: v for k, v in first_title.items() if k != "sort"},
            "kind": "first_recorded_title",
        })
        milestones.sort(key=lambda e: (
            -1 if e["effective_week"] is None else
            state.week.calendar.ordinal(e["effective_week"]["season_index"], e["effective_week"]["week"])
        ))
    summary = None
    if retired is not None:
        summary = {
            "retired_week": _week(retired.target_week),
            "turn_pro_rule": turn_pro_rule,
            "without_turn_pro": never_entered if turn_pro_rule else None,
            "without_tour_entry": never_entered if not turn_pro_rule else None,
            "opening_professional": opening_pro,
            "entry_week": None if entry_week is None else _week(entry_week),
            "titles": titles, "finals": finals, "editions_played": appearances,
            "first_recorded_title_week": None if first_title is None else first_title["effective_week"],
            "career_high_rank": None if best is None else best[1].rank,
            "source": {"kind": "week_transition", "fingerprint": retired.sporting_advance_fingerprint,
                       "command_id": retired.command_id},
            # A summary of recorded facts only: no cause is implied for the end of a career.
            "note": "Totals cover recorded history only; no cause of retirement is implied.",
        }
    return {
        "schema_version": SCHEMA,
        "run_id": state.run_id,
        "branch_id": state.branch_id,
        "source_tour_fingerprint": state.fingerprint,
        "as_of_ordinal": as_of,
        "player": {
            "player_id": player_id, "name": profile.name,
            "country_code": profile.country_code,
        },
        "covered_period": {
            "first_recorded_ranking_ordinal": covered_from,
            "note": "Coverage starts with the Run's first recorded ranking; "
                    "earlier history is unknown, not zero.",
        },
        "overview": {
            "status": (
                "retired" if retired is not None
                else "professional" if (entry_week is not None or opening_pro)
                else "not_professional"
            ),
            "titles": titles, "finals": finals, "editions_played": appearances,
            "career_high_rank": None if best is None else best[1].rank,
            "current_rank": None if current is None else current[1].rank,
        },
        "milestones": milestones,
        "timeline": timeline,
        "retirement_summary": summary,
        "unsupported": list(UNSUPPORTED),
    }
