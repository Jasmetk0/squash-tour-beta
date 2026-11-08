"""Strict arithmetic/provenance contracts plus genuine MatchEngine comparison."""
from __future__ import annotations

from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from beta_engine.application.match_lab_paired_comparison import (
    MAX_COMPARISON_SEEDS,
    MatchLabComparisonRequest,
    MatchLabComparisonSource,
    compare_match_lab_scenarios,
)
from beta_engine.application.match_test_lab_service import MatchTestLabService


pytestmark = pytest.mark.pr_critical


def _arms():
    base = MatchTestLabService().list_built_in_scenarios()[0].scenario
    old_player = base.context.player_a.player
    improved = old_player.model_copy(update={"technique": old_player.technique + 5})
    participant = base.context.player_a.model_copy(update={"player": improved})
    changed_context = base.context.model_copy(update={"player_a": participant})
    candidate = base.model_copy(update={"scenario_id": "increased-technique", "context": changed_context})
    return base, candidate


def _request(base, candidate, seeds=(17, 19)):
    return MatchLabComparisonRequest(
        baseline=MatchLabComparisonSource(scenario=base),
        candidate=MatchLabComparisonSource(scenario=candidate),
        batch_seeds=seeds,
    )


def test_real_kernel_paired_replay_and_exact_same_scenario_identity():
    service = MatchTestLabService()
    base, candidate = _arms()
    request = _request(base, candidate)
    first = compare_match_lab_scenarios(service, request)
    replay = compare_match_lab_scenarios(service, request)
    assert first == replay
    assert first.schema_version == "match_lab_paired_comparison.v1"
    assert first.compared_seeds == (17, 19)
    assert first.summary.compared_seeds == 2
    assert first.summary.winner_flip_count == sum(row.winner_changed for row in first.rows)
    assert first.summary.mean_rally_count_delta == pytest.approx(
        sum(row.rally_count_delta for row in first.rows) / 2, abs=1e-6
    )
    assert all(row.baseline.seed == row.candidate.seed == row.seed for row in first.rows)
    assert first.baseline_source.kind == "inline"
    assert first.candidate_source.kind == "inline"
    assert first.isolated and not first.mutations_performed and not first.source_equivalence_proven
    assert all(row.baseline.rally_count > 0 for row in first.rows)
    assert len(first.request_fingerprint) == 64

    exact = compare_match_lab_scenarios(service, _request(base, base, (17,)))
    assert exact.summary.identical_full_result_fingerprints == 1
    assert exact.summary.winner_flip_count == 0
    assert exact.rows[0].elapsed_seconds_delta == 0
    assert exact.rows[0].rally_count_delta == 0


@pytest.mark.parametrize("field,value,reason", [
    ("match_id", "different", "match_id"),
    ("best_of", 3, "best_of"),
    ("games_to", 9, "games_to"),
    ("win_by", 3, "win_by"),
    ("upset_variance", 0.02, "upset_variance"),
])
def test_incompatible_context_fails_before_any_match(field, value, reason):
    base, candidate = _arms()
    context = candidate.context.model_copy(update={field: value})
    candidate = candidate.model_copy(update={"context": context})

    class NeverSimulate(MatchTestLabService):
        def run(self, request):
            raise AssertionError("no MatchEngine call must occur for incompatible inputs")

    with pytest.raises(ValueError, match=reason):
        compare_match_lab_scenarios(NeverSimulate(), _request(base, candidate))


def test_reversed_player_side_and_retirement_mismatch_are_not_comparable():
    base, candidate = _arms()
    switched = candidate.context.model_copy(
        update={"player_a": candidate.context.player_b, "player_b": candidate.context.player_a}
    )
    with pytest.raises(ValueError, match="same sides"):
        compare_match_lab_scenarios(
            MatchTestLabService(), _request(base, candidate.model_copy(update={"context": switched}))
        )
    from beta_engine.domain.matches import RetirementRule
    changed = candidate.context.model_copy(
        update={"retirement_rule": RetirementRule(
            enabled=True, retired_player_id=base.context.player_a.player.player_id,
            set_number=1,
        )}
    )
    with pytest.raises(ValueError, match="retirement rules"):
        compare_match_lab_scenarios(
            MatchTestLabService(), _request(base, candidate.model_copy(update={"context": changed}))
        )


@pytest.mark.parametrize("seeds", [(), tuple(range(MAX_COMPARISON_SEEDS + 1)),
                                   (1, 1), (True,), (2**63,), (-(2**63) - 1,)])
def test_invalid_paired_seed_contract(seeds):
    base, candidate = _arms()
    with pytest.raises((ValidationError, ValueError)):
        _request(base, candidate, seeds)


def test_source_choice_and_fingerprint_require_reviewed_session():
    base, _ = _arms()
    with pytest.raises(ValidationError):
        MatchLabComparisonSource()
    with pytest.raises(ValidationError):
        MatchLabComparisonSource(scenario=base, session_id="also")
    with pytest.raises(ValidationError):
        MatchLabComparisonSource(session_id="missing-fingerprint")
    with pytest.raises(ValidationError):
        MatchLabComparisonSource(scenario=base, expected_session_fingerprint="0"*64)
    with pytest.raises(ValidationError):
        MatchLabComparisonSource(session_id="s1", expected_session_fingerprint="invalid")


def test_session_pin_mismatch_precedes_real_engine_and_source_evidence_retained():
    base, candidate = _arms()
    session = SimpleNamespace(
        session_id="s1", fingerprint="1"*64, scenario=base,
    )

    class Controlled(MatchTestLabService):
        def __init__(self):
            super().__init__()
            self.runs = 0

        def get_session(self, session_id):
            assert session_id == "s1"
            return session

        def run(self, request):
            self.runs += 1
            return super().run(request)

    svc = Controlled()
    stale = MatchLabComparisonRequest(
        baseline=MatchLabComparisonSource(session_id="s1", expected_session_fingerprint="2"*64),
        candidate=MatchLabComparisonSource(scenario=candidate),
        batch_seeds=(3,),
    )
    with pytest.raises(ValueError, match="changed since comparison"):
        compare_match_lab_scenarios(svc, stale)
    assert svc.runs == 0

    current = stale.model_copy(update={
        "baseline": MatchLabComparisonSource(session_id="s1", expected_session_fingerprint="1"*64)
    })
    result = compare_match_lab_scenarios(svc, current)
    assert result.baseline_source.kind == "saved_session"
    assert result.baseline_source.session_id == "s1"
    assert result.baseline_source.session_fingerprint == "1"*64
    assert svc.runs == 2


def test_invalid_duplicate_or_missing_match_data_fails_closed():
    base, candidate = _arms()
    request = _request(base, candidate, (101, 102))

    class Scramble(MatchTestLabService):
        def run(self, req):
            result = super().run(req)
            if req.scenario.scenario_id == candidate.scenario_id:
                return result.model_copy(update={
                    "results": tuple(reversed(result.results))
                })
            return result

    with pytest.raises(ValueError, match="misaligned seeds"):
        compare_match_lab_scenarios(Scramble(), request)
