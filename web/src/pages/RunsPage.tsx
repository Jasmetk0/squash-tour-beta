import { useQuery } from '@tanstack/react-query'
import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'

import { listBranchStates, listRunBranches, listRunContainers } from '../api/client'
import type { RunContainer } from '../api/types'
import { useLanguage } from '../i18n/LanguageContext'
import { rememberProductRun } from '../navigation/recentProductRuns'
import { formatApiError } from '../utils/apiErrors'
import { writeLastRunId } from '../viewer/activeRun'

const messages = {
  cs: {
    title: 'Runy', subtitle: 'Nezávislé uložené světy a jejich skutečné větve. Výběr větve mění pouze kontext Adminu.',
    create: 'Vytvořit prázdný Run', search: 'Hledat Run', placeholder: 'Název nebo ID Runu',
    empty: 'Zatím žádné uložené Runy.', noResults: 'Žádný Run neodpovídá hledání.',
    loading: 'Načítám uložené Runy…', error: 'Přehled Runů není dostupný',
    protected: 'Chráněný zdroj', editable: 'Upravitelný', branches: 'Větve',
    open: 'Otevřít', history: 'Historie a větve', missing: 'Čas není dostupný',
    noBranches: 'Run nemá dostupné větve.', branchError: 'Větve nejsou dostupné',
    legacy: 'Starší diagnostika simulačních Runů', legacyNote: 'Legacy výsledky jsou oddělené a nejsou kanonickými Product Run daty.',
    viewer: 'Zobrazuje Viewer'
  },
  en: {
    title: 'Runs', subtitle: 'Independent saved worlds and their actual Branches. Selecting a Branch changes Admin context only.',
    create: 'Create empty Run', search: 'Search Runs', placeholder: 'Run name or ID',
    empty: 'No saved Runs yet.', noResults: 'No Runs match your search.',
    loading: 'Loading saved Runs…', error: 'Runs inventory unavailable',
    protected: 'Protected source', editable: 'Editable', branches: 'Branches',
    open: 'Open', history: 'History & Branches', missing: 'Time unavailable',
    noBranches: 'No Branches available for this Run.', branchError: 'Branches unavailable',
    legacy: 'Legacy Simulation Run diagnostics', legacyNote: 'Legacy results are separate from canonical Product Run data.',
    viewer: 'Shown in Viewer'
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
  const branches = branchesQuery.data?.run_branches.filter(branch => branch.run_id === run.run_id) ?? []
  const states = statesQuery.data?.branch_states.filter(state => state.run_id === run.run_id) ?? []
  const viewerBranchId = run.viewer_branch_id ?? run.official_branch_id

  return <div className="runs-canonical-branches">
    {branchesQuery.isPending && <p role="status">{l.loading}</p>}
    {branchesQuery.isError && <p role="alert" className="error">{l.branchError}: {formatApiError(branchesQuery.error)}</p>}
    {branchesQuery.isSuccess && branches.length === 0 && <p className="status">{l.noBranches}</p>}
    {statesQuery.isError && <p role="alert" className="error">{l.missing}: {formatApiError(statesQuery.error)}</p>}
    {branches.map(branch => {
      const state = states.find(item => item.branch_id === branch.branch_id)
      const season = state && typeof state.current_season === 'number' && Number.isInteger(state.current_season)
        ? `${state.current_season}/${String((state.current_season + 1) % 100).padStart(2, '0')}` : null
      const week = state && typeof state.current_week === 'number' && Number.isInteger(state.current_week)
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
  const runsQuery = useQuery({
    queryKey: ['canonical-run-containers'],
    queryFn: listRunContainers,
    retry: false
  })
  const runs = useMemo(() => runsQuery.data?.run_containers.filter(run => (
    `${run.display_name ?? ''} ${run.run_id}`.toLocaleLowerCase().includes(query.trim().toLocaleLowerCase())
  )) ?? [], [runsQuery.data, query])

  return <section className="panel runs-canonical">
    <div className="page-intro"><h2>{l.title}</h2><p className="subtitle">{l.subtitle}</p></div>
    <div className="runs-canonical-toolbar">
      <label>{l.search}<input type="search" value={query} onChange={event => setQuery(event.target.value)} placeholder={l.placeholder} /></label>
      <Link className="button-link" to="/admin/runs/new">{l.create}</Link>
    </div>
    {runsQuery.isPending && <p role="status">{l.loading}</p>}
    {runsQuery.isError && <p role="alert" className="error">{l.error}: {formatApiError(runsQuery.error)}</p>}
    {runsQuery.isSuccess && runsQuery.data.run_containers.length === 0 && <p>{l.empty}</p>}
    {runsQuery.isSuccess && runsQuery.data.run_containers.length > 0 && runs.length === 0 && <p>{l.noResults}</p>}
    <ul className="runs-canonical-list" aria-label="Product Runs">{runs.map(run => <RunRow key={run.run_id} run={run} />)}</ul>
    <div className="runs-legacy-entry">
      <p className="status">{l.legacyNote}</p>
      <Link to="/admin/legacy-runs">{l.legacy}</Link>
    </div>
  </section>
}
