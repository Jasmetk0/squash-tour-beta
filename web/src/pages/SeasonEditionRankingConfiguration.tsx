import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { FormEvent, useEffect, useState } from 'react'

import { getSeasonCalendar, updateTournamentEditionRanking } from '../api/client'
import type { SeasonCalendarEvent } from '../api/types'
import { SectionCard } from '../components/RunScopedUi'
import { formatApiError } from '../utils/apiErrors'
import { safeToCompactSeasonLabel } from '../utils/seasonLabels'
import { normalizeEditionRanking } from './seasonEditionRanking'

function RankingEditor({ event, saving, save }: { event: SeasonCalendarEvent; saving: boolean; save: (status: 'ranked' | 'unranked', table: Record<string, unknown>) => void }): JSX.Element {
  const [status, setStatus] = useState(event.ranking_status)
  const [values, setValues] = useState<Record<string, string>>({})
  const editable = event.status === 'planned' && !saving
  useEffect(() => { setStatus(event.ranking_status); setValues(Object.fromEntries(event.required_ranking_point_stages.map((stage) => [stage, event.ranking_points_table[stage]?.toString() ?? '']))) }, [event])
  function submit(change: FormEvent<HTMLFormElement>): void {
    change.preventDefault(); const table = { ...event.ranking_points_table }
    for (const stage of event.required_ranking_point_stages) { const raw = values[stage]; if (raw === '' || !/^\d+$/.test(raw)) delete table[stage]; else table[stage] = Number(raw) }
    save(status, table)
  }
  return <form onSubmit={submit}><h4>{event.event_name}</h4><label>Ranking status <select aria-label={`Ranking status for ${event.event_name}`} value={status} disabled={!editable} onChange={(change) => setStatus(change.target.value as 'ranked' | 'unranked')}><option value="ranked">Ranked</option><option value="unranked">Unranked</option></select></label>{status === 'ranked' ? <><p className={event.points_table_complete ? 'status' : 'error'}>{event.points_table_complete ? 'Points table complete.' : `Points table incomplete. Missing: ${event.missing_required_point_stages.join(', ')}`}</p><fieldset disabled={!editable}><legend>Required ranking points</legend>{event.required_ranking_point_stages.map((stage) => <label key={stage}>{stage}<input aria-label={`Points for ${stage}`} type="number" min="0" step="1" required value={values[stage] ?? ''} aria-invalid={event.missing_required_point_stages.includes(stage)} onChange={(change) => setValues((current) => ({ ...current, [stage]: change.target.value }))} /></label>)}</fieldset></> : <p>Unranked: awards no MSA points or Best N result; tournament history remains.</p>}<button type="submit" disabled={!editable}>Save ranking configuration</button></form>
}

export function SeasonEditionRankingConfiguration({ seasonLabelRaw }: { seasonLabelRaw: string | null }): JSX.Element | null {
  const season = seasonLabelRaw ? safeToCompactSeasonLabel(seasonLabelRaw) : null
  const queryClient = useQueryClient()
  const query = useQuery({ queryKey: ['season-edition-ranking-configuration', season], queryFn: () => getSeasonCalendar(season ?? ''), enabled: Boolean(season), retry: false })
  const mutation = useMutation({ mutationFn: ({ eventId, status, table }: { eventId: string; status: 'ranked' | 'unranked'; table: Record<string, unknown> }) => updateTournamentEditionRanking(season ?? '', eventId, { ranking_status: status, ranking_points_table: table }), onSuccess: () => queryClient.invalidateQueries({ queryKey: ['season-edition-ranking-configuration', season] }) })
  if (!season) return null
  const events = (query.data?.calendar?.events ?? []).map(normalizeEditionRanking)
  return <SectionCard title="Tournament Edition ranking configuration">{query.error ? <p className="error">Unable to load ranking configuration: {formatApiError(query.error)}</p> : null}{events.length === 0 ? <p className="status">No persisted Tournament Editions are available.</p> : events.map((event) => <RankingEditor key={event.event_id} event={event} saving={mutation.isPending} save={(status, table) => mutation.mutate({ eventId: event.event_id, status, table })} />)}</SectionCard>
}
