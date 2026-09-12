import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, expect, it, vi } from 'vitest'
import { confirmRankingCommand, getRankingCandidateInputs, previewRankingCommand, previewRankingSave, saveRankingPreparation } from '../api/client'
import type { RankingCandidateDetail, RankingPreparationCommand, RankingPreparationPreview } from '../api/rankingCandidates'
import { RankingPreparationPanel, nextRankingWeek } from './RankingPreparationPanel'
import { RankingSavePanel } from './RankingSavePanel'
vi.mock('../api/client', async importOriginal => ({...await importOriginal<typeof import('../api/client')>(),confirmRankingCommand:vi.fn(),getRankingCandidateInputs:vi.fn(),previewRankingCommand:vi.fn(),previewRankingSave:vi.fn(),saveRankingPreparation:vi.fn()}))
const player = {player_id:'p',tie_break_token:'stable',tour_entry_week:{season_index:0,week:1},retired:false}
const latest:RankingCandidateDetail = {publication_status:'candidate_only',fingerprint:'a'.repeat(64),command_ids:['previous'],snapshot:{run_id:'run',branch_id:'branch',week:{season_index:0,week:1},policy:{policy_id:'policy',best_n:15},rows:[]}}
function result(command:RankingPreparationCommand):RankingPreparationPreview {
  const context = 'context' in command ? command.context : command
  return {preview_only:true,request_fingerprint:'b'.repeat(64),candidate:{...latest,fingerprint:'c'.repeat(64),command_ids:[command.command_id],snapshot:{...latest.snapshot,week:context.target_week,policy:context.policy}}}
}
function show(head?:RankingCandidateDetail, save=false) {
  return render(<QueryClientProvider client={new QueryClient({defaultOptions:{queries:{retry:false}}})}><RankingPreparationPanel runId="run" branchId="branch" latest={head}/>{save && <RankingSavePanel runId="run" branchId="branch"/>}</QueryClientProvider>)
}
async function audit() {
  await userEvent.type(screen.getByLabelText('Operator label'),'Operator')
  await userEvent.type(screen.getByLabelText('Reason'),'Reviewed inputs')
  await userEvent.click(screen.getByLabelText('I reviewed the roster, target policy and decisions for this week.'))
}
beforeEach(() => {
  vi.resetAllMocks()
  vi.mocked(previewRankingCommand).mockImplementation(async (_r,_b,c) => result(c))
  vi.mocked(confirmRankingCommand).mockImplementation(async (_r,_b,_c,p) => p.candidate)
  vi.mocked(getRankingCandidateInputs).mockResolvedValue({run_id:'run',branch_id:'branch',week:latest.snapshot.week,candidate_fingerprint:latest.fingerprint,publication_status:'candidate_only',verification_status:'complete_manifest',manifest:{players:[player],results:[],zeros_from_history:true},zero_history_status:'verified_stored_history',zero_sources:[]})
})

