import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getRankingCandidateInputs } from '../api/client'
import type { CandidateWeek } from '../api/rankingCandidates'
import { useLanguage } from '../i18n/LanguageContext'
import { formatApiError } from '../utils/apiErrors'
import { storedValue, tr, validCandidateResponse, weekLabel } from './rankingCandidateReadOnly'

export function RankingCandidateInputsPanel({ runId, branchId, week, fingerprint }: {
  runId: string; branchId: string; week: CandidateWeek; fingerprint: string
}): JSX.Element {
  const { language } = useLanguage()
  const t = (value: string) => tr(value, language)
  const [opened, setOpened] = useState(false)
  const query = useQuery({
    queryKey: ['ranking-inputs', runId, branchId, week.season_index, week.week, fingerprint],
    queryFn: async () => {
      const response = await getRankingCandidateInputs(runId, branchId, week.season_index, week.week)
      if (!validCandidateResponse(response, runId, branchId, week, fingerprint)) {
        throw new Error(t('Stored inputs do not match this candidate.'))
      }
      return response
    },
    enabled: opened, retry: false,
  })
  const data = query.data
  const value = (v: number | string | null | undefined): string =>
    v === null || v === undefined ? storedValue(v, language)
      : typeof v === 'number' ? String(v) : v
  return <section aria-label={t('Stored calculation inputs')}>
    <h3>{t('Stored calculation inputs')}</h3>
    <p>{t('Frozen roster and results supplied to this calculation, including players and results absent from the ranking.')}</p>
    {!opened ? <button type="button" onClick={() => setOpened(true)}>{t('Inspect stored inputs')}</button>
      : <>
        <button type="button" disabled={query.isFetching} onClick={() => void query.refetch()}>{t('Refresh stored inputs')}</button>
        {query.isPending || query.isFetching ? <p role="status">{t('Loading stored inputs…')}</p> : null}
        {query.isError && <div role="alert"><p>{formatApiError(query.error)}</p>
          <button type="button" disabled={query.isFetching} onClick={() => void query.refetch()}>{t('Retry stored inputs')}</button></div>}
        {data && <div hidden={query.isFetching || !query.isSuccess}>
          {data.verification_status === 'legacy_without_manifest' ? <p>{t('Legacy candidate: complete calculation inputs were not stored. They cannot be reconstructed from current data.')}</p>
            : data.verification_status === 'complete_manifest' && data.manifest ? <>
              <p>{t('Verified: stored inputs reproduce this candidate. This does not verify completeness against the entire world.')}</p>
              <h4>{t('Preparation audit')}</h4>
              {data.command_audits?.length
                ? <ul>{data.command_audits.map(entry => <li key={entry.command_id}>
                  <strong>{entry.audit.actor_label}</strong> · {entry.audit.reason}
                  <details><summary>{t('Preparation command')}</summary>{entry.command_id}</details>
                </li>)}</ul>
                : <p>{t('No preparation audit was recorded for this candidate.')}</p>}
              <h4>{t('Why equal-point players are ordered this way')}</h4>
              {data.tie_explanations === undefined ? <p>{t('Tie explanations are unavailable from this server.')}</p>
                : data.tie_explanations.length === 0 ? <p>{t('No adjacent players have equal points.')}</p>
                  : <ul>{data.tie_explanations.map(tie => {
                    const reason = {
                      result_profile: 'Counted points at result slot',
                      completion_age: 'Newer completion at result slot',
                      previous_position: 'Previous Official position',
                      stored_token: 'Stored tie-break token',
                    }[tie.reason]
                    // Historical legacy ranking indexes use 61-week season coordinates.
                    const tieValue = (v: number | string | null | undefined): string =>
                      tie.reason === 'completion_age' && typeof v === 'number'
                        ? weekLabel({ season_index: Math.floor(v / 61), week: v % 61 + 1 }, language)
                        : value(v)
                    return <li key={tie.higher_rank + '/' + tie.lower_rank}>
                      {tie.higher_rank}. {tie.higher_player_id} {t('precedes')} {tie.lower_rank}. {tie.lower_player_id} {t('at')} {tie.points} {t('points')}.
                      {' '}{t(reason)}{tie.result_slot === null ? '' : ' ' + value(tie.result_slot)}: {tieValue(tie.higher_value)} {t('versus')} {tieValue(tie.lower_value)}.
                    </li>
                  })}</ul>}
              <h4>{t('Stored roster')} ({data.manifest.players.length})</h4>
              {data.manifest.players.length === 0
                ? <p>{t('The stored roster is empty.')}</p>
                : <ul>{data.manifest.players.map(player => <li key={player.player_id}>
                  <strong>{player.player_id}</strong> · {t('Entry')} {weekLabel(player.tour_entry_week, language)}
                  {' · '}{player.retired ? t('Retired at this boundary') : t('Not retired at this boundary')}
                  <details><summary>{t('Stored tie-break token')}</summary>
                    <p style={{ overflowWrap: 'anywhere' }}>{player.tie_break_token}</p></details>
                </li>)}</ul>}
              {Boolean(data.manifest.disciplinary_zeros?.length) && <>
                <h4>{t('Resolved disciplinary zero inputs')}</h4>
                <p>{t('Each active zero reserves one Best N slot. These are stored inputs, not an automatic sanction decision.')}</p>
                <ul>{data.manifest.disciplinary_zeros?.map(z => <li key={z.zero_id}>
                  {z.player_id} · {z.zero_id} · {t('Effective')} {weekLabel(z.effective_week, language)} {t('for')} {z.duration_weeks} {t('weeks')}.
                  <details><summary>{t('Disciplinary source')}</summary>{z.source_fingerprint}</details>
                </li>)}</ul>
              </>}
              <h4>{t('Disciplinary decision history')}</h4>
              {data.zero_history_status === 'verified_stored_history' ? <>
                <p>{t('Verified against the stored decisions effective by this ranking week. Later changes are excluded.')}</p>
                {data.zero_sources?.length === 0 ? <p>{t('No zero decisions were effective by this week.')}</p>
                  : data.zero_sources === undefined ? <p>{t('Decision history verification is unavailable from this server.')}</p>
                    : <ul>{data.zero_sources.map(source => <li key={source.fingerprint}>
                      <strong>{source.version.zero.player_id} · {source.version.zero.zero_id}</strong>
                      <p>{t('Version effective')} {weekLabel(source.version.effective_week, language)}
                        {' · '}{t('Original start')} {weekLabel(source.version.zero.effective_week, language)}
                        {' · '}{t('Duration')} {source.version.zero.duration_weeks} {t('weeks')}</p>
                      <p>{t(({
                        superseded: 'Replaced by a later version at this boundary.',
                        expired: 'Expired at this boundary.',
                        reserves_slot: 'Active: reserves one Best N slot.',
                        player_not_classified: 'Active decision; player is outside this ranking.',
                      })[source.impact])}</p>
                      <details><summary>{t('Decision provenance')}</summary>
                        <p style={{ overflowWrap: 'anywhere' }}>{t('Source')}: {source.version.zero.source_fingerprint}</p>
                        <p style={{ overflowWrap: 'anywhere' }}>{t('Version')}: {source.fingerprint}</p>
                        <p style={{ overflowWrap: 'anywhere' }}>{t('Previous version')}: {source.version.previous_fingerprint ?? t('Initial decision')}</p>
                      </details>
                    </li>)}</ul>}
              </> : data.zero_history_status === 'caller_resolved'
                ? <p>{t('Zeros were supplied by the caller. This candidate does not verify their provenance against stored decision history.')}</p>
                : <p>{t('Decision history verification is unavailable from this server.')}</p>}
              <h4>{t('Stored result inputs')} ({data.manifest.results.length})</h4>
              {data.manifest.results.length === 0 ? <p>{t('No result inputs were supplied.')}</p>
                : <ul>{data.manifest.results.map(result => <li key={JSON.stringify([result.edition_id, result.player_id])}>
                  <strong>{result.player_id} · {result.edition_id}</strong>
                  {' · '}{t('Award')} {result.qualification_points + result.main_points} {t('points')}
                  {' · '}{result.ranked ? t('Ranked result') : t('Unranked result')}
                  <p>{t('First publication')} {weekLabel(result.first_publication_week, language)}
                    {' · '}{t('Validity')} {result.validity_weeks} {t('weeks')}</p>
                  <details><summary>{t('Stored source fingerprint')}</summary>
                    <p style={{ overflowWrap: 'anywhere' }}>{result.source_fingerprint}</p></details>
                </li>)}</ul>}
            </> : <p role="alert">{t('Stored inputs have no verified manifest.')}</p>}
        </div>}
      </>}
  </section>
}
