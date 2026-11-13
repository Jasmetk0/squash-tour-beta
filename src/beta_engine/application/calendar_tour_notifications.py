"""Following alerts derived from recorded career facts (Master 25.6/25.6.1, 27.23).

A *notification card* is a pure function of (authenticated Saved Tour of one Branch,
the Run's follows, the as-of week). Nothing about a card is stored except the Admin's
read/hidden state, so a retried command, a reconnect or a restart can never create a
second card, and reading or hiding can never delete a fact or touch the simulation.

This is a layer of attention, not a log: the World Event Log, Audit Log and Task
Center keep their own meaning, and facts stay in the career history for everyone,
followed or not. Cards never include facts later than the as-of week and, because the
Tour state belongs to one Branch, never a sibling Branch's results.

Provisional calibration (explicitly not canon; thresholds are exposed in ``criteria``):

* personal milestones of a followed player always alert;
* a followed country alerts for milestones of its *domestic leaders* (best
  ``DOMESTIC_LEADERS`` players of the country in the latest published ranking at the
  fact's week) and for exceptional individual facts of other representatives (a
  first recorded title or a published ranking of ``EXCEPTIONAL_RANK`` or better);
  it does not alert for every minor milestone of every representative;
* facts of one player at most ``GROUP_WINDOW`` weeks apart form one card.
"""

from __future__ import annotations

from beta_engine.application.calendar_tour_player_career import native_player_career
from beta_engine.application.calendar_tour_season_summary import native_tour_identities
from beta_engine.domain.run_packages import canonical_hash

SCHEMA = "native_tour_notifications.v1"
DOMESTIC_LEADERS = 3
EXCEPTIONAL_RANK = 1
GROUP_WINDOW = 2
ALERT_KINDS = ("turn_pro", "first_recorded_title", "first_top_rank", "career_high_ranking", "retirement")
CRITERIA = {
    "domestic_leaders": DOMESTIC_LEADERS,
    "exceptional_rank": EXCEPTIONAL_RANK,
    "group_window_weeks": GROUP_WINDOW,
    "alert_kinds": list(ALERT_KINDS),
    "status": "provisional calibration",
}


def _ordinal(week):
    return week["season_index"] * 10_000 + week["week"]  # monotonic sort key only


def _domestic_leaders(state, identities, country, fact_ordinal):
    """Best players of a country in the latest published ranking at or before as_of."""
    from beta_engine.application.calendar_tour_player_career import _ordinal as ranking_ordinal

    latest = None
    for snapshot in state.rankings:
        if ranking_ordinal(snapshot) <= fact_ordinal:
            latest = snapshot
    if latest is None:
        return set()
    domestic = [
        r for r in latest.rows
        if identities.get(r.player_id) is not None and identities[r.player_id].country_code == country
    ]
    return {r.player_id for r in domestic[:DOMESTIC_LEADERS]}


def derive_followed_facts(state, world, follows, as_of):
    """One entry per (player, fact) that matches at least one follow; never duplicated."""
    identities = {pid: profile for pid, profile in native_tour_identities(state, world).items()
                  if getattr(world, "career_birth_ordinals", {}).get(pid, 0) <= as_of}
    players = {}
    for kind, subject, enabled in follows:
        if not enabled:
            continue
        if kind == "player":
            if subject in identities:
                players.setdefault(subject, set()).add(("player", subject))
        elif kind == "country":
            for pid, profile in identities.items():
                if profile.country_code == subject:
                    players.setdefault(pid, set()).add(("country", subject))
    facts = []
    for pid in sorted(players):
        reasons = players[pid]
        career = native_player_career(state, world, pid, as_of_ordinal=as_of)
        for milestone in career["milestones"]:
            if milestone["kind"] not in ALERT_KINDS or milestone["effective_week"] is None:
                continue
            why = set()
            if ("player", pid) in reasons:
                why.add(f"player:{pid}")
            country = identities[pid].country_code
            if ("country", country) in reasons:
                week = milestone["effective_week"]
                fact_ordinal = state.week.calendar.ordinal(week["season_index"], week["week"])
                leaders = _domestic_leaders(state, identities, country, fact_ordinal)
                rank = milestone["detail"].get("rank")
                exceptional = milestone["kind"] == "first_recorded_title" or (
                    milestone["kind"] in {"first_top_rank", "career_high_ranking"}
                    and isinstance(rank, int) and rank <= EXCEPTIONAL_RANK
                )
                if pid in leaders:
                    why.add(f"country:{country}:domestic_leader")
                elif exceptional:
                    why.add(f"country:{country}:exceptional_individual")
            if why:
                facts.append({
                    "player_id": pid, "player_name": identities[pid].name,
                    "country_code": country, "kind": milestone["kind"],
                    "effective_week": milestone["effective_week"],
                    "detail": milestone["detail"], "source": milestone["source"],
                    "reasons": sorted(why),
                })
    return facts


def group_cards(branch_id, facts):
    """Group a player's nearby facts into one card; the key is anchored on its first fact."""
    cards = []
    by_player = {}
    for fact in facts:
        by_player.setdefault(fact["player_id"], []).append(fact)
    for pid in sorted(by_player):
        ordered = sorted(
            by_player[pid],
            key=lambda f: (_ordinal(f["effective_week"]), f["kind"], f["source"]["fingerprint"]),
        )
        groups = [[ordered[0]]]
        for fact in ordered[1:]:
            gap = _week_gap(groups[-1][-1]["effective_week"], fact["effective_week"])
            if gap <= GROUP_WINDOW:
                groups[-1].append(fact)
            else:
                groups.append([fact])
        for group in groups:
            anchor = group[0]
            key = canonical_hash({
                "kind": "native_notification.v1", "branch": branch_id, "player": pid,
                "anchor": [anchor["kind"], anchor["source"]["fingerprint"],
                           anchor["effective_week"]],
            })
            reasons = sorted({r for f in group for r in f["reasons"]})
            cards.append({
                "notification_key": key,
                "player_id": pid,
                "player_name": anchor["player_name"],
                "country_code": anchor["country_code"],
                "first_week": group[0]["effective_week"],
                "last_week": group[-1]["effective_week"],
                "item_count": len(group),
                "reasons": reasons,
                # Every item keeps its own source; the card is only a grouping.
                "items": group,
            })
    cards.sort(key=lambda c: (-_ordinal(c["last_week"]), c["notification_key"]))
    return cards


def _week_gap(a, b):
    """Weeks between two effective weeks (same-season arithmetic is enough for a window)."""
    return abs(_ordinal(b) - _ordinal(a)) if a["season_index"] == b["season_index"] else (
        # Across a season boundary the facts are not treated as one tournament's aftermath.
        10_000
    )


def derive_notifications(state, world, follows, branch_id, as_of_ordinal=None):
    as_of = state.week.ordinal if as_of_ordinal is None else as_of_ordinal
    if type(as_of) is not int or not 0 <= as_of <= state.week.ordinal:
        raise ValueError("Notification view cannot be later than the Saved Tour")
    facts = derive_followed_facts(state, world, follows, as_of)
    return {
        "schema_version": SCHEMA,
        "run_id": state.run_id,
        "branch_id": branch_id,
        "source_tour_fingerprint": state.fingerprint,
        "as_of_ordinal": as_of,
        "criteria": CRITERIA,
        "cards": group_cards(branch_id, facts),
    }
