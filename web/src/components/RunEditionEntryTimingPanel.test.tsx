/** Mocked React/API-boundary tests: NOT real browser, HTTP or SQLite acceptance. */
import { QueryClient, QueryClientProvider, useQueryClient } from '@tanstack/react-query'
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { ReactNode } from 'react'

import { RunEditionEntryTimingPanel } from './RunEditionEntryTimingPanel'
import { LanguageProvider, useLanguage } from '../i18n/LanguageContext'
import {
  sameTiming, verifiedRunCalendar, validEntryTimingInspection,
  type EditionEntryTiming, type EntryTimingPreview
} from '../api/runEditionEntryTiming'
import type { RunCalendarMetadata } from '../api/runCalendarCreation'

const api = vi.hoisted(() => ({
  ApiError: class ApiError extends Error { constructor(message: string, public status = 409) { super(message) } },
  getRunEditionEntryTiming: vi.fn(),
  previewRunEditionEntryTiming: vi.fn(),
  confirmRunEditionEntryTiming: vi.fn(),
  saveRunPackageWorkingDraft: vi.fn(),
  getRunContainer: vi.fn(),
  listRunBranches: vi.fn(),
  getBranchWorkingDraft: vi.fn(),
  getRunPackageState: vi.fn(),
  listTournamentRankingPublicationOptions: vi.fn()
}))
vi.mock('../api/client', () => api)
const hash = (letter: string) => letter.repeat(64)
const calendar: RunCalendarMetadata = {
  schema_version: 'run_calendar.v1', weeks_per_year: 80,
  season_start_year_week: 37, start_year: 2030, season_count: 5
}
const at = (week: number, season_index = 0) => ({ calendar, season_index, week })
const timing: EditionEntryTiming = {
  schema_version: 'edition_entry_timing.v1',
  main_open: at(13), main_duration_weeks: 2, qualification_duration_weeks: 1,
  final_commitment: null, ranking_publication_override: null
}
const missing = {
  run_id: 'run', branch_id: 'branch', package_id: 'calendar-package', event_id: 'edition',
  timing: null, preflight_status: 'missing_content' as const,
  blockers: [{ code: 'entry_timing_missing', detail: 'Choose opening' }],
  automatic_eligibility_status: 'not_implemented' as const
}
const preview: EntryTimingPreview = {
  schema_version: 'run_edition_entry_timing_preview.v1',
  run_id: 'run', branch_id: 'branch', package_id: 'calendar-package', event_id: 'edition',
  saved_head_revision_id: 'head', draft_version: 1, state_fingerprint: hash('a'),
  edition_fingerprint: hash('b'), timing, before: null,
  resolved: {
    main_open: at(13), main_close: at(14),
    qualification_open: at(15), qualification_close: at(15),
    final_commitment: at(15), default_ranking_completed_week: at(13),
    ranking_publication_week: at(14), ranking_source: 'after_main_closing_minus_one'
  },
  current_week: null, current_window: null,
  ranking_snapshot_fingerprint: null, ranking_authority_fingerprint: null,
  ranking_will_be_bound: false, ranking_binding_status: 'missing_prerequisite',
  configuration_state: 'working_draft', timing_and_ranking_ready: false,
  preflight_status: 'missing_content', automatic_eligibility_status: 'not_implemented',
  can_confirm_configuration: true, blockers: [
    { code: 'ranking_publication_missing', detail: 'Missing exact Official publication' }
  ],
  preview_fingerprint: hash('c')
}
const receipt = {
  command_id: 'placeholder', request_fingerprint: hash('d'),
  request: { kind: 'run_edition_entry_timing.v1', ...missing, timing,
    expected_preview_fingerprint: hash('c'), operator_label: 'Operator', audit_reason: 'Reviewed' },
  preview, draft_version: 2, state_fingerprint: hash('e'),
  state: { run_id: 'run', branch_id: 'branch' },
  ranking_authority_fingerprint: null, already_applied: false, receipt_fingerprint: hash('f')
}
function Toggle() {
  const { setLanguage, language } = useLanguage()
  return <button onClick={() => setLanguage(language === 'en' ? 'cs' : 'en')}>Switch language</button>
}
function BackgroundEntryRefresh() {
  const client = useQueryClient()
  return <button onClick={() => {void client.refetchQueries({queryKey:['edition-entry-timing']})}}>
    Background Entry refresh
  </button>
}
function Frame({ children }: { children: ReactNode }) {
  return <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
    <MemoryRouter><LanguageProvider><Toggle />{children}</LanguageProvider></MemoryRouter>
  </QueryClientProvider>
}
function mount(props: Partial<Parameters<typeof RunEditionEntryTimingPanel>[0]> = {}) {
  return render(<Frame><RunEditionEntryTimingPanel
    runId="run" branchId="branch" packageId="calendar-package"
    eventId="edition" calendar={calendar} enabled {...props} /></Frame>)
}
async function fill(): Promise<void> {
  await screen.findByText(/není uložený plán|has no configured Entry plan/i)
  fireEvent.change(screen.getByLabelText(/Main opening – season|Otevření Main – sezona/), { target: { value: '0' } })
  fireEvent.change(screen.getByLabelText(/Main opening – week|Otevření Main – týden/), { target: { value: '13' } })
  fireEvent.change(screen.getByLabelText(/Confirmation operator|Operátor potvrzení/), { target: { value: 'Operator' } })
  fireEvent.change(screen.getByLabelText(/Confirmation reason|Důvod potvrzení/), { target: { value: 'Reviewed' } })
}
async function requestPreview() {
  await userEvent.click(screen.getByRole('button', {name: /Spočítat serverový náhled|Calculate server preview/}))
  await screen.findByRole('heading', { name: /Serverový náhled – bez zápisu|Server preview – no write/ })
}
afterEach(() => vi.restoreAllMocks())
beforeEach(() => {
  vi.clearAllMocks()
  localStorage.setItem('squash-engine-language-v1', 'cs')
  api.getRunEditionEntryTiming.mockResolvedValue(missing)
  api.listTournamentRankingPublicationOptions.mockResolvedValue({
    run_id:'run', branch_id:'branch', event_id:'edition',
    source:'published_official_rankings.v1', publication_count:1,
    publications:[{
      ranking_week:{season_index:0,week:14},snapshot_fingerprint:hash('f'),
      ranked_row_count:50,policy_id:'policy',best_n:15
    }]
  })
  api.previewRunEditionEntryTiming.mockResolvedValue(preview)
  api.getRunContainer.mockResolvedValue({
    run_id:'run', storage_kind:'custom_local', read_only:false,
    metadata_json:{run_calendar:calendar}
  })
  api.listRunBranches.mockResolvedValue({run_branches:[{
    run_id:'run',branch_id:'branch',status:'active',read_only:false,
    saved_head_revision_id:'head'
  }]})
  api.getBranchWorkingDraft.mockResolvedValue({
    run_id:'run',branch_id:'branch',status:'dirty',
    base_saved_revision_id:'head',draft_version:2
  })
  api.getRunPackageState.mockResolvedValue({
    state:{run_id:'run',branch_id:'branch'},fingerprint:hash('e')
  })
  api.saveRunPackageWorkingDraft.mockResolvedValue({
    run_id:'run',branch_id:'branch',saved_revision:{revision_id:'revision-new'},
    working_draft:{run_id:'run',branch_id:'branch',
      base_saved_revision_id:'revision-new',status:'clean'}
  })
  api.confirmRunEditionEntryTiming.mockImplementation(async (
    _run: string, _branch: string, _pkg: string, _edition: string, payload: { command_id: string }) =>
    ({ ...receipt, command_id: payload.command_id }))
})

