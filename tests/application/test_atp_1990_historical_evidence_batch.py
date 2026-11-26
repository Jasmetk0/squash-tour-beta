"""Verify the first historical ATP evidence batch against canonical source data."""
from collections import Counter
import json

import pytest

from beta_engine.application.atp_earth_week_mapping import SOURCE_FILE, build_projection
from beta_engine.application.atp_earth_run_calendar_preview import preview_atp_earth_weeks_on_run
from beta_engine.domain.calendar.run_calendar import RunCalendar

pytestmark = pytest.mark.pr_critical
ROOT = SOURCE_FILE.parent


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def batch():
    return read(ROOT / "historical_evidence" / "1990_batch_01.json")


@pytest.fixture(scope="module")
def projection():
    return build_projection(read(SOURCE_FILE))


def test_complete_1990_queue_and_category_binding(batch, projection):
    rows = batch["occurrences"]
    source = read(SOURCE_FILE)["year_sources"]["1990"]
    year = next(row for row in read(ROOT / "seasons_1990_2026.json")["seasons"]
                if row["year"] == 1990)
    memberships = year["series_category_ids"]
    expected = sorted(source["events"], key=lambda e: (e["start_date"], e["series_id"]))
    assert len(rows) == len(expected) == len(memberships) == 75
    assert len({row["occurrence_id"] for row in rows}) == 75
    assert set(memberships) == {row["series_id"] for row in rows}
    assert Counter(row["category_id"] for row in rows) == {
        "atp_world_series": 53, "atp_championship_series": 12,
        "atp_championship_single_week": 9, "atp_finals": 1,
    }
    by_id = {row["source_identity"]: row for row in projection["mappings"]}
    for index, (row, event) in enumerate(zip(rows, expected), 1):
        assert row["queue_index"] == index
        assert row["series_id"] == event["series_id"]
        assert row["occurrence_id"] == "atp_1990_" + event["series_id"]
        assert row["category_id"] == memberships[event["series_id"]]
        assert row["original_start_date"] == event["start_date"]
        assert row["original_end_date"] == event["end_date"]
        assert row["calendar_source_url"] == event["source_url"]
        mapped = by_id[row["occurrence_id"]]
        assert row["mapped_year_weeks"] == mapped["mapped_year_weeks"]
        assert row["source_finish_iso_week"] == mapped["source_finish_iso_week"]
    assert batch["finals_alternate_window"] == source["finals_date_window_evidence"]
    assert batch["summary"]["all_dated_occurrences"] == projection["summary"]["source_event_count"]


@pytest.mark.parametrize("clock,field", [
    (RunCalendar(52, 1, 1990, 2), "run_positions_offset_1_start_1990"),
    (RunCalendar(52, 37, 1989, 2), "run_positions_offset_37_start_1989"),
])
def test_queue_positions_agree_with_real_run_calendar(batch, projection, clock, field):
    preview = preview_atp_earth_weeks_on_run(
        calendar=clock, mapping=projection, years=[1990])
    actual = {row["source_identity"]: row for row in preview["events"]}
    assert len(actual) == 75
    for row in batch["occurrences"]:
        positions = actual[row["occurrence_id"]]["run_weeks"]
        assert row[field] == [
            {k: pos[k] for k in ("season_index", "season_week")}
            for pos in positions
        ]


def test_first_january_evidence_is_not_playability(batch):
    rows = batch["occurrences"]
    assert [row["series_id"] for row in rows[:4]] == [
        "brisbane", "wellington_1992", "auckland", "sydney_2019",
    ]
    assert [row["historical_evidence"]["host_city"] for row in rows[:4]] == [
        "Adelaide", "Wellington", "Auckland", "Sydney",
    ]
    assert all(row["historical_evidence"]["main_entrants"] == 32
               for row in rows[:4])
    assert all(row["historical_evidence"]["qualification_start_date"] is None
               for row in rows[:4])
    assert all(row["profile_status"] == "not_in_published_sporting_source"
               and row["plan_status"] == "not_tested"
               and row["played_and_reopened_status"] == "not_tested"
               for row in rows)
    reviewed = batch["summary"]["individual_detail_reviewed"]
    assert reviewed == 75
    assert all("historical_evidence" in row for row in rows[:reviewed])
    assert all("historical_evidence" not in row for row in rows[reviewed:])
    assert batch["summary"]["published_sporting_profiles"] == 0
    assert batch["historical_points_evidence"]["rank_dependent_bonus_awards"] is True
    assert batch["first_next_unreviewed_occurrence"] == (
        rows[reviewed]["occurrence_id"] if reviewed < len(rows) else None
    )


def test_february_geometry_and_evidence_boundaries(batch):
    rows = {row["series_id"]: row["historical_evidence"]
            for row in batch["occurrences"] if "historical_evidence" in row}
    assert len(rows) == batch["summary"]["individual_detail_reviewed"]
    assert batch["summary"]["queued_for_individual_review"] == 75 - len(rows)
    assert rows["dallas"]["host_city"] == "San Francisco"
    assert rows["maceio_1992"]["host_city"] == "Guarujá"
    assert rows["sofia"]["host_city"] == "Milan"
    assert rows["rio"]["host_city"] == "Memphis"
    assert rows["maceio_1992"]["observed_lucky_losers"] == 1
    assert rows["maceio_1992"]["reported_main_qualifiers"] == 4
    for name, entrants, seeds, byes, q in (
        ("toronto_indoor_1990", 56, 16, 8, 28),
        ("philadelphia_1998", 48, 16, 16, 24),
        ("rio", 48, 16, 16, 24),
    ):
        evidence = rows[name]
        assert evidence["main_entrants"] == entrants
        assert evidence["main_bracket_slots"] == 64
        assert evidence["main_seeds"] == seeds
        assert evidence["main_byes"] == byes
        assert evidence["qualification_size_secondary"] == q
    for evidence in rows.values():
        if evidence.get("format") == "round_robin_then_knockout":
            assert evidence["main_bracket_slots"] is None
            assert evidence["main_byes"] is None
        else:
            assert evidence["main_entrants"] + evidence["main_byes"] == evidence["main_bracket_slots"]
        assert evidence["qualification_entrants"] is None
        assert evidence["qualification_start_date"] is None
        assert evidence["qualification_end_date"] is None
        assert evidence["point_table_status"] == "unresolved_exact_prize_band_and_full_historical_awards"
    assert sum(row.get("qualification_size_secondary") is not None
               for row in rows.values()) == batch["summary"]["reported_qualification_size_rows"]
    assert sum("candidate_point_row" in row for row in rows.values()) == batch["summary"]["candidate_point_row_links"]
    for evidence in rows.values():
        if "candidate_point_row" in evidence:
            candidate = evidence["candidate_point_row"]
            assert candidate["status"] == "secondary_candidate_not_verified_for_occurrence"
            assert candidate["iteration"] == 1990
            assert candidate["band_usd"] == evidence["reported_financial_commitment_usd"]
    points = batch["historical_points_evidence"]
    assert points["qualifying_loss_points"] is None
    assert points["base_points_150k_32_candidate"]["round_of_32"] == 1
    assert points["base_points_250k_32_candidate"]["champion"] == 103
    bands = points["bonus_bands_secondary"]
    assert bands[0] == {"from_rank": 1, "to_rank": 1, "points": 50}
    assert bands[-1]["to_rank"] == 200
    assert all(left["to_rank"] + 1 == right["from_rank"]
               for left, right in zip(bands, bands[1:]))


def test_reviewed_series_history_matches_canonical_1990_identity(batch):
    import unicodedata

    def normalized(value):
        return "".join(char for char in unicodedata.normalize("NFD", value)
                       if unicodedata.category(char) != "Mn").casefold()

    entities = {row["source_entity_id"]: row["payload"]
                for row in read(ROOT / "series.json")["entities"]}
    for row in batch["occurrences"]:
        if "historical_evidence" not in row:
            continue
        payload = entities[row["series_id"]]
        assert any(period["from"] <= 1990 <= period["to"]
                   and period["category_id"] == row["category_id"]
                   for period in payload["history_periods"])
        hosts = [entry for entry in payload.get("historical_host_change", [])
                 if entry["year"] == 1990]
        assert len(hosts) == 1
        assert normalized(hosts[0]["city"]) == normalized(row["historical_evidence"]["host_city"])
        assert hosts[0]["country_code"] == row["historical_evidence"]["country"]


def test_march_april_geometry_and_preserved_source_disagreements(batch):
    rows = {row["series_id"]: row for row in batch["occurrences"]}
    for name, entrants, seeds, byes, slots in (
        ("indian_wells", 56, 16, 8, 64),
        ("miami", 96, 32, 32, 128),
        ("barcelona", 56, 16, 8, 64),
        ("tokyo", 56, 16, 8, 64),
    ):
        evidence = rows[name]["historical_evidence"]
        assert (evidence["main_entrants"], evidence["main_seeds"],
                evidence["main_byes"], evidence["main_bracket_slots"]) == (
                    entrants, seeds, byes, slots
                )
    miami = rows["miami"]
    assert miami["original_start_date"] == "1990-03-16"
    assert miami["original_end_date"] == "1990-03-25"
    assert [week["year_week"] for week in miami["mapped_year_weeks"]] == [11, 12]
    assert miami["historical_evidence"]["alternate_annual_index_date"] == "1990-03-12"
    assert miami["historical_evidence"]["main_round_schedule_status"] == "not_verified_two_week_source_window"
    assert rows["barcelona"]["historical_evidence"]["main_draw_source_disagreement"]["annual_summary_entrants"] == 32
    assert rows["estoril"]["historical_evidence"]["venue_locality_secondary"] == "Oeiras"
    assert rows["rio_carpet_1990"]["historical_evidence"]["surface_enclosure_status"] == "conflicting_secondary_sources"
    for name, q, wc in (("marrakech", 4, 3), ("tokyo", 7, 5)):
        evidence = rows[name]["historical_evidence"]
        assert evidence["reported_main_qualifiers"] == q
        assert evidence["reported_main_wild_cards"] == wc
    assert rows["miami"]["historical_evidence"]["qualification_entrants"] is None


def test_full_year_census_is_distinct_from_individual_draw_review(batch):
    rows = batch["occurrences"]
    summary = batch["summary"]
    assert sum("annual_census_evidence" in row or "historical_evidence" in row
               for row in rows) == summary["annual_or_individual_historical_evidence_rows"] == 75
    assert sum("annual_census_evidence" in row and "historical_evidence" not in row
               for row in rows) == summary["annual_census_only_rows"]
    entities = {row["source_entity_id"]: row["payload"]
                for row in read(ROOT / "series.json")["entities"]}
    counts = Counter()
    for row in rows:
        e = row.get("historical_evidence")
        a = row.get("annual_census_evidence")
        n = e["main_entrants"] if e else a["reported_main_entrants"]
        counts[str(n)] += 1
        if a:
            assert a["status"] == "secondary_annual_summary_not_individual_draw_verification"
            host = next(h for h in entities[row["series_id"]]["historical_host_change"]
                        if h["year"] == 1990)
            assert a["canonical_1990_host_city"] == host["city"]
            assert a["canonical_1990_country_code"] == host["country_code"]
            if row["series_id"] != "atp_finals":
                slots = a["candidate_knockout_slots"]
                assert slots >= a["reported_main_entrants"]
                assert slots // 2 < a["reported_main_entrants"]
                assert slots - a["reported_main_entrants"] == a["candidate_byes_if_full_reported_field"]
            else:
                assert "candidate_knockout_slots" not in a
        if e is None:
            assert row["detail_status"] == "queued_for_individual_review"
    assert dict(counts) == summary["reported_field_distribution_all_year"]
    assert sum(row.get("historical_evidence", {}).get("main_seeds") is not None
               for row in rows) == summary["reported_seed_count_rows"]


def test_april_june_sources_and_frankfurt_finals(batch):
    rows = {row["series_id"]: row for row in batch["occurrences"]}
    assert rows["hong_kong"]["historical_evidence"]["host_city"] == "Nice"
    assert rows["hong_kong_salem_2002"]["historical_evidence"]["host_city"] == "Hong Kong"
    assert rows["hong_kong_salem_2002"]["historical_evidence"]["reported_main_wild_cards"] == 3
    assert rows["hong_kong_salem_2002"]["historical_evidence"]["observed_wild_cards_minimum"] == 1
    assert rows["hamburg"]["historical_evidence"]["alternate_event_end_date"] == "1990-05-14"
    assert rows["hamburg"]["original_end_date"] == "1990-05-13"
    for name, q, wc in (("hong_kong", 4, 3), ("monte_carlo", 6, 4),
                        ("umag", 4, 3), ("florence_1994", 4, 3),
                        ("s_hertogenbosch", 4, 2)):
        e = rows[name]["historical_evidence"]
        assert (e["reported_main_qualifiers"], e["reported_main_wild_cards"]) == (q, wc)
    for name in ("florence_1994", "s_hertogenbosch"):
        assert rows[name]["historical_evidence"]["observed_lucky_losers"] == 1
    a = rows["atp_finals"]["annual_census_evidence"]
    f = a["official_format_evidence"]
    assert (f["group_count"], f["group_size"], f["advancing_per_group"]) == (2, 4, 2)
    assert f["group_matches"] == 12 and f["total_matches"] == 15
    assert f["competition_start_date"] == "1990-11-13"
    assert rows["atp_finals"]["original_start_date"] == "1990-11-12"
    p = a["points_candidate"]
    assert p["group_win"] * 3 + p["champion_knockout_component"] == p["undefeated_champion"] == 400
    assert p["status"] == "secondary_not_verified_for_publication"
    assert p == batch["historical_points_evidence"]["finals_1990_candidate"]
    assert all(row["qualification_loss_points"] is None
               for row in batch["historical_points_evidence"]["world_series_64_candidate_rows"])


def test_1990_first_pass_completed_without_claiming_sporting_readiness(batch):
    summary = batch["summary"]
    assert summary["individual_detail_reviewed"] == 75
    assert summary["annual_census_only_rows"] == summary["queued_for_individual_review"] == 0
    assert batch["first_next_unreviewed_occurrence"] is None
    assert batch["next_open_evidence_occurrence"] == "atp_1990_brisbane"
    assert summary["published_sporting_profiles"] == summary["plan_verified"] == summary["played_and_reopened"] == 0
    rows = {row["series_id"]: row["historical_evidence"] for row in batch["occurrences"]}
    assert sum(e["reported_main_qualifiers"] is not None for e in rows.values()) == summary["reported_main_qualifier_count_rows"]
    assert sum(e["reported_main_wild_cards"] is not None for e in rows.values()) == summary["reported_main_wild_card_count_rows"]
    assert sum("main_draw_source_disagreement" in e for e in rows.values()) == summary["main_draw_disagreement_rows"]
    for series_id in ("bordeaux_1995", "cologne_1992_clay", "basel",
                      "brisbane_autumn_1992", "palermo", "athens_1994",
                      "toulouse_2000", "berlin_1991", "tel_aviv_1996",
                      "montpellier", "vienna", "sao_paulo_1993"):
        e = rows[series_id]
        assert e["main_draw_source_disagreement"]["annual_summary_entrants"] == 28
        assert e["main_entrants"] == 32
        assert e["main_byes"] == 0
    assert rows["wembley_1990"]["main_draw_source_disagreement"]["annual_summary_entrants"] == 56
    assert rows["wembley_1990"]["licence_continuity_status"] == "replacement_announcement_not_proof_of_legal_continuity"
    assert rows["wembley_1990"]["main_geometry_status"] == "candidate_field_not_certified_full_draw"
    for series_id, seeds in (("stuttgart", 16), ("atlanta", 8),
                            ("cincinnati", 8), ("winston_salem", 4),
                            ("stockholm", 16), ("paris_masters", 16)):
        e = rows[series_id]
        assert e["bye_seed_ranks"] == list(range(1, seeds + 1))
        assert len(e["bye_seed_ranks"]) == e["main_byes"]
    assert rows["stuttgart"]["reported_main_qualifiers"] == 5
    assert rows["atlanta"]["reported_main_qualifiers"] == 7
    assert rows["atlanta"]["observed_lucky_losers"] == 1
    assert rows["atp_finals"]["format"] == "round_robin_then_knockout"
    assert rows["atp_finals"]["group_format"]["total_matches"] == 15
    assert rows["atp_finals"]["main_bracket_slots"] is None
    assert rows["atp_finals"]["qualification_status"] == "not_a_standard_knockout_qualification_phase"
    assert all(e["remaining"] for e in rows.values())


