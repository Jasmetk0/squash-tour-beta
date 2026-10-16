import { useQuery } from '@tanstack/react-query'
import { useEffect, useRef, useState } from 'react'
import { getRunPackageState, previewRunCalendarPlayerPool } from '../api/client'
import { validateCalendarPoolPreview, type CalendarPoolPreview } from '../api/calendarInitialPool'
import type { RunCalendarMetadata } from '../api/runCalendarCreation'
import { runOwnedWorldIds } from '../api/runInitialWorldSetup'
import { formatApiError } from '../utils/apiErrors'

/** First v2 UI slice: new dates can be inspected; no adoption/Save authority. */
export function RunCalendarPlayerPreviewPanel({runId, branchId, head, clock, locale}: {
  runId: string; branchId: string; head: string; clock: RunCalendarMetadata; locale: 'cs' | 'en'
}): JSX.Element {
  const cs = locale === 'cs'
  const source = useQuery({queryKey: ['run-package-state', runId, branchId],
    queryFn: () => getRunPackageState(runId, branchId), retry: false})
  const state = source.data?.state
  const fingerprint = source.data?.fingerprint
  const sourceValid = source.isSuccess && !source.isFetching
    && state?.run_id === runId && state.branch_id === branchId && Boolean(fingerprint)
  const worlds = sourceValid ? runOwnedWorldIds(state) : []
  const [world, setWorld] = useState('')
  const selected = worlds.includes(world) ? world : worlds[0] ?? ''
  const [seed, setSeed] = useState('802')
  const [count, setCount] = useState('128')
  const [minAge, setMinAge] = useState('15')
  const [maxAge, setMaxAge] = useState('45')
  const [review, setReview] = useState<{scope: string; preview: CalendarPoolPreview} | null>(null)
  const [pending, setPending] = useState(false)
  const [error, setError] = useState('')
  const [page, setPage] = useState(0)
  const scope = JSON.stringify([runId, branchId, head, clock, fingerprint, selected, seed, count, minAge, maxAge])
  const scopeRef = useRef(scope)
  scopeRef.current = scope
  const token = useRef(0)
  useEffect(() => () => {token.current++}, [])
  // A source/refetch/scope change immediately hides stale results. Delayed
  // responses may never be shown as belonging to a new selection.
  const active = sourceValid && review?.scope === scope ? review.preview : null
  const numeric = [seed, count, minAge, maxAge].every(v => /^\d+$/.test(v) && Number.isSafeInteger(Number(v)))
  const valid = numeric && Number(seed) >= 0 && Number(count) >= 1 && Number(count) <= 10000
    && Number(minAge) >= 15 && Number(maxAge) <= 45 && Number(minAge) <= Number(maxAge)
  function changed(setter: (v: string) => void, value: string): void {
    token.current++; setPending(false); setReview(null); setError(''); setPage(0); setter(value)
  }
  async function generate(): Promise<void> {
    if (!valid || !sourceValid || !fingerprint || !selected) return
    const thisToken = ++token.current
    const thisScope = scope
    const input = {world_package_id: selected, seed: Number(seed), target_pool_size: Number(count),
      min_age: Number(minAge), max_age: Number(maxAge)}
    setReview(null); setError(''); setPending(true); setPage(0)
    try {
      const value = await previewRunCalendarPlayerPool(runId, branchId, input)
      if (token.current !== thisToken || scopeRef.current !== thisScope) return
      setReview({scope: thisScope, preview: validateCalendarPoolPreview(
        value, runId, branchId, head, fingerprint, clock, input)})
    } catch (e) {
      if (token.current === thisToken && scopeRef.current === thisScope) setError(formatApiError(e))
    } finally {
      if (token.current === thisToken) setPending(false)
    }
  }
  return <section data-run-navigation-readonly aria-label={cs ? 'Náhled hráčů podle kalendáře Runu' : 'Run calendar player preview'}>
    <p role="status">{cs
      ? 'Náhled podle uloženého kalendáře Runu. Hráči se zatím nepřidají do Runu; uložení a simulace pro tento kalendář čekají na převod lifecycle a rankingu.'
      : 'Preview using the saved Run calendar. Players cannot be added yet; adoption and simulation await the lifecycle and ranking migration.'}</p>
    {source.isPending && <p role="status">{cs ? 'Načítání balíčků…' : 'Loading packages…'}</p>}
    {source.error && <p role="alert">{formatApiError(source.error)}</p>}
    {source.isSuccess && !worlds.length && <p>{cs ? 'Nejdřív zkopíruj World Package do tohoto Runu.' : 'Copy a World Package into this Run first.'}</p>}
    <form onSubmit={e => {e.preventDefault(); void generate()}}>
      <label>{cs ? 'Svět' : 'World'}<select aria-label={cs ? 'Svět' : 'World'} value={selected}
        onChange={e => changed(setWorld, e.target.value)}>
        {!worlds.length && <option value="">—</option>}
        {worlds.map(id => <option key={id} value={id}>{id}</option>)}
      </select></label>
      {[[cs ? 'Seed' : 'Seed', seed, setSeed], [cs ? 'Počet hráčů' : 'Player count', count, setCount],
        [cs ? 'Minimální věk' : 'Minimum age', minAge, setMinAge],
        [cs ? 'Maximální věk' : 'Maximum age', maxAge, setMaxAge]].map(([label, value, setter]) =>
        <label key={label as string}>{label as string}<input aria-label={label as string} inputMode="numeric"
          value={value as string} onChange={e => changed(setter as (v: string) => void, e.target.value)}/></label>)}
      <button type="submit" disabled={!valid || !sourceValid || !selected || pending}>
        {pending ? (cs ? 'Generování…' : 'Generating…') : (cs ? 'Generovat náhled' : 'Generate preview')}</button>
    </form>
    {error && <p role="alert">{error}</p>}
    {active && <>
      <p>{cs ? 'Vygenerováno' : 'Generated'}: {active.result.players.length} · {clock.weeks_per_year} {cs ? 'týdnů za rok' : 'weeks per year'}</p>
      <div className="table-wrap"><table><thead><tr>{(cs
        ? ['Jméno', 'Země', 'Rok narození', 'Týden narození', 'Věk', 'Schopnost', 'Potenciál']
        : ['Name', 'Country', 'Birth year', 'Birth week', 'Age', 'Ability', 'Potential']).map(h => <th key={h}>{h}</th>)}</tr></thead>
        <tbody>{active.result.players.slice(page * 50, (page + 1) * 50).map(p => <tr key={p.player_id}>
          <td>{p.name}</td><td>{p.country_code}</td><td>{p.birth_year}</td><td>{p.birth_year_week}</td>
          <td>{p.current_age_years}</td><td>{p.current_ability}</td><td>{p.potential_ability}</td>
        </tr>)}</tbody></table></div>
      <div className="actions"><button disabled={page === 0} onClick={() => setPage(page - 1)}>{cs ? 'Předchozí' : 'Previous'}</button>
        <span>{page + 1} / {Math.ceil(active.result.players.length / 50)}</span>
        <button disabled={(page + 1) * 50 >= active.result.players.length} onClick={() => setPage(page + 1)}>{cs ? 'Další' : 'Next'}</button></div>
    </>}
  </section>
}
