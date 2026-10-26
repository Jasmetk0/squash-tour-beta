import { useState } from 'react'
import { RankingPreparationPanel } from './RankingPreparationPanel'
import { RankingSavePanel } from './RankingSavePanel'
import { RankingCandidateInputsPanel } from './RankingCandidateInputsPanel'
import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'
import { getRankingCandidates, getRankingCandidateSources } from '../api/client'
import type { CandidateWeek } from '../api/rankingCandidates'
import { EmptyState, PageIntro, SectionCard } from '../components/RunScopedUi'
import { useLanguage } from '../i18n/LanguageContext'
import { formatApiError } from '../utils/apiErrors'
import { sameWeek, tr, validCandidateHistory, validCandidateResponse, weekLabel } from './rankingCandidateReadOnly'

export function AdminRankingCandidatesPage(): JSX.Element {
  const { language } = useLanguage()
  const t = (value: string) => tr(value, language)
  const { runId = '', branchId = '', seasonIndex, week } = useParams()
  const base = '/admin/runs/' + encodeURIComponent(runId) + '/branches/' + encodeURIComponent(branchId) + '/ranking-candidates'
  // Retain existing legacy ranking week limits; this page does not change Run calendar rules.
  const valid = (seasonIndex === undefined && week === undefined) ||
    (seasonIndex !== undefined && week !== undefined && /^\d+$/.test(seasonIndex) && /^\d+$/.test(week) &&
      Number(seasonIndex) < 50 && Number(week) >= 1 && Number(week) <= 61)
  const query = useQuery({
    queryKey: ['ranking-candidates', runId, branchId],
    queryFn: async () => {
      const response = await getRankingCandidates(runId, branchId)
      if (!validCandidateHistory(response, runId, branchId)) throw new Error(t('Ranking history does not match this candidate.'))
      return response
    },
    enabled: Boolean(runId && branchId && valid),
    retry: false,
  })
  const data = query.data && validCandidateHistory(query.data, runId, branchId) ? query.data : undefined
  const selected = data?.candidates.find(c =>
    seasonIndex !== undefined && week !== undefined &&
    sameWeek(c.snapshot.week, { season_index: Number(seasonIndex), week: Number(week) }))
  return <main>
    <PageIntro title={t('Ranking candidates')}
      subtitle={t('Unpublished preparation history. Viewing does not publish rankings or advance time.')}
      meta={'Run: ' + runId + ' · ' + t('Branch') + ': ' + branchId} />
    <Link to={'/admin/runs/' + encodeURIComponent(runId) + '/branches'}>{t('Back to Branches')}</Link>
    {!valid ? <p role="alert">{t('Invalid season or week.')}</p>
      : query.isPending || query.isFetching ? <p role="status">{t('Loading ranking history…')}</p> : null}
    {valid && query.isError && <div role="alert"><p>{formatApiError(query.error)}</p>
      <button type="button" disabled={query.isFetching} onClick={() => void query.refetch()}>{t('Retry loading')}</button></div>}
    {valid && data && <div hidden={query.isFetching || query.isError || !query.isSuccess}>
      <RankingPreparationPanel key={'prepare/' + runId + '/' + branchId} runId={runId} branchId={branchId} latest={data.candidates[data.candidates.length - 1]} />
      <RankingSavePanel key={'save/' + runId + '/' + branchId} runId={runId} branchId={branchId} />
      <button type="button" disabled={query.isFetching} onClick={() => void query.refetch()}>{t('Refresh candidates')}</button>
      <SectionCard title={t('Candidate weeks')}>
        {data.candidates.length === 0
          ? <EmptyState message={t('No ranking candidates have been prepared for this Branch.')} />
          : <ul>{data.candidates.map(c => <li key={c.fingerprint}>
            <Link to={base + '/' + c.snapshot.week.season_index + '/' + c.snapshot.week.week}
              aria-current={selected?.fingerprint === c.fingerprint ? 'page' : undefined}>
              {weekLabel(c.snapshot.week, language)}</Link>
            {' — '}{c.snapshot.rows.length} {t('players')} · {t('Best')} {c.snapshot.policy.best_n} · {t('Unpublished candidate')} ({t('Not Official Ranking')})
          </li>)}</ul>}
      </SectionCard>
      {seasonIndex !== undefined && !selected ? <p role="alert">{t('No candidate is stored for this week.')}</p>
        : selected ? <SectionCard title={weekLabel(selected.snapshot.week, language)}>
          <p>{t('Unpublished candidate')} ({t('Not Official Ranking')}) · {t('Best')} {selected.snapshot.policy.best_n}</p>
          {selected.snapshot.rows.length === 0
            ? <EmptyState message={t('This candidate contains no ranked players.')} />
            : <div className="table-scroll" role="region" aria-label={t('Candidate ranking table')} tabIndex={0}>
              <table><thead><tr><th>{t('Rank')}</th><th>{t('Player ID')}</th><th>{t('Points')}</th><th>{t('Counted results')}</th></tr></thead>
                <tbody>{selected.snapshot.rows.map(row => <tr key={row.player_id}>
                  <td>{row.rank}</td><td>{row.player_id}</td><td>{row.points}
                    {Boolean(row.disciplinary_zeros?.length) && <details>
                      <summary>{row.disciplinary_zeros?.length} {t('active disciplinary zeros')}</summary>
                      <p>{Math.max(0, selected.snapshot.policy.best_n - (row.disciplinary_zeros?.length ?? 0))} {t('tournament result slots available.')}</p>
                      <ul>{row.disciplinary_zeros?.map(z =>
                        <li key={z.zero_id}>{z.zero_id}: {t('effective')} {weekLabel(z.effective_week, language)} {t('for')} {z.duration_weeks} {t('weeks')}.</li>)}</ul>
                    </details>}
                  </td>
                  <td>{row.counted_results.length === 0 ? t('No counted results')
                    : <details><summary>{row.counted_results.length} {t('counted results for')} {row.player_id}</summary>
                      <ul>{row.counted_results.map(result =>
                        <li key={result.edition_id}><strong>{result.edition_id}</strong>: {result.qualification_points + result.main_points} {t('points')}
                          {' ('}{result.qualification_points} {t('qualification')} + {result.main_points} {t('main')}{'). '}
                          {t('Completed')} {weekLabel(result.completed_week, language)}; {t('first publication')} {weekLabel(result.first_publication_week, language)};
                          {' '}{t('validity')} {result.validity_weeks} {t('weeks')}.</li>)}</ul>
                    </details>}
                  </td>
                </tr>)}</tbody>
              </table>
            </div>}
          <RankingCandidateInputsPanel
            key={'inputs/' + runId + '/' + branchId + '/' + selected.snapshot.week.season_index + '/' + selected.snapshot.week.week + '/' + selected.fingerprint}
            runId={runId} branchId={branchId} week={selected.snapshot.week} fingerprint={selected.fingerprint} />
          <RankingSources
            key={'sources/' + runId + '/' + branchId + '/' + selected.snapshot.week.season_index + '/' + selected.snapshot.week.week + '/' + selected.fingerprint}
            runId={runId} branchId={branchId} week={selected.snapshot.week} fingerprint={selected.fingerprint} />
          <details><summary>{t('Technical provenance')}</summary>
            <p>{t('Policy')}: {selected.snapshot.policy.policy_id}</p>
            <p style={{ overflowWrap: 'anywhere' }}>{t('Fingerprint')}: {selected.fingerprint}</p>
            <p>{t('Commands')}: {selected.command_ids.join(', ') || t('No command receipt')}</p>
          </details>
        </SectionCard>
        : data.candidates.length > 0 && <p>{t('Select a week to inspect its ranking.')}</p>}
    </div>}
  </main>
}