def test_second_pass_crosscheck_and_corrected_schenectady_field(batch):
    audit = batch["second_pass_source_audit"]
    assert audit["status"] == "research_cross_check_only_not_profile_provenance"
    assert audit["matched_occurrences"] == audit["matching_source_start_dates"] == 75
    assert audit["main_field_matches_before_correction"] == 74
    assert audit["main_field_matches_after_event_specific_correction"] == 75
    assert audit["qual_file_tour_level_rows"] == 0
    assert audit["qual_file_rows"] == 2233
    assert audit["main_field_disagreements"] == [{
        "occurrence_id": "atp_1990_schenectady_1994",
        "previous_candidate": 32,
        "independent_reported_field": 28,
    }]
    rows = batch["occurrences"]
    reviewed = batch["summary"]["second_pass_review_attempted_rows"]
    assert reviewed >= 13
    assert all("second_pass_review" in row["historical_evidence"]
               for row in rows[:reviewed])
    assert batch["next_second_pass_review_occurrence"] == (
        rows[reviewed]["occurrence_id"] if reviewed < len(rows) else None
    )
    assert batch["summary"]["complete_verified_qualification_draw_rows"] == 0
    assert batch["summary"]["verified_qualification_date_rows"] == 0
    e = next(row["historical_evidence"] for row in rows
             if row["series_id"] == "schenectady_1994")
    assert (e["main_entrants"], e["main_bracket_slots"],
            e["main_seeds"], e["main_byes"]) == (28, 32, 8, 4)
    assert e["bye_seed_ranks"] == [1, 2, 3, 4]
    assert (e["reported_main_qualifiers"], e["reported_main_wild_cards"],
            e["observed_lucky_losers"]) == (4, 3, 1)
    assert e["main_draw_source_disagreement"]["annual_summary_entrants"] == 32


def test_main_entry_labels_are_not_qualification_draws(batch):
    rows = {row["series_id"]: row["historical_evidence"]
            for row in batch["occurrences"]}
    for name in ("brisbane", "wellington_1992", "auckland", "sydney_2019",
                 "sofia", "brussels_championship_1992",
                 "stuttgart_indoor_feb_1995", "rotterdam", "schenectady_1994"):
        e = rows[name]
        labels = e["main_entry_label_evidence"]
        assert labels["status"] == "observed_labels_in_secondary_main_draw_not_guaranteed_policy"
        assert labels["observed_qualifiers"] == e["reported_main_qualifiers"] == 4
        assert labels["observed_wild_cards"] == e["reported_main_wild_cards"] == 3
        assert e["qualification_entrants"] is None
        assert e["qualification_start_date"] is None
    sydney = rows["sydney_2019"]["main_entry_label_evidence"]
    assert sydney["observed_seeded_wild_cards"] == 1
    assert sydney["observed_special_exempts"] == 1
    assert (sydney["observed_qualifiers"] + sydney["observed_wild_cards"]
            + sydney["observed_special_exempts"] + sydney["unmarked_entrants"]) == 32
    assert rows["sofia"]["observed_seeded_wild_card"] is True


def test_point_row_comparison_never_rounds_or_certifies_historical_awards(batch):
    method = batch["historical_points_evidence"]["candidate_comparison_method"]
    counts = Counter()
    for row in batch["occurrences"]:
        e = row["historical_evidence"]
        c = e["point_candidate_comparison"]
        counts[c["status"]] += 1
        assert c["source_rule_certified"] is False
        assert c["rule_iteration"] == 1990
        assert c["reported_financial_commitment_usd"] == e["reported_financial_commitment_usd"]
        assert c["working_bracket_positions"] == e["main_bracket_slots"]
        if row["category_id"] == "atp_finals":
            assert c["status"] == "finals_separate_group_points_candidate"
            assert c["source_tier_candidate"] is None
        elif c["reported_financial_commitment_usd"] is None:
            assert c["status"] == "missing_reported_financial_commitment"
        else:
            world = row["category_id"] == "atp_world_series"
            slots = c["working_bracket_positions"]
            expected_tier = "WORLD SERIES" if world else "CHAMP SERIES"
            assert c["source_tier_candidate"] == expected_tier
            bands = method["world_series_reported_band_labels_usd"] if world else (
                method["champ_series_128_reported_band_labels_usd"] if slots == 128
                else method["champ_series_reported_band_labels_usd"])
            sizes = method["world_series_md_labels"] if world else method["champ_series_md_labels"]
            expected = ("no_exact_bracket_size_row" if slots not in sizes else
                        "exact_reported_band_and_bracket_size_candidate"
                        if c["reported_financial_commitment_usd"] in bands
                        else "no_exact_financial_band_row")
            assert c["status"] == expected
    assert dict(counts) == batch["summary"]["point_candidate_comparison_counts"]
    assert sum(counts.values()) == 75
    assert batch["summary"]["published_sporting_profiles"] == 0


def test_second_pass_spring_entry_labels_and_phase_boundaries(batch):
    rows = {row["series_id"]: row for row in batch["occurrences"]}
    expected = {
        "indian_wells": (7, 5),
        "miami": (12, 2),
        "estoril": (4, 2),
        "orlando_1991": (4, 3),
        "rio_carpet_1990": (4, 3),
        "barcelona": (7, 5),
        "seoul_1996": (4, 3),
        "munich": (4, 3),
    }
    for series_id, (q, wc) in expected.items():
        e = rows[series_id]["historical_evidence"]
        labels = e["main_entry_label_evidence"]
        assert labels["observed_qualifiers"] == e["reported_main_qualifiers"] == q
        assert labels["observed_wild_cards"] == e["reported_main_wild_cards"] == wc
        assert labels["source_url"] in e["source_urls"]
        assert labels["status"] == "observed_labels_in_secondary_main_draw_not_guaranteed_policy"
        assert q + wc <= e["main_entrants"]
        assert e["qualification_entrants"] is None
        assert e["qualification_start_date"] is None
        assert e["qualification_end_date"] is None
    iw = rows["indian_wells"]["historical_evidence"]
    assert iw["observed_lucky_loser_in_bye_position"] is True
    assert iw["observed_lucky_losers"] == 1
    assert iw["observed_seeded_wild_card"] is True
    assert iw["contemporary_main_opening_date_evidence"]["date"] == rows["indian_wells"]["original_start_date"]
    miami = rows["miami"]["historical_evidence"]
    assert miami["bye_seed_ranks"] == list(range(1, 33))
    assert miami["itf_event_window_evidence"]["start_date"] == rows["miami"]["original_start_date"]
    assert miami["itf_event_window_evidence"]["end_date"] == rows["miami"]["original_end_date"]
    barcelona = rows["barcelona"]["historical_evidence"]
    window = barcelona["organiser_event_window_evidence"]
    assert window["start_date"] == "1990-04-07"
    assert rows["barcelona"]["original_start_date"] == "1990-04-09"
    assert window["end_date"] == rows["barcelona"]["original_end_date"]
    assert window["missing_seed_number"] == 8
    assert window["listed_seed_numbers"] == [1, 2, 3, 4, 5, 6, 7, 9, 10, 11, 12, 13, 14, 15, 16]
    assert barcelona["bye_seed_ranks"] == list(range(1, 9))
    assert barcelona["qualification_start_date"] is None
    assert batch["summary"]["second_pass_review_attempted_rows"] >= 27
    assert all("source_access" in row["historical_evidence"]["second_pass_review"]
               for row in batch["occurrences"][13:27])


def test_historical_v2_names_and_statuses_separate_geometry_from_entry_policy(batch):
    assert batch["schema_version"] == "atp_1990_historical_evidence_batch.v2"
    rows = batch["occurrences"]
    summary = batch["summary"]
    assert summary["calendar_verified_rows"] == sum(
        r["calendar_status"] == "canonical_archive_membership_and_date_reconciled"
        for r in rows) == 75
    assert summary["main_entrant_crosschecked_rows"] == 75
    assert summary["full_sporting_format_verified_rows"] == 0
    assert summary["published_sporting_profiles"] == summary["plan_verified"] == summary["played_and_reopened"] == 0
    for row in rows:
        e = row["historical_evidence"]
        assert not {"main_draw_capacity", "qualifier_spots", "wild_cards"} & e.keys()
        assert e["entry_policy"] == {
            "reserved_main_qualifier_spots": None,
            "reserved_main_wild_cards": None,
            "lucky_loser_replacement_rule": None,
        }
    miami = next(r["historical_evidence"] for r in rows if r["series_id"] == "miami")
    assert (miami["main_entrants"], miami["main_bracket_slots"], miami["main_byes"]) == (96, 128, 32)
    assert miami["reported_main_qualifiers"] == 12
    assert miami["entry_policy"]["reserved_main_qualifier_spots"] is None


def test_san_francisco_candidate_does_not_invent_q_or_ranking_provenance(batch):
    r = next(r for r in batch["occurrences"] if r["series_id"] == "dallas")
    e = r["historical_evidence"]
    c = e["import_candidate_evidence"]
    assert r["run_positions_offset_1_start_1990"] == [{"season_index": 0, "season_week": 6}]
    assert (e["main_entrants"], e["main_bracket_slots"], e["main_byes"], e["main_seeds"]) == (32, 32, 0, 8)
    assert (e["reported_main_qualifiers"], e["reported_main_wild_cards"], e["qualification_size_secondary"]) == (4, 3, 32)
    assert c["financial_evidence"][0]["reported_prize_money_usd"] == 225000
    assert c["financial_evidence"][1]["reported_purse_usd"] == 250000
    for key in ("qualification_actual_entrants", "qualification_feeder_sections",
                "qualification_reserved_advancers", "qualification_start_date",
                "qualification_end_date", "primary_point_table", "pdf_hashes"):
        assert c[key] is None
    assert c["atp_rule_evidence"]["secondary_candidate_qualifier_addition"] == 6
    assert c["atp_rule_evidence"]["qualification_loss_awards"] is None
    assert c["atp_rule_evidence"]["exact_occurrence_class_verified"] is False
    assert c["squash_adaptation"]["status"] == "requires_work_and_product_approval"


def test_historical_handoff_reproduces_current_profile_contract_blockers(batch):
    # Use a real existing, valid modern profile as a control. These deliberately
    # invalid patches are contract probes, not fabricated historical profiles.
    from beta_engine.application.atp_sporting_package_adapter import build_atp_sporting_package, parse_sporting_profile
    from beta_engine.domain.tournaments.atp_knockout_profile import ATPKnockoutProfile

    entity = next(e for e in build_atp_sporting_package().entities
                  if e.source_entity_id == "atp_2025_dallas")
    payload = parse_sporting_profile(entity.payload).model_dump(mode="json")
    historical = next(r["historical_evidence"]["import_candidate_evidence"]
                      for r in batch["occurrences"] if r["series_id"] == "dallas")
    handoff = historical["work_handoff"]
    html_url = historical["financial_evidence"][1]["source_url"]
    with pytest.raises(ValueError, match=handoff["provenance_error"]):
        ATPKnockoutProfile.model_validate_json(json.dumps({
            **payload, "source_urls": [html_url], "source_pdf_sha256": {},
        }))
    with pytest.raises(ValueError, match=handoff["ranking_error"]):
        ATPKnockoutProfile.model_validate_json(json.dumps({
            **payload, "rank_dependent_bonus_awards": True,
        }))
    with pytest.raises(ValueError, match=handoff["qualification_points_error"]):
        ATPKnockoutProfile.model_validate_json(json.dumps({
            **payload, "qualification_points": {"qualifier": 6},
        }))


def test_second_pass_may_evidence_is_not_a_complete_qualification_draw(batch):
    rows = batch["occurrences"]
    assert [r["series_id"] for r in rows[27:32]] == [
        "singapore_march_1992", "birmingham_1994", "hamburg", "rome", "umag"]
    by_id = {r["series_id"]: r["historical_evidence"] for r in rows}
    sg = by_id["singapore_march_1992"]
    assert sg["main_seeds"] == 8
    assert sg["itf_event_window_evidence"]["prize_money_usd"] == 225000
    assert sg["contemporary_main_opening_date_evidence"]["date"] == "1990-04-30"
    for name in ("birmingham_1994", "umag"):
        e = by_id[name]
        assert (e["reported_main_qualifiers"], e["reported_main_wild_cards"]) == (4, 3)
    assert by_id["birmingham_1994"]["observed_seeded_wild_card"] is True
    assert by_id["hamburg"]["nominal_bye_seed_ranks"] == list(range(1, 9))
    assert by_id["rome"]["main_entry_label_partial_evidence"]["observed_special_exempt_present"]
    for r in rows[27:32]:
        e = r["historical_evidence"]
        assert e["second_pass_review"]["qualification_draw_status"] == "not_obtained"
        assert e["qualification_entrants"] is e["qualification_start_date"] is e["qualification_end_date"] is None
    assert batch["summary"]["second_pass_review_attempted_rows"] >= 32


def test_second_pass_june_seed_and_entry_labels_remain_observations(batch):
    rows = batch["occurrences"]
    assert [r["series_id"] for r in rows[32:35]] == [
        "bologna_1998", "florence_1994", "queens_club"]
    b, f, q = [r["historical_evidence"] for r in rows[32:35]]
    assert b["main_seeds"] == 8
    assert (b["reported_main_qualifiers"], b["reported_main_wild_cards"]) == (4, 3)
    assert f["main_entry_label_evidence"]["observed_seeded_wild_card_ranks"] == [3, 6, 7]
    assert f["main_entry_label_evidence"]["observed_lucky_losers"] == 1
    assert (q["main_entrants"], q["main_bracket_slots"], q["main_byes"], q["main_seeds"]) == (56, 64, 8, 16)
    assert q["bye_seed_ranks"] == list(range(1, 9))
    assert (q["reported_main_qualifiers"], q["reported_main_wild_cards"]) == (7, 4)
    for e in (b, f, q):
        assert e["second_pass_review"]["qualification_draw_status"] == "not_obtained"
        assert e["qualification_entrants"] is e["qualification_start_date"] is e["qualification_end_date"] is None
        assert e["entry_policy"]["reserved_main_qualifier_spots"] is None
    assert batch["summary"]["second_pass_review_attempted_rows"] >= 35


def test_second_pass_rosmalen_through_newport_source_boundaries(batch):
    rows = batch["occurrences"]
    reviewed = rows[35:41]
    assert [r["series_id"] for r in reviewed] == [
        "s_hertogenbosch", "eastbourne", "poertschach_2008", "bastad",
        "gstaad", "newport"]
    r, m, g, b, s, n = [r["historical_evidence"] for r in reviewed]
    assert (r["reported_main_qualifiers"], r["reported_main_wild_cards"], r["observed_lucky_losers"]) == (4, 2, 1)
    assert (m["reported_main_qualifiers"], m["reported_main_wild_cards"], m["observed_special_exempts"]) == (4, 3, 1)
    assert m["main_entry_label_evidence"]["observed_seeded_wild_card_ranks"] == [2]
    assert g["itf_event_window_evidence"]["surface"] == "outdoor clay"
    assert g["itf_event_window_evidence"]["prize_money_usd"] == 225000
    assert b["main_entry_label_evidence"]["observed_seed_ranks"] == [1, 2, 3, 4, 6, 7, 8]
    assert s["itf_event_window_evidence"]["prize_money_usd"] == 275000
    assert s["reported_financial_commitment_usd"] == 300000
    assert s["contemporary_financial_evidence"]["reported_event_amount_usd"] == 305000
    assert s["point_candidate_comparison"]["status"] == "no_exact_financial_band_row"
    assert (n["reported_main_qualifiers"], n["reported_main_wild_cards"]) == (4, 1)
    assert n["contemporary_financial_evidence"]["reported_event_amount_usd"] == 150000
    for row in reviewed:
        e = row["historical_evidence"]
        assert e["second_pass_review"]["qualification_draw_status"] == "not_obtained"
        assert e["qualification_entrants"] is e["qualification_start_date"] is e["qualification_end_date"] is None
        assert e["entry_policy"]["reserved_main_qualifier_spots"] is None
    assert batch["summary"]["second_pass_review_attempted_rows"] >= 41


