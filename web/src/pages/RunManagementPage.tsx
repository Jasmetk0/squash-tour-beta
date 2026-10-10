import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'
import { getRunContainer } from '../api/client'
import { useAdminBranch } from '../admin/AdminBranchContext'
import { RunPackageSetupPanel } from '../components/RunPackageSetupPanel'
import { useLanguage } from '../i18n/LanguageContext'
import { formatApiError } from '../utils/apiErrors'

export function RunManagementPage(): JSX.Element {
  const { runId = '' } = useParams()
  const { selectedBranch } = useAdminBranch()
  const { language, t } = useLanguage()
  const query = useQuery({ queryKey: ['run-container', runId], queryFn: () => getRunContainer(runId), enabled: Boolean(runId), retry: false })
  const base = '/admin/runs/' + encodeURIComponent(runId)
  return <section className="panel">
    <div className="page-intro"><h2>{t('Run Management')}</h2><p className="subtitle">
      {language === 'cs' ? 'Správa uloženého Runu a jeho nezávislých dat. Nejde o globální zdrojové balíčky.' :
        'Manage this saved Run and its independent data, not the global source packages.'}
    </p></div>
    {query.isPending && <p role="status">{t('Loading')}</p>}
    {query.isError && <p role="alert" className="error">{formatApiError(query.error)}</p>}
    {query.data && <><p className="status">{query.data.display_name || runId} · {query.data.status} · {query.data.read_only ? 'Read-only' : 'Editable'}</p>
      {query.data.storage_kind === 'custom_local' && !query.data.read_only &&
        <RunPackageSetupPanel run={query.data} branch={selectedBranch} />}
    </>}
    <div className="home-entry-grid">
      <article className="home-entry"><h3>{language === 'cs' ? 'Validace a diagnostika' : 'Validation & diagnostics'}</h3>
        <Link to={base + '/diagnostics'}>{language === 'cs' ? 'Otevřít diagnostiku Runu' : 'Open Run diagnostics'} →</Link>
      </article>
      <article className="home-entry"><h3>{language === 'cs' ? 'Revize a obnova' : 'Revisions & recovery'}</h3>
        <Link to={base + '/branches'}>{language === 'cs' ? 'Historie uložených revizí' : 'Saved revision history'} →</Link>
      </article>
      <article className="home-entry"><h3>Central overrides, import/export, backups & storage</h3>
        <p className="status">{t('Not implemented')} — {language === 'cs' ? 'nepředstíráme existenci správy, která zatím nemá ověřený workflow.' : 'no completed workflow is claimed.'}</p>
      </article>
    </div>
  </section>
}
