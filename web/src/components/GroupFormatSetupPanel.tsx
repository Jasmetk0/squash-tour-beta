/** Actual production Admin operations required before a group-format Run is simulatable. */
import {useState} from 'react'
import {useMutation,useQuery,useQueryClient} from '@tanstack/react-query'
import {
  getAdminGroupRules,adoptAdminGroupRules,configureAdminPureGroups,
  generateAdminGroupTopology,
} from '../api/client'
import {proposedPureGroups} from '../api/tournamentGroupFormats'
import {formatApiError} from '../utils/apiErrors'

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
  const [groupCount,setGroupCount]=useState('1')
  const [groupSize,setGroupSize]=useState(String(entrantCount||''))
  const [bestOf,setBestOf]=useState<3|5>(5)
  const [confirmRules,setConfirmRules]=useState(false)
  const [confirmFormat,setConfirmFormat]=useState(false)
  const [confirmTopology,setConfirmTopology]=useState(false)
  const seasonValid=seasonIndex!==null&&Number.isInteger(seasonIndex)
    &&seasonIndex>=0&&seasonIndex<=49
  const enabled=Boolean(runId&&branchId&&eventId&&seasonValid)
  const rules=useQuery({
    queryKey:['admin-group-rules',runId,branchId,seasonIndex],
    queryFn:()=>getAdminGroupRules(runId,branchId,seasonIndex!),
    enabled,retry:false
  })
  const invalidate=()=>client.invalidateQueries({
    queryKey:['canonical-tournament-preparation',runId,branchId,eventId],
  })
  const rulesMutation=useMutation({
    mutationFn:()=>adoptAdminGroupRules(
      runId,branchId,seasonIndex!,bestOf,
      ('admin-ui-group-rules-'+branchId+'-'+seasonIndex+'-bo'+bestOf).slice(0,128),
    ),
    onSuccess:async()=>{setConfirmRules(false);await rules.refetch();await invalidate()}
  })
  const formatMutation=useMutation({
    mutationFn:()=>configureAdminPureGroups(
      runId,branchId,eventId,
      proposedPureGroups(groupCount,groupSize,entrantCount,
        ('admin-ui-pure-groups-'+eventId).slice(0,128)),
    ),
    onSuccess:async()=>{setConfirmFormat(false);await invalidate()}
  })
  const topologyMutation=useMutation({
    mutationFn:()=>generateAdminGroupTopology(
      runId,branchId,eventId,('admin-ui-group-topology-'+eventId).slice(0,128),
    ),
    onSuccess:async()=>{setConfirmTopology(false);await invalidate()}
  })
  let validation:string|null=null
  try{proposedPureGroups(groupCount,groupSize,entrantCount,'validation-only')}catch(error){
    validation=error instanceof Error?error.message:'Invalid group configuration.'
  }
  const missing=hasQualification||hasByes
  const frozen=step==='topology'
  return <section aria-label="Group Format setup" className="panel">
    <h3>{frozen?'Generate frozen group Topology':'Configure round-robin group Format'}</h3>
    <p>Use canonical entry players from this Run and Branch. Every operation freezes a
      sporting authority. No automatic seed placements, hybrid crossings, invented
      qualifying positions or unsaved historical data.</p>
    <p className="status">Frozen direct entrants: {entrantCount}
      {' · '}Season: {seasonValid?seasonIndex!+1:'unavailable'}
      {' · '}Run: <code>{runId}</code> · Branch: <code>{branchId}</code></p>
    {!seasonValid&&<p role="alert">Cannot prove the event season; group rules cannot be adopted.</p>}
    {missing&&<p role="alert">Pure groups require no Qualification, qualifier reservations or
      effective BYEs. Fix the Entry Field before configuring groups.</p>}
    {rules.error&&<p role="alert">{formatApiError(rules.error)}</p>}
    {rules.isPending&&enabled&&<p role="status">Loading effective season Group Rules…</p>}
    {rules.data?.effective?<p role="status">
      Frozen season group rules: BO{rules.data.effective.default_match_best_of},
      effective from season {rules.data.effective.effective_from_season_index+1}.
      The Format inherits this existing authority.
    </p>:step==='format'&&enabled&&!rules.isPending&&<div className="grid">
      <label>Season group-match format
        <select aria-label="Season group-match format" value={bestOf}
          onChange={e=>setBestOf(Number(e.target.value) as 3|5)}>
          <option value={3}>BO3</option><option value={5}>BO5</option>
        </select>
      </label>
      <label><input type="checkbox" checked={confirmRules}
        onChange={e=>setConfirmRules(e.target.checked)}/>
        Confirm immutable season Group Rules</label>
      <button type="button" disabled={!confirmRules||!enabled||missing||rulesMutation.isPending}
        onClick={()=>rulesMutation.mutate()}>Adopt season Group Rules</button>
      {rulesMutation.error&&<p role="alert">{formatApiError(rulesMutation.error)}</p>}
    </div>}
    {!frozen&&<div className="grid">
      <label>Group count
        <input aria-label="Group count" type="number" min="1" max="64" step="1"
          value={groupCount} onChange={e=>setGroupCount(e.target.value)}/>
      </label>
      <label>Players per group
        <input aria-label="Players per group" type="number" min="2" max="128" step="1"
          value={groupSize} onChange={e=>setGroupSize(e.target.value)}/>
      </label>
      <p>Pure round-robin only. Group count × players per group must match frozen
        direct entrants. Explicitly seeded groups and hybrid knockout
        require a separate approved crossing/placement UI.</p>
      {validation&&<p role="alert">{validation}</p>}
      <label><input type="checkbox" checked={confirmFormat}
        onChange={e=>setConfirmFormat(e.target.checked)}/>
        Confirm immutable pure-groups Format
      </label>
      <button type="button"
        disabled={!enabled||missing||validation!==null||!rules.data?.effective
          ||!confirmFormat||formatMutation.isPending}
        onClick={()=>formatMutation.mutate()}>Configure pure-groups Format</button>
      {formatMutation.error&&<p role="alert">{formatApiError(formatMutation.error)}</p>}
    </div>}
    {frozen&&<div className="grid">
      <p>Format is frozen. Generate the authoritative participant assignment and
        complete round-robin topology without inventing group placements.</p>
      <label><input type="checkbox" checked={confirmTopology}
        onChange={e=>setConfirmTopology(e.target.checked)}/>
        Confirm immutable group Topology</label>
      <button type="button" disabled={!enabled||!confirmTopology||topologyMutation.isPending}
        onClick={()=>topologyMutation.mutate()}>Generate group Topology</button>
      {topologyMutation.error&&<p role="alert">{formatApiError(topologyMutation.error)}</p>}
    </div>}
  </section>
}
