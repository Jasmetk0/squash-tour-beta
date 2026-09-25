from collections.abc import Iterator
import pytest

from beta_engine.application.run_branch_creation_service import RunBranchCreationService
from beta_engine.application.run_container_creation_service import (
    RunContainerCreationService,
)
from beta_engine.application.run_package_service import (
    RunPackageConflictError,
    RunPackageService,
)
from beta_engine.application.run_working_draft_service import RunWorkingDraftService
from beta_engine.domain.run_packages import (
    CanonicalPackageDocument,
    PackageEntity,
    PackageType,
    SourceReference,
)
from beta_engine.infrastructure.db import (
    DatabaseSettings,
    SimulationPersistenceRepository,
    create_session_factory,
    create_sqlite_engine,
)


def ids(*values):
    stream: Iterator[str] = iter(values)
    return lambda _: next(stream)


def repo(url="sqlite://"):
    engine = create_sqlite_engine(DatabaseSettings(url=url))
    result = SimulationPersistenceRepository(
        engine=engine, session_factory=create_session_factory(engine)
    )
    result.bootstrap_schema()
    return result


def empty(repository):
    RunContainerCreationService(
        repository, ids("run", "a", "r0", "d0")
    ).create_empty_run(display_name="Packages")


def doc(kind=PackageType.WORLD, package="p", version=1, entities=(), parent=None):
    return CanonicalPackageDocument(
        package_type=kind,
        package_id=package,
        source_version=version,
        explicit_scope=tuple(e.scope for e in entities),
        entities=tuple(entities),
        parent_source_fingerprint=parent,
    )


def entity(identity, payload, kind="country", scope="world", refs=(), valid=True):
    return PackageEntity(
        source_entity_id=identity,
        entity_kind=kind,
        scope=scope,
        payload=payload,
        references=refs,
        valid=valid,
    )


def apply(service, document, command="c", draft=0, state=None, head="r0", **kwargs):
    preview = service.preview(run_id="run", branch_id="a", document=document)
    return service.confirm(
        run_id="run",
        branch_id="a",
        document=document,
        command_id=command,
        expected_head_revision_id=head,
        expected_draft_version=draft,
        expected_state_fingerprint=state,
        expected_preview_fingerprint=preview.preview_fingerprint,
        **kwargs,
    )


@pytest.mark.pr_critical
def test_five_types_preview_is_read_only_and_initial_copy_is_independent():
    repository = repo()
    empty(repository)
    service = RunPackageService(repository)
    for kind in PackageType:
        candidate = doc(
            kind,
            kind.value.lower(),
            entities=()
            if kind == PackageType.SETUP
            else (entity("x", {"name": kind.value}),),
        )
        before = repository.get_viewer_branch_working_draft(run_id="run", branch_id="a")
        service.preview(run_id="run", branch_id="a", document=candidate)
        assert (
            repository.get_viewer_branch_working_draft(run_id="run", branch_id="a")
            == before
        )
    source = {"name": "Original"}
    package = doc(entities=(entity("x", source),))
    result = apply(service, package)
    source["name"] = "Changed"
    assert result.state.entities[0].payload == {"name": "Original"}
    assert (
        repository.get_viewer_branch_working_draft(run_id="run", branch_id="a").status
        == "dirty"
    )


@pytest.mark.pr_critical
def test_partial_scope_unresolved_exact_resolution_and_name_does_not_resolve():
    repository = repo()
    empty(repository)
    service = RunPackageService(repository)
    first = doc(entities=(entity("a", {"n": "A"}), entity("b", {"n": "B"})))
    r1 = apply(service, first)
    ref = SourceReference(
        source_package_id="categories",
        source_entity_id="c",
        expected_entity_kind="category",
    )
    series = doc(
        PackageType.SERIES,
        "series",
        entities=(entity("s", {"name": "same"}, "series", "series", (ref,)),),
    )
    r2 = apply(service, series, "c2", 1, r1.state.fingerprint)
    assert service.preview(
        run_id="run",
        branch_id="a",
        document=doc(
            PackageType.CATEGORY,
            "other",
            entities=(entity("wrong", {"name": "same"}, "category"),),
        ),
    ).unresolved
    categories = doc(
        PackageType.CATEGORY,
        "categories",
        entities=(entity("c", {"name": "C"}, "category"),),
    )
    assert service.preview(
        run_id="run", branch_id="a", document=categories
    ).automatically_resolvable
    r3 = apply(service, categories, "c3", 2, r2.state.fingerprint)
    partial = doc(
        entities=(entity("a", {"n": "A2"}),), version=2, parent=first.source_fingerprint
    )
    r4 = apply(service, partial, "c4", 3, r3.state.fingerprint)
    assert next(e for e in r4.state.entities if e.source_entity_id == "b").payload == {
        "n": "B"
    }


