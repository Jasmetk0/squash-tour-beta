"""Immutable structural bracket topology for the original FAX release fixture.

Bridge the *geometry*, not the authority: no seeded draw, Entry assignment,
Qualification winner, match simulation, points policy or implicit BYE outcome
is created. The existing canonical draw-node builder owns all feeder IDs.

Gold: 24 Main + 16 Qualification / 4 winners / 8 Main BYEs.
Platinum: 32 Main + 24 Qualification / 4 winners / four 6-person
sections expanded to capacity 8 (2 unassigned BYEs per section).
"""
from __future__ import annotations

from collections import Counter
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from beta_engine.domain.rankings.points import knockout_loss_point_stage
from beta_engine.domain.run_packages import canonical_hash
from beta_engine.domain.tournaments.draw_authority import (
    TournamentDrawNode,
    _build_nodes,
)
from beta_engine.domain.tournaments.models import SeasonCalendarEvent

SCHEMA = "fax_reference_bracket_topology.v1"


def bracket_capacity(entrants: int) -> int:
    """Real entrants -> minimal power-of-two bracket; never change entrant count."""
    if isinstance(entrants, bool) or not isinstance(entrants, int) or not 2 <= entrants <= 128:
        raise ValueError("Classic bracket requires 2..128 real entrants")
    return 1 << (entrants - 1).bit_length()


