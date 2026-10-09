import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import {
  getAuthoritativeMatchReplayContext,
  getAuthoritativeSimulationPosition,
  getBranchWorkingDraft,
  getCanonicalTournamentDrawAuthority,
  getCanonicalTournamentDrawState,
  getCanonicalTournamentEntryFieldState,
  getCanonicalTournamentPreparation,
  getRunContainer,
  inspectAuthoritativeMatchReconstruction,
  inspectAuthoritativeWeekSchedule,
  inspectAuthoritativeWeekSchedulePreflight,
  listAuthoritativeMatchReplays,
  listRunBranches,
  simulateAuthoritativeNextMatch
} from '../api/client'
import { verifiedGeneratedFirstDraw } from '../api/runFirstDrawReview'
import {
  verifiedMatchReplay, verifiedScheduledMatch,
  type ReviewedFirstMatchEvidence
} from '../api/runFirstMatchReview'
import { formatApiError } from '../utils/apiErrors'
import { SectionCard } from './RunScopedUi'

const sha = (value: unknown): value is string =>
  typeof value === 'string' && /^[a-f0-9]{64}$/.test(value)

export function RunFirstMatchPanel({ runId, branchId, eventId }: {
  runId: string; branchId: string; eventId: string
}): JSX.Element {
  const client = useQueryClient()
  const [selectedGroup, setSelectedGroup] = useState('')
  const [review, setReview] = useState<ReviewedFirstMatchEvidence | null>(null)
  const [approved, setApproved] = useState(false)
  const [result, setResult] = useState<{
    evidence: ReviewedFirstMatchEvidence
    winnerId: string
    loserId: string
    resultFingerprint: string
    totalRallies: number
  } | null>(null)
  const [notice, setNotice] = useState('')

  const runQuery = useQuery({
    queryKey: ['admin-run-container',runId],
    queryFn: () => getRunContainer(runId), retry:false
  })
  const branchesQuery = useQuery({
    queryKey: ['admin-run-branches',runId],
    queryFn: () => listRunBranches(runId), retry:false
  })
  const draftQuery = useQuery({
    queryKey: ['package-working-draft',runId,branchId],
    queryFn: () => getBranchWorkingDraft(runId,branchId), retry:false
  })
  const preparationQuery = useQuery({
    queryKey: ['canonical-tournament-preparation',runId,branchId,eventId],
    queryFn: () => getCanonicalTournamentPreparation(runId,branchId,eventId),
    retry:false
  })
  const fieldQuery = useQuery({
    queryKey: ['canonical-entry-field',runId,branchId,eventId],
    queryFn: () => getCanonicalTournamentEntryFieldState(runId,branchId,eventId),
    retry:false
  })
  const drawQuery = useQuery({
    queryKey: ['canonical-tournament-draw-state',runId,branchId,eventId],
    queryFn: () => getCanonicalTournamentDrawState(runId,branchId,eventId),
    retry:false
  })
  const drawAuthorityQuery = useQuery({
    queryKey: ['canonical-tournament-draw-authority',runId,branchId,eventId],
    queryFn: () => getCanonicalTournamentDrawAuthority(runId,branchId,eventId),
    enabled: drawQuery.data?.initial_draw_generated === true, retry:false
  })
  const schedulePreflightQuery = useQuery({
    queryKey: ['authoritative-simulation-week-schedule-preflight',runId,branchId],
    queryFn: () => inspectAuthoritativeWeekSchedulePreflight(runId,branchId),
    retry:false
  })
  const scheduleQuery = useQuery({
    queryKey: ['authoritative-simulation-week-schedule',runId,branchId],
    queryFn: () => inspectAuthoritativeWeekSchedule(runId,branchId),
    enabled:schedulePreflightQuery.data?.schedule_already_adopted === true,
    retry:false
  })
  const branch = branchesQuery.data?.run_branches.find(item =>
    item.run_id === runId && item.branch_id === branchId)
  const head = branch?.saved_head_revision_id ?? ''
  const draft = draftQuery.data?.run_id === runId &&
    draftQuery.data.branch_id === branchId ? draftQuery.data : null
  const writable = Boolean(runQuery.data?.run_id === runId &&
    runQuery.data.storage_kind === 'custom_local' &&
    !runQuery.data.read_only &&
    branch?.status === 'active' && !branch.read_only && head &&
    draft?.status === 'clean' && draft.base_saved_revision_id === head)
  const scheduleReady = Boolean(schedulePreflightQuery.data?.run_id === runId &&
    schedulePreflightQuery.data.branch_id === branchId &&
    schedulePreflightQuery.data.schedule_already_adopted === true &&
    scheduleQuery.data?.run_id === runId &&
    scheduleQuery.data.branch_id === branchId &&
    scheduleQuery.data.schedule?.schema_version === 'week_simulation_schedule.v2' &&
    sha(scheduleQuery.data.schedule_fingerprint))
  const field = fieldQuery.data?.run_id === runId && fieldQuery.data.branch_id === branchId &&
    fieldQuery.data.event_id === eventId ? fieldQuery.data : null
  const draw = drawQuery.data?.run_id === runId && drawQuery.data.branch_id === branchId &&
    drawQuery.data.event_id === eventId ? drawQuery.data : null
  const firstDrawVerified = Boolean(field && draw && draw.draw_input_fingerprint &&
    verifiedGeneratedFirstDraw(
      draw,drawAuthorityQuery.data,field,draw.draw_input_fingerprint,runId,branchId,eventId))
  const preparationReady = Boolean(preparationQuery.data?.run_id === runId &&
    preparationQuery.data.branch_id === branchId &&
    preparationQuery.data.event_id === eventId &&
    preparationQuery.data.authority_source === 'run_owned_db_authorities.v1' &&
    preparationQuery.data.phase === 'draw_ready' &&
    preparationQuery.data.ready_for_match_schedule &&
    preparationQuery.data.blockers.length === 0)
  const positionQuery = useQuery({
    queryKey: ['authoritative-simulation-position',runId,branchId],
    queryFn: () => getAuthoritativeSimulationPosition(runId,branchId),
    enabled: writable && scheduleReady && firstDrawVerified && preparationReady,
    retry:false
  })
  const position = positionQuery.data?.run_id === runId &&
    positionQuery.data.branch_id === branchId ? positionQuery.data : null
  const eligible = position?.current_slot_kind === 'match'
    ? position.eligible_match_ids : []
  const groupId = eligible.includes(selectedGroup) ? selectedGroup : eligible[0] ?? ''
  const matchQuery = useQuery({
    queryKey: ['authoritative-match-reconstruction-state',runId,branchId,groupId],
    queryFn: () => inspectAuthoritativeMatchReconstruction(runId,branchId,groupId),
    enabled:Boolean(writable && scheduleReady && firstDrawVerified &&
      preparationReady && groupId),retry:false
  })
  const match = verifiedScheduledMatch(
    position,matchQuery.data,scheduleQuery.data,runId,branchId,eventId,head)
    ? matchQuery.data : null
  const loading = [
    runQuery,branchesQuery,draftQuery,preparationQuery,fieldQuery,drawQuery,
    drawAuthorityQuery,schedulePreflightQuery,scheduleQuery,positionQuery,matchQuery
  ].some(query=>query.isFetching)
  const canReview = Boolean(writable && scheduleReady && firstDrawVerified &&
    preparationReady && match && position && !loading && !result)
  const currentReview = Boolean(review && canReview && draft && match && position && draw &&
    review.runId === runId && review.branchId === branchId && review.eventId === eventId &&
    review.head === head && review.draftVersion === draft.draft_version &&
    review.positionFingerprint === position.position_fingerprint &&
    review.week.season_index === position.current_week.season_index &&
    review.week.week === position.current_week.week &&
    review.groupId === match.group_id && review.matchId === match.match_id &&
    review.slotId === match.slot_id && review.slotOrdinal === position.slot_ordinal &&
    review.slotStartFingerprint === match.slot_start_fingerprint &&
    review.playerAId === match.player_a_id && review.playerBId === match.player_b_id &&
    review.drawFingerprint === draw.draw_authority_fingerprint &&
    review.scheduleFingerprint === scheduleQuery.data?.schedule_fingerprint)

  useEffect(() => {
    setReview(null);setApproved(false);setResult(null);setNotice('')
  }, [runId,branchId,eventId,head,position?.position_fingerprint,groupId])

  const simulate = useMutation({
    mutationFn: async (request: ReviewedFirstMatchEvidence) => {
      const [freshDraft,freshPosition,freshMatch,freshSchedule,freshDraw] = await Promise.all([
        getBranchWorkingDraft(runId,branchId),
        getAuthoritativeSimulationPosition(runId,branchId),
        inspectAuthoritativeMatchReconstruction(runId,branchId,request.groupId),
        inspectAuthoritativeWeekSchedule(runId,branchId),
        getCanonicalTournamentDrawState(runId,branchId,eventId)
      ])
      if (freshDraft.run_id !== runId || freshDraft.branch_id !== branchId ||
        freshDraft.base_saved_revision_id !== request.head ||
        freshDraft.status !== 'clean' ||
        freshDraft.draft_version !== request.draftVersion ||
        freshPosition.position_fingerprint !== request.positionFingerprint ||
        freshDraw.draw_authority_fingerprint !== request.drawFingerprint ||
        freshSchedule.schedule_fingerprint !== request.scheduleFingerprint ||
        !verifiedScheduledMatch(freshPosition,freshMatch,freshSchedule,runId,branchId,eventId,request.head) ||
        freshMatch.match_id !== request.matchId ||
        freshMatch.slot_start_fingerprint !== request.slotStartFingerprint ||
        freshMatch.player_a_id !== request.playerAId ||
        freshMatch.player_b_id !== request.playerBId)
        throw new Error('Match or timetable changed; inspect the latest authoritative slot before retrying.')
      const after = await simulateAuthoritativeNextMatch(runId,branchId,{
        command_id:request.commandId,
        run_id:runId,branch_id:branchId,
        expected_week:request.week,
        expected_position_fingerprint:request.positionFingerprint,
        expected_revision_id:request.head,
        group_id:request.groupId
      })
      if (after.run_id !== runId || after.branch_id !== branchId ||
        !sha(after.position_fingerprint) ||
        after.position_fingerprint === request.positionFingerprint)
        throw new Error('The match may have committed, but its position progression was not verified.')
      const [list,context] = await Promise.all([
        listAuthoritativeMatchReplays(runId,branchId,50),
        getAuthoritativeMatchReplayContext(runId,branchId,request.groupId)
      ])
      const replay = verifiedMatchReplay(list,context,request)
      if (!replay)
        throw new Error('The match may have committed, but the winner and stored rally replay could not be verified. Refresh before retrying.')
      return {evidence:request,...replay,after}
    },
    onSuccess: async (value) => {
      setReview(null);setApproved(false)
      setResult({
        evidence:value.evidence,winnerId:value.winnerId,loserId:value.loserId,
        resultFingerprint:value.resultFingerprint,totalRallies:value.totalRallies
      })
      setNotice('The authoritative match, winner and stored replay were verified. Save the updated Branch separately before closing this session.')
      await Promise.all([
        client.invalidateQueries({queryKey:['authoritative-simulation-position',runId,branchId]}),
        client.invalidateQueries({queryKey:['authoritative-simulation-week-schedule',runId,branchId]}),
        client.invalidateQueries({queryKey:['authoritative-match-reconstruction-state',runId,branchId]}),
        client.invalidateQueries({queryKey:['authoritative-match-replays',runId,branchId]}),
        client.invalidateQueries({queryKey:['canonical-tournament-preparation',runId,branchId,eventId]})
      ])
    },
    onError: async () => {
      setReview(null);setApproved(false)
      await client.invalidateQueries({queryKey:['authoritative-simulation-position',runId,branchId]})
    }
  })
  const simulationUrl = `/admin/runs/${encodeURIComponent(runId)}/simulate?branch=${encodeURIComponent(branchId)}`

  return <SectionCard title="First real match — reviewed simulation">
    <p className="status">Use only the frozen canonical Match slot: actual scheduled match identity, both real players, saved first Draw and current Run-owned sporting state. The existing match engine produces and commits the result; a verified replay supplies the actual winner.</p>
    {!writable && <p role="status">An active writable Product Run Branch with a clean Working Draft and Saved Revision head is required.</p>}
    {!firstDrawVerified && <p role="status">First generate and verify the authoritative initial knockout Draw above.</p>}
    {preparationQuery.error && <p role="alert" className="error">Tournament readiness unavailable: {formatApiError(preparationQuery.error)}</p>}
    {preparationQuery.data && !preparationReady && <p role="status">Tournament preparation has remaining blockers: {preparationQuery.data.blockers.join(', ') || preparationQuery.data.phase}.</p>}
    {schedulePreflightQuery.error && <p role="alert" className="error">Week Schedule preflight unavailable: {formatApiError(schedulePreflightQuery.error)}</p>}
    {schedulePreflightQuery.data && !scheduleReady && <p role="status">A verified adopted Week Simulation Schedule v2 is required before any match. {schedulePreflightQuery.data.blockers.join(', ') || 'Use the existing schedule proposal and reviewed adoption controls.'}</p>}
    {scheduleQuery.error && <p role="alert" className="error">Adopted schedule unavailable: {formatApiError(scheduleQuery.error)}</p>}
    <p><Link to={simulationUrl}>Open authoritative Week Schedule, simulation and Save controls</Link></p>
    {positionQuery.error && <p role="alert" className="error">Current sporting position unavailable: {formatApiError(positionQuery.error)}</p>}
    {position && position.current_slot_kind !== 'match' && <p role="status">The current global slot is {position.current_slot_kind ?? 'not active'}, not a competitive match. Resolve prior Entry/Week processing first.</p>}
    {position?.current_slot_kind === 'match' && eligible.length === 0 && <p role="status">No match is eligible to run in this current slot.</p>}
    {eligible.length > 0 && <label>Current eligible match
      <select aria-label="First actual match" value={groupId}
        onChange={e=>{setSelectedGroup(e.target.value);setReview(null);setApproved(false)}}>
        {eligible.map(id=><option key={id} value={id}>{id}</option>)}
      </select>
    </label>}
    {matchQuery.error && <p role="alert" className="error">Match identity unavailable: {formatApiError(matchQuery.error)}</p>}
    {matchQuery.data && !match && <p role="status">This eligible match does not belong to the selected event, current Week Schedule slot or saved revision. Open the corresponding tournament instead.</p>}
    {match && <section aria-label="Frozen first match identity">
      <p>Event {match.event_id} · Week {match.week.week} · Global slot {position?.slot_ordinal} · Match {match.match_id}</p>
      <p><strong>{match.player_a_id}</strong> vs. <strong>{match.player_b_id}</strong></p>
      <p className="status">Match identity, slot-start fingerprint and the current position must remain unchanged until the commit. No winner is predicted.</p>
      <button type="button" disabled={!canReview || simulate.isPending}
        onClick={()=>{
          if (!position || !draw || !scheduleQuery.data || !draft) return
          setReview({
            runId,branchId,eventId,head,draftVersion:draft.draft_version,
            positionFingerprint:position.position_fingerprint,
            week:position.current_week,
            groupId:match.group_id,matchId:match.match_id,slotId:match.slot_id,
            slotOrdinal:position.slot_ordinal!,slotStartFingerprint:match.slot_start_fingerprint,
            playerAId:match.player_a_id,playerBId:match.player_b_id,
            drawFingerprint:draw.draw_authority_fingerprint!,
            scheduleFingerprint:scheduleQuery.data.schedule_fingerprint!,
            commandId:`admin-first-real-match-${crypto.randomUUID()}`
          })
          setApproved(false)
        }}>Review first real match</button>
    </section>}
    {review && <section aria-label="Approve first match simulation">
      <h4>Confirm authoritative match execution</h4>
      <p>{review.playerAId} vs. {review.playerBId} · {review.eventId} · Slot {review.slotOrdinal}.</p>
      {!currentReview && <p role="alert" className="error">Match, Branch or authoritative position changed. Review again.</p>}
      <label><input type="checkbox" aria-label="Approve first real match" checked={approved}
        onChange={e=>setApproved(e.target.checked)}/>
        Simulate this exact match using the existing sporting engine.</label>
      <button type="button" disabled={!approved || !currentReview || simulate.isPending}
        onClick={()=>simulate.mutate(review)}>
        {simulate.isPending ? 'Simulating match…' : 'Simulate reviewed first match'}
      </button>
    </section>}
    {simulate.error && <p role="alert" className="error">Match execution/readback failed: {formatApiError(simulate.error)}. Inspect current position and replay before attempting another run.</p>}
    {result && <section aria-label="Verified first match result">
      <h4>Real stored match result</h4>
      <p>Match {result.evidence.matchId} · Winner <strong>{result.winnerId}</strong> · Loser {result.loserId}.</p>
      <p>{result.totalRallies} persisted rallies · Result fingerprint <code>{result.resultFingerprint}</code>.</p>
      <p className="status">This confirms an authoritative committed match and stored replay, not automatically completed rounds or ranking publication. Bracket progression follows the next canonical match/round processing.</p>
    </section>}
    {notice && <p role="status">{notice}</p>}
  </SectionCard>
}
