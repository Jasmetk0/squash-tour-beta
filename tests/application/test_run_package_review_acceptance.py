from __future__ import annotations

import json
from collections.abc import Iterator

import pytest

from beta_engine.application.run_container_creation_service import (
    RunContainerCreationService,
)
from beta_engine.application.run_branch_creation_service import RunBranchCreationService
from beta_engine.application.run_package_service import (
    RunPackageConflictError,
    RunPackageService,
)
from beta_engine.application.run_saved_revision_restore_service import (
    RunSavedRevisionRestoreService,
)
from beta_engine.application.run_working_draft_service import RunWorkingDraftService
from beta_engine.domain.run_containers import (
    ARCHIVED_RUN_STATUS,
    COMPLETED_RUN_STATUS,
    WORKING_RUN_STATUS,
)
from beta_engine.domain.run_packages import (
    CanonicalPackageDocument,
    PackageEntity,
    PackageType,
    RunPackageEntity,
    RunPackageState,
    SourceReference,
)
from beta_engine.infrastructure.db import (
    DatabaseSettings,
    SimulationPersistenceRepository,
    create_session_factory,
    create_sqlite_engine,
)
from beta_engine.infrastructure.db.models import (
    RunContainerModel,
    RunPackageApplicationReceiptModel,
    RunPackageIdentityAllocatorModel,
)
from beta_engine.infrastructure.db.run_package_state import load_saved_run_package_state


def _ids(*values: str):
    stream: Iterator[str] = iter(values)
    return lambda _: next(stream)


def _repo(url: str = "sqlite://"):
    engine = create_sqlite_engine(DatabaseSettings(url=url))
    repository = SimulationPersistenceRepository(
        engine=engine, session_factory=create_session_factory(engine)
    )
    repository.bootstrap_schema()
    return repository


def _empty(repository):
    RunContainerCreationService(
        repository, _ids("run", "branch", "r0", "draft")
    ).create_empty_run(display_name="Review")


def _entity(
    identity: str, value: object, *, kind="kind", schema=1, refs=(), valid=True
):
    return PackageEntity(
        source_entity_id=identity,
        entity_kind=kind,
        entity_schema_version=schema,
        scope="scope",
        payload={"value": value},
        references=refs,
        valid=valid,
    )


def _doc(
    package_id="p",
    version=1,
    *,
    kind=PackageType.WORLD,
    entities=(),
    parent=None,
    children=(),
):
    return CanonicalPackageDocument(
        package_id=package_id,
        source_version=version,
        package_type=kind,
        explicit_scope=tuple(e.source_entity_id for e in entities),
        entities=entities,
        children=children,
        parent_source_fingerprint=parent,
    )


def _confirm(
    service,
    document,
    *,
    command,
    draft,
    state,
    head="r0",
    branch="branch",
    selected=None,
    resolutions=None,
    fault=None,
):
    preview = service.preview(run_id="run", branch_id=branch, document=document)
    return service.confirm(
        run_id="run",
        branch_id=branch,
        document=document,
        command_id=command,
        expected_head_revision_id=head,
        expected_draft_version=draft,
        expected_state_fingerprint=state,
        expected_preview_fingerprint=preview.preview_fingerprint,
        selected_entities=selected,
        conflict_resolutions=resolutions,
        fault_at=fault,
    )


@pytest.mark.pr_critical
def test_valid_setup_persists_identity_frozen_children_and_truthful_selection():
    repository = _repo()
    _empty(repository)
    service = RunPackageService(repository)
    world = _doc("world", entities=(_entity("w", 1),))
    category = _doc("category", kind=PackageType.CATEGORY, entities=(_entity("c", 3),))
    invalid = _doc(
        "calendar",
        kind=PackageType.CALENDAR,
        entities=(_entity("bad", 0, valid=False),),
    )
    setup = _doc("setup", kind=PackageType.SETUP, children=(world, category, invalid))
    result = _confirm(
        service,
        setup,
        command="setup",
        draft=0,
        state=None,
        selected=("world/w", "category/c"),
    )
    setup_version = next(
        v for v in result.state.package_versions if v.package_id == "setup"
    )
    assert setup_version.package_type == PackageType.SETUP
    assert setup_version.source_fingerprint == setup.source_fingerprint
    assert setup_version.applied_entity_ids == ("category/c", "world/w")
    assert len(setup_version.frozen_child_versions) == 3
    assert {e.source_package_id for e in result.state.entities} == {"world", "category"}