def test_second_pass_stuttgart_through_los_angeles_preserves_source_scope(batch):
    reviewed = batch["occurrences"][41:47]
    assert [r["series_id"] for r in reviewed] == [
        "stuttgart", "washington", "belgrade_2012", "canadian_open",
        "kitzbuhel", "los_cabos"]
    s, w, h, c, k, la = [r["historical_evidence"] for r in reviewed]
    for e, q, wc in ((s, 5, 3), (w, 7, 4), (h, 4, 2), (c, 7, 5), (la, 4, 3)):
        assert (e["reported_main_qualifiers"], e["reported_main_wild_cards"]) == (q, wc)
        assert e["main_entry_label_evidence"]["status"] == "observed_labels_in_secondary_main_draw_not_guaranteed_policy"
        assert e["main_entry_label_evidence"]["source_url"] in e["source_urls"]
    assert w["historical_name"] == "Sovran Bank Classic"
    assert w["reported_prize_money"] == 420000
    assert w["reported_financial_commitment_usd"] == 450000
    assert w["contemporary_financial_evidence"]["reported_purse_usd"] == 550000
    assert w["point_candidate_comparison"]["status"] == "no_exact_financial_band_row"
    assert w["bye_seed_ranks"] == c["bye_seed_ranks"] == list(range(1, 9))
    assert sum(c["main_entry_label_evidence"]["qualifier_counts_by_section"]) == 7
    assert sum(c["main_entry_label_evidence"]["wild_card_counts_by_section"]) == 5
    assert k["secondary_main_match_count_evidence"]["reported_match_count"] == k["main_entrants"] - 1
    assert k["main_seeds"] == 16
    assert la["contemporary_main_opening_date_evidence"]["date"] == "1990-07-30"
    for row in reviewed:
        e = row["historical_evidence"]
        assert e["second_pass_review"]["qualification_draw_status"] == "not_obtained"
        assert e["qualification_entrants"] is e["qualification_start_date"] is e["qualification_end_date"] is None
    assert batch["summary"]["second_pass_review_attempted_rows"] >= 47


def test_august_second_pass_distinguishes_advertised_and_actual_qualification(batch):
    reviewed = batch["occurrences"][47:55]
    assert [r["series_id"] for r in reviewed] == [
        "san_remo_1990", "cincinnati", "prague_1999", "atlanta",
        "new_haven_1998", "san_marino_2000", "schenectady_1994", "winston_salem"]
    san, cin, pr, ind, nh, sm, sc, li = [r["historical_evidence"] for r in reviewed]
    for e, q, wc in ((san, 4, 3), (cin, 7, 5), (ind, 7, 5), (nh, 7, 6), (sc, 4, 3), (li, 4, 3)):
        assert (e["reported_main_qualifiers"], e["reported_main_wild_cards"]) == (q, wc)
    assert cin["main_entry_label_evidence"]["observed_seeded_wild_card_ranks"] == [3]
    assert ind["contemporary_entry_allocation_evidence"]["reported_wild_cards_granted"] == 5
    assert ind["entry_policy"]["reserved_main_wild_cards"] is None
    assert pr["secondary_main_match_count_evidence"]["reported_match_count"] == 31
    window = nh["advertised_qualification_window"]
    assert window["status"] == "historical_poster_described_by_auctioneer_not_actual_play"
    assert (window["start_date"], window["end_date"]) == ("1990-08-11", "1990-08-12")
    from datetime import date
    assert date.fromisoformat(window["start_date"]).isocalendar().week == window["calendar_year_week"] == 32
    assert date.fromisoformat(window["advertised_main_start_date"]).isocalendar().week == window["main_calendar_year_week"] == 33
    assert reviewed[4]["run_positions_offset_1_start_1990"] == [{"season_index": 0, "season_week": 33}]
    assert nh["second_pass_review"]["qualification_dates_status"] == (
        "advertised_window_with_contemporary_partial_play_corroboration_actual_dates_not_verified")
    assert batch["summary"]["advertised_qualification_window_rows"] == sum(
        "advertised_qualification_window" in r["historical_evidence"] for r in batch["occurrences"])
    for row in reviewed:
        e = row["historical_evidence"]
        assert e["qualification_entrants"] is e["qualification_start_date"] is e["qualification_end_date"] is None
    assert batch["summary"]["second_pass_review_attempted_rows"] >= 55


def test_second_pass_bordeaux_through_toulouse_keeps_observed_labels_separate(batch):
    reviewed = batch["occurrences"][55:63]
    assert [r["series_id"] for r in reviewed] == [
        "bordeaux_1995", "cologne_1992_clay", "basel", "brisbane_autumn_1992",
        "palermo", "athens_1994", "sydney_indoor_1994", "toulouse_2000"]
    b, g, bs, br, p, a, s, t = [r["historical_evidence"] for r in reviewed]
    for e, q, wc in ((b, 4, 3), (g, 4, 3), (bs, 4, 3), (br, 4, 3), (p, 4, 1), (a, 3, 3), (s, 6, 4)):
        assert (e["reported_main_qualifiers"], e["reported_main_wild_cards"]) == (q, wc)
        assert e["main_entry_label_evidence"]["status"] == "observed_labels_in_secondary_main_draw_not_guaranteed_policy"
    assert g["main_entry_label_evidence"]["observed_seeded_wild_card_ranks"] == [1]
    assert a["observed_lucky_losers"] == 1
    assert (s["main_entrants"], s["main_bracket_slots"], s["main_byes"], s["main_seeds"]) == (48, 64, 16, 16)
    assert s["bye_seed_ranks"] == list(range(1, 17))
    assert t["reported_main_qualifiers"] is t["reported_main_wild_cards"] is None
    for row in reviewed:
        e = row["historical_evidence"]
        assert e["qualification_entrants"] is e["qualification_start_date"] is e["qualification_end_date"] is None
        assert e["second_pass_review"]["qualification_draw_status"] == "not_obtained"
    assert batch["summary"]["second_pass_review_attempted_rows"] >= 63


def test_second_pass_berlin_through_sao_paulo_no_inferred_entry_policy(batch):
    reviewed = batch["occurrences"][63:69]
    assert [r["series_id"] for r in reviewed] == [
        "berlin_1991", "tel_aviv_1996", "tokyo_indoor_1995",
        "montpellier", "vienna", "sao_paulo_1993"]
    b, ta, tok, l, v, sp = [r["historical_evidence"] for r in reviewed]
    assert b["itf_event_window_evidence"]["prize_money_usd"] == 260000
    assert b["reported_financial_commitment_usd"] is None
    for e, q, wc in ((ta, 4, 3), (tok, 6, 4), (l, 4, 3), (v, 4, 3)):
        assert (e["reported_main_qualifiers"], e["reported_main_wild_cards"]) == (q, wc)
    assert ta["observed_lucky_losers"] == l["observed_lucky_losers"] == 1
    assert (tok["main_entrants"], tok["main_bracket_slots"], tok["main_byes"], tok["main_seeds"]) == (48, 64, 16, 16)
    assert tok["bye_seed_ranks"] == list(range(1, 17))
    assert v["main_entry_label_evidence"]["observed_seeded_wild_card_ranks"] == [5]
    assert sp["main_entry_label_partial_evidence"]["observed_lucky_loser_seed_rank"] == 7
    assert sp["reported_main_qualifiers"] is sp["reported_main_wild_cards"] is None
    for row in reviewed:
        e = row["historical_evidence"]
        assert e["qualification_entrants"] is e["qualification_start_date"] is e["qualification_end_date"] is None
        assert e["entry_policy"]["reserved_main_qualifier_spots"] is None
    assert batch["summary"]["second_pass_review_attempted_rows"] >= 69


def test_second_pass_final_six_preserves_wembley_conflict_and_finals_group_rules(batch):
    reviewed = batch["occurrences"][69:75]
    assert [r["series_id"] for r in reviewed] == [
        "stockholm", "paris_masters", "itaparica_1990", "moscow",
        "wembley_1990", "atp_finals"]
    s, p, i, m, w, a = [r["historical_evidence"] for r in reviewed]
    for e, q, wc in ((s, 6, 4), (p, 6, 4), (i, 4, 2), (m, 4, 3), (w, 4, 3)):
        assert (e["reported_main_qualifiers"], e["reported_main_wild_cards"]) == (q, wc)
        assert e["entry_policy"]["reserved_main_qualifier_spots"] is None
        assert e["second_pass_review"]["qualification_draw_status"] == "not_obtained"
    assert s["observed_lucky_losers"] == 3
    assert s["main_entry_label_evidence"]["observed_seeded_wild_card_ranks"] == [3]
    assert i["main_seeds"] == 8
    disagreement = w["main_draw_source_disagreement"]
    assert (disagreement["annual_summary_entrants"], disagreement["secondary_infobox_entrants"],
            disagreement["secondary_expanded_draw_entrants"]) == (56, 16, 32)
    assert w["observed_lucky_losers"] == 2
    assert w["main_geometry_status"] == "candidate_field_not_certified_full_draw"
    assert a["group_format"]["total_matches"] == 15
    assert a["second_pass_review"]["qualification_draw_status"] == "not_applicable"
    assert a["point_candidate_comparison"]["source_rule_certified"] is False
    assert batch["summary"]["second_pass_review_attempted_rows"] == 75
    assert batch["next_second_pass_review_occurrence"] is None
    assert all("second_pass_review" in r["historical_evidence"] for r in batch["occurrences"])


def test_targeted_historical_candidates_remain_separate_from_published_profiles(batch):
    by_id = {r["occurrence_id"]: r for r in batch["occurrences"]}
    order = batch["import_candidate_priority"]["ordered"]
    assert [x["occurrence_id"] for x in order] == [
        "atp_1990_atp_finals", "atp_1990_new_haven_1998", "atp_1990_dallas"]
    assert batch["summary"]["targeted_import_candidates_reviewed_rows"] == len(order)
    assert all(by_id[x["occurrence_id"]]["profile_status"] == "not_in_published_sporting_source" for x in order)
    assert batch["historical_points_evidence"]["qualification_loss_rule_research"]["qualification_loss_points"] is None
    assert batch["historical_points_evidence"]["qualifying_loss_points"] is None
    assert batch["primary_source_acquisition"]["status"] == "bibliographic_leads_only_content_not_obtained"
    assert [x["isbn10"] for x in batch["primary_source_acquisition"]["leads"]] == ["0747509123", "0002184036"]
    nh = by_id["atp_1990_new_haven_1998"]["historical_evidence"]
    assert nh["itf_event_window_evidence"]["prize_money_usd"] == 825000
    assert nh["reported_financial_commitment_usd"] == 1000000
    assert nh["qualification_start_date"] is nh["qualification_end_date"] is nh["qualification_entrants"] is None
    assert nh["targeted_import_research"]["candidate_points"]["qualification_loss_points"] is None
    assert nh["targeted_import_research"]["candidate_points"]["certified"] is False


@pytest.mark.parametrize("clock,position_key", [
    (RunCalendar(52, 1, 1990, 2), "calendar_year"),
    (RunCalendar(52, 37, 1989, 2), "offset_37"),
])
def test_frankfurt_secondary_points_fit_existing_group_contract_without_publication(batch, clock, position_key):
    # Compatibility probe only: use the existing squash policy fields from a
    # published modern profile, replace sourced geometry/points with historical
    # candidate values, and validate an isolated in-memory Edition. This is not
    # source certification, a Package import, schedule preview or actual Run.
    from beta_engine.application.atp_sporting_package_adapter import build_atp_sporting_package, parse_sporting_profile
    from beta_engine.domain.calendar.run_week_position import RunWeekPosition

    r = next(r for r in batch["occurrences"] if r["series_id"] == "atp_finals")
    e = r["historical_evidence"]
    candidate = e["targeted_import_research"]
    proposed = candidate["proposed_adaptation"]
    entity = next(e for e in build_atp_sporting_package().entities
                  if e.source_entity_id == "atp_2025_atp_finals")
    modern = parse_sporting_profile(entity.payload)
    payload = modern.model_dump(mode="json")
    payload.update({
        "occurrence_id": r["occurrence_id"], "category_id": r["category_id"],
        "name": e["historical_name"],
        "source_start_date": proposed["source_start_date"],
        "source_end_date": proposed["source_end_date"],
        "source_urls": proposed["source_urls"],
        "played_group_win_points": proposed["played_group_win_points"],
        "knockout_stage_points": proposed["knockout_stage_points"],
    })
    profile = parse_sporting_profile(payload)
    assert profile.group_count == 2 and profile.group_size == 4
    assert profile.advancing_per_group == 2 and len(profile.knockout_crossings) == 2
    pos = proposed["run_positions"][position_key]
    expected = r["run_positions_offset_1_start_1990" if position_key == "calendar_year" else "run_positions_offset_37_start_1989"]
    assert expected == [pos]
    week = RunWeekPosition(calendar=clock, season_index=pos["season_index"], week=pos["season_week"])
    announcement = RunWeekPosition(calendar=clock, season_index=pos["season_index"], week=pos["season_week"]-1)
    edition = profile.build_edition(run_id="historical-contract-probe", branch_id="probe",
        command_id="probe", week=week, announcement_week=announcement, start_slot=1, seed=0)
    assert edition.main_entrant_count == 8 and edition.validity_weeks == 52
    assert edition.week == week
    stages = profile.knockout_stage_points
    table = candidate["points_evidence"]["secondary_complete_table"]
    for wins in (1, 2, 3):
        assert wins * profile.played_group_win_points + stages["champion"] == table["champion_by_group_wins"][str(wins)]
        assert wins * profile.played_group_win_points + stages["finalist"] == table["finalist_by_group_wins"][str(wins)]
    for wins in range(4):
        assert wins * profile.played_group_win_points + stages["semifinal"] == table["non_finalist_by_group_wins"][str(wins)]
    assert proposed["max_points"] == 400
    assert modern.played_group_win_points == 200 and modern.knockout_stage_points["champion"] == 900
    assert candidate["points_evidence"]["primary_exact_table_verified"] is False
    assert proposed["status"] == "contract_probe_only_not_approved_for_import"
    assert candidate["official_group_evidence"]["pdf_sha256"] is None
    assert r["profile_status"] == "not_in_published_sporting_source"
    assert r["plan_status"] == r["played_and_reopened_status"] == "not_tested"
    assert not any(e.source_entity_id == r["occurrence_id"] for e in build_atp_sporting_package().entities)


