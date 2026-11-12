import { useQuery } from '@tanstack/react-query'
import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'

import { getGlobalFullSimulationOperations, listBranchStates, listRunBranches, listRunContainers } from '../api/client'
import type { RunContainer } from '../api/types'
import { useLanguage } from '../i18n/LanguageContext'
import { rememberProductRun } from '../navigation/recentProductRuns'
import { formatApiError } from '../utils/apiErrors'
import { writeLastRunId } from '../viewer/activeRun'
import { isValidRunListView, readRunListViews, RUN_LIST_VIEWS_KEY, RUN_LIST_VIEWS_LIMIT, writeRunListViews } from './runListViews'
import type { RunListVisibility, SavedRunListView } from './runListViews'

type ViewNotice = 'viewSaved' | 'viewUpdated' | 'viewHidden' | 'viewRestored'
  | 'viewDuplicate' | 'viewInvalid' | 'viewLimit' | 'viewWriteFailed' | 'viewConflict' | 'viewExternalChange'
  | 'viewRenamed' | 'viewRenameDuplicate'

const namedViewMessagesPairs = {
  viewsTitle: ['Pojmenované pohledy', 'Named views'],
  viewsLocal: ['Ukládají se pouze v tomto prohlížeči. Obsahují jen filtry přehledu, nikoli Runy.', 'Saved only in this browser. Stores list filters, never Runs.'],
  quickView: ['Uložený pohled', 'Saved view'],
  chooseView: ['Vybrat pohled', 'Choose a view'],
  newViewName: ['Název nového pohledu', 'New view name'],
  saveView: ['Uložit nový pohled', 'Save new view'],
  updateView: ['Výslovně aktualizovat pohled', 'Explicitly update view'],
  viewChanged: ['Filtry byly změněny. Uložený pohled zůstává beze změny.', 'Filters changed. The saved view has not been overwritten.'],
  manageViews: ['Spravovat pohledy', 'Manage views'],
  reloadViews: ['Znovu načíst uložené pohledy', 'Reload saved views'],
  viewsManager: ['Správce pohledů', 'View manager'],
  noViews: ['Zatím žádné uložené pohledy.', 'No saved views yet.'],
  hideView: ['Skrýt', 'Hide'],
  restoreView: ['Obnovit', 'Restore'],
  hiddenView: ['Skrytý', 'Hidden'],
  renameView: ['Přejmenovat', 'Rename'],
  renameInput: ['Nový název pohledu', 'New view name'],
  saveRename: ['Uložit nový název', 'Save new name'],
  cancelRename: ['Zrušit přejmenování', 'Cancel rename'],
  viewRenamed: ['Pohled přejmenován.', 'View renamed.'],
  viewRenameDuplicate: ['Jiný pohled se stejným názvem již existuje.', 'Another view already has this name.'],
  viewSaved: ['Pohled uložen.', 'View saved.'],
  viewUpdated: ['Pohled výslovně aktualizován.', 'View explicitly updated.'],
  viewHidden: ['Pohled skryt z rychlé nabídky.', 'View hidden from quick selection.'],
  viewRestored: ['Pohled obnoven.', 'View restored.'],
  viewDuplicate: ['Pohled se stejným názvem již existuje. Vyber jej a použij výslovnou aktualizaci.', 'A view with this name already exists. Select it and explicitly update it.'],
  viewInvalid: ['Zadej název (max. 64 znaků) a hledání do 250 znaků.', 'Enter a name (up to 64 characters) and search text up to 250 characters.'],
  viewLimit: ['Byl dosažen limit 24 pohledů.', 'The limit of 24 views has been reached.'],
  viewWriteFailed: ['Nastavení se nepodařilo uložit do prohlížeče. Změna nebyla provedena.', 'Could not save settings in this browser. No change was applied.'],
  viewConflict: ['Uložené pohledy se mezitím změnily v jiném panelu. Původní data nebyla přepsána; ověř nové pohledy a změnu případně zopakuj.', 'Saved views changed in another tab. The newer data was not overwritten; review the views and try again if needed.'],
  viewExternalChange: ['Uložené pohledy se změnily v jiném panelu. Filtry zůstaly beze změny; pro použití vyber pohled znovu.', 'Saved views changed in another tab. Current filters stayed unchanged; reselect a view to apply it.'],
  viewInvalidStorage: ['Uložené nastavení pohledů je poškozené. Zůstává nedotčené; základní filtry fungují.', 'Saved view settings are corrupted. Left untouched; basic filters still work.'],
  viewUnsupportedStorage: ['Nastavení pohledů má nepodporovanou verzi. Nebude přepsáno.', 'Saved view settings use an unsupported version and will not be overwritten.'],
  viewUnavailableStorage: ['Úložiště prohlížeče není dostupné. Ukládání pohledů je vypnuté.', 'Browser storage is unavailable. Saving views is disabled.'],
} as const