it('previews an initial roster and zero, explicitly confirms, then offers Save', async () => {
  vi.mocked(previewRankingSave).mockResolvedValue({run_id:'run',branch_id:'branch',ranking_fingerprint:'d'.repeat(64),saved_head_revision_id:'revision',draft_version:1,has_unsaved_changes:true,can_save:true})
  vi.mocked(saveRankingPreparation).mockResolvedValue({})
  show(undefined,true)
  await userEvent.click(screen.getByRole('button',{name:'Prepare initial ranking'}))
  await userEvent.type(screen.getByLabelText('Policy reference'),'policy')
  await userEvent.click(screen.getByRole('button',{name:'Add player'}))
  await userEvent.type(screen.getByLabelText('Player ID'),'p')
  await userEvent.click(screen.getByRole('button',{name:'Add disciplinary zero'}))
  await userEvent.selectOptions(screen.getByLabelText('Zero player'),'p')
  await userEvent.type(screen.getByLabelText('Duration in weeks'),'3')
  await userEvent.type(screen.getByLabelText('Decision reference'),'decision-1')
  await audit()
  await userEvent.click(screen.getByRole('button',{name:'Calculate preview'}))
  await screen.findByRole('region',{name:'Ranking preview'})
  expect(confirmRankingCommand).not.toHaveBeenCalled()
  const command = vi.mocked(previewRankingCommand).mock.calls[0][2]
  expect(command).toMatchObject({run_id:'run',branch_id:'branch',target_week:{season_index:0,week:1},zero_versions:[{zero:{player_id:'p',duration_weeks:3,source_fingerprint:'decision-1'}}]})
  expect(screen.getByLabelText('Policy reference')).toBeDisabled()
  await userEvent.click(screen.getByRole('button',{name:'Confirm candidate preparation'}))
  expect(await screen.findByText(/Candidate prepared. Review ranking changes/)).toBeVisible()
  expect(confirmRankingCommand).toHaveBeenCalledWith('run','branch',command,result(command))
  expect(saveRankingPreparation).not.toHaveBeenCalled()
  await userEvent.click(screen.getByRole('button',{name:'Review ranking changes'}))
  await userEvent.click(await screen.findByRole('button',{name:'Save ranking preparation'}))
  expect(await screen.findByText('Ranking preparation saved.')).toBeVisible()
})

it('prefills weekly inputs and preserves the original zero start during correction', async () => {
  const zero = {zero_id:'zero',run_id:'run',branch_id:'branch',player_id:'p',effective_week:{season_index:0,week:1},duration_weeks:4,source_fingerprint:'original'}
  vi.mocked(getRankingCandidateInputs).mockResolvedValue({run_id:'run',branch_id:'branch',week:latest.snapshot.week,candidate_fingerprint:latest.fingerprint,publication_status:'candidate_only',verification_status:'complete_manifest',manifest:{players:[player],results:[],zeros_from_history:true,disciplinary_zeros:[zero]},zero_sources:[{fingerprint:'e'.repeat(64),impact:'reserves_slot',version:{effective_week:zero.effective_week,previous_fingerprint:null,zero}}]})
  show(latest)
  await userEvent.click(screen.getByRole('button',{name:'Prepare next ranking'}))
  expect(await screen.findByLabelText('Player ID')).toHaveValue('p')
  await userEvent.click(screen.getByLabelText('Change this duration'))
  await userEvent.clear(screen.getByLabelText('New duration in weeks'))
  await userEvent.type(screen.getByLabelText('New duration in weeks'),'1')
  await userEvent.type(screen.getByLabelText('Correction reference'),'appeal')
  await audit()
  await userEvent.click(screen.getByRole('button',{name:'Calculate preview'}))
  await screen.findByRole('region',{name:'Ranking preview'})
  expect(vi.mocked(previewRankingCommand).mock.calls[0][2]).toMatchObject({context:{completed_week:{season_index:0,week:1},target_week:{season_index:0,week:2},players:[player]},zero_versions:[{effective_week:{season_index:0,week:2},previous_fingerprint:'e'.repeat(64),zero:{effective_week:{season_index:0,week:1},duration_weeks:1,source_fingerprint:'appeal'}}]})
})

it('keeps the exact reviewed request for retry after a lost confirmation response', async () => {
  vi.mocked(confirmRankingCommand).mockRejectedValueOnce(new Error('Connection lost')).mockImplementation(async (_r,_b,_c,p) => p.candidate)
  show()
  await userEvent.click(screen.getByRole('button',{name:'Prepare initial ranking'}))
  await userEvent.type(screen.getByLabelText('Policy reference'),'policy')
  await audit()
  await userEvent.click(screen.getByRole('button',{name:'Calculate preview'}))
  await userEvent.click(await screen.findByRole('button',{name:'Confirm candidate preparation'}))
  expect(await screen.findByRole('alert')).toHaveTextContent('Connection lost')
  expect(confirmRankingCommand).toHaveBeenCalledTimes(1)
  await userEvent.click(screen.getByRole('button',{name:'Retry this exact preparation'}))
  await screen.findByText(/Candidate prepared/)
  expect(vi.mocked(confirmRankingCommand).mock.calls[1]).toEqual(vi.mocked(confirmRankingCommand).mock.calls[0])
})