def test_frankfurt_candidate_award_reconciliation_uses_production_composition(batch):
    from beta_engine.domain.tournaments.hybrid_ranking_policy_authority import (
        TournamentHybridRankingPolicyAuthority, hybrid_phase_point_components,
    )
    r = next(r for r in batch["occurrences"] if r["series_id"] == "atp_finals")
    c = r["historical_evidence"]["targeted_import_research"]
    proposed = c["proposed_adaptation"]
    policy = TournamentHybridRankingPolicyAuthority(
        run_id="historical-award-probe", branch_id="probe",
        event_id=r["occurrence_id"], configured_by_command_id="probe",
        played_group_win_points=proposed["played_group_win_points"],
        knockout_stage_points=tuple(sorted(proposed["knockout_stage_points"].items())),
    )
    boundary = c["runtime_boundary"]
    assert policy.composition_policy_id == boundary["composition_policy_id"]
    assert policy.group_component_policy_id == boundary["group_component_policy_id"]
    aggregate = c["anonymous_award_reconciliation"]
    entrants = wins = group_total = knockout_total = 0
    for row in aggregate["rows"]:
        stage = None if row["stage"] == "group_only" else row["stage"]
        parts = hybrid_phase_point_components(
            policy=policy, played_group_wins=row["played_group_wins"],
            knockout_reached_stage=stage)
        assert len(parts) == (1 if stage is None else 2)
        assert sum(part.points_awarded for part in parts) == row["points_each"]
        entrants += row["count"]
        wins += row["count"] * row["played_group_wins"]
        group_total += row["count"] * parts[0].points_awarded
        knockout_total += row["count"] * sum(part.points_awarded for part in parts[1:])
    assert entrants == aggregate["total_entrants"] == 8
    assert wins == aggregate["total_played_group_wins"] == 12
    assert group_total == aggregate["total_group_points"] == 600
    assert knockout_total == aggregate["total_knockout_points"] == 350
    assert group_total + knockout_total == aggregate["total_points"] == 950
    for group_wins in range(4):
        for stage in (None, "semifinal", "finalist", "champion"):
            parts = hybrid_phase_point_components(
                policy=policy, played_group_wins=group_wins,
                knockout_reached_stage=stage)
            assert sum(part.points_awarded for part in parts) == (
                50 * group_wins + (0 if stage is None else dict(policy.knockout_stage_points)[stage]))
    with pytest.raises(ValueError, match="lacks knockout stage values"):
        hybrid_phase_point_components(policy=policy, played_group_wins=1,
                                      knockout_reached_stage="unknown")
    assert c["points_evidence"]["primary_exact_table_verified"] is False
    assert c["points_evidence"]["ranking_snapshot_attempt"]["status"] == "not_obtained_no_independent_point_verification"
    assert c["contemporary_entry_evidence"]["reported_first_alternate_rank"] == 9
    assert r["historical_evidence"]["reported_prize_money"] == 2020000
    assert c["contemporary_financial_crosscheck"]["reported_event_purse_usd"] == 2000000
    assert r["profile_status"] == "not_in_published_sporting_source"


def test_new_haven_partial_qualification_evidence_does_not_certify_dates_or_geometry(batch):
    from beta_engine.domain.tournaments.atp_knockout_profile import ATPQualificationDateEvidence
    from beta_engine.domain.tournaments.fax_reference_bracket_topology import build_knockout_bracket_parts

    r = next(r for r in batch["occurrences"] if r["series_id"] == "new_haven_1998")
    e = r["historical_evidence"]
    c = e["targeted_import_research"]
    actual = c["actual_qualification_partial_evidence"]
    advertised = e["advertised_qualification_window"]
    assert actual["reported_qualifier_match_wins"] == 3
    assert actual["inferred_weekend_start_date"] == advertised["start_date"]
    assert actual["inferred_weekend_end_date"] == advertised["end_date"]
    assert e["qualification_start_date"] is e["qualification_end_date"] is e["qualification_entrants"] is None
    assert e["entry_policy"]["reserved_main_qualifier_spots"] is None
    assert batch["summary"]["partial_actual_qualification_play_evidence_rows"] == 1
    assert batch["summary"]["verified_qualification_date_rows"] == 0
    assert batch["summary"]["complete_verified_qualification_draw_rows"] == 0
    handoff = c["work_handoff"]
    with pytest.raises(ValueError, match=handoff["date_validation_error"]):
        ATPQualificationDateEvidence.model_validate_json(json.dumps({
            "start_date": advertised["start_date"],
            "end_date": advertised["end_date"],
            "source_urls": [actual["source_url"]],
            "published_dates": [actual["published_on"]],
        }))
    probe = handoff["conditional_geometry_probe"]
    assumptions = probe["assumptions"]
    # Deliberately hypothetical: never import these values or infer them from
    # a single three-win path or observed Main entry labels.
    main, sections = build_knockout_bracket_parts(
        event_id=r["occurrence_id"], **assumptions)
    assert main.source_main_entrants == 56
    assert len(sections) == probe["expected_section_count"] == 7
    assert all(s.source_entrant_count == probe["expected_section_entrants"] == 8
               and s.bracket_capacity.bit_length() - 1 == probe["expected_q_rounds"] == 3
               for s in sections)
    with pytest.raises(ValueError, match=probe["alternative_error"]):
        build_knockout_bracket_parts(event_id=r["occurrence_id"], **{
            **assumptions, "qualification_entrants": probe["alternative_hypothetical_q_entrants"]})
    assert r["profile_status"] == "not_in_published_sporting_source"


def test_knockout_candidate_triage_uses_geometry_without_certifying_entry_policy(batch):
    from beta_engine.domain.tournaments.fax_reference_bracket_topology import build_knockout_bracket_parts

    triage = batch["knockout_candidate_triage"]
    rows = {r["occurrence_id"]: r for r in batch["occurrences"]}
    reported = {key for key, r in rows.items()
                if type(r["historical_evidence"].get("qualification_size_secondary")) is int}
    assert {r["occurrence_id"] for r in triage["rows"]} == reported
    assert triage["counts"] == {
        "reported_q_size": 23, "conditional_geometry": 23,
        "conditional_geometry_and_band": 17, "geometry_without_exact_band": 6,
        "missing_main_entry_labels": 0, "no_reported_q_size": 51,
    }
    statuses = Counter(r["triage_status"] for r in triage["rows"])
    assert statuses == {"conditional_geometry_and_band_candidate": 17,
                        "missing_exact_band_candidate": 6}
    for item in triage["rows"]:
        occurrence = rows[item["occurrence_id"]]
        e = occurrence["historical_evidence"]
        assert item["reported_q_size"] == e["qualification_size_secondary"]
        assert item["observed_q"] == e["reported_main_qualifiers"]
        assert item["observed_wc"] == e["reported_main_wild_cards"]
        assert e["qualification_entrants"] is e["qualification_start_date"] is e["qualification_end_date"] is None
        assert e["entry_policy"]["reserved_main_qualifier_spots"] is None
        assert e["entry_policy"]["reserved_main_wild_cards"] is None
        assert occurrence["profile_status"] == "not_in_published_sporting_source"
        assert item["exact_secondary_band_candidate"] == (
            e["point_candidate_comparison"]["status"] == "exact_reported_band_and_bracket_size_candidate")
        g = item["conditional_geometry"]
        assert g is not None
        # Explicitly conditional on equating reported size with actual entrants
        # and observed labels with reserved places. Neither equivalence is proven.
        main, sections = build_knockout_bracket_parts(
            event_id=item["occurrence_id"], main_entrants=g["main_entrants"],
            qualification_entrants=g["qualification_entrants"],
            qualifier_spots=g["qualifier_spots"], wild_cards=g["wild_cards"], byes=g["main_byes"])
        assert main.source_main_entrants == e["main_entrants"]
        assert main.bracket_capacity == e["main_bracket_slots"]
        assert len(sections) == g["sections"] == item["observed_q"]
        assert all(s.source_entrant_count == g["entrants_per_section"]
                   and s.bracket_capacity == g["bracket_slots_per_section"] for s in sections)
        assert g["potential_matches"] == e["main_entrants"] - 1 + sum(s.source_entrant_count - 1 for s in sections)
    assert batch["summary"]["published_sporting_profiles"] == 0
    assert batch["summary"]["played_and_reopened"] == 0


def test_frankfurt_verified_test_only_import_and_historical_ranking_cutoff_remain_distinct(batch):
    from beta_engine.application.atp_sporting_package_adapter import build_atp_sporting_package

    r = next(r for r in batch["occurrences"] if r["series_id"] == "atp_finals")
    c = r["historical_evidence"]["targeted_import_research"]
    probe = c["saved_source_execution_probe"]
    assert probe["status"] == "passed_test_only_saved_source_not_published"
    assert probe["verified_ci"]["conclusion"] == "success"
    assert probe["expected_match_counts"] == {"groups": 12, "knockout": 3, "total": 15}
    assert probe["points_certified"] is False
    assert c["points_evidence"]["primary_exact_table_verified"] is False
    assert c["proposed_adaptation"]["status"] == "contract_probe_only_not_approved_for_import"
    assert r["profile_status"] == "not_in_published_sporting_source"
    assert r["plan_status"] == r["played_and_reopened_status"] == "not_tested"
    assert r["occurrence_id"] not in {e.source_entity_id for e in build_atp_sporting_package().entities}
    cutoff = batch["historical_points_evidence"]["year_end_ranking_chronology"]
    assert cutoff["year_end_cutoff_change_year"] == 1991
    assert cutoff["singles_race_introduced_year"] == 2000
    assert batch["historical_points_evidence"]["year_end_snapshot_lead"]["ranking_date"] == "1990-12-24"
    assert batch["historical_points_evidence"]["qualifying_loss_points"] is None


def test_barcelona_contemporary_main_draw_resolves_geometry_not_qualification_dates(batch):
    r = next(r for r in batch["occurrences"] if r["series_id"] == "barcelona")
    e = r["historical_evidence"]
    main = e["contemporary_main_draw_evidence"]
    assert main["source_url"] in e["source_urls"]
    assert main["pdf_sha256"] is None
    for field in ("main_entrants", "main_bracket_slots", "main_byes", "main_seeds"):
        assert main[field] == e[field]
    assert main["seed_ranks"] == list(range(1, 17))
    assert main["bye_seed_ranks"] == e["bye_seed_ranks"] == list(range(1, 9))
    assert 8 not in e["organiser_event_window_evidence"]["listed_seed_numbers"]
    assert main["reported_first_main_day"] == r["original_start_date"]
    assert e["independent_main_opening_evidence"]["reported_main_start_date"] == r["original_start_date"]
    q = e["contemporary_qualification_completion_evidence"]
    assert q["qualifying_completed_before"] == r["original_start_date"]
    assert q["minimum_confirmed_qualifiers"] == 1
    assert e["qualification_entrants"] is e["qualification_start_date"] is e["qualification_end_date"] is None
    assert e["entry_policy"]["reserved_main_qualifier_spots"] is None
    assert batch["summary"]["contemporary_printed_main_draw_evidence_rows"] == 1
    assert batch["summary"]["contemporary_qualification_completion_evidence_rows"] == 5
    assert batch["summary"]["verified_qualification_date_rows"] == 0
    assert batch["summary"]["complete_verified_qualification_draw_rows"] == 0


def test_rotterdam_historical_name_is_not_modern_sponsor_name(batch):
    r = next(r for r in batch["occurrences"] if r["series_id"] == "rotterdam")
    e = r["historical_evidence"]
    source = e["historical_name_evidence"]
    assert r["occurrence_id"] == "atp_1990_rotterdam"
    assert e["historical_name"] == "ABN World Tennis Tournament"
    assert e["historical_name_previous"] == "ABN AMRO World Tennis Tournament"
    assert source["sponsor_name_change_year"] == 1991
    assert source["chronicle_reported_start_date"] == r["original_start_date"]
    assert source["chronicle_reported_end_date"] == r["original_end_date"]
    assert all(url in e["source_urls"] for url in source["source_urls"])
    assert e["qualification_start_date"] is e["qualification_end_date"] is None
    assert r["profile_status"] == "not_in_published_sporting_source"


def test_frankfurt_1990_followup_keeps_primary_rule_and_adaptation_approval_separate(batch):
    row = next(r for r in batch["occurrences"] if r["series_id"] == "atp_finals")
    evidence = row["historical_evidence"]
    review = evidence["targeted_source_followup_2026_11_26"]
    assert review["source_year"] == 1990
    assert review["primary_exact_table_verified"] is False
    table = review["secondary_table"]
    assert table["group_win"] == 50
    assert table["semifinal_win_component"] == 100
    assert table["final_win_increment"] == 150
    assert table["champion_knockout_total"] == 100 + 150
    assert table["undefeated_champion"] == 3 * 50 + 250 == 400
    assert table["next_year_undefeated_champion"] == 480
    decision = review["work_decision"]
    assert decision["status"] == "pending_work_and_owner_approval"
    assert decision["publication_allowed"] is False
    assert "historical Best 14 inclusion/replacement" in decision["excluded_unapproved_rules"]
    assert batch["historical_points_evidence"]["ranking_inclusion_source_disagreement"]["primary_rule_page"] is None
    assert evidence["targeted_import_research"]["saved_source_execution_probe"]["points_certified"] is False
    assert row["profile_status"] == "not_in_published_sporting_source"
    assert row["plan_status"] == row["played_and_reopened_status"] == "not_tested"


def test_targeted_qualification_followup_preserves_unknowns_and_calendar(batch):
    rows = {row["series_id"]: row for row in batch["occurrences"]}
    for series, week, shifted in (("dallas", 6, 22), ("barcelona", 15, 31),
                                   ("new_haven_1998", 33, 49)):
        row = rows[series]
        evidence = row["historical_evidence"]
        review = evidence["targeted_source_followup_2026_11_26"]
        assert review["status"] == "qualification_draw_not_obtained"
        assert review["pdf_sha256"] is None
        assert len(review["missing"]) == 3
        assert evidence["qualification_entrants"] is None
        assert evidence["qualification_start_date"] is None
        assert evidence["qualification_end_date"] is None
        assert evidence["entry_policy"]["reserved_main_qualifier_spots"] is None
        assert row["run_positions_offset_1_start_1990"] == [{"season_index": 0, "season_week": week}]
        assert row["run_positions_offset_37_start_1989"] == [{"season_index": 0, "season_week": shifted}]
        assert row["profile_status"] == "not_in_published_sporting_source"
    sf = rows["dallas"]["historical_evidence"]["targeted_source_followup_2026_11_26"]
    assert sf["observed_main_matches"] == sf["observed_main_entrants"] - 1 == 31
    assert (sf["observed_main_qualifiers"], sf["observed_main_wild_cards"]) == (4, 3)
    barcelona = rows["barcelona"]["historical_evidence"]["targeted_source_followup_2026_11_26"]
    assert barcelona["printed_page"] == 47 and barcelona["visually_rechecked"]
    haven = rows["new_haven_1998"]["historical_evidence"]["targeted_source_followup_2026_11_26"]
    assert haven["advertised_start_date"] == "1990-08-11"
    assert haven["advertised_end_date"] == "1990-08-12"
    assert haven["actual_qualification_dates"] is None
    assert batch["summary"]["verified_qualification_date_rows"] == 0
    assert batch["summary"]["complete_verified_qualification_draw_rows"] == 0


def test_historical_snapshot_followup_does_not_certify_tournament_awards(batch):
    rows = {row["series_id"]: row for row in batch["occurrences"]}
    finals = rows["atp_finals"]
    research = finals["historical_evidence"]["targeted_import_research"]["points_evidence"]["extended_ranking_snapshot_research"]
    snapshots = {s["date"]: s for s in research["snapshots"]}
    assert snapshots["1990-10-29"]["top_two_gap"] == 147
    assert snapshots["1990-11-12"]["top_two_gap"] == 225
    assert snapshots["1990-11-26"]["top_two_gap"] == 361
    ocr = snapshots["1990-11-04"]
    assert ocr["source_type"] == "contemporary_newspaper_scan_indexed_ocr_unverified"
    assert "top_two_gap" not in ocr
    assert ocr["pdf_sha256"] is None and ocr["printed_page"] is None
    assert research["missing_exact_weekly_snapshots"] == ["1990-11-12", "1990-11-19"]
    assert research["primary_award_table"] is None
    assert finals["profile_status"] == "not_in_published_sporting_source"
    barcelona = rows["barcelona"]
    category = barcelona["historical_evidence"]["category_history_followup"]
    assert category["status"] == "application_label_not_proof_of_effective_category"
    assert barcelona["category_id"] == "atp_championship_series"
    assert barcelona["run_positions_offset_1_start_1990"] == [{"season_index": 0, "season_week": 15}]
    for series in ("barcelona", "new_haven_1998"):
        evidence = rows[series]["historical_evidence"]
        assert evidence["qualification_entrants"] is None
        assert evidence["qualification_start_date"] is None
        assert evidence["qualification_end_date"] is None
        assert evidence["entry_policy"]["reserved_main_qualifier_spots"] is None