function namedViewMessages(language: 'cs' | 'en'): Record<keyof typeof namedViewMessagesPairs, string> {
  const column = language === 'cs' ? 0 : 1
  return Object.fromEntries(
    Object.entries(namedViewMessagesPairs).map(([key, translations]) => [key, translations[column]])
  ) as Record<keyof typeof namedViewMessagesPairs, string>
}

const messages = {
  cs: {
    title: 'Runy', subtitle: 'Nezávislé uložené světy a jejich skutečné větve. Výběr větve mění pouze kontext Adminu.',
    create: 'Vytvořit prázdný Run', search: 'Hledat Run', placeholder: 'Název nebo ID Runu',
    openRun: 'Otevřít Run', refreshRuns: 'Obnovit seznam Runů', refreshingRuns: 'Obnovuji seznam Runů…',
    visibility: 'Typ Runu', allRuns: 'Všechny Runy', editableOnly: 'Pouze upravitelné', protectedOnly: 'Pouze chráněné',
    visibleCount: 'Zobrazeno', resetFilters: 'Zrušit filtry',
    ...namedViewMessages('cs'),

    empty: 'Zatím žádné uložené Runy.', noResults: 'Žádný Run neodpovídá hledání.',
    loading: 'Načítám uložené Runy…', error: 'Přehled Runů není dostupný',
    protected: 'Chráněný zdroj', editable: 'Upravitelný', branches: 'Větve',
    open: 'Otevřít', history: 'Historie a větve', missing: 'Čas není dostupný', inventoryMismatch: 'Nekonzistentní identita inventáře',
    noBranches: 'Run nemá dostupné větve.', branchError: 'Větve nejsou dostupné',
    legacy: 'Starší diagnostika simulačních Runů', legacyNote: 'Legacy výsledky jsou oddělené a nejsou kanonickými Product Run daty.',
    viewer: 'Zobrazuje Viewer',
    operationsTitle: 'Rozpracované Full Simulation',
    operationsNote: 'Údaje pocházejí z uložených serverových záznamů. Stav „Povoleno“ neprokazuje, že právě běží proces. Po návratu zkontroluj konkrétní Run a větev; simulace se sama nespouští.',
    operationsEmpty: 'Žádná obnovitelná Full Simulation není uložená.',
    operationsLoading: 'Načítám uložené simulace…',
    operationsError: 'Přehled simulací není dostupný',
    operationsLegacy: 'Starší záznamy bez ověřitelného příkazu k obnovení',
    operationOpen: 'Otevřít ovládání',
    operationProgress: 'Dokončené sezony',
    operationFinalWeeks: 'Týdny poslední sezony',
    operationTarget: 'Původní cíl',
    operationWorker: 'Aktivita procesu nepotvrzena',
    operationState: {running: 'Povoleno – proces neověřen', pause_requested: 'Čeká na bezpečné pozastavení', paused: 'Pozastaveno'}
  },
  en: {
    title: 'Runs', subtitle: 'Independent saved worlds and their actual Branches. Selecting a Branch changes Admin context only.',
    create: 'Create empty Run', search: 'Search Runs', placeholder: 'Run name or ID',
    openRun: 'Open Run', refreshRuns: 'Refresh Run list', refreshingRuns: 'Refreshing Run list…',
    visibility: 'Run type', allRuns: 'All Runs', editableOnly: 'Editable only', protectedOnly: 'Protected only',
    visibleCount: 'Showing', resetFilters: 'Clear filters',
    ...namedViewMessages('en'),

    empty: 'No saved Runs yet.', noResults: 'No Runs match your search.',
    loading: 'Loading saved Runs…', error: 'Runs inventory unavailable',
    protected: 'Protected source', editable: 'Editable', branches: 'Branches',
    open: 'Open', history: 'History & Branches', missing: 'Time unavailable', inventoryMismatch: 'Inconsistent inventory identity',
    noBranches: 'No Branches available for this Run.', branchError: 'Branches unavailable',
    legacy: 'Legacy Simulation Run diagnostics', legacyNote: 'Legacy results are separate from canonical Product Run data.',
    viewer: 'Shown in Viewer',
    operationsTitle: 'Pending Full Simulations',
    operationsNote: 'This is persisted server evidence, not a live worker monitor. Authorized does not prove that a process is running. Reopen the exact Run and Branch to inspect it; nothing restarts automatically.',
    operationsEmpty: 'No recoverable Full Simulation parent is stored.',
    operationsLoading: 'Loading stored simulations…',
    operationsError: 'Simulation inventory unavailable',
    operationsLegacy: 'Legacy records without a verified resume command',
    operationOpen: 'Open controls',
    operationProgress: 'Completed seasons',
    operationFinalWeeks: 'Final season weeks',
    operationTarget: 'Original target',
    operationWorker: 'Worker activity unknown',
    operationState: {running: 'Authorized – worker unverified', pause_requested: 'Pause requested', paused: 'Paused'}
  }
}

