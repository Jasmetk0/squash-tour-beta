from __future__ import annotations

from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{path}: expected one match, found {count}: {old[:80]!r}")
    p.write_text(text.replace(old, new, 1), encoding="utf-8")


def replace_count(path: str, old: str, new: str, expected: int) -> None:
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    count = text.count(old)
    if count != expected:
        raise RuntimeError(f"{path}: expected {expected} matches, found {count}: {old[:80]!r}")
    p.write_text(text.replace(old, new), encoding="utf-8")


# 1) Freeze the resolved point-award authority at tournament adoption.
points = "src/beta_engine/application/season_point_awards_service.py"
replace_once(
    points,
    "\n\nclass PlayerPointAward(BaseModel):\n",
    '''\n\nclass FrozenPointAwardAuthority(BaseModel):
    """Resolved immutable points input captured when a tournament is adopted."""

    schema_version: Literal["frozen_point_award_authority.v1"] = (
        "frozen_point_award_authority.v1"
    )
    ranking_status: Literal["ranked", "unranked"]
    point_distribution: dict[str, int] = Field(default_factory=dict)
    point_distribution_source: str


class PlayerPointAward(BaseModel):
''',
)
replace_once(
    points,
    '    def generate_event_point_awards(self, *, event_id: str, request: PointAwardGenerateRequest) -> EventPointAwardPackageResult:\n',
    '''    def generate_event_point_awards(
        self,
        *,
        event_id: str,
        request: PointAwardGenerateRequest,
        frozen_authority: FrozenPointAwardAuthority | None = None,
    ) -> EventPointAwardPackageResult:
''',
)
replace_once(
    points,
    '''        event = self._calendar_event(result_package)
        unranked = event is not None and event.ranking_status.value == "unranked"
        active_players = self.active_players_service.get_active_players(season=result_package.season).players
        if not active_players and not unranked:
            raise ValueError(f"No active season players found for season '{result_package.season}'. Persist active players before awarding points.")
        active_by_id = {player.player_id: player for player in active_players}
        distribution, distribution_source = ({}, "calendar_event.unranked") if unranked else self._resolve_point_distribution(result_package)
''',
    '''        event = self._calendar_event(result_package)
        if frozen_authority is None:
            unranked = event is not None and event.ranking_status.value == "unranked"
            distribution, distribution_source = (
                ({}, "calendar_event.unranked")
                if unranked
                else self._resolve_point_distribution(result_package)
            )
        else:
            unranked = frozen_authority.ranking_status == "unranked"
            distribution = dict(frozen_authority.point_distribution)
            distribution_source = frozen_authority.point_distribution_source
        active_players = self.active_players_service.get_active_players(season=result_package.season).players
        if not active_players and not unranked:
            raise ValueError(f"No active season players found for season '{result_package.season}'. Persist active players before awarding points.")
        active_by_id = {player.player_id: player for player in active_players}
''',
)
replace_once(
    points,
    '''    def _load_result_package(self, event_id: str) -> SeasonEventResultPackage:
''',
    '''    def freeze_point_award_authority(self, package: Any) -> FrozenPointAwardAuthority:
        """Resolve live point configuration once for a future owned tournament close."""
        event = self._calendar_event(package)
        unranked = event is not None and event.ranking_status.value == "unranked"
        distribution, source = (
            ({}, "calendar_event.unranked")
            if unranked
            else self._resolve_point_distribution(package)
        )
        return FrozenPointAwardAuthority(
            ranking_status="unranked" if unranked else "ranked",
            point_distribution=dict(distribution),
            point_distribution_source=source,
        )

    def _load_result_package(self, event_id: str) -> SeasonEventResultPackage:
''',
)
replace_once(
    points,
    '    def _resolve_point_distribution(self, package: SeasonEventResultPackage) -> tuple[dict[str, int], str]:\n',
    '    def _resolve_point_distribution(self, package: Any) -> tuple[dict[str, int], str]:\n',
)
replace_once(
    points,
    '    def _calendar_event(self, package: SeasonEventResultPackage) -> Any | None:\n',
    '    def _calendar_event(self, package: Any) -> Any | None:\n',
)

