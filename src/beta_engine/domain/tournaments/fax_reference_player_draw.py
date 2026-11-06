"""Exact-source, real-player initial FAX Draw; no match execution or Q winners."""

from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from beta_engine.domain.rankings.official import FrozenInput
from beta_engine.domain.run_packages import canonical_hash
from beta_engine.domain.tournaments.draw_authority import (
    TournamentDrawAuthority,
    TournamentDrawAuthorityBuilder,
)
from beta_engine.domain.tournaments.draw_input_authority import (
    TournamentDrawInputAuthority,
)
from beta_engine.domain.tournaments.entry_field import TournamentEntryFieldCapacity
from beta_engine.domain.tournaments.fax_reference_bracket_topology import (
    build_fax_reference_bracket_topology,
)
from beta_engine.domain.tournaments.models import SeasonCalendarEvent


def fax_reference_entry_capacity(
    event: SeasonCalendarEvent,
) -> TournamentEntryFieldCapacity:
    """Keep the source admission cut, padding only the physical Main bracket.

    In particular Platinum Q24 must not admit 32 players just because its four
    six-player sections need eight physical positions apiece at the Draw stage.
    """
    topology = build_fax_reference_bracket_topology(event)
    return TournamentEntryFieldCapacity.for_main_entrant_count(
        main_entrant_count=topology.main.source_main_entrants,
        qualification_draw_size=event.qualification_draw_size,
        qualifier_spots=event.qualifier_spots,
        wild_card_slots=event.wild_cards,
    )


class FaxReferencePlayerDraw(FrozenInput):
    """Validated source + canonical initial input/Draw, safe to inspect/replay.

    This projection is not a Saved component or proof of Entry eligibility. Its
    authorities must be loaded through their normal authenticated stores.
    """

    schema_version: Literal["fax_reference_player_draw.v1"] = (
        "fax_reference_player_draw.v1"
    )
    source_binding_scope: Literal["current_copied_calendar_geometry"] = (
        "current_copied_calendar_geometry"
    )
    sporting_execution_ready: Literal[False] = False
    run_package_state_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    calendar_projection_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_event: SeasonCalendarEvent
    draw_input: TournamentDrawInputAuthority
    draw: TournamentDrawAuthority

    @model_validator(mode="after")
    def validate_source_draw(self) -> FaxReferencePlayerDraw:
        topology = build_fax_reference_bracket_topology(self.source_event)
        if self.draw_input.event_id != topology.source_event_id:
            raise ValueError("FAX Draw Input references another source Edition")
        if self.draw_input.capacity != fax_reference_entry_capacity(self.source_event):
            raise ValueError(
                "FAX Draw Input changes source entrant/WC/BYE/Q capacities"
            )
        if (
            len(self.draw_input.direct_main_player_ids)
            != topology.main.direct_main_slots
            or len(self.draw_input.wild_card_player_ids)
            != topology.main.wild_card_slots
            or len(self.draw_input.qualification_player_ids)
            != self.source_event.qualification_draw_size
        ):
            raise ValueError(
                "FAX initial Draw requires the complete real source-sized field"
            )
        if self.draw_input.schema_version not in {
            "tournament_draw_input_authority.v3",
            "tournament_draw_input_authority.v12",
        }:
            raise ValueError(
                "FAX initial Draw requires canonical pre-repair WC Draw Input"
            )
        expected_algorithm = (
            "padded_qualification_sections.v3"
            if self.draw_input.schema_version == "tournament_draw_input_authority.v12"
            else "idealized_seed_tiers.v2"
        )
        if self.draw.algorithm_version != expected_algorithm:
            raise ValueError(
                "FAX initial Draw requires the matching Master-aligned algorithm"
            )
        replay = TournamentDrawAuthorityBuilder.build(
            draw_input=self.draw_input,
            command_id=self.draw.generated_by_command_id,
            algorithm_version=self.draw.algorithm_version,
        )
        if self.draw != replay:
            raise ValueError("FAX Draw does not replay exactly from its frozen input")
        if self.draw.main.nodes != topology.main.nodes:
            raise ValueError("FAX Main Draw changes source topology")
        if len(self.draw.qualification_brackets) != len(
            topology.qualification_sections
        ):
            raise ValueError("FAX Qualification Draw changes source section count")
        for bracket, section in zip(
            self.draw.qualification_brackets,
            topology.qualification_sections,
            strict=True,
        ):
            if (
                bracket.section_id != section.section_id
                or bracket.nodes != section.nodes
                or len(bracket.bye_slot_indexes) != section.unplaced_byes
            ):
                raise ValueError(
                    "FAX Qualification Draw changes source section topology/BYEs"
                )
        return self

    @property
    def fingerprint(self) -> str:
        return canonical_hash(self.model_dump(mode="json"))
