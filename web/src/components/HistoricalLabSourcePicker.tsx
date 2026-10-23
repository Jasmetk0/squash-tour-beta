import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { listRunContainers, listRunBranches, listSavedRevisionHistory } from '../api/client'
import { useLanguage } from '../i18n/LanguageContext'
import { formatApiError } from '../utils/apiErrors'

/** Same Saved inventory endpoints as Run navigation; no Viewer selection writes. */
export function HistoricalLabSourcePicker({ lab, run, branch, revision, onChange }: {
  lab: string; run: string; branch: string; revision: string;
  onChange: (run: string, branch: string, revision: string) => void
}) {
  const { language } = useLanguage(), cs = language === 'cs'
  const [open, setOpen] = useState(false)
  const runs = useQuery({queryKey: ['lab-source-runs'], queryFn: listRunContainers, enabled: open, retry: false})
  const branches = useQuery({queryKey: ['lab-source-branches', run], queryFn: () => listRunBranches(run), enabled: open && Boolean(run), retry: false})
  const history = useQuery({queryKey: ['lab-source-history', run, branch], queryFn: () => listSavedRevisionHistory(run, branch, {limit: 200}), enabled: open && Boolean(run && branch), retry: false})
  // Explicit IDs may come from adjacent manual fields, including revisions older than
  // the 200-item picker page. Showing the selected value never verifies its existence.
  const missingRun = Boolean(run && runs.isSuccess && !runs.data.run_containers.some(item=>item.run_id===run))
  const missingBranch = Boolean(branch && branches.isSuccess && !branches.data.run_branches.some(item=>item.branch_id===branch))
  const missingRevision = Boolean(revision && history.isSuccess && !history.data.saved_revisions.some(item=>item.revision_id===revision))
  return <details onToggle={event => setOpen(event.currentTarget.open)}>
    <summary>{cs ? 'Vybrat uložený historický zdroj' : 'Choose a saved historical source'}</summary>
    <label>Run <select aria-label={`${lab} source Run`} value={run} onChange={e => onChange(e.target.value, '', '')}>
      <option value="">—</option>{missingRun && <option value={run}>{cs?'Ručně zadaný Run – mimo seznam':'Manual Run ID – not in list'} · {run}</option>}{runs.data?.run_containers.map(item => <option key={item.run_id} value={item.run_id}>{item.display_name}</option>)}
    </select></label>
    <label>{cs ? 'Větev' : 'Branch'} <select aria-label={`${lab} source Branch`} value={branch} onChange={e => onChange(run, e.target.value, '')}>
      <option value="">—</option>{missingBranch && <option value={branch}>{cs?'Ručně zadaná větev – mimo seznam':'Manual Branch ID – not in list'} · {branch}</option>}{branches.data?.run_branches.map(item => <option key={item.branch_id} value={item.branch_id}>{item.display_name}</option>)}
    </select></label>
    <label>{cs ? 'Uložená revize' : 'Saved Revision'} <select aria-label={`${lab} source Saved Revision`} value={revision} onChange={e => onChange(run, branch, e.target.value)}>
      <option value="">—</option>{missingRevision && <option value={revision}>{cs?'Ručně zadaná revize – mimo seznam':'Manual Revision ID – not in list'} · {revision}</option>}{history.data?.saved_revisions.map(item => <option key={item.revision_id} value={item.revision_id}>#{item.sequence} · {item.revision_id}</option>)}
    </select></label>
    {open && runs.isPending && <p role="status">{cs ? 'Načítám Runy…' : 'Loading Runs…'}</p>}
    {open && runs.isSuccess && runs.data.run_containers.length === 0 && <p role="status">{cs ? 'Žádné Runy v inventáři.' : 'No Runs in the source inventory.'}</p>}
    {open && run && branches.isPending && <p role="status">{cs ? 'Načítám větve…' : 'Loading Branches…'}</p>}
    {open && run && branches.isSuccess && branches.data.run_branches.length === 0 && <p role="status">{cs ? 'Vybraný Run nemá dostupné větve.' : 'No Branches available for the selected Run.'}</p>}
    {open && run && branch && history.isPending && <p role="status">{cs ? 'Načítám uložené revize…' : 'Loading Saved Revisions…'}</p>}
    {open && run && branch && history.isSuccess && history.data.saved_revisions.length === 0 && <p role="status">{cs ? 'V této větvi nejsou žádné dostupné uložené revize.' : 'No Saved Revisions available for this Branch.'}</p>}
    {open && run && branch && history.isSuccess && history.data.has_more_older && <p>{cs ? 'Starší revizi lze zadat jejím ID.' : 'An older revision can be entered by its ID.'}</p>}
    {open && runs.isError && <><p role="alert">{cs ? 'Nepodařilo se načíst seznam Runů.' : 'Failed to load Runs.'} {formatApiError(runs.error)}</p>
      <button type="button" disabled={runs.isFetching} onClick={() => { void runs.refetch() }}>{cs ? 'Znovu načíst Runy' : 'Retry Runs'}</button></>}
    {open && run && branches.isError && <><p role="alert">{cs ? 'Nepodařilo se načíst větve.' : 'Failed to load Branches.'} {formatApiError(branches.error)}</p>
      <button type="button" disabled={branches.isFetching} onClick={() => { void branches.refetch() }}>{cs ? 'Znovu načíst větve' : 'Retry Branches'}</button></>}
    {open && run && branch && history.isError && <><p role="alert">{cs ? 'Nepodařilo se načíst uložené revize.' : 'Failed to load Saved Revisions.'} {formatApiError(history.error)}</p>
      <button type="button" disabled={history.isFetching} onClick={() => { void history.refetch() }}>{cs ? 'Znovu načíst revize' : 'Retry Saved Revisions'}</button></>}
  </details>
}