@pytest.mark.pr_critical
def test_package_id_type_is_immutable_and_selection_labels_are_strict():
    repository = _repo()
    _empty(repository)
    service = RunPackageService(repository)
    first = _doc(entities=(_entity("a", 1),))
    applied = _confirm(service, first, command="one", draft=0, state=None)
    changed_type = _doc(
        version=2,
        kind=PackageType.CATEGORY,
        entities=(_entity("a", 2),),
        parent=first.source_fingerprint,
    )
    with pytest.raises(RunPackageConflictError):
        _confirm(
            service,
            changed_type,
            command="type",
            draft=1,
            state=applied.state.fingerprint,
        )
    empty_repo = _repo()
    _empty(empty_repo)
    empty_service = RunPackageService(empty_repo)
    empty = _confirm(
        empty_service, first, command="empty", draft=0, state=None, selected=()
    )
    assert empty.state is None
    assert (
        empty_repo.get_viewer_branch_working_draft(
            run_id="run", branch_id="branch"
        ).draft_version
        == 0
    )
    with pytest.raises(RunPackageConflictError):
        _confirm(
            empty_service,
            first,
            command="unknown",
            draft=0,
            state=None,
            selected=("no/such",),
        )
    with pytest.raises(RunPackageConflictError):
        _confirm(
            empty_service,
            first,
            command="resolution",
            draft=0,
            state=None,
            resolutions={"p/a": "keep_run"},
        )


@pytest.mark.pr_critical
@pytest.mark.parametrize(
    "target_kind,target_schema,compatible",
    [("category", 2, True), ("series", 2, False), ("category", 1, False)],
)
def test_exact_reference_resolution_checks_kind_and_schema(
    target_kind, target_schema, compatible
):
    repository = _repo()
    _empty(repository)
    service = RunPackageService(repository)
    ref = SourceReference(
        source_package_id="target",
        source_entity_id="x",
        expected_entity_kind="category",
        minimum_schema_version=2,
    )
    source = _doc(
        "source",
        kind=PackageType.SERIES,
        entities=(_entity("s", "S", kind="series", refs=(ref,)),),
    )
    first = _confirm(service, source, command="source", draft=0, state=None)
    target = _doc(
        "target",
        kind=PackageType.CATEGORY,
        entities=(_entity("x", "X", kind=target_kind, schema=target_schema),),
    )
    preview = service.preview(run_id="run", branch_id="branch", document=target)
    assert bool(preview.automatically_resolvable) is compatible
    assert bool(
        [c for c in preview.conflicts if c.endswith("incompatible_reference")]
    ) is (not compatible)
    if compatible:
        _confirm(
            service, target, command="target", draft=1, state=first.state.fingerprint
        )
    else:
        with pytest.raises(RunPackageConflictError):
            _confirm(
                service,
                target,
                command="target",
                draft=1,
                state=first.state.fingerprint,
            )


@pytest.mark.pr_critical
def test_exact_retry_returns_original_result_after_later_mutation():
    repository = _repo()
    _empty(repository)
    service = RunPackageService(repository)
    v1 = _doc(entities=(_entity("a", 1),))
    original_preview = service.preview(run_id="run", branch_id="branch", document=v1)
    first = service.confirm(
        run_id="run",
        branch_id="branch",
        document=v1,
        command_id="original",
        expected_head_revision_id="r0",
        expected_draft_version=0,
        expected_state_fingerprint=None,
        expected_preview_fingerprint=original_preview.preview_fingerprint,
    )
    v2 = _doc(version=2, parent=v1.source_fingerprint, entities=(_entity("a", 2),))
    later = _confirm(
        service, v2, command="later", draft=1, state=first.state.fingerprint
    )
    retry = service.confirm(
        run_id="run",
        branch_id="branch",
        document=v1,
        command_id="original",
        expected_head_revision_id="r0",
        expected_draft_version=0,
        expected_state_fingerprint=None,
        expected_preview_fingerprint=original_preview.preview_fingerprint,
    )
    assert retry.state.fingerprint == first.state.fingerprint
    assert retry.draft_version == first.draft_version
    assert (
        service.get(run_id="run", branch_id="branch").fingerprint
        == later.state.fingerprint
    )


@pytest.mark.pr_critical
@pytest.mark.parametrize(
    "status,allowed",
    [
        (WORKING_RUN_STATUS, True),
        ("active", True),
        (COMPLETED_RUN_STATUS, True),
        (ARCHIVED_RUN_STATUS, False),
        ("future-status", False),
    ],
)
def test_package_mutation_obeys_run_lifecycle(status, allowed):
    repository = _repo()
    _empty(repository)
    with repository._session_factory.begin() as session:
        session.get(RunContainerModel, "run").status = status

    def action():
        return _confirm(
            RunPackageService(repository),
            _doc(entities=(_entity("a", 1),)),
            command="c",
            draft=0,
            state=None,
        )

    if allowed:
        action()
    else:
        with pytest.raises(RunPackageConflictError):
            action()


