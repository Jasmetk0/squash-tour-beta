"""Sourced Main/Q configuration; geometry is separate from native readiness."""
from datetime import date
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

from beta_engine.domain.tournaments.fax_reference_bracket_topology import build_knockout_bracket_parts
from beta_engine.domain.run_packages import canonical_hash


class ATPKnockoutProfile(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    schema_version: Literal["atp_squash_knockout_profile.v1"]
    occurrence_id: str = Field(min_length=1)
    category_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    source_start_date: str
    source_end_date: str
    source_urls: tuple[str, ...] = Field(min_length=1)
    source_pdf_sha256: dict[str, str]
    # The PDF's event header is the Main window, not evidence of Q dates.
    qualification_date_status: Literal["not_verified"]
    entrant_selection: Literal["admin_selected_no_automatic_race_or_age"]
    main_entrants: int = Field(ge=2, le=128)
    qualification_entrants: int = Field(ge=2, le=128)
    qualifier_spots: int = Field(ge=1)
    wild_cards: int = Field(ge=0)
    seeds_count: int = Field(ge=0)
    byes: int = Field(ge=0)
    match_best_of: Literal[5]
    ranked: Literal[True]
    main_points: dict[str, int]
    qualification_points: dict[str, int]

    def geometry(self):
        main, sections = build_knockout_bracket_parts(
            event_id=self.occurrence_id, main_entrants=self.main_entrants,
            qualification_entrants=self.qualification_entrants,
            qualifier_spots=self.qualifier_spots, wild_cards=self.wild_cards, byes=self.byes,
        )
        return {"schema_version": "atp_knockout_geometry.v1",
                "profile_fingerprint": canonical_hash(self.model_dump(mode="json")),
                "main": main.model_dump(mode="json"),
                "qualification_sections": [s.model_dump(mode="json") for s in sections],
                "actual_match_count": main.actual_match_count_if_fully_played + sum(s.actual_match_count_if_fully_played for s in sections),
                "sporting_execution_ready": False}

    @model_validator(mode="after")
    def validate_source(self):
        start, end = date.fromisoformat(self.source_start_date), date.fromisoformat(self.source_end_date)
        if end < start or not self.occurrence_id.startswith(f"atp_{start.year}_"):
            raise ValueError("Invalid ATP knockout dates or identity")
        if self.seeds_count > self.main_entrants:
            raise ValueError("Seeds exceed Main entrants")
        if set(self.source_urls) != set(self.source_pdf_sha256) or any(not u.startswith('https://') for u in self.source_urls):
            raise ValueError("Knockout sources require exact PDF evidence hashes")
        import re
        if any(re.fullmatch(r"[0-9a-f]{64}", h) is None for h in self.source_pdf_sha256.values()):
            raise ValueError("Invalid source PDF hash")
        geometry = self.geometry()
        rounds = geometry["main"]["bracket_capacity"].bit_length() - 1
        stages = ["champion"] + [{2:'finalist',4:'semifinal',8:'quarterfinal'}.get(2**i, f'round_of_{2**i}') for i in range(1, rounds+1)]
        if set(self.main_points) != set(stages) or any(v < 0 for v in self.main_points.values()):
            raise ValueError("Incomplete Main points")
        if any(self.main_points[a] < self.main_points[b] for a,b in zip(stages, stages[1:])):
            raise ValueError("Main points must descend")
        q_rounds = geometry['qualification_sections'][0]['bracket_capacity'].bit_length()-1
        q_stages = {"qualifier"} | {f"round_{i}_loss" for i in range(1,q_rounds+1)}
        if set(self.qualification_points) != q_stages or any(v < 0 for v in self.qualification_points.values()):
            raise ValueError("Incomplete Qualification points")
        q_values = [self.qualification_points['qualifier']] + [self.qualification_points[f'round_{i}_loss'] for i in range(q_rounds,0,-1)]
        if any(a < b for a,b in zip(q_values, q_values[1:])):
            raise ValueError("Qualification points must descend")
        return self
