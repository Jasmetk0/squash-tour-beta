import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, expect, it, vi } from 'vitest'
import { LanguageProvider, useLanguage } from '../i18n/LanguageContext'
import { RankingPreparationPanel } from './RankingPreparationPanel'
import { RankingSavePanel } from './RankingSavePanel'
import { confirmRankingCommand, getRankingCandidateInputs, getRankingCandidateSources, previewRankingCommand, previewRankingSave, saveRankingPreparation } from '../api/client'
import type { RankingCandidateDetail, RankingPreparationCommand, RankingPreparationPreview } from '../api/rankingCandidates'

vi.mock('../api/client', async (importOriginal) => ({
  ...await importOriginal<typeof import('../api/client')>(),
  confirmRankingCommand: vi.fn(), getRankingCandidateInputs: vi.fn(),
  getRankingCandidateSources: vi.fn(), previewRankingCommand: vi.fn(),
  previewRankingSave: vi.fn(), saveRankingPreparation: vi.fn(),
}))

const latest: RankingCandidateDetail = {
  publication_status: 'candidate_only', fingerprint: 'a'.repeat(64),
  command_ids: ['old-command'],
  snapshot: { run_id: 'run', branch_id: 'branch', week: { season_index: 0, week: 2 },
    policy: { policy_id: 'policy-ref', best_n: 15 }, rows: [] },
}
const player = { player_id: 'player-1', tie_break_token: 'raw-token', tour_entry_week: { season_index: 0, week: 10 }, retired: false }
function previewFor(command: RankingPreparationCommand): RankingPreparationPreview {
  const context = 'context' in command ? command.context : command
  return { preview_only: true, request_fingerprint: 'b'.repeat(64), candidate: {
    ...latest, fingerprint: 'c'.repeat(64), command_ids: [command.command_id],
    snapshot: { ...latest.snapshot, week: context.target_week, policy: context.policy },
  } }
}
function SwitchLanguage() {
  const { setLanguage } = useLanguage()
  return <><button type="button" onClick={() => setLanguage('cs')}>Čeština</button>
    <button type="button" onClick={() => setLanguage('en')}>English</button></>
}
function show(head?: RankingCandidateDetail, save = false) {
  render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
    <LanguageProvider><SwitchLanguage />
      <RankingPreparationPanel runId="run" branchId="branch" latest={head} />
      {save && <RankingSavePanel runId="run" branchId="branch" />}
    </LanguageProvider>
  </QueryClientProvider>)
}
beforeEach(() => {
  localStorage.setItem('squash-engine-language-v1', 'en')
  vi.resetAllMocks()
  vi.mocked(previewRankingCommand).mockImplementation(async (_r, _b, command) => previewFor(command))
  vi.mocked(confirmRankingCommand).mockImplementation(async (_r, _b, _command, result) => result.candidate)
  vi.mocked(getRankingCandidateInputs).mockResolvedValue({
    run_id: 'run', branch_id: 'branch', week: latest.snapshot.week,
    candidate_fingerprint: latest.fingerprint, publication_status: 'candidate_only',
    verification_status: 'complete_manifest',
    manifest: { players: [player], results: [], zeros_from_history: true },
    zero_sources: [], zero_history_status: 'verified_stored_history',
  })
})