@pytest.mark.pr_critical
def test_allocator_and_all_writes_roll_back_after_late_failure():
    repository = _repo()
    _empty(repository)
    service = RunPackageService(repository)
    package = _doc(entities=(_entity("a", 1),))
    with pytest.raises(RuntimeError):
        _confirm(
            service,
            package,
            command="fail",
            draft=0,
            state=None,
            fault="after_identity_allocation",
        )
    with repository._session_factory() as session:
        assert session.get(RunPackageIdentityAllocatorModel, "run") is None
        assert (
            session.get(RunPackageApplicationReceiptModel, ("run", "branch", "fail"))
            is None
        )
    assert service.get(run_id="run", branch_id="branch") is None
    assert (
        repository.get_viewer_branch_working_draft(
            run_id="run", branch_id="branch"
        ).draft_version
        == 0
    )
    assert (
        _confirm(service, package, command="ok", draft=0, state=None)
        .state.entities[0]
        .run_local_id
        == 1
    )


@pytest.mark.pr_critical
def test_backward_forward_restore_reopen_and_retry_receipt(tmp_path):
    url = f"sqlite:///{tmp_path / 'restore.db'}"
    repository = _repo(url)
    _empty(repository)
    service = RunPackageService(repository)
    v1 = _doc(entities=(_entity("a", 1),))
    original_preview = service.preview(run_id="run", branch_id="branch", document=v1)
    state1 = service.confirm(
        run_id="run",
        branch_id="branch",
        document=v1,
        command_id="original",
        expected_head_revision_id="r0",
        expected_draft_version=0,
        expected_state_fingerprint=None,
        expected_preview_fingerprint=original_preview.preview_fingerprint,
    ).state
    RunWorkingDraftService(repository, _ids("r1", "a1")).save(
        run_id="run", branch_id="branch", expected_draft_version=1
    )
    v2 = _doc(version=2, parent=v1.source_fingerprint, entities=(_entity("a", 2),))
    state2 = _confirm(
        service, v2, command="v2", draft=2, state=state1.fingerprint, head="r1"
    ).state
    RunWorkingDraftService(repository, _ids("r2", "a2")).save(
        run_id="run", branch_id="branch", expected_draft_version=3
    )
    restore = RunSavedRevisionRestoreService(repository, _ids("cp1", "rr1", "ra1"))
    restore.restore_current_branch(
        run_id="run",
        branch_id="branch",
        target_saved_revision_id="r1",
        expected_head_saved_revision_id="r2",
        expected_draft_version=4,
        expected_current_viewer_branch_id="branch",
        explicit_confirmation=True,
    )
    assert (
        service.get(run_id="run", branch_id="branch").fingerprint == state1.fingerprint
    )
    retry = service.confirm(
        run_id="run",
        branch_id="branch",
        document=v1,
        command_id="original",
        expected_head_revision_id="r0",
        expected_draft_version=0,
        expected_state_fingerprint=None,
        expected_preview_fingerprint=original_preview.preview_fingerprint,
    )
    assert retry.state.fingerprint == state1.fingerprint
    restore2 = RunSavedRevisionRestoreService(repository, _ids("cp2", "rr2", "ra2"))
    restore2.restore_current_branch(
        run_id="run",
        branch_id="branch",
        target_saved_revision_id="r2",
        expected_head_saved_revision_id="rr1",
        expected_draft_version=5,
        expected_current_viewer_branch_id="branch",
        explicit_confirmation=True,
    )
    reopened = RunPackageService(_repo(url)).get(run_id="run", branch_id="branch")
    assert (
        reopened.fingerprint == state2.fingerprint
        and reopened.entities[0].run_local_id == 1
    )


@pytest.mark.pr_critical
def test_saved_component_corruption_fails_closed():
    entity = RunPackageEntity(
        run_local_id=1,
        source_package_id="p",
        source_entity_id="a",
        entity_kind="kind",
        scope="scope",
        payload={},
        source_baseline_fingerprint="x",
    )
    state = RunPackageState(run_id="run", branch_id="branch", entities=(entity,))
    valid = {
        "content": {
            "run_package_state": {
                "fingerprint": state.fingerprint,
                "state": state.model_dump(mode="json"),
            }
        }
    }
    corruptions = []
    outer = json.loads(json.dumps(valid))
    outer["content"]["run_package_state"]["fingerprint"] = "0" * 64
    corruptions.append(outer)
    wrong_run = json.loads(json.dumps(valid))
    wrong_run["content"]["run_package_state"]["state"]["run_id"] = "other"
    corruptions.append(wrong_run)
    wrong_branch = json.loads(json.dumps(valid))
    wrong_branch["content"]["run_package_state"]["state"]["branch_id"] = "other"
    corruptions.append(wrong_branch)
    duplicate = json.loads(json.dumps(valid))
    duplicate["content"]["run_package_state"]["state"]["entities"].append(
        duplicate["content"]["run_package_state"]["state"]["entities"][0]
    )
    corruptions.append(duplicate)
    for payload in corruptions:
        with pytest.raises(ValueError):
            load_saved_run_package_state(payload, run_id="run", branch_id="branch")


