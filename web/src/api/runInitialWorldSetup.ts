/** Production Run-owned generated InitialWorld request/review contracts. */
export type RunWorldKeepHistoryStep = {
  seed: number
  keep_from_seed: number
  keep_from_preview_fingerprint: string
  keep_player_ids: string[]
}

export type GeneratedPlayerFieldKey =
  | 'current_ability' | 'potential_ability'
  | 'attributes.technique' | 'attributes.movement' | 'attributes.physical'
  | 'attributes.mental' | 'attributes.consistency' | 'attributes.clutch'
  | 'attributes.recovery'

/** Append-only, fingerprint-anchored edits and Keep steps (v2 opt-in). */
export type RunWorldPreviewAutomaticField = {
  player_id: string
  field: GeneratedPlayerFieldKey
}

export type RunWorldVerifiedSessionStep = {
  kind: 'edit' | 'keep'
  source_preview_fingerprint: string
  seed: number
  keep_player_ids: string[]
  field_locks: RunWorldPreviewFieldLock[]
  automatic_fields?: RunWorldPreviewAutomaticField[]
}

export type RunWorldExactCountryQuota = {
  country_code: string
  count: number
}

export type RunWorldPreviewFieldLock = {
  player_id: string
  field: GeneratedPlayerFieldKey
  value: number
}

export const PREVIEW_FIELD_KEYS: GeneratedPlayerFieldKey[] = [
  'current_ability','potential_ability','attributes.technique',
  'attributes.movement','attributes.physical','attributes.mental',
  'attributes.consistency','attributes.clutch','attributes.recovery'
]

export function orderedPreviewFieldLocks(locks: RunWorldPreviewFieldLock[]): RunWorldPreviewFieldLock[] {
  return [...locks].sort((a,b)=>a.player_id.localeCompare(b.player_id) ||
    a.field.localeCompare(b.field))
}

export type RunSavedGenerationProposal = {
  schema_version: 'run_generation_proposal.v1'
  run_id: string
  branch_id: string
  proposal_id: string
  label: string
  saved_revision_id: string
  draft_version: number
  package_fingerprint: string
  preview_fingerprint: string
  source_seed: number
  next_seed: number
  selected_keep_ids: string[]
  pending_field_locks: RunWorldPreviewFieldLock[]
  request: RunInitialWorldAdoption
  preview: RunInitialWorldPreview
}

/** Historical inspection is not an Adopt approval. No preview regeneration on GET. */
export type RunGenerationProposalInspection = {
  schema_version: 'run_generation_proposal_inspection.v1'
  historical_only: true
  proposal: RunSavedGenerationProposal
  context: {
    saved_revision_id: string
    draft_version: number
    draft_status: string
    package_fingerprint: string | null
    head_matches: boolean
    draft_matches: boolean
    package_matches: boolean
    initial_world_exists: boolean
    revalidation_required: boolean
  }
}

export type RunGenerationProposalRevalidation = {
  schema_version: 'run_generation_proposal_revalidation.v1'
  preview_only: true
  proposal_id: string
  original_preview_fingerprint: string
  current_context: {
    saved_revision_id: string
    draft_version: number
    package_fingerprint: string
  }
  request: RunInitialWorldAdoption
  preview: RunInitialWorldPreview
  comparison: {
    old_count: number
    new_count: number
    added_identities: number
    removed_identities: number
    changed_profiles: number
    unchanged_profiles: number
  }
}

export type RunSavedGenerationProposalSummary = Pick<
  RunSavedGenerationProposal,
  'proposal_id' | 'label' | 'saved_revision_id' | 'draft_version' |
  'package_fingerprint' | 'preview_fingerprint'
>

export type RunSaveGenerationProposal = Pick<
  RunSavedGenerationProposal,
  'proposal_id' | 'label' | 'source_seed' | 'next_seed' |
  'selected_keep_ids' | 'pending_field_locks'
> & {
  saved_revision_id: string
  draft_version: number
  package_fingerprint: string
  preview_fingerprint: string
  request: RunInitialWorldAdoption
}

