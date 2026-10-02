from __future__ import annotations

from types import SimpleNamespace

import pytest

from beta_engine.application.initial_world import InitialWorldState
from beta_engine.application.pre_alpha_fax_reference_materialization import (
    PreAlphaFaxReferenceMaterializationService,
    PreAlphaFaxReferenceMaterializeCommand,
    PreAlphaFaxReferenceRequest,
)
from beta_engine.application.season_player_bootstrap_service import SeasonActivePlayer
from beta_engine.domain.players.initial_pool import GeneratedPlayerAttributes
from beta_engine.domain.players.models import HiddenCareerTraits
from beta_engine.domain.rankings.official import OfficialRankingPolicy
from beta_engine.domain.run_packages import (
    CanonicalPackageDocument,
    PackageEntity,
    PackageType,
)
from beta_engine.domain.tournaments.models import SeasonCalendarEvent
from beta_engine.infrastructure.db import (
    DatabaseSettings,
    SimulationPersistenceRepository,
    create_session_factory,
    create_sqlite_engine,
)


def _repository(database_url: str) -> SimulationPersistenceRepository:
    engine = create_sqlite_engine(DatabaseSettings(url=database_url))
    repository = SimulationPersistenceRepository(
        engine=engine,
        session_factory=create_session_factory(engine),
    )
    repository.bootstrap_schema()
    return repository


def _ids():
    counter = {"value": 0}
    def make(kind: str) -> str:
        counter["value"] += 1
        return f"{kind}-{counter['value']}"
    return make


def _player(index: int) -> SeasonActivePlayer:
    ability = 70 + index % 20
    return SeasonActivePlayer(
        player_id=f"P{index:04d}",
        name=f"Player {index:04d}",
        country_code="CZE",
        nationality="CZE",
        birth_year=1975,
        birth_year_week=1,
        age_years_at_season_start=25,
        age_weeks_at_season_start=1300,
        current_ability=ability,
        potential_ability=max(ability, 90),
        potential_tier="A",
        career_stage="prime",
        play_style="balanced",
        archetype="all_court",
        attributes=GeneratedPlayerAttributes(
            technique=ability,
            movement=ability,
            physical=ability,
            mental=ability,
            consistency=ability,
            clutch=ability,
            recovery=ability,
        ),
        hidden_career_traits=HiddenCareerTraits(
            potential_ceiling=max(ability, 90),
            growth_curve="steady",
            professionalism=0.9,
            ambition=0.9,
            travel_tolerance=0.9,
            schedule_aggression=0.9,
            injury_proneness=0.1,
            resilience=0.9,
        ),
        season="2000/2001",
        source_pool_player_id=f"P{index:04d}",
        source_generation_fingerprint=f"src-{index}",
        source_generation="initial_pool",
        manual_override=False,
        locked_from_initial_pool=True,
        bootstrap_fingerprint=f"boot-{index}",
        bootstrap_seed=200001,
        bootstrap_id="FAX-REFERENCE",
    )


class _WorldAdapter:
    def build_document(self, world_id: str) -> CanonicalPackageDocument:
        return CanonicalPackageDocument(
            package_type=PackageType.WORLD,
            package_id=world_id,
            source_version=1,
            provenance={"source": "test"},
            explicit_scope=("world",),
            entities=(),
        )


class _CalendarAdapter:
    def __init__(self, count: int = 80):
        self.count = count

    def build_document(self, season: str) -> CanonicalPackageDocument:
        metadata = PackageEntity(
            source_entity_id="calendar.metadata",
            entity_kind="calendar.metadata.v1",
            entity_schema_version=1,
            scope="season_calendar",
            payload={
                "season": season,
                "metadata": None,
                "validation_warnings": [],
                "validation_errors": [],
            },
        )
        events = []
        for index in range(1, self.count + 1):
            event = SeasonCalendarEvent.model_validate(
                {
                    "event_id": f"FAX-WT-{index:03d}",
                    "season": season,
                    "season_week": ((index - 1) % 61) + 1,
                    "template_id": "FAX-REFERENCE",
                    "event_name": f"FAX World Tour {index:03d}",
                    "category": "REFERENCE",
                    "tour_level": "WORLD_TOUR",
                    "host_country": "CZE",
                    "region": "EUROPE",
                    "main_draw_size": 8,
                    "qualification_draw_size": 0,
                    "seeds_count": 2,
                    "qualifier_spots": 0,
                    "wild_cards": 0,
                    "byes": 0,
                    "ranking_status": "unranked",
                    "ranking_configuration_legacy": False,
                }
            )
            events.append(
                PackageEntity(
                    source_entity_id=event.event_id,
                    entity_kind="calendar.event.v1",
                    entity_schema_version=1,
                    scope="season_calendar",
                    payload=event.model_dump(mode="json"),
                )
            )
        return CanonicalPackageDocument(
            package_type=PackageType.CALENDAR,
            package_id="calendar-2000-2001",
            source_version=1,
            provenance={"source": "explicit-pre-alpha-test-reference"},
            explicit_scope=("season_calendar",),
            entities=(metadata, *events),
        )


