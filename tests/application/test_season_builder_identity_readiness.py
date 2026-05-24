from beta_engine.application.season_builder_identity_readiness import build_dry_run_identity_readiness


def test_ready_reference_with_candidate_identity_ok() -> None:
    readiness = build_dry_run_identity_readiness(
        preflight_fingerprint="pf_ok",
        reviewed_diff_id="rd_ok",
        dry_run_result_fingerprint="drf_abc123",
        dry_run_result_id="drr_abc123",
        validation_summary={"status": "clean"},
        plan_readiness={"read_only_plan_available": True},
        candidate_identity_fingerprint={"fingerprint": "cidf_ok"},
        candidate_identity_review_reference={
            "reference_id": "cidref_ok",
            "can_reference_future_apply": True,
            "reference_type": "candidate_identity_set",
        },
    )
    assert readiness["status"] == "ready_reference"
    future = readiness["future_command_reference"]
    assert future["can_reference_future_command"] is True
    assert future["can_reference_candidate_identity_set"] is True
    candidate_item = next(item for item in readiness["items"] if item["area"] == "candidate_identity_review_reference")
    assert candidate_item["status"] == "OK"
    overview = readiness["candidate_identity_readiness_overview"]
    assert overview["available"] is True
    assert overview["can_reference_candidate_identity_set"] is True
    assert overview["candidate_reference_status"] == "OK"
    assert overview["main_future_command_reference_ready"] is True
    assert overview["read_only"] is True
    assert overview["mutation_permitted"] is False
    assert "referenceable" in overview["message"]




def test_candidate_identity_ok_does_not_override_blocked_main_reference() -> None:
    readiness = build_dry_run_identity_readiness(
        preflight_fingerprint="pf_ok",
        reviewed_diff_id="rd_ok",
        dry_run_result_fingerprint="drf_abc123",
        dry_run_result_id="drr_abc123",
        validation_summary={"status": "blocking"},
        plan_readiness={"read_only_plan_available": True},
        candidate_identity_fingerprint={"fingerprint": "cidf_ok"},
        candidate_identity_review_reference={"can_reference_future_apply": True},
    )
    assert readiness["status"] == "blocked_reference"
    future = readiness["future_command_reference"]
    assert future["can_reference_future_command"] is False
    assert future["can_reference_candidate_identity_set"] is True
    assert future["mutation_still_disabled"] is True
    candidate_item = next(item for item in readiness["items"] if item["area"] == "candidate_identity_review_reference")
    assert candidate_item["status"] == "OK"
    overview = readiness["candidate_identity_readiness_overview"]
    assert overview["available"] is False
    assert overview["can_reference_candidate_identity_set"] is True
    assert overview["candidate_reference_status"] == "OK"
    assert overview["main_future_command_reference_ready"] is False
    assert overview["read_only"] is True
    assert overview["mutation_permitted"] is False
    assert "referenceable" in overview["message"]
    mutation_item = next(item for item in readiness["items"] if item["area"] == "mutation_state")
    assert mutation_item["status"] == "Blocked"


def test_blocked_reference_when_validation_blocking() -> None:
    readiness = build_dry_run_identity_readiness(
        preflight_fingerprint="pf_ok",
        reviewed_diff_id="rd_ok",
        dry_run_result_fingerprint="drf_abc123",
        dry_run_result_id="drr_abc123",
        validation_summary={"status": "blocking"},
        plan_readiness={"read_only_plan_available": True},
        candidate_identity_fingerprint={"fingerprint": "cidf_ok"},
        candidate_identity_review_reference={"can_reference_future_apply": True},
    )
    assert readiness["status"] == "blocked_reference"
    future = readiness["future_command_reference"]
    assert future["can_reference_future_command"] is False
    assert future["can_reference_candidate_identity_set"] is True


def test_missing_identity_when_primary_identity_missing() -> None:
    readiness = build_dry_run_identity_readiness(
        preflight_fingerprint="",
        reviewed_diff_id="rd_ok",
        dry_run_result_fingerprint="drf_abc123",
        dry_run_result_id=None,
        validation_summary={"status": "clean"},
        plan_readiness={"read_only_plan_available": True},
        candidate_identity_fingerprint={"fingerprint": "cidf_ok"},
        candidate_identity_review_reference={"can_reference_future_apply": True},
    )
    assert readiness["status"] == "missing_identity"


def test_candidate_identity_blocked_does_not_block_main_reference() -> None:
    readiness = build_dry_run_identity_readiness(
        preflight_fingerprint="pf_ok",
        reviewed_diff_id="rd_ok",
        dry_run_result_fingerprint="drf_abc123",
        dry_run_result_id="drr_abc123",
        validation_summary={"status": "clean"},
        plan_readiness={"read_only_plan_available": True},
        candidate_identity_fingerprint={"fingerprint": "cidf_ok"},
        candidate_identity_review_reference={"can_reference_future_apply": False},
    )
    assert readiness["status"] == "ready_reference"
    future = readiness["future_command_reference"]
    assert future["can_reference_future_command"] is True
    assert future["can_reference_candidate_identity_set"] is False
    candidate_item = next(item for item in readiness["items"] if item["area"] == "candidate_identity_review_reference")
    assert candidate_item["status"] == "BLOCKED"
    overview = readiness["candidate_identity_readiness_overview"]
    assert overview["available"] is False
    assert overview["can_reference_candidate_identity_set"] is False
    assert overview["candidate_reference_status"] == "BLOCKED"
    assert overview["main_future_command_reference_ready"] is True
    assert overview["read_only"] is True
    assert overview["mutation_permitted"] is False
    assert "not referenceable" in overview["message"]
    assert future["mutation_still_disabled"] is True
    mutation_item = next(item for item in readiness["items"] if item["area"] == "mutation_state")
    assert mutation_item["status"] == "Blocked"


def test_malformed_candidate_identity_values_default_safely() -> None:
    readiness = build_dry_run_identity_readiness(
        preflight_fingerprint="pf_ok",
        reviewed_diff_id="rd_ok",
        dry_run_result_fingerprint="drf_abc123",
        dry_run_result_id="drr_abc123",
        validation_summary={"status": "clean"},
        plan_readiness={"read_only_plan_available": True},
        candidate_identity_fingerprint={"fingerprint": "   "},
        candidate_identity_review_reference={
            "reference_id": "",
            "can_reference_future_apply": "yes",
            "reference_type": " ",
        },
    )
    future = readiness["future_command_reference"]
    assert future["candidate_identity_fingerprint"] is None
    assert future["candidate_identity_reference_id"] is None
    assert future["can_reference_candidate_identity_set"] is False
    candidate_item = next(item for item in readiness["items"] if item["area"] == "candidate_identity_review_reference")
    assert candidate_item["status"] == "BLOCKED"
    overview = readiness["candidate_identity_readiness_overview"]
    assert overview["candidate_identity_fingerprint"] is None
    assert overview["candidate_identity_reference_id"] is None
    assert overview["candidate_identity_reference_type"] is None
    assert overview["available"] is False
    assert overview["can_reference_candidate_identity_set"] is False
    assert overview["read_only"] is True
    assert overview["mutation_permitted"] is False
