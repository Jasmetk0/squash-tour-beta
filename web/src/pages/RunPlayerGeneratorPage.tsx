/** The single Run → Players → Generate entry, backed by production InitialWorld authority. */
import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'

import { getRunContainer } from '../api/client'
import { useAdminBranch } from '../admin/AdminBranchContext'
import { useAdminTime } from '../admin/AdminTimeContext'
import { RunInitialWorldSetupPanel } from '../components/RunInitialWorldSetupPanel'
import { useLanguage } from '../i18n/LanguageContext'
import { formatApiError } from '../utils/apiErrors'

export function RunPlayerGeneratorPage(): JSX.Element {
  const { runId = '' } = useParams()
  const { language } = useLanguage()
  const cs = language === 'cs'
  const { selectedBranch, isLoading: branchLoading, error: branchError } = useAdminBranch()
  const time = useAdminTime()
  const q = useQuery({
    queryKey: ['run-container', runId],
    queryFn: () => getRunContainer(runId),
    enabled: Boolean(runId),
    retry: false,
  })
  const run = q.data?.run_id === runId ? q.data : null
  const branch = selectedBranch?.run_id === runId ? selectedBranch : null
  const present = time.mode === 'present' && !time.isLoading && !time.error
  const canUse = run && branch && present && !branchLoading && !branchError
  return <section className="panel run-home">
    <div className="page-intro">
      <p className="eyebrow">PRODUCT RUN · PLAYERS · GENERATE</p>
      <h2>{cs ? 'Generovat hráče' : 'Generate players'}</h2>
      <p className="subtitle">{cs
        ? 'Jediný produkční generátor: kompletní dávka podle uloženého světa, náhled, potvrzení, Working Draft, ruční Save.'
        : 'One production generator: complete batch from the saved World, preview, explicit confirmation, Working Draft, manual Save.'}</p>
    </div>
    <p><Link to={'/admin/runs/' + encodeURIComponent(runId) + '/players'}>
      {cs ? '← Zpět na Hráče' : '← Back to Players'}</Link></p>
    {q.isPending && <p role="status">{cs ? 'Načítám Run…' : 'Loading Run…'}</p>}
    {q.error && <p role="alert" className="error">{formatApiError(q.error)}</p>}
    {q.isSuccess && !run && <p role="alert">{cs ? 'Identita Runu nesouhlasí.' : 'Run identity mismatch.'}</p>}
    {branchError && <p role="alert">{branchError}</p>}
    {time.error && <p role="alert">{time.error}</p>}
    {time.mode !== 'present' && <p role="alert">{cs
      ? 'Historický checkpoint je pouze pro čtení. Generování je povoleno jen nad současným uloženým stavem vybrané branche.'
      : 'Historical checkpoints are read-only. Generate only from the selected Branch current saved context.'}</p>}
    {!branchLoading && !branch && <p role="alert">{cs
      ? 'Vyber platnou aktivní branch.' : 'Select a valid Active Admin Branch.'}</p>}
    {canUse && <RunInitialWorldSetupPanel
      key={runId + ':' + branch.branch_id + ':' + branch.saved_head_revision_id}
      run={run} branch={branch} locale={language} />}
  </section>
}