describe('Edition Entry timing Admin panel (mocked component boundary)', () => {
  it('restores only local timing fields; retains audit without server writes', async () => {
    api.getRunEditionEntryTiming.mockResolvedValueOnce({...preview, preview_fingerprint: hash('a')})
    mount()
    await waitFor(() => expect(screen.getByLabelText('Otevření Main – týden')).toHaveValue(13))
    fireEvent.change(screen.getByLabelText('Otevření Main – týden'), {target:{value:'18'}})
    fireEvent.change(screen.getByLabelText('Délka Main (týdny)'), {target:{value:'4'}})
    fireEvent.change(screen.getByLabelText('Operátor potvrzení'), {target:{value:'Operator'}})
    expect(screen.getByText(/Rozepsané lokální změny/)).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button',{name:'Obnovit lokální pole z načteného plánu'}))
    expect(screen.getByLabelText('Otevření Main – týden')).toHaveValue(13)
    expect(screen.getByLabelText('Délka Main (týdny)')).toHaveValue(2)
    expect(screen.getByLabelText('Operátor potvrzení')).toHaveValue('Operator')
    expect(api.previewRunEditionEntryTiming).not.toHaveBeenCalled()
    expect(api.confirmRunEditionEntryTiming).not.toHaveBeenCalled()
    expect(api.saveRunPackageWorkingDraft).not.toHaveBeenCalled()
  })

  it('does not show obsolete windows or ready-to-bind claims after unreviewed local edits', async () => {
    api.getRunEditionEntryTiming.mockResolvedValueOnce({
      ...preview, timing_and_ranking_ready:true, ranking_will_be_bound:true
    })
    mount()
    await waitFor(() => expect(screen.getByLabelText('Otevření Main – týden')).toHaveValue(13))
    expect(screen.getByText('Main okno')).toBeInTheDocument()
    expect(screen.getByText(/Při potvrzení se naváže tento ověřený snapshot/)).toBeInTheDocument()
    fireEvent.change(screen.getByLabelText('Otevření Main – týden'), {target:{value:'18'}})
    expect(screen.queryByText('Main okno')).not.toBeInTheDocument()
    expect(screen.queryByText(/Při potvrzení se naváže tento ověřený snapshot/)).not.toBeInTheDocument()
    expect(screen.queryByText(/Časování a ranking jsou připravené pouze/)).not.toBeInTheDocument()
    expect(screen.getByText(/Zobrazené serverové překážky se vztahují k poslednímu načtenému plánu/)).toBeInTheDocument()
    expect(api.confirmRunEditionEntryTiming).not.toHaveBeenCalled()
  })

  it('rejects a self-consistent server plan whose calendar differs from the present Run clock', async () => {
    const foreignClock = {...calendar, weeks_per_year:52}
    const foreignWeek = (week: number) => ({calendar:foreignClock,season_index:0,week})
    api.getRunEditionEntryTiming.mockResolvedValueOnce({
      ...preview,
      timing:{...timing,main_open:foreignWeek(13)},
      resolved:{
        ...preview.resolved,
        main_open:foreignWeek(13),main_close:foreignWeek(14),
        qualification_open:foreignWeek(15),qualification_close:foreignWeek(15),
        final_commitment:foreignWeek(15),
        default_ranking_completed_week:foreignWeek(13),
        ranking_publication_week:foreignWeek(14)
      }
    })
    mount()
    expect(await screen.findByText(/Načtený plán používá jiný kalendář Runu/)).toBeInTheDocument()
    expect(screen.getByRole('button',{name:'Spočítat serverový náhled'})).toBeDisabled()
    expect(screen.queryByText('Main okno')).not.toBeInTheDocument()
    expect(api.previewRunEditionEntryTiming).not.toHaveBeenCalled()
    expect(api.confirmRunEditionEntryTiming).not.toHaveBeenCalled()
  })

  it('does not report previous server blockers as readiness for unreviewed local edits', async () => {
    mount(); await fill()
    expect(screen.getByText(/Zobrazené serverové překážky se vztahují k poslednímu načtenému plánu/)).toBeInTheDocument()
    expect(screen.queryByText(/Server dovoluje potvrdit konfiguraci/)).not.toBeInTheDocument()
    await requestPreview()
    expect(screen.queryByText(/Zobrazené serverové překážky se vztahují/)).not.toBeInTheDocument()
    expect(screen.getByText(/Server dovoluje potvrdit konfiguraci/)).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button',{name:'Switch language'}))
    expect(screen.queryByText(/These server blockers describe the last loaded plan/)).not.toBeInTheDocument()
    fireEvent.change(screen.getByLabelText('Main opening – week'), {target:{value:'18'}})
    expect(screen.getByText(/These server blockers describe the last loaded plan/)).toBeInTheDocument()
    expect(api.confirmRunEditionEntryTiming).not.toHaveBeenCalled()
  })

  it('invalidates existing preview after a fresh background inspection without reusing its fingerprint', async () => {
    api.getRunEditionEntryTiming.mockResolvedValueOnce(missing)
      .mockResolvedValueOnce({...preview, timing})
    render(<Frame>
      <RunEditionEntryTimingPanel runId="run" branchId="branch"
        packageId="calendar-package" eventId="edition" calendar={calendar} enabled />
      <BackgroundEntryRefresh />
    </Frame>)
    await fill(); await requestPreview()
    expect(screen.getByRole('button',{name:'Výslovně potvrdit do Working Draftu'})).toBeEnabled()
    await userEvent.click(screen.getByRole('button',{name:'Background Entry refresh'}))
    await waitFor(() => expect(api.getRunEditionEntryTiming).toHaveBeenCalledTimes(2))
    await waitFor(() => expect(screen.queryByRole('button',{
      name:'Výslovně potvrdit do Working Draftu'
    })).not.toBeInTheDocument())
    expect(api.previewRunEditionEntryTiming).toHaveBeenCalledTimes(1)
    expect(api.confirmRunEditionEntryTiming).not.toHaveBeenCalled()
  })

  it('keeps reviewed preview on audit edits; timing edit invalidates it', async () => {
    mount(); await fill(); await requestPreview()
    fireEvent.change(screen.getByLabelText('Důvod potvrzení (audit)'), {target:{value:'New reason'}})
    expect(screen.getByText('Serverový náhled – bez zápisu')).toBeInTheDocument()
    expect(screen.getByRole('button',{name:'Výslovně potvrdit do Working Draftu'})).toBeEnabled()
    fireEvent.change(screen.getByLabelText('Délka Main (týdny)'), {target:{value:'3'}})
    expect(screen.queryByText('Serverový náhled – bez zápisu')).not.toBeInTheDocument()
  })

  it('shows week errors and can restore only the approved durations explicitly', async () => {
    mount(); await fill()
    fireEvent.change(screen.getByLabelText('Otevření Main – týden'), {target:{value:'81'}})
    expect(screen.getByText(/Týden musí být v rozsahu 1–80/)).toBeInTheDocument()
    expect(screen.getByLabelText('Otevření Main – týden')).toHaveAttribute('aria-invalid','true')
    fireEvent.change(screen.getByLabelText('Délka Main (týdny)'), {target:{value:'4'}})
    await userEvent.click(screen.getByRole('button',{name:'Nastavit délky Main 2 / Q 1'}))
    expect(screen.getByLabelText('Délka Main (týdny)')).toHaveValue(2)
    expect(screen.getByLabelText('Otevření Main – týden')).toHaveValue(81)
    expect(api.previewRunEditionEntryTiming).not.toHaveBeenCalled()
  })

  it('shows a read-only diff from the frozen server before/after values', async () => {
    const modified = {...timing, main_duration_weeks:3}
    api.getRunEditionEntryTiming.mockResolvedValueOnce({...preview, timing})
    api.previewRunEditionEntryTiming.mockResolvedValueOnce({...preview, timing:modified, before:timing})
    mount()
    // The numeric duration starts at 2 even before GET initializes the saved plan.
    // Wait for server-provided Main opening instead of assuming initial load finished.
    await waitFor(() => expect(screen.getByLabelText('Otevření Main – týden')).toHaveValue(13))
    fireEvent.change(screen.getByLabelText('Délka Main (týdny)'), {target:{value:'3'}})
    await requestPreview()
    expect(screen.getByText('Co serverový náhled mění')).toBeInTheDocument()
    expect(screen.getByText('Délka Main', {selector:'strong'})).toBeInTheDocument()
    expect(screen.getByText('Zobrazit nezměněná pole')).toBeInTheDocument()
    expect(api.confirmRunEditionEntryTiming).not.toHaveBeenCalled()
  })

  it('loads real publication options only when override is enabled and does not bind by selection', async () => {
    mount(); await fill()
    expect(api.listTournamentRankingPublicationOptions).not.toHaveBeenCalled()
    await userEvent.click(screen.getByLabelText('Použít explicitní publikaci Official Ranking'))
    await waitFor(() => expect(api.listTournamentRankingPublicationOptions).toHaveBeenCalledWith(
      'run','branch','edition'
    ))
    await userEvent.selectOptions(screen.getByLabelText('Vybrat existující publikaci Official Ranking'),'0:14')
    expect(screen.getByLabelText('Publikace rankingu – týden')).toHaveValue(14)
    expect(api.confirmRunEditionEntryTiming).not.toHaveBeenCalled()
    expect(api.saveRunPackageWorkingDraft).not.toHaveBeenCalled()
  })

  it('distinguishes missing publication history without selecting a fictional ranking', async () => {
    api.listTournamentRankingPublicationOptions.mockResolvedValueOnce({
      run_id:'run',branch_id:'branch',event_id:'edition',
      source:'published_official_rankings.v1',publication_count:0,publications:[]
    })
    mount(); await fill()
    await userEvent.click(screen.getByLabelText('Použít explicitní publikaci Official Ranking'))
    expect(await screen.findByText(/nebyla nalezena použitelná publikace/)).toBeInTheDocument()
    expect(screen.getByLabelText('Publikace rankingu – týden')).toHaveValue(null)
    expect(api.confirmRunEditionEntryTiming).not.toHaveBeenCalled()
  })

  it('does not infer the opening from play week; keeps only approved 2+1 defaults', async () => {
    mount()
    await screen.findByText(/zatím není uložený plán/)
    expect(screen.getByLabelText('Otevření Main – týden')).toHaveValue(null)
    expect(screen.getByLabelText('Délka Main (týdny)')).toHaveValue(2)
    expect(screen.getByLabelText('Délka kvalifikace Q (týdny)')).toHaveValue(1)
    expect(screen.getByRole('button',{name:'Spočítat serverový náhled'})).toBeDisabled()
    expect(api.confirmRunEditionEntryTiming).not.toHaveBeenCalled()
    expect(api.saveRunPackageWorkingDraft).not.toHaveBeenCalled()
  })

  it('does not lose local input or preview when equivalent Run calendar keys are reordered', async () => {
    const view = mount()
    await fill(); await requestPreview()
    const reorderedClock: RunCalendarMetadata = {
      start_year: calendar.start_year, season_count: calendar.season_count,
      schema_version: calendar.schema_version,
      season_start_year_week: calendar.season_start_year_week,
      weeks_per_year: calendar.weeks_per_year
    }
    view.rerender(<Frame><RunEditionEntryTimingPanel
      runId="run" branchId="branch" packageId="calendar-package"
      eventId="edition" calendar={reorderedClock} enabled /></Frame>)
    await waitFor(() => expect(screen.getByRole('button',{
      name:'Výslovně potvrdit do Working Draftu'
    })).toBeEnabled())
    expect(screen.getByLabelText('Otevření Main – týden')).toHaveValue(13)
    expect(screen.getByLabelText('Operátor potvrzení')).toHaveValue('Operator')
    expect(screen.getByLabelText('Důvod potvrzení (audit)')).toHaveValue('Reviewed')
    expect(api.confirmRunEditionEntryTiming).not.toHaveBeenCalled()
    expect(api.saveRunPackageWorkingDraft).not.toHaveBeenCalled()
  })

  it('keeps input, audit and valid server preview on CS/EN language switch', async () => {
    mount()
    await fill()
    await requestPreview()
    expect(screen.getAllByText(/2030\/2031 · S0 W13/).length).toBeGreaterThan(0)
    await userEvent.click(screen.getByRole('button',{name:'Switch language'}))
    expect(screen.getByLabelText('Main opening – week')).toHaveValue(13)
    expect(screen.getByLabelText('Confirmation operator')).toHaveValue('Operator')
    expect(screen.getByLabelText('Confirmation reason (audit)')).toHaveValue('Reviewed')
    expect(screen.getByText(/Server preview – no write/)).toBeInTheDocument()
    expect(screen.getByRole('button',{name:'Explicitly confirm into Working Draft'})).toBeEnabled()
    expect(api.confirmRunEditionEntryTiming).not.toHaveBeenCalled()
  })

  it('shows the server-owned current Entry phase without inventing one for unknown Run time', async () => {
    mount(); await fill(); await requestPreview()
    expect(screen.getByText('Aktuální fáze přihlášek (podle serveru)').nextElementSibling)
      .toHaveTextContent('Server aktuální fázi neurčil')
    expect(api.confirmRunEditionEntryTiming).not.toHaveBeenCalled()
  })

  it('localizes an explicitly known server Entry phase without calculating it from weeks', async () => {
    api.previewRunEditionEntryTiming.mockResolvedValueOnce({
      ...preview, current_week:at(13), current_window:'main'
    })
    mount(); await fill(); await requestPreview()
    expect(screen.getByText('Aktuální fáze přihlášek (podle serveru)').nextElementSibling)
      .toHaveTextContent('Main přihlášky jsou otevřené')
    await userEvent.click(screen.getByRole('button',{name:'Switch language'}))
    expect(screen.getByText('Current Entry phase (server)').nextElementSibling)
      .toHaveTextContent('Main Entry open')
    expect(screen.getAllByText(/2030\/2031 · S0 W13/).length).toBeGreaterThan(0)
    expect(api.confirmRunEditionEntryTiming).not.toHaveBeenCalled()
  })

  it('shows the exact completed-data 13 and publication 14 server values, not recalculated in UI', async () => {
    mount()
    await fill(); await requestPreview()
    const dataLabel = screen.getByText('Ranking – data po dokončeném týdnu')
    const publishedLabel = screen.getByText('Ranking – označení publikace')
    expect(dataLabel.nextElementSibling?.textContent).toContain('W13')
    expect(publishedLabel.nextElementSibling?.textContent).toContain('W14')
    expect(screen.getByText(/Přesná publikace není k dispozici/)).toBeInTheDocument()
    expect(screen.getByText(/automatická validace/i)).toBeInTheDocument()
  })

  it('invalidates preview immediately after changing Main duration', async () => {
    mount()
    await fill(); await requestPreview()
    expect(screen.getByRole('button',{name:'Výslovně potvrdit do Working Draftu'})).toBeEnabled()
    fireEvent.change(screen.getByLabelText('Délka Main (týdny)'), { target: {value:'3'} })
    expect(screen.queryByText('Serverový náhled – bez zápisu')).not.toBeInTheDocument()
    expect(screen.queryByRole('button',{name:'Výslovně potvrdit do Working Draftu'})).not.toBeInTheDocument()
  })

  it('shows all real blockers, denies blocked configurations, distinguishes unsupported sporting execution', async () => {
    api.previewRunEditionEntryTiming.mockResolvedValueOnce({
      ...preview, can_confirm_configuration: false, preflight_status:'unsupported_execution',
      blockers:[{code:'unsupported_execution',detail:'wrong clock'},
        {code:'entry_timing_locked',detail:'already open'},
        {code:'ranking_binding_conflict',detail:'immutable'}]
    })
    mount(); await fill(); await requestPreview()
    expect(screen.getByText(/Kalendář lze plánovat/)).toBeInTheDocument()
    expect(screen.getByText(/Entry už bylo otevřeno/)).toBeInTheDocument()
    expect(screen.getByText(/Časování po otevření Entry neupravuj/)).toBeInTheDocument()
    expect(screen.getByText(/Edition už má jiný neměnný ranking/)).toBeInTheDocument()
    expect(screen.getAllByText('already open').length).toBe(1)
    expect(screen.getByRole('button',{name:'Výslovně potvrdit do Working Draftu'})).toBeDisabled()
  })

  it('preserves every identical server blocker without React duplicate-key warnings', async () => {
    api.previewRunEditionEntryTiming.mockResolvedValueOnce({
      ...preview, can_confirm_configuration:false, blockers:[
        {code:'entry_timing_locked',detail:'Already opened'},
        {code:'entry_timing_locked',detail:'Already opened'}
      ]
    })
    const spy = vi.spyOn(console, 'error')
    mount(); await fill(); await requestPreview()
    expect(screen.getAllByText(/Entry už bylo otevřeno/)).toHaveLength(2)
    expect(spy.mock.calls.join(' ')).not.toMatch(/same key|unique key/i)
    expect(api.confirmRunEditionEntryTiming).not.toHaveBeenCalled()
  })

  it('confirms a future plan without a ranking only with server permission; never Saves or adopts itself', async () => {
    mount(); await fill(); await requestPreview()
    await userEvent.click(screen.getByRole('button',{name:'Výslovně potvrdit do Working Draftu'}))
    await waitFor(() => expect(api.confirmRunEditionEntryTiming).toHaveBeenCalledTimes(1))
    expect(api.confirmRunEditionEntryTiming.mock.calls[0][4].expected_preview_fingerprint).toBe(hash('c'))
    expect(api.confirmRunEditionEntryTiming.mock.calls[0][4].timing.ranking_publication_override).toBeNull()
    expect(api.saveRunPackageWorkingDraft).not.toHaveBeenCalled()
    expect(await screen.findByText(/Potvrzeno pouze do Working Draftu/)).toBeInTheDocument()
    expect(screen.getByRole('link',{name:/Run Management a uložené revize/})).toHaveAttribute('href', expect.stringContaining('/admin/runs/run'))
    expect(screen.getByRole('link',{name:/skutečnou historii Saved Revisions/})).toHaveAttribute('href','/admin/runs/run/branches')
  })

  it('keeps exact command ID and full payload for explicit retry after an uncertain response', async () => {
    api.confirmRunEditionEntryTiming.mockRejectedValueOnce(new TypeError('network lost'))
    mount(); await fill(); await requestPreview()
    await userEvent.click(screen.getByRole('button',{name:'Výslovně potvrdit do Working Draftu'}))
    await screen.findByText(/Odpověď na potvrzení je nejistá/)
    const prior = api.confirmRunEditionEntryTiming.mock.calls[0][4]
    // The original request might have reached the backend. A new preview
    // would discard the only safe idempotent retry payload.
    expect(screen.getByRole('button',{name:'Spočítat serverový náhled'})).toBeDisabled()
    expect(screen.getByLabelText('Otevření Main – týden')).toBeDisabled()
    expect(api.previewRunEditionEntryTiming).toHaveBeenCalledTimes(1)
    await userEvent.click(screen.getByRole('button',{name:'Switch language'}))
    expect(screen.getByRole('button',{name:'Calculate server preview'})).toBeDisabled()
    expect(screen.getByRole('button',{name:'Retry the exact same command'})).toBeEnabled()
    await userEvent.click(screen.getByRole('button',{name:'Retry the exact same command'}))
    await waitFor(() => expect(api.confirmRunEditionEntryTiming).toHaveBeenCalledTimes(2))
    expect(api.confirmRunEditionEntryTiming.mock.calls[1][4]).toEqual(prior)
    expect(api.confirmRunEditionEntryTiming.mock.calls[1][4].command_id).toBe(prior.command_id)
    expect(api.previewRunEditionEntryTiming).toHaveBeenCalledTimes(1)
  })

  it('allows only the original immutable Confirm retry when the parent becomes read-only after lost response', async () => {
    api.confirmRunEditionEntryTiming.mockRejectedValueOnce(new TypeError('network lost'))
    const view = mount(); await fill(); await requestPreview()
    await userEvent.click(screen.getByRole('button',{name:'Výslovně potvrdit do Working Draftu'}))
    await screen.findByText(/Odpověď na potvrzení je nejistá/)
    const original = api.confirmRunEditionEntryTiming.mock.calls[0][4]
    view.rerender(<Frame><RunEditionEntryTimingPanel runId="run"
      branchId="branch" packageId="calendar-package" eventId="edition"
      calendar={calendar} enabled={false} /></Frame>)
    expect(screen.getByRole('button',{name:'Spočítat serverový náhled'})).toBeDisabled()
    expect(screen.getByLabelText('Otevření Main – týden')).toBeDisabled()
    expect(screen.getByRole('button',{name:'Zopakovat přesně stejný příkaz'})).toBeEnabled()
    await userEvent.click(screen.getByRole('button',{name:'Zopakovat přesně stejný příkaz'}))
    expect(await screen.findByText(/Potvrzeno pouze do Working Draftu/)).toBeInTheDocument()
    expect(api.confirmRunEditionEntryTiming).toHaveBeenCalledTimes(2)
    expect(api.confirmRunEditionEntryTiming.mock.calls[1][4]).toEqual(original)
    expect(api.previewRunEditionEntryTiming).toHaveBeenCalledTimes(1)
    expect(api.saveRunPackageWorkingDraft).not.toHaveBeenCalled()
  })

  it('suppresses writes when parent context is historical, foreign or otherwise unverified', async () => {
    mount({enabled:false})
    await screen.findByText(/není zapisovatelný/)
    expect(screen.getByRole('button',{name:'Spočítat serverový náhled'})).toBeDisabled()
    expect(api.previewRunEditionEntryTiming).not.toHaveBeenCalled()
    expect(api.confirmRunEditionEntryTiming).not.toHaveBeenCalled()
  })

  it('rejects foreign scope inspection and does not expose the editor', async () => {
    api.getRunEditionEntryTiming.mockRejectedValueOnce(new Error('Foreign Edition scope'))
    mount()
    await screen.findByText(/Čtení časování selhalo/)
    expect(screen.getByRole('button',{name:'Spočítat serverový náhled'})).toBeDisabled()
    expect(validEntryTimingInspection({...missing, branch_id:'other'},'run','branch','calendar-package','edition')).toBe(false)
  })

  it('does not equate JSON key ordering with an altered Run week or timing', () => {
    const reordered = {...calendar, schema_version:calendar.schema_version}
    const another: EditionEntryTiming = {...timing, main_open: {calendar: {
      start_year:reordered.start_year, weeks_per_year:reordered.weeks_per_year,
      season_count:reordered.season_count, season_start_year_week:reordered.season_start_year_week,
      schema_version:reordered.schema_version
    }, season_index:0,week:13}}
    expect(sameTiming(timing,another)).toBe(true)
    expect(verifiedRunCalendar({metadata_json:{run_calendar:calendar}} as never)).toEqual(calendar)
    expect(verifiedRunCalendar({metadata_json:{run_calendar:null}} as never)).toBeNull()
  })

  it('does not accept a delayed preview from another Run/Branch/Edition context', async () => {
    let finish!: (value: EntryTimingPreview) => void
    api.previewRunEditionEntryTiming.mockImplementationOnce(() => new Promise(resolve => { finish = resolve }))
    api.getRunEditionEntryTiming.mockImplementation(
      async (_run: string, branch: string) => ({ ...missing, branch_id: branch }))
    const view = mount()
    await fill()
    await userEvent.click(screen.getByRole('button',{name:'Spočítat serverový náhled'}))
    view.rerender(<Frame><RunEditionEntryTimingPanel runId="run" branchId="other"
      packageId="calendar-package" eventId="edition" calendar={calendar} enabled /></Frame>)
    await screen.findByText(/Pro tuto Edition zatím není uložený plán/)
    await act(async () => finish(preview))
    expect(screen.queryByText('Serverový náhled – bez zápisu')).not.toBeInTheDocument()
    expect(api.confirmRunEditionEntryTiming).not.toHaveBeenCalled()
  })

  it('sends an explicit final commitment and override, then removes the override as null', async () => {
    const updated: EditionEntryTiming = {
      ...timing, final_commitment: at(15), ranking_publication_override: at(14)
    }
    api.previewRunEditionEntryTiming.mockImplementation(async (
      _run: string, _branch: string, _pkg: string, _edition: string, input: EditionEntryTiming
    ) => ({ ...preview, timing:input, resolved:{
      ...preview.resolved, ranking_source: input.ranking_publication_override ?
        'explicit_publication_override' : 'after_main_closing_minus_one'
    }}))
    mount()
    await fill()
    await userEvent.click(screen.getByLabelText('Zadat vlastní Final Commitment'))
    fireEvent.change(screen.getByLabelText('Final Commitment – sezona'),{target:{value:'0'}})
    fireEvent.change(screen.getByLabelText('Final Commitment – týden'),{target:{value:'15'}})
    await userEvent.click(screen.getByLabelText('Použít explicitní publikaci Official Ranking'))
    fireEvent.change(screen.getByLabelText('Publikace rankingu – sezona'),{target:{value:'0'}})
    fireEvent.change(screen.getByLabelText('Publikace rankingu – týden'),{target:{value:'14'}})
    await userEvent.click(screen.getByRole('button',{name:'Spočítat serverový náhled'}))
    await waitFor(() => expect(api.previewRunEditionEntryTiming).toHaveBeenCalledWith(
      'run','branch','calendar-package','edition',updated
    ))
    await userEvent.click(screen.getByLabelText('Použít explicitní publikaci Official Ranking'))
    await userEvent.click(screen.getByRole('button',{name:'Spočítat serverový náhled'}))
    await waitFor(() => expect(api.previewRunEditionEntryTiming).toHaveBeenCalledTimes(2))
    expect(api.previewRunEditionEntryTiming.mock.calls[1][4].ranking_publication_override).toBeNull()
  })

  it('requires separate Save consent and fresh real scope/version/fingerprint verification', async () => {
    mount(); await fill(); await requestPreview()
    await userEvent.click(screen.getByRole('button',{name:'Výslovně potvrdit do Working Draftu'}))
    await screen.findByText(/Potvrzeno pouze do Working Draftu/)
    expect(api.saveRunPackageWorkingDraft).not.toHaveBeenCalled()
    expect(screen.getByRole('button',{name:'Samostatně uložit Working Draft'})).toBeDisabled()
    await userEvent.click(screen.getByLabelText(/Samostatně schvaluji uložení/))
    await userEvent.click(screen.getByRole('button',{name:'Samostatně uložit Working Draft'}))
    await waitFor(() => expect(api.saveRunPackageWorkingDraft).toHaveBeenCalledWith('run','branch',2))
    expect(api.getRunContainer).toHaveBeenCalledWith('run')
    expect(api.getBranchWorkingDraft).toHaveBeenCalledWith('run','branch')
    expect(api.getRunPackageState).toHaveBeenCalledWith('run','branch')
    expect(await screen.findByText(/Saved Revision byla uložena/)).toBeInTheDocument()
    expect(screen.getByRole('link',{name:/skutečnou historii Saved Revisions/})).toHaveAttribute(
      'href','/admin/runs/run/branches')
    expect(screen.getByLabelText('Otevření Main – týden')).toBeDisabled()
    expect(screen.getByRole('button',{name:'Spočítat serverový náhled'})).toBeDisabled()
    expect(screen.getByRole('button',{name:'Znovu načíst ze serveru'})).toBeDisabled()
    expect(api.previewRunEditionEntryTiming).toHaveBeenCalledTimes(1)
  })

  it('locks all repeated Save writes after a lost response, without claiming a Saved Revision', async () => {
    api.saveRunPackageWorkingDraft.mockRejectedValueOnce(new TypeError('network lost'))
    mount(); await fill(); await requestPreview()
    await userEvent.click(screen.getByRole('button',{name:'Výslovně potvrdit do Working Draftu'}))
    await screen.findByText(/Potvrzeno pouze do Working Draftu/)
    await userEvent.click(screen.getByLabelText(/Samostatně schvaluji uložení/))
    await userEvent.click(screen.getByRole('button',{name:'Samostatně uložit Working Draft'}))
    expect(await screen.findByText(/Výsledek Save je nejistý/)).toBeInTheDocument()
    expect(screen.getByText(/Save už mohl vytvořit Saved Revision/)).toBeInTheDocument()
    expect(screen.queryByText('Saved Revision byla uložena a potvrzena serverem.')).not.toBeInTheDocument()
    expect(screen.getByRole('button',{name:'Samostatně uložit Working Draft'})).toBeDisabled()
    expect(screen.getByRole('link',{name:/skutečnou historii Saved Revisions/})).toHaveAttribute(
      'href','/admin/runs/run/branches')
    expect(screen.getByLabelText(/Samostatně schvaluji uložení/)).toBeDisabled()
    expect(screen.getByRole('button',{name:'Znovu načíst ze serveru'})).toBeDisabled()
    expect(screen.getByRole('link',{name:/Run Management a uložené revize/})).toHaveAttribute(
      'href', expect.stringContaining('/admin/runs/run'))
    await userEvent.click(screen.getByRole('button',{name:'Switch language'}))
    expect(screen.getByText(/Uncertain Save outcome/)).toBeInTheDocument()
    expect(screen.getByRole('button',{name:'Save Working Draft separately'})).toBeDisabled()
    expect(api.saveRunPackageWorkingDraft).toHaveBeenCalledTimes(1)
  })

  it('fails closed on malformed Save receipt and never resends the unverified write', async () => {
    api.saveRunPackageWorkingDraft.mockResolvedValueOnce({
      run_id:'run',branch_id:'branch',saved_revision:{revision_id:'revision-new'},
      working_draft:{run_id:'run',branch_id:'foreign',base_saved_revision_id:'revision-new',status:'clean'}
    })
    mount(); await fill(); await requestPreview()
    await userEvent.click(screen.getByRole('button',{name:'Výslovně potvrdit do Working Draftu'}))
    await screen.findByText(/Potvrzeno pouze do Working Draftu/)
    await userEvent.click(screen.getByLabelText(/Samostatně schvaluji uložení/))
    await userEvent.click(screen.getByRole('button',{name:'Samostatně uložit Working Draft'}))
    expect(await screen.findByText(/Výsledek Save je nejistý/)).toBeInTheDocument()
    expect(screen.getByRole('button',{name:'Samostatně uložit Working Draft'})).toBeDisabled()
    expect(api.saveRunPackageWorkingDraft).toHaveBeenCalledTimes(1)
  })

  it('does not accept a non-string Saved Revision ID as proof of an actual Save', async () => {
    api.saveRunPackageWorkingDraft.mockResolvedValueOnce({
      run_id:'run',branch_id:'branch',saved_revision:{revision_id:12345},
      working_draft:{run_id:'run',branch_id:'branch',
        base_saved_revision_id:12345,status:'clean'}
    })
    mount(); await fill(); await requestPreview()
    await userEvent.click(screen.getByRole('button',{name:'Výslovně potvrdit do Working Draftu'}))
    await screen.findByText(/Potvrzeno pouze do Working Draftu/)
    await userEvent.click(screen.getByLabelText(/Samostatně schvaluji uložení/))
    await userEvent.click(screen.getByRole('button',{name:'Samostatně uložit Working Draft'}))
    expect(await screen.findByText(/Výsledek Save je nejistý/)).toBeInTheDocument()
    expect(screen.queryByText(/Saved Revision byla uložena a potvrzena serverem/)).not.toBeInTheDocument()
    expect(screen.getByRole('button',{name:'Samostatně uložit Working Draft'})).toBeDisabled()
    expect(api.saveRunPackageWorkingDraft).toHaveBeenCalledTimes(1)
  })

  it('fails closed on stale Draft version without making Save call', async () => {
    api.getBranchWorkingDraft.mockResolvedValue({
      run_id:'run',branch_id:'branch',status:'dirty',
      base_saved_revision_id:'head',draft_version:7
    })
    mount(); await fill(); await requestPreview()
    await userEvent.click(screen.getByRole('button',{name:'Výslovně potvrdit do Working Draftu'}))
    await screen.findByText(/Potvrzeno pouze do Working Draftu/)
    await userEvent.click(screen.getByLabelText(/Samostatně schvaluji uložení/))
    await userEvent.click(screen.getByRole('button',{name:'Samostatně uložit Working Draft'}))
    expect(await screen.findByText(/Uložení nelze bezpečně provést/)).toBeInTheDocument()
    expect(api.saveRunPackageWorkingDraft).not.toHaveBeenCalled()
    expect(screen.queryByText(/Výsledek Save je nejistý/)).not.toBeInTheDocument()
    expect(screen.getByRole('button',{name:'Samostatně uložit Working Draft'})).toBeEnabled()
  })

  it('keeps successful confirm receipt authoritative even when subsequent GET refresh fails', async () => {
    mount(); await fill(); await requestPreview()
    api.getRunEditionEntryTiming.mockRejectedValue(new Error('read unavailable'))
    await userEvent.click(screen.getByRole('button', { name: 'Výslovně potvrdit do Working Draftu' }))
    expect(await screen.findByText(/Potvrzeno pouze do Working Draftu/)).toBeInTheDocument()
    expect(await screen.findByText(/Potvrzení proběhlo, ale následné načtení stavu selhalo/)).toBeInTheDocument()
    expect(screen.queryByRole('button', {name: /Zopakovat přesně stejný příkaz/})).not.toBeInTheDocument()
    expect(api.confirmRunEditionEntryTiming).toHaveBeenCalledTimes(1)
    expect(api.saveRunPackageWorkingDraft).not.toHaveBeenCalled()
  })

  it('does not hide a failed explicit re-read behind cached data or reuse the old preview', async () => {
    mount(); await fill(); await requestPreview()
    api.getRunEditionEntryTiming.mockRejectedValueOnce(new Error('server unavailable'))
    await userEvent.click(screen.getByRole('button', { name: 'Znovu načíst ze serveru' }))
    expect(await screen.findByText(/Čtení časování selhalo: server unavailable/)).toBeInTheDocument()
    expect(screen.queryByRole('button', {name:'Výslovně potvrdit do Working Draftu'})).not.toBeInTheDocument()
    expect(screen.getByRole('button', {name:'Spočítat serverový náhled'})).toBeDisabled()
    expect(api.confirmRunEditionEntryTiming).not.toHaveBeenCalled()
  })

  it('rehydrates a changed server plan on explicit re-read without losing user audit or sending writes', async () => {
    mount(); await fill(); await requestPreview()
    const serverChanged = {...preview, timing:{...timing, main_open:at(18),
      main_duration_weeks:3, qualification_duration_weeks:2}}
    api.getRunEditionEntryTiming.mockResolvedValueOnce(serverChanged)
    await userEvent.click(screen.getByRole('button',{name:'Znovu načíst ze serveru'}))
    await waitFor(() => expect(screen.getByLabelText('Otevření Main – týden')).toHaveValue(18))
    expect(screen.getByLabelText('Délka Main (týdny)')).toHaveValue(3)
    expect(screen.getByLabelText('Délka kvalifikace Q (týdny)')).toHaveValue(2)
    expect(screen.getByLabelText('Operátor potvrzení')).toHaveValue('Operator')
    expect(screen.getByLabelText('Důvod potvrzení (audit)')).toHaveValue('Reviewed')
    expect(screen.queryByRole('button',{name:'Výslovně potvrdit do Working Draftu'})).not.toBeInTheDocument()
    expect(api.previewRunEditionEntryTiming).toHaveBeenCalledTimes(1)
    expect(api.confirmRunEditionEntryTiming).not.toHaveBeenCalled()
    expect(api.saveRunPackageWorkingDraft).not.toHaveBeenCalled()
  })

  it('freezes timing and audit inputs until a delayed explicit GET finishes', async () => {
    let finish!: (data: typeof missing) => void
    api.getRunEditionEntryTiming.mockResolvedValueOnce(missing)
      .mockImplementationOnce(() => new Promise(resolve => {finish = resolve}))
    mount(); await fill()
    const input = screen.getByLabelText('Otevření Main – týden')
    expect(input).toHaveValue(13)
    await userEvent.click(screen.getByRole('button',{name:'Znovu načíst ze serveru'}))
    await waitFor(() => expect(input).toBeDisabled())
    expect(screen.getByLabelText('Důvod potvrzení (audit)')).toBeDisabled()
    fireEvent.change(input,{target:{value:'20'}})
    expect(input).toHaveValue(13)
    await act(async () => finish(missing))
    await waitFor(() => expect(input).toBeEnabled())
    expect(input).toHaveValue(null)
    expect(screen.getByLabelText('Důvod potvrzení (audit)')).toHaveValue('Reviewed')
    expect(api.confirmRunEditionEntryTiming).not.toHaveBeenCalled()
    expect(api.saveRunPackageWorkingDraft).not.toHaveBeenCalled()
  })

  it('disables explicit re-read while retaining uncertain Confirm exact retry', async () => {
    api.confirmRunEditionEntryTiming.mockRejectedValueOnce(new TypeError('network lost'))
    mount(); await fill(); await requestPreview()
    await userEvent.click(screen.getByRole('button',{name:'Výslovně potvrdit do Working Draftu'}))
    await screen.findByText(/Odpověď na potvrzení je nejistá/)
    expect(screen.getByRole('button',{name:'Znovu načíst ze serveru'})).toBeDisabled()
    expect(screen.getByRole('button',{name:'Zopakovat přesně stejný příkaz'})).toBeEnabled()
    expect(api.getRunEditionEntryTiming).toHaveBeenCalledTimes(1)
  })

  it('discards an ordinary review on explicit re-read even if the GET is successful', async () => {
    mount(); await fill(); await requestPreview()
    expect(screen.getByRole('button', {name:'Výslovně potvrdit do Working Draftu'})).toBeEnabled()
    await userEvent.click(screen.getByRole('button', {name:'Znovu načíst ze serveru'}))
    expect(screen.queryByRole('button',{name:'Výslovně potvrdit do Working Draftu'})).not.toBeInTheDocument()
    expect(api.confirmRunEditionEntryTiming).not.toHaveBeenCalled()
  })

  it('locks reviewed inputs after confirm so an unsaved Working Draft cannot be accidentally discarded', async () => {
    mount(); await fill(); await requestPreview()
    await userEvent.click(screen.getByRole('button', {name:'Výslovně potvrdit do Working Draftu'}))
    expect(await screen.findByText(/Potvrzeno pouze do Working Draftu/)).toBeInTheDocument()
    expect(screen.getByLabelText('Otevření Main – týden')).toBeDisabled()
    expect(screen.getByRole('button', {name:'Spočítat serverový náhled'})).toBeDisabled()
    await userEvent.click(screen.getByLabelText(/Samostatně schvaluji uložení/))
    expect(screen.getByRole('button', {name:'Samostatně uložit Working Draft'})).toBeEnabled()
  })

  it('does not undo a Saved Revision or claim Save failed if subsequent cache invalidation fails', async () => {
    mount(); await fill(); await requestPreview()
    await userEvent.click(screen.getByRole('button', {name:'Výslovně potvrdit do Working Draftu'}))
    expect(await screen.findByText(/Potvrzeno pouze do Working Draftu/)).toBeInTheDocument()
    await waitFor(() => expect(api.getRunEditionEntryTiming.mock.calls.length).toBeGreaterThan(1))
    vi.spyOn(QueryClient.prototype, 'invalidateQueries').mockRejectedValue(new Error('cache unavailable'))
    await userEvent.click(screen.getByLabelText(/Samostatně schvaluji uložení/))
    await userEvent.click(screen.getByRole('button', {name:'Samostatně uložit Working Draft'}))
    expect(await screen.findByText(/Saved Revision byla uložena/)).toBeInTheDocument()
    expect(await screen.findByText(/Saved Revision byla vytvořena, ale obnovení náhledu selhalo/)).toBeInTheDocument()
    expect(api.saveRunPackageWorkingDraft).toHaveBeenCalledTimes(1)
    expect(screen.queryByRole('button',{name:'Samostatně uložit Working Draft'})).not.toBeInTheDocument()
  })
})
