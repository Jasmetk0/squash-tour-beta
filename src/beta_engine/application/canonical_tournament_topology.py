"""Bridge canonical Run-owned Draw authority into authoritative match topology.

The legacy MatchPackage remains a temporary execution/result payload, but its bracket
shape is no longer trusted when canonical Draw authority is available. Every legacy
match record must bind one-to-one to a canonical Draw node or the bridge fails closed.
"""

from __future__ import annotations

from pydantic import Field, model_validator

from beta_engine.application.season_match_service import (
    FrozenQualifierPromotion,
    SeasonEventMatchPackage,
    SeasonMatchRecord,
)
from beta_engine.domain.rankings.official import FrozenInput
from beta_engine.domain.simulation_slots import SimulationMatchEventPlan, fingerprint
from beta_engine.domain.tournaments.draw_authority import (
    TournamentDrawAuthority,
    TournamentDrawBracket,
    TournamentDrawNode,
)


class CanonicalTournamentTopologyProjection(FrozenInput):
    schema_version: str = "canonical_tournament_topology_projection.v1"
    event_id: str
    draw_authority_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    plans: tuple[SimulationMatchEventPlan, ...]
    terminal_group_id: str
    bye_match_ids: tuple[str, ...] = ()
    bye_winners: tuple[tuple[str, str], ...] = ()
    qualifier_promotions: tuple[FrozenQualifierPromotion, ...] = ()

    @model_validator(mode="after")
    def validate_projection(self):
        ids = tuple(plan.group_id for plan in self.plans)
        if len(ids) != len(set(ids)):
            raise ValueError("canonical topology projection contains duplicate group identity")
        if self.terminal_group_id not in ids:
            raise ValueError("canonical topology terminal is not executable")
        if set(self.bye_match_ids) & set(ids):
            raise ValueError("canonical BYE matches cannot also be executable groups")
        return self

    @property
    def fingerprint(self) -> str:
        return fingerprint(self.model_dump(mode="json"))


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
        raise ValueError("MatchPackage node count differs from canonical Draw authority")

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

    qualification_terminal_match_ids: dict[str, str] = {}
    for index, bracket in enumerate(draw.qualification_brackets, start=1):
        section_id = bracket.section_id or f"Q{index}"
        terminal = _terminal_node(bracket)
        qualification_terminal_match_ids[section_id] = record_by_node[
            terminal.node_id
        ].match_id

    auto_sources: dict[str, str] = {}
    bye_match_ids: list[str] = []
    bye_winners: list[tuple[str, str]] = []
    promotions: list[FrozenQualifierPromotion] = []
    plans: list[SimulationMatchEventPlan] = []

    brackets = [*draw.qualification_brackets, draw.main]

    for bracket in brackets:
        slots = {slot.slot_index: slot for slot in bracket.slots}
        nodes = {node.node_id: node for node in bracket.nodes}

        for node in sorted(
            bracket.nodes, key=lambda item: (item.round_number, item.round_sequence)
        ):
            record = record_by_node[node.node_id]
            raw_sources = (node.source_top, node.source_bottom)
            resolved = tuple(
                _resolve_source(
                    source,
                    slots=slots,
                    nodes=nodes,
                    record_by_node=record_by_node,
                    auto_sources=auto_sources,
                    qualification_terminal_match_ids=qualification_terminal_match_ids,
                )
                for source in raw_sources
            )

            bye_sides = tuple(index for index, value in enumerate(resolved) if value == "bye")
            if bye_sides:
                if len(bye_sides) != 1:
                    raise ValueError("canonical Draw contains an ambiguous BYE match")
                live_source = resolved[1 - bye_sides[0]]
                if live_source == "bye":
                    raise ValueError("canonical Draw contains a double BYE")
                auto_sources[node.node_id] = live_source
                bye_match_ids.append(record.match_id)
                if live_source.startswith("player:"):
                    winner = live_source.removeprefix("player:")
                    bye_winners.append((record.match_id, winner))
                    known = [p for p in (record.top_player_id, record.bottom_player_id) if p]
                    if known and known != [winner]:
                        raise ValueError(
                            "MatchPackage BYE participant conflicts with canonical Draw"
                        )
                else:
                    raise ValueError(
                        "canonical BYE currently requires a directly known player winner"
                    )
                continue

            participant_sources = tuple(_collapse_auto_source(value, auto_sources) for value in resolved)
            if any(value == "bye" for value in participant_sources):
                raise ValueError("canonical BYE source was not collapsed")

            _validate_known_record_participants(record, participant_sources)
            plans.append(
                SimulationMatchEventPlan(
                    group_id=record.match_id,
                    event_id=package.event_id,
                    match_id=record.match_id,
                    participant_sources=participant_sources,
                )
            )

            for side_index, canonical_source in enumerate(raw_sources):
                if (
                    bracket.draw_type == "main"
                    and canonical_source.startswith("slot:")
                ):
                    slot = slots[int(canonical_source.removeprefix("slot:"))]
                    if slot.entrant_kind == "qualifier_placeholder":
                        source_match_id = qualification_terminal_match_ids.get(
                            slot.placeholder_id
                        )
                        if source_match_id is None:
                            raise ValueError(
                                "Main Draw qualifier placeholder lacks linked Qualification authority"
                            )
                        promotions.append(
                            FrozenQualifierPromotion(
                                qualifier_index=int(
                                    slot.placeholder_id.removeprefix("Q")
                                ),
                                source_match_id=source_match_id,
                                target_match_id=record.match_id,
                                target_side="top" if side_index == 0 else "bottom",
                                target_slot_id=f"{package.event_id}:main:S{slot.slot_index}",
                            )
                        )

    executable_ids = {plan.match_id for plan in plans}
    expected_ids = {record.match_id for record in all_records} - set(bye_match_ids)
    if executable_ids != expected_ids:
        raise ValueError("canonical Draw/MatchPackage executable universes differ")

    terminal = _terminal_node(draw.main)
    terminal_match_id = record_by_node[terminal.node_id].match_id
    if terminal_match_id in bye_match_ids:
        raise ValueError("canonical Main Draw terminal cannot be a BYE auto-advance")

    _validate_legacy_feeder_hints(
        package=package,
        draw=draw,
        record_by_node=record_by_node,
        bye_match_ids=set(bye_match_ids),
    )

    return CanonicalTournamentTopologyProjection(
        event_id=package.event_id,
        draw_authority_fingerprint=draw.fingerprint,
        plans=tuple(sorted(plans, key=lambda plan: plan.group_id)),
        terminal_group_id=terminal_match_id,
        bye_match_ids=tuple(sorted(bye_match_ids)),
        bye_winners=tuple(sorted(bye_winners)),
        qualifier_promotions=tuple(
            sorted(
                promotions,
                key=lambda item: (
                    item.qualifier_index,
                    item.target_match_id,
                    item.target_side,
                ),
            )
        ),
    )