it('keeps initial form, audit, preview and exact command retry across CS/EN switching', async () => {
  vi.mocked(confirmRankingCommand).mockRejectedValueOnce(new Error('Connection lost'))
    .mockImplementation(async (_r, _b, _command, result) => result.candidate)
  show()
  await userEvent.click(screen.getByRole('button', { name: 'Prepare initial ranking' }))
  await userEvent.type(screen.getByLabelText('Policy reference'), 'custom-policy')
  await userEvent.click(screen.getByRole('button', { name: 'Add player' }))
  await userEvent.type(screen.getByLabelText('Player ID'), 'future-player')
  await userEvent.type(screen.getByLabelText('Operator label'), 'My operator')
  await userEvent.type(screen.getByLabelText('Reason'), 'Manual audit text')
  await userEvent.click(screen.getByLabelText('I reviewed the roster, target policy and decisions for this week.'))
  await userEvent.click(screen.getByRole('button', { name: 'Čeština' }))
  expect(screen.getByLabelText('Reference pravidel (policy)')).toHaveValue('custom-policy')
  expect(screen.getByLabelText('ID hráče')).toHaveValue('future-player')
  expect(screen.getByLabelText('Označení operátora')).toHaveValue('My operator')
  expect(screen.getByLabelText('Důvod změny')).toHaveValue('Manual audit text')
  expect(previewRankingCommand).not.toHaveBeenCalled()
  expect(confirmRankingCommand).not.toHaveBeenCalled()
  await userEvent.click(screen.getByRole('button', { name: 'Vypočítat náhled' }))
  expect(await screen.findByRole('region', { name: 'Náhled žebříčku' })).toBeVisible()
  const command = vi.mocked(previewRankingCommand).mock.calls[0][2]
  expect(command).toMatchObject({ policy: { policy_id: 'custom-policy', best_n: 15 },
    audit: { actor_label: 'My operator', reason: 'Manual audit text' } })
  await userEvent.click(screen.getByRole('button', { name: 'English' }))
  expect(screen.getByRole('region', { name: 'Ranking preview' })).toBeVisible()
  expect(previewRankingCommand).toHaveBeenCalledTimes(1)
  await userEvent.click(screen.getByRole('button', { name: 'Confirm candidate preparation' }))
  expect(await screen.findByRole('alert')).toHaveTextContent('Connection lost')
  await userEvent.click(screen.getByRole('button', { name: 'Čeština' }))
  await userEvent.click(screen.getByRole('button', { name: 'Zopakovat přesně stejnou přípravu' }))
  expect(await screen.findByText(/Kandidát je připraven/)).toBeVisible()
  expect(vi.mocked(confirmRankingCommand).mock.calls[1]).toEqual(vi.mocked(confirmRankingCommand).mock.calls[0])
  expect(saveRankingPreparation).not.toHaveBeenCalled()
})

it('preserves corrections, raw terminal enum and original timing through language switch', async () => {
  const source = {
    fingerprint: 's'.repeat(64), counted: false,
    version: { run_id: 'run', branch_id: 'branch', effective_week: latest.snapshot.week,
      previous_fingerprint: null,
      result: { edition_id: 'edition-1', player_id: 'player-1', source_fingerprint: 'old-result',
        qualification_points: 0, main_points: 12,
        completed_week: { season_index: 0, week: 1 }, first_publication_week: latest.snapshot.week,
        validity_weeks: 61, ranked: false, terminal_status: 'abandoned' as const },
    },
  }
  vi.mocked(getRankingCandidateSources).mockResolvedValue({
    run_id: 'run', branch_id: 'branch', week: latest.snapshot.week,
    candidate_fingerprint: latest.fingerprint, publication_status: 'candidate_only', sources: [source],
  })
  show(latest)
  await userEvent.click(screen.getByRole('button', { name: 'Prepare next ranking' }))
  await userEvent.click(await screen.findByRole('button', { name: 'Load stored results to correct' }))
  await userEvent.click(await screen.findByLabelText('Correct player-1 / edition-1'))
  await userEvent.clear(screen.getByLabelText('Corrected main points'))
  await userEvent.type(screen.getByLabelText('Corrected main points'), '25')
  await userEvent.selectOptions(screen.getByLabelText('Corrected terminal status'), 'completed')
  await userEvent.type(screen.getByLabelText('Result correction reference'), 'manual-source')
  await userEvent.click(screen.getByRole('button', { name: 'Čeština' }))
  expect(screen.getByLabelText('Opravené body hlavní soutěže')).toHaveValue(25)
  expect(screen.getByLabelText('Opravený konečný stav')).toHaveValue('completed')
  expect(screen.getByLabelText('Reference opravy výsledku')).toHaveValue('manual-source')
  expect(screen.getByText(/První zveřejnění: sezona 1, týden 2/)).toBeVisible()
  expect(getRankingCandidateSources).toHaveBeenCalledTimes(1)
  await userEvent.type(screen.getByLabelText('Označení operátora'), 'Operator')
  await userEvent.type(screen.getByLabelText('Důvod změny'), 'Appeal')
  await userEvent.click(screen.getByLabelText('Zkontroloval(a) jsem soupisku, cílová pravidla a rozhodnutí pro tento týden.'))
  await userEvent.click(screen.getByRole('button', { name: 'Vypočítat náhled' }))
  const cmd = vi.mocked(previewRankingCommand).mock.calls[0][2]
  expect(cmd).toMatchObject({ corrections: [{
    previous_fingerprint: source.fingerprint,
    result: { main_points: 25, terminal_status: 'completed', source_fingerprint: 'manual-source' },
  }] })
  expect('context' in cmd && cmd.context.players[0].tour_entry_week).toEqual({ season_index: 0, week: 10 })
  expect(confirmRankingCommand).not.toHaveBeenCalled()
  expect(saveRankingPreparation).not.toHaveBeenCalled()
})

