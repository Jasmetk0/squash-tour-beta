"""Legacy MatchPackage binding around the shared pure canonical node resolver."""

from __future__ import annotations

from beta_engine.application.season_match_service import (
    SeasonEventMatchPackage,
    SeasonMatchRecord,
)
from beta_engine.domain.tournaments.canonical_knockout_topology import (
    CanonicalTournamentTopologyProjection,
    _project_topology,
    _terminal_node,
    project_canonical_draw_nodes,
)
from beta_engine.domain.tournaments.draw_authority import TournamentDrawAuthority

__all__ = [
    "CanonicalTournamentTopologyProjection",
    "project_canonical_draw_nodes",
    "project_canonical_draw_to_match_topology",
]


def project_canonical_draw_to_match_topology(
    *,
    draw: TournamentDrawAuthority,
    package: SeasonEventMatchPackage,
) -> CanonicalTournamentTopologyProjection:
    if package.event_id != draw.event_id:
        raise ValueError("canonical Draw and MatchPackage event identities differ")
    if package.validation_errors:
        raise ValueError("MatchPackage contains validation errors")

    all_records = tuple(package.qualification_matches + package.main_draw_matches)
    if len({record.match_id for record in all_records}) != len(all_records):
        raise ValueError("MatchPackage contains duplicate match identity")

    records_by_shape = {}
    for record in all_records:
        key = (record.draw_type, record.round_number, record.bracket_position)
        if key in records_by_shape:
            raise ValueError("MatchPackage contains duplicate bracket node shape")
        records_by_shape[key] = record

    canonical_nodes = [
        ("qualification", node)
        for bracket in draw.qualification_brackets
        for node in bracket.nodes
    ]
    canonical_nodes.extend(("main", node) for node in draw.main.nodes)
    if len(canonical_nodes) != len(all_records):
        raise ValueError(
            "MatchPackage node count differs from canonical Draw authority"
        )

    record_by_node: dict[str, SeasonMatchRecord] = {}
    for draw_type, node in canonical_nodes:
        record = records_by_shape.get(
            (draw_type, node.round_number, node.round_sequence)
        )
        if record is None:
            raise ValueError(
                "MatchPackage cannot be bound one-to-one to canonical Draw nodes"
            )
        if record.event_id != package.event_id:
            raise ValueError("MatchPackage contains a foreign event match")
        record_by_node[node.node_id] = record

    projected = _project_topology(draw=draw, record_by_node=record_by_node)
    _validate_legacy_feeder_hints(
        package=package,
        draw=draw,
        record_by_node=record_by_node,
        bye_match_ids=set(projected.bye_match_ids),
    )
    return projected


def _validate_legacy_feeder_hints(
    *,
    package: SeasonEventMatchPackage,
    draw: TournamentDrawAuthority,
    record_by_node: dict[str, SeasonMatchRecord],
    bye_match_ids: set[str],
) -> None:
    expected_targets: dict[str, str | None] = {}
    brackets = [*draw.qualification_brackets, draw.main]
    for bracket in brackets:
        for node in bracket.nodes:
            target = next(
                (
                    candidate
                    for candidate in bracket.nodes
                    if f"winner:{node.node_id}"
                    in (candidate.source_top, candidate.source_bottom)
                ),
                None,
            )
            expected_targets[record_by_node[node.node_id].match_id] = (
                record_by_node[target.node_id].match_id if target else None
            )

    qualification_terminal_match_ids = {
        record_by_node[_terminal_node(bracket).node_id].match_id
        for bracket in draw.qualification_brackets
    }

    for record in package.qualification_matches + package.main_draw_matches:
        expected = expected_targets[record.match_id]
        if record.winner_to_match_id not in {None, expected}:
            raise ValueError(
                "MatchPackage feeder target conflicts with canonical Draw authority"
            )
        if (
            record.match_id in bye_match_ids
            and expected is None
            and record.match_id not in qualification_terminal_match_ids
        ):
            raise ValueError("terminal canonical match cannot be a BYE")
