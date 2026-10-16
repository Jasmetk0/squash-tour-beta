import {useMutation,useQuery,useQueryClient} from '@tanstack/react-query'
import {useEffect,useState} from 'react'
import {Link} from 'react-router-dom'
import {confirmRunCalendarPopulation,getBranchWorkingDraft,getRunCalendarPopulation,
  previewRunInitialWorldSave,reviewRunCalendarPopulation,saveRunOwnedInitialWorld} from '../api/client'
import {validateCalendarPopulation,validateCalendarPopulationReview,validateCalendarPopulationSave,
  type CalendarPopulationRequest,type CalendarPopulationReview} from '../api/calendarPopulation'
import type {CalendarPoolPreview} from '../api/calendarInitialPool'
import type {RunCalendarMetadata} from '../api/runCalendarCreation'
import {formatApiError} from '../utils/apiErrors'
import {acknowledgeSavedRunForm} from './RunNavigationSafeguard'

export function RunCalendarPopulationControls({runId,branchId,head,clock,packageFingerprint,pool,locale,onInstalled}: {
  runId:string;branchId:string;head:string;clock:RunCalendarMetadata;packageFingerprint:string|null
  pool:CalendarPoolPreview|null;locale:'cs'|'en';onInstalled:(value:boolean)=>void
}):JSX.Element {
  const cs=locale==='cs', client=useQueryClient()
  const [review,setReview]=useState<{request:CalendarPopulationRequest;value:CalendarPopulationReview}|null>(null)
  const [approved,setApproved]=useState(false),[saveApproved,setSaveApproved]=useState(false)
  const [error,setError]=useState('')
  const population=useQuery({queryKey:['calendar-initial-world',runId,branchId,head],retry:false,
    queryFn:async()=>{const p=await getRunCalendarPopulation(runId,branchId)
      return p===null?null:validateCalendarPopulation(p,runId,branchId,clock)}})
  const draftQuery=useQuery({queryKey:['package-working-draft',runId,branchId],
    queryFn:()=>getBranchWorkingDraft(runId,branchId),retry:false})
  const world=population.data
  const draft=draftQuery.data?.run_id===runId && draftQuery.data.branch_id===branchId?draftQuery.data:null
  useEffect(()=>onInstalled(Boolean(world)),[world,onInstalled])
  const signature=JSON.stringify([runId,branchId,head,packageFingerprint,pool?.preview_fingerprint,draft?.draft_version])
  useEffect(()=>{setReview(null);setApproved(false);setSaveApproved(false);setError('')},[signature])
  const saveProof=useQuery({queryKey:['calendar-population-save',runId,branchId,head,world?.fingerprint],
    queryFn:()=>previewRunInitialWorldSave(runId,branchId),enabled:Boolean(world),retry:false})
  async function refresh():Promise<void> {
    await Promise.all([
      client.invalidateQueries({queryKey:['calendar-initial-world',runId,branchId]}),
      client.invalidateQueries({queryKey:['calendar-population-save',runId,branchId]}),
      client.invalidateQueries({queryKey:['package-working-draft',runId,branchId]}),
      client.invalidateQueries({queryKey:['admin-run-branches',runId]}),
      client.invalidateQueries({queryKey:['run-branches',runId]})])
  }
  const reviewing=useMutation({
    retry:false,
    mutationFn:async()=>{
      if(!pool || !draft || !packageFingerprint)throw Error('Saved population source is unavailable')
      const payload:CalendarPopulationRequest={command_id:'calendar-population-'+crypto.randomUUID(),
        expected_saved_head:head,expected_draft_version:draft.draft_version,
        expected_package_fingerprint:packageFingerprint,generation:pool.request,
        audit_label:'Admin',audit_reason:'Reviewed generated initial population for this Run calendar'}
      const value=await reviewRunCalendarPopulation(runId,branchId,payload)
      return {request:payload,value:validateCalendarPopulationReview(value,payload,pool,runId,branchId,clock),signature}
    },
    onSuccess:r=>{if(r.signature===signature){setReview({request:r.value.request,value:r.value});setApproved(false);setError('')}},
    onError:e=>{setError(formatApiError(e));setApproved(false)}
  })
  const confirming=useMutation({
    retry:false,
    mutationFn:async(frozen:NonNullable<typeof review>)=>{
      const value=await confirmRunCalendarPopulation(runId,branchId,frozen.request,frozen.value.initial_world_fingerprint)
      const installed=validateCalendarPopulation(value,runId,branchId,clock)
      if(installed.fingerprint!==frozen.value.initial_world_fingerprint)throw Error('Confirmed population differs from review')
      return installed
    },
    onSuccess:async()=>{setApproved(false);setReview(null);setError('');await refresh()},
    onError:async e=>{setError(formatApiError(e));setApproved(false);await refresh()}
  })
  const saving=useMutation({
    retry:false,
    mutationFn:async()=>{
      if(!world || !proofMatches || !proof?.can_save || proof.draft_version!==draft?.draft_version)throw Error('Save proof changed')
      const receipt=await saveRunOwnedInitialWorld(runId,branchId,proof.draft_version,world.fingerprint)
      return validateCalendarPopulationSave(receipt,runId,branchId,world.fingerprint)
    },
    onSuccess:async()=>{acknowledgeSavedRunForm(runId,branchId);setSaveApproved(false);setError('');await refresh()},
    onError:async e=>{setSaveApproved(false);setError(formatApiError(e));await refresh()}
  })
  const busy=reviewing.isPending||confirming.isPending||saving.isPending
  const canReview=Boolean(pool && !world && population.isSuccess && !population.isFetching
    && draft?.status==='clean' && draft.base_saved_revision_id===head && packageFingerprint
    && pool.run_package_state_fingerprint===packageFingerprint && !busy)
  const reviewCurrent=Boolean(review && pool && review.value.pool_preview.preview_fingerprint===pool.preview_fingerprint
    && review.request.expected_saved_head===head && review.request.expected_draft_version===draft?.draft_version
    && review.request.expected_package_fingerprint===packageFingerprint && draft?.status==='clean')
  const proof=saveProof.data
  const proofMatches=Boolean(world && proof && !saveProof.isFetching && proof.run_id===runId && proof.branch_id===branchId
    && proof.saved_head_revision_id===head && proof.initial_world_fingerprint===world.fingerprint
    && proof.draft_version===draft?.draft_version && draft?.status==='clean')
  const saveReady=Boolean(proofMatches && proof?.can_save && !busy)
  return <section className="calendar-population-controls" data-run-navigation-readonly
    aria-label={cs?'Potvrzení a uložení populace':'Population confirmation and Save'}>
    {(population.error||draftQuery.error||saveProof.error) && <p role="alert">{formatApiError(population.error??draftQuery.error??saveProof.error)}</p>}
    {error && <p role="alert">{error}</p>}
    {world ? <>
      <h3>{cs?'Hráči přidaní do Runu':'Players added to this Run'}</h3>
      <p>{cs?'Počet hráčů':'Player count'}: {world.state.players.length} · {clock.weeks_per_year} {cs?'týdnů za rok':'weeks per year'}</p>
      <p>{cs?'Populace je připravená. Zápasy a posouvání času pro tento kalendář zatím nejsou dostupné.':
        'Population is prepared. Matches and time progression are not yet available for this calendar.'}</p>
      {proofMatches && proof?.has_unsaved_changes && <>
        <p role="status">{cs?'Hráči ještě nejsou součástí uložené revize. Vytvoř ji ručním Save.':
          'Players are not part of a Saved Revision yet. Create it with an explicit Save.'}</p>
        <label className="calendar-population-approval"><input type="checkbox" checked={saveApproved}
          onChange={e=>setSaveApproved(e.target.checked)} aria-label={cs?'Potvrdit uložení populace':'Confirm population Save'}/>
          {cs?'Chci uložit tuto populaci do nové revize.':'Save this population in a new revision.'}</label>
        <button disabled={!saveReady||!saveApproved} onClick={()=>saving.mutate()}>{cs?'Uložit hráče':'Save players'}</button>
      </>}
      {proofMatches && proof && !proof.has_unsaved_changes && <p role="status">{cs?'Populace je uložená.':'Population is saved.'}</p>}
      <p><Link to={'/admin/runs/'+encodeURIComponent(runId)+'/players'}>{cs?'Otevřít seznam hráčů':'Open player list'} →</Link></p>
    </> : <>
      {pool && <button disabled={!canReview} onClick={()=>{setReview(null);setApproved(false);reviewing.mutate()}}>
        {cs?'Zkontrolovat přidání hráčů':'Review adding players'}</button>}
      {pool && draft?.status!=='clean' && <p>{cs?'Nejdřív ulož změny zdrojových balíčků.':'Save source package changes first.'}</p>}
      {review && reviewCurrent && <>
        <h3>{cs?'Zkontroluj změnu populace':'Review population change'}</h3>
        <p>{cs?'Počet hráčů':'Player count'}: 0 → {review.value.player_count_after}</p>
        <p>{cs?'Narození a věk použijí kalendář tohoto Runu. Výsledky ani vstupy na Tour se tím nevytvářejí.':
          'Birthdays and ages use this Run calendar. This creates no results or Tour entry events.'}</p>
        <label className="calendar-population-approval"><input type="checkbox" checked={approved}
          onChange={e=>setApproved(e.target.checked)} aria-label={cs?'Potvrdit přidání populace':'Confirm population adoption'}/>
          {cs?'Zkontroloval jsem hráče a chci je přidat.':'I reviewed these players and want to add them.'}</label>
        <button disabled={!reviewCurrent||!approved||busy} onClick={()=>review&&confirming.mutate(review)}>
          {cs?'Přidat hráče do Runu':'Add players to Run'}</button>
      </>}
    </>}
  </section>
}
