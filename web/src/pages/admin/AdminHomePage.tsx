import { useQuery } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { listRunContainers, listWorldPackages } from '../../api/client'
import { useLanguage } from '../../i18n/LanguageContext'
import { clearRecentProductRuns, readRecentProductRuns, RECENT_PRODUCT_RUNS_STORAGE_KEY, rememberProductRun } from '../../navigation/recentProductRuns'
import { formatApiError } from '../../utils/apiErrors'

export function AdminHomePage(): JSX.Element {
  const { language, t } = useLanguage()
  const [recentIds, setRecentIds] = useState(() => readRecentProductRuns())
  const [clearStatus, setClearStatus] = useState<'idle' | 'cleared' | 'error'>('idle')

  useEffect(() => {
    const onStorage = (event: StorageEvent) => {
      if (event.storageArea === localStorage && (event.key === RECENT_PRODUCT_RUNS_STORAGE_KEY || event.key === null)) {
        setRecentIds(readRecentProductRuns())
        setClearStatus('idle')
      }
    }
    // The same-tab clear updates state directly; storage events cover other tabs.
    window.addEventListener('storage', onStorage)
    return () => window.removeEventListener('storage', onStorage)
  }, [])

  const clearRecent = () => {
    if (clearRecentProductRuns()) {
      setRecentIds([])
      setClearStatus('cleared')
    } else {
      setClearStatus('error')
    }
  }
  const runs = useQuery({ queryKey: ['canonical-run-containers'], queryFn: listRunContainers, retry: false })
  const worlds = useQuery({ queryKey: ['world-packages'], queryFn: listWorldPackages, retry: false })
  const all = runs.data?.run_containers ?? []
  const recent = recentIds.map(id => all.find(run => run.run_id === id)).filter((run): run is typeof all[number] => Boolean(run))
  const others = all.filter(run => !recentIds.includes(run.run_id)).slice(0, 5)
  const runCount = runs.isPending ? t('Loading') : runs.isError ? t('Unavailable') : String(all.length)
  const worldCount = worlds.isPending ? t('Loading') : worlds.isError ? t('Unavailable') : String(worlds.data.packages.length)
  const entryCards = [
    { name: 'Runs', to: '/admin/runs', summary: t('Create, open and manage independent saved worlds.'), metric: t('Saved Runs') + ': ' + runCount },
    { name: 'Packages', to: '/admin/packages', summary: t('Browse source packages; applying a package creates a Run-owned copy.'), metric: t('World packages') + ': ' + worldCount },
    { name: 'Test Lab', to: '/admin/labs', summary: t('Run isolated Match, Tournament and Player experiments.'), metric: language === 'cs' ? '3 dostupné laboratoře' : '3 available labs' }
  ]
  return <section className="panel global-home">
    <div className="page-intro"><p className="eyebrow">PRE-ALPHA · ADMIN</p><h2>{t('Squash Engine Home')}</h2>
      <p className="subtitle">{t('A world-building and simulation workspace. Choose what to work with.')}</p></div>
    <div className="home-entry-grid">{entryCards.map(card => <Link className="home-entry" key={card.to} to={card.to}>
      <span className="eyebrow">{card.metric}</span><h3>{t(card.name)} ↗</h3><p>{card.summary}</p>
    </Link>)}</div>
    <p><Link to="/admin/operations">{language === 'cs' ? 'Centrum simulací – rozpracované Full Simulation →' : 'Simulation Task Center – persisted Full Simulation →'}</Link></p>
    <section className="home-recent" aria-label="Saved Product Runs">
      <div className="home-recent__heading"><h3>{t('Saved Product Runs')}</h3><Link to="/admin/runs/new">{t('Create Run')} +</Link></div>
      {runs.isPending && <p role="status">{t('Loading')}</p>}
      {runs.isError && <p role="alert" className="error">{t('Unavailable')}: {formatApiError(runs.error)}</p>}
      {runs.isSuccess && all.length === 0 && <p className="status">{t('No Runs yet')}</p>}
      {runs.isSuccess && recent.length === 0 && all.length > 0 && <p className="status">{language === 'cs' ? 'Žádné dostupné nedávno otevřené Runy v tomto prohlížeči.' : 'No accessible recently opened Runs in this browser.'}</p>}
      {runs.isSuccess && recent.length > 0 && <><div className="home-recent__heading"><h4>{t('Recently opened')}</h4><button type="button" onClick={clearRecent}>{language === 'cs' ? 'Vymazat nedávné návštěvy' : 'Clear recent visits'}</button></div><ul className="home-run-list">
        {recent.map(run => <li key={run.run_id}><span><strong>{run.display_name || run.run_id}</strong><small>{run.status} · {run.read_only ? 'Read-only' : 'Editable'}</small></span>
          <Link to={'/admin/runs/' + encodeURIComponent(run.run_id)} onClick={() => rememberProductRun(run.run_id)}>{t('Open Run')} →</Link></li>)}</ul></>}
      {clearStatus === 'cleared' && <p role="status">{language === 'cs' ? 'Historie nedávných návštěv byla vymazána jen v tomto prohlížeči. Runy zůstaly uložené.' : 'Recent visits were cleared only in this browser. Saved Runs remain unchanged.'}</p>}
      {clearStatus === 'error' && <p role="alert" className="error">{language === 'cs' ? 'Historii se nepodařilo vymazat. Zkontroluj nastavení úložiště prohlížeče.' : 'Could not clear recent visits. Check browser storage permissions.'}</p>}
      {runs.isSuccess && others.length > 0 && <><h4>{recent.length ? t('Other saved Runs') : t('Saved Product Runs')}</h4><ul className="home-run-list">
        {others.map(run => <li key={run.run_id}><span><strong>{run.display_name || run.run_id}</strong><small>{run.status} · {run.read_only ? 'Read-only' : 'Editable'}</small></span>
          <Link to={'/admin/runs/' + encodeURIComponent(run.run_id)} onClick={() => rememberProductRun(run.run_id)}>{t('Open Run')} →</Link></li>)}</ul></>}
      <p className="status">{language === 'cs' ? 'Na globální stránce není aktivní Run, branch ani čas. Run se otevírá pouze tvým kliknutím.' :
        'No Run, Branch or Time is active on this page. Opening a Run requires an explicit click.'}</p>
    </section>
  </section>
}
