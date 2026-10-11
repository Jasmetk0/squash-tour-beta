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
  orderedPreviewFieldLocks,
  type GeneratedPlayerFieldKey, type RunWorldPreviewFieldLock,
  type RunInitialWorldAdoption, type RunInitialWorldPreview
} from '../api/runInitialWorldSetup'
import { formatApiError, isApiNotFound } from '../utils/apiErrors'
import { SectionCard } from './RunScopedUi'
import { GeneratedPlayerReviewInspector } from './GeneratedPlayerReviewInspector'
import { GeneratedPlayerFieldLockEditor } from './GeneratedPlayerFieldLockEditor'

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
  const [travelRegion, setTravelRegion] = useState('')
  const [minAge, setMinAge] = useState('')
  const [maxAge, setMaxAge] = useState('')
  const [bestN, setBestN] = useState(15)
  const [auditReason, setAuditReason] = useState('Create the first-season player population from the reviewed Run-owned World snapshot.')
  const [review, setReview] = useState<ReviewedWorld | null>(null)
  const [reviewBaseSeed, setReviewBaseSeed] = useState<number | null>(null)
  const [approved, setApproved] = useState(false)
  const [keptIds, setKeptIds] = useState<string[]>([])
  const [rerollSeed, setRerollSeed] = useState(20261010)
  const [selectedPlayerId, setSelectedPlayerId] = useState<string | null>(null)
  const [pendingFieldLocks, setPendingFieldLocks] = useState<RunWorldPreviewFieldLock[]>([])
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
    poolSize >= 1 && poolSize <= 1000 && Number.isInteger(bestN) && bestN >= 1 &&
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
    ? generatorConditionConflict(countryCode, '', options, region, travelRegion)
    : null
  const ageConflict = ageConditionConflict(minAge, maxAge)
  const canPreview = editable && worldIds.length > 0 && validParameters &&
    packageQuery.isSuccess && Boolean(options) && !conditionConflict && !ageConflict &&
    draft?.base_saved_revision_id === head &&
    draft.status === 'clean' && !existing && existingQuery.isSuccess === false &&
    isApiNotFound(existingQuery.error) && !pendingSave

  useEffect(() => {
    setReview(null)
    setReviewBaseSeed(null)
    setKeptIds([])
    setPendingFieldLocks([])
    setSelectedPlayerId(null)
    setPendingSave(null)
    setApproved(false)
    setSaveApproved(false)
    setNotice('')
  }, [runId, branchId, head, sourceId, seed, poolSize, countryCode, region, travelRegion, minAge, maxAge, bestN, auditReason])

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
          ...(region ? { geographic_region: region } : {}),
          ...(travelRegion ? { travel_region: travelRegion } : {}),
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
    onSuccess: value => {
      setReview(value); setReviewBaseSeed(seed); setKeptIds([]); setRerollSeed(seed + 1)
      setPendingFieldLocks([]); setSelectedPlayerId(null)
      setApproved(false); setNotice('')
    }
  })
  const reviewMatches = Boolean(review && review.runId === runId &&
    review.branchId === branchId && review.head === head &&
    review.sourceFingerprint === snapshotFingerprint &&
    review.draftVersion === draft?.draft_version &&
    draft?.base_saved_revision_id === head && draft?.status === 'clean' &&
    review.request.generation.world_package_id === selectedWorldId &&
    reviewBaseSeed === seed &&
    review.request.generation.target_pool_size === poolSize &&
    (review.request.generation.country_code ?? '') === countryCode &&
    (review.request.generation.geographic_region ?? '') === region &&
    (review.request.generation.travel_region ?? '') === travelRegion &&
    String(review.request.generation.min_age ?? '') === minAge &&
    String(review.request.generation.max_age ?? '') === maxAge &&
    Boolean(options) && !conditionConflict && !ageConflict &&
    review.request.best_n === bestN && review.request.audit_reason === auditReason.trim() &&
    !existing && isApiNotFound(existingQuery.error))

  const approvedFieldLocks = orderedPreviewFieldLocks(review?.request.generation.field_locks ?? [])
  const locksDirty = JSON.stringify(approvedFieldLocks) !==
    JSON.stringify(orderedPreviewFieldLocks(pendingFieldLocks))
  const fieldEditingEnabled = Boolean(reviewMatches && review &&
    review.request.generation.keep_from_seed == null && canPreview)
  const onPreviewFieldChange = (field: GeneratedPlayerFieldKey, value: number | null) => {
    if (!selectedPlayerId || !fieldEditingEnabled) return
    setPendingFieldLocks(current => orderedPreviewFieldLocks(
      value == null
        ? current.filter(lock => !(lock.player_id === selectedPlayerId && lock.field === field))
        : [...current.filter(lock => !(lock.player_id === selectedPlayerId && lock.field === field)),
          { player_id: selectedPlayerId, field, value }]
    ))
    setApproved(false)
  }
  const sessionSteps = (review?.request.generation.keep_history?.length ?? 0) +
    (review?.request.generation.keep_from_seed == null ? 0 : 1)
  const canKeepPreview = Boolean(reviewMatches && review && canPreview && sessionSteps < 17)
  const canRegenerate = canKeepPreview &&
    keptIds.length > 0 && keptIds.length < poolSize &&
    Number.isSafeInteger(rerollSeed) && rerollSeed !== review?.request.generation.seed

  const regenerateAction = useMutation({
    mutationFn: async () => {
      if (!canRegenerate || !review || !draft || !snapshotFingerprint)
        throw new Error('Verified source preview, Keep selection and new seed are required.')
      const sourceIds = new Set(review.preview.state.players.map(p => p.player_id))
      const retained = [...new Set(keptIds)].sort()
      if (retained.length !== keptIds.length || retained.some(id => !sourceIds.has(id)))
        throw new Error('Session Keep contains unknown or duplicate source players.')
      const previous = review.request.generation
      const history = previous.keep_from_seed == null
        ? []
        : [...(previous.keep_history ?? []), {
            seed: previous.seed,
            keep_from_seed: previous.keep_from_seed,
            keep_from_preview_fingerprint: previous.keep_from_preview_fingerprint!,
            keep_player_ids: previous.keep_player_ids ?? []
          }]
      const request: RunInitialWorldAdoption = {
        ...review.request,
        command_id: `admin-initial-world-${crypto.randomUUID()}`,
        generation: {
          ...previous,
          seed: rerollSeed,
          ...(history.length ? { keep_history: history } : {}),
          keep_from_seed: review.request.generation.seed,
          keep_from_preview_fingerprint: review.preview.state.run_world_pool_preview_fingerprint,
          keep_player_ids: retained
        },
      }
      const preview = await previewRunOwnedInitialWorld(runId, branchId, request)
      if (!verifiedInitialWorldPreview(preview, runId, branchId, request, options))
        throw new Error('Regenerated preview is inconsistent with the exact reviewed source.')
      const original = new Map(review.preview.state.players.map(p => [p.player_id, p]))
      for (const id of retained) {
        const before = original.get(id)
        const after = preview.state.players.find(p => p.player_id === id)
        if (!before || !after || before.name !== after.name ||
          before.country_code !== after.country_code ||
          before.age_years_at_season_start !== after.age_years_at_season_start ||
          before.current_ability !== after.current_ability ||
          before.potential_ability !== after.potential_ability ||
          before.potential_tier !== after.potential_tier)
          throw new Error('A Keep player changed in the regenerated preview.')
      }
      return { runId, branchId, head, sourceFingerprint: snapshotFingerprint,
        draftVersion: draft.draft_version, request, preview, retained }
    },
    onSuccess: value => {
      setReview(value); setKeptIds(value.retained)
      setPendingFieldLocks(orderedPreviewFieldLocks(value.request.generation.field_locks ?? []))
      setRerollSeed(value.request.generation.seed + 1)
      setApproved(false); setNotice(
        'Regenerated the remaining players. Keep selections remain available for another pass; Adopt and Save are separate.'
      )
    }
  })

  // No field value supplied by the browser is authoritative until the server
  // returns a fresh exact preview. A failed edit leaves the prior review intact.
  const fieldPreviewAction = useMutation({
    mutationFn: async (regenerate: boolean) => {
      if (!fieldEditingEnabled || !review || !draft || !snapshotFingerprint ||
          keptIds.length > 0)
        throw new Error('An unmodified, active first-cohort preview is required to edit source fields.')
      if (regenerate && (locksDirty || !pendingFieldLocks.length ||
          !Number.isSafeInteger(rerollSeed) ||
          rerollSeed === review.request.generation.seed))
        throw new Error('Apply all locks first and choose a new seed before regenerating unlocked fields.')
      const request: RunInitialWorldAdoption = {
        ...review.request,
        command_id: `admin-initial-world-${crypto.randomUUID()}`,
        generation: {
          ...review.request.generation,
          seed: regenerate ? rerollSeed : review.request.generation.seed,
          ...(pendingFieldLocks.length
            ? { field_locks: orderedPreviewFieldLocks(pendingFieldLocks) }
            : { field_locks: [] })
        }
      }
      const preview = await previewRunOwnedInitialWorld(runId, branchId, request)
      if (!verifiedInitialWorldPreview(preview, runId, branchId, request, options))
        throw new Error('Server preview does not match all verified locked values or generation scope.')
      return { runId, branchId, head, sourceFingerprint: snapshotFingerprint,
        draftVersion: draft.draft_version, request, preview, regenerate }
    },
    onSuccess: value => {
      setReview(value)
      setPendingFieldLocks(orderedPreviewFieldLocks(value.request.generation.field_locks ?? []))
      setApproved(false)
      if (value.regenerate) setRerollSeed(value.request.generation.seed + 1)
      setNotice(value.regenerate
        ? 'Unlocked source fields regenerated; locked values were verified. Review before Adopt and Save.'
        : 'Field locks applied to the exact server preview; Run remains unchanged.')
    }
  })

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

  const appliedKeep = review?.request.generation.keep_player_ids ?? []
  const pendingKeepChange = keptIds.join('|') !== appliedKeep.join('|')
  const canAdopt = reviewMatches && approved && !pendingKeepChange && !locksDirty &&
    !fieldPreviewAction.isPending &&
    !regenerateAction.isPending && !adoptAction.isPending && !previewAction.isPending
  const viewedPlayers = review?.preview.state.players ?? []

  return <SectionCard title={cs ? 'Generovat hráče — první úplná dávka' : 'Generate first-season players'}>
    <p className="status">{cs
      ? 'První funkční dávka 1–1000 hráčů pro sezónu 2000/01. Používá pouze uložený World Package dané branche. Náhled nic nezapisuje; potvrzení připraví InitialWorld a teprve ruční Save vytváří Saved Revision.'
      : 'First supported complete batch (1–1000 players) for season 2000/01. Uses the saved Run-owned World Package only. Preview never writes; confirmation stages InitialWorld, then manual Save creates a Saved Revision.'}</p>
    <p className="status">{cs
      ? 'Závazné podmínky země, regionu a věku platí pro všechny hráče dávky. Prázdná pole zachovávají automatické rozdělení. Skupiny a kvóty zatím nejsou podporované; editor podporuje devět zdrojových schopností (1–99).'
      : 'Hard country, region and age conditions apply to every player. Blank conditions preserve automatic allocation. Groups and quotas are not supported yet; the preview editor supports nine source abilities (1–99).'}</p>
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
        onChange={event => { setSourceId(event.target.value); setCountryCode(''); setRegion(''); setTravelRegion('') }}>
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
      <label>{cs ? 'Geografický region' : 'Geographic Region'}
        <select aria-label="Player generation geographic region" value={region}
          disabled={!options} onChange={event => setRegion(event.target.value)}>
          <option value="">{cs ? 'Automaticky podle světa' : 'Automatic from World'}</option>
          {(options?.geographic_regions ?? [...new Set(options?.countries.map(c => c.region) ?? [])].sort()).map(item =>
            <option key={item} value={item}>{item}</option>)}
        </select>
      </label>
      <label>{cs ? 'Cestovní region' : 'Travel Region'}
        <select aria-label="Player generation travel region" value={travelRegion}
          disabled={!options} onChange={event => setTravelRegion(event.target.value)}>
          <option value="">{cs ? 'Automaticky podle světa' : 'Automatic from World'}</option>
          {(options?.travel_regions ?? [...new Set(options?.countries.map(c => c.travel_region) ?? [])].sort()).map(item =>
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
      {' '}{region || (cs ? 'všechny geografické regiony' : 'all geographic regions')} ·
      {' '}{travelRegion || (cs ? 'všechny cestovní regiony' : 'all travel regions')}.
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
    <label>Number of players (1–1000) <input aria-label="Number of generated players" type="number"
      min={1} max={1000} value={poolSize} onChange={event => setPoolSize(Number(event.target.value))} /></label>
    <label>First-season ranking Best N <input aria-label="First-season ranking Best N" type="number"
      min={1} value={bestN} onChange={event => setBestN(Number(event.target.value))} /></label>
    <label>Audit reason <input aria-label="InitialWorld audit reason" maxLength={1000}
      value={auditReason} onChange={event => setAuditReason(event.target.value)} /></label>
    <p className="status">Lifecycle retirement-age input: 46 (current first-season policy). No player talent calibration is changed.</p>
    <button type="button" disabled={!canPreview || previewAction.isPending || regenerateAction.isPending ||
        adoptAction.isPending || saveAction.isPending}
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
        {' '}{region || (cs ? 'geografický region automaticky' : 'geographic region automatic')} ·
        {' '}{travelRegion || (cs ? 'cestovní region automaticky' : 'travel region automatic')} ·
        {' '}{minAge || '15'}–{maxAge || '45'} {cs ? 'let' : 'years'}.</p>
      {options && <p className="status">{cs ? 'Kontrola splnění' : 'Fulfilment'}:
        {' '}{viewedPlayers.every(player => (!countryCode || player.country_code === countryCode) &&
          (!region || options.countries.some(country => country.code === player.country_code &&
            country.region === region)) &&
          (!travelRegion || options.countries.some(country => country.code === player.country_code &&
            country.travel_region === travelRegion)) &&
          (!minAge || player.age_years_at_season_start >= Number(minAge)) &&
          (!maxAge || player.age_years_at_season_start <= Number(maxAge)))
          ? (cs ? 'Všichni hráči splňují závazné podmínky.' : 'Every player satisfies the hard conditions.')
          : (cs ? 'Konflikt! Někteří hráči nesplňují podmínky.' : 'Conflict! Some players fail hard conditions.')}
      </p>}
      <p>{cs ? 'Model' : 'Model'}: <code>{review.preview.state.source_kind}</code> · {cs ? 'Otisk náhledu' : 'Preview fingerprint'}: <code>{review.preview.fingerprint.slice(0, 20)}…</code></p>
      <GeneratedPlayerReviewInspector key={review.preview.fingerprint} players={viewedPlayers} locale={locale}
        selectedPlayerId={selectedPlayerId}
        onSelectPlayer={fieldEditingEnabled ? setSelectedPlayerId : undefined}
        keepIds={keptIds}
        onKeepChange={canKeepPreview ? (id, checked) => {
          setKeptIds(current => checked
            ? [...new Set([...current, id])].sort()
            : current.filter(item => item !== id))
          setApproved(false)
        } : undefined} />
      {selectedPlayerId && viewedPlayers.some(p=>p.player_id===selectedPlayerId) &&
        <GeneratedPlayerFieldLockEditor
          key={selectedPlayerId + ':' + review.preview.fingerprint}
          player={viewedPlayers.find(p=>p.player_id===selectedPlayerId)!}
          locks={pendingFieldLocks}
          onChange={onPreviewFieldChange}
          onApply={()=>fieldPreviewAction.mutate(false)}
          onRegenerate={()=>fieldPreviewAction.mutate(true)}
          onClose={()=>setSelectedPlayerId(null)}
          dirty={locksDirty}
          busy={fieldPreviewAction.isPending || regenerateAction.isPending ||
            previewAction.isPending || adoptAction.isPending}
          disabled={!fieldEditingEnabled || keptIds.length > 0}
          error={fieldPreviewAction.error ? formatApiError(fieldPreviewAction.error) : null}
          seed={rerollSeed}
        />}
      {fieldPreviewAction.error && !selectedPlayerId &&
        <p role="alert">Field edit conflict: {formatApiError(fieldPreviewAction.error)}</p>}
      {canKeepPreview && <section aria-label="Session Keep regeneration">
        <h5>{cs ? 'Keep vybraných a regenerace ostatních' : 'Keep selected, regenerate remaining'}</h5>
        <p className="status">{cs
          ? 'Vyber Keep u hráčů v tabulce a zadej jiný seed. Server znovu ověří původní náhled a přegeneruje ostatní bez zápisu do Runu. Keep není trvalý Lock.'
          : 'Mark Keep on preview players and supply a different seed. The server verifies the original preview and regenerates the remaining players without writing to the Run. Keep is not a permanent Lock.'}</p>
        <label>{cs ? 'Nový seed' : 'New regeneration seed'}
          <input type="number" aria-label="Session Keep regeneration seed" value={rerollSeed}
            onChange={e => setRerollSeed(Number(e.target.value))} />
        </label>
        <p>{cs ? 'Ponecháno' : 'Kept'}: {keptIds.length} / {poolSize} ·
          {' '}{cs ? 'K regeneraci' : 'Regenerate'}: {poolSize - keptIds.length}</p>
        {keptIds.length === poolSize && <p role="alert">{cs
          ? 'Ponechání všech hráčů nenechává nic k regeneraci.'
          : 'Keeping every player leaves nothing to regenerate.'}</p>}
        {rerollSeed === review.request.generation.seed && <p role="alert">{cs
          ? 'Pro regeneraci je potřeba jiný seed.'
          : 'A different seed is required for regeneration.'}</p>}
        <button type="button" disabled={!canRegenerate || regenerateAction.isPending ||
          adoptAction.isPending || previewAction.isPending}
          onClick={() => regenerateAction.mutate()}>
          {regenerateAction.isPending ? (cs ? 'Regeneruji…' : 'Regenerating…')
            : (cs ? 'Regenerovat ostatní – nový náhled' : 'Regenerate remaining – new preview')}
        </button>
        {pendingKeepChange && <p className="status">{cs
          ? 'Keep výběr dosud nic nemění. Nejprve spusť regeneraci, pak potvrď nový celý náhled.'
          : 'Keep selection alone changes nothing. Regenerate first, then confirm the entire new preview.'}</p>}
      </section>}
      {sessionSteps > 0 && <p className="status">
        {cs ? `Počet ověřených regenerací v relaci: ${sessionSteps}. Keep je dočasný, bez trvalých zámků.`
          : `Verified session Keep regenerations: ${sessionSteps}. Keep is temporary, not a permanent player lock.`}
      </p>}
      {regenerateAction.error && <p role="alert" className="error">
        {cs ? 'Regenerace selhala' : 'Regeneration failed'}: {formatApiError(regenerateAction.error)}
      </p>}

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
