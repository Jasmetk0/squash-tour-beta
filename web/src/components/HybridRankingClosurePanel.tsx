import {useEffect,useState} from 'react'
import {useMutation,useQuery,useQueryClient} from '@tanstack/react-query'
import {
  getAdminHybridRankingPolicy,configureAdminHybridRankingPolicy,
  getAdminHybridRankingClosure,closeAdminHybridRanking,
  getAuthoritativeMatchReplayContext,
} from '../api/client'
import type {HybridKnockoutBracket} from '../api/tournamentHybridKnockout'
import type {CompletedGroupStandings} from '../api/tournamentGroupStandings'
import {reviewedHybridRankingPayload,requiredHybridStages} from '../api/tournamentHybridRanking'
import {newCommandId} from '../admin/branchSimulation'
import {useLanguage} from '../i18n/LanguageContext'
import {formatApiError,isApiNotFound} from '../utils/apiErrors'

type Props={
  runId:string;branchId:string;eventId:string;enabled:boolean
  bracket:HybridKnockoutBracket;standings:CompletedGroupStandings
}
/** Explicit per-edition points, persisted source, never a guessed ranking award. */
export function HybridRankingClosurePanel({
  runId,branchId,eventId,enabled,bracket,standings,
}:Props):JSX.Element{
  const {language}=useLanguage(),cs=language==='cs'
  const client=useQueryClient()
  const scope=['hybrid-ranking',runId,branchId,eventId]
  const policyKey=[...scope,'policy'],closureKey=[...scope,'closure']
  const [groupPoints,setGroupPoints]=useState('')
  const [stagePoints,setStagePoints]=useState<Record<string,string>>({})
  const [reviewedPolicy,setReviewedPolicy]=useState<string|null>(null)
  const [reviewedClose,setReviewedClose]=useState<string|null>(null)
  const [policyCommand,setPolicyCommand]=useState(()=>newCommandId())
  const [closeCommand,setCloseCommand]=useState(()=>newCommandId())
  const valid=enabled&&Boolean(runId&&branchId&&eventId)
  const stages=requiredHybridStages(bracket)
  const policy=useQuery({
    queryKey:policyKey,
    queryFn:()=>getAdminHybridRankingPolicy(runId,branchId,eventId,bracket),
    enabled:valid,retry:false,
  })
  const closed=useQuery({
    queryKey:closureKey,
    queryFn:()=>getAdminHybridRankingClosure(runId,branchId,eventId),
    enabled:valid,retry:false,
  })
  const replay=useQuery({
    queryKey:[...scope,'terminal',bracket.terminal_match_id],
    queryFn:()=>getAuthoritativeMatchReplayContext(runId,branchId,bracket.terminal_match_id),
    enabled:valid&&!closed.data,retry:false,
  })
  const terminalVerified=Boolean(replay.data&&
    replay.data.match_id===bracket.terminal_match_id&&
    replay.data.event_id===eventId&&
    /^[0-9a-f]{64}$/.test(replay.data.result_fingerprint))
  const existingPolicyMissing=isApiNotFound(policy.error)
  const closureMissing=isApiNotFound(closed.error)
  let payloadError:string|null=null
  let proposal:ReturnType<typeof reviewedHybridRankingPayload>|null=null
  try{
    proposal=reviewedHybridRankingPayload(bracket,standings,groupPoints,stagePoints,policyCommand)
  }catch(e){payloadError=e instanceof Error?e.message:'Invalid ranking policy.'}
  const snapshot=JSON.stringify([bracket.authority_fingerprint,
    standings.authority_fingerprint,proposal])
  const configure=useMutation({
    mutationFn:()=>configureAdminHybridRankingPolicy(runId,branchId,eventId,bracket,proposal!),
    onSuccess:async result=>{
      client.setQueryData(policyKey,result)
      setReviewedPolicy(null);setPolicyCommand(newCommandId())
      await client.invalidateQueries({queryKey:closureKey})
    },
  })
  const close=useMutation({
    mutationFn:()=>closeAdminHybridRanking(runId,branchId,eventId,closeCommand),
    onSuccess:result=>{
      client.setQueryData(closureKey,result)
      setReviewedClose(null);setCloseCommand(newCommandId())
    },
  })
  useEffect(()=>{
    setReviewedPolicy(null);setReviewedClose(null)
    setGroupPoints('');setStagePoints({})
    setPolicyCommand(newCommandId());setCloseCommand(newCommandId())
  },[runId,branchId,eventId,bracket.authority_fingerprint])
  return <section className="panel" aria-label={cs?'Rankingové body hybridního turnaje':'Hybrid tournament ranking closure'}>
    <h3>{cs?'Rankingové body a uzavření turnaje':'Ranking points & tournament closure'}</h3>
    <p>{cs?'Hodnoty nejsou přednastavené. Rozhodni body za odehranou výhru ve skupině a za každé dosažené umístění v pavouku. Na hráče vznikne jediný souhrnný rankingový zdroj.':
      'No point amounts are assumed. Enter points for each played group win and for every knockout finish. A player receives one composed tournament ranking source.'}</p>
    {!valid&&<p role="status">{cs?'Historická nebo neověřená větev není zapisovatelná.':'Historical or unverified Branch cannot be modified.'}</p>}
    {valid&&closed.data&&<div>
      <p role="status">{cs?'Turnaj je oficiálně uzavřen':'Canonical tournament source is frozen'}</p>
      <dl><dt>{cs?'Výsledková autorita':'Result fingerprint'}</dt><dd><code>{closed.data.result_fingerprint}</code></dd>
        <dt>{cs?'Bodová autorita':'Points fingerprint'}</dt><dd><code>{closed.data.award_fingerprint}</code></dd>
        <dt>{cs?'Celkem přidělených bodů':'Total awarded points'}</dt><dd>{closed.data.total_ranking_points}</dd>
        <dt>{cs?'Autorita zdroje':'Owned ranking source'}</dt><dd><code>{closed.data.source_fingerprint}</code></dd></dl>
      <p>{cs?'Ulož revizi v Simulaci a otevři historickou Edition. Zápis Ranking publikace zůstává svázán s příslušným týdnem.':
        'Save a new Simulation Revision to preserve the completed Edition. Official publication follows the source\u2019s eligible Ranking week.'}</p>
    </div>}
    {valid&&closed.error&&!closureMissing&&<p role="alert">{formatApiError(closed.error)}</p>}
    {valid&&policy.error&&!existingPolicyMissing&&<p role="alert">{formatApiError(policy.error)}</p>}
    {valid&&!closed.data&&!policy.data&&existingPolicyMissing&&closureMissing&&
      <div>
        <p>{cs?'Konkrétní body schvaluje operátor, nikoli ranking hráčů nebo simulace.':
          'An operator must approve the actual points. Rankings or engine seeds cannot supply them.'}</p>
        <label>{cs?'Body za jednu odehranou výhru ve skupině':'Points per played group win'}
          <input aria-label="Played group win points" type="number" min="0" step="1"
            value={groupPoints} onChange={e=>{setGroupPoints(e.target.value);setReviewedPolicy(null)}}/>
        </label>
        {stages.map(stage=><label key={stage}>{stage}
          <input aria-label={`Hybrid points for ${stage}`} type="number" min="0" step="1"
            value={stagePoints[stage]??''} onChange={e=>{
              setStagePoints(previous=>({...previous,[stage]:e.target.value}))
              setReviewedPolicy(null)
            }}/>
        </label>)}
        {payloadError&&<p role="status">{payloadError}</p>}
        <label><input aria-label="Confirm exact hybrid ranking point values"
          type="checkbox" disabled={!proposal||configure.isPending}
          checked={reviewedPolicy===snapshot&&Boolean(proposal)}
          onChange={e=>setReviewedPolicy(e.target.checked?snapshot:null)}/>
          {cs?'Potvrdit přesné hodnoty všech rankingových bodů':'Confirm every explicit knockout and group points amount'}
        </label>
        <button type="button" disabled={!valid||!proposal||reviewedPolicy!==snapshot||configure.isPending}
          onClick={()=>configure.mutate()}>
          {cs?'Zmrazit rankingová pravidla turnaje':'Freeze hybrid ranking points policy'}
        </button>
        {configure.error&&<p role="alert">{formatApiError(configure.error)}</p>}
      </div>}
    {valid&&policy.data&&<div>
      <p role="status">{cs?'Bodování již nelze měnit':'Immutable ranking policy confirmed'}:
        {' '}<code>{policy.data.authority_fingerprint}</code></p>
      <p>{cs?'Výhra ve skupině':'Played group win'}: {policy.data.played_group_win_points}</p>
      <table aria-label="Frozen hybrid ranking phase points"><thead><tr>
        <th>{cs?'Umístění':'Stage'}</th><th>{cs?'Body':'Points'}</th></tr></thead>
        <tbody>{policy.data.knockout_stage_points.map(([stage,pts])=>
          <tr key={stage}><td>{stage}</td><td>{pts}</td></tr>)}</tbody>
      </table>
      {!closed.data&&closureMissing&&<>
        {!terminalVerified&&<p role="status">{cs?'Uzavření vyžaduje skutečně odehrané finále a ověřený záznam MatchEngine.':
          'Closing requires a real played knockout terminal match and verified MatchEngine replay.'}</p>}
        {replay.error&&!isApiNotFound(replay.error)&&<p role="status">{cs?'Finálový replay zatím nelze ověřit.':
          'Final match replay is not yet verifiable.'}</p>}
        <label><input type="checkbox"
          aria-label="Confirm close from real hybrid match results"
          disabled={!terminalVerified||close.isPending}
          checked={reviewedClose===policy.data.authority_fingerprint&&terminalVerified}
          onChange={e=>setReviewedClose(e.target.checked?policy.data!.authority_fingerprint:null)}/>
          {cs?'Potvrdit skutečné výsledky a zmrazené bodování':'Confirm frozen points and real knockout final'}
        </label>
        <button type="button"
          disabled={!terminalVerified||reviewedClose!==policy.data.authority_fingerprint||close.isPending}
          onClick={()=>close.mutate()}>
          {cs?'Uzavřít turnaj a přidělit rankingové body':'Close real hybrid tournament ranking source'}
        </button>
        {close.error&&<p role="alert">{formatApiError(close.error)}</p>}
      </>}
    </div>}
  </section>
}