export type RunInitialWorldGeneration = {
  world_package_id: string
  season: '2000/2001'
  seed: number
  target_pool_size: number
  country_code?: string | null
  region?: string | null // Legacy geographic OR travel condition
  geographic_region?: string | null
  travel_region?: string | null
  min_age?: number | null
  max_age?: number | null
  country_quotas?: RunWorldExactCountryQuota[]
  keep_from_seed?: number | null
  keep_from_preview_fingerprint?: string | null
  keep_player_ids?: string[]
  keep_history?: RunWorldKeepHistoryStep[]
  field_locks?: RunWorldPreviewFieldLock[]
  session_schema_version?: 'run_world_generation_session.v2' | null
  session_origin_request?: RunInitialWorldGeneration | null
  session_origin_fingerprint?: string | null
  session_steps?: RunWorldVerifiedSessionStep[]
}

export type RunWorldGenerationCountry = {
  code: string
  name: string
  region: string
  travel_region: string
}

export type RunWorldGenerationOptions = {
  schema_version: 'run_world_generation_options.v1'
  run_id: string
  branch_id: string
  saved_revision_id: string
  draft_version: number
  run_package_fingerprint: string
  world_package_id: string
  countries: RunWorldGenerationCountry[]
  regions: string[] // Legacy combined options
  geographic_regions?: string[]
  travel_regions?: string[]
}

export function verifiedGenerationOptions(
  data: RunWorldGenerationOptions, runId: string, branchId: string,
  head: string, draftVersion: number, fingerprint: string, worldId: string
): boolean {
  return data?.schema_version === 'run_world_generation_options.v1' &&
    data.run_id === runId && data.branch_id === branchId &&
    data.saved_revision_id === head && data.draft_version === draftVersion &&
    data.run_package_fingerprint === fingerprint &&
    data.world_package_id === worldId && Array.isArray(data.countries) &&
    data.countries.length > 0 && Array.isArray(data.regions) &&
    data.countries.every(country => /^[A-Z]{3}$/.test(country.code) &&
      typeof country.name === 'string' && country.name.length > 0 &&
      typeof country.region === 'string' && country.region.length > 0 &&
      typeof country.travel_region === 'string' && country.travel_region.length > 0) &&
    new Set(data.countries.map(country => country.code)).size === data.countries.length &&
    data.regions.every(region => typeof region === 'string' && region.length > 0) &&
    new Set(data.regions).size === data.regions.length &&
    data.countries.every(country => data.regions.includes(country.region) &&
      data.regions.includes(country.travel_region)) &&
    (!data.geographic_regions || (Array.isArray(data.geographic_regions) &&
      new Set(data.geographic_regions).size === data.geographic_regions.length &&
      data.countries.every(c => data.geographic_regions!.includes(c.region)))) &&
    (!data.travel_regions || (Array.isArray(data.travel_regions) &&
      new Set(data.travel_regions).size === data.travel_regions.length &&
      data.countries.every(c => data.travel_regions!.includes(c.travel_region))))
}

export type RunInitialWorldAdoption = {
  command_id: string
  generation: RunInitialWorldGeneration
  audit_label: string
  audit_reason: string
  official_run: false
  best_n: number
  automatic_retirement_age: 46
}

export type RunInitialWorldPlayer = {
  player_id: string
  name: string
  country_code: string
  age_years_at_season_start: number
  current_ability: number
  potential_ability: number
  potential_tier: string
  career_stage?: string
  attributes?: Record<string, number>
}

export type RunInitialWorldState = {
  run_id: string
  branch_id: string
  season: '2000/2001'
  source_kind: 'run_world_generated_pool.v1'
  world_package_id: string
  bootstrap_seed: number
  adopted_by_command_id: string
  adoption_request_fingerprint: string
  world_country_content_fingerprint: string
  world_generation_content_fingerprint: string
  run_world_pool_preview_fingerprint: string
  players: RunInitialWorldPlayer[]
  policies: { policy_id: string; best_n: number }[]
}

export type RunInitialWorldPreview = {
  preview_only: true
  state: RunInitialWorldState
  fingerprint: string
}

export type RunInitialWorldSavePreview = {
  draft_version: number
  initial_world_fingerprint: string
  has_unsaved_changes: boolean
  run_id?: string
  branch_id?: string
  saved_head_revision_id?: string
  can_save?: boolean
}

export type RunInitialWorldSaved = {
  saved_revision: { revision_id: string }
  working_draft: {
    run_id: string
    branch_id: string
    base_saved_revision_id: string
    status: string
  }
}

