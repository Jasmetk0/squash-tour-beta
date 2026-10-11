"""Safety checks for one reviewed generator confirmation over a Saved HEAD."""
from types import SimpleNamespace as Obj

import pytest

from beta_engine.api.routers import admin_players


pytestmark = pytest.mark.pr_critical


class FakeRepo:
    def __init__(self):
        self.run = Obj(storage_kind="custom_local", read_only=False)
        self.branch = Obj(run_id="run-a", branch_id="branch-a", read_only=False,
                          status="active", saved_head_revision_id="head-a")
        saved = Obj(revision_id="head-a", run_id="run-a",
                    branch_id="branch-a", payload={"content": {}})
        draft = Obj(base_saved_revision_id="head-a", draft_version=3, status="clean")
        self.state = Obj(run_id="run-a", branch_id="branch-a",
                         saved_revision=saved, working_draft=draft)

    def get_run_container(self, *, run_id):
        return self.run

    def get_run_branch(self, *, branch_id):
        return self.branch

    def get_branch_revision_state(self, *, branch_id):
        return self.state


class FakePackages:
    def __init__(self):
        self.current = Obj(fingerprint="a" * 64)

    def get(self, *, run_id, branch_id):
        return self.current


def validate(repo, packages, **changes):
    args = dict(runtime=Obj(repository=repo), package_service=packages,
                run_id="run-a", branch_id="branch-a", expected_head="head-a",
                expected_draft_version=3, expected_package_fingerprint="a" * 64)
    args.update(changes)
    admin_players._assert_reviewed_generation_context(**args)


def test_exact_context_allows_reviewed_production_generator(monkeypatch):
    repo, packages = FakeRepo(), FakePackages()
    monkeypatch.setattr(admin_players, "load_saved_run_package_state",
                        lambda *_args, **_kwargs: Obj(fingerprint="a" * 64))
    validate(repo, packages)


@pytest.mark.parametrize("change,expected", [
    ("head", "HEAD"),
    ("draft", "HEAD"),
    ("dirty", "HEAD"),
    ("foreign", "HEAD"),
    ("source", "World Package"),
    ("protected", "writable"),
])
def test_stale_or_foreign_context_never_confirms(monkeypatch, change, expected):
    repo, packages = FakeRepo(), FakePackages()
    monkeypatch.setattr(admin_players, "load_saved_run_package_state",
                        lambda *_args, **_kwargs: Obj(fingerprint="a" * 64))
    if change == "head":
        repo.branch.saved_head_revision_id = "new-head"
    elif change == "draft":
        repo.state.working_draft.draft_version = 4
    elif change == "dirty":
        repo.state.working_draft.status = "dirty"
    elif change == "foreign":
        repo.state.saved_revision.branch_id = "foreign"
    elif change == "source":
        packages.current.fingerprint = "b" * 64
    elif change == "protected":
        repo.run.read_only = True
    with pytest.raises(ValueError, match=expected):
        validate(repo, packages)


def test_modified_saved_world_is_not_silently_used(monkeypatch):
    repo, packages = FakeRepo(), FakePackages()
    monkeypatch.setattr(admin_players, "load_saved_run_package_state",
                        lambda *_args, **_kwargs: Obj(fingerprint="c" * 64))
    with pytest.raises(ValueError, match="World Package"):
        validate(repo, packages)
