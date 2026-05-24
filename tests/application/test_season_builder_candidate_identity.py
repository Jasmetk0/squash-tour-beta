from beta_engine.application.season_builder_candidate_identity import (
    build_candidate_identity,
    build_candidate_identity_summary,
    sanitize_candidate_identity_part,
)


def test_sanitize_candidate_identity_part_cases() -> None:
    assert sanitize_candidate_identity_part(None) == "unknown"
    assert sanitize_candidate_identity_part("") == "unknown"
    assert sanitize_candidate_identity_part("  ") == "unknown"
    assert sanitize_candidate_identity_part("Default MSA Template Preview") == "default_msa_template_preview"
    assert sanitize_candidate_identity_part("Slot-01 WT Gold!") == "slot_01_wt_gold"
    assert sanitize_candidate_identity_part("///") == "unknown"


def test_build_candidate_identity_is_deterministic_and_sanitized() -> None:
    kwargs = {
        "source_template_id": "Default MSA Template Preview",
        "source_slot_id": "Slot-01 WT Gold!",
        "season_week_start": 7,
        "target_season_label": "2002 / 2003",
        "source_type": "Season Template",
        "event_name": "World's Event #1",
        "category": "WT Gold+",
        "source_template_ref": "Ref/Alpha",
    }
    candidate_id_a, candidate_identity_key_a = build_candidate_identity(**kwargs)
    candidate_id_b, candidate_identity_key_b = build_candidate_identity(**kwargs)

    assert candidate_id_a == candidate_id_b
    assert candidate_identity_key_a == candidate_identity_key_b
    assert candidate_id_a.startswith("cand_")
    assert " " not in candidate_id_a
    assert " " not in candidate_identity_key_a
    for key_name in [
        "target_season=",
        "source_type=",
        "source_template_id=",
        "source_slot_id=",
        "season_week_start=",
        "event_name=",
        "category=",
        "source_template_ref=",
    ]:
        assert key_name in candidate_identity_key_a


def test_build_candidate_identity_changes_with_meaningful_inputs() -> None:
    baseline = build_candidate_identity(
        source_template_id="default_msa_template_preview",
        source_slot_id="slot_1",
        season_week_start=3,
        target_season_label="2002/2003",
        source_type="season_template",
        event_name="World A",
        category="PLATINUM",
        source_template_ref="wt_a",
    )
    changed_slot = build_candidate_identity(
        source_template_id="default_msa_template_preview",
        source_slot_id="slot_2",
        season_week_start=3,
        target_season_label="2002/2003",
        source_type="season_template",
        event_name="World A",
        category="PLATINUM",
        source_template_ref="wt_a",
    )
    changed_week = build_candidate_identity(
        source_template_id="default_msa_template_preview",
        source_slot_id="slot_1",
        season_week_start=4,
        target_season_label="2002/2003",
        source_type="season_template",
        event_name="World A",
        category="PLATINUM",
        source_template_ref="wt_a",
    )

    assert baseline != changed_slot
    assert baseline != changed_week


def test_build_candidate_identity_summary_empty() -> None:
    summary = build_candidate_identity_summary([])
    assert summary["candidate_count"] == 0
    assert summary["candidate_ids"] == []
    assert summary["candidate_identity_keys"] == []
    assert summary["duplicate_candidate_ids"] == []
    assert summary["duplicate_candidate_identity_keys"] == []
    assert summary["read_only"] is True
    assert summary["mutation_permitted"] is False


def test_build_candidate_identity_summary_detects_duplicates_once_sorted() -> None:
    summary = build_candidate_identity_summary(
        [
            {"candidate_id": "cand_b", "candidate_identity_key": "key_z"},
            {"candidate_id": "cand_a", "candidate_identity_key": "key_a"},
            {"candidate_id": "cand_b", "candidate_identity_key": "key_z"},
            {"candidate_id": "cand_a", "candidate_identity_key": "key_a"},
            {"candidate_id": "", "candidate_identity_key": ""},
        ]
    )
    assert summary["duplicate_candidate_ids"] == ["cand_a", "cand_b"]
    assert summary["duplicate_candidate_identity_keys"] == ["key_a", "key_z"]
