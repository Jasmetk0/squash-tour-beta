"""Real native HTTP/SQLite review; unsupported historical re-authority stays blocked.

This is evidence of the remaining fork gap, not successful native Branch support.
"""

import json

import pytest

from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.native_fork_source import NativeForkSourceBinding
from beta_engine.domain.run_packages import canonical_hash
from beta_engine.infrastructure.db.models import (
    BranchSavedRevisionModel,
    RunBranchModel,
)
from beta_engine.infrastructure.db.native_fork_source import (
    resolve_native_fork_source_binding,
)
from tests.api.test_calendar_native_birth_week_execution import sign_prospects
from tests.api.test_calendar_opening_knockout_flow import base
from tests.api.test_calendar_population_sporting_checkpoint import restore
from tests.api.test_calendar_tour_flow import (
    command,
    create_edition,
    edition,
    execute,
    inspect,
    save_tour,
    setup,
)
from tests.api.test_native_prospect_source_epochs_http import (
    _review_new_year,
    _source_url,
)
from tests.api.test_player_generation_calendar_gate import _dump
from tests.api.test_saved_revision_branch_review_api import confirmed, preview
from tests.api.test_saved_revision_history_api import ApiServer, _request

pytestmark = pytest.mark.smoke


def saved_bytes(repo, revision_id):
    with repo._session_factory() as session:
        row = session.get(BranchSavedRevisionModel, revision_id)
        return row.payload_json, row.change_summary_json, row.content_hash


