import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useState } from 'react'

import { getSeasonCategoryPoints, initializeSeasonCategoryPoints, updateSeasonCategoryPoints } from '../api/client'
import type { SeasonCategoryPointsTable } from '../api/types'

function CategoryEditor({ row, onSaved }: { row: SeasonCategoryPointsTable; onSaved: () => void }): JSX.Element {
  const [values, setValues] = useState<Record<string, string>>({})
  useEffect(() => setValues(Object.fromEntries(Object.entries(row.ranking_points_table).map(([key, value]) => [key, String(value)]))), [row])
  const save = useMutation({ mutationFn: () => updateSeasonCategoryPoints(row.season, row.category, Object.fromEntries(Object.entries(values).filter(([, value]) => value !== '').map(([key, value]) => [key, Number(value)]))), onSuccess: onSaved })
  const keys = Array.from(new Set([...Object.keys(row.ranking_points_table), 'champion', 'finalist', 'semifinal', 'quarterfinal', 'round_of_16', 'round_of_32', 'round_of_64', 'round_of_128'] ))
  return <form onSubmit={(event) => { event.preventDefault(); save.mutate() }}><h4>{row.category}</h4><p>Source: <strong>{row.provenance}</strong>{row.source_season ? ` (${row.source_season})` : ''}</p><div className="grid">{keys.map((key) => <label key={key}>{key}<input aria-label={`${row.category} ${key}`} type="number" min="0" step="1" value={values[key] ?? ''} onChange={(event) => setValues((current) => ({ ...current, [key]: event.target.value }))} /></label>)}</div><button type="submit" disabled={save.isPending}>Save {row.category}</button></form>
}

export function SeasonCategoryPoints({ seasonLabelRaw }: { seasonLabelRaw: string | null }): JSX.Element | null {
  const client = useQueryClient()
  const query = useQuery({ queryKey: ['season-category-points', seasonLabelRaw], queryFn: () => getSeasonCategoryPoints(seasonLabelRaw ?? ''), enabled: Boolean(seasonLabelRaw) })
  const initialize = useMutation({ mutationFn: () => initializeSeasonCategoryPoints(seasonLabelRaw ?? ''), onSuccess: () => client.invalidateQueries({ queryKey: ['season-category-points', seasonLabelRaw] }) })
  if (!seasonLabelRaw) return null
  return <section><h2>Season Category Points</h2><p>Category tables are owned by this Season. Existing Tournament Editions keep their historical points snapshots.</p>{query.data && !query.data.initialized ? <button type="button" onClick={() => initialize.mutate()}>Initialize Season Category Points</button> : null}{query.data?.categories.map((row) => <CategoryEditor key={row.category} row={row} onSaved={() => client.invalidateQueries({ queryKey: ['season-category-points', seasonLabelRaw] })} />)}</section>
}