def _resolve_source(
    source: str,
    *,
    slots,
    nodes,
    record_by_node,
    auto_sources,
    qualification_terminal_match_ids,
) -> str:
    if source.startswith("slot:"):
        slot = slots[int(source.removeprefix("slot:"))]
        if slot.entrant_kind == "player":
            return f"player:{slot.player_id}"
        if slot.entrant_kind == "bye":
            return "bye"
        if slot.entrant_kind == "qualifier_placeholder":
            source_match_id = qualification_terminal_match_ids.get(slot.placeholder_id)
            if source_match_id is None:
                raise ValueError(
                    "canonical qualifier placeholder lacks linked Qualification terminal"
                )
            return f"winner:{source_match_id}"
        raise ValueError("canonical Draw slot entrant type is unsupported")
    if source.startswith("winner:"):
        node_id = source.removeprefix("winner:")
        if node_id not in nodes:
            raise ValueError("canonical Draw feeder node is missing")
        if node_id in auto_sources:
            return auto_sources[node_id]
        record = record_by_node.get(node_id)
        if record is None:
            raise ValueError("canonical Draw feeder has no MatchPackage binding")
        return f"winner:{record.match_id}"
    raise ValueError("canonical Draw source identity is unsupported")


def _collapse_auto_source(value: str, auto_sources: dict[str, str]) -> str:
    return value


def _terminal_node(bracket: TournamentDrawBracket) -> TournamentDrawNode:
    max_round = max(node.round_number for node in bracket.nodes)
    terminals = tuple(node for node in bracket.nodes if node.round_number == max_round)
    if len(terminals) != 1:
        raise ValueError("canonical bracket does not have exactly one terminal")
    return terminals[0]


def _validate_known_record_participants(
    record: SeasonMatchRecord,
    participant_sources: tuple[str, str],
) -> None:
    for side, source in zip(("top", "bottom"), participant_sources, strict=True):
        known = getattr(record, f"{side}_player_id")
        if source.startswith("player:") and known not in {
            None,
            source.removeprefix("player:"),
        }:
            raise ValueError(
                "MatchPackage direct participant conflicts with canonical Draw"
            )


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
        node_ids = {node.node_id for node in bracket.nodes}
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