def test_frankfurt_visual_source_corroborates_geometry_not_ranking_points(batch):
    rows = {row["series_id"]: row for row in batch["occurrences"]}
    row = rows["atp_finals"]
    e = row["historical_evidence"]
    research = e["targeted_import_research"]
    visual = research["official_group_evidence"]["visually_verified_alternate_pdf"]
    assert visual["visual_status"] == "page_render_checked"
    assert visual["printed_page"] == 18 and visual["pdf_page_index"] == 17
    assert visual["source_url"] in e["source_urls"]
    for key in ("group_count", "group_size", "group_matches", "semifinals", "finals",
                "competition_start_date", "competition_end_date"):
        assert visual[key] == e["group_format"][key]
    assert len(visual["group_win_distribution"]) == visual["group_count"] * visual["group_size"]
    assert sum(visual["group_win_distribution"]) == visual["group_matches"]
    assert sum(visual["prize_money_distribution_usd"]) == visual["prize_money_sum_usd"] == 2000000
    assert visual["primary_ranking_points_table"] is None
    assert visual["pdf_sha256"] is None
    assert research["saved_source_execution_probe"]["points_certified"] is False
    assert row["profile_status"] == "not_in_published_sporting_source"
    rule = batch["historical_points_evidence"]["contemporary_rule_announcement"]
    assert rule["effective_season"] == batch["source_year"] == 1990
    assert rule["best_results_count"] == 14
    assert rule["primary_full_rule_text"] is None


def test_historical_singles_finish_and_itf_money_are_not_inferred_qualification(batch):
    rows = {row["series_id"]: row for row in batch["occurrences"]}
    nh = rows["new_haven_1998"]
    e = nh["historical_evidence"]
    finish = e["singles_vs_doubles_finish_evidence"]
    assert finish["singles_final_date"] == nh["original_end_date"] == "1990-08-19"
    assert finish["doubles_final_postponed_due_to_rain"] is True
    assert e["alternate_event_end_date"] == "1990-08-20"
    g = rows["maceio_1992"]
    e = g["historical_evidence"]
    itf = e["itf_event_metadata_crosscheck"]
    assert itf["start_date"] == g["original_start_date"]
    assert itf["end_date"] == g["original_end_date"]
    assert itf["prize_money_usd"] == e["reported_prize_money"] == 125000
    assert e["reported_financial_commitment_usd"] == 150000
    assert g["category_id"] == "atp_world_series"
    assert e["point_candidate_comparison"]["source_rule_certified"] is False
    for row in (nh, g):
        evidence = row["historical_evidence"]
        assert evidence["qualification_entrants"] is None
        assert evidence["qualification_start_date"] is None
        assert evidence["qualification_end_date"] is None
        assert evidence["entry_policy"]["reserved_main_qualifier_spots"] is None


def test_orlando_and_estoril_contemporary_reports_do_not_certify_q_fields(batch):
    rows = {row["series_id"]: row for row in batch["occurrences"]}
    orlando = rows["orlando_1991"]
    e = orlando["historical_evidence"]
    press = e["contemporary_main_financial_evidence"]
    assert press["visual_status"] == "page_render_checked"
    assert press["printed_page"] == "1B" and press["pdf_page_index"] == 6
    assert press["reported_top_seeds"] == e["main_seeds"] == 8
    assert press["reported_event_amount_usd"] == e["reported_financial_commitment_usd"] == 250000
    assert e["reported_prize_money"] == 225000
    assert press["reported_first_prize_usd"] == 32400
    assert press["pdf_sha256"] is None
    q = e["contemporary_qualification_completion_evidence"]
    assert q["minimum_confirmed_qualifiers"] == 1
    assert q["reported_qualifier_reached"] == "semifinal"
    draw = e["secondary_main_draw_crosscheck"]
    assert (draw["main_entrants"], draw["observed_main_qualifiers"], draw["observed_main_wild_cards"]) == (32, 4, 3)
    assert e["qualification_archive_lead"]["status"] == "archive_and_main_issue_obtained_qualifying_issues_not_obtained"
    estoril = rows["estoril"]
    e = estoril["historical_evidence"]
    press = e["contemporary_main_opening_evidence"]
    assert press["printed_page"] == 54 and press["pdf_page_index"] == 0
    assert press["reported_main_start_date"] == estoril["original_start_date"]
    assert press["reported_first_day_singles_matches"] == 4
    assert press["reported_event_amount_usd"] == 76000
    assert e["reported_prize_money"] == 225000
    assert e["reported_financial_commitment_usd"] == 250000
    challenger = e["distinct_challenger_archive_evidence"]
    assert challenger["reported_start_date"] < estoril["original_start_date"]
    assert challenger["reported_end_date"] == estoril["original_end_date"]
    for row in (orlando, estoril):
        e = row["historical_evidence"]
        assert row["category_id"] == "atp_world_series"
        assert row["run_positions_offset_1_start_1990"] == [{"season_index": 0, "season_week": 14}]
        assert row["run_positions_offset_37_start_1989"] == [{"season_index": 0, "season_week": 30}]
        assert e["qualification_entrants"] is e["qualification_start_date"] is e["qualification_end_date"] is None
        assert e["entry_policy"]["reserved_main_qualifier_spots"] is None
        assert e["point_candidate_comparison"]["source_rule_certified"] is False
        assert row["profile_status"] == "not_in_published_sporting_source"
    assert batch["summary"]["contemporary_qualification_completion_evidence_rows"] == 5


def test_latest_frankfurt_ci_is_test_only_prior_head_evidence(batch):
    row = next(r for r in batch["occurrences"] if r["series_id"] == "atp_finals")
    research = row["historical_evidence"]["targeted_import_research"]
    ci = research["latest_verified_followup_ci"]
    assert ci["head"] == "035ffcab2c6e2b0e3f317fb7ea52423605ed6846"
    assert ci["conclusion"] == "success"
    assert ci["selected_tests_passed"] == 121
    assert ci["security_tests_passed"] == 24
    assert research["saved_source_execution_probe"]["points_certified"] is False
    assert row["profile_status"] == "not_in_published_sporting_source"


def test_los_angeles_advertised_q_and_prequalification_are_distinct(batch):
    from datetime import date

    rows = {row["series_id"]: row for row in batch["occurrences"]}
    row = rows["los_cabos"]
    e = row["historical_evidence"]
    advertised = e["advertised_qualification_window"]
    pre = e["prequalification_evidence"]
    assert advertised["status"] == "contemporary_press_announced_window_not_actual_play"
    assert advertised["source_url"] == pre["source_url"]
    assert advertised["source_url"] in e["source_urls"]
    assert advertised["published_on"] < advertised["start_date"]
    assert (advertised["start_date"], advertised["end_date"]) == ("1990-07-28", "1990-07-29")
    assert advertised["advertised_main_start_date"] == row["original_start_date"] == "1990-07-30"
    for key in ("start_date", "end_date"):
        iso = date.fromisoformat(advertised[key]).isocalendar()
        assert (iso.year, iso.week) == (1990, advertised["calendar_year_week"]) == (1990, 30)
    assert advertised["main_calendar_year_week"] == 31
    for clock, key in (
        (RunCalendar(52, 1, 1990, 2), "run_positions_offset_1_start_1990"),
        (RunCalendar(52, 37, 1989, 2), "run_positions_offset_37_start_1989"),
    ):
        q = clock.calendar_to_season(1990, 30)
        main = clock.calendar_to_season(1990, 31)
        assert advertised[key] == [{"season_index": q.season_index, "season_week": q.season_week}]
        assert row[key] == [{"season_index": main.season_index, "season_week": main.season_week}]
        assert clock.advance_weeks(q.season_index, q.season_week, 1) == main
    assert pre["reported_prequalification_main_slots"] == (
        pre["reported_seeded_reserved_berths"] + pre["reported_other_berths"]) == 32
    assert pre["reported_advances_to_regular_qualification"] == 2
    assert pre["minimum_reported_prequalification_main_matches"] == 5
    assert e["reported_main_qualifiers"] == 4
    assert e["qualification_size_secondary"] is None
    assert e["qualification_entrants"] is e["qualification_start_date"] is e["qualification_end_date"] is None
    assert e["entry_policy"]["reserved_main_qualifier_spots"] is None
    assert row["profile_status"] == "not_in_published_sporting_source"
    assert batch["summary"]["advertised_qualification_window_rows"] == 2
    assert batch["summary"]["verified_qualification_date_rows"] == 0


def test_indian_wells_contemporary_qualifier_and_ranking_announcement_scope(batch):
    row = next(r for r in batch["occurrences"] if r["series_id"] == "indian_wells")
    e = row["historical_evidence"]
    q = e["contemporary_qualification_completion_evidence"]
    assert q["source_url"] in e["source_urls"]
    assert q["minimum_confirmed_qualifiers"] == 1
    assert q["reported_qualifier_main_match_date"] == row["original_start_date"]
    assert q["reported_qualifier_defeated_seed_rank"] == 15
    assert e["qualification_entrants"] is e["qualification_start_date"] is e["qualification_end_date"] is None
    assert e["entry_policy"]["reserved_main_qualifier_spots"] is None
    assert row["category_id"] == "atp_championship_single_week"
    assert e["contemporary_advance_announcement"]["advertised_main_start_date"] == row["original_start_date"]
    assert e["contemporary_advance_announcement"]["advertised_main_end_date"] == row["original_end_date"]
    announcement = batch["historical_points_evidence"]["contemporary_rule_announcement"]
    upi = announcement["upi_corroboration"]
    assert upi["effective_season"] == announcement["effective_season"] == 1990
    assert upi["best_results_count"] == announcement["best_results_count"] == 14
    assert announcement["primary_full_rule_text"] is None
    assert batch["summary"]["contemporary_qualification_completion_evidence_rows"] == 5


def test_1990_entry_commitments_are_not_ranking_counting_or_actual_draws(batch):
    rows = {row["series_id"]: row for row in batch["occurrences"]}
    rules = batch["historical_points_evidence"]
    announced = rules["preseason_entry_commitment_announcement"]
    assert announced["announced_for_season"] == 1990
    assert announced["reported_top10_championship_events_required"] == 11
    assert announced["reported_top10_designated_single_championship_week"] == 7
    assert announced["reported_top10_designated_per_event_dual_championship_week"] == 3
    assert announced["reported_top10_required_open_week"] is False
    assert announced["reported_planned_tournaments"] == 77
    assert len(rows) == batch["summary"]["year_dated_occurrences"] == 75
    la = rows["los_cabos"]
    evidence = la["historical_evidence"]
    assert la["category_id"] == "atp_world_series"
    assert evidence["preseason_category_announcement"]["reported_1990_main_start_date"] == la["original_start_date"]
    itf = evidence["itf_event_metadata_crosscheck"]
    assert (itf["start_date"], itf["end_date"]) == (la["original_start_date"], la["original_end_date"])
    assert itf["prize_money_usd"] == evidence["reported_prize_money"] == 225000
    assert evidence["preseason_category_announcement"]["announced_event_amount_usd"] == 250000
    assert evidence["point_candidate_comparison"]["source_rule_certified"] is False
    iw = rows["indian_wells"]
    e = iw["historical_evidence"]
    assert iw["category_id"] == "atp_championship_single_week"
    assert e["preseason_category_announcement"]["announced_category_description"] == "Championship Series"
    # The advance announcement and actual edition report differ. Do not
    # replace the edition-specific entitlement with a general planned number.
    assert e["contemporary_main_opening_date_evidence"]["reported_designated_top10_players_entitlement"] == 6
    ranking = rules["ranking_inclusion_source_disagreement"]
    late = ranking["late_decade_press_crosscheck"]
    assert late["reported_best_results_count_since_1990"] == 14
    assert late["reported_rolling_weeks"] == 52
    assert late["reported_bonus_elimination_effective_year"] == 2000
    assert ranking["primary_rule_page"] is None


def test_stuttgart_indoor_qualifier_and_evidence_count(batch):
    rows = {row["series_id"]: row for row in batch["occurrences"]}
    indoor = rows["stuttgart_indoor_feb_1995"]
    outdoor = rows["stuttgart"]
    e = indoor["historical_evidence"]
    q = e["contemporary_qualification_completion_evidence"]
    assert indoor["original_start_date"] == "1990-02-19"
    assert outdoor["original_start_date"] == "1990-07-16"
    assert q["source_url"] in e["source_urls"]
    assert indoor["original_start_date"] <= q["published_on"] <= indoor["original_end_date"]
    assert q["minimum_confirmed_qualifiers"] == 1
    assert q["reported_qualifier_reached"] == "quarterfinal"
    assert "contemporary_qualification_completion_evidence" not in outdoor["historical_evidence"]
    for row in (indoor, outdoor):
        e = row["historical_evidence"]
        assert e["qualification_entrants"] is e["qualification_start_date"] is e["qualification_end_date"] is None
        assert e["entry_policy"]["reserved_main_qualifier_spots"] is None
        assert row["profile_status"] == "not_in_published_sporting_source"
    count = sum(
        bool(e.get("contemporary_qualification_completion_evidence") or
             e.get("targeted_import_research", {}).get("actual_qualification_partial_evidence"))
        for e in (row["historical_evidence"] for row in batch["occurrences"])
    )
    assert batch["summary"]["contemporary_qualification_completion_evidence_rows"] == count == 5


def test_edition_specific_secondary_workbook_points_remain_unapproved(batch):
    rows = {row["series_id"]: row for row in batch["occurrences"]}
    rules = batch["historical_points_evidence"]
    workbook = rules["edition_specific_workbook_crosscheck"]
    assert workbook["git_blob_sha1"] == "ccfdb7120d06f9391dfa4413f6de9c0a8cfc4eb6"
    assert workbook["byte_count"] == 23346
    assert workbook["workbook_sheets"] == ["View", "Week-by-week", "RG", "AO"]
    stages = tuple(workbook["main_stage_columns"].values())
    expected = {
        "dallas": (56, [103, 78, 52, 26, 13, 1]),
        "los_cabos": (49, [103, 78, 52, 26, 13, 1]),
        "rotterdam": (31, [133, 100, 67, 34, 17, 1]),
        "barcelona": (26, [180, 135, 90, 45, 23, 12, 1]),
        "new_haven_1998": (14, [230, 173, 115, 58, 30, 15, 1]),
        "indian_wells": (20, [230, 173, 115, 58, 30, 15, 1]),
        "stuttgart_indoor_feb_1995": (18, [230, 173, 115, 58, 30, 1]),
    }
    for series, (sheet_row, values) in expected.items():
        row = rows[series]
        e = row["historical_evidence"]
        source = e["edition_specific_base_points_crosscheck"]
        assert source["source_url"] == workbook["source_url"]
        assert source["workbook_git_blob_sha1"] == workbook["git_blob_sha1"]
        assert source["row"] == sheet_row
        assert source["reported_main_entrants"] == e["main_entrants"]
        assert source["reported_prize_money_usd"] == e["reported_prize_money"]
        assert source["base_main_points"] == dict(zip(stages, values))
        assert source["week_by_week_champion_points"] == values[0]
        assert source["qualifier_award"] is source["qualifying_loss_points"] is None
        assert source["source_rule_certified"] is False
        assert row["profile_status"] == "not_in_published_sporting_source"
    for series, band in (("dallas", "base_points_250k_32_candidate"),
                         ("los_cabos", "base_points_250k_32_candidate"),
                         ("rotterdam", "base_points_500k_32_candidate")):
        candidate = rules[band]
        observed = rows[series]["historical_evidence"]["edition_specific_base_points_crosscheck"]["base_main_points"]
        assert observed == {stage: candidate[stage] for stage in observed}
    for series in ("barcelona", "new_haven_1998", "indian_wells"):
        e = rows[series]["historical_evidence"]
        assert e["edition_specific_base_points_crosscheck"]["reported_main_entrants"] == 56
        assert e["main_bracket_slots"] == 64
    finals = rows["atp_finals"]
    observed = finals["historical_evidence"]["edition_specific_base_points_crosscheck"]
    assert observed["cell"] == "B81"
    assert observed["reported_maximum_points"] == rules["finals_1990_candidate"]["undefeated_champion"] == 400
    assert observed["group_win_points"] is observed["finalist_knockout_component"] is observed["champion_knockout_component"] is None
    assert observed["source_rule_certified"] is False
    assert workbook["primary_rule_page"] is None
    assert finals["profile_status"] == "not_in_published_sporting_source"
    assert batch["summary"]["published_sporting_profiles"] == 0


