"""Rotterdam and Dallas 2025 in one native W52 Run, in the same Q/Main weeks.

Both copied Saved profiles source Q on 1-2 February (W05) and Main on 3-9
February (W06). Their applicants are disjoint here; the shared slot ledger
plays both Editions' rounds in the same slots from the same frozen snapshot.
"""

import pytest

from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.tournaments.native_scheduled_knockout import scheduled_edition_plan
from tests.api.test_atp_dallas_native_w52 import (
    DALLAS, TIMINGS, accepted_matches, authority, catalog_entry, confirm, dallas_schedule, edition,
    prepare_dallas_entry, preview_scheduled, scheduled_request, timed_slot, transition,
)
from tests.api.test_atp_next_gen_edition import _save_atp_source
from tests.api.test_calendar_tour_flow import command, execute, inspect, save_tour, setup
from tests.api.test_saved_revision_history_api import ApiServer

pytestmark = pytest.mark.smoke

ROTTERDAM = "atp_2025_rotterdam"


def test_rotterdam_and_dallas_share_weeks_with_separate_draws_qualifiers_and_points(tmp_path):
    database = f"sqlite:///{tmp_path / 'two-atp.db'}"
    with ApiServer(database_url=database) as server:
        repo, _ = setup(server, RunCalendar(52, 1, 2025, 2), count=96)
        _save_atp_source(server)
        for occurrence, name in ((DALLAS, "import-dallas"), (ROTTERDAM, "import-rotterdam")):
            view = inspect(server)
            entry = catalog_entry(server, occurrence)
            code, review = preview_scheduled(
                server, occurrence, scheduled_request(view, entry, dallas_schedule(view), name=name))
            assert code == 200, review
            confirm(server, review)
            save_tour(server)
        for week in (2, 3, 4):
            transition(server, f"two-week-{week}")
        wc = {
            DALLAS: prepare_dallas_entry(server, name_prefix="dallas"),
            ROTTERDAM: prepare_dallas_entry(server, occurrence_id=ROTTERDAM, name_prefix="rotterdam",
                                            players=slice(44, 88), direct=24, wild_cards=4),
        }
        for occurrence in (DALLAS, ROTTERDAM):
            execute(server, command(inspect(server), "draw", name=f"{occurrence}-draw", edition_id=occurrence,
                                    data={"wild_card_player_ids": wc[occurrence]}))
        save_tour(server)
        view = inspect(server)
        plans = {o: scheduled_edition_plan(authority(view, o)) for o in (DALLAS, ROTTERDAM)}
        assert plans[DALLAS].draw.fingerprint != plans[ROTTERDAM].draw.fingerprint
        ids = {o: {p.match_id for p in plan.topology.plans} for o, plan in plans.items()}
        assert not ids[DALLAS] & ids[ROTTERDAM]
        first, _, _ = timed_slot(server, "two-q-1")
        assert len(first["match_ids"]) == 16
        second, _, _ = timed_slot(server, "two-q-2")
        assert len(second["match_ids"]) == 8
        transition(server, "two-q-to-main")
        matches = accepted_matches(repo)
        main_view = inspect(server)
        pairs = {m["match_id"]: (m["player_a_id"], m["player_b_id"]) for m in main_view["next_slot"]["matches"]}
        assert len(pairs) == 32
        for occurrence, plan in plans.items():
            q_finals = [max(b.nodes, key=lambda n: n.round_number).node_id for b in plan.draw.qualification_brackets]
            winners = {matches[mid].result.winner_player_id for mid in q_finals}
            assert len(winners) == 4
            first_main = {pid for n in plan.draw.main.nodes if n.round_number == 1
                          for pid in pairs[n.node_id]}
            assert winners <= first_main
        for number in range(1, 6):
            timed_slot(server, f"two-main-{number}")
        view = inspect(server)
        for occurrence in (DALLAS, ROTTERDAM):
            assert edition(view, occurrence)["tournament_fingerprint"]
            assert len(view["edition_evidence"][occurrence]["matches"]) == 43
            execute(server, command(inspect(server), "confirm-result", name=f"confirm-{occurrence}",
                                    edition_id=occurrence))
            save_tour(server)
        transition(server, "two-publication")
        final = inspect(server)
        rows = {row["player_id"]: row for row in final["state"]["rankings"][-1]["rows"]}
        for occurrence in (DALLAS, ROTTERDAM):
            results = final["edition_evidence"][occurrence]["results"]
            assert len(results) == 44
            for r in results:
                counted = [c for c in rows[r["player_id"]]["counted_results"] if c["edition_id"] == occurrence]
                assert len(counted) == 1
                assert counted[0]["completed_week"]["week"] == 6
                assert counted[0]["first_publication_week"]["week"] == 7
        champions = {o: max(final["edition_evidence"][o]["results"], key=lambda r: r["main_points"])
                     for o in (DALLAS, ROTTERDAM)}
        assert champions[DALLAS]["main_points"] == 500 and champions[ROTTERDAM]["main_points"] == 500
    print("TWO_ATP_TIMINGS", TIMINGS)
