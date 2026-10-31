import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'
import { getRunContainer } from '../api/client'
import { useAdminBranch } from '../admin/AdminBranchContext'
import { RunPackageSetupPanel } from '../components/RunPackageSetupPanel'
import { SavedBranchArchiveExportPanel } from '../components/SavedBranchArchiveExportPanel'
import { useLanguage } from '../i18n/LanguageContext'
import { formatApiError } from '../utils/apiErrors'

export function RunManagementPage(): JSX.Element {
  const { runId = '' } = useParams()
  const { selectedBranch } = useAdminBranch()
  const { language, t } = useLanguage()
  const query = useQuery({ queryKey: ['run-container', runId], queryFn: () => getRunContainer(runId), enabled: Boolean(runId), retry: false })
  const base = '/admin/runs/' + encodeURIComponent(runId)
  const activeBranch = selectedBranch?.run_id === runId ? selectedBranch : null
  const run = query.data?.run_id === runId ? query.data : null
  const runMismatch = Boolean(query.data && !run)
  return <section className="panel">
    <div className="page-intro"><h2>{t('Run Management')}</h2><p className="subtitle">
      {language === 'cs' ? 'Správa uloženého Runu a jeho nezávislých dat. Nejde o globální zdrojové balíčky.' :
        'Manage this saved Run and its independent data, not the global source packages.'}
    </p></div>
    {query.isPending && <p role="status">{t('Loading')}</p>}
    {query.isError && <p role="alert" className="error">{formatApiError(query.error)}</p>}
    {runMismatch && <p role="alert" className="error">{language === 'cs'
      ? 'Server vrátil jiný Run. Editační ovládání zůstává skryté.'
      : 'The server returned another Run. Editing controls remain hidden.'}</p>}
    {run && <>
      <p className="status">{run.display_name || runId} · {run.status} · {run.read_only
        ? (language === 'cs' ? 'Pouze ke čtení' : 'Read-only')
        : (language === 'cs' ? 'Upravitelný' : 'Editable')}</p>
      <p className="status">{language === 'cs' ? 'Vybraná Branch' : 'Selected Branch'}: {
        activeBranch?.display_name || activeBranch?.branch_id ||
        (language === 'cs' ? 'Zatím nevybraná' : 'Not selected')
      } · {language === 'cs' ? 'Uložená revize' : 'Saved revision'}: {
        activeBranch?.saved_head_revision_id ? (language === 'cs' ? 'Dostupná' : 'Available')
          : (language === 'cs' ? 'Nedostupná' : 'Unavailable')
      }</p>
      <p><Link to={base}>{language === 'cs' ? 'Otevřít přehled Runu' : 'Open Run overview'} →</Link></p>
      {run.storage_kind === 'custom_local' && !run.read_only &&
        <RunPackageSetupPanel run={run} branch={activeBranch} />}
    </>}
    <div className="home-entry-grid">
      <article className="home-entry"><h3>{language === 'cs' ? 'Validace a diagnostika' : 'Validation & diagnostics'}</h3>
        <Link to={base + '/diagnostics'}>{language === 'cs' ? 'Otevřít diagnostiku Runu' : 'Open Run diagnostics'} →</Link>
      </article>
      <article className="home-entry"><h3>{language === 'cs' ? 'Revize a obnova' : 'Revisions & recovery'}</h3>
        <Link to={base + '/branches'}>{language === 'cs' ? 'Historie uložených revizí' : 'Saved revision history'} →</Link>
      </article>
      <article className="home-entry"><h3>{language === 'cs' ? 'Přenosný export Saved Branch' : 'Portable Saved Branch export'}</h3>
        {run ? <SavedBranchArchiveExportPanel run={run} branch={activeBranch} /> :
          <p className="status">{t('Unavailable')}</p>}
        <p className="status">{t('Not implemented')} — {language === 'cs'
          ? 'UI importu, přepisu Runu a ostatních režimů záloh zde zatím není.'
          : 'Import, Run replacement and other backup-mode UI are not available here yet.'}</p>
      </article>
    </div>
  </section>
}