@pytest.mark.pr_critical
def test_receipt_contains_auditable_application_evidence():
    repository = _repo()
    _empty(repository)
    service = RunPackageService(repository)
    package = _doc(entities=(_entity("a", 1),))
    _confirm(service, package, command="audit", draft=0, state=None)
    with repository._session_factory() as session:
        receipt = session.get(
            RunPackageApplicationReceiptModel, ("run", "branch", "audit")
        )
        evidence = json.loads(receipt.payload_json)
    assert evidence["document"]["package_id"] == "p"
    assert evidence["selected_entities"] == ["p/a"]
    assert evidence["source_to_run_local_ids"] == {"p/a": 1}
    assert evidence["request_fingerprint"] == receipt.request_fingerprint


@pytest.mark.pr_critical
def test_generic_save_with_unchanged_package_is_not_hijacked(tmp_path):
    repository = _repo(f"sqlite:///{tmp_path / 'coexist.db'}")
    _empty(repository)
    packages = RunPackageService(repository)
    v1 = _doc(entities=(_entity("a", 1),))
    state = _confirm(packages, v1, command="v1", draft=0, state=None).state
    RunWorkingDraftService(repository, _ids("r1", "a1")).save(
        run_id="run", branch_id="branch", expected_draft_version=1
    )
    RunBranchCreationService(
        repository, _ids("other", "other-draft", "other-root")
    ).create_from_saved_revision(
        run_id="run", source_branch_id="branch", source_saved_revision_id="r1"
    )
    drafts = RunWorkingDraftService(repository, _ids("r2", "a2"))
    drafts.stage_viewer_branch(
        run_id="run",
        branch_id="branch",
        viewer_branch_id="other",
        expected_draft_version=2,
    )
    saved = drafts.save(run_id="run", branch_id="branch", expected_draft_version=3)
    assert (
        saved.saved_revision.payload["content"]["run_package_state"]["fingerprint"]
        == state.fingerprint
    )


@pytest.mark.pr_critical
def test_materialized_fork_divergence_and_nested_inheritance(tmp_path):
    url = f"sqlite:///{tmp_path / 'fork.db'}"
    repository = _repo(url)
    _empty(repository)
    source = RunPackageService(repository)
    state_a = _confirm(
        source, _doc(entities=(_entity("a", 1),)), command="v1", draft=0, state=None
    ).state
    RunWorkingDraftService(repository, _ids("r1", "a1")).save(
        run_id="run", branch_id="branch", expected_draft_version=1
    )
    RunBranchCreationService(
        repository, _ids("b", "db", "rb")
    ).create_from_saved_revision(
        run_id="run", source_branch_id="branch", source_saved_revision_id="r1"
    )
    service_b = RunPackageService(repository)
    package_b = _doc("q", entities=(_entity("new", 2),))
    preview = service_b.preview(run_id="run", branch_id="b", document=package_b)
    state_b = service_b.confirm(
        run_id="run",
        branch_id="b",
        document=package_b,
        command_id="b-change",
        expected_head_revision_id="rb",
        expected_draft_version=0,
        expected_state_fingerprint=preview.current_state_fingerprint,
        expected_preview_fingerprint=preview.preview_fingerprint,
    ).state
    assert [e.run_local_id for e in state_b.entities] == [1, 2]
    RunWorkingDraftService(repository, _ids("b-save", "b-audit")).save(
        run_id="run", branch_id="b", expected_draft_version=1
    )
    assert (
        source.get(run_id="run", branch_id="branch").fingerprint == state_a.fingerprint
    )
    assert repository.get_run_container(run_id="run").viewer_branch_id == "branch"
    RunBranchCreationService(
        repository, _ids("c", "dc", "rc")
    ).create_from_saved_revision(
        run_id="run", source_branch_id="b", source_saved_revision_id="b-save"
    )
    reopened = RunPackageService(_repo(url))
    assert (
        reopened.get(run_id="run", branch_id="branch").fingerprint
        == state_a.fingerprint
    )
    assert reopened.get(run_id="run", branch_id="c").entities == state_b.entities
