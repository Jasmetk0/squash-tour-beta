import {useMutation, useQuery, useQueryClient} from '@tanstack/react-query'
import {useState} from 'react'
import {useSearchParams} from 'react-router-dom'
import {getInitialPopulationComparison, getInitialPopulationPlayers, initialPopulationExportUrl, listInitialPopulationComparisons, runInitialPopulationComparison} from '../api/client'
import type {PopulationComparison, PopulationDistribution, PopulationRequest} from '../api/initialPopulationComparison'
import {SectionCard} from './RunScopedUi'
import {formatApiError} from '../utils/apiErrors'

const worldName = (id: string) => id === 'fifa_earth' ? 'FIFA Earth' : id === 'atp_earth' ? 'ATP Earth' : id
const number = (value: number | null | undefined) => value == null ? '—' : Number.isInteger(value) ? String(value) : value.toFixed(2)
const percent = (value: number | null | undefined) => value == null ? '—' : `${(value * 100).toFixed(2)}%`

export function InitialPopulationComparisonPanel(): JSX.Element {
  const client = useQueryClient()
  const [search, setSearch] = useSearchParams()
  const sessionId = search.get('population_session') ?? ''
  const [first, setFirst] = useState('fifa_earth')
  const [second, setSecond] = useState('atp_earth')
  const [season, setSeason] = useState('2000/01')
  const [count, setCount] = useState(1000)
  const [seeds, setSeeds] = useState('101, 202, 303, 404, 505')
  const [localError, setLocalError] = useState<string | null>(null)
  const sessions = useQuery({queryKey: ['player-population-sessions'], queryFn: listInitialPopulationComparisons, retry: false})
  const saved = useQuery({queryKey: ['player-population-comparison', sessionId], queryFn: () => getInitialPopulationComparison(sessionId), enabled: Boolean(sessionId), retry: false})
  const generate = useMutation({mutationFn: runInitialPopulationComparison, onSuccess: (result) => {
    client.setQueryData(['player-population-comparison', result.session_id], result)
    const next = new URLSearchParams(search); next.set('population_session', result.session_id); setSearch(next)
    void client.invalidateQueries({queryKey: ['player-population-sessions']})
  }})
  function submit(event: React.FormEvent) {
    event.preventDefault(); setLocalError(null)
    const parsed = seeds.trim().split(/[\s,;]+/).map(Number)
    if (!seeds.trim() || parsed.some(value => !Number.isSafeInteger(value) || value < 0 || value > 4294967295) || new Set(parsed).size !== parsed.length || first === second) {
      setLocalError('Select both distinct Earth packages and an explicit list of distinct integer seeds.'); return
    }
    const request: PopulationRequest = {world_ids: [first, second], season, player_count: count, seeds: parsed}
    generate.mutate(request)
  }
  return <SectionCard title="Initial population comparison">
    <p>Generate actual initial populations with the production World Package generator, outside every Run. Annual Talent Intake and synthetic prospect calibration are separate experiments.</p>
    <form className="grid" onSubmit={submit}>
      <label>First World Package<select aria-label="First World Package" value={first} disabled={generate.isPending} onChange={e => setFirst(e.target.value)}><option value="fifa_earth">FIFA Earth</option><option value="atp_earth">ATP Earth</option></select></label>
      <label>Second World Package<select aria-label="Second World Package" value={second} disabled={generate.isPending} onChange={e => setSecond(e.target.value)}><option value="fifa_earth">FIFA Earth</option><option value="atp_earth">ATP Earth</option></select></label>
      <label>Initial season<input aria-label="Initial population season" value={season} disabled={generate.isPending} onChange={e => setSeason(e.target.value)} /></label>
      <label>Players per population<input aria-label="Players per population" type="number" min={1} max={2000} value={count} disabled={generate.isPending} onChange={e => setCount(Number(e.target.value))} /></label>
      <label>Explicit seeds<input aria-label="Initial population seeds" value={seeds} disabled={generate.isPending} onChange={e => setSeeds(e.target.value)} /></label>
      <button type="submit" disabled={generate.isPending}>Generate and save population comparison</button>
    </form>
    {generate.isPending ? <p role="status">Loading read-only source snapshots and generating populations…</p> : null}
    {localError || generate.error ? <p role="alert" className="error">{localError ?? formatApiError(generate.error)}</p> : null}
    <label>Saved population comparison<select aria-label="Saved population comparison" value={sessionId} onChange={e => {const next = new URLSearchParams(search); if (e.target.value) next.set('population_session',e.target.value); else next.delete('population_session'); setSearch(next)}}>
      <option value="">Choose a saved Test Session</option>
      {sessions.data?.map(item => <option key={item.session_id} value={item.session_id}>{item.request.season} · {item.request.player_count} players · seeds {item.request.seeds.join(', ')} · {item.fingerprint.slice(0,8)}</option>)}
    </select></label>
    {sessions.error || saved.error ? <p role="alert" className="error">{formatApiError(sessions.error ?? saved.error)}</p> : null}
    {saved.data ? <PopulationResults key={saved.data.session_id} result={saved.data} /> : null}
  </SectionCard>
}