function BranchList({ run }: { run: RunContainer }): JSX.Element {
  const { language } = useLanguage()
  const l = messages[language]
  const branchesQuery = useQuery({
    queryKey: ['runs-inventory-branches', run.run_id],
    queryFn: () => listRunBranches(run.run_id),
    retry: false
  })
  const statesQuery = useQuery({
    queryKey: ['runs-inventory-states', run.run_id],
    queryFn: () => listBranchStates({ run_id: run.run_id }),
    retry: false
  })
  const rawBranches = branchesQuery.data?.run_branches
  const branchesValid = Array.isArray(rawBranches) && rawBranches.every(b =>
    b && b.run_id === run.run_id && typeof b.branch_id === 'string' && Boolean(b.branch_id.trim())
  ) && new Set(rawBranches.map(b => b.branch_id)).size === rawBranches.length
  const branches = branchesValid ? rawBranches : []

  const rawStates = statesQuery.data?.branch_states
  const statesValid = Array.isArray(rawStates) && rawStates.every(s =>
    s && s.run_id === run.run_id && typeof s.branch_id === 'string' && Boolean(s.branch_id.trim())
  ) && new Set(rawStates.map(s => s.branch_id)).size === rawStates.length
  const states = statesValid ? rawStates : []

  const viewerBranchId = run.viewer_branch_id ?? run.official_branch_id

  return <div className="runs-canonical-branches">
    {branchesQuery.isPending && <p role="status">{l.loading}</p>}
    {branchesQuery.isError && <p role="alert" className="error">{l.branchError}: {formatApiError(branchesQuery.error)}</p>}
    {branchesQuery.isSuccess && !branchesValid && <p role="alert" className="error">{l.inventoryMismatch}</p>}
    {branchesQuery.isSuccess && branchesValid && branches.length === 0 && <p className="status">{l.noBranches}</p>}
    {statesQuery.isError && <p role="alert" className="error">{l.missing}: {formatApiError(statesQuery.error)}</p>}
    {statesQuery.isSuccess && !statesValid && <p role="alert" className="error">{l.missing}: {l.inventoryMismatch}</p>}
    {branches.map(branch => {
      const state = statesValid ? states.find(item => item.branch_id === branch.branch_id) : null
      const season = state && typeof state.current_season === 'number' && Number.isSafeInteger(state.current_season) && state.current_season > 0
        ? `${state.current_season}/${String((state.current_season + 1) % 100).padStart(2, '0')}` : null
      const week = state && typeof state.current_week === 'number' && Number.isSafeInteger(state.current_week) && state.current_week > 0
        ? `W${state.current_week}` : null
      const target = `/admin/runs/${encodeURIComponent(run.run_id)}?branch=${encodeURIComponent(branch.branch_id)}`
      return <div className="runs-canonical-branch" key={branch.branch_id}>
        <div>
          <strong>{branch.display_name || branch.branch_id}</strong>
          <span className="status">{season || l.missing}{week ? ` · ${week}` : ''}</span>
          {branch.branch_id === viewerBranchId && <small className="status">{l.viewer}</small>}
        </div>
        <Link to={target} className="button-link" onClick={() => {
          writeLastRunId(run.run_id)
          rememberProductRun(run.run_id)
        }}>{l.open}</Link>
      </div>
    })}
  </div>
}