@pytest.mark.pr_critical
def test_repeat_corrupt_version_and_local_divergence_resolution():
    repository = repo()
    empty(repository)
    service = RunPackageService(repository)
    v1 = doc(entities=(entity("a", {"v": 1}),))
    r1 = apply(service, v1)
    repeat = apply(service, v1, "repeat", 1, r1.state.fingerprint)
    assert repeat.already_applied
    corrupt = doc(entities=(entity("a", {"v": 99}),))
    with pytest.raises(RunPackageConflictError):
        apply(service, corrupt, "bad", 1, r1.state.fingerprint)
    edited = service.edit_entity(
        run_id="run",
        branch_id="a",
        run_local_id=1,
        payload={"v": "local"},
        expected_draft_version=1,
        expected_state_fingerprint=r1.state.fingerprint,
    )
    v2 = doc(version=2, parent=v1.source_fingerprint, entities=(entity("a", {"v": 2}),))
    preview = service.preview(run_id="run", branch_id="a", document=v2)
    assert preview.conflicts
    kept = apply(
        service,
        v2,
        "keep",
        2,
        edited.fingerprint,
        conflict_resolutions={"p/a": "keep_run"},
    )
    assert kept.state.entities[0].payload == {"v": "local"}


@pytest.mark.pr_critical
def test_save_reopen_and_materialized_nested_fork(tmp_path):
    url = f"sqlite:///{tmp_path / 'packages.db'}"
    repository = repo(url)
    empty(repository)
    service = RunPackageService(repository)
    applied = apply(service, doc(entities=(entity("a", {"v": 1}),)))
    saved = RunWorkingDraftService(repository, ids("r1", "audit1")).save(
        run_id="run", branch_id="a", expected_draft_version=1
    )
    assert (
        saved.saved_revision.payload["content"]["run_package_state"]["fingerprint"]
        == applied.state.fingerprint
    )
    branch = RunBranchCreationService(
        repository, ids("b", "db", "rb")
    ).create_from_saved_revision(
        run_id="run", source_branch_id="a", source_saved_revision_id="r1"
    )
    target = RunPackageService(repository).get(run_id="run", branch_id=branch.branch_id)
    assert target.branch_id == "b" and target.entities[0].run_local_id == 1
    nested = RunBranchCreationService(
        repository, ids("c", "dc", "rc")
    ).create_from_saved_revision(
        run_id="run", source_branch_id="b", source_saved_revision_id="rb"
    )
    assert (
        RunPackageService(repo(url))
        .get(run_id="run", branch_id=nested.branch_id)
        .entities[0]
        .run_local_id
        == 1
    )


@pytest.mark.pr_critical
def test_setup_invalid_selection_rolls_back_atomically():
    repository = repo()
    empty(repository)
    service = RunPackageService(repository)
    good = doc(PackageType.WORLD, "w", entities=(entity("a", {"ok": 1}),))
    bad = doc(PackageType.CALENDAR, "cal", entities=(entity("bad", {}, valid=False),))
    setup = CanonicalPackageDocument(
        package_type=PackageType.SETUP,
        package_id="setup",
        source_version=1,
        explicit_scope=("w", "cal"),
        children=(good, bad),
    )
    preview = service.preview(run_id="run", branch_id="a", document=setup)
    with pytest.raises(RunPackageConflictError):
        service.confirm(
            run_id="run",
            branch_id="a",
            document=setup,
            command_id="setup",
            expected_head_revision_id="r0",
            expected_draft_version=0,
            expected_state_fingerprint=None,
            expected_preview_fingerprint=preview.preview_fingerprint,
        )
    assert service.get(run_id="run", branch_id="a") is None
