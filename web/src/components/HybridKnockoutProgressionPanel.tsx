import {useMutation,useQuery,useQueryClient} from '@tanstack/react-query'
import {useEffect,useState} from 'react'
import {Link} from 'react-router-dom'
import {
  generateAdminHybridKnockoutEntrants,generateAdminHybridKnockoutBracket,
  getAdminCompletedGroupStandings,getAdminHybridKnockoutEntrants,
  getAdminHybridKnockoutBracket,
} from '../api/client'
import {newCommandId} from '../admin/branchSimulation'
import {useLanguage} from '../i18n/LanguageContext'
import {formatApiError,isApiNotFound} from '../utils/apiErrors'
import {HybridRankingClosurePanel} from './HybridRankingClosurePanel'

type Props={runId:string;branchId:string;eventId:string;enabled:boolean}

/** Real, immutable post-group sporting progression. Does not simulate a winner. */
export function HybridKnockoutProgressionPanel({
  runId,branchId,eventId,enabled,
}:Props):JSX.Element{
  const {language}=useLanguage(),cs=language==='cs'
  const client=useQueryClient()
  const [reviewedEntrants,setReviewedEntrants]=useState<string|null>(null)
  const [reviewedBracket,setReviewedBracket]=useState<string|null>(null)
  const [entrantsCommand,setEntrantsCommand]=useState(()=>newCommandId())
  const [bracketCommand,setBracketCommand]=useState(()=>newCommandId())
  const valid=enabled&&Boolean(runId&&branchId&&eventId)
  const standingsKey=['admin-completed-group-standings',runId,branchId,eventId]
  const entrantsKey=['admin-hybrid-knockout-entrants',runId,branchId,eventId]
  const bracketKey=['admin-hybrid-knockout-bracket',runId,branchId,eventId]
  const standings=useQuery({
    queryKey:standingsKey,
    queryFn:()=>getAdminCompletedGroupStandings(runId,branchId,eventId),
    enabled:valid,retry:false,
  })
  const entrants=useQuery({
    queryKey:entrantsKey,
    queryFn:()=>getAdminHybridKnockoutEntrants(
      runId,branchId,eventId,standings.data!),
    enabled:valid&&Boolean(standings.data),retry:false,
  })
  const bracket=useQuery({
    queryKey:bracketKey,
    queryFn:()=>getAdminHybridKnockoutBracket(
      runId,branchId,eventId,entrants.data!),
    enabled:valid&&Boolean(entrants.data),retry:false,
  })
  const noStandings=isApiNotFound(standings.error)
  const noEntrants=isApiNotFound(entrants.error)
  const noBracket=isApiNotFound(bracket.error)
  const entrantsFingerprint=standings.data?.authority_fingerprint??null
  const bracketFingerprint=entrants.data?.authority_fingerprint??null
  const createEntrants=useMutation({
    mutationFn:()=>generateAdminHybridKnockoutEntrants(
      runId,branchId,eventId,standings.data!,entrantsCommand),
    onSuccess:async value=>{
      client.setQueryData(entrantsKey,value)
      setReviewedEntrants(null);setEntrantsCommand(newCommandId())
      await client.invalidateQueries({queryKey:bracketKey})
    },
  })
  const createBracket=useMutation({
    mutationFn:()=>generateAdminHybridKnockoutBracket(
      runId,branchId,eventId,entrants.data!,bracketCommand),
    onSuccess:value=>{
      client.setQueryData(bracketKey,value)
      setReviewedBracket(null);setBracketCommand(newCommandId())
    },
  })
  useEffect(()=>{
    setReviewedEntrants(null);setReviewedBracket(null)
    setEntrantsCommand(newCommandId());setBracketCommand(newCommandId())
  },[runId,branchId,eventId])

  return <section className="panel" aria-label={cs?'Postup skupiny do vyřazovacího pavouka':'Hybrid knockout progression'}>
    <h3>{cs?'Postup ze skupin do pavouka':'Groups → knockout progression'}</h3>
    <p>{cs?'Postupující vzniknou výhradně z potvrzených konečných tabulek skupin. Pavouk pak převezme přesné dříve schválené křížení a jeho další kola odkazují jen na budoucí vítěze.':
      'Entrants derive only from frozen completed group positions. The immutable bracket uses the reviewed crossing; later rounds refer to future winners, not predicted results.'}</p>
    {!valid&&<p role="status">{cs?'Pouze ověřený současný Run/Branch může vytvářet sportovní autoritu.':'Only a verified current Run/Branch can generate sporting authorities.'}</p>}
    {valid&&standings.isPending&&<p role="status">{cs?'Ověřuji konečné tabulky skupin…':'Checking frozen group tables…'}</p>}
    {noStandings&&<p role="status">{cs?'Nejprve odehraj všechny skupinové zápasy a potvrď konečné tabulky.':'Play all canonical group matches and freeze the final standings first.'}</p>}
    {standings.error&&!noStandings&&<p role="alert">{cs?'Konečné tabulky nelze ověřit: ':'Cannot verify frozen standings: '}{formatApiError(standings.error)}</p>}
    {standings.data&&<>
      <p>{cs?'Konečné pořadí skupin':'Source group standings'}: <code>{standings.data.authority_fingerprint}</code></p>
      {entrants.isPending&&<p role="status">{cs?'Ověřuji postupující…':'Checking canonical advancing players…'}</p>}
      {entrants.error&&!noEntrants&&<p role="alert">{cs?'Postupující nelze ověřit: ':'Cannot verify knockout entrants: '}{formatApiError(entrants.error)}</p>}
      {noEntrants&&!entrants.data&&<div className="grid">
        <p role="status">{cs?'Postupující ještě nejsou potvrzeni. Žádný odhad hráčů se nepoužije.':
          'No frozen advancers yet. Players will not be selected from current Ranking or guessed.'}</p>
        <label><input type="checkbox" checked={reviewedEntrants===entrantsFingerprint}
          disabled={!valid||createEntrants.isPending}
          aria-label={cs?'Potvrdit postupující z konečného pořadí':'Confirm entrants from exact final group standings'}
          onChange={e=>setReviewedEntrants(e.target.checked?entrantsFingerprint:null)}/>
          {cs?'Potvrdit postupující z konečného pořadí':'Confirm entrants from exact final group standings'}
        </label>
        <button type="button"
          disabled={!valid||reviewedEntrants!==entrantsFingerprint||createEntrants.isPending}
          onClick={()=>{if(valid&&reviewedEntrants===entrantsFingerprint)createEntrants.mutate()}}>
          {cs?'Potvrdit postupující do pavouka':'Generate frozen knockout entrants'}
        </button>
        {createEntrants.error&&<p role="alert">{formatApiError(createEntrants.error)}</p>}
      </div>}
      {entrants.data&&<>
        <p role="status">{cs?'Potvrzení postupující':'Frozen knockout entrants'}: <code>{entrants.data.authority_fingerprint}</code></p>
        <table aria-label={cs?'Schválení postupující':'Canonical advancing positions'}>
          <thead><tr><th>{cs?'Zápas':'Match'}</th><th>{cs?'Horní pozice':'Top group place'}</th>
            <th>{cs?'Hráč':'Player'}</th><th>{cs?'Dolní pozice':'Bottom group place'}</th><th>{cs?'Hráč':'Player'}</th></tr></thead>
          <tbody>{entrants.data.first_round_matches.map(m=><tr key={m.match_id}>
            <td>{m.match_index}</td>
            <td>{m.top_source.group_index}:{m.top_source.finishing_position}</td>
            <td><code>{m.top_player_id}</code></td>
            <td>{m.bottom_source.group_index}:{m.bottom_source.finishing_position}</td>
            <td><code>{m.bottom_player_id}</code></td>
          </tr>)}</tbody>
        </table>
        {bracket.isPending&&<p role="status">{cs?'Ověřuji pavouk…':'Checking frozen knockout bracket…'}</p>}
        {bracket.error&&!noBracket&&<p role="alert">{cs?'Pavouk nelze ověřit: ':'Cannot verify frozen knockout bracket: '}{formatApiError(bracket.error)}</p>}
        {noBracket&&!bracket.data&&<div className="grid">
          <p>{cs?'Vygeneruje se úplný strom zápasů bez automatického dosazování vítězů.':
            'Generate an exact first round and subsequent winner-feeder tree. No winner is simulated.'}</p>
          <label><input type="checkbox" checked={reviewedBracket===bracketFingerprint}
            disabled={!valid||createBracket.isPending}
            aria-label={cs?'Potvrdit pavouk z uložených postupujících':'Confirm bracket from exact frozen entrants'}
            onChange={e=>setReviewedBracket(e.target.checked?bracketFingerprint:null)}/>
            {cs?'Potvrdit pavouk z uložených postupujících':'Confirm bracket from exact frozen entrants'}
          </label>
          <button type="button"
            disabled={!valid||reviewedBracket!==bracketFingerprint||createBracket.isPending}
            onClick={()=>{if(valid&&reviewedBracket===bracketFingerprint)createBracket.mutate()}}>
            {cs?'Vygenerovat neměnný pavouk':'Generate frozen knockout bracket'}
          </button>
          {createBracket.error&&<p role="alert">{formatApiError(createBracket.error)}</p>}
        </div>}
        {bracket.data&&<>
          <p role="status">{cs?'Potvrzený pavouk':'Frozen knockout bracket'}:
            {' '}<code>{bracket.data.authority_fingerprint}</code></p>
          <p>{cs?'Počet postupujících':'Entrants'}: {bracket.data.entrant_count}
            {' · '}{cs?'Kol':'Rounds'}: {bracket.data.round_count}
            {' · '}{cs?'Finálový zápas':'Final match'}: <code>{bracket.data.terminal_match_id}</code></p>
          <table aria-label={cs?'Neměnný vyřazovací pavouk':'Canonical hybrid knockout bracket'}>
            <thead><tr><th>{cs?'Kolo':'Round'}</th><th>{cs?'Zápas':'Match'}</th><th>{cs?'První zdroj':'First source'}</th><th>{cs?'Druhý zdroj':'Second source'}</th></tr></thead>
            <tbody>{bracket.data.matches.map(m=><tr key={m.match_id}>
              <td>{m.round_number}</td><td><code>{m.match_id}</code></td>
              <td><code>{m.participant_sources[0]}</code></td>
              <td><code>{m.participant_sources[1]}</code></td>
            </tr>)}</tbody>
          </table>
          <p className="status">{cs?'Pavouk je připraven na skutečné vyřazovací zápasy v simulaci. Potvrď příští zápasový den, nikoli automatického vítěze. Po odehrání ulož revizi pomocí Simulation Save. Rankingové body ještě nejsou přiděleny.':
            'The frozen bracket is ready for real knockout Match Days. Review and simulate the next canonical Match Day; no winner is inferred. Save the completed matches via Simulation Save. Ranking points remain unawarded.'}</p>
          {valid&&<p><Link to={`/admin/runs/${encodeURIComponent(runId)}/simulate?branch=${encodeURIComponent(branchId)}`}>
            {cs?'Odehrát skutečný vyřazovací zápas v Simulaci':'Play the real knockout Match Day in Simulation'}
          </Link></p>}
          <HybridRankingClosurePanel
            runId={runId} branchId={branchId} eventId={eventId} enabled={valid}
            bracket={bracket.data} standings={standings.data}/>
        </>}
      </>}
    </>}
  </section>
}