function PopulationResults({result}: {result: PopulationComparison}) {
  const [runIndex,setRunIndex] = useState(0)
  const [metric,setMetric] = useState('potential_ability')
  const [page,setPage] = useState(0)
  const run = result.runs[runIndex]
  const raw = useQuery({queryKey: ['player-population-players',result.session_id,run?.world_id,run?.seed], queryFn: () => getInitialPopulationPlayers(result.session_id,run.world_id,run.seed,run.gameplay_fingerprint), enabled: Boolean(run), retry: false})
  const [left,right] = result.aggregates
  const countries = [...new Set([...left.summary.countries,...right.summary.countries].map(c => c.code))].sort((a,b) => {
    const total = (code: string) => (left.summary.countries.find(c => c.code===code)?.count ?? 0)+(right.summary.countries.find(c => c.code===code)?.count ?? 0)
    return total(b)-total(a) || a.localeCompare(b)
  })
  return <>
    <h4>Saved initial population results</h4>
    <p>Saved {result.request.season} · {result.request.player_count} players per population · seeds {result.request.seeds.join(', ')} · {result.duration_seconds.toFixed(2)} s including source preparation. {result.cached ? 'Reused the identical saved experiment; no generation repeated.' : ''}</p>
    <div className="quick-actions"><a href={initialPopulationExportUrl(result.session_id,'json')}>Export complete population JSON</a><a href={initialPopulationExportUrl(result.session_id,'csv')}>Export players CSV</a></div>
    <h5>Pooled distributions across seeds</h5>
    <p>Current ability and attributes use the existing initial-pool 1–99 model, separate from Potential Ability. Quantiles interpolate linearly; pooled samples are observations, not theoretical probabilities.</p>
    <MetricTable label="Pooled population metrics" metrics={Object.keys(left.summary.metrics)} left={left.summary.metrics} right={right.summary.metrics} leftName={worldName(left.world_id)} rightName={worldName(right.world_id)} />
    <table aria-label="Between-seed metric variability"><thead><tr><th>Metric</th><th>World</th><th>Seed means min–max</th><th>SD of seed means</th><th>Seed P99 min–max</th></tr></thead><tbody>{Object.keys(left.summary.metrics).flatMap(name => result.aggregates.map(aggregate => {
      const mean = aggregate.between_seed_metrics[name].mean, tail = aggregate.between_seed_metrics[name].p99
      return <tr key={`${aggregate.world_id}-${name}`}><td>{name}</td><td>{worldName(aggregate.world_id)}</td><td>{number(mean.minimum)}–{number(mean.maximum)}</td><td>{number(mean.standard_deviation)}</td><td>{number(tail.minimum)}–{number(tail.maximum)}</td></tr>
    }))}</tbody></table>
    <h5>Existing potential tiers and rare tails</h5>
    <table aria-label="Existing initial-pool potential tiers"><thead><tr><th>Tier</th><th>World</th><th>Pooled count / share</th><th>Per-seed count min–max</th></tr></thead><tbody>{Object.keys(left.summary.potential_tiers).flatMap(tier => result.aggregates.map(a => <tr key={`${a.world_id}-${tier}`}><td>{tier}</td><td>{worldName(a.world_id)}</td><td>{a.summary.potential_tiers[tier]} / {percent(a.summary.potential_tiers[tier]/a.summary.player_count)}</td><td>{number(a.between_seed_tiers[tier].minimum)}–{number(a.between_seed_tiers[tier].maximum)}</td></tr>))}</tbody></table>
    <label>Histogram metric<select aria-label="Population histogram metric" value={metric} onChange={e => setMetric(e.target.value)}>{Object.keys(left.summary.metrics).map(name => <option key={name}>{name}</option>)}</select></label>
    <p>Intervals below are analytical histogram bins, not new talent categories.</p>
    <table aria-label="Population histogram"><thead><tr><th>Interval</th><th>{worldName(left.world_id)}</th><th>{worldName(right.world_id)}</th></tr></thead><tbody>{left.summary.metrics[metric].histogram.map((bin,index) => <tr key={bin.lower}><td>{bin.lower}–{bin.upper}</td>{result.aggregates.map(a => <td key={a.world_id}><progress max={a.summary.player_count} value={a.summary.metrics[metric].histogram[index].count} /> {a.summary.metrics[metric].histogram[index].count}</td>)}</tr>)}</tbody></table>
    <h5>Country representation, including zero counts</h5>
    <p>Counts below pool all seeds; min–max uses one population per seed. The production country allocation is seed-independent. Countries missing from a package would show — rather than zero.</p>
    <div style={{maxHeight: '28rem',overflow: 'auto'}}><table aria-label="Earth population country comparison"><thead><tr><th>Country</th><th>{worldName(left.world_id)} count/share</th><th>Per-seed min–max</th><th>{worldName(right.world_id)} count/share</th><th>Per-seed min–max</th><th>Share difference right − left</th></tr></thead><tbody>{countries.map(code => {
      const a=left.summary.countries.find(c=>c.code===code), b=right.summary.countries.find(c=>c.code===code)
      return <tr key={code}><td>{code} · {a?.name ?? b?.name}</td>{result.aggregates.flatMap(aggregate => {
        const row=aggregate.summary.countries.find(c=>c.code===code), v=aggregate.between_seed_countries[code]
        return [<td key={`${aggregate.world_id}-count`}>{row ? `${row.count} / ${percent(row.share)}` : '—'}</td>,<td key={`${aggregate.world_id}-range`}>{v ? `${number(v.minimum)}–${number(v.maximum)}` : '—'}</td>]
      })}<td>{a?.share != null && b?.share != null ? percent(b.share-a.share) : '—'}</td></tr>
    })}</tbody></table></div>
    <p>Tour registration before/after entry: —. {left.summary.tour_registration.reason}</p>
    <h5>Individual populations</h5>
    <label>Inspect population<select aria-label="Inspect generated population" value={runIndex} onChange={e=>{setRunIndex(Number(e.target.value));setPage(0)}}>{result.runs.map((r,index)=><option key={`${r.world_id}-${r.seed}`} value={index}>{worldName(r.world_id)} · seed {r.seed} · {r.summary.player_count} players · {r.duration_seconds.toFixed(3)} s</option>)}</select></label>
    <MetricTable label="Selected population metrics" metrics={Object.keys(run.summary.metrics)} left={run.summary.metrics} leftName={`${worldName(run.world_id)} seed ${run.seed}`} />
    <div style={{maxHeight: '20rem',overflow: 'auto'}}><table aria-label="Selected population country counts"><thead><tr><th>Country</th><th>Count</th><th>Share</th></tr></thead><tbody>{run.summary.countries.map(c=><tr key={c.code}><td>{c.code}</td><td>{c.count}</td><td>{percent(c.share)}</td></tr>)}</tbody></table></div>
    {raw.error ? <p role="alert" className="error">{formatApiError(raw.error)}</p> : null}
    {raw.data ? <><p>Stored population: {raw.data.players.length} players; fingerprint {raw.data.gameplay_fingerprint}.</p><table aria-label="Actual generated population players"><thead><tr><th>Player</th><th>Country</th><th>Birth</th><th>Age</th><th>Potential / tier</th><th>Current ability</th><th>Current attributes</th></tr></thead><tbody>{raw.data.players.slice(page*25,(page+1)*25).map(p=><tr key={p.player_id}><td>{p.name} · {p.player_id}</td><td>{p.country_code}</td><td>{p.birth_year} / W{p.birth_year_week}</td><td>{p.age_at_generation}</td><td>{p.potential_ability} / {p.potential_tier}</td><td>{p.current_ability}</td><td>{Object.entries(p.attributes).map(([name,value])=>`${name}: ${value}`).join(' · ')}</td></tr>)}</tbody></table><div className="quick-actions"><button disabled={page===0} onClick={()=>setPage(page-1)}>Previous population players</button><span>Page {page+1}</span><button disabled={(page+1)*25>=raw.data.players.length} onClick={()=>setPage(page+1)}>Next population players</button></div></> : null}
    <details><summary>Generation provenance, effective configuration and historical fallbacks</summary><p>Engine commit: {result.engine.commit ?? 'unavailable'}; uncommitted source: {String(result.engine.uncommitted_source)}; source fingerprint {result.engine.source_fingerprint}.</p><p>Session: {result.session_id}; saved payload fingerprint {result.fingerprint}.</p>{result.sources.map(source=><p key={source.world_id}>{worldName(source.world_id)} · {source.country_count} countries · version {source.version} · {source.package_fingerprint}</p>)}{Object.entries(result.interpretation).map(([name,text])=><p key={name}><strong>{name}:</strong> {text}</p>)}<p>Full per-country source years and fallback values are in the JSON export.</p><pre>{JSON.stringify(result.effective_configuration,null,2)}</pre></details>
  </>
}

function MetricTable({label,metrics,left,right,leftName,rightName}: {label: string; metrics: string[]; left: Record<string,PopulationDistribution>; right?: Record<string,PopulationDistribution>; leftName: string; rightName?: string}) {
  return <table aria-label={label}><thead><tr><th>Metric</th><th>World</th><th>Min</th><th>P10</th><th>P25</th><th>Median</th><th>P75</th><th>P90</th><th>P99</th><th>Max</th><th>Mean</th>{right ? <th>Mean difference right − left</th> : null}</tr></thead><tbody>{metrics.flatMap(name=>(right ? [left,right] : [left]).map((source,index)=><tr key={`${name}-${index}`}><td>{name}</td><td>{index===0 ? leftName : rightName}</td>{(['minimum','p10','p25','p50','p75','p90','p99','maximum','mean'] as const).map(stat=><td key={stat}>{number(source[name][stat])}</td>)}{right ? <td>{index===1 && right[name].mean != null && left[name].mean != null ? number(right[name].mean!-left[name].mean!) : '—'}</td> : null}</tr>))}</tbody></table>
}
