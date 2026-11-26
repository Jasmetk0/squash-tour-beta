"""Opt-in real ATP 2019 Setup acceptance with externally reviewed PDF bytes.

No substitute hashes, no committed raw PDFs, no production publication.
See docs/ATP_2019_FIRST_RESEARCH_BATCH.md for the input contract.
"""
import hashlib
import json
import os
from pathlib import Path

import pytest

from beta_engine.application.atp_historical_calendar_adapter import ATPHistoricalCalendarAdapter
from beta_engine.application.atp_sporting_package_adapter import build_atp_sporting_package
from beta_engine.domain.tournaments.atp_knockout_profile import ATPKnockoutProfile
from tests.api.test_atp_saved_run_week_preview_api import _make_run
from tests.api.test_saved_revision_history_api import ApiServer, _request

ROOT = Path(__file__).resolve().parents[2] / "config/reference_packages/atp_tour_1990_2026"
KEY = "atp_2019_cordoba"


def _reviewed_candidate(directory):
    rows = json.loads((ROOT / "research_2019/profile_candidates.json").read_text(encoding="utf-8"))
    profile = next(c["profile"] for c in rows["candidates"] if c["occurrence_id"] == KEY)
    review = json.loads((directory / "review.json").read_text(encoding="utf-8"))
    if review.get("occurrence_id") != KEY or not review.get("reviewer"):
        raise ValueError("Explicit edition-specific review is required")
    required = {"identity", "main_geometry", "qualification_geometry", "point_rules", "qualification_dates"}
    if set(review.get("reviewed_fields", [])) != required:
        raise ValueError("Complete explicit sporting evidence review is required")
    sources = review["sources"]
    if set(sources) != set(profile["source_urls"]):
        raise ValueError("Exact candidate original URLs required")
    hashes = {}
    for url in profile["source_urls"]:
        proof = sources[url]
        filename = url.rsplit("/", 1)[-1]
        raw = (directory / filename).read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        if (not raw.startswith(b"%PDF-") or b"%%EOF" not in raw[-4096:]
                or proof["sha256"] != digest or proof["bytes"] != len(raw)
                or not proof.get("retrieved_at") or not proof.get("review_notes")):
            raise ValueError(f"Original PDF/review digest mismatch: {filename}")
        hashes[url] = digest
    profile["source_pdf_sha256"] = hashes
    return ATPKnockoutProfile.model_validate_json(json.dumps(profile)).model_dump(mode="json")


@pytest.mark.parametrize(("offset", "start", "q_week", "main_week"),
                         [(1, 2019, 5, 6), (37, 2018, 21, 22)])
