import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getRankingCandidateSources } from '../api/client'
import type { CandidateWeek, RankingCandidateDetail, RankingCandidateSources, RankingResultCorrection } from '../api/rankingCandidates'
import { formatApiError } from '../utils/apiErrors'
import { useLanguage } from '../i18n/LanguageContext'
import { rankingWorkflowText } from './rankingWorkflowText'

type Source = RankingCandidateSources['sources'][number]
type Change = { source: Source; result: RankingResultCorrection['result'] }

/** Corrections select a verified stored predecessor; timing is never editable. */
export function RankingResultCorrections({runId, branchId, latest, target, onChange}: {
  runId: string; branchId: string; latest: RankingCandidateDetail; target: CandidateWeek
  onChange: (corrections: RankingResultCorrection[]) => void
}): JSX.Element {
  const { language } = useLanguage()
  const t = (value: string) => rankingWorkflowText(value, language)
  const [opened, setOpened] = useState(false)
  const [changes, setChanges] = useState<Change[]>([])
  const sources = useQuery({
    queryKey: ['ranking-correction-sources', runId, branchId, latest.fingerprint],
    enabled: opened, retry: false,
    queryFn: async () => {
      const data = await getRankingCandidateSources(runId, branchId, latest.snapshot.week.season_index, latest.snapshot.week.week)
      if (data.run_id !== runId || data.branch_id !== branchId || data.candidate_fingerprint !== latest.fingerprint
          || data.week.season_index !== latest.snapshot.week.season_index || data.week.week !== latest.snapshot.week.week
          || data.publication_status !== 'candidate_only') throw new Error('Result sources no longer match the selected ranking. Refresh history.')
      return data.sources
    },
  })
  const update = (next: Change[]) => {
    setChanges(next)
    onChange(next.map(change => ({run_id: runId, branch_id: branchId, effective_week: target,
      previous_fingerprint: change.source.fingerprint, result: change.result})))
  }
  const edit = (fingerprint: string, patch: Partial<Change['result']>) => update(changes.map(c =>
    c.source.fingerprint === fingerprint ? {...c, result: {...c.result, ...patch}} : c))
  return <section aria-label={t('Result corrections')}>
    <h3>{t('Result corrections')}</h3>
    <p>{t('Corrections affect the next candidate. Earlier rankings and the result’s original expiry remain unchanged.')}</p>
    {!opened ? <button type="button" onClick={() => setOpened(true)}>{t('Load stored results to correct')}</button>
      : sources.isPending ? <p role="status">{t('Loading stored results…')}</p>
      : sources.isError ? <div role="alert">{t(formatApiError(sources.error))} <button type="button" onClick={() => void sources.refetch()}>{t('Retry result sources')}</button></div>
      : <>
        {!sources.data?.length && <p>{t('No stored results are available to correct.')}</p>}
        {sources.data?.map(source => {
          const change = changes.find(c => c.source.fingerprint === source.fingerprint)
          const result = source.version.result
          return <fieldset key={source.fingerprint}>
            <legend>{result.player_id} · {result.edition_id}</legend>
            <p>{t('Stored')}: {t('Q')} {result.qualification_points} + {t('Main')} {result.main_points} · {t(result.ranked ? 'Ranking eligible' : 'Excluded')} · {t(result.terminal_status === 'completed' ? 'Completed' : 'Abandoned')}</p>
            <p>{t('First publication')}: {t('season')} {result.first_publication_week.season_index + 1}, {t('week')} {result.first_publication_week.week} · {t('Validity')}: {result.validity_weeks} {t('weeks')}</p>
            <label className="checkbox-label"><input type="checkbox" checked={Boolean(change)} onChange={e => update(e.target.checked
              ? [...changes, {source, result: {...result, source_fingerprint: ''}}]
              : changes.filter(c => c.source.fingerprint !== source.fingerprint))} />{t('Correct')} {result.player_id} / {result.edition_id}</label>
            {change && <>
              <label>{t('Corrected qualification points')} <input required type="number" min="0" step="1" value={change.result.qualification_points} onChange={e => edit(source.fingerprint, {qualification_points: Number(e.target.value)})} /></label>
              <label>{t('Corrected main points')} <input required type="number" min="0" step="1" value={change.result.main_points} onChange={e => edit(source.fingerprint, {main_points: Number(e.target.value)})} /></label>
              <label className="checkbox-label"><input type="checkbox" checked={change.result.ranked} onChange={e => edit(source.fingerprint, {ranked: e.target.checked})} />{t('Ranking eligible after correction')}</label>
              <label>{t('Corrected terminal status')} <select value={change.result.terminal_status} onChange={e => edit(source.fingerprint, {terminal_status: e.target.value as 'completed' | 'abandoned'})}><option value="completed">{t("Completed")}</option><option value="abandoned">{t("Abandoned")}</option></select></label>
              <label>{t('Result correction reference')} <input required value={change.result.source_fingerprint} onChange={e => edit(source.fingerprint, {source_fingerprint: e.target.value})} /></label>
            </>}
          </fieldset>
        })}
      </>}
  </section>
}
