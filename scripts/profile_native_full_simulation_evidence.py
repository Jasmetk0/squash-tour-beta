"""UUID-independent sporting comparison only; never used by runtime validation."""

import re

# These exact schema paths contain hashes whose ancestry includes a generated
# Save ID. Keep every other hash, value, list order and field presence. Actual
# signed logs/receipts are still verified by the unchanged production acceptance.
UUID_BOUND_DIGEST_PATHS = frozenset(
    [
        "tour.editions.*.tournament_fingerprint",
        "tour.transitions.*.ranking_fingerprint",
        "tour.transitions.*.public_event.ranking_fingerprint",
        "tour.transitions.*.sporting_advance_fingerprint",
        "tour.rankings.*.input_fingerprint",
        "tour.rankings.*.rows.*.counted_results.*.source_fingerprint",
        "tour.rankings.*.previous_fingerprint",
        "tour.checkpoint_fingerprint",
        "tournaments.*.prepared_awards.*.source_tournament_fingerprint",
        "tournaments.*.request_fingerprint",
        "tournaments.*.matches.*.log_anchor_hash",
        "tournaments.*.matches.*.effects.*.result_fingerprint",
        "tournaments.*.matches.*.result.stamina_log.transitions.*.transition_hash",
        "tournaments.*.matches.*.result.stamina_log.transitions.*.previous_transition_hash",
        "tournaments.*.matches.*.result.stamina_log.transitions.*.source_timeline_event_hash",
        "tournaments.*.matches.*.result.stamina_log.match_log_hash",
        "tournaments.*.matches.*.result.stamina_log.timeline_log_hash",
        "tournaments.*.matches.*.result.timeline_log.input_snapshot_hash",
        "tournaments.*.matches.*.result.timeline_log.match_log_hash",
        "tournaments.*.matches.*.result.timeline_log.events.*.event_hash",
        "tournaments.*.matches.*.result.timeline_log.events.*.previous_event_hash",
        "tournaments.*.matches.*.result.timeline_log.events.*.rally_event_hash",
        "tournaments.*.matches.*.result.rally_log.input_snapshot_hash",
        "tournaments.*.matches.*.result.rally_log.match_log_hash",
        "tournaments.*.matches.*.result.rally_log.events.*.event_hash",
        "tournaments.*.matches.*.result.rally_log.events.*.previous_event_hash",
        "tournaments.*.matches.*.request_fingerprint",
        "advances.*.source_checkpoint_fingerprint",
    ]
)


def normalized_sporting_state(state, revision_aliases):
    """Compare all sporting facts across separate executions with different UUIDs.

    Exclude duplicate command receipts/journal from this comparison only. Replace
    actual Saved IDs by their Run-local Branch/sequence aliases. Mask ONLY the
    listed UUID-derived digest paths; preserve configuration/source hashes and all
    score, rally, time, stamina, seed, player, development and ranking values.
    """
    state = dict(state)
    state.pop("journal", None)
    state["tour"] = {
        key: value for key, value in state["tour"].items() if key != "receipts"
    }

    def visit(value, path):
        if ".".join(path) in UUID_BOUND_DIGEST_PATHS and value is not None:
            if (
                not isinstance(value, str)
                or re.fullmatch("[0-9a-f]{64}", value) is None
            ):
                raise ValueError(
                    "Expected a versioned UUID-bound digest at " + ".".join(path)
                )
            return "<UUID-bound digest>"
        if isinstance(value, str):
            return revision_aliases.get(value, value)
        if isinstance(value, dict):
            return {key: visit(item, (*path, key)) for key, item in value.items()}
        if isinstance(value, list):
            return [visit(item, (*path, "*")) for item in value]
        return value

    return visit(state, ())