slots = "src/beta_engine/application/authoritative_slot_matches.py"
replace_once(
    slots,
    '''from beta_engine.application.season_point_awards_service import (
    EventPointAwardPackage,
    PointAwardGenerateRequest,
    SeasonPointAwardsRegistry,
    SeasonPointAwardsService,
)
''',
    '''from beta_engine.application.season_point_awards_service import (
    EventPointAwardPackage,
    FrozenPointAwardAuthority,
    PointAwardGenerateRequest,
    SeasonPointAwardsRegistry,
    SeasonPointAwardsService,
)
''',
)
replace_once(
    slots,
    '''    authoritative: AuthoritativeFourPlayerTournamentResult,
    result_seed: int,
    award_seed: int,
) -> tuple[SeasonEventMatchPackage, SeasonEventResultPackage, EventPointAwardPackage]:
''',
    '''    authoritative: AuthoritativeFourPlayerTournamentResult,
    result_seed: int,
    award_seed: int,
    frozen_point_authority: FrozenPointAwardAuthority | None = None,
) -> tuple[SeasonEventMatchPackage, SeasonEventResultPackage, EventPointAwardPackage]:
''',
)
replace_once(
    slots,
    '''    awards = award_builder.generate_event_point_awards(
        event_id=package.event_id,
        request=PointAwardGenerateRequest(seed=award_seed, dry_run=True),
    ).award_package
''',
    '''    awards = award_builder.generate_event_point_awards(
        event_id=package.event_id,
        request=PointAwardGenerateRequest(seed=award_seed, dry_run=True),
        frozen_authority=frozen_point_authority,
    ).award_package
''',
)

