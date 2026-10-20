import {useEffect,useRef,useState} from 'react'
import {useQueryClient} from '@tanstack/react-query'
import {
  previewFutureNativeProspects, materializeFutureNativeProspects,
  type NativeFutureCohortRequest, type NativeFutureCohortPreview,
} from '../api/nativeFutureProspects'
import {previewRunProspectSourceSave,saveRunProspectSource} from '../api/client'
import type {RunProspectSourceSavePreview} from '../api/types'
import {useLanguage} from '../i18n/LanguageContext'
import {formatApiError} from '../utils/apiErrors'

/** Real Admin HTTP workflow; never admits a player, only the Tour transition does. */
export function NativeProspectSourceEpochPanel({
  runId,branchId,head,
}:{runId:string;branchId:string;head:string}){
  const cs=useLanguage().language==='cs', client=useQueryClient()
  const scope=JSON.stringify([runId,branchId,head])
  const current=useRef(scope),serial=useRef(0)
  if(current.current!==scope){current.current=scope;serial.current++}
  const [world,setWorld]=useState('official_fax_world')
  const [season,setSeason]=useState('1'),[target,setTarget]=useState('8')
  const [country,setCountry]=useState('')
  const [reason,setReason]=useState('')
  const [review,setReview]=useState<NativeFutureCohortPreview|null>(null)
  const [saveReview,setSaveReview]=useState<RunProspectSourceSavePreview|null>(null)
  const [materialized,setMaterialized]=useState(false)
  const [consent,setConsent]=useState(false),[saveConsent,setSaveConsent]=useState(false)
  const [busy,setBusy]=useState(false),[notice,setNotice]=useState<string|null>(null)
  const [error,setError]=useState<string|null>(null)
  useEffect(()=>{
    serial.current++;setReview(null);setSaveReview(null);setMaterialized(false)
    setConsent(false);setSaveConsent(false);setNotice(null);setError(null);setBusy(false)
    return ()=>{serial.current++}
  },[scope])
  const invalidate=()=>{
    serial.current++;setReview(null);setSaveReview(null);setConsent(false)
    setSaveConsent(false);setNotice(null);setError(null);setBusy(false)
  }
  const requestBody=():NativeFutureCohortRequest=>({
    schema_version:'native_calendar_cohort_request.v1',
    world_package_id:world.trim(),
    season_index:Number(season),
    base_annual_intake_target:Number(target),
    country_code:country.trim()?country.trim().toUpperCase():null,
  })
  const run=async(action:'review'|'materialize'|'reviewSave'|'save')=>{
    const stamp=++serial.current
    const valid=()=>serial.current===stamp&&current.current===scope
    setBusy(true);setError(null);setNotice(null)
    try{
      if(action==='review'){
        setReview(null);setSaveReview(null);setConsent(false)
        const data=await previewFutureNativeProspects(runId,branchId,requestBody())
        if(!valid())return
        if(data.saved_head_revision_id!==head)throw Error(cs?'Změnila se uložená revize. Načtěte aktuální větev.':'Saved HEAD changed. Reload the current Branch.')
        setReview(data)
      }else if(action==='materialize'){
        if(!review||!consent||review.saved_head_revision_id!==head||reason.trim().length<10)return
        const receipt=await materializeFutureNativeProspects(runId,branchId,review,'Admin prospect source epoch',reason.trim())
        if(!valid())return
        invalidate();setMaterialized(true)
        setNotice(cs?`Vytvořeno ${receipt.created_count} nových prospectů. Nyní je nutný samostatný Save zdroje.`:
          `Materialized ${receipt.created_count} new prospects. Separate manual source Save is required.`)
      }else if(action==='reviewSave'){
        setSaveReview(null);setSaveConsent(false)
        const preview=await previewRunProspectSourceSave(runId,branchId)
        if(!valid())return
        if(preview.saved_head_revision_id!==head)throw Error(cs?'Saved HEAD se změnil.':'Saved HEAD changed.')
        setSaveReview(preview)
      }else if(action==='save'){
        if(!saveReview||!saveReview.can_save||!saveConsent||
            saveReview.saved_head_revision_id!==head||!saveReview.run_prospect_source_fingerprint)return
        const receipt=await saveRunProspectSource(runId,branchId,{
          expected_draft_version:saveReview.draft_version,
          expected_run_prospect_source_fingerprint:saveReview.run_prospect_source_fingerprint,
          expected_saved_head_revision_id:head,
        })
        if(!valid())return
        if(!receipt.saved_revision?.revision_id||!receipt.saved_revision?.content_hash)
          throw Error('Saved prospect source has a foreign Run/Branch')
        invalidate();setMaterialized(false)
        setNotice(cs?'Nová verze prospect zdroje byla uložena; hráče přijme až Week/Season Transition.':
          'New prospect source epoch Saved. Only a later Week/Season Transition admits players.')
        void client.invalidateQueries()
      }
    }catch(e){if(valid())setError(formatApiError(e))}
    finally{if(valid())setBusy(false)}
  }
  const validNumbers=Number.isSafeInteger(Number(season))&&Number(season)>=0&&
    Number.isSafeInteger(Number(target))&&Number(target)>=1&&Number(target)<=2000
  const edit=(setter:(value:string)=>void,value:string)=>{invalidate();setter(value)}
  return <section className="panel" aria-label="Future prospect source epochs" data-saved-head={head}>
    <h3>{cs?'Další budoucí ročník prospectů':'Next future prospect cohort'}</h3>
    <p>{cs?
      'Připraví nový neměnný ročník ve sdíleném Run katalogu. Historické narození, zápasy a ostatní větve zůstanou na svém původním zdroji. Náhled nic neukládá; přijetí vykoná až potvrzený Week/Season Transition.':
      'Prepare an append-only future cohort in the shared Run catalog. Past births, matches and other Branches retain their original source. Preview never writes; only a confirmed Week/Season Transition admits players.'}</p>
    <div>
      <label>{cs?'ID uloženého World Package':'Saved World Package ID'}
        <input value={world} disabled={busy||materialized} onChange={e=>edit(setWorld,e.target.value)}/></label>
      <label>{cs?'Index budoucí sezóny (0 = první)':'Future season index (0 = first)'}
        <input type="number" min="0" value={season} disabled={busy||materialized} onChange={e=>edit(setSeason,e.target.value)}/></label>
      <label>{cs?'Roční základní počet':'Annual base target'}
        <input type="number" min="1" max="2000" value={target} disabled={busy||materialized} onChange={e=>edit(setTarget,e.target.value)}/></label>
      <label>{cs?'Země ISO3 (volitelné)':'ISO3 country (optional)'}
        <input maxLength={3} value={country} disabled={busy||materialized} onChange={e=>edit(setCountry,e.target.value)}/></label>
    </div>
    {!materialized&&<button disabled={busy||!world.trim()||!validNumbers} onClick={()=>void run('review')}>
      {cs?'1. Zkontrolovat budoucí kohortu':'1. Review future cohort'}</button>}
    {review?.saved_head_revision_id===head&&!materialized&&<div aria-label="Reviewed immutable prospect cohort">
      <p>{cs?'Ročník':'Season'}: {review.season_label} · {cs?'Nové profily':'New profiles'}: {review.prepared_profile_count}</p>
      <p>{cs?'Původní uložený zdroj':'Previous Saved source'}: <code>{review.previous_run_prospect_source_fingerprint?.slice(0,16)??'—'}</code></p>
      <p>{cs?'Nový obsah':'New content'}: <code>{review.record_content_fingerprint.slice(0,16)}</code></p>
      {review.first_prepared_prospects.map(p=><p key={p.prospect_id}>{p.prospect_id} · {p.country_code} · W{p.season_week}</p>)}
      {!review.materialization_supported&&<p role="alert">{review.materialization_blocker}</p>}
      <label>{cs?'Důvod potvrzení (alespoň 10 znaků)':'Confirmation reason (at least 10 characters)'}
        <textarea value={reason} disabled={busy} onChange={e=>{setReason(e.target.value);setConsent(false)}}/></label>
      <label><input type="checkbox" checked={consent} disabled={busy} onChange={e=>setConsent(e.target.checked)}/>
        {cs?'Výslovně potvrzuji vytvoření nových záznamů (bez přijetí hráčů).':
          'I explicitly confirm creating new records (without admitting players).'}</label>
      <button disabled={busy||!review.materialization_supported||!consent||reason.trim().length<10}
        onClick={()=>void run('materialize')}>{cs?'2. Vytvořit nové budoucí prospecty':'2. Materialize future prospects'}</button>
    </div>}
    {materialized&&<p>{cs?'Nové záznamy čekají na manuální Save.':'New records require manual source Save.'}</p>}
    {(materialized||saveReview)&&<button disabled={busy} onClick={()=>void run('reviewSave')}>
      {cs?'3. Zkontrolovat uložení nové verze':'3. Review source-epoch Save'}</button>}
    {saveReview&&saveReview.blockers?.length>0&&<p role="alert">{cs?
      'Uložení je nyní blokováno. Všechny dříve uložené záznamy musejí zůstat beze změny a nový ročník musí mít narozeniny až v budoucím týdnu všech větví.':
      'Source Save is blocked. Previously Signed records must stay unchanged and new cohort birthdays must occur after completed weeks on every Branch.'}</p>}
    {saveReview?.saved_head_revision_id===head&&<div aria-label="Reviewed prospect source Save">
      <p>{cs?'Celkem prospectů':'Total prospects'}: {saveReview.prospect_count} · {cs?'Neuložené změny':'Unsaved changes'}: {String(saveReview.has_unsaved_changes)}</p>
      <p>{cs?'Zdroj':'Source'}: <code>{saveReview.run_prospect_source_fingerprint?.slice(0,16)}</code> · HEAD <code>{head}</code></p>
      {saveReview.blockers?.map(blocker=><p role="alert" key={blocker}>{blocker}</p>)}
      <label><input type="checkbox" checked={saveConsent} disabled={busy||!saveReview.can_save}
        onChange={e=>setSaveConsent(e.target.checked)}/>
        {cs?'Výslovně potvrzuji oddělený manuální Save.':'I explicitly confirm the separate manual Save.'}</label>
      <button disabled={busy||!saveConsent||!saveReview.can_save} onClick={()=>void run('save')}>
        {cs?'4. Uložit neměnnou verzi':'4. Save immutable source epoch'}</button>
    </div>}
    {error&&<p role="alert">{error}</p>}
    {notice&&<p role="status">{notice}</p>}
  </section>
}
