/** Actual production Admin operations required before a group-format Run is simulatable. */
import {useEffect,useState} from 'react'
import {useMutation,useQuery,useQueryClient} from '@tanstack/react-query'
import {
  getAdminGroupRules,adoptAdminGroupRules,configureAdminPureGroups,
  generateAdminGroupTopology,
} from '../api/client'
import {proposedPureGroups} from '../api/tournamentGroupFormats'
import {formatApiError} from '../utils/apiErrors'
import {useLanguage} from '../i18n/LanguageContext'

type Props={
  runId:string;branchId:string;eventId:string
  seasonIndex:number|null
  entrantCount:number
  hasQualification:boolean
  hasByes:boolean
  step:'format'|'topology'
}
export function GroupFormatSetupPanel({
  runId,branchId,eventId,seasonIndex,entrantCount,hasQualification,hasByes,step,
}:Props):JSX.Element{
  const client=useQueryClient()
  const {language}=useLanguage(),cs=language==='cs'
  const [groupCount,setGroupCount]=useState('1')
  const [groupSize,setGroupSize]=useState(String(entrantCount||''))
  useEffect(()=>{setGroupSize(entrantCount ? String(entrantCount) : '')},[entrantCount,runId,branchId,eventId])
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
    hasQualification,hasByes,step])
  useEffect(()=>{setConfirmRules(null);setConfirmFormat(null);setConfirmTopology(null)},[scope])
  const rulesScope=JSON.stringify([scope,bestOf])
  const formatScope=JSON.stringify([scope,groupCount,groupSize,
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
    mutationFn:(v:{runId:string;branchId:string;eventId:string;groupCount:string;
      groupSize:string;entrantCount:number})=>configureAdminPureGroups(
      v.runId,v.branchId,v.eventId,
      proposedPureGroups(v.groupCount,v.groupSize,v.entrantCount,
        ('admin-ui-pure-groups-'+v.eventId).slice(0,128))),
    onSuccess:async()=>{setConfirmFormat(null);await invalidate()}
  })
  const topologyMutation=useMutation({
    mutationFn:(v:{runId:string;branchId:string;eventId:string;seed:number})=>
      generateAdminGroupTopology(v.runId,v.branchId,v.eventId,
        ('admin-ui-group-topology-'+v.eventId).slice(0,128),v.seed),
    onSuccess:async()=>{setConfirmTopology(null);await invalidate()}
  })
  let validation:string|null=null
  try{proposedPureGroups(groupCount,groupSize,entrantCount,'validation-only')}catch(error){
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
    (cs?'Nastavit formát skupin každý s každým':'Configure round-robin group Format')}</h3>
    <p>{cs?'Použij výhradně ověřené účastníky tohoto Runu a Branch. Každý krok ukládá sportovní autoritu. Bez automatického nasazení, hybridního křížení, vymyšlených kvalifikantů nebo živých dat místo historie.':
    'Use canonical entry players from this Run and Branch. Every operation freezes a sporting authority. No automatic seed placements, hybrid crossings, invented qualifying positions or unsaved historical data.'}</p>
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
          disabled={formatMutation.isPending} value={groupCount} onChange={e=>{setGroupCount(e.target.value);setConfirmFormat(null)}}/>
      </label>
      <label>{cs?'Hráčů ve skupině':'Players per group'}
        <input aria-label={cs?'Hráčů ve skupině':'Players per group'} type="number" min="2" max="128" step="1"
          disabled={formatMutation.isPending} value={groupSize} onChange={e=>{setGroupSize(e.target.value);setConfirmFormat(null)}}/>
      </label>
      <p>{cs?'Pouze skupiny každý s každým. Počet skupin × hráčů ve skupině musí odpovídat potvrzeným přímým účastníkům. Nasazování a hybridní pavouk vyžadují samostatné schválené ovládání.':
        'Pure round-robin only. Group count × players per group must match frozen direct entrants. Explicitly seeded groups and hybrid knockout require a separate approved crossing/placement UI.'}</p>
      {validationLabel&&<p role="alert">{validationLabel}</p>}
      <label><input type="checkbox" checked={confirmFormat===formatScope}
        aria-label={cs?'Potvrdit neměnný formát čistých skupin':'Confirm immutable pure-groups Format'}
        disabled={formatMutation.isPending}
        onChange={e=>setConfirmFormat(e.target.checked?formatScope:null)}/>
        {cs?'Potvrdit neměnný formát čistých skupin':'Confirm immutable pure-groups Format'}
      </label>
      <button type="button"
        disabled={!enabled||missing||validation!==null||!rules.data?.effective
          ||confirmFormat!==formatScope||formatMutation.isPending}
        onClick={()=>{if(confirmFormat===formatScope&&enabled&&!missing
          &&validation===null&&rules.data?.effective&&!formatMutation.isPending)
          formatMutation.mutate({runId,branchId,eventId,groupCount,groupSize,entrantCount})}}>
        {cs?'Nastavit čisté skupiny':'Configure pure-groups Format'}</button>
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