it('requires a new preview after editing the reviewed inputs', async () => {
  show()
  await userEvent.click(screen.getByRole('button',{name:'Prepare initial ranking'}))
  await userEvent.type(screen.getByLabelText('Policy reference'),'policy')
  await audit()
  await userEvent.click(screen.getByRole('button',{name:'Calculate preview'}))
  await userEvent.click(await screen.findByRole('button',{name:'Edit inputs and recalculate'}))
  expect(screen.queryByRole('button',{name:'Confirm candidate preparation'})).not.toBeInTheDocument()
  expect(screen.getByRole('button',{name:'Calculate preview'})).toBeDisabled()
  await userEvent.clear(screen.getByLabelText('Best N'))
  await userEvent.type(screen.getByLabelText('Best N'),'5')
  await userEvent.click(screen.getByLabelText('I reviewed the roster, target policy and decisions for this week.'))
  await userEvent.click(screen.getByRole('button',{name:'Calculate preview'}))
  await screen.findByRole('region',{name:'Ranking preview'})
  const calls = vi.mocked(previewRankingCommand).mock.calls
  expect(calls[1][2].command_id).not.toBe(calls[0][2].command_id)
  expect('policy' in calls[1][2] && calls[1][2].policy.best_n).toBe(5)
})

it('does not use a late response after unmounting the branch form', async () => {
  let finish!: (value:RankingCandidateDetail) => void
  vi.mocked(confirmRankingCommand).mockImplementation(() => new Promise(resolve => {finish=resolve}))
  const view = show()
  await userEvent.click(screen.getByRole('button',{name:'Prepare initial ranking'}))
  await userEvent.type(screen.getByLabelText('Policy reference'),'policy')
  await audit()
  await userEvent.click(screen.getByRole('button',{name:'Calculate preview'}))
  await userEvent.click(await screen.findByRole('button',{name:'Confirm candidate preparation'}))
  view.unmount()
  const next = show()
  await act(async () => {finish(latest)})
  expect(screen.queryByText(/Candidate prepared/)).not.toBeInTheDocument()
  expect(screen.getByRole('button',{name:'Prepare initial ranking'})).toBeVisible()
  next.unmount()
})

it('blocks legacy missing manifests and allows input read retry', async () => {
  vi.mocked(getRankingCandidateInputs).mockResolvedValueOnce({run_id:'run',branch_id:'branch',week:latest.snapshot.week,candidate_fingerprint:latest.fingerprint,publication_status:'candidate_only',verification_status:'legacy_without_manifest',manifest:null})
  show(latest)
  await userEvent.click(screen.getByRole('button',{name:'Prepare next ranking'}))
  expect(await screen.findByRole('alert')).toHaveTextContent('legacy candidate has no complete roster')
  expect(previewRankingCommand).not.toHaveBeenCalled()
  await userEvent.click(screen.getByRole('button',{name:'Retry preparation inputs'}))
  await waitFor(() => expect(screen.getByLabelText('Player ID')).toHaveValue('p'))
})

it('stops at the final week and handles season rollover without adding a year', () => {
  expect(nextRankingWeek({season_index:0,week:61})).toEqual({season_index:1,week:1})
  expect(nextRankingWeek({season_index:49,week:60})).toEqual({season_index:49,week:61})
  expect(nextRankingWeek({season_index:49,week:61})).toBeNull()
  show({...latest,snapshot:{...latest.snapshot,week:{season_index:49,week:61}}})
  expect(screen.getByText(/No season 51 ranking can be created/)).toBeVisible()
  expect(screen.queryByRole('button',{name:'Prepare next ranking'})).not.toBeInTheDocument()
})
