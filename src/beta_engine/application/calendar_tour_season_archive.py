"""Seasonal archive, world overview and honest comparison over signed summaries.

Read-only extension of ``calendar_tour_season_summary``: the caller authenticates the
complete Saved Revision first. Nothing here writes, publishes a ranking or pauses a
Run, and no composite country score is invented.

Rules of the comparison (Master 6.5/6.9, 21.5, 27.25, 31.40):

* a country or player that is *absent* from a season's summary was not represented in
  its Editions; that is "not represented", never a zero result, so no delta is shown
  unless both seasons contain the entity;
* a season without completed Editions is "no completed Editions", not zero titles;
* seasons played under a different effective ranking or development policy are
  flagged as limited-comparability, with the exact differing values;
* the ranking views stay distinct: the ranking published at Week W, the outgoing-policy
  Season Closing Ranking (final closure only) and the next season's Week-1 ranking.
"""

from __future__ import annotations

from beta_engine.application.calendar_tour_season_summary import (
    completed_season_indices,
    native_tour_season_summary,
)
from beta_engine.domain.run_packages import canonical_hash
from beta_engine.domain.tournaments.calendar_tour import effective_policy

try:  # Master v87 Turn Pro runtime (not on every base): debut evidence when recorded.
    from beta_engine.domain.tournaments.calendar_tour import tour_turn_pro_decisions
except ImportError:  # pragma: no cover - exercised only on a base without Turn Pro

    def tour_turn_pro_decisions(state):
        return ()

ARCHIVE_SCHEMA = "native_tour_season_archive.v1"
COMPARISON_SCHEMA = "native_tour_season_comparison_detail.v1"


def _last_week(state, season_index):
    from beta_engine.domain.calendar.run_week_position import RunWeekPosition

    clock = state.week.calendar
    return RunWeekPosition(
        calendar=clock, season_index=season_index, week=clock.weeks_per_year
    )


def season_rule_basis(state, season_index):
    """Effective policies at the season's last week (what produced its ranking)."""
    policy = effective_policy(state, _last_week(state, season_index))
    return {
        "ranking_policy_id": policy.ranking.policy_id,
        "ranking_best_n": policy.ranking.best_n,
        "development_policy_fingerprint": canonical_hash(
            policy.development.model_dump(mode="json")
        ),
        "weeks_per_season": state.week.calendar.weeks_per_year,
        "edition_point_tables_fingerprint": canonical_hash(sorted({
            canonical_hash(a.edition.point_table) for a in state.editions
            if a.edition.week.season_index == season_index
        })),
        "edition_formats_fingerprint": canonical_hash(sorted({
            canonical_hash({"main_entrant_count": a.edition.main_entrant_count,
                            "group_configuration": None if a.edition.group_configuration is None
                            else a.edition.group_configuration.model_dump(mode="json")})
            for a in state.editions if a.edition.week.season_index == season_index
        })),
    }


def season_comparability(state, selected_index, other_index):
    """Limited comparability with the exact differing rule values."""
    a = season_rule_basis(state, selected_index)
    b = season_rule_basis(state, other_index)
    differences = [
        {"field": key, "selected": a[key], "comparison": b[key]}
        for key in a
        if a[key] != b[key]
    ]
    return {
        "comparable": not differences,
        "differences": differences,
        # Honest scope: only these rule inputs are compared, not every category.
        "compared_fields": sorted(a),
        "not_compared": ["edition_categories", "qualification_geometry"],
    }


def _new_retirements(state, season_index):
    seen = set()
    result = []
    for transition in (*getattr(getattr(state, "pre_tour_turn_pro", None), "weeks", ()), *state.transitions):
        now = set(transition.retired_player_ids)
        if transition.target_week.season_index == season_index:
            result.extend(sorted(now - seen))
        seen |= now
    return result


