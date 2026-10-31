/** Entry-only HTTP boundary. Shared clients and their consumers retain their original contracts. */
import { ApiError } from './client'
import type { TournamentRankingPublicationOptions } from './types'

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) }
  })

  if (!response.ok) {
    const body = await response.text()
    throw new ApiError(body || 'Request failed', response.status)
  }

  if (response.status === 204) {
    return undefined as T
  }

  const text = await response.text()
  if (!text) {
    return undefined as T
  }
  return JSON.parse(text) as T
}

export async function listTournamentRankingPublicationOptions(
  runId: string,
  branchId: string,
  eventId: string
): Promise<TournamentRankingPublicationOptions> {
  const data = await request<TournamentRankingPublicationOptions>(
    '/admin/runs/' + encodeURIComponent(runId) + '/branches/' + encodeURIComponent(branchId) +
      '/tournaments/' + encodeURIComponent(eventId) + '/ranking-snapshot-authority/available'
  )
  const publications = data?.publications
  // The published list is server-owned input. Validate nested records before
  // the Admin picker creates select options or their stable week identities.
  const publicationWeeks = Array.isArray(publications) ? publications.map(item =>
    item?.ranking_week && Number.isSafeInteger(item.ranking_week.season_index) &&
    Number.isSafeInteger(item.ranking_week.week) &&
    item.ranking_week.season_index >= 0 && item.ranking_week.week >= 1
      ? item.ranking_week.season_index + ':' + item.ranking_week.week : null
  ) : []
  if (
    !data || data.run_id !== runId || data.branch_id !== branchId || data.event_id !== eventId ||
    data.source !== 'published_official_rankings.v1' ||
    !Number.isSafeInteger(data.publication_count) || data.publication_count < 0 ||
    !Array.isArray(publications) || data.publication_count !== publications.length ||
    publications.some(item =>
      !item || !item.ranking_week ||
      typeof item.snapshot_fingerprint !== 'string' ||
      !/^[0-9a-f]{64}$/.test(item.snapshot_fingerprint) ||
      !Number.isSafeInteger(item.ranking_week.season_index) ||
      !Number.isSafeInteger(item.ranking_week.week) ||
      item.ranking_week.season_index < 0 || item.ranking_week.week < 1 ||
      !Number.isSafeInteger(item.ranked_row_count) || item.ranked_row_count < 0 ||
      !Number.isSafeInteger(item.best_n) || item.best_n < 1 ||
      typeof item.policy_id !== 'string' || !item.policy_id.trim()) ||
    publicationWeeks.includes(null) ||
    new Set(publicationWeeks).size !== publicationWeeks.length
  ) {
    throw new Error('Published Official Ranking options do not match the requested tournament scope.')
  }
  return data
}

/** Run-owned Edition Entry preparation; preview and confirm NEVER call Working Draft Save. */
function editionEntryTimingRoot(run: string, branch: string, pkg: string, edition: string): string {
  return '/admin/runs/' + encodeURIComponent(run) +
    '/branches/' + encodeURIComponent(branch) +
    '/packages/calendar/' + encodeURIComponent(pkg) +
    '/editions/' + encodeURIComponent(edition) + '/entry-timing'
}

export async function getRunEditionEntryTiming(
  run: string, branch: string, pkg: string, edition: string
): Promise<import('./runEditionEntryTiming').EntryTimingInspection> {
  const data = await request<import('./runEditionEntryTiming').EntryTimingInspection>(
    editionEntryTimingRoot(run, branch, pkg, edition))
  const { validEntryTimingInspection } = await import('./runEditionEntryTiming')
  if (!validEntryTimingInspection(data, run, branch, pkg, edition))
    throw new Error('Edition Entry timing inspection has a foreign scope or invalid contract.')
  return data
}

export async function previewRunEditionEntryTiming(
  run: string, branch: string, pkg: string, edition: string,
  timing: import('./runEditionEntryTiming').EditionEntryTiming
): Promise<import('./runEditionEntryTiming').EntryTimingPreview> {
  const data = await request<import('./runEditionEntryTiming').EntryTimingPreview>(
    editionEntryTimingRoot(run, branch, pkg, edition) + '/preview',
    { method: 'POST', body: JSON.stringify({ timing }) })
  const { validEntryTimingInspection, sameTiming } = await import('./runEditionEntryTiming')
  if (!validEntryTimingInspection(data, run, branch, pkg, edition) || !data.preview_fingerprint ||
    !sameTiming(data.timing, timing))
    throw new Error('Edition Entry timing preview does not match the reviewed configuration and scope.')
  return data
}

export async function confirmRunEditionEntryTiming(
  run: string, branch: string, pkg: string, edition: string,
  payload: import('./runEditionEntryTiming').EntryTimingConfirmPayload
): Promise<import('./runEditionEntryTiming').EntryTimingReceipt> {
  const data = await request<import('./runEditionEntryTiming').EntryTimingReceipt>(
    editionEntryTimingRoot(run, branch, pkg, edition) + '/confirm',
    { method: 'POST', body: JSON.stringify(payload) })
  const { entryTimingScope, isHash, sameTiming, validEntryTimingInspection } = await import('./runEditionEntryTiming')
  if (!data || data.command_id !== payload.command_id || !isHash(data.receipt_fingerprint) ||
    !isHash(data.state_fingerprint) || !isHash(data.request_fingerprint) ||
    !Number.isSafeInteger(data.draft_version) || data.draft_version < 1 ||
    typeof data.already_applied !== 'boolean' ||
    (data.ranking_authority_fingerprint !== null && !isHash(data.ranking_authority_fingerprint)) ||
    !data.state || typeof data.state !== 'object' || Array.isArray(data.state) ||
    !entryTimingScope(data.request, run, branch, pkg, edition) ||
    data.request.kind !== 'run_edition_entry_timing.v1' ||
    data.request.expected_preview_fingerprint !== payload.expected_preview_fingerprint ||
    data.request.operator_label !== payload.operator_label ||
    data.request.audit_reason !== payload.audit_reason ||
    !sameTiming(data.request.timing, payload.timing) ||
    !validEntryTimingInspection(data.preview, run, branch, pkg, edition) ||
    !sameTiming(data.preview.timing, payload.timing) ||
    data.preview.preview_fingerprint !== payload.expected_preview_fingerprint ||
    data.state.run_id !== run || data.state.branch_id !== branch)
    throw new Error('Edition Entry timing receipt does not match the exact confirmed command.')
  return data
}
