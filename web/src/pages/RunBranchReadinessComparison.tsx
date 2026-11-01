import { useEffect, useRef, useState } from 'react'
import type { RunBranch } from '../api/types'
import { getRunHomeReadiness, listRunBranches } from '../api/client'
import { useLanguage } from '../i18n/LanguageContext'
import { formatApiError } from '../utils/apiErrors'
import {
  inspectBranchReadinessComparison, serializeBranchReadinessComparison,
  type BranchReadinessComparison
} from './runBranchReadinessComparison'

const copy = {
  cs: {
    title: 'Porovnání uložených podkladů Branchí',
    info: 'Srovnání dvou nezávislých uložených stavů. Nejde o validaci připravenosti k simulaci ani o společný atomický snímek.',
    target: 'Porovnat s Branch', pick: 'Vyber jinou Branch', inspect: 'Načíst porovnání',
    loading: 'Ověřuji oba Saved HEAD a zdrojové podklady…',
    failed: 'Porovnání není důvěryhodné a nebylo zobrazeno. Zkus nové načtení.',
    retry: 'Načíst znovu', from: 'Výchozí Branch', to: 'Druhá Branch',
    foundation: 'Uložený podklad', status: 'Stav', amount: 'Počet', delta: 'Rozdíl (druhá − výchozí)',
    world: 'World', calendar_package: 'Kalendář turnajů', population: 'Hráči',
    health: 'Health', official_ranking: 'Publikovaný ranking', working_draft: 'Working Draft',
    saved: 'Uloženo', missing: 'Chybí', candidate_only: 'Pouze kandidát', unsaved: 'Neuloženo', optional: 'Volitelné',
    phase: 'Fáze', transitions: 'Uložené přechody', rankings: 'Publikace rankingu',
    tasks: 'Aktivní úlohy', seasonCalendar: 'Hodiny kalendáře',
    compatible: 'Shodné', different: 'Rozdílné', source: 'Zdrojová revize',
    origin: 'Zdrojový hash', countUnit: 'počty v samostatných snímcích',
    inspectAgain: 'Nové ověření může vrátit jinou verzi uložených dat.',
    export: 'Stáhnout ověřené srovnání JSON',
    note: 'Počty vyjadřují existenci uložených podkladů; jiná operace může vyžadovat další validaci. Neuložené změny a probíhající úlohy nejsou automaticky potvrzené.',
    refresh: 'Pokud se mezitím změnil Saved HEAD jiné Branche, načti srovnání znovu.'
  },
  en: {
    title: 'Compare Branch Saved foundations',
    info: 'Two independent Saved inspections, not an execution readiness certificate or a shared atomic snapshot.',
    target: 'Compare with Branch', pick: 'Choose another Branch', inspect: 'Inspect comparison',
    loading: 'Verifying both Saved HEADs and source foundations…',
    failed: 'The comparison could not be verified and has not been shown. Try a fresh read.',
    retry: 'Inspect again', from: 'Primary Branch', to: 'Other Branch',
    foundation: 'Saved foundation', status: 'Status', amount: 'Count', delta: 'Difference (other − primary)',
    world: 'World', calendar_package: 'Tournament calendar', population: 'Players',
    health: 'Health', official_ranking: 'Published ranking', working_draft: 'Working Draft',
    saved: 'Saved', missing: 'Missing', candidate_only: 'Candidate only', unsaved: 'Unsaved', optional: 'Optional',
    phase: 'Phase', transitions: 'Saved transitions', rankings: 'Published rankings',
    tasks: 'Active tasks', seasonCalendar: 'Run calendar',
    compatible: 'Same', different: 'Different', source: 'Source revision',
    origin: 'Source hash', countUnit: 'counts in independent snapshots',
    inspectAgain: 'Another inspection may see a different Saved version.',
    export: 'Download verified comparison JSON',
    note: 'Counts indicate Saved foundations only; a specific operation may need further validation. Unsaved edits and running tasks have not been approved automatically.',
    refresh: 'If another Branch Saved HEAD changed meanwhile, inspect again.'
  }
} as const

function signedNumber(value: number): string {
  return value > 0 ? '+' + value : String(value)
}

