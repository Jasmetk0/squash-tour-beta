import { acknowledgeSavedRunForm } from './RunNavigationSafeguard'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import {
  adoptRunOwnedInitialWorld, getBranchWorkingDraft, getRunOwnedInitialWorld,
  getRunPackageState, getRunWorldGenerationOptions, previewRunInitialWorldSave, previewRunOwnedInitialWorld,
  saveRunOwnedInitialWorld
} from '../api/client'
import type { RunBranch, RunContainer } from '../api/types'
import {
  ageConditionConflict, generatorConditionConflict, runOwnedWorldIds, verifiedGenerationOptions, verifiedInitialWorldPreview,
  type RunInitialWorldAdoption, type RunInitialWorldPreview
} from '../api/runInitialWorldSetup'
import { formatApiError, isApiNotFound } from '../utils/apiErrors'
import { SectionCard } from './RunScopedUi'

type ReviewedWorld = {
  runId: string
  branchId: string
  head: string
  sourceFingerprint: string
  draftVersion: number
  request: RunInitialWorldAdoption
  preview: RunInitialWorldPreview
}

type PendingSave = { runId: string; branchId: string; head: string; fingerprint: string }

export function RunInitialWorldSetupPanel({ run, branch, locale = 'en' }: {
  run: RunContainer; branch: RunBranch | null; locale?: 'cs' | 'en'
}): JSX.Element {
  const cs = locale === 'cs'
  const queryClient = useQueryClient()
  const runId = run.run_id
  const branchId = branch?.run_id === runId ? branch.branch_id : ''
  const head = branch?.run_id === runId ? branch.saved_head_revision_id ?? '' : ''
  const editable = run.storage_kind === 'custom_local' && !run.read_only &&
    ['working', 'active', 'completed'].includes(run.status) &&
    Boolean(branchId && head && branch?.status === 'active' && !branch.read_only)
  const [sourceId, setSourceId] = useState('')
  const [seed, setSeed] = useState(20261009)
  const [poolSize, setPoolSize] = useState(64)
  const [countryCode, setCountryCode] = useState('')
  const [region, setRegion] = useState('')
  const [minAge, setMinAge] = useState('')
  const [maxAge, setMaxAge] = useState('')
  const [bestN, setBestN] = useState(15)
  const [auditReason, setAuditReason] = useState('Create the first-season player population from the reviewed Run-owned World snapshot.')
  const [review, setReview] = useState<ReviewedWorld | null>(null)
  const [approved, setApproved] = useState(false)
  const [pendingSave, setPendingSave] = useState<PendingSave | null>(null)
  const [saveApproved, setSaveApproved] = useState(false)
  const [notice, setNotice] = useState('')

  const packageQuery = useQuery({
    queryKey: ['run-package-state', runId, branchId],
    queryFn: () => getRunPackageState(runId, branchId),
    enabled: Boolean(branchId),
    retry: false
  })
  const draftQuery = useQuery({
    queryKey: ['package-working-draft', runId, branchId],
    queryFn: () => getBranchWorkingDraft(runId, branchId),
    enabled: Boolean(branchId),
    retry: false
  })
  const existingQuery = useQuery({
    queryKey: ['run-owned-initial-world', runId, branchId],
    queryFn: () => getRunOwnedInitialWorld(runId, branchId),
    enabled: Boolean(branchId),
    retry: false
  })
  const worldIds = runOwnedWorldIds(packageQuery.data?.state)
  const selectedWorldId = worldIds.includes(sourceId) ? sourceId : (worldIds[0] ?? '')
  const draft = draftQuery.data?.run_id === runId &&
    draftQuery.data.branch_id === branchId ? draftQuery.data : null
  const existing = existingQuery.data?.run_id === runId &&
    existingQuery.data.branch_id === branchId ? existingQuery.data : null
  const unexpectedExistingError = existingQuery.error && !isApiNotFound(existingQuery.error)
  const validParameters = Number.isSafeInteger(seed) && Number.isInteger(poolSize) &&
    poolSize >= 1 && poolSize <= 128 && Number.isInteger(bestN) && bestN >= 1 &&
    auditReason.trim().length >= 1 && auditReason.trim().length <= 1000
  const snapshotFingerprint = packageQuery.data?.fingerprint ?? null
  const optionsQuery = useQuery({
    queryKey: ['run-world-generation-options', runId, branchId, head, draft?.draft_version,
      snapshotFingerprint, selectedWorldId],
    queryFn: () => getRunWorldGenerationOptions(
      runId, branchId, selectedWorldId, head, draft!.draft_version, snapshotFingerprint!
    ),
    enabled: editable && Boolean(selectedWorldId && snapshotFingerprint && draft &&
      draft.status === 'clean' && draft.base_saved_revision_id === head && !existing),
    retry: false,
  })
  const options = optionsQuery.data && draft && snapshotFingerprint &&
    verifiedGenerationOptions(optionsQuery.data, runId, branchId, head,
      draft.draft_version, snapshotFingerprint, selectedWorldId)
    ? optionsQuery.data : null
  const conditionConflict = optionsQuery.isSuccess
    ? generatorConditionConflict(countryCode, region, options)
    : null
  const ageConflict = ageConditionConflict(minAge, maxAge)
  const canPreview = editable && worldIds.length > 0 && validParameters &&
    packageQuery.isSuccess && Boolean(options) && !conditionConflict && !ageConflict &&
    draft?.base_saved_revision_id === head &&
    draft.status === 'clean' && !existing && existingQuery.isSuccess === false &&
    isApiNotFound(existingQuery.error) && !pendingSave

  useEffect(() => {
    setReview(null)
    setPendingSave(null)
    setApproved(false)
    setSaveApproved(false)
    setNotice('')
  }, [runId, branchId, head, sourceId, seed, poolSize, countryCode, region, minAge, maxAge, bestN, auditReason])

  const previewAction = useMutation({
    mutationFn: async () => {
      if (!canPreview || !selectedWorldId || !draft || !snapshotFingerprint)
        throw new Error('Run World, clean Saved Revision and writable target must be verified.')
      const request: RunInitialWorldAdoption = {
        command_id: `admin-initial-world-${crypto.randomUUID()}`,
        generation: {
          world_package_id: selectedWorldId,
          season: '2000/2001',
          seed, target_pool_size: poolSize,
          ...(countryCode ? { country_code: countryCode } : {}),
          ...(region ? { region } : {}),
          ...(minAge ? { min_age: Number(minAge) } : {}),
          ...(maxAge ? { max_age: Number(maxAge) } : {})
        },
        audit_label: 'Run Admin first-season player setup',
        audit_reason: auditReason.trim(),
        official_run: false,
        best_n: bestN,
        automatic_retirement_age: 46
      }
      const preview = await previewRunOwnedInitialWorld(runId, branchId, request)
      if (!verifiedInitialWorldPreview(preview, runId, branchId, request, options))
        throw new Error('InitialWorld preview is inconsistent with the requested World, Run, Branch or policy.')
      return { runId, branchId, head, sourceFingerprint: snapshotFingerprint,
        draftVersion: draft.draft_version, request, preview }
    },
    onSuccess: value => { setReview(value); setApproved(false); setNotice('') }
  })
  const reviewMatches = Boolean(review && review.runId === runId &&
    review.branchId === branchId && review.head === head &&
    review.sourceFingerprint === snapshotFingerprint &&
    review.draftVersion === draft?.draft_version &&
    draft?.base_saved_revision_id === head && draft?.status === 'clean' &&
    review.request.generation.world_package_id === selectedWorldId &&
    review.request.generation.seed === seed && review.request.generation.target_pool_size === poolSize &&
    (review.request.generation.country_code ?? '') === countryCode &&
    (review.request.generation.region ?? '') === region &&
    String(review.request.generation.min_age ?? '') === minAge &&
    String(review.request.generation.max_age ?? '') === maxAge &&
    Boolean(options) && !conditionConflict && !ageConflict &&
    review.request.best_n === bestN && review.request.audit_reason === auditReason.trim() &&
    !existing && isApiNotFound(existingQuery.error))

  const adoptAction = useMutation({
    mutationFn: async (current: ReviewedWorld) => {
      const result = await adoptRunOwnedInitialWorld(
        current.runId, current.branchId, current.request, current.preview.fingerprint,
        { head: current.head, draftVersion: current.draftVersion,
          packageFingerprint: current.sourceFingerprint }
      )
      if (result.run_id !== current.runId || result.branch_id !== current.branchId ||
        result.adopted_by_command_id !== current.request.command_id ||
        result.world_package_id !== current.request.generation.world_package_id ||
        result.players.length !== current.preview.state.players.length ||
        result.adoption_request_fingerprint !== current.preview.state.adoption_request_fingerprint)
        throw new Error('Adoption response has unexpected ownership or source identity. Inspect stored state before saving.')
      return { current, result }
    },
    onSuccess: async ({ current }) => {
      setReview(null); setApproved(false)
      setPendingSave({ runId: current.runId, branchId: current.branchId,
        head: current.head, fingerprint: current.preview.fingerprint })
      setNotice('Players were adopted to Run-owned InitialWorld. A separate Saved Revision is still required.')
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['run-owned-initial-world', current.runId, current.branchId] }),
        queryClient.invalidateQueries({ queryKey: ['package-working-draft', current.runId, current.branchId] })
      ])
    },
    onError: () => {
      setReview(null); setApproved(false)
      setNotice('Adoption was not verified. Read the stored InitialWorld before trying again.')
      void queryClient.invalidateQueries({ queryKey: ['run-owned-initial-world', runId, branchId] })
    }
  })

  const savePreviewQuery = useQuery({
    queryKey: ['initial-world-save-preview', runId, branchId, pendingSave?.fingerprint],
    queryFn: () => previewRunInitialWorldSave(runId, branchId),
    enabled: Boolean(pendingSave || existing),
    retry: false
  })
  const savePreflight = savePreviewQuery.data
  const canResume = Boolean(!pendingSave && editable && existing && draft?.status === 'clean' &&
    draft.base_saved_revision_id === head && savePreflight &&
    /^[a-f0-9]{64}$/.test(savePreflight.initial_world_fingerprint) &&
    savePreflight.draft_version === draft.draft_version &&
    (savePreflight.run_id === undefined || savePreflight.run_id === runId) &&
    (savePreflight.branch_id === undefined || savePreflight.branch_id === branchId) &&
    (savePreflight.saved_head_revision_id === undefined || savePreflight.saved_head_revision_id === head) &&
    savePreflight.has_unsaved_changes === true && savePreflight.can_save === true)
  const saveReady = Boolean(pendingSave && pendingSave.runId === runId &&
    pendingSave.branchId === branchId && pendingSave.head === head &&
    existing && existing.adopted_by_command_id &&
    existing.world_package_id &&
    draft?.base_saved_revision_id === head && draft?.status === 'clean' &&
    savePreflight && savePreflight.initial_world_fingerprint === pendingSave.fingerprint &&
    savePreflight.draft_version === draft?.draft_version &&
    (savePreflight.run_id === undefined || savePreflight.run_id === runId) &&
    (savePreflight.branch_id === undefined || savePreflight.branch_id === branchId) &&
    (savePreflight.saved_head_revision_id === undefined || savePreflight.saved_head_revision_id === head) &&
    savePreflight.has_unsaved_changes === true && savePreflight.can_save === true)

  const saveAction = useMutation({
    mutationFn: async () => {
      if (!pendingSave || !savePreflight || !saveReady)
        throw new Error('InitialWorld Save preflight no longer matches the reviewed adoption.')
      const saved = await saveRunOwnedInitialWorld(
        runId, branchId, savePreflight.draft_version, pendingSave.fingerprint
      )
      if (!saved.saved_revision.revision_id ||
        saved.working_draft.run_id !== runId || saved.working_draft.branch_id !== branchId ||
        saved.working_draft.base_saved_revision_id !== saved.saved_revision.revision_id ||
        saved.working_draft.status !== 'clean')
        throw new Error('Saved Revision was not verified. Refresh Run-owned state.')
      return saved
    },
    onSuccess: async () => {
      setPendingSave(null); setSaveApproved(false)
      acknowledgeSavedRunForm(runId, branchId)
      setNotice('First-season InitialWorld is saved and recoverable. Next: derive the initial ranking.')
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['run-branches', runId] }),
        queryClient.invalidateQueries({ queryKey: ['admin-run-branches', runId] }),
        queryClient.invalidateQueries({ queryKey: ['saved-revision-history', runId, branchId] }),
        queryClient.invalidateQueries({ queryKey: ['run-owned-initial-world', runId, branchId] }),
        queryClient.invalidateQueries({ queryKey: ['package-working-draft', runId, branchId] })
      ])
    }
  })

  const canAdopt = reviewMatches && approved && !adoptAction.isPending && !previewAction.isPending
  const viewedPlayers = review?.preview.state.players ?? []
  const distribution = Object.entries(viewedPlayers.reduce<Record<string, number>>((result, player) => {
    result[player.country_code] = (result[player.country_code] ?? 0) + 1
    return result
  }, {})).sort((a, b) => b[1] - a[1]).slice(0, 8)

  return <SectionCard title={cs ? 'Generovat hráče — první úplná dávka' : 'Generate first-season players'}>
    <p className="status">{cs
      ? 'První funkční dávka 1–128 hráčů pro sezónu 2000/01. Používá pouze uložený World Package dané branche. Náhled nic nezapisuje; potvrzení připraví InitialWorld a teprve ruční Save vytváří Saved Revision.'
      : 'First supported complete batch (1–128 players) for season 2000/01. Uses the saved Run-owned World Package only. Preview never writes; confirmation stages InitialWorld, then manual Save creates a Saved Revision.'}</p>
    <p className="status">{cs
      ? 'Závazné podmínky země, regionu a věku platí pro všechny hráče dávky. Prázdná pole zachovávají automatické rozdělení. Skupiny, kvóty a individuální úpravy zatím nejsou podporované.'
      : 'Hard country, region and age conditions apply to every player. Blank conditions preserve automatic allocation. Groups, quotas and individual editing are not supported yet.'}</p>
    {existing && <p role="status">InitialWorld exists: {existing.players.length} players from {existing.world_package_id}; seed {existing.bootstrap_seed}. Existing players cannot be silently regenerated or overwritten.</p>}
    {unexpectedExistingError && <p role="alert" className="error">Cannot verify whether this Run already has InitialWorld: {formatApiError(existingQuery.error)}</p>}
    {packageQuery.isError && <p role="alert" className="error">Run World state unavailable: {formatApiError(packageQuery.error)}</p>}
    {draftQuery.isError && <p role="alert" className="error">Working Draft unavailable: {formatApiError(draftQuery.error)}</p>}
    {!existing && worldIds.length === 0 && <p>{cs
      ? 'Nejprve musíš zkopírovat World Package do Runu a ručně jej uložit.'
      : 'First copy a World Package into the Run and manually Save its revision.'}
      {' '}<Link to={'/admin/runs/' + encodeURIComponent(runId) + '/manage'}>
        {cs ? 'Otevřít správu Runu →' : 'Open Run Management →'}
      </Link></p>}
    {draft && draft.status !== 'clean' && !pendingSave && <p className="status">Save or resolve existing Working Draft changes before generating new players.</p>}
    <label>Run-owned World{' '}
      <select aria-label="Run World for player generation" value={selectedWorldId}
        onChange={event => { setSourceId(event.target.value); setCountryCode(''); setRegion('') }}>
        {worldIds.map(id => <option key={id} value={id}>{id}</option>)}
      </select>
    </label>
    <div className="form-grid" aria-label="Hard player generation conditions">
      <label>{cs ? 'Sportovní země' : 'Sport country'}
        <select aria-label="Player generation sport country" value={countryCode}
          disabled={!options} onChange={event => setCountryCode(event.target.value)}>
          <option value="">{cs ? 'Automaticky podle světa' : 'Automatic from World'}</option>
          {(options?.countries ?? []).map(country =>
            <option key={country.code} value={country.code}>{country.code} — {country.name}</option>)}
        </select>
      </label>
      <label>{cs ? 'Region' : 'Region'}
        <select aria-label="Player generation region" value={region}
          disabled={!options} onChange={event => setRegion(event.target.value)}>
          <option value="">{cs ? 'Automaticky podle světa' : 'Automatic from World'}</option>
          {(options?.regions ?? []).map(item =>
            <option key={item} value={item}>{item}</option>)}
        </select>
      </label>
    </div>
    {optionsQuery.isPending && editable && selectedWorldId && !existing &&
      <p role="status">{cs ? 'Ověřuji země a regiony uloženého světa…' : 'Checking saved World countries and regions…'}</p>}
    {optionsQuery.error && <p role="alert" className="error">
      {cs ? 'Podmínky uloženého světa nelze ověřit' : 'Saved World conditions unavailable'}: {formatApiError(optionsQuery.error)}
    </p>}
    {optionsQuery.isSuccess && !options && <p role="alert" className="error">
      {cs ? 'Odpověď podmínek nepatří této branchi, revizi nebo světu.' : 'World condition response does not match this Branch, revision or World.'}
    </p>}
    {conditionConflict && <p role="alert" className="error">{cs ? 'Rozpor podmínek' : 'Condition conflict'}: {conditionConflict}</p>}
    {options && !conditionConflict && <p className="status">
      {cs ? 'Závazný výběr' : 'Hard selection'}: {countryCode || (cs ? 'všechny země' : 'all countries')} ·
      {' '}{region || (cs ? 'všechny regiony' : 'all regions')}.
      {' '}{cs ? 'Nevybrané vlastnosti zůstanou přirozeně proměnlivé.' : 'Unconstrained attributes remain naturally variable.'}
    </p>}
    <div className="form-grid" aria-label="Hard first-season age conditions">
      <label>{cs ? 'Minimální věk (15–45)' : 'Minimum age (15–45)'}
        <input type="number" min={15} max={45} step={1}
          aria-label="Player generation minimum age"
          placeholder={cs ? 'Automaticky' : 'Automatic'}
          value={minAge} onChange={e => setMinAge(e.target.value)} />
      </label>
      <label>{cs ? 'Maximální věk (15–45)' : 'Maximum age (15–45)'}
        <input type="number" min={15} max={45} step={1}
          aria-label="Player generation maximum age"
          placeholder={cs ? 'Automaticky' : 'Automatic'}
          value={maxAge} onChange={e => setMaxAge(e.target.value)} />
      </label>
    </div>
    {ageConflict && <p role="alert" className="error">{cs ? 'Rozpor věkových podmínek' : 'Age condition conflict'}: {ageConflict}</p>}
    <p className="status">{cs
      ? 'Věk k prvnímu týdnu sezóny 2000/01. Při omezení věku se přepočítají pravděpodobnosti existujících kariérních fází, nikoli potenciál hráčů podle země.'
      : 'Age at Week 1 of 2000/01. Age bounds condition the existing career-stage weights, not nationality-based innate potential.'}</p>
    <label>Seed <input aria-label="Player generation seed" type="number" value={seed}
      onChange={event => setSeed(Number(event.target.value))} /></label>
    <label>Number of players (1–128) <input aria-label="Number of generated players" type="number"
      min={1} max={128} value={poolSize} onChange={event => setPoolSize(Number(event.target.value))} /></label>
    <label>First-season ranking Best N <input aria-label="First-season ranking Best N" type="number"
      min={1} value={bestN} onChange={event => setBestN(Number(event.target.value))} /></label>
    <label>Audit reason <input aria-label="InitialWorld audit reason" maxLength={1000}
      value={auditReason} onChange={event => setAuditReason(event.target.value)} /></label>
    <p className="status">Lifecycle retirement-age input: 46 (current first-season policy). No player talent calibration is changed.</p>
    <button type="button" disabled={!canPreview || previewAction.isPending || adoptAction.isPending || saveAction.isPending}
      onClick={() => { setReview(null); setApproved(false); previewAction.mutate() }}>
      {previewAction.isPending ? (cs ? 'Generuji náhled…' : 'Generating preview…') : (cs ? 'Generovat – zobrazit náhled' : 'Preview generated players')}
    </button>
    {previewAction.error && <p role="alert" className="error">Preview failed: {formatApiError(previewAction.error)}</p>}
    {review && <section aria-label="Generated player review">
      <h4>Review {viewedPlayers.length} players</h4>
      <p>Run: {review.runId} · Branch: {review.branchId} · Saved HEAD: <code>{review.head}</code></p>
      <p>{cs ? 'Svět' : 'World'}: {review.request.generation.world_package_id} · Seed: {review.request.generation.seed} · First-season Best {review.request.best_n} · Draft v{review.draftVersion}</p>
      <p>{cs ? 'Použité závazné podmínky' : 'Reviewed hard conditions'}:
        {' '}{countryCode || (cs ? 'země automaticky' : 'country automatic')} ·
        {' '}{region || (cs ? 'region automaticky' : 'region automatic')} ·
        {' '}{minAge || '15'}–{maxAge || '45'} {cs ? 'let' : 'years'}.</p>
      {options && <p className="status">{cs ? 'Kontrola splnění' : 'Fulfilment'}:
        {' '}{viewedPlayers.every(player => (!countryCode || player.country_code === countryCode) &&
          (!region || options.countries.some(country => country.code === player.country_code &&
            (country.region === region || country.travel_region === region))) &&
          (!minAge || player.age_years_at_season_start >= Number(minAge)) &&
          (!maxAge || player.age_years_at_season_start <= Number(maxAge)))
          ? (cs ? 'Všichni hráči splňují závazné podmínky.' : 'Every player satisfies the hard conditions.')
          : (cs ? 'Konflikt! Někteří hráči nesplňují podmínky.' : 'Conflict! Some players fail hard conditions.')}
      </p>}
      <p>{cs ? 'Model' : 'Model'}: <code>{review.preview.state.source_kind}</code> · {cs ? 'Otisk náhledu' : 'Preview fingerprint'}: <code>{review.preview.fingerprint.slice(0, 20)}…</code></p>
      <p>Largest nationality groups: {distribution.map(([country, count]) => `${country} ${count}`).join(' · ')}</p>
      <div className="table-responsive"><table>
        <thead><tr><th>{cs ? 'Hráč' : 'Player'}</th><th>{cs ? 'Země' : 'Country'}</th>
          <th>{cs ? 'Věk na začátku sezóny' : 'First-season age'}</th>
          <th>{cs ? 'Aktuální / potenciál (zdrojová škála)' : 'Current / potential (source scale)'}</th></tr></thead>
        <tbody>{viewedPlayers.map(player =>
          <tr key={player.player_id}><td>{player.name}<small> · {player.player_id}</small></td>
            <td>{player.country_code}</td><td>{player.age_years_at_season_start}</td>
            <td>{player.current_ability} / {player.potential_ability}</td></tr>
        )}</tbody>
      </table></div>
      <p className="status">{cs ? 'V náhledu je kompletní skutečná dávka' : 'Full actual batch is reviewable'}: {viewedPlayers.length}.</p>
      <p className="status">{cs ? 'Aktuální schopnosti 1–99 nejsou canonical 0–200 OVR. Žádné falešné historické zápasy nebo ranking se nevytvářejí.' : 'Current 1–99 abilities are not canonical 0–200 OVR. No fictional past matches or rankings are generated.'}</p>
      {!reviewMatches && <p role="alert" className="error">Review expired: selected Run, Branch, World, revision or generation inputs changed.</p>}
      <label><input type="checkbox" aria-label="Approve InitialWorld adoption" checked={approved}
        onChange={event => setApproved(event.target.checked)} /> Adopt this exact generated InitialWorld to the current Branch.</label>
      <button type="button" disabled={!canAdopt} onClick={() => review && adoptAction.mutate(review)}>
        {adoptAction.isPending ? (cs ? 'Připravuji dávku…' : 'Staging players…') : (cs ? 'Potvrdit a připravit Working Draft' : 'Adopt generated players')}
      </button>
    </section>}
    {adoptAction.error && <p role="alert" className="error">Adoption failed: {formatApiError(adoptAction.error)}</p>}
    {canResume && <section aria-label="Recover InitialWorld save">
      <p role="status">This Branch contains an adopted InitialWorld with unsaved changes. Confirm its Saved Revision without regenerating players.</p>
      <p>{existing?.players.length} existing players from {existing?.world_package_id}. Source seed: {existing?.bootstrap_seed}.</p>
      <button type="button" onClick={() => savePreflight && setPendingSave({
        runId, branchId, head, fingerprint: savePreflight.initial_world_fingerprint
      })}>Review existing InitialWorld save</button>
    </section>}
    {pendingSave && <section aria-label="Save InitialWorld revision">
      <p>{cs ? 'Hráči jsou připraveni v Run-owned InitialWorld. Saved Revision vznikne až výslovným uložením.' : 'Players are staged in Run-owned InitialWorld. Saved Revision is only created by an explicit Save.'}</p>
      {savePreviewQuery.error && <p role="alert" className="error">Save preflight failed: {formatApiError(savePreviewQuery.error)}</p>}
      {!saveReady && !savePreviewQuery.isLoading && <p role="alert" className="error">The saved head, Draft or InitialWorld fingerprint does not match. Refresh before saving.</p>}
      <label><input type="checkbox" aria-label="Approve InitialWorld revision save" checked={saveApproved}
        onChange={event => setSaveApproved(event.target.checked)} /> Create the immutable Saved Revision.</label>
      <button type="button" disabled={!saveReady || !saveApproved || saveAction.isPending}
        onClick={() => saveAction.mutate()}>
        {saveAction.isPending ? (cs ? 'Ukládám revizi…' : 'Saving InitialWorld…') : (cs ? 'Ruční Save nové revize' : 'Save InitialWorld revision')}
      </button>
    </section>}
    {saveAction.error && <p role="alert" className="error">Save failed: {formatApiError(saveAction.error)}</p>}
    {notice && <p role="status">{notice}</p>}
  </SectionCard>
}
