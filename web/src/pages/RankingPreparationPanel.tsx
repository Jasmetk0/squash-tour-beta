import { useEffect, useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { confirmRankingCommand, getRankingCandidateInputs, previewRankingCommand } from '../api/client'
import type { CandidateWeek, RankingCandidateDetail, RankingCandidateInputs, RankingDisciplinaryZero, RankingPreparationCommand, RankingPreparationPlayer, RankingPreparationPreview } from '../api/rankingCandidates'
import { formatApiError } from '../utils/apiErrors'

const label = (w: CandidateWeek) => `${2000 + w.season_index}/${String(2001 + w.season_index).slice(-2)} · Week ${w.week}`
export function nextRankingWeek(latest?: CandidateWeek): CandidateWeek | null {
  if (!latest) return {season_index:0,week:1}
  const ordinal = latest.season_index * 61 + latest.week
  return ordinal >= 3050 ? null : {season_index:Math.floor(ordinal / 61),week:ordinal % 61 + 1}
}

export function RankingPreparationPanel({runId, branchId, latest}: {runId:string;branchId:string;latest?:RankingCandidateDetail}): JSX.Element {
  const [opened,setOpened] = useState(false)
  const [saved,setSaved] = useState(false)
  const cache = useQueryClient()
  const target = nextRankingWeek(latest?.snapshot.week)
  const inputs = useQuery({
    queryKey:['ranking-preparation-inputs',runId,branchId,latest?.fingerprint],
    enabled:opened && Boolean(latest), retry:false,
    queryFn:async () => {
      const data = await getRankingCandidateInputs(runId,branchId,latest!.snapshot.week.season_index,latest!.snapshot.week.week)
      if (data.candidate_fingerprint !== latest!.fingerprint) throw new Error('The ranking head changed. Refresh history before preparing.')
      if (!data.manifest) throw new Error('This legacy candidate has no complete roster. Preparation requires a verified input history.')
      if (!data.manifest.zeros_from_history && data.manifest.disciplinary_zeros?.length) throw new Error('Caller-resolved zeros require an explicit history migration before using this form.')
      return data
    },
  })
  return <section className="ranking-preparation" aria-label="Prepare ranking">
    <h2>Prepare ranking</h2>
    {saved && <p role="status">Candidate prepared. Review ranking changes below to save a recoverable revision.</p>}
    {!target ? <p>The final Run week is already prepared. No season 51 ranking can be created.</p>
      : !opened ? <button type="button" onClick={() => {setSaved(false);setOpened(true)}}>{latest ? 'Prepare next ranking' : 'Prepare initial ranking'}</button>
      : latest && inputs.isPending ? <p role="status">Loading the previous roster and decisions…</p>
      : latest && inputs.isError ? <div role="alert"><p>{formatApiError(inputs.error)}</p><button type="button" onClick={() => void inputs.refetch()}>Retry preparation inputs</button></div>
      : <PreparationForm key={`${runId}/${branchId}/${latest?.fingerprint ?? 'initial'}`} runId={runId} branchId={branchId} latest={latest} inputs={inputs.data} target={target} onDone={() => {
          setOpened(false);setSaved(true)
          void cache.invalidateQueries({queryKey:['ranking-candidates',runId,branchId]})
          void cache.invalidateQueries({queryKey:['ranking-save',runId,branchId]})
        }} />}
  </section>
}

type ZeroChange = {version:NonNullable<RankingCandidateInputs['zero_sources']>[number];enabled:boolean;duration:number;source:string}
function PreparationForm({runId,branchId,latest,inputs,target,onDone}: {runId:string;branchId:string;latest?:RankingCandidateDetail;inputs?:RankingCandidateInputs;target:CandidateWeek;onDone:()=>void}): JSX.Element {
  const [players,setPlayers] = useState<RankingPreparationPlayer[]>(() => structuredClone(inputs?.manifest?.players ?? []))
  const [policyId,setPolicyId] = useState(latest?.snapshot.policy.policy_id ?? '')
  const [bestN,setBestN] = useState(latest?.snapshot.policy.best_n ?? 15)
  const [operator,setOperator] = useState('')
  const [reason,setReason] = useState('')
  const [reviewed,setReviewed] = useState(false)
  const [newZeros,setNewZeros] = useState<RankingDisciplinaryZero[]>([])
  const [changes,setChanges] = useState<ZeroChange[]>(() => (inputs?.zero_sources ?? []).filter(s => s.impact !== 'superseded').map(version => ({version,enabled:false,duration:version.version.zero.duration_weeks,source:''})))
  const [review,setReview] = useState<{command:RankingPreparationCommand;preview:RankingPreparationPreview} | null>(null)
  const mounted = useRef(true)
  useEffect(() => {mounted.current=true;return () => {mounted.current=false}},[])
  const preview = useMutation({mutationFn:(command:RankingPreparationCommand) => previewRankingCommand(runId,branchId,command),retry:false,
    onSuccess:(result,command) => {if (mounted.current) setReview({command,preview:result})}})
  const confirm = useMutation({mutationFn:() => {
    if (!review) throw new Error('Review a preview first.')
    return confirmRankingCommand(runId,branchId,review.command,review.preview)
  },retry:false,onSuccess:() => {if (mounted.current) onDone()}})
  const busy = preview.isPending || confirm.isPending
  const updatePlayer = (index:number, patch:Partial<RankingPreparationPlayer>) => setPlayers(old => old.map((p,i) => i === index ? {...p,...patch} : p))
  const build = ():RankingPreparationCommand => {
    const context = {run_id:runId,branch_id:branchId,target_week:target,policy:{policy_id:policyId,best_n:bestN},players:structuredClone(players),discipline:'stored_zeros' as const}
    const common = {command_id:`ranking-${crypto.randomUUID()}`,audit:{actor_label:operator,reason},zero_versions:[
      ...newZeros.map(zero => ({effective_week:target,previous_fingerprint:null,zero:structuredClone(zero)})),
      ...changes.filter(c => c.enabled).map(c => ({effective_week:target,previous_fingerprint:c.version.fingerprint,zero:{...c.version.version.zero,duration_weeks:c.duration,source_fingerprint:c.source}})),
    ]}
    return latest ? {...common,context:{...context,completed_week:latest.snapshot.week},tournaments:[]} : {...common,...context}
  }
  return <div>
    <p>Prepare {label(target)} using stored tournament results. Review the complete roster, policy and decisions for this boundary.</p>
    <p>This creates an unpublished candidate. World time and Viewer selection stay at their saved state.</p>
    {latest && target.week === 1 && <p>Season boundary: explicitly review the incoming season’s policy before calculating.</p>}
    <form onSubmit={event => {event.preventDefault();confirm.reset();preview.mutate(build())}}>
      <fieldset disabled={busy || Boolean(review)}>
        <legend>Ranking inputs</legend>
        <label>Policy reference <input required value={policyId} onChange={e => setPolicyId(e.target.value)} /></label>
        <label>Best N <input required type="number" min="1" step="1" value={bestN} onChange={e => setBestN(Number(e.target.value))} /></label>
        <h3>Roster ({players.length})</h3>
        {players.length === 0 && <p>An empty roster produces no ranked players.</p>}
        {players.map((player,index) => <fieldset key={index}>
          <legend>Player {index+1}</legend>
          <label>Player ID <input required value={player.player_id} onChange={e => updatePlayer(index,{player_id:e.target.value})} /></label>
          <label>Stable tie-break token <input required value={player.tie_break_token} onChange={e => updatePlayer(index,{tie_break_token:e.target.value})} /></label>
          <label>Tour entry season (1–50) <input required type="number" min="1" max="50" value={player.tour_entry_week.season_index+1} onChange={e => updatePlayer(index,{tour_entry_week:{...player.tour_entry_week,season_index:Number(e.target.value)-1}})} /></label>
          <label>Tour entry week <input required type="number" min="1" max="61" value={player.tour_entry_week.week} onChange={e => updatePlayer(index,{tour_entry_week:{...player.tour_entry_week,week:Number(e.target.value)}})} /></label>
          <label className="checkbox-label"><input type="checkbox" checked={player.retired} onChange={e => updatePlayer(index,{retired:e.target.checked})} />Retired at target week</label>
          <button type="button" onClick={() => setPlayers(old => old.filter((_,i) => i !== index))}>Remove player {index+1}</button>
        </fieldset>)}
        <button type="button" onClick={() => setPlayers(old => [...old,{player_id:'',tie_break_token:crypto.randomUUID(),tour_entry_week:{...target},retired:false}])}>Add player</button>
        <h3>Disciplinary zeros</h3>
        <p>New decisions apply at {label(target)}. Duration changes preserve each zero’s original start. Durations are explicit reviewed decisions.</p>
        {changes.map((change,index) => <fieldset key={change.version.fingerprint}>
          <legend>{change.version.version.zero.player_id} · {change.version.version.zero.zero_id}</legend>
          <p>Original start {label(change.version.version.zero.effective_week)} · Duration {change.version.version.zero.duration_weeks} weeks</p>
          <label className="checkbox-label"><input type="checkbox" checked={change.enabled} onChange={e => setChanges(old => old.map((c,i) => i === index ? {...c,enabled:e.target.checked} : c))} />Change this duration</label>
          {change.enabled && <>
            <label>New duration in weeks <input required type="number" min="1" value={change.duration} onChange={e => setChanges(old => old.map((c,i) => i === index ? {...c,duration:Number(e.target.value)} : c))} /></label>
            <label>Correction reference <input required value={change.source} onChange={e => setChanges(old => old.map((c,i) => i === index ? {...c,source:e.target.value} : c))} /></label>
          </>}
        </fieldset>)}
        {newZeros.map((zero,index) => <fieldset key={zero.zero_id}>
          <legend>New zero {index+1}</legend>
          <label>Zero player <select required value={zero.player_id} onChange={e => setNewZeros(old => old.map((z,i) => i === index ? {...z,player_id:e.target.value} : z))}><option value="">Select player</option>{players.filter(p => p.player_id).map((p,i) => <option key={i} value={p.player_id}>{p.player_id}</option>)}</select></label>
          <label>Duration in weeks <input required type="number" min="1" value={zero.duration_weeks || ''} onChange={e => setNewZeros(old => old.map((z,i) => i === index ? {...z,duration_weeks:Number(e.target.value)} : z))} /></label>
          <label>Decision reference <input required value={zero.source_fingerprint} onChange={e => setNewZeros(old => old.map((z,i) => i === index ? {...z,source_fingerprint:e.target.value} : z))} /></label>
          <button type="button" onClick={() => setNewZeros(old => old.filter((_,i) => i !== index))}>Remove zero {index+1}</button>
        </fieldset>)}
        <button type="button" onClick={() => setNewZeros(old => [...old,{zero_id:`zero-${crypto.randomUUID()}`,run_id:runId,branch_id:branchId,player_id:'',effective_week:{...target},duration_weeks:0,source_fingerprint:''}])}>Add disciplinary zero</button>
        <h3>Preparation audit</h3>
        <label>Operator label <input required maxLength={128} value={operator} onChange={e => setOperator(e.target.value)} /></label>
        <label>Reason <textarea required maxLength={2000} value={reason} onChange={e => setReason(e.target.value)} /></label>
        <label className="checkbox-label"><input required type="checkbox" checked={reviewed} onChange={e => setReviewed(e.target.checked)} />I reviewed the roster, target policy and decisions for this week.</label>
        <button type="submit" disabled={!reviewed}>Calculate preview</button>
      </fieldset>
    </form>
    {preview.isPending && <p role="status">Calculating preview…</p>}
    {preview.isError && <p role="alert">{formatApiError(preview.error)}</p>}
    {review && <section aria-label="Ranking preview">
      <h3>Review {label(review.preview.candidate.snapshot.week)}</h3>
      <p>Preview only · Best {review.preview.candidate.snapshot.policy.best_n} · {review.preview.candidate.snapshot.rows.length} ranked players · {review.command.zero_versions.length} decision changes</p>
      {review.preview.candidate.snapshot.rows.length === 0 ? <p>No players are classified at this boundary.</p> : <div className="table-scroll"><table><thead><tr><th>Rank</th><th>Player</th><th>Points</th><th>Active zeros</th></tr></thead><tbody>{review.preview.candidate.snapshot.rows.map(row => <tr key={row.player_id}><td>{row.rank}</td><td>{row.player_id}</td><td>{row.points}</td><td>{row.disciplinary_zeros?.length ?? 0}</td></tr>)}</tbody></table></div>}
      <button type="button" disabled={busy} onClick={() => confirm.mutate()}>{confirm.isError ? 'Retry this exact preparation' : 'Confirm candidate preparation'}</button>
      <button type="button" disabled={busy} onClick={() => {setReview(null);preview.reset();confirm.reset();setReviewed(false)}}>Edit inputs and recalculate</button>
      {confirm.isPending && <p role="status">Preparing candidate…</p>}
      {confirm.isError && <p role="alert">{formatApiError(confirm.error)} The request is retained for an exact retry. If inputs changed, edit and recalculate.</p>}
    </section>}
  </div>
}