it('switching language never opens Save, refreshes preview or writes an unconfirmed revision', async () => {
  vi.mocked(previewRankingSave).mockResolvedValue({
    run_id: 'run', branch_id: 'branch', ranking_fingerprint: 'd'.repeat(64),
    saved_head_revision_id: 'revision', draft_version: 1,
    has_unsaved_changes: true, can_save: true,
  })
  vi.mocked(saveRankingPreparation).mockResolvedValue({})
  show(undefined, true)
  await userEvent.click(screen.getByRole('button', { name: 'Čeština' }))
  expect(previewRankingSave).not.toHaveBeenCalled()
  expect(saveRankingPreparation).not.toHaveBeenCalled()
  await userEvent.click(screen.getByRole('button', { name: 'Zkontrolovat změny žebříčku' }))
  expect(await screen.findByText('Změny žebříčku jsou připraveny k uložení.')).toBeVisible()
  await userEvent.click(screen.getByRole('button', { name: 'English' }))
  expect(screen.getByText('Ranking changes are ready to save.')).toBeVisible()
  expect(previewRankingSave).toHaveBeenCalledTimes(1)
  expect(saveRankingPreparation).not.toHaveBeenCalled()
  await userEvent.click(screen.getByRole('button', { name: 'Save ranking preparation' }))
  expect(await screen.findByText('Ranking preparation saved.')).toBeVisible()
  expect(saveRankingPreparation).toHaveBeenCalledTimes(1)
  await userEvent.click(screen.getByRole('button', { name: 'Čeština' }))
  expect(screen.getByText('Příprava žebříčku byla uložena.')).toBeVisible()
  expect(saveRankingPreparation).toHaveBeenCalledTimes(1)
  // An explicit successful Save intentionally invalidates queries once; language changes do not.
  await waitFor(() => expect(previewRankingSave).toHaveBeenCalledTimes(2))
})

it('keeps a failed result source request read-only and retries only on explicit click after a switch', async () => {
  vi.mocked(getRankingCandidateSources).mockRejectedValueOnce(new Error('Network problem'))
    .mockResolvedValue({ run_id: 'run', branch_id: 'branch', week: latest.snapshot.week,
      candidate_fingerprint: latest.fingerprint, publication_status: 'candidate_only', sources: [] })
  show(latest)
  await userEvent.click(screen.getByRole('button', { name: 'Prepare next ranking' }))
  await userEvent.click(await screen.findByRole('button', { name: 'Load stored results to correct' }))
  expect(await screen.findByRole('alert')).toHaveTextContent('Network problem')
  await userEvent.click(screen.getByRole('button', { name: 'Čeština' }))
  expect(getRankingCandidateSources).toHaveBeenCalledTimes(1)
  await userEvent.click(screen.getByRole('button', { name: 'Znovu načíst zdroje výsledků' }))
  expect(await screen.findByText('Nejsou dostupné žádné uložené výsledky k opravě.')).toBeVisible()
  expect(getRankingCandidateSources).toHaveBeenCalledTimes(2)
  expect(previewRankingCommand).not.toHaveBeenCalled()
  expect(confirmRankingCommand).not.toHaveBeenCalled()
})