def test_entry_commitment_followup_ci_keeps_candidate_test_only(batch):
    e = next(r["historical_evidence"] for r in batch["occurrences"] if r["series_id"] == "atp_finals")
    research = e["targeted_import_research"]
    ci = research["verified_ci_after_entry_commitment_followup"]
    assert ci["head"] == "512deaaa710f7e3a9078cb7ad3ed2f5e861d6126"
    assert ci["conclusion"] == "success"
    assert ci["selected_tests_passed"] == 127
    assert ci["security_tests_passed"] == 24
    assert research["saved_source_execution_probe"]["points_certified"] is False


def test_1990_workbook_season_mapping_and_disagreement_census(batch):
    rules = batch["historical_points_evidence"]
    book = rules["edition_specific_workbook_crosscheck"]
    census = book["season_crosscheck"]
    rows = {r["series_id"]: r for r in batch["occurrences"]}
    knockout = {k: r for k, r in rows.items() if k != "atp_finals"}
    seen_view, seen_week = set(), set()
    field_diff, prize_diff, stage_diff = [], [], []
    agrees, disagrees, not_compared = [], [], []
    both = 0
    stages = list(book["main_stage_columns"].values())
    for series, row in knockout.items():
        e = row["historical_evidence"]
        x = e["edition_specific_base_points_crosscheck"]
        assert x["source_url"] == book["source_url"]
        assert x["workbook_git_blob_sha1"] == book["git_blob_sha1"]
        assert x["sheet"] == "View"
        assert x["row"] not in seen_view
        seen_view.add(x["row"])
        week = int(x["week_by_week_champion_cell"][1:])
        assert week not in seen_week
        seen_week.add(week)
        values = x["base_main_points"]
        assert list(values) == stages[:len(values)]
        assert all(type(v) is int and v > 0 for v in values.values())
        assert list(values.values()) == sorted(values.values(), reverse=True)
        assert values["champion"] == x["week_by_week_champion_points"]
        assert x["qualifier_award"] is x["qualifying_loss_points"] is None
        assert x["source_rule_certified"] is False
        comparison = x["comparison_to_prior_evidence"]
        field_matches = x["reported_main_entrants"] == e["main_entrants"]
        prize_matches = x["reported_prize_money_usd"] == e["reported_prize_money"]
        stage_matches = len(values) == e["main_bracket_slots"].bit_length()
        assert comparison["reported_field_matches"] == field_matches
        assert comparison["reported_prize_matches"] == prize_matches
        assert comparison["main_stage_count_matches_working_bracket"] == stage_matches
        assert comparison["prior_main_bracket_slots"] == e["main_bracket_slots"]
        assert comparison["prior_main_entrants"] == e["main_entrants"]
        assert comparison["prior_reported_prize_money_usd"] == e["reported_prize_money"]
        if not field_matches:
            field_diff.append(series)
        if not prize_matches:
            prize_diff.append(series)
        if not stage_matches:
            stage_diff.append(series)
        both += int(field_matches and prize_matches)
        ref = comparison["stored_candidate_reference"]
        if ref is None:
            not_compared.append(series)
            expected = "not_compared_no_stored_exact_candidate_table"
        else:
            if ref.startswith("world_series_64_candidate_rows:"):
                band = int(ref.split(":")[1])
                candidate = next(c["main"] for c in rules["world_series_64_candidate_rows"] if c["band_usd"] == band)
            else:
                candidate = [rules[ref][k] for k in stages[:6]]
            if list(values.values()) == candidate:
                agrees.append(series)
                expected = "all_main_stage_values_agree"
            else:
                disagrees.append(series)
                expected = "main_stage_values_or_count_differ"
        assert comparison["stored_candidate_comparison_status"] == expected
        assert row["profile_status"] == "not_in_published_sporting_source"
    assert seen_view == set(range(6, 80))
    assert seen_week == set(range(3, 81)) - set(census["excluded_week_by_week_rows"])
    assert len(rows) == census["mapped_occurrences"] == 75
    assert len(knockout) == census["knockout_rows"] == 74
    assert census["excluded_view_rows"] == [2, 3, 4, 5]
    assert census["finals_maximum_rows"] == 1
    assert both == census["knockout_field_and_prize_agree_rows"] == 68
    assert field_diff == census["reported_field_disagreement_series"] == ["kitzbuhel", "schenectady_1994"]
    assert prize_diff == census["reported_prize_disagreement_series"] == [
        "sofia", "toronto_indoor_1990", "moscow", "wembley_1990"]
    assert stage_diff == census["main_stage_count_disagreement_series"] == ["kitzbuhel"]
    assert agrees == census["stored_main_candidate_exact_match_series"]
    assert disagrees == census["stored_main_candidate_disagreement_series"] == ["wembley_1990"]
    assert not_compared == census["stored_main_candidate_not_compared_series"]
    assert (len(agrees), len(disagrees), len(not_compared)) == (36, 1, 37)
    assert rows["sofia"]["historical_evidence"]["edition_specific_base_points_crosscheck"]["reported_name"] == "Milan"
    assert rows["dallas"]["historical_evidence"]["edition_specific_base_points_crosscheck"]["reported_name"] == "San Francisco"
    assert rows["hong_kong"]["historical_evidence"]["edition_specific_base_points_crosscheck"]["reported_name"] == "Nice"
    assert rows["toronto_indoor_1990"]["historical_evidence"]["edition_specific_base_points_crosscheck"]["row"] == 10
    assert rows["canadian_open"]["historical_evidence"]["edition_specific_base_points_crosscheck"]["row"] == 11
    finals = rows["atp_finals"]["historical_evidence"]
    assert finals["edition_specific_base_points_crosscheck"]["cell"] == "B81"
    assert finals["edition_specific_base_points_crosscheck"]["reported_maximum_points"] == 400
    assert book["primary_rule_page"] is None
    assert batch["summary"]["published_sporting_profiles"] == 0
    assert batch["summary"]["verified_qualification_date_rows"] == 0
    assert batch["summary"]["complete_verified_qualification_draw_rows"] == 0


def test_workbook_first_pass_ci_does_not_certify_season_crosscheck(batch):
    e = next(r["historical_evidence"] for r in batch["occurrences"] if r["series_id"] == "atp_finals")
    research = e["targeted_import_research"]
    ci = research["verified_ci_after_workbook_first_pass"]
    assert ci["head"] == "a9154b049175967cfc2cceeecb9d7bc71c732c79"
    assert ci["conclusion"] == "success"
    assert ci["selected_tests_passed"] == 129
    assert ci["security_tests_passed"] == 24
    assert research["saved_source_execution_probe"]["points_certified"] is False


def test_workbook_conflict_followup_preserves_original_comparison_and_qualification(batch):
    rows = {r["series_id"]: r for r in batch["occurrences"]}
    k = rows["kitzbuhel"]["historical_evidence"]
    source = k["workbook_conflict_followup"]
    assert (k["main_entrants"], k["main_bracket_slots"], k["main_byes"], k["main_seeds"]) == (48, 64, 16, 16)
    assert source["bye_seed_ranks"] == k["bye_seed_ranks"] == list(range(1, 17))
    assert (k["reported_main_qualifiers"], k["reported_main_wild_cards"]) == (6, 4)
    assert source["observed_seeded_wild_card_ranks"] == [2]
    assert source["observed_special_exempt"] == 1
    assert (source["workbook_field"], source["workbook_stage_count"], source["working_stage_count"]) == (32, 6, 7)
    assert k["secondary_main_match_count_evidence"]["reported_match_count"] == 47
    assert k["main_entry_label_evidence"]["source_url"] in k["source_urls"]
    s = rows["schenectady_1994"]["historical_evidence"]
    source = s["workbook_conflict_followup"]
    assert (source["reported_main_entrants"], source["reported_main_byes"], source["reported_main_seeds"]) == (28, 4, 8)
    assert source["workbook_field"] == 32
    assert s["bye_seed_ranks"] == [1, 2, 3, 4]
    expected = {
        "sofia": (540000, 450000, 540000, "supports_prior_prize"),
        "toronto_indoor_1990": (1005000, 1050000, 1005000, "supports_prior_prize"),
        "moscow": (225000, 297000, 297000, "supports_workbook_prize"),
        "wembley_1990": (450000, 297000, 297000, "supports_workbook_prize"),
    }
    for series, (prior, workbook, itf, status) in expected.items():
        e = rows[series]["historical_evidence"]
        source = e["workbook_conflict_followup"]
        assert e["reported_prize_money"] == source["prior_prize_money_usd"] == prior
        assert e["edition_specific_base_points_crosscheck"]["reported_prize_money_usd"] == source["workbook_prize_money_usd"] == workbook
        assert source["reported_prize_money_usd"] == itf
        assert source["status"] == status
    m = rows["moscow"]["historical_evidence"]["workbook_conflict_followup"]
    assert m["contemporary_event_amount"]["reported_event_amount_usd"] == m["organiser_retrospective"]["reported_prize_money_usd"] == 330000
    assert m["contemporary_event_amount"]["reported_start_date"] == rows["moscow"]["original_start_date"] == "1990-11-05"
    assert m["organiser_retrospective"]["reported_start_date"] == "1990-10-05"
    for series in ("kitzbuhel", "schenectady_1994", *expected):
        row = rows[series]
        e = row["historical_evidence"]
        assert e["qualification_entrants"] is e["qualification_start_date"] is e["qualification_end_date"] is None
        assert e["entry_policy"]["reserved_main_qualifier_spots"] is None
        assert row["profile_status"] == "not_in_published_sporting_source"
    assert batch["summary"]["reported_seed_count_rows"] == 73
    assert batch["summary"]["reported_main_qualifier_count_rows"] == batch["summary"]["reported_main_wild_card_count_rows"] == 70


def test_championship_1990_secondary_rule_comparison_preserves_round16_discrepancy(batch):
    rules = batch["historical_points_evidence"]
    source = rules["champ_series_1990_targeted_secondary_rows"]
    assert source["iteration"] == 1990
    assert source["qualification_loss_points"] is None
    tables = {(r["band_usd"], r["md"]): r for r in source["rows"]}
    assert len(tables) == 4
    agree, diff = [], []
    for row in batch["occurrences"]:
        e = row["historical_evidence"]
        prior = e["point_candidate_comparison"]
        if prior["status"] != "exact_reported_band_and_bracket_size_candidate" or prior["source_tier_candidate"] != "CHAMP SERIES":
            continue
        x = e["edition_specific_base_points_crosscheck"]
        comp = x["targeted_champ_series_rule_comparison"]
        t = tables[(prior["reported_financial_commitment_usd"], e["main_bracket_slots"])]
        assert (comp["band_usd"], comp["md"]) == (t["band_usd"], t["md"])
        assert comp["iteration"] == 1990
        assert len(t["main"]) == len(x["base_main_points"])
        differences = [
            {"stage": k, "workbook": v, "rule_row": candidate}
            for (k, v), candidate in zip(x["base_main_points"].items(), t["main"])
            if v != candidate
        ]
        assert comp["differences"] == differences
        if differences:
            assert differences == [{"stage": "round_of_16", "workbook": 30, "rule_row": 29}]
            assert comp["status"] == "main_stage_values_differ"
            diff.append(row["series_id"])
        else:
            assert comp["status"] == "all_main_stage_values_agree"
            agree.append(row["series_id"])
        assert comp["secondary_qualifier_award_candidate"] == t["qualifier"]
        assert comp["workbook_qualifier_award"] is None
        assert comp["source_rule_certified"] is False
        assert row["profile_status"] == "not_in_published_sporting_source"
    book = rules["edition_specific_workbook_crosscheck"]
    followup = book["targeted_rule_followup"]
    baseline = book["season_crosscheck"]
    assert agree == followup["additional_agree_series"] == ["miami", "barcelona"]
    assert diff == followup["additional_disagreement_series"]
    assert len(diff) == 11
    assert len(agree) + len(diff) == followup["additional_compared_knockout_rows"] == 13
    assert len(baseline["stored_main_candidate_exact_match_series"]) + len(agree) == followup["combined_agree_rows"] == 38
    assert len(baseline["stored_main_candidate_disagreement_series"]) + len(diff) == followup["combined_disagreement_rows"] == 12
    assert followup["combined_compared_knockout_rows"] == 50
    assert len(baseline["stored_main_candidate_not_compared_series"]) - 13 == followup["remaining_without_exact_label_numeric_comparison"] == 24
    assert book["primary_rule_page"] is None
    assert batch["summary"]["published_sporting_profiles"] == 0


def test_full_season_workbook_ci_is_prior_head_not_publication_approval(batch):
    e = next(r["historical_evidence"] for r in batch["occurrences"] if r["series_id"] == "atp_finals")
    research = e["targeted_import_research"]
    ci = research["verified_ci_after_workbook_full_season"]
    assert ci["head"] == "378121db699ea063bb56bf8f4e7d25632112d1e6"
    assert ci["conclusion"] == "success"
    assert ci["selected_tests_passed"] == 131
    assert ci["security_tests_passed"] == 24
    assert research["saved_source_execution_probe"]["points_certified"] is False


def test_remaining_1990_numeric_hypotheses_do_not_promote_financial_classes(batch):
    rules = batch["historical_points_evidence"]
    book = rules["edition_specific_workbook_crosscheck"]
    stages = list(book["main_stage_columns"].values())
    baseline = book["season_crosscheck"]
    targeted = book["targeted_rule_followup"]
    alternative = book["alternative_numeric_followup"]
    rows = {r["series_id"]: r for r in batch["occurrences"]}
    earlier = set(baseline["stored_main_candidate_exact_match_series"] +
                  baseline["stored_main_candidate_disagreement_series"] +
                  targeted["additional_agree_series"] +
                  targeted["additional_disagreement_series"])
    remaining = set(rows) - {"atp_finals"} - earlier
    assert len(earlier) == 50 and len(remaining) == 24
    agree, disagree = set(), set()
    for series, row in rows.items():
        e = row["historical_evidence"]
        workbook = e["edition_specific_base_points_crosscheck"]
        candidate = workbook.get("alternative_numeric_rule_comparison")
        if series not in remaining:
            assert candidate is None
            continue
        assert candidate is not None
        assert candidate["selection_basis"] == "same_historical_tier_working_bracket_and_workbook_champion_points_not_financial_class"
        assert candidate["prior_reported_financial_commitment_usd"] == e["reported_financial_commitment_usd"]
        assert workbook["comparison_to_prior_evidence"]["stored_candidate_reference"] is None
        assert candidate["source_rule_certified"] is False
        assert candidate["workbook_qualifier_award"] is None
        assert workbook["qualifying_loss_points"] is None
        assert candidate["md"] == e["main_bracket_slots"]
        assert candidate["source_tier"] == ("WORLD SERIES" if row["category_id"] == "atp_world_series" else "CHAMP SERIES")
        ref = candidate["stored_table_reference"]
        band, md = candidate["hypothetical_band_usd"], candidate["md"]
        if ref.startswith("world_series_64_candidate_rows:"):
            table = next(t for t in rules["world_series_64_candidate_rows"] if t["band_usd"] == band)
            assert md == 64
        elif ref.startswith("base_points_"):
            assert ref == f"base_points_{band // 1000}k_32_candidate"
            assert md == 32
            table = {"main": [rules[ref][s] for s in stages[:6]], "qualifier": rules[ref]["qualifier"]}
        else:
            assert ref in ("champ_series_1990_targeted_secondary_rows", "additional_champ_series_1990_hypothesis_rows")
            assert rules[ref]["iteration"] == 1990
            table = next(t for t in rules[ref]["rows"] if (t["band_usd"], t["md"]) == (band, md))
        assert len(table["main"]) == md.bit_length()
        values = workbook["base_main_points"]
        assert values["champion"] == table["main"][0]
        expected = []
        for i, stage in enumerate(stages[:max(len(values), len(table["main"]))]):
            a = values.get(stage)
            b = table["main"][i] if i < len(table["main"]) else None
            if a != b:
                expected.append({"stage": stage, "workbook": a, "rule_row": b})
        assert candidate["differences"] == expected
        assert candidate["secondary_qualifier_award_candidate"] == table["qualifier"]
        if expected:
            assert candidate["status"] == "main_stage_values_or_count_differ"
            disagree.add(series)
        else:
            assert candidate["status"] == "all_main_stage_values_agree"
            agree.add(series)
        assert row["profile_status"] == "not_in_published_sporting_source"
    assert agree == set(alternative["agree_series"])
    assert disagree == set(alternative["disagreement_series"]) == {
        "kitzbuhel", "toronto_indoor_1990", "canadian_open", "stockholm", "paris_masters"}
    assert (len(agree), len(disagree)) == (19, 5)
    assert agree | disagree == remaining
    assert alternative["compared_knockout_rows"] == 24
    assert alternative["exact_label_comparison_count_unchanged"] == 50
    assert alternative["remaining_without_exact_label_numeric_comparison"] == 24
    assert alternative["total_knockout_numeric_comparison_coverage"] == 74
    assert batch["summary"]["published_sporting_profiles"] == 0