class FaxQualificationSectionGeometry(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    section_id: str = Field(pattern=r"^Q[1-9][0-9]*$")
    qualifier_placeholder_id: str = Field(pattern=r"^Q[1-9][0-9]*$")
    source_entrant_count: int = Field(ge=2)
    bracket_capacity: int = Field(ge=2)
    unplaced_byes: int = Field(ge=0)
    nodes: tuple[TournamentDrawNode, ...]

    @model_validator(mode="after")
    def validate_tree(self):
        if (
            self.section_id != self.qualifier_placeholder_id
            or self.bracket_capacity != bracket_capacity(self.source_entrant_count)
            or self.unplaced_byes != self.bracket_capacity - self.source_entrant_count
            or len(self.nodes) != self.bracket_capacity - 1
            or self.nodes[-1].round_number != self.bracket_capacity.bit_length() - 1
        ):
            raise ValueError("Qualification must preserve its exact unassigned BYE geometry")
        if len({node.node_id for node in self.nodes}) != len(self.nodes):
            raise ValueError("Duplicate Qualification match node identity")
        return self

    @property
    def actual_match_count_if_fully_played(self) -> int:
        # A single-elimination section reduces N real entrants to 1 winner.
        return self.source_entrant_count - 1


class FaxMainBracketGeometry(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    source_main_entrants: int = Field(ge=2)
    bracket_capacity: int = Field(ge=2)
    direct_main_slots: int = Field(ge=0)
    wild_card_slots: int = Field(ge=0)
    qualifier_placeholder_ids: tuple[str, ...]
    unplaced_byes: int = Field(ge=0)
    nodes: tuple[TournamentDrawNode, ...]

    @model_validator(mode="after")
    def validate_main(self):
        entrants = (
            self.direct_main_slots
            + self.wild_card_slots
            + len(self.qualifier_placeholder_ids)
        )
        if (
            entrants != self.source_main_entrants
            or self.bracket_capacity != bracket_capacity(entrants)
            or self.unplaced_byes != self.bracket_capacity - entrants
            or len(self.nodes) != self.bracket_capacity - 1
            or self.nodes[-1].round_number != self.bracket_capacity.bit_length() - 1
        ):
            raise ValueError("Main bracket must preserve every original place and BYE")
        if self.qualifier_placeholder_ids != tuple(
            f"Q{i}" for i in range(1, len(self.qualifier_placeholder_ids) + 1)
        ):
            raise ValueError("Qualifiers must be canonical pending Q1..Qn identities")
        if len({node.node_id for node in self.nodes}) != len(self.nodes):
            raise ValueError("Duplicate Main match node identity")
        return self

    @property
    def actual_match_count_if_fully_played(self) -> int:
        return self.source_main_entrants - 1


class FaxReferenceBracketTopology(BaseModel):
    """One source-bound *unassigned* structural graph, never a playable Run."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal["fax_reference_bracket_topology.v1"] = SCHEMA
    source_kind: Literal["fax_release_fixture_non_canonical"] = (
        "fax_release_fixture_non_canonical"
    )
    source_event_id: str = Field(min_length=1)
    source_template_id: str = Field(min_length=1)
    source_calendar_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_event_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    main: FaxMainBracketGeometry
    qualification_sections: tuple[FaxQualificationSectionGeometry, ...]
    sporting_results_known: Literal[False] = False

    @model_validator(mode="after")
    def validate_bracket_sources(self):
        links = self.main.qualifier_placeholder_ids
        if tuple(x.section_id for x in self.qualification_sections) != links:
            raise ValueError("Qualification bracket winners must bind exact Main Q links")
        if self.main.nodes != _build_nodes(self.source_event_id, "main", self.main.bracket_capacity):
            raise ValueError("Main feeder graph differs from its canonical source nodes")
        for ordinal, section in enumerate(self.qualification_sections):
            expected = _build_nodes(
                self.source_event_id, "qualification", section.bracket_capacity,
                section_id=section.section_id, section_ordinal=ordinal,
                section_count=len(self.qualification_sections),
            )
            if section.nodes != expected:
                raise ValueError("Qualification feeder graph differs from its canonical source nodes")
        all_nodes = (*self.main.nodes, *(
            node for section in self.qualification_sections for node in section.nodes
        ))
        if len({node.node_id for node in all_nodes}) != len(all_nodes):
            raise ValueError("Main and Qualification match identities overlap")
        return self

    @property
    def actual_match_count_if_fully_played(self) -> int:
        return (
            self.main.actual_match_count_if_fully_played
            + sum(x.actual_match_count_if_fully_played
                  for x in self.qualification_sections)
        )

    @property
    def ranked_point_stages(self) -> tuple[str, ...]:
        """Use physical rounds, including first-round awards after a BYE.

        Four independent Qualification sections do not play one aggregate draw.
        Readiness needs the same stages the canonical results and awards use.
        """
        main_final = self.main.nodes[-1].round_number
        stages = ["champion", *(
            knockout_loss_point_stage(
                draw_type="main", round_number=round_number, final_round=main_final,
            )
            for round_number in range(main_final, 0, -1)
        )]
        if self.qualification_sections:
            stages.append("qualification_winner")
        for section in self.qualification_sections:
            final = section.nodes[-1].round_number
            stages.extend(
                knockout_loss_point_stage(
                    draw_type="qualification", round_number=round_number, final_round=final,
                )
                for round_number in range(final, 0, -1)
            )
        return tuple(dict.fromkeys(stages))

    @property
    def fingerprint(self) -> str:
        return canonical_hash(self.model_dump(mode="json"))


def build_fax_reference_bracket_topology(
    event: SeasonCalendarEvent,
) -> FaxReferenceBracketTopology:
    """Use original FAX template numbers, not an invented or reduced draw.

    This is an immutable *structural* graph. The exact placement of BYEs,
    seeding/WC identities, active Entry decisions, Q winners and genuine
    MatchEngine games belong to later independently reviewed authorities.
    """
    if (
        event.tour_level != "WORLD_TOUR"
        or event.is_world_tour is not True
        or event.is_elite_tour is True
        or event.event_level_overrides.get("pre_alpha_release_fixture") is not True
    ):
        raise ValueError("A copied FAX World Tour release-fixture Edition is required")
    if (
        not event.calendar_fingerprint
        or len(event.calendar_fingerprint) != 64
    ):
        raise ValueError("Source Edition needs its exact versioned Calendar fingerprint")

    size = event.main_draw_size
    capacity = bracket_capacity(size)
    if event.byes != capacity - size:
        raise ValueError("FAX Main BYEs do not match its original 24/32 entrant geometry")
    if event.wild_cards < 0 or event.qualifier_spots < 1:
        raise ValueError("FAX fixture must retain nonnegative WC and actual Q spots")
    if event.qualification_draw_size < 2:
        raise ValueError("FAX Qualification source requires at least two real entrants")
    if event.qualification_draw_size % event.qualifier_spots:
        raise ValueError("Original Qualification entrants are not divisible into equal Q sections")
    entrants_per_section = event.qualification_draw_size // event.qualifier_spots
    q_capacity = bracket_capacity(entrants_per_section)
    if q_capacity > 128:
        raise ValueError("Qualification bracket exceeds the domain capacity")

    # No hypothetical player identity is allocated: the Main field is an
    # exact count of direct players, real Wild Cards and unresolved Q winners.
    direct = size - event.wild_cards - event.qualifier_spots
    if direct < 0:
        raise ValueError("FAX WC and Qualification places exceed real Main entrants")
    links = tuple(f"Q{i}" for i in range(1, event.qualifier_spots + 1))
    main = FaxMainBracketGeometry(
        source_main_entrants=size,
        bracket_capacity=capacity,
        direct_main_slots=direct,
        wild_card_slots=event.wild_cards,
        qualifier_placeholder_ids=links,
        unplaced_byes=event.byes,
        nodes=_build_nodes(event.event_id, "main", capacity),
    )
    sections = tuple(
        FaxQualificationSectionGeometry(
            section_id=section_id,
            qualifier_placeholder_id=section_id,
            source_entrant_count=entrants_per_section,
            bracket_capacity=q_capacity,
            unplaced_byes=q_capacity - entrants_per_section,
            nodes=_build_nodes(
                event.event_id, "qualification", q_capacity,
                section_id=section_id, section_ordinal=index,
                section_count=event.qualifier_spots,
            ),
        )
        for index, section_id in enumerate(links)
    )
    return FaxReferenceBracketTopology(
        source_event_id=event.event_id,
        source_template_id=event.template_id,
        source_calendar_fingerprint=event.calendar_fingerprint,
        source_event_fingerprint=canonical_hash(event.model_dump(mode="json")),
        main=main,
        qualification_sections=sections,
    )


def summarise_fax_reference_geometries(
    events: tuple[SeasonCalendarEvent, ...] | list[SeasonCalendarEvent],
) -> dict:
    """Exactly 80 source Editions; small deterministic engineering summary."""
    if len(events) != 80 or len({e.event_id for e in events}) != 80:
        raise ValueError("FAX summary requires 80 unique original source Editions")
    shapes = [build_fax_reference_bracket_topology(event) for event in events]
    sources = {shape.source_calendar_fingerprint for shape in shapes}
    if len(sources) != 1:
        raise ValueError("FAX Editions originate from different Calendar snapshots")
    totals = Counter()
    for shape in shapes:
        totals["main_entrants"] += shape.main.source_main_entrants
        totals["main_byes"] += shape.main.unplaced_byes
        totals["qualification_entrants"] += sum(
            section.source_entrant_count for section in shape.qualification_sections
        )
        totals["qualification_byes"] += sum(
            section.unplaced_byes for section in shape.qualification_sections
        )
        totals["qualifier_winner_placeholders"] += len(shape.qualification_sections)
        totals["potential_actual_matches"] += shape.actual_match_count_if_fully_played
    return {
        "schema_version": "fax_reference_bracket_geometry_summary.v1",
        "source_calendar_fingerprint": next(iter(sources)),
        "edition_count": len(shapes),
        "totals": dict(sorted(totals.items())),
        "editions": [
            {
                "event_id": shape.source_event_id,
                "source_event_fingerprint": shape.source_event_fingerprint,
                "topology_fingerprint": shape.fingerprint,
                "main_entrant_count": shape.main.source_main_entrants,
                "main_bracket_capacity": shape.main.bracket_capacity,
                "main_byes": shape.main.unplaced_byes,
                "qualification_section_count": len(shape.qualification_sections),
                "qualification_entrants_per_section":
                    shape.qualification_sections[0].source_entrant_count,
                "qualification_bracket_capacity_per_section":
                    shape.qualification_sections[0].bracket_capacity,
                "qualification_byes_per_section":
                    shape.qualification_sections[0].unplaced_byes,
                "potential_actual_matches": shape.actual_match_count_if_fully_played,
            } for shape in shapes
        ],
        "results_generated": 0,
        "sporting_execution_ready": False,
        "qualification_winners_known": False,
    }