def test_native_matched_birth_and_epoch_reviews_preserve_actual_saved_history(tmp_path):
    path = tmp_path / "native-review.db"
    database = f"sqlite:///{path}"
    with ApiServer(database_url=database) as server:
        repo, initial = setup(server, RunCalendar(7, 1, 2030, 3), 4)
        sign_prospects(server, repo, RunCalendar(7, 1, 2030, 3))
        initial = inspect(server)["saved_head_revision_id"]
        snapshots = {}
        immutable_bytes = {}
        bindings = {}

        def check(revision_id, expected_codes):
            before = _dump(path)
            source, review = preview(server, "run", "branch", revision_id)
            assert not review["can_create"]
            assert review["saved_match_count"] >= 3
            assert review["source_revision_branch_id"] == "branch"
            assert expected_codes <= {b["code"] for b in review["blockers"]}
            assert _dump(path) == before
            assert (
                _request(
                    "POST",
                    server.base_url + "/run-containers/run/branches",
                    confirmed(source, review, "blocked-" + revision_id),
                )[0]
                == 409
            )
            assert _dump(path) == before
            current = repo.get_branch_saved_revision(revision_id=revision_id)
            raw_binding = dict(review["native_source_binding"])
            fingerprint = raw_binding.pop("fingerprint")
            binding = NativeForkSourceBinding.model_validate_json(
                json.dumps(raw_binding)
            )
            assert fingerprint == binding.fingerprint
            assert binding.run_id == "run" and binding.source.branch_id == "branch"
            assert binding.source.revision_id == revision_id
            assert binding.source.content_hash == current.content_hash
            assert {c.key: c.content_hash for c in binding.components} == {
                key: canonical_hash(value)
                for key, value in current.payload["content"].items()
            }
            bindings.setdefault(revision_id, binding)
            assert binding == bindings[revision_id]
            with repo._session_factory() as session:
                resolved = resolve_native_fork_source_binding(
                    repo,
                    session,
                    binding=binding,
                    branch=session.get(RunBranchModel, "branch"),
                )
                assert resolved == current
            snapshots.setdefault(revision_id, current)
            immutable_bytes.setdefault(revision_id, saved_bytes(repo, revision_id))
            assert current == snapshots[revision_id]
            assert saved_bytes(repo, revision_id) == immutable_bytes[revision_id]
            return review

        check(initial, {"unsupported_fork_components"})
        execute(
            server, command(inspect(server), "transition", name="admit-before-review")
        )
        born = save_tour(server)["revision_id"]
        check(
            born,
            {
                "native_birth_fork_authority_required",
                "native_health_fork_authority_required",
            },
        )
        # Authenticate a v12 sporting/v4 Tour root containing real post-birth
        # matches, actual applications/draw and the original born player's Entry.
        create_edition(server, "fork-source-tour", size=4)
        for week in (4, 5):
            execute(server, command(inspect(server), "transition", name=f"to-{week}"))
            save_tour(server)
        edition(server, "fork-source-tour", size=4)
        played = inspect(server)["saved_head_revision_id"]
        played_review = check(played, {"native_birth_fork_authority_required"})
        assert played_review["saved_match_count"] == 6
        with repo._session_factory() as session:
            from beta_engine.infrastructure.db.calendar_standalone_match_state import (
                decode_prevalidated_calendar_sources,
            )
            from beta_engine.infrastructure.db.calendar_tour import verify_tour_origins

            _, _, tour = decode_prevalidated_calendar_sources(
                snapshots[played].payload,
                run_id="run",
                branch_id="branch",
            )
            # These origins exist in the live Branch. They still cannot be used
            # when a historical boundary excludes them.
            with pytest.raises(ValueError, match="missing or foreign"):
                verify_tour_origins(session, tour, _reachable_revision_ids=frozenset())
        url, request, review = _review_new_year(server, season=1)
        status, materialized = _request(
            "POST",
            url + "/materialize",
            {
                "request": request,
                "expected_saved_head": review["saved_head_revision_id"],
                "expected_review_fingerprint": review["review_fingerprint"],
                "explicit_confirmation": True,
                "audit_label": "Admin",
                "audit_reason": "Real future source for Branch boundary validation",
            },
        )
        assert status == 201, materialized
        status, source_review = _request("GET", _source_url(server) + "/preview")
        assert status == 200 and source_review["can_save"], source_review
        status, saved = _request(
            "POST",
            _source_url(server),
            {
                "expected_draft_version": source_review["draft_version"],
                "expected_run_prospect_source_fingerprint": source_review[
                    "run_prospect_source_fingerprint"
                ],
                "expected_saved_head_revision_id": source_review[
                    "saved_head_revision_id"
                ],
            },
        )
        assert status == 201, saved
        epoch = saved["saved_revision"]["revision_id"]
        assert (
            check(epoch, {"native_birth_fork_authority_required"})[
                "prospect_source_schema"
            ]
            == "run_prospect_source_epochs.v2"
        )
        # Earlier source revisions remain reachable and have exactly their old bytes.
        check(initial, {"unsupported_fork_components"})
        for revision_id, snapshot in snapshots.items():
            assert repo.get_branch_saved_revision(revision_id=revision_id) == snapshot
            assert saved_bytes(repo, revision_id) == immutable_bytes[revision_id]
        # A recomputed, self-consistent reference hash never authorizes changed
        # component bytes, another revision, or a foreign original owner.
        binding = bindings[born]
        with repo._session_factory() as session:
            lineage = repo._validated_branch_revision_lineage_in_session(
                session=session,
                branch=session.get(RunBranchModel, "branch"),
                payload_revision_ids=frozenset(),
            )
            empty_origin = lineage[-1].revision_id
        status, unrelated = _request(
            "POST",
            server.base_url + "/run-containers/run/branches",
            {"source_branch_id": "branch", "source_saved_revision_id": empty_origin},
        )
        assert status == 201, unrelated
        with (
            repo._session_factory() as session,
            pytest.raises(ValueError, match="not reachable"),
        ):
            resolve_native_fork_source_binding(
                repo,
                session,
                binding=binding,
                branch=session.get(RunBranchModel, unrelated["branch_id"]),
            )
        for altered in (
            binding.model_copy(
                update={
                    "source": binding.source.model_copy(
                        update={
                            "branch_id": "another-owner",
                        }
                    )
                }
            ),
            binding.model_copy(
                update={
                    "source": binding.source.model_copy(
                        update={
                            "revision_id": initial,
                        }
                    )
                }
            ),
            binding.model_copy(
                update={
                    "components": (
                        binding.components[0].model_copy(
                            update={"content_hash": "0" * 64},
                        ),
                        *binding.components[1:],
                    )
                }
            ),
        ):
            assert altered.fingerprint != binding.fingerprint
            with repo._session_factory() as session, pytest.raises(ValueError):
                resolve_native_fork_source_binding(
                    repo,
                    session,
                    binding=altered,
                    branch=session.get(RunBranchModel, "branch"),
                )
        # Source rows are checked afresh even after a successful cached review.
        # Corrupt a real execution origin, leaving its old hash column intact.
        origin_id = binding.historical_sources[0].revision_id
        with repo._session_factory.begin() as session:
            row = session.get(BranchSavedRevisionModel, origin_id)
            original_summary = row.change_summary_json
            row.change_summary_json = json.dumps({"tampered_source": True})
        try:
            before = _dump(path)
            assert (
                _request(
                    "POST",
                    server.base_url + "/run-containers/run/branches/preview",
                    {"source_branch_id": "branch", "source_saved_revision_id": born},
                )[0]
                == 409
            )
            assert _dump(path) == before
        finally:
            with repo._session_factory.begin() as session:
                session.get(
                    BranchSavedRevisionModel, origin_id
                ).change_summary_json = original_summary
    with ApiServer(database_url=database) as restarted:
        repo = restarted.app.state.runtime.repository
        for revision_id, snapshot in snapshots.items():
            assert repo.get_branch_saved_revision(revision_id=revision_id) == snapshot
            assert saved_bytes(repo, revision_id) == immutable_bytes[revision_id]
            before = _dump(path)
            assert not preview(restarted, "run", "branch", revision_id)[1]["can_create"]
            assert _dump(path) == before
            with repo._session_factory() as session:
                assert (
                    resolve_native_fork_source_binding(
                        repo,
                        session,
                        binding=bindings[revision_id],
                        branch=session.get(RunBranchModel, "branch"),
                    )
                    == snapshot
                )
        # Original genuine match remains replayable after source epoch changes.
        code, replay = _request("GET", base(restarted) + "/world-owner/replay")
        assert code == 200 and replay["exact_replay"], replay
        restore(restarted, initial)
        assert inspect(restarted)["state"]["week"]["week"] == 2
        restore(restarted, epoch)
        assert inspect(restarted)["state"]["week"]["week"] == 5