# 2) Harden the authoritative driver: writable scope, frozen award envelope,
# and idempotent close when another valid command already closed the event.
driver = "src/beta_engine/application/authoritative_run_simulation_driver.py"
replace_once(
    driver,
    'from beta_engine.application.season_point_awards_service import SeasonPointAwardsService\n',
    '''from beta_engine.application.season_point_awards_service import (
    FrozenPointAwardAuthority,
    SeasonPointAwardsService,
)
''',
)
replace_once(
    driver,
    '''    PlayerSportingWeekStateModel,
    RunBranchModel,
    RankingTransitionAuthorityModel,
''',
    '''    PlayerSportingWeekStateModel,
    RunBranchModel,
    RunContainerModel,
    RankingTransitionAuthorityModel,
''',
)
replace_count(
    driver,
    '            session.execute(text("BEGIN IMMEDIATE"))\n',
    '''            session.execute(text("BEGIN IMMEDIATE"))
            self._require_writable_scope(session, command.run_id, command.branch_id)
''',
    3,
)
replace_once(
    driver,
    '''    @staticmethod
    def _validate_expected(session, command, before):
''',
    '''    @staticmethod
    def _require_writable_scope(session, run_id, branch_id):
        run = session.get(RunContainerModel, run_id)
        branch = session.get(RunBranchModel, branch_id)
        if run is None or branch is None or branch.run_id != run_id:
            raise ValueError("authoritative simulation Run/Branch scope does not exist")
        if run.read_only or branch.read_only or branch.status != "active":
            raise ValueError("authoritative simulation Run/Branch is not writable")

    @staticmethod
    def _validate_expected(session, command, before):
''',
)
old_authority = '''    def _authority_package(self, session, run_id, branch_id, week, *, adopt):
        row = session.get(
            AdoptedTournamentAuthorityModel, (run_id, branch_id, week.ordinal)
        )
        if row is not None:
            package = SeasonEventMatchPackage.model_validate_json(row.package_json)
            authority_fp = self._tournament_authority_fingerprint(
                run_id, branch_id, week, package
            )
            if (
                authority_fp != row.authority_fingerprint
                or package.event_id != row.event_id
            ):
                raise ValueError("frozen tournament authority is corrupt")
            return package, authority_fp
        if not adopt:
            raise ValueError("frozen tournament authority is missing")
        package = self._package(week)
        if package is None:
            raise ValueError("supported tournament authority is missing")
        authority_fp = self._tournament_authority_fingerprint(
            run_id, branch_id, week, package
        )
        session.add(
            AdoptedTournamentAuthorityModel(
                run_id=run_id,
                branch_id=branch_id,
                week_ordinal=week.ordinal,
                event_id=package.event_id,
                authority_fingerprint=authority_fp,
                package_json=package.model_dump_json(),
            )
        )
        session.flush()
        return package, authority_fp

    @staticmethod
    def _tournament_authority_fingerprint(run_id, branch_id, week, package):
        payload = package.model_dump(mode="json")
        payload["metadata"].pop("persistence_path", None)
        return fingerprint(
            {"scope": [run_id, branch_id, week.ordinal], "package": payload}
        )
'''
new_authority = '''    @staticmethod
    def _decode_adopted_authority(payload_json):
        payload = json.loads(payload_json)
        if payload.get("schema_version") == "adopted_tournament_authority.v2":
            return (
                SeasonEventMatchPackage.model_validate(payload["package"]),
                FrozenPointAwardAuthority.model_validate(payload["point_award_authority"]),
            )
        return SeasonEventMatchPackage.model_validate(payload), None

    @staticmethod
    def _encode_adopted_authority(package, point_authority):
        return json.dumps(
            {
                "schema_version": "adopted_tournament_authority.v2",
                "package": package.model_dump(mode="json"),
                "point_award_authority": point_authority.model_dump(mode="json"),
            },
            sort_keys=True,
            separators=(",", ":"),
        )

    def _authority_package(self, session, run_id, branch_id, week, *, adopt):
        row = session.get(
            AdoptedTournamentAuthorityModel, (run_id, branch_id, week.ordinal)
        )
        if row is not None:
            package, point_authority = self._decode_adopted_authority(row.package_json)
            authority_fp = self._tournament_authority_fingerprint(
                run_id, branch_id, week, package, point_authority
            )
            if (
                authority_fp != row.authority_fingerprint
                or package.event_id != row.event_id
            ):
                raise ValueError("frozen tournament authority is corrupt")
            return package, authority_fp
        if not adopt:
            raise ValueError("frozen tournament authority is missing")
        package = self._package(week)
        if package is None:
            raise ValueError("supported tournament authority is missing")
        point_authority = self.awards_service.freeze_point_award_authority(package)
        authority_fp = self._tournament_authority_fingerprint(
            run_id, branch_id, week, package, point_authority
        )
        session.add(
            AdoptedTournamentAuthorityModel(
                run_id=run_id,
                branch_id=branch_id,
                week_ordinal=week.ordinal,
                event_id=package.event_id,
                authority_fingerprint=authority_fp,
                package_json=self._encode_adopted_authority(package, point_authority),
            )
        )
        session.flush()
        return package, authority_fp

    def _point_award_authority(self, session, run_id, branch_id, week):
        row = session.get(
            AdoptedTournamentAuthorityModel, (run_id, branch_id, week.ordinal)
        )
        if row is None:
            raise ValueError("frozen tournament authority is missing")
        _, point_authority = self._decode_adopted_authority(row.package_json)
        return point_authority

    @staticmethod
    def _tournament_authority_fingerprint(
        run_id, branch_id, week, package, point_authority=None
    ):
        payload = package.model_dump(mode="json")
        payload["metadata"].pop("persistence_path", None)
        body = {"scope": [run_id, branch_id, week.ordinal], "package": payload}
        if point_authority is not None:
            body["point_award_authority"] = point_authority.model_dump(mode="json")
        return fingerprint(body)
'''
replace_once(driver, old_authority, new_authority)
replace_once(
    driver,
    '''            else self._tournament_authority_fingerprint(
                run_id, branch_id, week, package
            ),
''',
    '''            else self._tournament_authority_fingerprint(
                run_id,
                branch_id,
                week,
                package,
                self.awards_service.freeze_point_award_authority(package),
            ),
''',
)
replace_once(
    driver,
    '''        if fault_at == "after_final_before_source":
            raise RuntimeError(
                "fault after tournament final before ranking source persistence"
            )
        _, result, awards = build_authoritative_tournament_ranking_packages(
            self.awards_service,
            package=package,
            authoritative=auth,
            result_seed=self._stable_seed(package, "result"),
            award_seed=self._stable_seed(package, "awards"),
        )
''',
    '''        if fault_at == "after_final_before_source":
            raise RuntimeError(
                "fault after tournament final before ranking source persistence"
            )
        store = OwnedTournamentRankingSourceStore(session)
        existing = store.get(
            run_id=command.run_id,
            branch_id=command.branch_id,
            edition_id=package.event_id,
        )
        if existing is not None:
            self._validate_existing_owned_source(existing, command, package, auth)
            return
        point_authority = self._point_award_authority(
            session,
            command.run_id,
            command.branch_id,
            command.expected_week,
        )
        if point_authority is None:
            raise ValueError(
                "legacy adopted tournament has no frozen point-award authority"
            )
        _, result, awards = build_authoritative_tournament_ranking_packages(
            self.awards_service,
            package=package,
            authoritative=auth,
            result_seed=self._stable_seed(package, "result"),
            award_seed=self._stable_seed(package, "awards"),
            frozen_point_authority=point_authority,
        )
''',
)
replace_once(
    driver,
    '''        OwnedTournamentRankingSourceStore(session).append(
            OwnedTournamentRankingSource(
''',
    '''        store.append(
            OwnedTournamentRankingSource(
''',
)
replace_once(
    driver,
    '''    @staticmethod
    def _stable_seed(package, suffix):
''',
    '''    @staticmethod
    def _validate_existing_owned_source(existing, command, package, authoritative):
        binding = existing.binding
        if (
            binding.run_id != command.run_id
            or binding.branch_id != command.branch_id
            or binding.edition_id != package.event_id
            or binding.event_id != package.event_id
            or binding.completed_week != command.expected_week
        ):
            raise ValueError("Conflicting owned tournament source")
        expected = {
            group.authoritative_input.match_id: group.result_fingerprint
            for group in (
                *authoritative.semifinal_groups,
                authoritative.final_group,
            )
        }
        actual = {
            ref.match_id: ref.result_fingerprint
            for ref in existing.result.match_result_refs
        }
        if actual != expected:
            raise ValueError("Conflicting owned tournament source")
        prepare_tournament_ranking_sources(
            existing.binding, existing.result, existing.awards
        )

    @staticmethod
    def _stable_seed(package, suffix):
''',
)

