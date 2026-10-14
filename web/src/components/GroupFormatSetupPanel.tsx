/** Actual production Admin operations required before a group-format Run is simulatable. */
import {useEffect,useState} from 'react'
import {useMutation,useQuery,useQueryClient} from '@tanstack/react-query'
import {
  getAdminGroupRules,adoptAdminGroupRules,configureAdminPureGroups,
  generateAdminGroupTopology,configureAdminHybridGroups,
} from '../api/client'
import {proposedPureGroups,proposedHybridGroups} from '../api/tournamentGroupFormats'
import type {HybridCrossingChoice} from '../api/tournamentGroupFormats'
import {formatApiError} from '../utils/apiErrors'
import {useLanguage} from '../i18n/LanguageContext'

type Props={
  runId:string;branchId:string;eventId:string
  seasonIndex:number|null
  entrantCount:number
  hasQualification:boolean
  hasByes:boolean
  step:'format'|'topology';kind?:'groups'|'groups_knockout'
}
export function GroupFormatSetupPanel({
  runId,branchId,eventId,seasonIndex,entrantCount,hasQualification,hasByes,step,kind='groups',
}:Props):JSX.Element{
  const client=useQueryClient()
  const {language}=useLanguage(),cs=language==='cs'
  const hybrid=kind==='groups_knockout'
  const [groupCount,setGroupCount]=useState(hybrid&&entrantCount>=4&&entrantCount%2===0?'2':'1')
  const [groupSize,setGroupSize]=useState(String(entrantCount?entrantCount/Number(groupCount):''))
  const [advancers,setAdvancers]=useState('1')
  const [crossings,setCrossings]=useState<HybridCrossingChoice[]>([])
  useEffect(()=>{
    setGroupCount(hybrid&&entrantCount>=4&&entrantCount%2===0?'2':'1')
    setGroupSize(String(entrantCount?(hybrid&&entrantCount>=4&&entrantCount%2===0?
      entrantCount/2:entrantCount):''))
    setAdvancers('1');setCrossings([])
    setConfirmFormat(null)
  },[entrantCount,runId,branchId,eventId,kind])
  const [bestOf,setBestOf]=useState<3|5>(5)
  // Approval belongs to an exact input/context snapshot, not to the component's lifetime.
  const [confirmRules,setConfirmRules]=useState<string|null>(null)
  const [confirmFormat,setConfirmFormat]=useState<string|null>(null)
  const [confirmTopology,setConfirmTopology]=useState<string|null>(null)
  const [topologySeed,setTopologySeed]=useState('137')
  const validTopologySeed=/^(0|[1-9][0-9]*)$/.test(topologySeed)
    &&Number.isSafeInteger(Number(topologySeed))&&Number(topologySeed)<=2147483647
  const seasonValid=seasonIndex!==null&&Number.isInteger(seasonIndex)
    &&seasonIndex>=0&&seasonIndex<=49
  const enabled=Boolean(runId&&branchId&&eventId&&seasonValid)
  const rules=useQuery({
    queryKey:['admin-group-rules',runId,branchId,seasonIndex],
    queryFn:()=>getAdminGroupRules(runId,branchId,seasonIndex!),
    enabled,retry:false
  })
  const scope=JSON.stringify([runId,branchId,eventId,seasonIndex,entrantCount,
    hasQualification,hasByes,step,kind])
  useEffect(()=>{setConfirmRules(null);setConfirmFormat(null);setConfirmTopology(null)},[scope])
  const rulesScope=JSON.stringify([scope,bestOf])
  const formatScope=JSON.stringify([scope,groupCount,groupSize,advancers,crossings,
    rules.data?.effective?.authority_fingerprint??null])
  const topologyScope=JSON.stringify([scope,topologySeed,
    rules.data?.effective?.authority_fingerprint??null])
  const invalidate=()=>client.invalidateQueries({
    queryKey:['canonical-tournament-preparation',runId,branchId,eventId],
  })
  const rulesMutation=useMutation({
    mutationFn:(v:{runId:string;branchId:string;seasonIndex:number;bestOf:3|5})=>
      adoptAdminGroupRules(v.runId,v.branchId,v.seasonIndex,v.bestOf,
        ('admin-ui-group-rules-'+v.branchId+'-'+v.seasonIndex+'-bo'+v.bestOf).slice(0,128)),
    onSuccess:async()=>{setConfirmRules(null);await rules.refetch();await invalidate()}
  })
  const formatMutation=useMutation({
    mutationFn:()=>hybrid?
      configureAdminHybridGroups(runId,branchId,eventId,
        proposedHybridGroups(groupCount,groupSize,advancers,entrantCount,crossings,
          ('admin-ui-hybrid-'+eventId).slice(0,128))):
      configureAdminPureGroups(runId,branchId,eventId,
        proposedPureGroups(groupCount,groupSize,entrantCount,
          ('admin-ui-pure-groups-'+eventId).slice(0,128))),
    onSuccess:async()=>{setConfirmFormat(null);await invalidate()}
  })
  const topologyMutation=useMutation({
    mutationFn:(v:{runId:string;branchId:string;eventId:string;seed:number})=>
      generateAdminGroupTopology(v.runId,v.branchId,v.eventId,
        ('admin-ui-group-topology-'+v.eventId).slice(0,128),v.seed,kind),
    onSuccess:async()=>{setConfirmTopology(null);await invalidate()}
  })
  const advancingCount=Number(groupCount)*Number(advancers)
  const firstRoundCount=Number.isInteger(advancingCount)&&advancingCount>=2
    &&advancingCount<=128&&(advancingCount&(advancingCount-1))===0
    ?advancingCount/2:0
  const choices=firstRoundCount&&firstRoundCount<=64?Array.from({length:firstRoundCount},
    (_,i)=>crossings[i]??{top:'',bottom:''}):[]
  const positions=Number.isInteger(Number(groupCount))&&Number.isInteger(Number(advancers))
    &&Number(groupCount)>=1&&Number(groupCount)<=64
    &&Number(advancers)>=1&&Number(advancers)<=128
    ?Array.from({length:Number(groupCount)},(_,g)=>Array.from(
      {length:Number(advancers)},(_,p)=>`${g+1}:${p+1}`)).flat():[]
  const revise=(index:number,side:'top'|'bottom',value:string)=>{
    const updated=choices.map(v=>({...v}));updated[index][side]=value
    setCrossings(updated);setConfirmFormat(null)
  }
  let validation:string|null=null
  try{
    if(hybrid)proposedHybridGroups(groupCount,groupSize,advancers,entrantCount,
      choices,'validation-only')
    else proposedPureGroups(groupCount,groupSize,entrantCount,'validation-only')
  }catch(error){
    validation=error instanceof Error?error.message:'Invalid group configuration.'
  }
  const validationLabel=validation===null?null:cs?({
    'Use positive whole group counts and sizes.':'Zadej kladné celé počty skupin a hráčů.',
    'Group count × group size must equal the frozen direct entrants, with no BYEs.':
      'Počet skupin × hráči ve skupině se musí rovnat počtu potvrzených přímých účastníků, bez BYE.',
  } as Record<string,string>)[validation]??validation:validation
  const missing=hasQualification||hasByes
  const frozen=step==='topology'
  return <section aria-label={cs?'Nastavení formátu skupin':'Group Format setup'} className="panel">
    <h3>{frozen?(cs?'Vytvořit uloženou topologii skupin':'Generate frozen group Topology'):
    (hybrid?(cs?'Nastavit skupiny + vyřazovací pavouk':'Configure groups + knockout Format'):
      (cs?'Nastavit formát skupin každý s každým':'Configure round-robin group Format'))}</h3>
    <p>{cs?'Použij výhradně ověřené účastníky tohoto Runu a Branch. Každý krok ukládá sportovní autoritu. Bez automatického nasazení, hybridního křížení, vymyšlených kvalifikantů nebo živých dat místo historie.':
    'Use canonical entry players from this Run and Branch. Every operation freezes a sporting authority. Crossings are explicitly selected from completed group positions, never inferred from player IDs.'}</p>
    <p className="status">{cs?'Potvrzení přímí účastníci':'Frozen direct entrants'}: {entrantCount}
      {' · '}{cs?'Sezona':'Season'}: {seasonValid?seasonIndex!+1:(cs?'nedostupná':'unavailable')}
      {' · '}Run: <code>{runId}</code> · Branch: <code>{branchId}</code></p>
    {!seasonValid&&<p role="alert">{cs?'Nelze ověřit sezonu turnaje; skupinová pravidla nelze převzít.':
    'Cannot prove the event season; group rules cannot be adopted.'}</p>}
    {missing&&<p role="alert">{cs?'Čisté skupiny nesmějí obsahovat kvalifikaci, rezervovaná místa kvalifikantů ani BYE. Nejprve oprav pole účastníků.':
    'Pure groups require no Qualification, qualifier reservations or effective BYEs. Fix the Entry Field before configuring groups.'}</p>}
    {rules.error&&<p role="alert">{cs?'Načtení pravidel skupin selhalo: ':'Group Rules loading failed: '}{formatApiError(rules.error)}</p>}
    {rules.isPending&&enabled&&<p role="status">{cs?'Načítám platná skupinová pravidla…':'Loading effective season Group Rules…'}</p>}
    {rules.data?.effective?<p role="status">
      {cs?'Potvrzená skupinová pravidla sezony':'Frozen season group rules'}: BO{rules.data.effective.default_match_best_of},
      {cs?'platná od sezony':'effective from season'} {rules.data.effective.effective_from_season_index+1}.
      {cs?'Formát přebírá tato pravidla.':'The Format inherits this existing authority.'}
    </p>:step==='format'&&enabled&&!rules.isPending&&<div className="grid">
      <label>{cs?'Délka skupinových zápasů':'Season group-match format'}
        <select aria-label={cs?'Délka skupinových zápasů':'Season group-match format'} value={bestOf}
          disabled={rulesMutation.isPending} onChange={e=>{setBestOf(Number(e.target.value) as 3|5);setConfirmRules(null)}}>
          <option value={3}>BO3</option><option value={5}>BO5</option>
        </select>
      </label>
      <label><input type="checkbox" aria-label={cs?'Potvrdit neměnná skupinová pravidla sezony':'Confirm immutable season Group Rules'}
        checked={confirmRules===rulesScope} disabled={rulesMutation.isPending}
        onChange={e=>setConfirmRules(e.target.checked?rulesScope:null)}/>
        {cs?'Potvrdit neměnná skupinová pravidla sezony':'Confirm immutable season Group Rules'}</label>
      <button type="button" disabled={confirmRules!==rulesScope||!enabled||missing||rulesMutation.isPending}
        onClick={()=>{if(confirmRules===rulesScope&&enabled&&!missing&&!rulesMutation.isPending)
          rulesMutation.mutate({runId,branchId,seasonIndex:seasonIndex!,bestOf})}}>
        {cs?'Převzít skupinová pravidla sezony':'Adopt season Group Rules'}</button>
      {rulesMutation.error&&<p role="alert">{cs?'Převzetí pravidel selhalo: ':'Group Rules adoption failed: '}{formatApiError(rulesMutation.error)}</p>}
    </div>}
    {!frozen&&<div className="grid">
      <label>{cs?'Počet skupin':'Group count'}
        <input aria-label={cs?'Počet skupin':'Group count'} type="number" min="1" max="64" step="1"
          disabled={formatMutation.isPending} value={groupCount} onChange={e=>{setGroupCount(e.target.value);setCrossings([]);setConfirmFormat(null)}}/>
      </label>
      <label>{cs?'Hráčů ve skupině':'Players per group'}
        <input aria-label={cs?'Hráčů ve skupině':'Players per group'} type="number" min="2" max="128" step="1"
          disabled={formatMutation.isPending} value={groupSize} onChange={e=>{setGroupSize(e.target.value);setCrossings([]);setConfirmFormat(null)}}/>
      </label>
      <p>{cs?'Pouze skupiny každý s každým. Počet skupin × hráčů ve skupině musí odpovídat potvrzeným přímým účastníkům. Nasazování a hybridní pavouk vyžadují samostatné schválené ovládání.':
        hybrid?'Every qualifying group position must be explicitly paired once. No inferred seeding, winners, or automatic crossing.':
        'Pure round-robin only. Group count × players per group must match frozen direct entrants. Explicitly seeded groups require separate setup.'}</p>
      {hybrid&&<>
        <label>{cs?'Postupujících z každé skupiny':'Advancers per group'}
          <input aria-label={cs?'Postupujících z každé skupiny':'Advancers per group'}
            type="number" min="1" max="128" step="1"
            disabled={formatMutation.isPending} value={advancers}
            onChange={e=>{setAdvancers(e.target.value);setCrossings([]);setConfirmFormat(null)}}/>
        </label>
        {choices.length>0&&<section aria-label="Explicit hybrid knockout crossings">
          <h4>{cs?'První kolo pavouka':'First knockout round'} · {choices.length} {cs?'zápasů':'matches'}</h4>
          {choices.map((choice,i)=><div className="actions" key={i}>
            <strong>{cs?'Zápas':'Match'} {i+1}</strong>
            {(['top','bottom'] as const).map(side=><label key={side}>
              {side==='top'?(cs?'Horní pozice':'Top source'):(cs?'Dolní pozice':'Bottom source')}
              <select aria-label={`Hybrid match ${i+1} ${side} source`}
                value={choice[side]} disabled={formatMutation.isPending}
                onChange={e=>revise(i,side,e.target.value)}>
                <option value="">{cs?'Vyber skupinu / místo':'Select group / position'}</option>
                {positions.map(v=><option key={v} value={v}>
                  {cs?'Skupina':'Group'} {v.split(':')[0]} · #{v.split(':')[1]}</option>)}
              </select>
            </label>)}
          </div>)}
        </section>}
      </>}
      {validationLabel&&<p role="alert">{validationLabel}</p>}
      <label><input type="checkbox" checked={confirmFormat===formatScope}
        aria-label={hybrid?(cs?'Potvrdit skupiny a úplné křížení':'Confirm exact hybrid Format and crossings'):
          (cs?'Potvrdit neměnný formát čistých skupin':'Confirm immutable pure-groups Format')}
        disabled={formatMutation.isPending}
        onChange={e=>setConfirmFormat(e.target.checked?formatScope:null)}/>
        {hybrid?(cs?'Potvrdit skupiny a úplné křížení':'Confirm exact hybrid Format and crossings'):
        (cs?'Potvrdit neměnný formát čistých skupin':'Confirm immutable pure-groups Format')}
      </label>
      <button type="button"
        disabled={!enabled||missing||validation!==null||!rules.data?.effective
          ||confirmFormat!==formatScope||formatMutation.isPending}
        onClick={()=>{if(confirmFormat===formatScope&&enabled&&!missing
          &&validation===null&&rules.data?.effective&&!formatMutation.isPending)
          formatMutation.mutate()}}>
        {hybrid?(cs?'Potvrdit skupiny + pavouk':'Configure groups + knockout Format'):
          (cs?'Nastavit čisté skupiny':'Configure pure-groups Format')}</button>
      {formatMutation.error&&<p role="alert">{cs?'Nastavení skupin selhalo: ':'Group Format configuration failed: '}{formatApiError(formatMutation.error)}</p>}
    </div>}
    {frozen&&<div className="grid">
      <p>{cs?'Formát je potvrzen. Vygeneruj autoritativní přiřazení účastníků a úplný rozpis skupin bez vymyšleného nasazení.':
        'Format is frozen. Generate the authoritative participant assignment and complete round-robin topology without inventing group placements.'}</p>
      <label>{cs?'Seed topologie skupin':'Group Topology seed'}
        <input aria-label={cs?'Seed topologie skupin':'Group Topology seed'} type="number" min="0" max="2147483647"
          step="1" disabled={topologyMutation.isPending} value={topologySeed}
          onChange={e=>{setTopologySeed(e.target.value);setConfirmTopology(null)}}/>
      </label>
      {!validTopologySeed&&<p role="alert">{cs?'Seed topologie musí být celé číslo od 0 do 2147483647.':
        'Topology seed must be a whole number from 0 to 2147483647.'}</p>}
      <label><input type="checkbox" checked={confirmTopology===topologyScope}
        aria-label={cs?'Potvrdit neměnnou topologii skupin':'Confirm immutable group Topology'}
        disabled={topologyMutation.isPending}
        onChange={e=>setConfirmTopology(e.target.checked?topologyScope:null)}/>
        {cs?'Potvrdit neměnnou topologii skupin':'Confirm immutable group Topology'}</label>
      <button type="button"
        disabled={!enabled||confirmTopology!==topologyScope||!validTopologySeed||topologyMutation.isPending}
        onClick={()=>{if(confirmTopology===topologyScope&&enabled&&validTopologySeed&&!topologyMutation.isPending)
          topologyMutation.mutate({runId,branchId,eventId,seed:Number(topologySeed)})}}>
        {cs?'Vygenerovat topologii skupin':'Generate group Topology'}</button>
      {topologyMutation.error&&<p role="alert">{cs?'Generování topologie selhalo: ':'Group Topology generation failed: '}{formatApiError(topologyMutation.error)}</p>}
    </div>}
  </section>
}