/** Strict hard country+region validation; never turn an invalid combination into a hint. */
export function generatorConditionConflict(
  countryCode: string, region: string, options: RunWorldGenerationOptions | null,
  geographicRegion = '', travelRegion = ''
): string | null {
  if (!options) return 'Saved World condition options are not available.'
  if (countryCode && !options.countries.some(c => c.code === countryCode))
    return `Sport country ${countryCode} is not present in the selected saved World.`
  if (region && !options.regions.includes(region))
    return `Region ${region} is not present in the selected saved World.`
  if (countryCode && region && !options.countries.some(c =>
    c.code === countryCode && (c.region === region || c.travel_region === region)))
    return `Country ${countryCode} does not belong to region ${region} in this saved World.`
  if (geographicRegion && !options.countries.some(c => c.region === geographicRegion))
    return `Geographic Region ${geographicRegion} has no countries in this saved World.`
  if (travelRegion && !options.countries.some(c => c.travel_region === travelRegion))
    return `Travel Region ${travelRegion} has no countries in this saved World.`
  if ((geographicRegion || travelRegion) && !options.countries.some(c =>
    (!countryCode || c.code === countryCode) &&
    (!region || c.region === region || c.travel_region === region) &&
    (!geographicRegion || c.region === geographicRegion) &&
    (!travelRegion || c.travel_region === travelRegion)))
    return 'Conflicting geographic/travel conditions for the selected country or regions.'
  return null
}

/** Country quotas are exact whole-cohort counts, not extra players.
 * The remaining seats may only come from eligible, non-quota countries.
 * This deliberately does not implement overlapping talent/handedness groups.
 */
export function countryQuotaConflict(
  quotas: RunWorldExactCountryQuota[], total: number,
  options: RunWorldGenerationOptions | null,
  countryCode = '', geographicRegion = '', travelRegion = ''
): string | null {
  if (!quotas.length) return null
  if (!options) return 'Saved World country options are unavailable.'
  const eligible = options.countries.filter(c =>
    (!countryCode || c.code === countryCode) &&
    (!geographicRegion || c.region === geographicRegion) &&
    (!travelRegion || c.travel_region === travelRegion)
  )
  const codes = quotas.map(q => q.country_code)
  if (codes.join('|') !== [...new Set(codes)].sort().join('|'))
    return 'Country quota codes must be unique and alphabetically sorted.'
  if (quotas.some(q => !Number.isSafeInteger(q.count) || q.count < 0 ||
    q.count > 2000 || !eligible.some(c => c.code === q.country_code)))
    return 'A quota has an invalid count or country outside the selected saved World conditions.'
  const assigned = quotas.reduce((sum,q) => sum + q.count,0)
  if (assigned > total) return 'Exact country quotas exceed the total number of players.'
  if (assigned < total && eligible.every(c => codes.includes(c.code)))
    return 'No other eligible countries remain to fill the automatic remainder.'
  return null
}

/** Frontend preflight mirrors backend bounds; blank = unconstrained. */
export function ageConditionConflict(minAge: string, maxAge: string): string | null {
  const valid = (value: string): boolean =>
    value === '' || (/^[0-9]+$/.test(value) &&
      Number.isSafeInteger(Number(value)) && Number(value) >= 15 && Number(value) <= 45)
  if (!valid(minAge) || !valid(maxAge))
    return 'Age conditions must be whole years between 15 and 45.'
  if (minAge !== '' && maxAge !== '' && Number(minAge) > Number(maxAge))
    return 'Minimum age cannot exceed maximum age.'
  return null
}