# 3) Legacy replay reader recognizes v10 as the same protected rules/log generation.
replay = "src/beta_engine/application/season_match_service.py"
replace_once(
    replay,
    '        current_rules = match.match_input_snapshot.schema_version == "match_input_snapshot.v9"\n',
    '''        current_rules = match.match_input_snapshot.schema_version in {
            "match_input_snapshot.v9",
            "match_input_snapshot.v10",
        }
''',
)
replace_once(
    replay,
    '''            "match_input_snapshot.v8",
            "match_input_snapshot.v9",
        }:
''',
    '''            "match_input_snapshot.v8",
            "match_input_snapshot.v9",
            "match_input_snapshot.v10",
        }:
''',
)

# 4) The bootstrap test reloaded main.py while deps.build_runtime was still monkeypatched,
# leaking the sentinel function into later tests. Undo the patch before the final reload.
bootstrap_test = "tests/application/test_app_bootstrap.py"
replace_once(
    bootstrap_test,
    '''    finally:
        importlib.reload(reloaded_module)
''',
    '''    finally:
        monkeypatch.undo()
        importlib.reload(reloaded_module)
''',
)

# Existing driver fixtures now satisfy the same product Run/Branch scope guard.
slot_tests = "tests/application/test_authoritative_slot_matches.py"
replace_once(
    slot_tests,
    '''    SimulationSlotModel,
    RunBranchModel,
)
''',
    '''    SimulationSlotModel,
    RunBranchModel,
    RunContainerModel,
)
''',
)
replace_count(
    slot_tests,
    '''    session.add(
        RunBranchModel(
''',
    '''    session.add(
        RunContainerModel(
            run_id="run",
            display_name="Driver test run",
            timeline_start_season=2000,
            timeline_end_season=2049,
        )
    )
    session.add(
        RunBranchModel(
''',
    2,
)

