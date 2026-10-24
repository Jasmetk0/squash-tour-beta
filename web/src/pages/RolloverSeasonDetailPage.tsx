import { useQuery } from '@tanstack/react-query'
import { ChangeEvent, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import { getNextSeasonPlayers, getPlayerTransitions, getRolloverBySeason } from '../api/client'
import {
  CompactSummaryCard,
  CurrentContextStrip,
  EmptyState,
  JsonPayloadBlock,
  MetadataList,
  RunScopedHeader,
  SectionCard,
  SummaryPills
} from '../components/RunScopedUi'
import { formatApiError, isApiNotFound } from '../utils/apiErrors'

function parseToSeasonParam(toSeasonParam: string | undefined): number | null {
  if (!toSeasonParam || !/^[0-9]+$/.test(toSeasonParam)) return null
  const parsed = Number(toSeasonParam)
  return Number.isSafeInteger(parsed) && parsed > 0 ? parsed : null
}

import { useHistoryText } from './runHistoryText'
export function RolloverSeasonDetailPage(): JSX.Element {
  const t = useHistoryText()
  const { runId = '', toSeason: toSeasonParam } = useParams()
  const [playerIdFilter, setPlayerIdFilter] = useState('')

  const toSeason = parseToSeasonParam(toSeasonParam)

  const seasonSummaryQuery = useQuery({
    queryKey: ['rollover-by-season', runId, toSeason],
    queryFn: () => getRolloverBySeason(runId, toSeason ?? 0),
    enabled: Boolean(runId && toSeason !== null),
    retry: false
  })

  const transitionsQuery = useQuery({
    queryKey: ['rollover-transitions', runId, toSeason],
    queryFn: () => getPlayerTransitions(runId, toSeason ?? 0),
    enabled: Boolean(runId && toSeason !== null),
    retry: false
  })

  const playersQuery = useQuery({
    queryKey: ['rollover-next-season-players', runId, toSeason],
    queryFn: () => getNextSeasonPlayers(runId, toSeason ?? 0),
    enabled: Boolean(runId && toSeason !== null),
    retry: false
  })

  const normalizedFilter = playerIdFilter.trim().toLowerCase()

  const filteredTransitions = useMemo(() => {
    const transitions = transitionsQuery.data?.transitions ?? []
    if (!normalizedFilter) return transitions
    return transitions.filter((item) => item.player_id.toLowerCase().includes(normalizedFilter))
  }, [normalizedFilter, transitionsQuery.data])

  const filteredPlayers = useMemo(() => {
    const players = playersQuery.data?.players ?? []
    if (!normalizedFilter) return players
    return players.filter((item) => item.player_id.toLowerCase().includes(normalizedFilter))
  }, [normalizedFilter, playersQuery.data])

  const invalidSeasonParam = toSeason === null
  const seasonNotFound = isApiNotFound(seasonSummaryQuery.error)

  return (
    <section className="panel">
      <RunScopedHeader
        title={t('Rollover season detail')}
        runId={runId}
        subtitle={t('Read-only inspection for one rollover target season.')}
      />
      <CurrentContextStrip
        items={[
          { label: t('Run'), value: runId || 'unknown' },
          { label: t('Target season'), value: toSeason ?? t('Invalid') },
          { label: 'Filter', value: normalizedFilter || t('None') }
        ]}
      />

      <SectionCard title={t('Rollover season context')}>
        <MetadataList
          items={[
            { label: t('Overview'), value: <Link to={`/runs/${encodeURIComponent(runId)}/rollover`}>{t('Back to rollover overview')}</Link> },
            { label: t('Run'), value: runId || 'unknown' },
            { label: t('To season parameter'), value: toSeasonParam ?? 'missing' }
          ]}
        />
        {invalidSeasonParam ? <EmptyState message={t('Invalid or missing target season in URL. Use a positive integer season.')} /> : null}
      </SectionCard>

      {!invalidSeasonParam ? (
        <>
          <SectionCard title={`Rollover summary (S${toSeason})`}>
            {seasonSummaryQuery.isLoading && <p className="status">{t('Loading rollover summary...')}</p>}
            {seasonNotFound && <EmptyState message={`No rollover summary found for season ${toSeason}.`} />}
            {seasonSummaryQuery.error && !seasonNotFound && (
              <p className="error">Failed to load rollover summary: {formatApiError(seasonSummaryQuery.error)}</p>
            )}
            {seasonSummaryQuery.data ? (
              <>
                <SummaryPills
                  items={[
                    { label: t('From season'), value: seasonSummaryQuery.data.rollover.from_season },
                    { label: t('To season'), value: seasonSummaryQuery.data.rollover.to_season },
                    { label: t('Transitioned players'), value: seasonSummaryQuery.data.rollover.transitioned_players }
                  ]}
                />
                <CompactSummaryCard
                  items={[
                    { label: t('Run ID'), value: seasonSummaryQuery.data.rollover.run_id },
                    {
                      label: t('Metadata keys'),
                      value: Object.keys(seasonSummaryQuery.data.rollover.metadata ?? {}).length
                    }
                  ]}
                />
              </>
            ) : null}
          </SectionCard>

          <SectionCard title={t('Inspection summary')}>
            <SummaryPills
              items={[
                { label: t('Target season'), value: toSeason },
                { label: t('Transition records'), value: transitionsQuery.isLoading ? t('Loading...') : filteredTransitions.length },
                { label: t('Next-season players'), value: playersQuery.isLoading ? t('Loading...') : filteredPlayers.length }
              ]}
            />
            <label>
              {t('player_id filter')}
              <input
                type="text"
                value={playerIdFilter}
                onChange={(event: ChangeEvent<HTMLInputElement>) => setPlayerIdFilter(event.target.value)}
                placeholder={t('Filter by player_id')}
                aria-label={t('player_id filter')}
              />
            </label>
          </SectionCard>

          <SectionCard title={t('Player transitions')}>
            {transitionsQuery.isLoading && <p className="status">{t('Loading transitions...')}</p>}
            {transitionsQuery.error && <p className="error">Failed to load transitions: {formatApiError(transitionsQuery.error)}</p>}
            {transitionsQuery.data ? (
              filteredTransitions.length === 0 ? (
                <EmptyState
                  message={normalizedFilter ? t('No transition records match the active player_id filter.') : t('No transition records are available for this season.')}
                />
              ) : (
                <JsonPayloadBlock title={t('Transitions payload')} payload={filteredTransitions} emptyText={t('No transition payload available.')} />
              )
            ) : null}
          </SectionCard>

          <SectionCard title={t('Next-season players')}>
            {playersQuery.isLoading && <p className="status">{t('Loading next-season players...')}</p>}
            {playersQuery.error && <p className="error">Failed to load next-season players: {formatApiError(playersQuery.error)}</p>}
            {playersQuery.data ? (
              filteredPlayers.length === 0 ? (
                <EmptyState
                  message={normalizedFilter ? t('No next-season players match the active player_id filter.') : t('No next-season players are available for this season.')}
                />
              ) : (
                <JsonPayloadBlock title={t('Next-season players payload')} payload={filteredPlayers} emptyText={t('No player payload available.')} />
              )
            ) : null}
          </SectionCard>
        </>
      ) : null}
    </section>
  )
}