it.each([
  ['unchanged', { has_unsaved_changes: false, can_save: false }, 'Příprava žebříčku je již uložená.'],
  ['blocked', { has_unsaved_changes: true, can_save: false }, 'Uložení je zablokováno. Zkontrolujte oprávnění větve a nevyřízené změny konceptu.'],
] as const)('keeps %s save review read-only when switching language', async (_name, state, message) => {
  vi.mocked(previewRankingSave).mockResolvedValue({
    run_id: 'run', branch_id: 'branch', ranking_fingerprint: 'd'.repeat(64),
    saved_head_revision_id: 'saved-1', draft_version: 0, ...state,
  })
  show(undefined, true)
  await userEvent.click(screen.getByRole('button', { name: 'Review ranking changes' }))
  await screen.findByRole('button', { name: 'Save ranking preparation' })
  expect(screen.getByRole('button', { name: 'Save ranking preparation' })).toBeDisabled()
  await userEvent.click(screen.getByRole('button', { name: 'Čeština' }))
  expect(screen.getByText(message)).toBeVisible()
  expect(screen.getByRole('button', { name: 'Uložit přípravu žebříčku' })).toBeDisabled()
  expect(previewRankingSave).toHaveBeenCalledTimes(1)
  expect(saveRankingPreparation).not.toHaveBeenCalled()
  expect(previewRankingCommand).not.toHaveBeenCalled()
  expect(confirmRankingCommand).not.toHaveBeenCalled()
})

it('requires fresh explicit Save after an error; language switch never retries the failed write', async () => {
  const payload = {
    run_id: 'run', branch_id: 'branch', ranking_fingerprint: 'd'.repeat(64),
    saved_head_revision_id: 'saved-1', draft_version: 2,
    has_unsaved_changes: true, can_save: true,
  }
  vi.mocked(previewRankingSave).mockResolvedValue(payload)
  vi.mocked(saveRankingPreparation).mockRejectedValueOnce(new Error('Save connection lost'))
    .mockResolvedValue({})
  show(undefined, true)
  await userEvent.click(screen.getByRole('button', { name: 'Review ranking changes' }))
  await userEvent.click(await screen.findByRole('button', { name: 'Save ranking preparation' }))
  expect(await screen.findByRole('alert')).toHaveTextContent('Save connection lost')
  await waitFor(() => expect(previewRankingSave).toHaveBeenCalledTimes(2))
  expect(saveRankingPreparation).toHaveBeenCalledTimes(1)
  await userEvent.click(screen.getByRole('button', { name: 'Čeština' }))
  expect(screen.getByRole('alert')).toHaveTextContent('Uložení selhalo')
  expect(previewRankingSave).toHaveBeenCalledTimes(2)
  expect(saveRankingPreparation).toHaveBeenCalledTimes(1)
  await userEvent.click(screen.getByRole('button', { name: 'Obnovit kontrolu žebříčku' }))
  await waitFor(() => expect(previewRankingSave).toHaveBeenCalledTimes(3))
  expect(saveRankingPreparation).toHaveBeenCalledTimes(1)
  await userEvent.click(await screen.findByRole('button', { name: 'Uložit přípravu žebříčku' }))
  expect(await screen.findByText('Příprava žebříčku byla uložena.')).toBeVisible()
  expect(vi.mocked(saveRankingPreparation).mock.calls).toEqual([
    ['run', 'branch', payload], ['run', 'branch', payload],
  ])
})

