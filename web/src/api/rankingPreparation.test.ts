import { afterEach, expect, it, vi } from 'vitest'
import { confirmRankingCommand, previewRankingCommand } from './client'
import type { RankingPreparationCommand, RankingPreparationPreview } from './rankingCandidates'
const command:RankingPreparationCommand = {command_id:'cmd',audit:{actor_label:'Operator',reason:'Review'},zero_versions:[],run_id:'run',branch_id:'branch',target_week:{season_index:0,week:1},policy:{policy_id:'policy',best_n:15},players:[],discipline:'stored_zeros'}
const preview:RankingPreparationPreview = {preview_only:true,request_fingerprint:'a'.repeat(64),candidate:{publication_status:'candidate_only',fingerprint:'b'.repeat(64),command_ids:['cmd'],snapshot:{run_id:'run',branch_id:'branch',week:{season_index:0,week:1},policy:{policy_id:'policy',best_n:15},rows:[]}}}
const response = (data:unknown) => ({ok:true,status:200,text:async () => JSON.stringify(data)})
afterEach(() => vi.unstubAllGlobals())
it('sends exact command JSON and the reviewed candidate fingerprint with JSON content type', async () => {
  const fetcher = vi.fn().mockResolvedValueOnce(response(preview)).mockResolvedValueOnce(response(preview.candidate))
  vi.stubGlobal('fetch',fetcher)
  expect(await previewRankingCommand('run','branch',command)).toEqual(preview)
  expect(await confirmRankingCommand('run','branch',command,preview)).toEqual(preview.candidate)
  expect(fetcher.mock.calls[1][1]).toMatchObject({method:'POST',body:JSON.stringify(command),headers:{'Content-Type':'application/json','X-Ranking-Preview-Fingerprint':preview.candidate.fingerprint,'X-Ranking-Preview-Request':preview.request_fingerprint}})
})
it.each(['scope','week','command','hash'])('rejects a mismatched %s response', async field => {
  const bad = structuredClone(preview.candidate)
  if (field === 'scope') bad.snapshot.branch_id = 'other'
  if (field === 'week') bad.snapshot.week.week = 2
  if (field === 'command') bad.command_ids = ['other']
  if (field === 'hash') bad.fingerprint = 'c'.repeat(64)
  vi.stubGlobal('fetch',vi.fn().mockResolvedValue(response(bad)))
  await expect(confirmRankingCommand('run','branch',command,preview)).rejects.toThrow()
})