def test_additional_event_amounts_and_commitment_leads_preserve_evidence_boundaries(batch):
    rows = {r["series_id"]: r for r in batch["occurrences"]}
    amounts = {"kitzbuhel": 375000, "washington": 550000, "stockholm": 1100000,
               "paris_masters": 2000000, "moscow": 330000}
    for series, amount in amounts.items():
        e = rows[series]["historical_evidence"]
        source = e["additional_contemporary_financial_crosscheck"]
        assert source["reported_event_amount_usd"] == amount
        assert source["source_url"] in e["source_urls"]
        assert e["reported_prize_money"] != amount
    for series, amount in {"canadian_open": 1200000, "cincinnati": 1300000,
                           "stockholm": 1100000, "paris_masters": 2000000}.items():
        e = rows[series]["historical_evidence"]
        lead = e["additional_reported_commitment_lead"]
        assert lead["reported_financial_commitment_usd"] == amount
        assert lead["prior_reported_financial_commitment_usd"] == e["reported_financial_commitment_usd"] is None
        assert lead["source_url"] in e["source_urls"]
    m = rows["moscow"]["historical_evidence"]["additional_contemporary_financial_crosscheck"]
    assert m["reported_singles_champion_prize_usd"] == 42800
    assert m["reported_singles_finalist_prize_usd"] == 25200
    k = rows["kitzbuhel"]["historical_evidence"]["edition_specific_base_points_crosscheck"]
    assert k["alternative_numeric_rule_comparison"]["differences"] == [
        {"stage": "round_of_32", "workbook": 1, "rule_row": 8},
        {"stage": "round_of_64", "workbook": None, "rule_row": 1},
    ]
    ci = rows["atp_finals"]["historical_evidence"]["targeted_import_research"]["verified_ci_after_championship_followup"]
    assert ci["head"] == "7aaa8e43f01c18ac9892a4d2f7c9810742090a67"
    assert ci["selected_tests_passed"] == 134 and ci["security_tests_passed"] == 24
    assert ci["conclusion"] == "success"


def test_february_main_entry_label_followup_enables_conditional_geometry_only(batch):
    from beta_engine.domain.tournaments.fax_reference_bracket_topology import build_knockout_bracket_parts

    rows = {r["series_id"]: r for r in batch["occurrences"]}
    triage = {r["occurrence_id"]: r for r in batch["knockout_candidate_triage"]["rows"]}
    for series, host, qsize, q, wc, byes, matches, exact_band in (
        ("toronto_indoor_1990", "Toronto", 28, 7, 5, 8, 76, False),
        ("philadelphia_1998", "Philadelphia", 24, 6, 4, 16, 65, True),
        ("rio", "Memphis", 24, 6, 3, 16, 65, True),
    ):
        row = rows[series]
        e = row["historical_evidence"]
        assert e["host_city"] == host
        assert e["qualification_size_secondary"] == qsize
        assert (e["reported_main_qualifiers"], e["reported_main_wild_cards"]) == (q, wc)
        labels = e["main_entry_label_evidence"]
        assert labels["status"] == "observed_labels_in_secondary_main_draw_not_guaranteed_policy"
        assert labels["source_url"] in e["source_urls"]
        assert labels["corroborating_main_draw_url"] in e["source_urls"]
        assert e["bye_seed_ranks"] == list(range(1, byes + 1))
        item = triage[row["occurrence_id"]]
        g = item["conditional_geometry"]
        assert item["exact_secondary_band_candidate"] is exact_band
        assert (g["sections"], g["entrants_per_section"], g["potential_matches"]) == (q, 4, matches)
        main, sections = build_knockout_bracket_parts(
            event_id=row["occurrence_id"], main_entrants=g["main_entrants"],
            qualification_entrants=qsize, qualifier_spots=q, wild_cards=wc, byes=byes)
        assert main.direct_main_slots == e["main_entrants"] - q - wc
        assert len(main.qualifier_placeholder_ids) == len(sections) == q
        assert len({s.section_id for s in sections}) == q
        assert {s.qualifier_placeholder_id for s in sections} == set(main.qualifier_placeholder_ids)
        assert all(s.source_entrant_count == s.bracket_capacity == 4 for s in sections)
        assert main.actual_match_count_if_fully_played + sum(s.actual_match_count_if_fully_played for s in sections) == matches
        assert e["qualification_entrants"] is e["qualification_start_date"] is e["qualification_end_date"] is None
        assert e["entry_policy"]["reserved_main_qualifier_spots"] is e["entry_policy"]["reserved_main_wild_cards"] is None
        assert row["profile_status"] == "not_in_published_sporting_source"
    ph = rows["philadelphia_1998"]["historical_evidence"]["main_entry_label_evidence"]
    assert sum(ph["qualifier_counts_by_section"]) == 6
    assert sum(ph["wild_card_counts_by_section"]) == 4


def test_los_angeles_announcement_can_pass_date_shape_without_proving_actual_play(batch):
    from beta_engine.domain.tournaments.atp_knockout_profile import ATPQualificationDateEvidence

    row = next(r for r in batch["occurrences"] if r["series_id"] == "los_cabos")
    e = row["historical_evidence"]
    announcement = e["advertised_qualification_window"]
    # A model's structural validation is not a provenance review.
    evidence = ATPQualificationDateEvidence.model_validate_json(json.dumps({
        "start_date": announcement["start_date"],
        "end_date": announcement["end_date"],
        "source_urls": [announcement["source_url"]],
        "published_dates": [announcement["published_on"]],
    }))
    assert (evidence.start_date, evidence.end_date) == ("1990-07-28", "1990-07-29")
    assert e["historical_date_contract_followup"]["expected_structural_date_validator_result"] == "accepts_dated_https_announcement_shape_only"
    assert e["qualification_entrants"] is e["qualification_start_date"] is e["qualification_end_date"] is None
    assert e["entry_policy"]["reserved_main_qualifier_spots"] is None
    assert row["profile_status"] == "not_in_published_sporting_source"
    assert batch["summary"]["verified_qualification_date_rows"] == 0


def test_targeted_finals_adaptation_requires_separate_owner_and_ranking_decisions(batch):
    row = next(r for r in batch["occurrences"] if r["series_id"] == "atp_finals")
    e = row["historical_evidence"]
    followup = e["targeted_archive_followup_2026_11_26"]
    decision = followup["decision"]
    assert followup["primary_rule_verified"] is False
    assert decision["status"] == "pending_owner_approval"
    assert decision["publication_allowed"] is False
    assert decision["historical_finals_inclusion_verified"] is False
    assert decision["workbook_phase_breakdown"] is None
    assert decision["played_group_win"] == 50
    assert decision["semifinal_win_increment"] == 100
    assert decision["final_win_increment"] == 150
    assert decision["champion_knockout_total"] == 250
    assert decision["finalist_knockout_total"] == 100
    assert decision["semifinal_loser_knockout_total"] == 0
    assert decision["champion_knockout_total"] == (
        decision["semifinal_win_increment"] + decision["final_win_increment"])
    assert decision["maximum"] == decision["workbook_maximum_only"] == (
        3 * decision["played_group_win"] + decision["champion_knockout_total"])
    assert decision["completed_15_match_award_sum"] == (
        12 * decision["played_group_win"] +
        2 * decision["semifinal_win_increment"] + decision["final_win_increment"])
    assert row["profile_status"] == "not_in_published_sporting_source"
    assert all(s["url"] in e["source_urls"] for s in followup["sources"])


@pytest.mark.parametrize("series,window_key,expected_week", [
    ("atp_finals", "actual_competition", 46),
    ("new_haven_1998", "advertised_qualification", 32),
    ("los_cabos", "advertised_qualification", 30),
])
def test_targeted_archive_windows_project_without_promoting_evidence(
        batch, series, window_key, expected_week):
    from datetime import date

    row = next(r for r in batch["occurrences"] if r["series_id"] == series)
    e = row["historical_evidence"]
    window = e["targeted_archive_followup_2026_11_26"][window_key]
    assert window["calendar_year_week"] == expected_week
    for endpoint in ("start", "end"):
        original = date.fromisoformat(window[endpoint])
        assert original.year == 1990 and original.isocalendar().week == expected_week
        for offset, clock in (
                (1, RunCalendar(52, 1, 1990, 2)),
                (37, RunCalendar(52, 37, 1989, 2))):
            pos = clock.calendar_to_season(original.year, expected_week)
            assert pos is not None
            assert window[f"offset_{offset}"] == {
                "season_index": pos.season_index, "season_week": pos.season_week}
    assert row["profile_status"] == "not_in_published_sporting_source"
    if window_key == "advertised_qualification":
        assert window["end"] < row["original_start_date"]
        assert e["qualification_start_date"] is e["qualification_end_date"] is None


def test_targeted_archive_inventory_and_prequalifying_are_not_main_entry_rules(batch):
    rows = {r["series_id"]: r for r in batch["occurrences"]}
    for series in ("new_haven_1998", "los_cabos", "dallas"):
        row = rows[series]
        e = row["historical_evidence"]
        followup = e["targeted_archive_followup_2026_11_26"]
        assert followup["actual_qualification"] is None
        assert followup["full_qualifying_draw"] is None
        assert followup["reserved_main_places"] is None
        assert e["qualification_start_date"] is e["qualification_end_date"] is None
        assert e["entry_policy"]["reserved_main_qualifier_spots"] is None
        assert row["profile_status"] == "not_in_published_sporting_source"
        assert all(s["url"] in e["source_urls"] for s in followup["sources"])
    yale = rows["new_haven_1998"]["historical_evidence"]["targeted_archive_followup_2026_11_26"]["archive"]
    assert (yale["collection"], yale["accession"], yale["box"], yale["folder"]) == (
        "RU 507", "2006-A-242", 11, 411)
    assert (yale["finding_aid_pdf_page_index"], yale["printed_page"]) == (37, 38)
    assert yale["folder_contents_accessed"] is False
    assert yale["pdf_sha256"] is None
    pre = rows["los_cabos"]["historical_evidence"]["targeted_archive_followup_2026_11_26"]["prequalifying"]
    assert pre["reported_draw"] == 32
    assert pre["reported_advances_to_regular_qualification"] == 2
    assert pre["advances_to_main"] is None
    sf = rows["dallas"]["historical_evidence"]["targeted_archive_followup_2026_11_26"]
    assert sf["search_window"]["purpose"] == "archive search dates only, not qualifying dates"
    assert batch["summary"]["verified_qualification_date_rows"] == 0


def test_frankfurt_contemporary_play_dates_do_not_certify_numeric_ranking_policy(batch):
    from datetime import date

    row = next(r for r in batch["occurrences"] if r["series_id"] == "atp_finals")
    e = row["historical_evidence"]
    followup = e["contemporary_source_integrity_followup_2026_11_26"]
    opening = followup["opening_report"]
    closing = followup["semifinal_final_report"]
    assert opening["reported_completed_group_matches"] == 3
    assert opening["reported_retirements_in_those_matches"] == 0
    assert (closing["reported_semifinals"], closing["reported_finals"]) == (2, 1)
    assert (opening["actual_day"], closing["semifinal_day"], closing["final_day"]) == (
        "1990-11-13", "1990-11-17", "1990-11-18")
    for day in (opening["actual_day"], closing["semifinal_day"], closing["final_day"]):
        d = date.fromisoformat(day)
        assert d.isocalendar().week == opening["calendar_year_week"] == 46
        assert row["original_start_date"] <= day <= row["original_end_date"]
        for clock, key in (
            (RunCalendar(52, 1, 1990, 2), "run_positions_offset_1_start_1990"),
            (RunCalendar(52, 37, 1989, 2), "run_positions_offset_37_start_1989"),
        ):
            pos = clock.calendar_to_season(d.year, d.isocalendar().week)
            assert pos is not None
            assert row[key] == [{"season_index": pos.season_index, "season_week": pos.season_week}]
    crosscheck = followup["source_extraction_crosscheck"]
    assert crosscheck["current_pdf_screen_attempts"] == "http_403"
    assert crosscheck["pdf_sha256"] is None
    assert all(url in e["source_urls"] for url in crosscheck["pdf_urls"])
    assert all(s["source_url"] in e["source_urls"]
               for s in [opening, closing, *followup["ranking_context"]])
    assert [s["published_on"] for s in followup["ranking_context"]] == [
        "1989-08-31", "1999-11-22", "1992-11-18"]
    for key in ("historical_finals_inclusion_verified", "primary_numeric_rule_verified",
                "owner_approval", "publication_allowed"):
        assert followup[key] is False
    assert row["profile_status"] == "not_in_published_sporting_source"


def test_new_haven_additional_partial_report_does_not_inflate_qualification_coverage(batch):
    row = next(r for r in batch["occurrences"] if r["series_id"] == "new_haven_1998")
    e = row["historical_evidence"]
    followup = e["contemporary_source_integrity_followup_2026_11_26"]
    report = followup["source"]
    prior = e["targeted_import_research"]["actual_qualification_partial_evidence"]
    assert report["reported_q_wins"] == prior["reported_qualifier_match_wins"] == 3
    assert report["reported_matches_in_seven_days"] == 8
    assert report["reported_quarterfinal_day"] == "1990-08-17"
    assert report["source_url"] in e["source_urls"]
    assert followup["additional_source"]["source_url"] in e["source_urls"]
    assert report["screen_status"] == "http_403"
    assert report["pdf_sha256"] is report["pdf_page_index"] is report["printed_page"] is None
    for key in ("actual_qualification_start_date", "actual_qualification_end_date",
                "actual_qualification_entrants", "full_qualifying_draw", "reserved_main_places"):
        assert followup[key] is None
    assert e["qualification_start_date"] is e["qualification_end_date"] is None
    assert e["entry_policy"]["reserved_main_qualifier_spots"] is None
    assert row["profile_status"] == "not_in_published_sporting_source"
    assert batch["summary"]["verified_qualification_date_rows"] == 0


def test_prague_original_programme_range_is_not_a_qualification_phase(batch):
    from datetime import date, timedelta

    row = next(r for r in batch["occurrences"] if r["series_id"] == "prague_1999")
    e = row["historical_evidence"]
    a = e["prague_program_archive_followup_2026_11_26"]
    museum = a["museum_inventory"]
    assert (museum["carton"], museum["item"], museum["pdf_page_index"]) == (3, 126, 7)
    assert museum["visual_verification"] is True
    assert museum["pdf_sha256"] is museum["printed_page"] is None
    assert a["bibliographic_record"]["publication_year"] == 1990
    assert (e["main_seeds"], e["reported_main_qualifiers"], e["reported_main_wild_cards"]) == (8, 4, 3)
    assert a["partial_label_crosscheck"]["observed_q_labels_in_one_main_pairing"] == 2
    assert a["main_opening"]["reported_round"] == "R32"
    assert a["main_opening"]["reported_date"] == row["original_start_date"] == "1990-08-06"
    assert row["original_end_date"] == "1990-08-12"
    w = a["program_event_window"]
    start, end = date.fromisoformat(w["start_date"]), date.fromisoformat(w["end_date"])
    assert start.isoformat() == "1990-08-04" and end.isoformat() == row["original_end_date"]
    weeks = sorted({(start + timedelta(days=i)).isocalendar().week
                    for i in range((end - start).days + 1)})
    assert weeks == w["calendar_year_weeks"] == [31, 32]
    for offset, clock in ((1, RunCalendar(52, 1, 1990, 2)), (37, RunCalendar(52, 37, 1989, 2))):
        positions = [clock.calendar_to_season(1990, week) for week in weeks]
        assert all(pos is not None for pos in positions)
        assert w[f"offset_{offset}"] == [
            {"season_index": pos.season_index, "season_week": pos.season_week}
            for pos in positions]
    assert row["mapped_year_weeks"] == [{"calendar_year": 1990, "year_week": 32}]
    assert all(a[k] is None for k in ("actual_q_dates", "actual_q_entrants", "complete_q_draw", "reserved_main_places"))
    assert e["qualification_size_secondary"] is e["qualification_entrants"] is None
    assert e["qualification_start_date"] is e["qualification_end_date"] is None
    assert e["entry_policy"]["reserved_main_qualifier_spots"] is None
    assert "advertised_qualification_window" not in e
    assert row["profile_status"] == "not_in_published_sporting_source"
    assert all(a[key]["source_url"] in e["source_urls"] for key in (
        "museum_inventory", "bibliographic_record", "main_opening",
        "partial_label_crosscheck", "local_press_route"))


