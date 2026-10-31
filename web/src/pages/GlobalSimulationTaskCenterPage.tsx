import { BoundaryDescription } from '../components/FullSimulationBoundaryTargets'
import { FullSimulationServerTasks, useServerTasks } from '../components/FullSimulationServerTasks'
import { useQuery } from '@tanstack/react-query'
import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'

import { getGlobalFullSimulationOperations } from '../api/client'
import type { GlobalFullSimulationOperation } from '../api/types'
import { useLanguage } from '../i18n/LanguageContext'
import { rememberProductRun } from '../navigation/recentProductRuns'
import { formatApiError } from '../utils/apiErrors'
import { writeLastRunId } from '../viewer/activeRun'

type OperationStateFilter = 'all' | GlobalFullSimulationOperation['control_state']

const copy = {
  cs: {
    title: 'Centrum simulací',
    subtitle: 'Globální přehled uložených Full Simulation napříč Runy a větvemi.',
    truth: 'Jde o uložené záznamy postupu, nikoli o sledování běžících procesů. Stav „Povoleno“ neznamená, že server právě simuluje. Obnovení vyžaduje výslovnou akci ve správné větvi.',
    loading: 'Načítám uložené simulace…',
    unavailable: 'Přehled rozpracovaných simulací není dostupný',
    refresh: 'Obnovit údaje',
    refreshing: 'Obnovuji…',
    count: 'Obnovitelné záznamy',
    legacy: 'Starší záznamy bez ověřitelného příkazu k obnovení',
    empty: 'Nejsou uložené žádné obnovitelné Full Simulation.',
    noMatches: 'Zadaným filtrům neodpovídá žádná uložená simulace.',
    search: 'Hledat Run, větev nebo ID příkazu',
    searchPlaceholder: 'Název, ID Runu, Branch nebo příkazu',
    filter: 'Stav uložené operace',
    all: 'Všechny stavy',
    state: {
      running: 'Povoleno – aktivita procesu nepotvrzena',
      pause_requested: 'Požadováno pozastavení',
      paused: 'Pozastaveno'
    },
    run: 'Run',
    branch: 'Větev',
    command: 'ID příkazu',
    progress: 'Dokončené sezony',
    finalWeeks: 'Dokončené týdny poslední sezony',
    from: 'Původní začátek',
    target: 'Původní cíl',
    worker: 'Skutečná aktivita workeru není potvrzena',
    lease: {
      absent: 'Bez aktuální execution lease',
      matching_active: 'Platná lease této simulace (nikoli potvrzení zdraví procesu)',
      matching_expired: 'Expirovaná lease této simulace',
      other_active: 'Globální lease aktuálně drží jiná simulace',
      other_expired: 'Uložená expirovaná lease patří jiné simulaci'
    },
    readonly: 'Jen pro čtení; možnost pokračovat musí ověřit cílový Run a větev.',
    inspect: 'Otevřít detail a ovládání',
    runs: 'Otevřít seznam Runů',
    receiptsTitle: 'Starší pending receipts · neznamenají další běžící workery',
    linked: 'Tento původní příkaz už patří serverové úloze uvedené výše:',
    linkedDetail: 'Zobrazit původní pending receipt',
    distinction: 'Serverové úlohy mají vlastní stav, heartbeat a explicitní obnovu. Níže jsou samostatně uchované historické příkazy; záznam propojený s úlohou není další simulace.',
    ambiguousLink: 'Tento příkaz je nejednoznačně spojen s více serverovými úlohami a nelze jej bezpečně propojit.'
  },
  en: {
    title: 'Simulation Task Center',
    subtitle: 'Global inventory of persisted Full Simulations across Runs and Branches.',
    truth: 'These are persisted progress receipts, not a monitor of executing workers. “Authorized” does not mean the server is currently simulating. Resuming requires an explicit action in the exact Branch.',
    loading: 'Loading stored simulations…',
    unavailable: 'Pending simulation inventory is unavailable',
    refresh: 'Refresh evidence',
    refreshing: 'Refreshing…',
    count: 'Recoverable receipts',
    legacy: 'Legacy receipts without verified resume commands',
    empty: 'There are no recoverable Full Simulation receipts.',
    noMatches: 'No saved simulation matches your filters.',
    search: 'Search Run, Branch or command ID',
    searchPlaceholder: 'Name, Run ID, Branch ID or command ID',
    filter: 'Saved control state',
    all: 'All states',
    state: {
      running: 'Authorized – worker activity unverified',
      pause_requested: 'Pause requested',
      paused: 'Paused'
    },
    run: 'Run',
    branch: 'Branch',
    command: 'Command ID',
    progress: 'Completed seasons',
    finalWeeks: 'Completed final-season weeks',
    from: 'Original start',
    target: 'Original target',
    worker: 'Actual worker activity is unverified',
    lease: {
      absent: 'No current execution lease',
      matching_active: 'Unexpired lease for this simulation (not a process-health guarantee)',
      matching_expired: 'Expired lease for this simulation',
      other_active: 'Another simulation currently holds the global lease',
      other_expired: 'A different simulation owns the stored expired lease'
    },
    readonly: 'Read-only: the exact Run and Branch must confirm whether resume is available.',
    inspect: 'Open detail and controls',
    runs: 'Open Runs inventory',
    receiptsTitle: 'Older pending receipts · not additional running workers',
    linked: 'This original command already belongs to the server task above:',
    linkedDetail: 'Show original pending receipt',
    distinction: 'Server tasks have their own status, heartbeat and explicit recovery. The separately persisted original commands below are historical evidence; a linked receipt is not a second simulation.',
    ambiguousLink: 'This command is ambiguously linked to multiple server tasks and cannot be safely connected.'
  }
} as const

