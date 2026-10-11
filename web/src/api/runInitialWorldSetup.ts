/** Production Run-owned generated InitialWorld request/review contracts. */
export type RunInitialWorldGeneration = {
  world_package_id: string
  season: '2000/2001'
  seed: number
  target_pool_size: number
  country_code?: string | null
  region?: string | null
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
  regions: string[]
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
      data.regions.includes(country.travel_region))
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

export function verifiedInitialWorldPreview(
  value: RunInitialWorldPreview,
  runId: string,
  branchId: string,
  request: RunInitialWorldAdoption
): boolean {
  const state = value?.state
  const players = state?.players
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
    players.every(player => typeof player.player_id === 'string' && player.player_id.length > 0 &&
      typeof player.name === 'string' && typeof player.country_code === 'string' &&
      (!request.generation.country_code ||
        player.country_code === request.generation.country_code) &&
      (!request.generation.region || player.country_code.length === 3)) &&
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