export function verifiedInitialWorldPreview(
  value: RunInitialWorldPreview,
  runId: string,
  branchId: string,
  request: RunInitialWorldAdoption,
  options?: RunWorldGenerationOptions | null
): boolean {
  const state = value?.state
  const players = state?.players
  if ((request.generation.country_code || request.generation.region ||
       request.generation.geographic_region || request.generation.travel_region) &&
      generatorConditionConflict(request.generation.country_code ?? '',
        request.generation.region ?? '', options ?? null,
        request.generation.geographic_region ?? '', request.generation.travel_region ?? '')) return false
  const min = request.generation.min_age ?? null
  const max = request.generation.max_age ?? null
  if (min != null && (!Number.isInteger(min) || min < 15 || min > 45)) return false
  if (max != null && (!Number.isInteger(max) || max < 15 || max > 45)) return false
  if (min != null && max != null && min > max) return false
  if (!Number.isInteger(request.generation.target_pool_size) ||
      request.generation.target_pool_size < 1 || request.generation.target_pool_size > 2000) return false
  const quotas = request.generation.country_quotas ?? []
  if (!Array.isArray(quotas) || quotas.length > 250 ||
      countryQuotaConflict(quotas, request.generation.target_pool_size,
        options ?? null, request.generation.country_code ?? '',
        request.generation.geographic_region ?? '',
        request.generation.travel_region ?? '')) return false
  const fieldLocks = request.generation.field_locks ?? []
  if (!Array.isArray(fieldLocks) || fieldLocks.length > 2000 ||
      fieldLocks.some(lock => !lock || !lock.player_id ||
        typeof lock.player_id !== 'string' || lock.player_id.length > 128 ||
        !PREVIEW_FIELD_KEYS.includes(lock.field) ||
        !Number.isInteger(lock.value) || lock.value < 1 || lock.value > 99) ||
      JSON.stringify(fieldLocks) !== JSON.stringify(orderedPreviewFieldLocks(fieldLocks)) ||
      new Set(fieldLocks.map(lock => lock.player_id + ':' + lock.field)).size !== fieldLocks.length)
    return false
  const session = request.generation
  const sessionSteps = session.session_steps ?? []
  const sessionV2 = session.session_schema_version === 'run_world_generation_session.v2'
  if (sessionV2) {
    const origin = session.session_origin_request
    if (!origin || origin.session_schema_version || !/^[0-9a-f]{64}$/.test(
      session.session_origin_fingerprint ?? ''
    ) || !sessionSteps.length || sessionSteps.length > 48 ||
       sessionSteps.filter(step => step.kind === 'keep').length > 17) return false
    if (sessionSteps.some(step => {
      const automatic = step.automatic_fields ?? []
      return !Array.isArray(automatic) || automatic.length > 2000 ||
        automatic.some(item => !item || typeof item.player_id !== 'string' ||
          !item.player_id || item.player_id.length > 128 ||
          !PREVIEW_FIELD_KEYS.includes(item.field)) ||
        JSON.stringify(automatic) !== JSON.stringify(
          [...automatic].sort((a,b)=>a.player_id.localeCompare(b.player_id) ||
            a.field.localeCompare(b.field))) ||
        new Set(automatic.map(item=>item.player_id+':'+item.field)).size !== automatic.length ||
        automatic.some(item=>step.field_locks.some(lock=>
          lock.player_id === item.player_id && lock.field === item.field)) ||
        (step.kind === 'keep' && automatic.length > 0) ||
      (step.kind !== 'edit' && step.kind !== 'keep') ||
      !/^[0-9a-f]{64}$/.test(step.source_preview_fingerprint) ||
      !Number.isSafeInteger(step.seed) ||
      (step.kind === 'edit' && step.keep_player_ids.length > 0) ||
      (step.kind === 'keep' && (!step.keep_player_ids.length ||
        step.keep_player_ids.length >= session.target_pool_size)) ||
      step.keep_player_ids.join('|') !== [...new Set(step.keep_player_ids)].sort().join('|') ||
      step.field_locks.length > 2000 ||
      JSON.stringify(step.field_locks) !== JSON.stringify(orderedPreviewFieldLocks(step.field_locks)) ||
      new Set(step.field_locks.map(lock=>lock.player_id+':'+lock.field)).size !== step.field_locks.length
    })) return false
    const last = sessionSteps[sessionSteps.length-1]
    if (last.seed !== session.seed ||
      JSON.stringify(last.field_locks) !== JSON.stringify(fieldLocks)) return false
  } else if (session.session_origin_request || session.session_origin_fingerprint ||
             sessionSteps.length) return false
  const newestKeep = [...sessionSteps].reverse().find(step=>step.kind==='keep')
  const kept = newestKeep?.keep_player_ids ?? session.keep_player_ids ?? []
  const history = session.keep_history ?? []
  if (!Array.isArray(history) || history.length > 16) return false
  if (history.length && (!session.keep_player_ids?.length ||
      history[history.length - 1].seed !== request.generation.keep_from_seed)) return false
  for (let i = 0; i < history.length; i++) {
    const step = history[i]
    if (!step || !Number.isSafeInteger(step.seed) ||
        !Number.isSafeInteger(step.keep_from_seed) ||
        step.seed === step.keep_from_seed ||
        (i > 0 && step.keep_from_seed !== history[i - 1].seed) ||
        !/^[0-9a-f]{64}$/.test(step.keep_from_preview_fingerprint) ||
        !Array.isArray(step.keep_player_ids) || !step.keep_player_ids.length ||
        step.keep_player_ids.length >= request.generation.target_pool_size ||
        step.keep_player_ids.some(id => typeof id !== 'string' || !id || id.length > 128) ||
        step.keep_player_ids.join('|') !== [...new Set(step.keep_player_ids)].sort().join('|')) return false
  }
  if (kept.length > 0) {
    if ((!sessionV2 && !Number.isSafeInteger(request.generation.keep_from_seed)) ||
        (!sessionV2 && request.generation.keep_from_seed === request.generation.seed) ||
        (!sessionV2 && !/^[0-9a-f]{64}$/.test(request.generation.keep_from_preview_fingerprint ?? '')) ||
        kept.length >= request.generation.target_pool_size ||
        kept.some(id => typeof id !== 'string' || !id) ||
        kept.join('|') !== [...new Set(kept)].sort().join('|') ||
        !Array.isArray(players) ||
        !kept.every(id => players.some(player => player.player_id === id)))
      return false
  } else if (request.generation.keep_from_seed != null ||
             request.generation.keep_from_preview_fingerprint != null) {
    return false
  }
  return value?.preview_only === true &&
    /^[a-f0-9]{64}$/.test(value.fingerprint) &&
    state?.run_id === runId && state?.branch_id === branchId &&
    state.season === '2000/2001' &&
    state.source_kind === 'run_world_generated_pool.v1' &&
    state.world_package_id === request.generation.world_package_id &&
    state.bootstrap_seed === request.generation.seed &&
    state.adopted_by_command_id === request.command_id &&
    /^[a-f0-9]{64}$/.test(state.adoption_request_fingerprint) &&
    /^[a-f0-9]{64}$/.test(state.world_country_content_fingerprint) &&
    /^[a-f0-9]{64}$/.test(state.world_generation_content_fingerprint) &&
    /^[a-f0-9]{64}$/.test(state.run_world_pool_preview_fingerprint) &&
    Array.isArray(players) && players.length === request.generation.target_pool_size &&
    new Set(players.map(p => p.player_id)).size === players.length &&
    quotas.every(quota =>
      players.filter(p => p.country_code === quota.country_code).length === quota.count
    ) &&
    fieldLocks.every(lock => {
      const player = players.find(p=>p.player_id === lock.player_id)
      const value = player && (lock.field.startsWith('attributes.')
        ? player.attributes?.[lock.field.split('.')[1]]
        : player[lock.field as 'current_ability'|'potential_ability'])
      return value === lock.value
    }) &&
    players.every(player => typeof player.player_id === 'string' && player.player_id.length > 0 &&
      typeof player.name === 'string' && typeof player.country_code === 'string' &&
      (!request.generation.country_code ||
        player.country_code === request.generation.country_code) &&
      (!request.generation.region || (options?.countries.some(country =>
        country.code === player.country_code &&
        (country.region === request.generation.region ||
         country.travel_region === request.generation.region)) ?? false)) &&
      (!request.generation.geographic_region || (options?.countries.some(c =>
        c.code === player.country_code && c.region === request.generation.geographic_region) ?? false)) &&
      (!request.generation.travel_region || (options?.countries.some(c =>
        c.code === player.country_code && c.travel_region === request.generation.travel_region) ?? false)) &&
      (min == null || (Number.isInteger(player.age_years_at_season_start) &&
        player.age_years_at_season_start >= min)) &&
      (max == null || (Number.isInteger(player.age_years_at_season_start) &&
        player.age_years_at_season_start <= max))) &&
    Array.isArray(state.policies) && state.policies.length === 1 &&
    state.policies[0].best_n === request.best_n
}

export function runOwnedWorldIds(state: unknown): string[] {
  if (!state || typeof state !== 'object' || !('package_versions' in state)) return []
  const versions = (state as { package_versions?: unknown }).package_versions
  if (!Array.isArray(versions)) return []
  return [...new Set(versions.filter((v): v is { package_id: string; package_type: string } =>
    Boolean(v && typeof v === 'object' && v.package_type === 'World' &&
      typeof v.package_id === 'string' && v.package_id.length > 0)
  ).map(v => v.package_id))].sort()
}
