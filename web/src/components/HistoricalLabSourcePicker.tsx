import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { listRunContainers, listRunBranches, listSavedRevisionHistory } from '../api/client'
import { useLanguage } from '../i18n/LanguageContext'

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
  return <details onToggle={event => setOpen(event.currentTarget.open)}>
    <summary>{cs ? 'Vybrat uložený historický zdroj' : 'Choose a saved historical source'}</summary>
    <label>Run <select aria-label={`${lab} source Run`} value={run} onChange={e => onChange(e.target.value, '', '')}>
      <option value="">—</option>{runs.data?.run_containers.map(item => <option key={item.run_id} value={item.run_id}>{item.display_name}</option>)}
    </select></label>
    <label>{cs ? 'Větev' : 'Branch'} <select aria-label={`${lab} source Branch`} value={branch} onChange={e => onChange(run, e.target.value, '')}>
      <option value="">—</option>{branches.data?.run_branches.map(item => <option key={item.branch_id} value={item.branch_id}>{item.display_name}</option>)}
    </select></label>
    <label>{cs ? 'Uložená revize' : 'Saved Revision'} <select aria-label={`${lab} source Saved Revision`} value={revision} onChange={e => onChange(run, branch, e.target.value)}>
      <option value="">—</option>{history.data?.saved_revisions.map(item => <option key={item.revision_id} value={item.revision_id}>#{item.sequence} · {item.revision_id}</option>)}
    </select></label>
    {history.data?.has_more_older && <p>{cs ? 'Starší revizi lze zadat jejím ID.' : 'An older revision can be entered by its ID.'}</p>}
    {(runs.isError || branches.isError || history.isError) && <p role="alert">{cs ? 'Zdroj nelze ověřit.' : 'Source inventory could not be verified.'}</p>}
  </details>
}