it('preserves revised zero duration, original start, new zero and player token across language changes', async () => {
  const originalZero = {
    zero_id: 'old-zero', run_id: 'run', branch_id: 'branch', player_id: 'player-1',
    effective_week: { season_index: 0, week: 1 }, duration_weeks: 4,
    source_fingerprint: 'original-decision',
  }
  vi.mocked(getRankingCandidateInputs).mockResolvedValue({
    run_id: 'run', branch_id: 'branch', week: latest.snapshot.week,
    candidate_fingerprint: latest.fingerprint, publication_status: 'candidate_only',
    verification_status: 'complete_manifest',
    manifest: { players: [player], results: [], zeros_from_history: true, disciplinary_zeros: [originalZero] },
    zero_sources: [{ fingerprint: 'old-version', impact: 'reserves_slot',
      version: { effective_week: originalZero.effective_week, previous_fingerprint: null, zero: originalZero } }],
  })
  show(latest)
  await userEvent.click(screen.getByRole('button', { name: 'Prepare next ranking' }))
  expect(await screen.findByLabelText('Player ID')).toHaveValue('player-1')
  await userEvent.click(screen.getByLabelText('Change this duration'))
  await userEvent.clear(screen.getByLabelText('New duration in weeks'))
  await userEvent.type(screen.getByLabelText('New duration in weeks'), '2')
  await userEvent.type(screen.getByLabelText('Correction reference'), 'appeal-123')
  await userEvent.click(screen.getByRole('button', { name: 'Add disciplinary zero' }))
  await userEvent.selectOptions(screen.getByLabelText('Zero player'), 'player-1')
  await userEvent.type(screen.getByLabelText('Duration in weeks'), '3')
  await userEvent.type(screen.getByLabelText('Decision reference'), 'new-decision')
  await userEvent.type(screen.getByLabelText('Operator label'), 'Operator stays raw')
  await userEvent.type(screen.getByLabelText('Reason'), 'Reason stays raw')
  await userEvent.click(screen.getByRole('button', { name: 'Čeština' }))
  expect(screen.getByText(/Původní začátek 2000\/01 · Týden 1/)).toBeVisible()
  expect(screen.getByLabelText('Nová doba trvání v týdnech')).toHaveValue(2)
  expect(screen.getByLabelText('Reference opravy')).toHaveValue('appeal-123')
  expect(screen.getByLabelText('Hráč s nulou')).toHaveValue('player-1')
  expect(screen.getByLabelText('Doba trvání v týdnech')).toHaveValue(3)
  expect(screen.getByLabelText('Reference rozhodnutí')).toHaveValue('new-decision')
  expect(screen.getByLabelText('Stabilní token pro rozhodnutí shody')).toHaveValue('raw-token')
  expect(screen.getByLabelText('Označení operátora')).toHaveValue('Operator stays raw')
  await userEvent.click(screen.getByLabelText('Zkontroloval(a) jsem soupisku, cílová pravidla a rozhodnutí pro tento týden.'))
  await userEvent.click(screen.getByRole('button', { name: 'Vypočítat náhled' }))
  expect(await screen.findByRole('region', { name: 'Náhled žebříčku' })).toBeVisible()
  const command = vi.mocked(previewRankingCommand).mock.calls[0][2]
  expect(command.zero_versions).toEqual([
    { effective_week: { season_index: 0, week: 3 }, previous_fingerprint: null,
      zero: expect.objectContaining({ player_id: 'player-1', duration_weeks: 3, source_fingerprint: 'new-decision' }) },
    { effective_week: { season_index: 0, week: 3 }, previous_fingerprint: 'old-version',
      zero: { ...originalZero, duration_weeks: 2, source_fingerprint: 'appeal-123' } },
  ])
  expect(command.audit).toEqual({ actor_label: 'Operator stays raw', reason: 'Reason stays raw' })
  await userEvent.click(screen.getByRole('button', { name: 'English' }))
  expect(screen.getByRole('region', { name: 'Ranking preview' })).toBeVisible()
  expect(previewRankingCommand).toHaveBeenCalledTimes(1)
  expect(confirmRankingCommand).not.toHaveBeenCalled()
  expect(saveRankingPreparation).not.toHaveBeenCalled()
})