def test_ranking_source_conflicts_are_not_approved_historical_policy(batch):
    rules = batch["historical_points_evidence"]
    a = rules["ranking_inclusion_source_disagreement"]["additional_source_review_2026_11_26"]
    assert a["atp"]["reported_bonus_end_year"] == 1999
    assert a["ao"]["reported_bonus_end_year"] == 1989
    assert a["contemporary_bonus"]["published_on"] == "1992-01-31"
    assert a["contemporary_bonus"]["reported_opponent_rank_max"] == 200
    assert a["contemporary_bonus"]["printed_page"] == "4B"
    assert a["contemporary_bonus"]["pdf_sha256"] is None
    assert a["source_reconstruction"]["reported_mandatory_grand_slams"] == 4
    assert a["ao"]["reported_grand_slams_mandatory_in_1990"] is False
    assert a["itf_visual"]["reported_cutoff_change_year"] == 1991
    assert a["itf_visual"]["pdf_page_index"] == 6
    assert a["finals_primary_rule"] is a["qualifying_loss_points"] is None
    assert a["product_policy_approved"] is False
    assert rules["rank_dependent_bonus_awards"] is True
    assert rules["qualifying_loss_points"] is None
    row = next(r for r in batch["occurrences"] if r["series_id"] == "atp_finals")
    f = row["historical_evidence"]["ranking_source_conflict_followup_2026_11_26"]
    assert f["secondary_reported_opponent_bonus"] is False
    assert f["secondary_reported_special_inclusion"] is True
    assert f["primary_finals_bonus_rule"] is f["primary_finals_inclusion_rule"] is None
    assert f["owner_approved"] is False
    assert row["profile_status"] == "not_in_published_sporting_source"


@pytest.mark.parametrize("series,week,q_sections,wc_sections,nominal_gap,ll,se,seeded_wc,exact_band", [
    ("hong_kong_salem_2002", 17, [2, 0, 2, 0], [0, 2, 0, 1], [], 0, 0, [], False),
    ("madrid_clay_1994", 18, [1, 1, 0, 2], [2, 0, 1, 0], [6], 1, 0, [], False),
    ("singapore_march_1992", 18, [1, 2, 1, 0], [0, 3, 0, 0], [], 0, 1, [], True),
    ("bologna_1998", 21, [2, 0, 0, 2], [1, 1, 1, 0], [], 0, 0, [6], True),
])
def test_april_may_additional_main_observations_are_conditional_geometry_only(
    batch, series, week, q_sections, wc_sections, nominal_gap, ll, se, seeded_wc, exact_band
):
    from datetime import date
    from beta_engine.domain.tournaments.fax_reference_bracket_topology import build_knockout_bracket_parts

    row = next(r for r in batch["occurrences"] if r["series_id"] == series)
    e = row["historical_evidence"]
    a = e["april_may_main_draw_followup_2026_11_26"]
    labels = e["main_entry_label_evidence"]
    assert a["prior_fields"]["qualification_size_secondary"] is None
    assert a["prior_fields"]["reported_main_qualifiers"] is None
    assert a["prior_fields"]["reported_main_wild_cards"] is None
    assert a["source_url"] == e["qualification_size_source"] == labels["source_url"]
    assert a["source_url"] in e["source_urls"]
    assert a["reported_qualification_draw_size"] == e["qualification_size_secondary"] == 32
    assert e["main_seeds"] == a["reported_nominal_seeds"] == 8
    assert a["missing_nominal_seed_ranks"] == nominal_gap
    assert a["observed_seed_count"] == 8 - len(nominal_gap)
    assert labels["observed_seed_ranks"] == [n for n in range(1, 9) if n not in nominal_gap]
    assert labels["qualifier_counts_by_section"] == q_sections
    assert labels["wild_card_counts_by_section"] == wc_sections
    assert sum(q_sections) == e["reported_main_qualifiers"] == 4
    assert sum(wc_sections) == e["reported_main_wild_cards"] == 3
    assert labels["observed_lucky_losers"] == ll
    assert labels["observed_special_exempts"] == se
    assert labels["observed_seeded_wild_card_ranks"] == seeded_wc
    assert labels["observed_seeded_wild_cards"] == len(seeded_wc)
    assert labels["unmarked_entrants"] + ll + se + 4 + 3 == 32
    assert all(a[k] is None for k in (
        "actual_qualification_entrants", "actual_qualification_dates",
        "complete_qualification_graph", "reserved_advancement_places"))
    assert e["qualification_entrants"] is e["qualification_start_date"] is e["qualification_end_date"] is None
    assert all(v is None for v in e["entry_policy"].values())
    assert row["profile_status"] == "not_in_published_sporting_source"
    t = next(t for t in batch["knockout_candidate_triage"]["rows"] if t["occurrence_id"] == row["occurrence_id"])
    assert t["exact_secondary_band_candidate"] is exact_band
    g = t["conditional_geometry"]
    main, sections = build_knockout_bracket_parts(
        event_id=row["occurrence_id"], main_entrants=g["main_entrants"],
        qualification_entrants=g["qualification_entrants"], qualifier_spots=g["qualifier_spots"],
        wild_cards=g["wild_cards"], byes=g["main_byes"])
    assert main.bracket_capacity == 32
    assert len(sections) == 4  # LL and SE are not extra assumed qualifier spots.
    assert all(s.bracket_capacity == s.source_entrant_count == 8 for s in sections)
    assert g["potential_matches"] == 31 + sum(s.source_entrant_count - 1 for s in sections) == 59
    assert date.fromisoformat(row["original_start_date"]).isocalendar().week == week
    assert date.fromisoformat(row["original_end_date"]).isocalendar().week == week
    for clock, key in (
        (RunCalendar(52, 1, 1990, 2), "run_positions_offset_1_start_1990"),
        (RunCalendar(52, 37, 1989, 2), "run_positions_offset_37_start_1989"),
    ):
        pos = clock.calendar_to_season(1990, week)
        assert pos is not None
        assert row[key] == [{"season_index": pos.season_index, "season_week": pos.season_week}]


def test_madrid_replacement_and_prague_press_do_not_prove_qualifying_rules(batch):
    rows = {r["series_id"]: r for r in batch["occurrences"]}
    m = rows["madrid_clay_1994"]["historical_evidence"]
    a = m["april_may_main_draw_followup_2026_11_26"]
    press = a["contemporary_replacement_evidence"]
    assert press["main_opening_date"] == rows["madrid_clay_1994"]["original_start_date"]
    assert press["main_opening_publication_date"] == "1990-05-01"
    assert press["replacement_publication_date"] == "1990-05-05"
    assert press["observed_lucky_loser_count"] == m["observed_lucky_losers"] == 1
    assert m["entry_policy"]["lucky_loser_replacement_rule"] is None
    assert a["itf_main_crosscheck"]["observed_qualifiers"] == 4
    sg = rows["singapore_march_1992"]["historical_evidence"]["april_may_main_draw_followup_2026_11_26"]
    assert sg["surface_source_disagreement"]["official_itf_reported_surface"] == "outdoor hard"
    assert sg["surface_source_disagreement"]["secondary_reported_surface"] == "indoor hard"
    bo = rows["bologna_1998"]["historical_evidence"]["april_may_main_draw_followup_2026_11_26"]
    assert bo["qualification_size_series_comparison"]["series_generic_draw_size"] == 16
    assert bo["qualification_size_series_comparison"]["edition_specific_reported_draw_size"] == 32
    p = rows["prague_1999"]["historical_evidence"]
    c = p["contemporary_czech_press_followup_2026_11_26"]
    assert c["printed_page"] == "IV" and c["pdf_page_index"] == 11
    assert c["pdf_page_visually_checked"] is True and c["pdf_sha256"] is None
    assert c["source_url"] in p["source_urls"]
    assert c["reported_singles_champion_prize_usd"] == 21370
    assert c["reported_singles_champion_prize_usd"] != p["reported_prize_money"]
    assert p["qualification_start_date"] is p["qualification_end_date"] is None


@pytest.mark.parametrize("series,week,main,byes,q_size,q_spots,wc,q_per_section,matches,exact_band", [
    ("brisbane", 1, 32, 0, 32, 4, 3, 8, 59, True),
    ("stuttgart_indoor_feb_1995", 8, 32, 0, 32, 4, 3, 8, 59, True),
    ("monte_carlo", 17, 56, 8, 48, 6, 4, 8, 97, True),
    ("munich", 18, 32, 0, 16, 4, 3, 4, 43, True),
    ("hamburg", 19, 56, 8, 28, 7, 5, 4, 76, True),
    ("rome", 20, 64, 0, 32, 8, 5, 4, 87, False),
])
def test_additional_edition_q_sizes_keep_candidate_geometry_and_calendar_separate(
    batch, series, week, main, byes, q_size, q_spots, wc, q_per_section, matches, exact_band
):
    from datetime import date
    from beta_engine.domain.tournaments.fax_reference_bracket_topology import build_knockout_bracket_parts

    row = next(r for r in batch["occurrences"] if r["series_id"] == series)
    e = row["historical_evidence"]
    a = e["additional_qualification_size_followup_2026_11_26"]
    assert a["status"] == "edition_specific_secondary_qualification_size_only_not_actual_draw"
    assert a["prior_fields"]["qualification_size_secondary"] is None
    assert a["source_url"] == e["qualification_size_source"]
    assert a["source_url"] in e["source_urls"]
    assert a["reported_header_main"] == e["main_entrants"] == main
    assert a["reported_header_q"] == e["qualification_size_secondary"] == q_size
    assert e["reported_main_qualifiers"] == q_spots
    assert e["reported_main_wild_cards"] == wc
    assert e["main_byes"] == byes
    assert all(a[k] is None for k in (
        "actual_q_entrants", "actual_q_dates", "complete_q_graph", "reserved_advancement_places"))
    assert e["qualification_entrants"] is e["qualification_start_date"] is e["qualification_end_date"] is None
    assert all(v is None for v in e["entry_policy"].values())
    assert row["profile_status"] == "not_in_published_sporting_source"
    t = next(t for t in batch["knockout_candidate_triage"]["rows"] if t["occurrence_id"] == row["occurrence_id"])
    assert t["exact_secondary_band_candidate"] is exact_band
    g = t["conditional_geometry"]
    m, sections = build_knockout_bracket_parts(
        event_id=row["occurrence_id"], main_entrants=main,
        qualification_entrants=q_size, qualifier_spots=q_spots,
        wild_cards=wc, byes=byes)
    assert m.source_main_entrants == main
    assert m.bracket_capacity == main + byes
    assert m.unplaced_byes == byes
    assert len(sections) == g["sections"] == q_spots
    assert all(s.source_entrant_count == s.bracket_capacity == q_per_section for s in sections)
    assert g["potential_matches"] == matches == main - 1 + sum(
        s.actual_match_count_if_fully_played for s in sections)
    assert date.fromisoformat(row["original_start_date"]).isocalendar().week == week
    assert date.fromisoformat(row["original_end_date"]).isocalendar().week == week
    for clock, key in (
        (RunCalendar(52, 1, 1990, 2), "run_positions_offset_1_start_1990"),
        (RunCalendar(52, 37, 1989, 2), "run_positions_offset_37_start_1989"),
    ):
        pos = clock.calendar_to_season(1990, week)
        assert pos is not None
        assert row[key] == [{"season_index": pos.season_index, "season_week": pos.season_week}]


@pytest.mark.parametrize("series,main,seeds,q_by_section,wc_by_section,ll_by_section,se,missing_seeds", [
    ("hamburg", 56, 16, [1, 2, 3, 1], [3, 1, 1, 0], [1, 1, 0, 0], 0, [8, 12]),
    ("rome", 64, 16, [2, 3, 2, 1], [0, 1, 3, 1], [1, 0, 1, 0], 1, []),
    ("berlin_1991", 32, 8, [3, 1], [1, 2], [2, 0], 0, []),
])
def test_remaining_main_labels_preserve_lucky_loser_and_seed_distinctions(
    batch, series, main, seeds, q_by_section, wc_by_section, ll_by_section, se, missing_seeds
):
    row = next(r for r in batch["occurrences"] if r["series_id"] == series)
    e = row["historical_evidence"]
    labels = e["main_entry_label_evidence"]
    assert labels["source_url"] in e["source_urls"]
    assert labels["status"] == "observed_labels_in_secondary_main_draw_not_guaranteed_policy"
    assert labels["qualifier_counts_by_section"] == q_by_section
    assert labels["wild_card_counts_by_section"] == wc_by_section
    assert labels["lucky_loser_counts_by_section"] == ll_by_section
    assert labels["observed_seed_ranks"] == [n for n in range(1, seeds + 1) if n not in missing_seeds]
    assert e["main_seeds"] == seeds
    assert sum(q_by_section) == labels["observed_qualifiers"] == e["reported_main_qualifiers"]
    assert sum(wc_by_section) == labels["observed_wild_cards"] == e["reported_main_wild_cards"]
    assert sum(ll_by_section) == labels["observed_lucky_losers"] == e["observed_lucky_losers"]
    assert labels.get("observed_special_exempts", 0) == se
    assert main == labels["unmarked_entrants"] + sum(q_by_section) + sum(wc_by_section) + sum(ll_by_section) + se
    assert all(v is None for v in e["entry_policy"].values())
    assert e["qualification_entrants"] is e["qualification_start_date"] is e["qualification_end_date"] is None
    if series == "hamburg":
        a = e["additional_qualification_size_followup_2026_11_26"]["main_label_followup"]
        assert a["observed_seed_count"] == 14 and a["observed_bye_positions"] == e["main_byes"] == 8
        assert a["observed_lucky_loser_in_bye_position"] is e["observed_lucky_loser_in_bye_position"] is True
    elif series == "rome":
        a = e["additional_qualification_size_followup_2026_11_26"]
        assert a["retrospective_entry_crosscheck"]["published_year"] == 2014
        assert a["retrospective_entry_crosscheck"]["source_url"] in e["source_urls"]
        assert [x["outcome"] for x in a["archive_attempts"]] == [
            "content_too_large", "not_accessible", "content_too_large"]
    else:
        assert e["qualification_size_secondary"] is None
    assert row["profile_status"] == "not_in_published_sporting_source"


@pytest.mark.parametrize("series", ["poertschach_2008", "san_marino_2000"])
def test_italian_seed_lists_do_not_turn_omitted_entry_labels_into_zero(batch, series):
    row = next(r for r in batch["occurrences"] if r["series_id"] == series)
    e = row["historical_evidence"]
    a = e["main_draw_seed_followup_2026_11_26"]
    assert a["source_url"] in e["source_urls"]
    assert a["status"] == "secondary_edition_seed_list_only_entry_labels_omitted"
    assert a["nominal_seed_ranks"] == list(range(1, 9))
    assert e["main_seeds"] == 8
    assert e["reported_main_qualifiers"] is e["reported_main_wild_cards"] is None
    assert e["qualification_size_secondary"] is e["qualification_entrants"] is None
    assert all(v is None for v in e["entry_policy"].values())
    assert row["profile_status"] == "not_in_published_sporting_source"