def season_world_overview(state, world, season_index, summary):
    """Distinct participants, evidenced debuts and retirements of one season."""
    debuts = sorted(
        d.player_id
        for d in tour_turn_pro_decisions(state)
        if d.effective_week.season_index == season_index
    )
    if getattr(world, "initial_turn_pro", None) is None:
        # Historical rule: the first valid application is the debut.
        first = {}
        for authority in state.editions:
            for s in authority.submissions:
                known = first.get(s.player_id)
                if known is None or s.submission_week.ordinal < known:
                    first[s.player_id] = s.submission_week.ordinal
        clock = state.week.calendar
        debuts = sorted(
            pid
            for pid, ordinal in first.items()
            if clock.position_at_ordinal(ordinal).season_index == season_index
        )
    boundary = next(
        (
            r for r in state.rankings
            if r.week.season_index == season_index + 1 and r.week.week == 1
        ),
        None,
    )
    return {
        "completed_edition_count": summary["completed_edition_count"],
        "players_with_results": len(summary["players"]),
        "countries_represented": len(summary["countries"]),
        "titles_awarded": sum(c["titles"] for c in summary["countries"]),
        "turned_pro": debuts,
        "retired": _new_retirements(state, season_index),
        "rankings": {
            "week_w_published_fingerprint": summary["last_week_published_ranking"][
                "source_fingerprint"
            ],
            "season_closing_ranking_available": "closing_ranking" in summary,
            "next_season_week_1_fingerprint": None if boundary is None else boundary.fingerprint,
        },
        "no_completed_editions": summary["completed_edition_count"] == 0,
    }


def _leading_country(countries):
    """Most titles, then awarded points; one explicit criterion, not a composite score."""
    if not countries:
        return None
    best = max(countries, key=lambda c: (c["titles"], c["awarded_points"], c["country_code"]))
    return {k: best[k] for k in ("country_code", "titles", "finals", "awarded_points")}


def season_archive(state, world, *, closure=None):
    """Compact entry for every completed season, oldest first."""
    rows = []
    for index in sorted(set(completed_season_indices(state, closure))):
        summary = native_tour_season_summary(state, world, index, closure=closure)
        top = summary["players"][0] if summary["players"] else None
        rows.append({
            "season_index": index,
            "season_label": summary["season_label"],
            "boundary_command_id": summary["boundary_command_id"],
            "source_tour_fingerprint": summary["source_tour_fingerprint"],
            "rules": season_rule_basis(state, index),
            "overview": season_world_overview(state, world, index, summary),
            "leading_player": None if top is None else {
                "player_id": top["player_id"], "name": top["name"],
                "country_code": top["country_code"], "titles": top["titles"],
                "awarded_points": top["awarded_points"],
            },
            "leading_country": _leading_country(summary["countries"]),
        })
    return {
        "schema_version": ARCHIVE_SCHEMA,
        "run_id": state.run_id,
        "branch_id": state.branch_id,
        "source_tour_fingerprint": state.fingerprint,
        "seasons": rows,
    }


def _presence_rows(selected, other, key, fields):
    sel = {r[key]: r for r in selected}
    oth = {r[key]: r for r in other}
    rows = []
    for ident in sorted(set(sel) | set(oth)):
        a, b = sel.get(ident), oth.get(ident)
        row = {
            key: ident,
            "presence": "both" if a and b else "only_selected" if a else "only_comparison",
            "selected": None if a is None else {f: a[f] for f in fields},
            "comparison": None if b is None else {f: b[f] for f in fields},
        }
        # No delta unless both seasons represent the entity: absence is not zero.
        row["delta"] = (
            {f: a[f] - b[f] for f in fields} if a and b else None
        )
        rows.append(row)
    return rows


def season_comparison_detail(state, world, selected_index, other_index, *, closure=None):
    """Overview, rule comparability and presence-aware country/player comparison."""
    selected = native_tour_season_summary(state, world, selected_index, closure=closure)
    other = native_tour_season_summary(state, world, other_index, closure=closure)
    fields = ("titles", "finals", "awarded_points")
    return {
        "schema_version": COMPARISON_SCHEMA,
        "selected_season_index": selected_index,
        "comparison_season_index": other_index,
        "selected_overview": season_world_overview(state, world, selected_index, selected),
        "comparison_overview": season_world_overview(state, world, other_index, other),
        "comparability": season_comparability(state, selected_index, other_index),
        "countries": _presence_rows(selected["countries"], other["countries"], "country_code", fields),
        "players": _presence_rows(selected["players"], other["players"], "player_id", fields),
        "note": "Absence means not represented in that season's Editions, not zero.",
    }


def season_summary_extras(state, world, season_index, summary, compare_to, *, closure=None):
    """Additive keys of the season read: world overview and, with a comparison, detail."""
    extra = {"overview": season_world_overview(state, world, season_index, summary["selected"])}
    if compare_to is not None:
        extra["detail"] = season_comparison_detail(
            state, world, season_index, compare_to, closure=closure
        )
    return extra