it('shows rollover target and season warning in both languages without changing the target payload', async () => {
  const lastWeek = { ...latest, snapshot: { ...latest.snapshot, week: { season_index: 0, week: 61 } } }
  vi.mocked(getRankingCandidateInputs).mockResolvedValue({
    run_id: 'run', branch_id: 'branch', week: lastWeek.snapshot.week,
    candidate_fingerprint: latest.fingerprint, publication_status: 'candidate_only',
    verification_status: 'complete_manifest',
    manifest: { players: [player], results: [], zeros_from_history: true },
    zero_sources: [],
  })
  show(lastWeek)
  await userEvent.click(screen.getByRole('button', { name: 'Prepare next ranking' }))
  expect(await screen.findByText(/Season boundary: explicitly review/)).toBeVisible()
  expect(screen.getByText(/Prepare 2001\/02 · Week 1/)).toBeVisible()
  await userEvent.click(screen.getByRole('button', { name: 'Čeština' }))
  expect(screen.getByText(/Hranice sezony: před výpočtem/)).toBeVisible()
  expect(screen.getByText(/Připravit 2001\/02 · Týden 1/)).toBeVisible()
  expect(screen.getByLabelText('ID hráče')).toHaveValue('player-1')
  await userEvent.type(screen.getByLabelText('Označení operátora'), 'Operator')
  await userEvent.type(screen.getByLabelText('Důvod změny'), 'Rollover checked')
  await userEvent.click(screen.getByLabelText('Zkontroloval(a) jsem soupisku, cílová pravidla a rozhodnutí pro tento týden.'))
  await userEvent.click(screen.getByRole('button', { name: 'Vypočítat náhled' }))
  expect(await screen.findByRole('region', { name: 'Náhled žebříčku' })).toBeVisible()
  const cmd = vi.mocked(previewRankingCommand).mock.calls[0][2]
  expect('context' in cmd && cmd.context.target_week).toEqual({ season_index: 1, week: 1 })
  expect(confirmRankingCommand).not.toHaveBeenCalled()
  expect(saveRankingPreparation).not.toHaveBeenCalled()
})

it('keeps loading and retry of prior candidate inputs read-only after a language switch', async () => {
  const response = {
    run_id: 'run', branch_id: 'branch', week: latest.snapshot.week,
    candidate_fingerprint: latest.fingerprint, publication_status: 'candidate_only' as const,
    verification_status: 'complete_manifest' as const,
    manifest: { players: [player], results: [], zeros_from_history: true },
    zero_sources: [],
  }
  vi.mocked(getRankingCandidateInputs).mockRejectedValueOnce(new Error('Input network unavailable'))
    .mockResolvedValue(response)
  show(latest)
  await userEvent.click(screen.getByRole('button', { name: 'Prepare next ranking' }))
  expect(await screen.findByRole('alert')).toHaveTextContent('Input network unavailable')
  await userEvent.click(screen.getByRole('button', { name: 'Čeština' }))
  expect(getRankingCandidateInputs).toHaveBeenCalledTimes(1)
  await userEvent.click(screen.getByRole('button', { name: 'Znovu načíst vstupy přípravy' }))
  expect(await screen.findByLabelText('ID hráče')).toHaveValue('player-1')
  expect(screen.getByLabelText('Stabilní token pro rozhodnutí shody')).toHaveValue('raw-token')
  expect(getRankingCandidateInputs).toHaveBeenCalledTimes(2)
  expect(previewRankingCommand).not.toHaveBeenCalled()
  expect(confirmRankingCommand).not.toHaveBeenCalled()
  expect(saveRankingPreparation).not.toHaveBeenCalled()
})

it('keeps unique numbered player-removal controls and unchanged tokens across locale changes', async () => {
  show()
  await userEvent.click(screen.getByRole('button', { name: 'Prepare initial ranking' }))
  await userEvent.click(screen.getByRole('button', { name: 'Add player' }))
  await userEvent.click(screen.getByRole('button', { name: 'Add player' }))
  const rawTokens = screen.getAllByLabelText('Stable tie-break token').map(input => (input as HTMLInputElement).value)
  expect(rawTokens).toHaveLength(2)
  expect(rawTokens[0]).not.toBe(rawTokens[1])
  expect(screen.getByRole('button', { name: 'Remove player 1' })).toBeVisible()
  expect(screen.getByRole('button', { name: 'Remove player 2' })).toBeVisible()
  await userEvent.click(screen.getByRole('button', { name: 'Čeština' }))
  expect(screen.getAllByLabelText('Stabilní token pro rozhodnutí shody').map(input => (input as HTMLInputElement).value)).toEqual(rawTokens)
  await userEvent.click(screen.getByRole('button', { name: 'Odebrat hráče 1' }))
  expect(screen.getByRole('button', { name: 'Odebrat hráče 1' })).toBeVisible()
  expect(screen.queryByRole('button', { name: 'Odebrat hráče 2' })).not.toBeInTheDocument()
  expect(screen.getByLabelText('Stabilní token pro rozhodnutí shody')).toHaveValue(rawTokens[1])
  expect(previewRankingCommand).not.toHaveBeenCalled()
  expect(confirmRankingCommand).not.toHaveBeenCalled()
  expect(saveRankingPreparation).not.toHaveBeenCalled()
})