export function RunBranchReadinessComparison({ runId, branchId, head, branches }: {
  runId: string
  branchId: string
  head: string
  branches: RunBranch[]
}): JSX.Element | null {
  const { language } = useLanguage()
  const t = copy[language]
  const [target, setTarget] = useState('')
  const [report, setReport] = useState<BranchReadinessComparison | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const version = useRef(0)
  useEffect(() => () => { version.current++ }, [])

  const alternatives = branches.filter(b => b.run_id === runId && b.branch_id !== branchId
    && Boolean(b.saved_head_revision_id))
  if (!head || alternatives.length === 0) return null

  const targetHead = branches.find(b => b.run_id === runId && b.branch_id === target)?.saved_head_revision_id
  const trustworthy = report?.run_id === runId
    && report.left.branch_id === branchId && report.left.saved_head_revision_id === head
    && report.right.branch_id === target && report.right.saved_head_revision_id === targetHead
  const shown = trustworthy ? report : null

  const inspect = async () => {
    if (!target || loading || !head) return
    const stamp = ++version.current
    setReport(null); setError(null); setLoading(true)
    try {
      const verified = await inspectBranchReadinessComparison(
        { branches: listRunBranches, readiness: getRunHomeReadiness },
        runId, branchId, target, head
      )
      if (version.current === stamp) setReport(verified)
    } catch (e) {
      if (version.current === stamp) setError(formatApiError(e))
    } finally {
      if (version.current === stamp) setLoading(false)
    }
  }

  const download = () => {
    if (!shown) return
    const bytes = serializeBranchReadinessComparison(shown)
    const url = URL.createObjectURL(new Blob([bytes], { type: 'application/json;charset=utf-8' }))
    try {
      const link = document.createElement('a')
      link.href = url
      link.download = 'squash-branch-readiness-' + shown.left.branch_id.replace(/[^a-zA-Z0-9_-]/g, '_').slice(0, 40)
        + '-vs-' + shown.right.branch_id.replace(/[^a-zA-Z0-9_-]/g, '_').slice(0, 40) + '.json'
      document.body.appendChild(link)
      link.click()
      link.remove()
    } finally { URL.revokeObjectURL(url) }
  }

  const labels = (which: 'left' | 'right') => shown![which].branch_name || shown![which].branch_id
  const calendarText = (side: 'left' | 'right') => {
    const c = shown![side].evidence.current_calendar
    return c.weeks_per_year + ' W / ' + c.season_count + ' seasons / ' + c.start_year
      + ' / start W' + c.season_start_year_week
  }

  return <section className="run-home-status-block" aria-label={t.title}>
    <h3>{t.title}</h3>
    <p className="status">{t.info}</p>
    <label htmlFor="compare-run-saved-branch">{t.target}</label>
    <select id="compare-run-saved-branch" value={target} disabled={loading}
      onChange={event => {
        version.current++
        setTarget(event.target.value)
        setReport(null)
        setError(null)
      }}>
      <option value="">{t.pick}</option>
      {alternatives.map(branch => <option key={branch.branch_id} value={branch.branch_id}>
        {branch.display_name || branch.branch_id}
      </option>)}
    </select>
    {' '}
    <button type="button" disabled={!target || loading} onClick={() => void inspect()}>
      {shown ? t.retry : t.inspect}
    </button>
    {loading && <p role="status">{t.loading}</p>}
    {error && !loading && <><p className="error" role="alert">{t.failed}</p>
      <p className="status">{error}</p></>}
    {!loading && !error && target && report && !trustworthy &&
      <p role="alert" className="error">{t.refresh}</p>}
    {shown && !loading && !error && <>
      <p className="status">{t.inspectAgain}</p>
      <table>
        <caption>{t.countUnit}</caption>
        <thead><tr><th scope="col">{t.foundation}</th><th scope="col">{labels('left')}</th>
          <th scope="col">{labels('right')}</th><th scope="col">{t.delta}</th></tr></thead>
        <tbody>{shown.comparisons.map(row => <tr key={row.code}>
          <th scope="row">{t[row.code]}</th>
          <td>{t[row.left.status]} · {row.left.evidence_count}</td>
          <td>{t[row.right.status]} · {row.right.evidence_count}</td>
          <td>{signedNumber(row.count_delta)}{row.status_changed ? ' · Δ ' + t.status : ''}</td>
        </tr>)}</tbody>
      </table>
      <dl>
        <dt>{t.phase}</dt><dd>{shown.left.evidence.phase} → {shown.right.evidence.phase}</dd>
        <dt>{t.seasonCalendar}</dt><dd>{calendarText('left')} → {calendarText('right')} · {shown.same_calendar ? t.compatible : t.different}</dd>
        <dt>{t.transitions}</dt><dd>{shown.left.evidence.saved_transition_count} → {shown.right.evidence.saved_transition_count} ({signedNumber(shown.saved_transitions_delta)})</dd>
        <dt>{t.rankings}</dt><dd>{shown.left.evidence.saved_published_ranking_count} → {shown.right.evidence.saved_published_ranking_count} ({signedNumber(shown.published_rankings_delta)})</dd>
        <dt>{t.tasks}</dt><dd>{shown.left.evidence.active_full_simulation_task_count} → {shown.right.evidence.active_full_simulation_task_count} ({signedNumber(shown.active_tasks_delta)})</dd>
        <dt>{t.source}</dt><dd><code>{shown.left.saved_head_revision_id}</code> → <code>{shown.right.saved_head_revision_id}</code></dd>
        <dt>{t.origin}</dt><dd><code>{shown.left.evidence.saved_revision_content_hash}</code> → <code>{shown.right.evidence.saved_revision_content_hash}</code></dd>
      </dl>
      <p className="status">{t.note}</p>
      <button type="button" onClick={download}>{t.export}</button>
    </>}
  </section>
}
