"""Global Tournament Test Lab API."""

from fastapi import APIRouter, Depends

from beta_engine.api.deps import get_tournament_test_lab_service
from beta_engine.application.tournament_test_lab_service import (
    BuiltInTournamentLabScenario,
    TournamentLabCompatibility,
    TournamentLabRequest,
    TournamentLabResult,
    TournamentLabScenario,
    TournamentTestLabService,
)

router = APIRouter(prefix="/admin/labs/tournament", tags=["admin-labs"])


@router.get("/scenarios", response_model=list[BuiltInTournamentLabScenario])
def list_tournament_lab_scenarios(
    service: TournamentTestLabService = Depends(get_tournament_test_lab_service),
) -> list[BuiltInTournamentLabScenario]:
    return list(service.list_built_in_scenarios())


@router.post("/inspect", response_model=TournamentLabCompatibility)
def inspect_tournament_lab_scenario(
    scenario: TournamentLabScenario,
    service: TournamentTestLabService = Depends(get_tournament_test_lab_service),
) -> TournamentLabCompatibility:
    return service.inspect(scenario)


@router.post("/run", response_model=TournamentLabResult)
def run_tournament_lab(
    request: TournamentLabRequest,
    service: TournamentTestLabService = Depends(get_tournament_test_lab_service),
) -> TournamentLabResult:
    return service.run(request)