function RunRow({ run }: { run: RunContainer }): JSX.Element {
  const [expanded, setExpanded] = useState(false)
  const { language } = useLanguage()
  const l = messages[language]
  return <li className="runs-canonical-row">
    <div className="runs-canonical-row__top">
      <div className="runs-canonical-row__identity">
        <strong>{run.display_name || run.run_id}</strong>
        <small className="status">{run.run_id} · {run.read_only ? l.protected : l.editable} · {run.status}</small>
      </div>
      <div className="runs-canonical-row__actions">
        <Link to={`/admin/runs/${encodeURIComponent(run.run_id)}`} onClick={() => {
          writeLastRunId(run.run_id)
          rememberProductRun(run.run_id)
        }}>{l.openRun}</Link>
        <Link to={`/admin/runs/${encodeURIComponent(run.run_id)}/branches`} onClick={() => {
          writeLastRunId(run.run_id)
          rememberProductRun(run.run_id)
        }}>{l.history}</Link>
        <button type="button" aria-expanded={expanded} onClick={() => setExpanded(value => !value)}>
          {l.branches} {expanded ? '−' : '+'}
        </button>
      </div>
    </div>
    {expanded && <BranchList run={run} />}
  </li>
}

export function RunsPage(): JSX.Element {
  const { language } = useLanguage()
  const l = messages[language]
  const [query, setQuery] = useState('')
  const [visibility, setVisibility] = useState<RunListVisibility>('all')
  const [savedViews, setSavedViews] = useState(readRunListViews)
  const [selectedViewName, setSelectedViewName] = useState('')
  const [newViewName, setNewViewName] = useState('')
  const [manageViews, setManageViews] = useState(false)
  const [renamingViewName, setRenamingViewName] = useState('')
  const [renameDraft, setRenameDraft] = useState('')
  const [viewNotice, setViewNotice] = useState<ViewNotice | null>(null)
  const selectedView = savedViews.items.find(view => view.name === selectedViewName)
  const viewChanged = Boolean(selectedView && (query !== selectedView.query || visibility !== selectedView.visibility))

  function acceptStoredViews(next: ReturnType<typeof readRunListViews>, notice: ViewNotice | null): void {
    setSavedViews(next)
    setSelectedViewName(current => next.items.some(view => view.name === current && !view.hidden) ? current : '')
    setRenamingViewName('')
    setRenameDraft('')
    setViewNotice(notice)
  }

  // The StorageEvent fires in OTHER same-origin tabs, not for this tab's own write.
  // Never apply a remotely edited preference to the active filters automatically.
  useEffect(() => {
    const onStorage = (event: StorageEvent) => {
      if (event.key !== null && event.key !== RUN_LIST_VIEWS_KEY) return
      acceptStoredViews(readRunListViews(), 'viewExternalChange')
    }
    window.addEventListener('storage', onStorage)
    return () => window.removeEventListener('storage', onStorage)
  }, [])

  function persistViews(items: SavedRunListView[], notice: ViewNotice): boolean {
    if (savedViews.status !== 'ok') {
      setViewNotice('viewWriteFailed')
      return false
    }
    // Best-effort stale-tab protection: don't silently replace a different
    // version written since this page loaded. localStorage has no atomic CAS.
    const latest = readRunListViews()
    if (latest.status !== 'ok' || JSON.stringify(latest.items) !== JSON.stringify(savedViews.items)) {
      acceptStoredViews(latest, 'viewConflict')
      return false
    }
    if (!writeRunListViews(items)) {
      setViewNotice('viewWriteFailed')
      return false
    }
    setSavedViews({ status: 'ok', items })
    setViewNotice(notice)
    return true
  }

  function saveNewView(): void {
    const view: SavedRunListView = {
      name: newViewName.trim(), query, visibility, hidden: false
    }
    if (!isValidRunListView(view)) {
      setViewNotice('viewInvalid')
      return
    }
    if (savedViews.items.some(item => item.name.toLocaleLowerCase() === view.name.toLocaleLowerCase())) {
      setViewNotice('viewDuplicate')
      return
    }
    if (savedViews.items.length >= RUN_LIST_VIEWS_LIMIT) {
      setViewNotice('viewLimit')
      return
    }
    if (persistViews([...savedViews.items, view], 'viewSaved')) {
      setSelectedViewName(view.name)
      setNewViewName('')
    }
  }

  function selectView(name: string): void {
    const view = savedViews.items.find(item => item.name === name && !item.hidden)
    setSelectedViewName(view?.name ?? '')
    if (view) {
      setQuery(view.query)
      setVisibility(view.visibility)
    }
    setViewNotice(null)
  }

  function updateSelectedView(): void {
    if (!selectedView) return
    const updated = { ...selectedView, query, visibility }
    if (!isValidRunListView(updated)) {
      setViewNotice('viewInvalid')
      return
    }
    persistViews(savedViews.items.map(item => item.name === selectedView.name ? updated : item), 'viewUpdated')
  }

  function renameView(view: SavedRunListView): void {
    const name = renameDraft.trim()
    const updated = { ...view, name }
    if (!isValidRunListView(updated)) {
      setViewNotice('viewInvalid')
      return
    }
    if (savedViews.items.some(item =>
      item.name !== view.name && item.name.toLocaleLowerCase() === name.toLocaleLowerCase()
    )) {
      setViewNotice('viewRenameDuplicate')
      return
    }
    if (name === view.name) {
      setRenamingViewName('')
      setRenameDraft('')
      setViewNotice(null)
      return
    }
    if (persistViews(savedViews.items.map(item => item.name === view.name ? updated : item), 'viewRenamed')) {
      setSelectedViewName(current => current === view.name ? name : current)
      setRenamingViewName('')
      setRenameDraft('')
    }
  }

  function toggleHiddenView(name: string): void {
    const existing = savedViews.items.find(item => item.name === name)
    if (!existing) return
    if (persistViews(savedViews.items.map(item => item.name === name
      ? { ...item, hidden: !item.hidden } : item), existing.hidden ? 'viewRestored' : 'viewHidden')
      && !existing.hidden && selectedViewName === name) setSelectedViewName('')
  }
  const runsQuery = useQuery({
    queryKey: ['canonical-run-containers'],
    queryFn: listRunContainers,
    retry: false
  })
  const operationsQuery = useQuery({
    queryKey: ['global-full-simulation-operations'],
    queryFn: getGlobalFullSimulationOperations,
    retry: false,
    refetchInterval: 10000
  })
  const runs = useMemo(() => runsQuery.data?.run_containers.filter(run => (
    `${run.display_name ?? ''} ${run.run_id}`.toLocaleLowerCase().includes(query.trim().toLocaleLowerCase()) &&
    (visibility === 'all' || (visibility === 'protected' ? run.read_only : !run.read_only))
  )) ?? [], [runsQuery.data, query, visibility])

  return <section className="panel runs-canonical">
    <div className="page-intro"><h2>{l.title}</h2><p className="subtitle">{l.subtitle}</p></div>
    <p><Link to="/admin/operations">{language === 'cs' ? 'Otevřít Centrum simulací s filtrováním a ruční aktualizací →' : 'Open Simulation Task Center with filters and refresh →'}</Link></p>
    <section className="panel" aria-label={l.operationsTitle}>
      <h3>{l.operationsTitle}</h3>
      <p className="status">{l.operationsNote}</p>
      {operationsQuery.isPending && <p role="status">{l.operationsLoading}</p>}
      {operationsQuery.isError && <p role="alert" className="error">{l.operationsError}: {formatApiError(operationsQuery.error)}</p>}
      {operationsQuery.isSuccess && operationsQuery.data.pending_count === 0 && (
        <p className="status">{l.operationsEmpty}</p>
      )}
      {operationsQuery.isSuccess && operationsQuery.data.legacy_pending_count > 0 && (
        <p className="status">{l.operationsLegacy}: {operationsQuery.data.legacy_pending_count}</p>
      )}
      {operationsQuery.isSuccess && operationsQuery.data.operations.length > 0 && (
        <ul aria-label={l.operationsTitle}>
          {operationsQuery.data.operations.map(operation => (
            <li key={JSON.stringify([operation.run_id, operation.branch_id, operation.command_id])}>
              <strong>{operation.run_name} · {operation.branch_name}</strong>
              <p className="status">
                {l.operationState[operation.control_state]} · {l.operationWorker}
              </p>
              <p className="status">
                {l.operationProgress}: {operation.completed_season_count} · {l.operationFinalWeeks}: {operation.final_completed_week_count}
                {' · '}{l.operationTarget}: S{operation.final_week.season_index} W{operation.final_week.week}
              </p>
              <small className="status">{operation.command_id} · {operation.run_id} / {operation.branch_id}</small>
              {' '}
              <Link
                to={`/admin/runs/${encodeURIComponent(operation.run_id)}/simulate?branch=${encodeURIComponent(operation.branch_id)}`}
                onClick={() => {
                  writeLastRunId(operation.run_id)
                  rememberProductRun(operation.run_id)
                }}
              >{l.operationOpen}</Link>
            </li>
          ))}
        </ul>
      )}
    </section>
    <div className="runs-canonical-toolbar">
      <label>{l.search}<input type="search" value={query} onChange={event => setQuery(event.target.value)} placeholder={l.placeholder} /></label>
      <label>{l.visibility}<select value={visibility} onChange={event => setVisibility(event.target.value as typeof visibility)}>
        <option value="all">{l.allRuns}</option>
        <option value="editable">{l.editableOnly}</option>
        <option value="protected">{l.protectedOnly}</option>
      </select></label>
      {(query || visibility !== 'all') && <button type="button" onClick={() => { setQuery(''); setVisibility('all') }}>{l.resetFilters}</button>}
      <button type="button" disabled={runsQuery.isFetching} onClick={() => { void runsQuery.refetch() }}>{runsQuery.isFetching ? l.refreshingRuns : l.refreshRuns}</button>
      <Link className="button-link" to="/admin/runs/new">{l.create}</Link>
    </div>
    <section className="panel" aria-label={l.viewsTitle}>
      <h3>{l.viewsTitle}</h3>
      <p className="status">{l.viewsLocal}</p>
      {savedViews.status !== 'ok' && <p role="alert" className="error">{savedViews.status === 'invalid'
        ? l.viewInvalidStorage : savedViews.status === 'unsupported'
          ? l.viewUnsupportedStorage : l.viewUnavailableStorage}</p>}
      <div className="runs-canonical-toolbar">
        <label>{l.quickView}<select value={selectedViewName} onChange={event => selectView(event.target.value)}>
          <option value="">{l.chooseView}</option>
          {savedViews.items.filter(view => !view.hidden).map(view =>
            <option key={view.name} value={view.name}>{view.name}</option>)}
        </select></label>
        <form className="runs-canonical-toolbar" onSubmit={event => { event.preventDefault(); saveNewView() }}>
          <label>{l.newViewName}<input type="text" maxLength={64} value={newViewName}
            onChange={event => setNewViewName(event.target.value)} /></label>
          <button type="submit" disabled={savedViews.status !== 'ok'}>{l.saveView}</button>
        </form>
        {selectedView && <button type="button" disabled={savedViews.status !== 'ok' || !viewChanged}
          onClick={updateSelectedView}>{l.updateView}</button>}
        <button type="button" aria-expanded={manageViews} onClick={() => setManageViews(open => !open)}>{l.manageViews}</button>
        <button type="button" onClick={() => acceptStoredViews(readRunListViews(), null)}>{l.reloadViews}</button>
      </div>
      {viewChanged && <p className="status">{l.viewChanged}</p>}
      {viewNotice && <p role={['viewDuplicate', 'viewInvalid', 'viewLimit', 'viewWriteFailed', 'viewConflict', 'viewRenameDuplicate'].includes(viewNotice) ? 'alert' : 'status'}>
        {l[viewNotice]}</p>}
      {manageViews && <div>
        <h4>{l.viewsManager}</h4>
        {savedViews.items.length === 0 && <p>{l.noViews}</p>}
        <ul aria-label={l.viewsManager}>
          {savedViews.items.map(view => <li key={view.name}>
            <span>{view.name}{view.hidden ? ' · ' + l.hiddenView : ''}</span>{' '}
            <button type="button" disabled={savedViews.status !== 'ok'}
              aria-label={(view.hidden ? l.restoreView : l.hideView) + ': ' + view.name}
              onClick={() => toggleHiddenView(view.name)}>
              {view.hidden ? l.restoreView : l.hideView}
            </button>{' '}
            {renamingViewName === view.name
              ? <form onSubmit={event => { event.preventDefault(); renameView(view) }}>
                <label>{l.renameInput}<input type="text" maxLength={64}
                  value={renameDraft} onChange={event => setRenameDraft(event.target.value)} /></label>
                <button type="submit" disabled={savedViews.status !== 'ok'}>{l.saveRename}</button>{' '}
                <button type="button" onClick={() => {
                  setRenamingViewName('')
                  setRenameDraft('')
                  setViewNotice(null)
                }}>{l.cancelRename}</button>
              </form>
              : <button type="button" disabled={savedViews.status !== 'ok'}
                aria-label={l.renameView + ': ' + view.name}
                onClick={() => {
                  setRenamingViewName(view.name)
                  setRenameDraft(view.name)
                  setViewNotice(null)
                }}>{l.renameView}</button>}
          </li>)}
        </ul>
      </div>}
    </section>
    {runsQuery.isPending && <p role="status">{l.loading}</p>}
    {runsQuery.isSuccess && runsQuery.data.run_containers.length > 0 &&
      <p className="status">{l.visibleCount}: {runs.length} / {runsQuery.data.run_containers.length}</p>}
    {runsQuery.isError && <p role="alert" className="error">{l.error}: {formatApiError(runsQuery.error)}</p>}
    {runsQuery.isSuccess && runsQuery.data.run_containers.length === 0 && <p>{l.empty}</p>}
    {runsQuery.isSuccess && runsQuery.data.run_containers.length > 0 && runs.length === 0 && <p>{l.noResults}</p>}
    <ul className="runs-canonical-list" aria-label={language === 'cs' ? 'Product Runy' : 'Product Runs'}>{runs.map(run => <RunRow key={run.run_id} run={run} />)}</ul>
    <div className="runs-legacy-entry">
      <p className="status">{l.legacyNote}</p>
      <Link to="/admin/legacy-runs">{l.legacy}</Link>
    </div>
  </section>
}
