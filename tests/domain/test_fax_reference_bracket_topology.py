"""Original FAX Gold/Platinum bracket geometry, not simulated events.

Every test reads the actual versioned 80-Edition source and the canonical
native Draw node model. No player, seed, result, points or Run is forged.
"""
from collections import Counter
from pathlib import Path

import pytest
from pydantic import ValidationError

from beta_engine.application.pre_alpha_fax_acceptance_calendar_source import (
    PreAlphaFaxAcceptanceCalendarSource,
)
from beta_engine.application.season_calendar_service import SeasonCalendarService
from beta_engine.application.season_category_points_service import SeasonCategoryPointsService
from beta_engine.application.tournament_templates_service import TournamentTemplatesConfigService
from beta_engine.domain.run_packages import canonical_hash
from beta_engine.domain.tournaments.draw_authority import (
    TournamentDrawNode, _build_nodes,
)
from beta_engine.domain.tournaments.fax_reference_bracket_topology import (
    FaxReferenceBracketTopology,
    bracket_capacity,
    build_fax_reference_bracket_topology,
    summarise_fax_reference_geometries,
)

pytestmark = pytest.mark.smoke


@pytest.fixture
def fax_calendar(tmp_path):
    template = TournamentTemplatesConfigService(
        config_path=Path("config/tournament_templates/mvp_templates.json"),
    )
    points = SeasonCategoryPointsService(
        template, registry_path=tmp_path / "missing-points-registry.json",
    )
    source = PreAlphaFaxAcceptanceCalendarSource(
        template_service=template,
        calendar_validation_service=SeasonCalendarService(
            template_service=template, category_points_service=points,
        ),
    )
    result = source.build_calendar("2000/2001")
    assert len(result.events) == 80
    assert not points.registry_path.exists(), "Preview must never create points data"
    return result


@pytest.mark.pr_critical
def test_gold_24_main_sixteen_qualification_is_canonical_geometry_without_hidden_results(fax_calendar):
    gold = next(e for e in fax_calendar.events if e.main_draw_size == 24)
    shape = build_fax_reference_bracket_topology(gold)
    assert shape.main.source_main_entrants == 24
    assert shape.main.bracket_capacity == 32
    assert shape.main.direct_main_slots == 18
    assert shape.main.wild_card_slots == 2
    assert shape.main.qualifier_placeholder_ids == ("Q1", "Q2", "Q3", "Q4")
    assert shape.main.unplaced_byes == 8
    assert len(shape.main.nodes) == 31
    assert len(shape.qualification_sections) == 4
    for i, section in enumerate(shape.qualification_sections):
        assert section.section_id == f"Q{i+1}"
        assert section.source_entrant_count == 4
        assert section.bracket_capacity == 4
        assert section.unplaced_byes == 0
        assert section.actual_match_count_if_fully_played == 3
        assert len(section.nodes) == 3
        assert section.nodes == _build_nodes(
            gold.event_id, "qualification", 4, section_id=f"Q{i+1}",
            section_ordinal=i, section_count=4,
        )
    assert shape.main.nodes == _build_nodes(gold.event_id, "main", 32)
    assert shape.actual_match_count_if_fully_played == 35
    assert shape.sporting_results_known is False
    assert shape.source_event_fingerprint == canonical_hash(gold.model_dump(mode="json"))
    assert shape.source_calendar_fingerprint == gold.calendar_fingerprint
    assert FaxReferenceBracketTopology.model_validate_json(shape.model_dump_json()) == shape


@pytest.mark.pr_critical
def test_platinum_32_main_and_q24_four_six_entrant_sections_are_padded_without_fictitious_players(fax_calendar):
    platinum = next(e for e in fax_calendar.events if e.main_draw_size == 32)
    shape = build_fax_reference_bracket_topology(platinum)
    assert shape.main.source_main_entrants == 32
    assert shape.main.bracket_capacity == 32
    assert shape.main.direct_main_slots == 26
    assert shape.main.wild_card_slots == 2
    assert shape.main.unplaced_byes == 0
    assert shape.main.qualifier_placeholder_ids == ("Q1", "Q2", "Q3", "Q4")
    assert len(shape.main.nodes) == 31
    assert len(shape.qualification_sections) == 4
    assert all(section.source_entrant_count == 6 for section in shape.qualification_sections)
    assert all(section.bracket_capacity == 8 for section in shape.qualification_sections)
    assert all(section.unplaced_byes == 2 for section in shape.qualification_sections)
    assert all(len(section.nodes) == 7 for section in shape.qualification_sections)
    assert all(section.actual_match_count_if_fully_played == 5 for section in shape.qualification_sections)
    assert shape.actual_match_count_if_fully_played == 51
    # The abstract complete bracket contains *seven* nodes, but only
    # five real matches per 6-person Q section after two unplaced BYEs.
    # No winner, seed or BYE placement is invented by the topology.
    assert not any(
        hasattr(node, "player_id") or hasattr(node, "winner_player_id")
        for section in shape.qualification_sections for node in section.nodes
    )
    assert shape.main.nodes == _build_nodes(platinum.event_id, "main", 32)
    assert FaxReferenceBracketTopology.model_validate_json(shape.model_dump_json()) == shape


