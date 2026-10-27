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
  await waitFor(() => expect(previewRankingSave).toHaveBeenCalledTimes(1))
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
