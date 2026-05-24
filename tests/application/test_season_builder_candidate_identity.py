from beta_engine.application.season_builder_candidate_identity import (
    build_candidate_identity,
    build_candidate_identity_contract,
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


def test_build_candidate_identity_contract_safe_when_non_empty_without_duplicates() -> None:
    summary = {
        "candidate_count": 2,
        "duplicate_candidate_ids": [],
        "duplicate_candidate_identity_keys": [],
    }
    contract = build_candidate_identity_contract(summary)
    assert contract["safe_for_future_reference"] is True
    assert contract["has_duplicate_candidate_ids"] is False
    assert contract["has_duplicate_candidate_identity_keys"] is False
    assert contract["key_components"] == [
        "target_season",
        "source_type",
        "source_template_id",
        "source_slot_id",
        "season_week_start",
        "event_name",
        "category",
        "source_template_ref",
    ]
    assert contract["read_only"] is True
    assert contract["mutation_permitted"] is False


def test_build_candidate_identity_contract_unsafe_when_duplicates_exist() -> None:
    summary = {
        "candidate_count": 2,
        "duplicate_candidate_ids": ["cand_a"],
        "duplicate_candidate_identity_keys": [],
    }
    contract = build_candidate_identity_contract(summary)
    assert contract["safe_for_future_reference"] is False
    assert contract["has_duplicate_candidate_ids"] is True
    assert "duplicates" in str(contract["message"]).lower()


def test_build_candidate_identity_contract_unsafe_when_no_candidates() -> None:
    summary = build_candidate_identity_summary([])
    contract = build_candidate_identity_contract(summary)
    assert contract["safe_for_future_reference"] is False
    assert "no candidates" in str(contract["message"]).lower()


def test_candidate_identity_contract_is_read_only_and_not_permission_grant() -> None:
    summary = {
        "candidate_count": 1,
        "duplicate_candidate_ids": [],
        "duplicate_candidate_identity_keys": [],
    }
    contract = build_candidate_identity_contract(summary)

    # safe_for_future_reference means IDs can be referenced later, not that mutation is allowed.
    assert contract["safe_for_future_reference"] is True
    assert contract["read_only"] is True
    assert contract["mutation_permitted"] is False
    assert "safe for future reference" in str(contract["message"]).lower()


def test_build_candidate_identity_contract_message_branches_are_stable() -> None:
    safe_contract = build_candidate_identity_contract(
        {
            "candidate_count": 1,
            "duplicate_candidate_ids": [],
            "duplicate_candidate_identity_keys": [],
        }
    )
    duplicate_contract = build_candidate_identity_contract(
        {
            "candidate_count": 2,
            "duplicate_candidate_ids": ["cand_a"],
            "duplicate_candidate_identity_keys": [],
        }
    )
    no_candidates_contract = build_candidate_identity_contract(
        {
            "candidate_count": 0,
            "duplicate_candidate_ids": [],
            "duplicate_candidate_identity_keys": [],
        }
    )

    assert "safe for future reference" in str(safe_contract["message"]).lower()
    assert "duplicates" in str(duplicate_contract["message"]).lower()
    assert "no candidates" in str(no_candidates_contract["message"]).lower()
