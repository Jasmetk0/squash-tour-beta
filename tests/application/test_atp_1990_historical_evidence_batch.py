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
    assert all(row["historical_evidence"]["main_draw_capacity"] == 32
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
    assert rows["maceio_1992"]["qualifier_spots"] == 4
    for name, entrants, seeds, byes, q in (
        ("toronto_indoor_1990", 56, 16, 8, 28),
        ("philadelphia_1998", 48, 16, 16, 24),
        ("rio", 48, 16, 16, 24),
    ):
        evidence = rows[name]
        assert evidence["main_draw_capacity"] == entrants
        assert evidence["main_bracket_slots"] == 64
        assert evidence["main_seeds"] == seeds
        assert evidence["main_byes"] == byes
        assert evidence["qualification_size_secondary"] == q
    for evidence in rows.values():
        if evidence.get("format") == "round_robin_then_knockout":
            assert evidence["main_bracket_slots"] is None
            assert evidence["main_byes"] is None
        else:
            assert evidence["main_draw_capacity"] + evidence["main_byes"] == evidence["main_bracket_slots"]
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
        assert (evidence["main_draw_capacity"], evidence["main_seeds"],
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
        assert evidence["qualifier_spots"] == q
        assert evidence["wild_cards"] == wc
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
        n = e["main_draw_capacity"] if e else a["reported_main_entrants"]
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
    assert rows["hong_kong_salem_2002"]["historical_evidence"]["wild_cards"] is None
    assert rows["hong_kong_salem_2002"]["historical_evidence"]["observed_wild_cards_minimum"] == 1
    assert rows["hamburg"]["historical_evidence"]["alternate_event_end_date"] == "1990-05-14"
    assert rows["hamburg"]["original_end_date"] == "1990-05-13"
    for name, q, wc in (("hong_kong", 4, 3), ("monte_carlo", 6, 4),
                        ("umag", 4, 3), ("florence_1994", 4, 3),
                        ("s_hertogenbosch", 4, 2)):
        e = rows[name]["historical_evidence"]
        assert (e["qualifier_spots"], e["wild_cards"]) == (q, wc)
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
    assert sum(e["qualifier_spots"] is not None for e in rows.values()) == summary["reported_q_spot_count_rows"]
    assert sum(e["wild_cards"] is not None for e in rows.values()) == summary["reported_wc_count_rows"]
    assert sum("main_draw_source_disagreement" in e for e in rows.values()) == summary["main_draw_disagreement_rows"]
    for series_id in ("bordeaux_1995", "cologne_1992_clay", "basel",
                      "brisbane_autumn_1992", "palermo", "athens_1994",
                      "toulouse_2000", "berlin_1991", "tel_aviv_1996",
                      "montpellier", "vienna", "sao_paulo_1993"):
        e = rows[series_id]
        assert e["main_draw_source_disagreement"]["annual_summary_entrants"] == 28
        assert e["main_draw_capacity"] == 32
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
    assert rows["stuttgart"]["qualifier_spots"] == 5
    assert rows["atlanta"]["qualifier_spots"] == 7
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
    assert (e["main_draw_capacity"], e["main_bracket_slots"],
            e["main_seeds"], e["main_byes"]) == (28, 32, 8, 4)
    assert e["bye_seed_ranks"] == [1, 2, 3, 4]
    assert (e["qualifier_spots"], e["wild_cards"],
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
        assert labels["observed_qualifiers"] == e["qualifier_spots"] == 4
        assert labels["observed_wild_cards"] == e["wild_cards"] == 3
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
        assert labels["observed_qualifiers"] == e["qualifier_spots"] == q
        assert labels["observed_wild_cards"] == e["wild_cards"] == wc
        assert labels["source_url"] in e["source_urls"]
        assert labels["status"] == "observed_labels_in_secondary_main_draw_not_guaranteed_policy"
        assert q + wc <= e["main_draw_capacity"]
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
