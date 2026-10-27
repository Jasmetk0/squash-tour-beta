"""Real Admin Chromium group creation, multi-round playoff, Save and cold restart."""
import argparse
import json
import os
import subprocess
import sqlite3
import sys
from contextlib import contextmanager
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main():
    from playwright.sync_api import expect, sync_playwright

    from beta_engine.domain.calendar.run_calendar import RunCalendar
    from scripts.native_tour_browser_acceptance import stop_process, wait_http
    from tests.api.test_calendar_tour_flow import inspect, setup
    from tests.api.test_saved_revision_history_api import ApiServer

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--source', type=Path)
    parser.add_argument('--chromium', default=os.environ.get('CHROME_BIN', '/usr/bin/chromium'))
    args = parser.parse_args()
    root = args.root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    database = root / 'groups.sqlite'
    if database.exists():
        raise ValueError('Use a fresh isolated browser evidence directory')
    if args.source:
        with sqlite3.connect(args.source) as src, sqlite3.connect(database) as target:
            src.backup(target)
    errors = []
    expect.set_options(timeout=90000)

    @contextmanager
    def browser_session(pw, server, language):
        with (root / f'frontend-{language}.log').open('w') as log:
            frontend = subprocess.Popen(['npm', '--prefix', 'web', 'run', 'dev', '--',
                '--host', '127.0.0.1', '--port', '5173', '--strictPort'],
                env={**os.environ, 'VITE_API_BASE_URL': server.base_url}, stdout=log,
                stderr=subprocess.STDOUT, start_new_session=True)
            browser = None
            page = None
            try:
                wait_http('http://127.0.0.1:5173', frontend)
                browser = pw.chromium.launch(executable_path=args.chromium, args=['--no-sandbox'])
                context = browser.new_context(viewport={'width':1440, 'height':1100})
                context.add_init_script(f"localStorage.setItem('squash-engine-language-v1',{json.dumps(language)})")
                page = context.new_page()
                page.set_default_timeout(90000)
                page.on('pageerror', lambda error: errors.append(str(error)))
                page.on('response', lambda response: print('HTTP failure', response.status, response.url, flush=True) if response.status >= 400 else None)
                page.goto('http://127.0.0.1:5173/admin/runs/run/tour/editions?branch=branch')
                panel = page.get_by_role('region', name='Configured native Tour', exact=True)
                expect(panel.get_by_label('Tour operation reason')).to_be_visible()
                panel.get_by_label('Tour operation reason').fill('Real Chromium reviewed native groups')
                yield page, panel
            except Exception:
                if page:
                    page.screenshot(path=str(root / 'failure.png'), full_page=True)
                    print('Browser body:', page.locator('body').inner_text()[:5000], 'Errors:', errors, flush=True)
                raise
            finally:
                if browser:
                    browser.close()
                stop_process(frontend)

    def accept(page, panel, label):
        panel.get_by_role('button', name=label, exact=True).click()
        panel.get_by_label('Confirm Tour command').check()
        with page.expect_response(lambda r:r.request.method=='POST' and r.url.endswith('/calendar-tour/execute?include_inspection=true')) as pending:
            panel.get_by_role('button', name='Execute confirmed operation', exact=True).click()
        response = pending.value
        assert response.status == 201, response.text()
        result = response.json()
        assert result['schema_version'] == 'calendar_tour_execution_inspection.v1'
        assert not result['inspection']['saved']
        return result['inspection']

    def manual_save(page, panel):
        panel.get_by_label('Confirm Tour Save').check()
        with page.expect_response(lambda r:r.request.method=='POST' and r.url.endswith('/calendar-tour/save')) as pending:
            panel.get_by_role('button', name='Manual Tour Save', exact=True).click()
        assert pending.value.status == 201, pending.value.text()
        expect(panel.get_by_label('Tour operation reason')).to_be_visible()
        # Wait for the immutable HEAD effect's independent read / verified handoff.
        expect(panel.get_by_role('button', name='Review Week Transition', exact=True)).to_be_visible()

    with sync_playwright() as pw:
        with ApiServer(database_url=f'sqlite:///{database}') as server:
            if not args.source:
                setup(server, RunCalendar(52, 1, 2030, 2), 8)
            with browser_session(pw, server, 'en') as (page, panel):
                panel.get_by_text('New Tournament Edition', exact=True).click()
                panel.get_by_label('Tour Edition ID').fill('browser-groups')
                panel.get_by_label('Tour Edition name').fill('Chromium Groups + knockout')
                panel.get_by_label('Tour Edition format').select_option('groups_knockout')
                panel.get_by_label('Group ranking win points').fill('7')
                expect(panel.get_by_label('Group crossings')).to_have_value('A1-B2 / B1-A2')
                accept(page, panel, 'Review new Edition')
                manual_save(page, panel)
                for _ in range(2):
                    accept(page, panel, 'Review Week Transition')
                    manual_save(page, panel)
                players = [p['player_id'] for p in inspect(server)['players']]
                panel.get_by_label('Tour applicants browser-groups').select_option(players)
                accept(page, panel, 'Review applications')
                accept(page, panel, 'Review approval')
                accept(page, panel, 'Review draw')
                manual_save(page, panel)
                accept(page, panel, 'Review Next Match')
                manual_save(page, panel)
                frozen = inspect(server)['next_slot']['snapshot_fingerprint']
                page.screenshot(path=str(root / 'partial-group-saved.png'), full_page=True)
        with ApiServer(database_url=f'sqlite:///{database}') as server:
            assert inspect(server)['next_slot']['snapshot_fingerprint'] == frozen
            with browser_session(pw, server, 'en') as (page, panel):
                for _ in range(5):
                    accept(page, panel, 'Review Next Slot')
                    manual_save(page, panel)
                expect(panel.get_by_role('table', name='Group 1 standings')).to_be_visible()
                expect(panel.get_by_role('table', name='Group 2 standings')).to_be_visible()
                expect(panel.get_by_role('table', name='Played matches browser-groups').locator('tbody tr')).to_have_count(15)
                expect(panel.get_by_role('table', name='Edition results browser-groups').locator('tbody tr')).to_have_count(8)
                accept(page, panel, 'Review results')
                manual_save(page, panel)
                accept(page, panel, 'Review Week Transition')
                manual_save(page, panel)
                saved = inspect(server)
                rows = saved['state']['rankings'][-1]['rows']
                assert len(rows) == 8 and all(len(r['counted_results']) == 1 for r in rows)
                page.screenshot(path=str(root / 'saved-ranking.png'), full_page=True)
        with ApiServer(database_url=f'sqlite:///{database}') as server:
            assert inspect(server)['state']['rankings'][-1]['rows'] == rows
            with browser_session(pw, server, 'cs') as (page, panel):
                expect(panel.get_by_text('Skupiny a postup', exact=True)).to_be_visible()
                expect(panel.get_by_role('table', name='Group 1 standings')).to_be_visible()
                page.screenshot(path=str(root / 'cold-czech-groups.png'), full_page=True)
    assert not errors, errors
    (root / 'result.json').write_text(json.dumps({'real_chromium':True,'actual_matches':15,
        'manual_save':True,'cold_restart':True,'ranked_players':len(rows),'browser_errors':errors}, indent=2))
    print('PASS: actual Admin groups, 15 MatchEngine matches, playoff, points, Save, cold restart and CS/EN')


if __name__ == '__main__':
    main()