def test_cordoba_reviewed_originals_setup_save_schedule_and_reopen(tmp_path, monkeypatch, offset, start, q_week, main_week):
    folder = os.environ.get("ATP_2019_CORDOBA_REVIEW_DIR")
    if not folder:
        pytest.skip("No externally reviewed 2019 original PDF inputs; no import evidence")
    profile = _reviewed_candidate(Path(folder))
    source_path = ROOT / "squash_sporting_profiles_v1.json"
    old_bytes = source_path.read_bytes()
    raw = json.loads(old_bytes)
    assert raw["source_version"] == 6
    assert len(raw["profiles"]) == 23
    assert KEY not in {p["occurrence_id"] for p in raw["profiles"]}
    old_package = build_atp_sporting_package(ROOT)
    raw["source_version"] = 7
    raw["profiles"].append(profile)
    (tmp_path / source_path.name).write_text(json.dumps(raw), encoding="utf-8")
    candidate_package = build_atp_sporting_package(tmp_path)
    assert len(candidate_package.entities) == len(old_package.entities) + 1
    assert tuple(e.fingerprint for e in candidate_package.entities[:-1]) == tuple(
        e.fingerprint for e in old_package.entities)
    base_document = ATPHistoricalCalendarAdapter().build_document()
    assert base_document.source_version == 7
    document = base_document.model_copy(update={"source_version": 8,
        "children": (*base_document.children[:-1], candidate_package)})
    assert source_path.read_bytes() == old_bytes

    database = f"sqlite:///{tmp_path / 'cordoba-reviewed.db'}"
    with ApiServer(database_url=database) as server:
        r, b = _make_run(server, name="Cordoba reviewed source", start=start, count=2, offset=offset)
        root_path = f"/admin/runs/{r}/branches/{b}"
        working_path = f"/run-containers/{r}/branches/{b}/working-draft"
        root, working = server.base_url + root_path, server.base_url + working_path
        source = root + "/packages/source-atp-reference-calendar"
        with monkeypatch.context() as isolated:
            isolated.setattr(ATPHistoricalCalendarAdapter, "build_document", lambda self: document)
            code, review = _request("POST", source + "/preview", {})
            assert code == 200, review
            code, applied = _request("POST", source + "/confirm", {
                "command_id": "copy-reviewed-cordoba",
                "expected_head_revision_id": review["saved_head_revision_id"],
                "expected_draft_version": review["draft_version"],
                "expected_state_fingerprint": review["current_state_fingerprint"],
                "expected_preview_fingerprint": review["preview_fingerprint"],
                "conflict_resolutions": {},
            })
            assert code == 200, applied
            code, saved = _request("POST", working + "/save",
                                   {"expected_draft_version": applied["draft_version"]})
            assert code == 201, saved
        catalog_path = root_path + "/calendar-tour/atp-source-editions"
        code, catalog = _request("GET", server.base_url + catalog_path)
        assert code == 200, catalog
        entry = next(e for e in catalog["entries"] if e["profile"]["occurrence_id"] == KEY)
        assert entry["profile"] == profile
        assert entry["qualification_calendar_projection"]["run_weeks"] == [
            {"season_index": 0, "season_week": q_week}]
        assert entry["calendar_projection"]["run_weeks"][0]["season_week"] == main_week
        calendar = {"schema_version": "run_calendar.v1", "weeks_per_year": 52,
                    "season_start_year_week": offset, "start_year": start, "season_count": 2}

        def pos(w, s):
            return {"week": {"calendar": calendar, "season_index": 0, "week": w}, "slot": s}

        request = {"expected_saved_head": catalog["saved_head_revision_id"],
                   "expected_profile_fingerprint": entry["profile_fingerprint"],
                   "schedule": {"calendar": calendar, "qualification": [pos(q_week, 1), pos(q_week, 2)],
                                "main": [pos(main_week, n) for n in range(1, 6)]}}
        schedule_path = catalog_path + f"/{KEY}/schedule-preview"
        before = _request("GET", working)
        code, preview = _request("POST", server.base_url + schedule_path, request)
        assert code == 200, preview
        assert preview["actual_match_count"] == 39
        assert preview["qualification_dates_verified"] is True
        assert preview["sporting_execution_ready"] is preview["run_mutated"] is False
        wrong = {**request, "schedule": {**request["schedule"],
                 "qualification": [pos(q_week - 1, 1), pos(q_week - 1, 2)]}}
        assert _request("POST", server.base_url + schedule_path, wrong)[0] == 409
        assert _request("GET", working) == before
        repo = server.app.state.runtime.repository
        revision = repo.get_branch_saved_revision(
            revision_id=repo.get_branch_revision_state(branch_id=b).saved_head_revision_id)
        revision_id, saved_hash = revision.revision_id, revision.content_hash
        saved_body = json.dumps(revision.payload, sort_keys=True)

    def unavailable(*args, **kwargs):
        raise AssertionError("Cold Saved read must not consult current source defaults")

    monkeypatch.setattr(ATPHistoricalCalendarAdapter, "build_document", unavailable)
    with ApiServer(database_url=database) as reopened:
        assert _request("GET", reopened.base_url + catalog_path) == (200, catalog)
        assert _request("POST", reopened.base_url + schedule_path, request) == (200, preview)
        assert _request("GET", reopened.base_url + working_path) == before
        revision = reopened.app.state.runtime.repository.get_branch_saved_revision(revision_id=revision_id)
        assert revision.content_hash == saved_hash
        assert json.dumps(revision.payload, sort_keys=True) == saved_body
    assert source_path.read_bytes() == old_bytes