function matchingOperation(operation: GlobalFullSimulationOperation, value: string): boolean {
  const haystack = [
    operation.run_id, operation.run_name, operation.branch_id,
    operation.branch_name, operation.command_id
  ].join(' ').toLocaleLowerCase()
  return haystack.includes(value)
}

export function GlobalSimulationTaskCenterPage(): JSX.Element {
  const { language } = useLanguage()
  const text = copy[language]
  const [search, setSearch] = useState('')
  const [state, setState] = useState<OperationStateFilter>('all')
  const serverTasks = useServerTasks()
  const inventory = useQuery({
    queryKey: ['global-full-simulation-operations'],
    queryFn: getGlobalFullSimulationOperations,
    retry: false,
    refetchInterval: 10000
  })
  const normalized = search.trim().toLocaleLowerCase()

  const serverTaskIndex = useMemo(() => {
    const index = new Map<string, typeof serverTasks.data>()
    if (serverTasks.isSuccess) {
      for (const task of serverTasks.data) {
        const key = `${task.run_id}::${task.branch_id}::${task.parent_command_id}`
        const existing = index.get(key)
        if (existing) {
          existing.push(task)
        } else {
          index.set(key, [task])
        }
      }
    }
    return index
  }, [serverTasks.isSuccess, serverTasks.data])

  const operations = useMemo(() => (
    (inventory.isSuccess ? inventory.data.operations : [])
      .filter(operation => state === 'all' || operation.control_state === state)
      .filter(operation => matchingOperation(operation, normalized))
      .sort((a, b) =>
        a.run_name.localeCompare(b.run_name) ||
        a.branch_name.localeCompare(b.branch_name) ||
        a.command_id.localeCompare(b.command_id))
  ), [inventory.isSuccess, inventory.data, state, normalized])

  return <section className="panel simulation-task-center">
    <div className="page-intro">
      <h2>{text.title}</h2><p className="subtitle">{text.subtitle}</p>
    </div>
    <FullSimulationServerTasks />
    <h3>{text.receiptsTitle}</h3>
    <p className="status">{text.distinction}</p>
    <p className="status">{text.truth}</p>
    <div className="simulation-task-center__toolbar">
      <label>{text.search}
        <input type="search" value={search}
          onChange={event => setSearch(event.target.value)}
          placeholder={text.searchPlaceholder} />
      </label>
      <label>{text.filter}
        <select value={state} onChange={event => setState(event.target.value as OperationStateFilter)}>
          <option value="all">{text.all}</option>
          <option value="running">{text.state.running}</option>
          <option value="pause_requested">{text.state.pause_requested}</option>
          <option value="paused">{text.state.paused}</option>
        </select>
      </label>
      <button type="button" onClick={() => { void inventory.refetch() }}
        disabled={inventory.isFetching}>{inventory.isFetching ? text.refreshing : text.refresh}</button>
    </div>
    {inventory.isPending && <p role="status">{text.loading}</p>}
    {inventory.isError && <p role="alert" className="error">{text.unavailable}: {formatApiError(inventory.error)}</p>}
    {inventory.isSuccess && <>
      <p className="status">{text.count}: <strong>{inventory.data.pending_count}</strong>
        {' · '}{text.legacy}: <strong>{inventory.data.legacy_pending_count}</strong></p>
      {inventory.data.pending_count === 0 ? <p className="status">{text.empty}</p>
        : operations.length === 0 ? <p className="status">{text.noMatches}</p>
          : <ul className="simulation-task-center__list" aria-label={text.title}>
            {operations.map(operation => {
              const taskKey = `${operation.run_id}::${operation.branch_id}::${operation.command_id}`
              const linkedTasks = serverTaskIndex.get(taskKey)
              const isAmbiguous = linkedTasks && linkedTasks.length > 1
              const linkedTask = linkedTasks && linkedTasks.length === 1 ? linkedTasks[0] : undefined

              const receiptMetadata = <div className="simulation-task-center__metadata">
                <span><b>{text.run}:</b> {operation.run_id}</span>
                <span><b>{text.branch}:</b> {operation.branch_id}</span>
                <span><b>{text.command}:</b> {operation.command_id}</span>
                <span><b>{text.progress}:</b> {operation.completed_season_count}</span>
                <span><b>{text.finalWeeks}:</b> {operation.final_completed_week_count}</span>
                <span><b>{text.from}:</b> S{operation.start_week.season_index} W{operation.start_week.week}</span>
                <span><b>{text.target}:</b> {operation.effective_boundary_target?<BoundaryDescription target={operation.effective_boundary_target}/>:<>S{(operation.effective_target_week??operation.final_week).season_index} W{(operation.effective_target_week??operation.final_week).week}</>}</span>
              </div>
              return <li key={JSON.stringify([operation.run_id, operation.branch_id, operation.command_id])}
                className="simulation-task-center__item">
                <div className="simulation-task-center__heading">
                  <strong>{operation.run_name} / {operation.branch_name}</strong>
                  <span className="status">{text.state[operation.control_state]}</span>
                </div>
                {isAmbiguous && <p className="status error">{text.ambiguousLink}</p>}
                {linkedTask && <p className="status">{text.linked} <code>{linkedTask.task_id}</code></p>}
                {linkedTask?<details><summary>{text.linkedDetail}</summary>{receiptMetadata}</details>:receiptMetadata}
                <p className="status">{text.worker} · {text.lease[operation.lease_state]}</p>
                {(operation.run_read_only || operation.branch_read_only || operation.branch_status !== 'active')
                  && <p className="status">{text.readonly}</p>}
                <Link className="button-link"
                  to={`/admin/runs/${encodeURIComponent(operation.run_id)}/simulate?branch=${encodeURIComponent(operation.branch_id)}${linkedTask ? `&task=${encodeURIComponent(linkedTask.task_id)}` : ''}`}
                  onClick={() => {
                    writeLastRunId(operation.run_id)
                    rememberProductRun(operation.run_id)
                  }}>{text.inspect}</Link>
              </li>
            })}
          </ul>}
    </>}
    <p><Link to="/admin/runs">{text.runs}</Link></p>
  </section>
}