# Focused regressions for the four reproduced functional bugs.
regression = Path("tests/application/test_authoritative_simulation_stabilization.py")
regression.write_text(
    r'''from __future__ import annotations

import json

import pytest
from sqlalchemy import select

from beta_engine.application.authoritative_run_simulation_driver import (
    AuthoritativeSimulationCommand,
)
from beta_engine.application.season_match_service import (
    MatchPackageGenerateRequest,
    MatchSimulateRequest,
)
from beta_engine.core import DeterministicRng
from beta_engine.domain.matches import MatchEngine, MatchInputSnapshot
from beta_engine.infrastructure.db.models import (
    AuthoritativeSimulationCommandModel,
    OwnedTournamentRankingSourceModel,
    RunBranchModel,
    RunContainerModel,
    SimulationEventGroupModel,
    SimulationSlotModel,
)
from beta_engine.infrastructure.db.owned_tournament_sources import (
    OwnedTournamentRankingSourceStore,
)

from test_authoritative_slot_matches import _driver_command, _driver_fixture
from test_season_match_service import make_match_service


def test_adopted_tournament_freezes_point_authority(tmp_path):
    driver, factory, week = _driver_fixture(tmp_path / "frozen-awards")
    semifinals, _ = _driver_command(driver, week, "semifinals")
    driver.simulate_next_slot(semifinals)

    match_registry = driver.match_service._load_registry()
    event_id = next(iter(match_registry.matches_by_event_id))
    calendar_service = driver.awards_service.calendar_service
    calendar_registry = calendar_service._load_registry()
    calendar = calendar_registry.calendars_by_season["2000/2001"]
    event = next(item for item in calendar.events if item.event_id == event_id)
    event.ranking_points_table = {
        "winner": 999,
        "finalist": 888,
        "semifinalist": 777,
    }
    event.point_distribution_ref = None
    calendar_service._save_registry(calendar_registry)

    final, _ = _driver_command(driver, week, "final")
    driver.simulate_next_slot(final)
    with factory() as session:
        source = OwnedTournamentRankingSourceStore(session).history(
            run_id="run", branch_id="branch"
        )[0]
        by_stage = {
            award.reached_stage: award.ranking_points_awarded
            for award in source.awards.awards
        }
        assert by_stage["champion"] == 100
        assert by_stage["finalist"] == 60
        assert by_stage["semifinal"] == 30


@pytest.mark.parametrize("scope", ["run", "branch", "archived"])
def test_simulation_rejects_non_writable_scope_before_any_write(tmp_path, scope):
    driver, factory, week = _driver_fixture(tmp_path / scope)
    command, _ = _driver_command(driver, week, f"blocked-{scope}")
    with factory.begin() as session:
        if scope == "run":
            session.get(RunContainerModel, "run").read_only = 1
        else:
            branch = session.get(RunBranchModel, "branch")
            if scope == "branch":
                branch.read_only = 1
            else:
                branch.status = "archived"

    with pytest.raises(ValueError, match="not writable"):
        driver.simulate_next_slot(command)

    with factory() as session:
        assert session.scalars(select(SimulationSlotModel)).all() == []
        assert session.scalars(select(SimulationEventGroupModel)).all() == []
        assert session.scalars(select(AuthoritativeSimulationCommandModel)).all() == []
        assert session.scalars(select(OwnedTournamentRankingSourceModel)).all() == []


def test_pending_next_slot_accepts_matching_close_by_other_commands(tmp_path):
    driver, factory, week = _driver_fixture(tmp_path / "interleaving")
    pending, _ = _driver_command(driver, week, "pending-slot")
    with pytest.raises(RuntimeError, match="before second"):
        driver.simulate_next_slot(pending, fault_at="before_second_group")

    position = driver.position(run_id="run", branch_id="branch")
    other = AuthoritativeSimulationCommand(
        command_id="other-semifinal",
        run_id="run",
        branch_id="branch",
        expected_week=week,
        expected_position_fingerprint=position.position_fingerprint,
        expected_revision_id="revision",
        group_id=position.eligible_match_ids[0],
    )
    driver.simulate_next_match(other)
    final, _ = _driver_command(driver, week, "other-final")
    driver.simulate_next_slot(final)

    resumed = driver.simulate_next_slot(pending)
    assert resumed["supported_tournament_complete"] is True
    with factory() as session:
        assert len(session.scalars(select(SimulationEventGroupModel)).all()) == 3
        assert len(
            OwnedTournamentRankingSourceStore(session).history(
                run_id="run", branch_id="branch"
            )
        ) == 1
        receipt = session.get(
            AuthoritativeSimulationCommandModel,
            ("run", "branch", "pending-slot"),
        )
        assert receipt.status == "complete"


def test_pending_next_slot_still_fails_closed_on_mismatching_owned_source(tmp_path):
    driver, factory, week = _driver_fixture(tmp_path / "interleaving-conflict")
    pending, _ = _driver_command(driver, week, "pending-slot")
    with pytest.raises(RuntimeError, match="before second"):
        driver.simulate_next_slot(pending, fault_at="before_second_group")
    position = driver.position(run_id="run", branch_id="branch")
    other = AuthoritativeSimulationCommand(
        command_id="other-semifinal",
        run_id="run",
        branch_id="branch",
        expected_week=week,
        expected_position_fingerprint=position.position_fingerprint,
        expected_revision_id="revision",
        group_id=position.eligible_match_ids[0],
    )
    driver.simulate_next_match(other)
    final, _ = _driver_command(driver, week, "other-final")
    driver.simulate_next_slot(final)

    with factory.begin() as session:
        row = session.scalar(select(OwnedTournamentRankingSourceModel))
        payload = json.loads(row.payload_json)
        payload["result"]["match_result_refs"][0]["result_fingerprint"] = "0" * 64
        row.payload_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        # Make the store-level fingerprint agree so the driver must detect the
        # semantic mismatch rather than relying only on row corruption checks.
        from beta_engine.domain.rankings.tournament_source import OwnedTournamentRankingSource
        changed = OwnedTournamentRankingSource.model_validate(payload)
        row.source_fingerprint = changed.fingerprint

    with pytest.raises(ValueError, match="Conflicting owned tournament source"):
        driver.simulate_next_slot(pending)


def test_legacy_replay_reader_accepts_v10_snapshot(tmp_path):
    service, event_id = make_match_service(tmp_path / "replay-v10")
    service.generate_match_package(
        event_id=event_id,
        request=MatchPackageGenerateRequest(seed=101, dry_run=False),
    )
    package = service.simulate_next_match(
        event_id=event_id,
        request=MatchSimulateRequest(seed=777),
    ).match_package
    assert package is not None
    completed = next(
        match
        for match in package.qualification_matches + package.main_draw_matches
        if match.status == "completed"
    )
    old = completed.match_input_snapshot
    assert old is not None
    current = MatchInputSnapshot.create(
        context=old.context,
        effective_match_format=old.effective_match_format,
        simulation_seed=old.simulation_seed,
        match_engine_version="match_engine_v10",
        effective_match_timing=old.effective_match_timing,
        effective_match_stamina=old.effective_match_stamina,
        rally_calibration_profile=old.rally_calibration_profile,
        effective_match_gameplans=old.effective_match_gameplans,
        effective_rally_rules=old.effective_rally_rules,
    )
    result = MatchEngine(rng=DeterministicRng(current.simulation_seed)).simulate(
        current.context,
        log_anchor_hash=current.snapshot_hash,
        effective_match_timing=current.effective_match_timing,
        effective_match_stamina=current.effective_match_stamina,
        rally_calibration_profile=current.rally_calibration_profile,
        effective_match_gameplans=current.effective_match_gameplans,
        effective_rally_rules=current.effective_rally_rules,
    )
    registry = service._load_registry()
    stored = next(
        match
        for match in (
            registry.matches_by_event_id[event_id].qualification_matches
            + registry.matches_by_event_id[event_id].main_draw_matches
        )
        if match.match_id == completed.match_id
    )
    stored.match_input_snapshot = current
    stored.simulated_result = result
    stored.result_fingerprint = result.simulation_fingerprint
    stored.simulation_seed = current.simulation_seed
    service._save_registry(registry)

    replay = service.get_match_replay(event_id=event_id, match_id=completed.match_id)
    assert replay.verified is True
    assert replay.match_input_snapshot.schema_version == "match_input_snapshot.v10"
    assert replay.rng_rerun is False
''',
    encoding="utf-8",
)

print("authoritative simulation stabilization patch applied")
