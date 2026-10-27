import { useEffect, useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { confirmRankingCommand, getRankingCandidateInputs, previewRankingCommand } from '../api/client'
import type { CandidateWeek, RankingCandidateDetail, RankingCandidateInputs, RankingDisciplinaryZero, RankingPreparationCommand, RankingPreparationPlayer, RankingPreparationPreview } from '../api/rankingCandidates'
import { RankingResultCorrections } from './RankingResultCorrections'
import type { RankingResultCorrection } from '../api/rankingCandidates'
import { formatApiError } from '../utils/apiErrors'
import { useRankingWorkflowLanguage, rankingWorkflowText, rankingWorkflowWeekLabel } from './rankingWorkflowText'

export function nextRankingWeek(latest?: CandidateWeek): CandidateWeek | null {
  if (!latest) return {season_index:0,week:1}
  const ordinal = latest.season_index * 61 + latest.week
  return ordinal >= 3050 ? null : {season_index:Math.floor(ordinal / 61),week:ordinal % 61 + 1}
}

export function RankingPreparationPanel({runId, branchId, latest}: {runId:string;branchId:string;latest?:RankingCandidateDetail}): JSX.Element {
  const language = useRankingWorkflowLanguage()
  const t = (value: string) => rankingWorkflowText(value, language)
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
  return <section className="ranking-preparation" aria-label={t('Prepare ranking')}>
    <h2>{t('Prepare ranking')}</h2>
    {saved && <p role="status">{t('Candidate prepared. Review ranking changes below to save a recoverable revision.')}</p>}
    {!target ? <p>{t('The final Run week is already prepared. No season 51 ranking can be created.')}</p>
      : !opened ? <button type="button" onClick={() => {setSaved(false);setOpened(true)}}>{t(latest ? 'Prepare next ranking' : 'Prepare initial ranking')}</button>
      : latest && inputs.isPending ? <p role="status">{t('Loading the previous roster and decisions…')}</p>
      : latest && inputs.isError ? <div role="alert"><p>{t('Unable to load preparation inputs.')} {t(formatApiError(inputs.error))}</p><button type="button" onClick={() => void inputs.refetch()}>{t('Retry preparation inputs')}</button></div>
      : <PreparationForm key={`${runId}/${branchId}/${latest?.fingerprint ?? 'initial'}`} runId={runId} branchId={branchId} latest={latest} inputs={inputs.data} target={target} onDone={() => {
          setOpened(false);setSaved(true)
          void cache.invalidateQueries({queryKey:['ranking-candidates',runId,branchId]})
          void cache.invalidateQueries({queryKey:['ranking-save',runId,branchId]})
        }} />}
  </section>
}

type ZeroChange = {version:NonNullable<RankingCandidateInputs['zero_sources']>[number];enabled:boolean;duration:number;source:string}
function PreparationForm({runId,branchId,latest,inputs,target,onDone}: {runId:string;branchId:string;latest?:RankingCandidateDetail;inputs?:RankingCandidateInputs;target:CandidateWeek;onDone:()=>void}): JSX.Element {
  const language = useRankingWorkflowLanguage()
  const t = (value: string) => rankingWorkflowText(value, language)
  const [corrections,setCorrections] = useState<RankingResultCorrection[]>([])
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
    return latest ? {...common,context:{...context,completed_week:latest.snapshot.week},tournaments:[],...(corrections.length ? {corrections:structuredClone(corrections)} : {})} : {...common,...context}
  }
  return <div>
    <p>{t('Prepare')} {rankingWorkflowWeekLabel(target, language)} {t('using stored tournament results. Review the complete roster, policy and decisions for this boundary.')}</p>
    <p>{t('This creates an unpublished candidate. World time and Viewer selection stay at their saved state.')}</p>
    {latest && target.week === 1 && <p>{t('Season boundary: explicitly review the incoming season’s policy before calculating.')}</p>}
    <form onSubmit={event => {event.preventDefault();confirm.reset();preview.mutate(build())}}>
      <fieldset disabled={busy || Boolean(review)}>
        <legend>{t('Ranking inputs')}</legend>
        <label>{t('Policy reference')} <input required value={policyId} onChange={e => setPolicyId(e.target.value)} /></label>
        <label>{t('Best N')} <input required type="number" min="1" step="1" value={bestN} onChange={e => setBestN(Number(e.target.value))} /></label>
        <h3>{t('Roster')} ({players.length})</h3>
        {players.length === 0 && <p>{t('An empty roster produces no ranked players.')}</p>}
        {players.map((player,index) => <fieldset key={index}>
          <legend>{t('Player')} {index+1}</legend>
          <label>{t('Player ID')} <input required value={player.player_id} onChange={e => updatePlayer(index,{player_id:e.target.value})} /></label>
          <label>{t('Stable tie-break token')} <input required value={player.tie_break_token} onChange={e => updatePlayer(index,{tie_break_token:e.target.value})} /></label>
          <label>{t('Tour entry season (1–50)')} <input required type="number" min="1" max="50" value={player.tour_entry_week.season_index+1} onChange={e => updatePlayer(index,{tour_entry_week:{...player.tour_entry_week,season_index:Number(e.target.value)-1}})} /></label>
          <label>{t('Tour entry week')} <input required type="number" min="1" max="61" value={player.tour_entry_week.week} onChange={e => updatePlayer(index,{tour_entry_week:{...player.tour_entry_week,week:Number(e.target.value)}})} /></label>
          <label className="checkbox-label"><input type="checkbox" checked={player.retired} onChange={e => updatePlayer(index,{retired:e.target.checked})} />{t('Retired at target week')}</label>
          <button type="button" onClick={() => setPlayers(old => old.filter((_,i) => i !== index))}>{t('Remove player')} {index+1}</button>
        </fieldset>)}
        <button type="button" onClick={() => setPlayers(old => [...old,{player_id:'',tie_break_token:crypto.randomUUID(),tour_entry_week:{...target},retired:false}])}>{t('Add player')}</button>
        {latest && <RankingResultCorrections runId={runId} branchId={branchId} latest={latest} target={target} onChange={setCorrections} />}
        <h3>{t('Disciplinary zeros')}</h3>
        <p>{t('New decisions apply at')} {rankingWorkflowWeekLabel(target, language)}. {t('Duration changes preserve each zero’s original start. Durations are explicit reviewed decisions.')}</p>
        {changes.map((change,index) => <fieldset key={change.version.fingerprint}>
          <legend>{change.version.version.zero.player_id} · {change.version.version.zero.zero_id}</legend>
          <p>{t('Original start')} {rankingWorkflowWeekLabel(change.version.version.zero.effective_week, language)} · {t('Duration')} {change.version.version.zero.duration_weeks} {t('weeks')}</p>
          <label className="checkbox-label"><input type="checkbox" checked={change.enabled} onChange={e => setChanges(old => old.map((c,i) => i === index ? {...c,enabled:e.target.checked} : c))} />{t('Change this duration')}</label>
          {change.enabled && <>
            <label>{t('New duration in weeks')} <input required type="number" min="1" value={change.duration} onChange={e => setChanges(old => old.map((c,i) => i === index ? {...c,duration:Number(e.target.value)} : c))} /></label>
            <label>{t('Correction reference')} <input required value={change.source} onChange={e => setChanges(old => old.map((c,i) => i === index ? {...c,source:e.target.value} : c))} /></label>
          </>}
        </fieldset>)}
        {newZeros.map((zero,index) => <fieldset key={zero.zero_id}>
          <legend>{t('New zero')} {index+1}</legend>
          <label>{t('Zero player')} <select required value={zero.player_id} onChange={e => setNewZeros(old => old.map((z,i) => i === index ? {...z,player_id:e.target.value} : z))}><option value="">{t('Select player')}</option>{players.filter(p => p.player_id).map((p,i) => <option key={i} value={p.player_id}>{p.player_id}</option>)}</select></label>
          <label>{t('Duration in weeks')} <input required type="number" min="1" value={zero.duration_weeks || ''} onChange={e => setNewZeros(old => old.map((z,i) => i === index ? {...z,duration_weeks:Number(e.target.value)} : z))} /></label>
          <label>{t('Decision reference')} <input required value={zero.source_fingerprint} onChange={e => setNewZeros(old => old.map((z,i) => i === index ? {...z,source_fingerprint:e.target.value} : z))} /></label>
          <button type="button" onClick={() => setNewZeros(old => old.filter((_,i) => i !== index))}>{t('Remove zero')} {index+1}</button>
        </fieldset>)}
        <button type="button" onClick={() => setNewZeros(old => [...old,{zero_id:`zero-${crypto.randomUUID()}`,run_id:runId,branch_id:branchId,player_id:'',effective_week:{...target},duration_weeks:0,source_fingerprint:''}])}>{t('Add disciplinary zero')}</button>
        <h3>{t('Preparation audit')}</h3>
        <label>{t('Operator label')} <input required maxLength={128} value={operator} onChange={e => setOperator(e.target.value)} /></label>
        <label>{t('Reason')} <textarea required maxLength={2000} value={reason} onChange={e => setReason(e.target.value)} /></label>
        <label className="checkbox-label"><input required type="checkbox" checked={reviewed} onChange={e => setReviewed(e.target.checked)} />{t('I reviewed the roster, target policy and decisions for this week.')}</label>
        <button type="submit" disabled={!reviewed}>{t('Calculate preview')}</button>
      </fieldset>
    </form>
    {preview.isPending && <p role="status">{t('Calculating preview…')}</p>}
    {preview.isError && <p role="alert">{t('Unable to calculate ranking preview.')} {t(formatApiError(preview.error))}</p>}
    {review && <section aria-label={t('Ranking preview')}>
      <h3>{t('Review')} {rankingWorkflowWeekLabel(review.preview.candidate.snapshot.week, language)}</h3>
      <p>{t('Preview only')} · {t('Best')} {review.preview.candidate.snapshot.policy.best_n} · {review.preview.candidate.snapshot.rows.length} {t('ranked players')} · {review.command.zero_versions.length} {t('zero changes')} · {'context' in review.command ? review.command.corrections?.length ?? 0 : 0} {t('result corrections')}</p>
      {review.preview.candidate.snapshot.rows.length === 0 ? <p>{t('No players are classified at this boundary.')}</p> : <div className="table-scroll"><table><thead><tr><th>{t('Rank')}</th><th>{t('Player')}</th><th>{t('Points')}</th><th>{t('Active zeros')}</th></tr></thead><tbody>{review.preview.candidate.snapshot.rows.map(row => <tr key={row.player_id}><td>{row.rank}</td><td>{row.player_id}</td><td>{row.points}</td><td>{row.disciplinary_zeros?.length ?? 0}</td></tr>)}</tbody></table></div>}
      <button type="button" disabled={busy} onClick={() => confirm.mutate()}>{t(confirm.isError ? 'Retry this exact preparation' : 'Confirm candidate preparation')}</button>
      <button type="button" disabled={busy} onClick={() => {setReview(null);preview.reset();confirm.reset();setReviewed(false)}}>{t('Edit inputs and recalculate')}</button>
      {confirm.isPending && <p role="status">{t('Preparing candidate…')}</p>}
      {confirm.isError && <p role="alert">{t('Unable to confirm candidate preparation.')} {t(formatApiError(confirm.error))} {t('The request is retained for an exact retry. If inputs changed, edit and recalculate.')}</p>}
    </section>}
  </div>
}