@pytest.mark.pr_critical
def test_all_original_80_editions_keep_their_fax_geometry_and_provenance(fax_calendar):
    preview = summarise_fax_reference_geometries(fax_calendar.events)
    again = summarise_fax_reference_geometries(list(reversed(fax_calendar.events)))
    # Rows preserve caller Calendar order, while every per-source topology is stable.
    assert preview["editions"] == list(reversed(again["editions"]))
    assert preview["schema_version"] == "fax_reference_bracket_geometry_summary.v1"
    assert preview["source_calendar_fingerprint"] == fax_calendar.metadata.build_fingerprint
    assert preview["edition_count"] == 80
    assert preview["results_generated"] == 0
    assert preview["sporting_execution_ready"] is False
    assert preview["qualification_winners_known"] is False
    assert preview["totals"] == {
        "main_byes": 320,
        "main_entrants": 2240,
        "potential_actual_matches": 3440,
        "qualification_byes": 320,
        "qualification_entrants": 1600,
        "qualifier_winner_placeholders": 320,
    }
    assert Counter(item["potential_actual_matches"] for item in preview["editions"]) == {
        35: 40, 51: 40,
    }
    assert Counter(item["qualification_byes_per_section"] for item in preview["editions"]) == {
        0: 40, 2: 40,
    }
    assert len({x["topology_fingerprint"] for x in preview["editions"]}) == 80
    assert len({x["source_event_fingerprint"] for x in preview["editions"]}) == 80
    assert all(len(x["topology_fingerprint"]) == 64 for x in preview["editions"])


def test_canonical_nodes_have_no_hidden_seed_placeholders_and_are_stable_across_reads(fax_calendar):
    first = fax_calendar.events[1]
    shape = build_fax_reference_bracket_topology(first)
    assert shape == build_fax_reference_bracket_topology(first)
    assert shape.fingerprint == build_fax_reference_bracket_topology(first).fingerprint
    nodes = (*shape.main.nodes, *(
        node for section in shape.qualification_sections for node in section.nodes
    ))
    assert len(nodes) == 59
    assert len({node.node_id for node in nodes}) == 59
    assert all(isinstance(node, TournamentDrawNode) for node in nodes)
    assert shape.main.nodes[0].source_top == "slot:1"
    assert shape.main.nodes[0].source_bottom == "slot:2"
    assert shape.main.nodes[-1].round_number == 5
    assert all(n.source_top.startswith(("slot:", "winner:"))
               and n.source_bottom.startswith(("slot:", "winner:")) for n in nodes)


def test_adversarial_geometry_rejects_dropped_byes_foreign_sources_and_inconsistent_qualifier_counts(fax_calendar):
    gold = next(x for x in fax_calendar.events if x.main_draw_size == 24)
    with pytest.raises(ValueError, match="BYEs"):
        build_fax_reference_bracket_topology(
            gold.model_copy(update={"byes": 0})
        )
    with pytest.raises(ValueError, match="divisible"):
        build_fax_reference_bracket_topology(
            gold.model_copy(update={"qualification_draw_size": 17})
        )
    with pytest.raises(ValueError, match="exceed real Main"):
        build_fax_reference_bracket_topology(
            gold.model_copy(update={"wild_cards": 24})
        )
    with pytest.raises(ValueError, match="versioned Calendar"):
        build_fax_reference_bracket_topology(
            gold.model_copy(update={"calendar_fingerprint": None})
        )
    with pytest.raises(ValueError, match="release-fixture"):
        build_fax_reference_bracket_topology(
            gold.model_copy(update={"event_level_overrides": {}})
        )
    with pytest.raises(ValueError, match="release-fixture"):
        build_fax_reference_bracket_topology(
            gold.model_copy(update={"tour_level": "ELITE_TOUR"})
        )
    with pytest.raises(ValueError, match="80 unique"):
        summarise_fax_reference_geometries(fax_calendar.events[:-1])
    with pytest.raises(ValueError, match="80 unique"):
        summarise_fax_reference_geometries(
            [*fax_calendar.events[:-1], fax_calendar.events[0]]
        )


def test_immutable_models_reject_forged_winner_links_extra_fields_or_changed_bye_counts(fax_calendar):
    shape = build_fax_reference_bracket_topology(fax_calendar.events[1])
    with pytest.raises(ValidationError, match="extra_forbidden"):
        FaxReferenceBracketTopology.model_validate({
            **shape.model_dump(mode="json"),
            "played": True,
        })
    with pytest.raises(ValidationError, match="unassigned BYE"):
        shape.qualification_sections[0].model_copy(
            update={"unplaced_byes": 0}
        ).__class__.model_validate({
            **shape.qualification_sections[0].model_dump(mode="json"),
            "unplaced_byes": 0,
        })
    with pytest.raises(ValidationError, match="exact Main Q links"):
        FaxReferenceBracketTopology.model_validate({
            **shape.model_dump(mode="json"),
            "qualification_sections": shape.model_dump(mode="json")["qualification_sections"][:-1],
        })
    with pytest.raises(ValidationError, match="frozen_instance"):
        shape.main.unplaced_byes = 10


@pytest.mark.parametrize("actual,expected", [(2,2),(4,4),(6,8),(8,8),(24,32),(32,32),(64,64),(128,128)])
def test_capacity_preserves_real_entrants(actual,expected):
    assert bracket_capacity(actual) == expected


@pytest.mark.parametrize("bad", [0,1,-2,129,False,6.5,"24",None])
def test_capacity_rejects_invalid_inputs(bad):
    with pytest.raises(ValueError, match="2..128"):
        bracket_capacity(bad)