class _InitialWorldService:
    def preview(self, *, run_id: str, branch_id: str, request):
        players = tuple(_player(i) for i in range(1, request.generation.target_pool_size + 1))
        return InitialWorldState(
            run_id=run_id,
            branch_id=branch_id,
            players=players,
            policies=(OfficialRankingPolicy(policy_id="msa-official-2000-01", best_n=15),),
            source_kind="run_world_generated_pool.v1",
            source_season="2000/2001",
            source_fingerprint="a" * 64,
            world_package_id=request.generation.world_package_id,
            world_country_content_fingerprint="b" * 64,
            world_generation_content_fingerprint="c" * 64,
            run_world_pool_preview_fingerprint="a" * 64,
            bootstrap_seed=request.generation.seed,
            bootstrap_fingerprint="d" * 64,
            adopted_by_command_id=request.command_id,
            audit_label=request.audit_label,
            audit_reason=request.audit_reason,
            adoption_request_fingerprint=request.fingerprint_for_scope(
                run_id=run_id, branch_id=branch_id
            ),
        )


@pytest.mark.pr_critical
def test_materializes_persisted_copied_fax_reference_that_passes_release_input_gate(tmp_path) -> None:
    repository = _repository(f"sqlite:///{tmp_path / 'fax-reference.db'}")
    service = PreAlphaFaxReferenceMaterializationService(
        repository=repository,
        id_factory=_ids(),
        world_adapter=_WorldAdapter(),
        calendar_adapter=_CalendarAdapter(),
        initial_world_service=_InitialWorldService(),
    )
    request = PreAlphaFaxReferenceRequest(
        display_name="Copied FAX Release Reference",
        world_package_id="official_fax_world",
        target_pool_size=1000,
    )
    preview = service.preview(request)

    assert preview.ready_to_materialize is True
    assert preview.world_tour_edition_count == 80
    assert preview.calendar_event_count == 80
    assert len(preview.preview_fingerprint) == 64

    result = service.materialize(
        PreAlphaFaxReferenceMaterializeCommand(
            request=request,
            expected_preview_fingerprint=preview.preview_fingerprint,
        )
    )

    assert result.acceptance_profile.ready_for_long_acceptance is True
    assert result.acceptance_profile.timeline_season_count == 50
    assert result.acceptance_profile.initial_player_count == 1000
    assert result.acceptance_profile.world_tour_edition_count == 80
    assert result.acceptance_profile.calendar_package_id == "calendar-2000-2001"

    revision_state = repository.get_branch_revision_state(branch_id=result.branch_id)
    assert revision_state.saved_head_revision_id == result.saved_revision_id
    assert revision_state.working_draft.status == "clean"
    assert repository.verify_branch_saved_revision_hash(
        revision_id=result.saved_revision_id
    )


def test_preview_rejects_non_reference_world_tour_count_without_creating_run(tmp_path) -> None:
    repository = _repository(f"sqlite:///{tmp_path / 'fax-reference-invalid.db'}")
    service = PreAlphaFaxReferenceMaterializationService(
        repository=repository,
        id_factory=_ids(),
        world_adapter=_WorldAdapter(),
        calendar_adapter=_CalendarAdapter(count=79),
        initial_world_service=_InitialWorldService(),
    )
    request = PreAlphaFaxReferenceRequest(
        display_name="Invalid Copied FAX",
        world_package_id="official_fax_world",
    )
    preview = service.preview(request)

    assert preview.ready_to_materialize is False
    assert preview.world_tour_edition_count == 79

    with pytest.raises(ValueError, match="exactly 80"):
        service.materialize(
            PreAlphaFaxReferenceMaterializeCommand(
                request=request,
                expected_preview_fingerprint=preview.preview_fingerprint,
            )
        )
    assert repository.list_run_containers() == []
