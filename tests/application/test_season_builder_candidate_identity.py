from beta_engine.application.season_builder_candidate_identity import (
    build_candidate_identity,
    build_candidate_identity_contract,
    build_candidate_identity_fingerprint,
    build_candidate_identity_overview,
    build_candidate_identity_review_reference,
    build_future_apply_request_validation_preview,
    build_future_apply_reference_contract,
    build_create_only_apply_execution_preflight_preview,
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


def test_build_candidate_identity_overview_safe() -> None:
    summary = {"candidate_count": 2}
    contract = {
        "candidate_count": 2,
        "safe_for_future_reference": True,
        "has_duplicate_candidate_ids": False,
        "has_duplicate_candidate_identity_keys": False,
        "identity_source": "season_template_slot",
        "id_strategy": "sanitized_template_slot_week",
        "key_strategy": "pipe_joined_sanitized_components",
    }
    overview = build_candidate_identity_overview(summary, contract)
    assert overview["available"] is True
    assert overview["safe_for_future_reference"] is True
    assert overview["candidate_count"] == 2
    assert overview["mutation_permitted"] is False


def test_build_candidate_identity_overview_duplicate_unsafe() -> None:
    overview = build_candidate_identity_overview(
        {"candidate_count": 1},
        {
            "candidate_count": 1,
            "safe_for_future_reference": False,
            "has_duplicate_candidate_ids": True,
            "has_duplicate_candidate_identity_keys": False,
            "identity_source": "season_template_slot",
            "id_strategy": "sanitized_template_slot_week",
            "key_strategy": "pipe_joined_sanitized_components",
        },
    )
    assert overview["available"] is True
    assert overview["safe_for_future_reference"] is False
    assert overview["has_duplicate_candidate_ids"] is True
    assert "duplicate" in str(overview["message"]).lower()


def test_build_candidate_identity_overview_no_candidates() -> None:
    overview = build_candidate_identity_overview({"candidate_count": 0}, {"candidate_count": 0})
    assert overview["available"] is False
    assert overview["candidate_count"] == 0
    assert overview["safe_for_future_reference"] is False
    assert "no candidates" in str(overview["message"]).lower()


def test_build_candidate_identity_overview_malformed_values_defaults_safely() -> None:
    overview = build_candidate_identity_overview(
        {"candidate_count": "bad"},
        {
            "candidate_count": -1,
            "safe_for_future_reference": "yes",
            "has_duplicate_candidate_ids": 1,
            "has_duplicate_candidate_identity_keys": None,
            "identity_source": "",
            "id_strategy": "   ",
            "key_strategy": None,
        },
    )
    assert overview["available"] is False
    assert overview["candidate_count"] == 0
    assert overview["safe_for_future_reference"] is False
    assert overview["has_duplicate_candidate_ids"] is False
    assert overview["has_duplicate_candidate_identity_keys"] is False
    assert overview["identity_source"] == "n/a"
    assert overview["id_strategy"] == "n/a"
    assert overview["key_strategy"] == "n/a"


def test_build_candidate_identity_fingerprint_is_deterministic() -> None:
    summary = {
        "candidate_count": 2,
        "candidate_ids": ["cand_a", "cand_b"],
        "candidate_identity_keys": ["k_a", "k_b"],
    }
    contract = {"safe_for_future_reference": True}

    first = build_candidate_identity_fingerprint(
        target_season_label="2035/2036",
        source_type="season_template",
        source_template_id="default_msa_template_preview",
        candidate_identity_summary=summary,
        candidate_identity_contract=contract,
    )
    second = build_candidate_identity_fingerprint(
        target_season_label="2035/2036",
        source_type="season_template",
        source_template_id="default_msa_template_preview",
        candidate_identity_summary=summary,
        candidate_identity_contract=contract,
    )

    assert first == second
    assert isinstance(first["fingerprint"], str) and first["fingerprint"]


def test_build_candidate_identity_fingerprint_changes_with_identity_set() -> None:
    contract = {"safe_for_future_reference": True}
    base = build_candidate_identity_fingerprint(
        target_season_label="2035/2036",
        source_type="season_template",
        source_template_id="default",
        candidate_identity_summary={
            "candidate_count": 1,
            "candidate_ids": ["cand_a"],
            "candidate_identity_keys": ["k_a"],
        },
        candidate_identity_contract=contract,
    )
    changed_ids = build_candidate_identity_fingerprint(
        target_season_label="2035/2036",
        source_type="season_template",
        source_template_id="default",
        candidate_identity_summary={
            "candidate_count": 1,
            "candidate_ids": ["cand_b"],
            "candidate_identity_keys": ["k_a"],
        },
        candidate_identity_contract=contract,
    )
    changed_keys = build_candidate_identity_fingerprint(
        target_season_label="2035/2036",
        source_type="season_template",
        source_template_id="default",
        candidate_identity_summary={
            "candidate_count": 1,
            "candidate_ids": ["cand_a"],
            "candidate_identity_keys": ["k_b"],
        },
        candidate_identity_contract=contract,
    )

    assert base["fingerprint"] != changed_ids["fingerprint"]
    assert base["fingerprint"] != changed_keys["fingerprint"]


def test_build_candidate_identity_fingerprint_handles_malformed_summary_safely() -> None:
    fingerprint = build_candidate_identity_fingerprint(
        target_season_label="2035/2036",
        source_type="season_template",
        source_template_id="default",
        candidate_identity_summary={
            "candidate_count": "bad",
            "candidate_ids": ["cand_a", 1],
            "candidate_identity_keys": "bad",
        },
        candidate_identity_contract={"safe_for_future_reference": "bad"},
    )

    assert fingerprint["candidate_ids"] == []
    assert fingerprint["candidate_identity_keys"] == []
    assert fingerprint["candidate_count"] == 0
    assert fingerprint["safe_for_future_reference"] is False


def test_build_candidate_identity_review_reference_can_reference_when_safe_and_non_empty() -> None:
    review_reference = build_candidate_identity_review_reference(
        {
            "fingerprint": "abc123",
            "candidate_count": 3,
            "safe_for_future_reference": True,
        }
    )

    assert review_reference["reference_id"] == "abc123"
    assert review_reference["can_reference_future_apply"] is True
    assert review_reference["mutation_permitted"] is False


def test_build_candidate_identity_review_reference_cannot_reference_when_empty_or_unsafe() -> None:
    no_candidates = build_candidate_identity_review_reference(
        {
            "fingerprint": "abc123",
            "candidate_count": 0,
            "safe_for_future_reference": True,
        }
    )
    unsafe = build_candidate_identity_review_reference(
        {
            "fingerprint": "abc123",
            "candidate_count": 2,
            "safe_for_future_reference": False,
        }
    )

    assert no_candidates["can_reference_future_apply"] is False
    assert unsafe["can_reference_future_apply"] is False


def test_future_apply_reference_contract_resolved_referenceable_case() -> None:
    contract = build_future_apply_reference_contract(
        candidate_identity_fingerprint={"fingerprint": "fp_abc"},
        candidate_identity_review_reference={
            "reference_type": "candidate_identity_set",
            "reference_id": "fp_abc",
            "can_reference_future_apply": True,
        },
        identity_readiness={"future_command_reference": {"can_reference_future_command": True}},
    )
    assert contract["available"] is True
    assert contract["candidate_identity_set_referenceable"] is True
    assert contract["main_future_command_reference_ready"] is True
    assert contract["apply_execution_enabled"] is False
    assert contract["create_only_apply_required"] is True
    assert contract["read_only"] is True
    assert contract["mutation_permitted"] is False
    assert isinstance(contract["message"], str) and contract["message"]


def test_future_apply_reference_contract_blocked_non_referenceable_case() -> None:
    contract = build_future_apply_reference_contract(
        candidate_identity_fingerprint={"fingerprint": ""},
        candidate_identity_review_reference={
            "reference_type": "candidate_identity_set",
            "reference_id": "",
            "can_reference_future_apply": False,
        },
        identity_readiness={"future_command_reference": {"can_reference_future_command": False}},
    )
    assert contract["available"] is False
    assert contract["candidate_identity_set_referenceable"] is False
    assert contract["main_future_command_reference_ready"] is False
    assert contract["apply_execution_enabled"] is False
    assert contract["create_only_apply_required"] is True
    assert contract["read_only"] is True
    assert contract["mutation_permitted"] is False
    assert isinstance(contract["message"], str) and contract["message"]


def test_future_apply_reference_contract_main_future_command_readiness_parity() -> None:
    ready_contract = build_future_apply_reference_contract(
        candidate_identity_fingerprint={"fingerprint": "fp_ready"},
        candidate_identity_review_reference={
            "reference_type": "candidate_identity_set",
            "reference_id": "fp_ready",
            "can_reference_future_apply": True,
        },
        identity_readiness={"future_command_reference": {"can_reference_future_command": True}},
    )
    blocked_contract = build_future_apply_reference_contract(
        candidate_identity_fingerprint={"fingerprint": "fp_blocked"},
        candidate_identity_review_reference={
            "reference_type": "candidate_identity_set",
            "reference_id": "fp_blocked",
            "can_reference_future_apply": True,
        },
        identity_readiness={"future_command_reference": {"can_reference_future_command": False}},
    )

    assert ready_contract["main_future_command_reference_ready"] is True
    assert blocked_contract["main_future_command_reference_ready"] is False


def test_future_apply_request_validation_preview_matching_referenceable_contract() -> None:
    preview = build_future_apply_request_validation_preview(
        requested_candidate_identity_reference_id="fp_abc",
        requested_candidate_identity_fingerprint="fp_abc",
        requested_candidate_identity_reference_type="candidate_identity_set",
        future_apply_reference_contract={
            "available": True,
            "candidate_identity_reference_id": "fp_abc",
            "candidate_identity_fingerprint": "fp_abc",
            "candidate_identity_reference_type": "candidate_identity_set",
            "candidate_identity_set_referenceable": True,
        },
    )
    assert preview["available"] is True
    assert preview["reference_id_matches"] is True
    assert preview["fingerprint_matches"] is True
    assert preview["reference_type_matches"] is True
    assert preview["contract_referenceable"] is True
    assert preview["apply_execution_enabled"] is False
    assert preview["read_only"] is True
    assert preview["mutation_permitted"] is False


def test_future_apply_request_validation_available_does_not_enable_apply_execution() -> None:
    preview = build_future_apply_request_validation_preview(
        requested_candidate_identity_reference_id="fp_abc",
        requested_candidate_identity_fingerprint="fp_abc",
        requested_candidate_identity_reference_type="candidate_identity_set",
        future_apply_reference_contract={
            "available": True,
            "candidate_identity_reference_id": "fp_abc",
            "candidate_identity_fingerprint": "fp_abc",
            "candidate_identity_reference_type": "candidate_identity_set",
            "candidate_identity_set_referenceable": True,
        },
    )
    assert preview["available"] is True
    assert preview["apply_execution_enabled"] is False
    assert preview["read_only"] is True
    assert preview["mutation_permitted"] is False
    assert "validation-only" in str(preview["message"]).lower()
    assert "does not execute apply" in str(preview["message"]).lower()


def test_future_apply_request_validation_preview_mismatched_values() -> None:
    preview = build_future_apply_request_validation_preview(
        requested_candidate_identity_reference_id="wrong_id",
        requested_candidate_identity_fingerprint="wrong_fp",
        requested_candidate_identity_reference_type="wrong_type",
        future_apply_reference_contract={
            "available": True,
            "candidate_identity_reference_id": "fp_abc",
            "candidate_identity_fingerprint": "fp_abc",
            "candidate_identity_reference_type": "candidate_identity_set",
            "candidate_identity_set_referenceable": True,
        },
    )
    assert preview["available"] is False
    assert preview["reference_id_matches"] is False
    assert preview["fingerprint_matches"] is False
    assert preview["reference_type_matches"] is False
    assert preview["apply_execution_enabled"] is False
    assert preview["read_only"] is True
    assert preview["mutation_permitted"] is False


def test_future_apply_request_validation_preview_missing_request_values() -> None:
    preview = build_future_apply_request_validation_preview(
        requested_candidate_identity_reference_id=None,
        requested_candidate_identity_fingerprint="",
        requested_candidate_identity_reference_type=None,
        future_apply_reference_contract={
            "available": True,
            "candidate_identity_reference_id": "fp_abc",
            "candidate_identity_fingerprint": "fp_abc",
            "candidate_identity_reference_type": "candidate_identity_set",
            "candidate_identity_set_referenceable": True,
        },
    )
    assert preview["available"] is False
    assert preview["requested_candidate_identity_reference_id"] == ""
    assert preview["requested_candidate_identity_fingerprint"] == ""
    assert preview["requested_candidate_identity_reference_type"] == ""
    assert preview["reference_id_matches"] is False
    assert preview["fingerprint_matches"] is False
    assert preview["reference_type_matches"] is False
    assert preview["apply_execution_enabled"] is False
    assert preview["read_only"] is True
    assert preview["mutation_permitted"] is False


def test_future_apply_request_validation_preview_matching_values_blocked_contract() -> None:
    preview = build_future_apply_request_validation_preview(
        requested_candidate_identity_reference_id="fp_abc",
        requested_candidate_identity_fingerprint="fp_abc",
        requested_candidate_identity_reference_type="candidate_identity_set",
        future_apply_reference_contract={
            "available": False,
            "candidate_identity_reference_id": "fp_abc",
            "candidate_identity_fingerprint": "fp_abc",
            "candidate_identity_reference_type": "candidate_identity_set",
            "candidate_identity_set_referenceable": False,
        },
    )
    assert preview["reference_id_matches"] is True
    assert preview["fingerprint_matches"] is True
    assert preview["reference_type_matches"] is True
    assert preview["contract_referenceable"] is False
    assert preview["available"] is False
    assert preview["apply_execution_enabled"] is False
    assert preview["read_only"] is True
    assert preview["mutation_permitted"] is False


def test_future_apply_request_validation_preview_malformed_contract_values() -> None:
    preview = build_future_apply_request_validation_preview(
        requested_candidate_identity_reference_id="fp_abc",
        requested_candidate_identity_fingerprint="fp_abc",
        requested_candidate_identity_reference_type="candidate_identity_set",
        future_apply_reference_contract={
            "available": "yes",
            "candidate_identity_reference_id": 123,
            "candidate_identity_fingerprint": None,
            "candidate_identity_reference_type": {},
        },
    )
    assert preview["expected_candidate_identity_reference_id"] == ""
    assert preview["expected_candidate_identity_fingerprint"] == ""
    assert preview["expected_candidate_identity_reference_type"] == ""
    assert preview["contract_referenceable"] is False
    assert preview["available"] is False


def test_create_only_apply_execution_preflight_preview_all_preconditions_true() -> None:
    preview = build_create_only_apply_execution_preflight_preview(
        future_apply_reference_contract={"available": True},
        future_apply_request_validation_preview={
            "available": True,
            "reference_id_matches": True,
            "fingerprint_matches": True,
            "reference_type_matches": True,
        },
        identity_readiness={"future_command_reference": {"can_reference_future_command": True}},
        target_absent=True,
        create_only_scope_confirmed=True,
        audit_metadata_present=True,
    )
    assert preview["available"] is True
    assert preview["all_known_preconditions_met"] is True
    assert preview["execution_enabled"] is False
    assert preview["can_execute"] is False
    assert preview["read_only"] is True
    assert preview["mutation_permitted"] is False
    message = str(preview["message"]).lower()
    assert "disabled" in message
    assert "preview" in message
    assert "does not execute apply" in message


def test_create_only_apply_execution_preflight_preview_missing_target_absent() -> None:
    preview = build_create_only_apply_execution_preflight_preview(
        future_apply_reference_contract={"available": True},
        future_apply_request_validation_preview={
            "available": True,
            "reference_id_matches": True,
            "fingerprint_matches": True,
            "reference_type_matches": True,
        },
        identity_readiness={"future_command_reference": {"can_reference_future_command": True}},
        target_absent=False,
        create_only_scope_confirmed=True,
        audit_metadata_present=True,
    )
    assert preview["available"] is False
    assert preview["all_known_preconditions_met"] is False
    assert preview["execution_enabled"] is False
    assert preview["can_execute"] is False


def test_create_only_apply_execution_preflight_preview_validation_unavailable() -> None:
    preview = build_create_only_apply_execution_preflight_preview(
        future_apply_reference_contract={"available": True},
        future_apply_request_validation_preview={
            "available": False,
            "reference_id_matches": True,
            "fingerprint_matches": True,
            "reference_type_matches": True,
        },
        identity_readiness={"future_command_reference": {"can_reference_future_command": True}},
        target_absent=True,
        create_only_scope_confirmed=True,
        audit_metadata_present=True,
    )
    assert preview["available"] is False
    assert preview["all_known_preconditions_met"] is False


def test_create_only_apply_execution_preflight_preview_incomplete_identity_match_flags() -> None:
    preview = build_create_only_apply_execution_preflight_preview(
        future_apply_reference_contract={"available": True},
        future_apply_request_validation_preview={
            "available": True,
            "reference_id_matches": True,
            "fingerprint_matches": False,
            "reference_type_matches": True,
        },
        identity_readiness={"future_command_reference": {"can_reference_future_command": True}},
        target_absent=True,
        create_only_scope_confirmed=True,
        audit_metadata_present=True,
    )
    assert preview["candidate_identity_reference_matches"] is False
    assert preview["all_known_preconditions_met"] is False


def test_create_only_apply_execution_preflight_preview_malformed_inputs_default_safely() -> None:
    preview = build_create_only_apply_execution_preflight_preview(
        future_apply_reference_contract={"available": "yes"},
        future_apply_request_validation_preview={
            "available": "yes",
            "reference_id_matches": 1,
            "fingerprint_matches": object(),
            "reference_type_matches": None,
        },
        identity_readiness={"future_command_reference": {"can_reference_future_command": "true"}},
        target_absent="yes",
        create_only_scope_confirmed=1,
        audit_metadata_present=None,
    )
    assert preview["target_absent"] is False
    assert preview["create_only_scope_confirmed"] is False
    assert preview["audit_metadata_present"] is False
    assert preview["future_apply_reference_contract_available"] is False
    assert preview["future_apply_request_validation_available"] is False
    assert preview["candidate_identity_reference_matches"] is False
    assert preview["main_future_command_reference_ready"] is False
    assert preview["available"] is False
    assert preview["execution_enabled"] is False
    assert preview["mutation_permitted"] is False