function RankingSources({ runId, branchId, week, fingerprint }: {
  runId: string; branchId: string; week: CandidateWeek; fingerprint: string
}): JSX.Element {
  const { language } = useLanguage()
  const t = (value: string) => tr(value, language)
  const [opened, setOpened] = useState(false)
  const query = useQuery({
    queryKey: ['ranking-sources', runId, branchId, week.season_index, week.week, fingerprint],
    queryFn: async () => {
      const response = await getRankingCandidateSources(runId, branchId, week.season_index, week.week)
      if (!validCandidateResponse(response, runId, branchId, week, fingerprint)) {
        throw new Error(t('Source history does not match this candidate.'))
      }
      return response
    },
    enabled: opened, retry: false,
  })
  return <section aria-label={t('Historical ranking sources')}>
    <h3>{t('Source results')}</h3>
    <p>{t('Results effective for this candidate week, including results outside Best N. Later corrections are excluded.')}</p>
    {!opened ? <button type="button" onClick={() => setOpened(true)}>{t('Load source results')}</button>
      : <>
        <button type="button" disabled={query.isFetching} onClick={() => void query.refetch()}>{t('Refresh source results')}</button>
        {query.isPending || query.isFetching ? <p role="status">{t('Loading source results…')}</p> : null}
        {query.isError && <div role="alert"><p>{formatApiError(query.error)}</p>
          <button type="button" disabled={query.isFetching} onClick={() => void query.refetch()}>{t('Retry source results')}</button></div>}
        {query.data && <div hidden={query.isFetching || !query.isSuccess}>
          {query.data.sources.length === 0 ? <p>{t('No source results at this boundary.')}</p>
            : <ul>{query.data.sources.map(source => {
              const v = source.version
              return <li key={source.fingerprint}>
                <strong>{v.result.player_id} · {v.result.edition_id}</strong>: {v.result.qualification_points + v.result.main_points} {t('points')}
                {' · '}{source.counted ? t('Counted') : t('Not counted in this candidate')}
                <p>{t('Effective')} {weekLabel(v.effective_week, language)} · {t('First publication')} {weekLabel(v.result.first_publication_week, language)}
                  {' · '}{t('Validity')} {v.result.validity_weeks} {t('weeks')}</p>
                <details><summary>{t('Source provenance')}</summary>
                  <p style={{ overflowWrap: 'anywhere' }}>{t('Source')}: {v.result.source_fingerprint}<br />
                    {t('Version')}: {source.fingerprint}<br />
                    {t('Previous version')}: {v.previous_fingerprint ?? t('Initial result')}</p>
                </details>
              </li>
            })}</ul>}
        </div>}
      </>}
  </section>
}