it('localizes input-load error context without changing raw API diagnostics or retry count', async () => {
  vi.mocked(getRankingCandidateInputs).mockRejectedValueOnce(new Error('raw-input-diagnostic-42'))
  show(latest)
  await userEvent.click(screen.getByRole('button', { name: 'Prepare next ranking' }))
  expect(await screen.findByRole('alert')).toHaveTextContent('raw-input-diagnostic-42')
  await userEvent.click(screen.getByRole('button', { name: 'Čeština' }))
  expect(screen.getByRole('alert')).toHaveTextContent('Nepodařilo se načíst vstupy přípravy.')
  expect(screen.getByRole('alert')).toHaveTextContent('raw-input-diagnostic-42')
  expect(getRankingCandidateInputs).toHaveBeenCalledTimes(1)
  expect(previewRankingCommand).not.toHaveBeenCalled()
  expect(confirmRankingCommand).not.toHaveBeenCalled()
})

it('localizes preview error and retains form and audit for explicit recalculation', async () => {
  vi.mocked(previewRankingCommand).mockRejectedValueOnce(new Error('raw-preview-diagnostic-43'))
  show()
  await userEvent.click(screen.getByRole('button', { name: 'Prepare initial ranking' }))
  await userEvent.type(screen.getByLabelText('Policy reference'), 'raw-policy-43')
  await userEvent.type(screen.getByLabelText('Operator label'), 'raw-operator-43')
  await userEvent.type(screen.getByLabelText('Reason'), 'raw-audit-43')
  await userEvent.click(screen.getByLabelText('I reviewed the roster, target policy and decisions for this week.'))
  await userEvent.click(screen.getByRole('button', { name: 'Calculate preview' }))
  expect(await screen.findByRole('alert')).toHaveTextContent('raw-preview-diagnostic-43')
  await userEvent.click(screen.getByRole('button', { name: 'Čeština' }))
  expect(screen.getByRole('alert')).toHaveTextContent('Nepodařilo se vypočítat náhled žebříčku.')
  expect(screen.getByRole('alert')).toHaveTextContent('raw-preview-diagnostic-43')
  expect(screen.getByLabelText('Reference pravidel (policy)')).toHaveValue('raw-policy-43')
  expect(screen.getByLabelText('Označení operátora')).toHaveValue('raw-operator-43')
  expect(screen.getByLabelText('Důvod změny')).toHaveValue('raw-audit-43')
  expect(previewRankingCommand).toHaveBeenCalledTimes(1)
  expect(confirmRankingCommand).not.toHaveBeenCalled()
  expect(saveRankingPreparation).not.toHaveBeenCalled()
})

it('localizes failed Save review and does not try Save or refetch on language change', async () => {
  vi.mocked(previewRankingSave).mockRejectedValueOnce(new Error('raw-review-diagnostic-44'))
  show(undefined, true)
  await userEvent.click(screen.getByRole('button', { name: 'Review ranking changes' }))
  expect(await screen.findByRole('alert')).toHaveTextContent('raw-review-diagnostic-44')
  await userEvent.click(screen.getByRole('button', { name: 'Čeština' }))
  expect(screen.getByRole('alert')).toHaveTextContent('Nepodařilo se zkontrolovat uložení žebříčku.')
  expect(screen.getByRole('alert')).toHaveTextContent('raw-review-diagnostic-44')
  expect(previewRankingSave).toHaveBeenCalledTimes(1)
  expect(saveRankingPreparation).not.toHaveBeenCalled()
})
