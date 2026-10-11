/** Production Run-owned generated InitialWorld request/review contracts. */
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
  keep_from_seed?: number | null
  keep_from_preview_fingerprint?: string | null
  keep_player_ids?: string[]
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
  const kept = request.generation.keep_player_ids ?? []
  if (kept.length > 0) {
    if (!Number.isSafeInteger(request.generation.keep_from_seed) ||
        request.generation.keep_from_seed === request.generation.seed ||
        !/^[0-9a-f]{64}$/.test(request.generation.keep_from_preview_fingerprint ?? '') ||
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
