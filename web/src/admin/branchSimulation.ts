import {
  simulateFullSeasonOnBranch, simulateNextMatchOnBranch, simulateNextRoundOnBranch,
  simulateNextTournamentOnBranch, simulateNextWeekOnBranch, simulateWorldTourFinalsOnBranch
} from '../api/client'
import type { AdminBranchExecutionResponse, AdminBranchSimulationRequest, BranchCheckpoint, BranchState, RunBranch, RunContainer } from '../api/types'

export type BranchSimulationAction = 'next_match' | 'next_round' | 'next_week' | 'next_tournament' | 'full_season' | 'world_tour_finals'

export const simulationActions = {
  next_match: { label: 'Next Match', buttonLabel: 'Simulate Next Match', confirmationLabel: 'Confirm Simulate Next Match', expectedMode: 'simulate_next_match', explanation: 'Exactly one match progression command will run on the selected Branch.', replayText: 'The previously completed Next Match command was returned. No duplicate match was simulated.' },
  next_round: { label: 'Next Round', buttonLabel: 'Simulate Next Round', confirmationLabel: 'Confirm Simulate Next Round', expectedMode: 'simulate_next_round', explanation: 'The engine will use its existing Next Round semantics. This may simulate multiple matches and may complete the current round or tournament.', replayText: 'The previously completed Next Round command was returned. No duplicate round progression was simulated.' },
  next_week: { label: 'Next Week', buttonLabel: 'Simulate Next Week', confirmationLabel: 'Confirm Simulate Next Week', expectedMode: 'simulate_next_week', explanation: 'The engine will use its existing Next Week semantics. It may finalize a currently active tournament and then simulate every consecutive event belonging to the next calendar week group. One command may therefore complete multiple tournaments.', replayText: 'The previously completed Next Week command was returned. No duplicate week progression was simulated.' },
  next_tournament: { label: 'Next Tournament', buttonLabel: 'Simulate Next Tournament', confirmationLabel: 'Confirm Simulate Next Tournament', expectedMode: 'simulate_next_tournament', explanation: 'The engine will use its existing Next Tournament semantics. If a tournament is currently active, that tournament will be finalized and no additional tournament will be simulated. Otherwise, exactly the next calendar tournament will be simulated and completed.', replayText: 'The previously completed Next Tournament command was returned. No duplicate tournament progression was simulated.' },
  full_season: { label: 'Full Season', buttonLabel: 'Simulate Full Season', confirmationLabel: 'Confirm Simulate Full Season', expectedMode: 'simulate_full_season', explanation: 'The engine will finalize any currently active tournament and then complete every remaining calendar event in the selected Branch’s current season. It will not simulate World Tour Finals, perform season rollover, bootstrap the next season, or advance another season.', replayText: 'The previously completed Full Season command was returned. No duplicate season progression was simulated.' },
  world_tour_finals: { label: 'World Tour Finals', buttonLabel: 'Simulate World Tour Finals', confirmationLabel: 'Confirm Simulate World Tour Finals', expectedMode: 'simulate_world_tour_finals', explanation: 'The engine will simulate the deterministic World Tour Finals for the selected Branch after its regular-season calendar is complete. Finals qualification and the Finals result will be persisted atomically. SeasonState and its current locator remain unchanged, but the Branch head advances. This command does not perform season rollover or create the next season.', replayText: 'The previously completed World Tour Finals command was returned. No duplicate Finals event was simulated.' }
} as const

const executionHeadKinds = new Set(['initial', 'current_state_capture', 'branch_fork_start'])

export function executeBranchSimulation(action: BranchSimulationAction, runId: string, branchId: string, payload: AdminBranchSimulationRequest): Promise<AdminBranchExecutionResponse> {
  switch (action) {
    case 'next_match': return simulateNextMatchOnBranch(runId, branchId, payload)
    case 'next_round': return simulateNextRoundOnBranch(runId, branchId, payload)
    case 'next_week': return simulateNextWeekOnBranch(runId, branchId, payload)
    case 'next_tournament': return simulateNextTournamentOnBranch(runId, branchId, payload)
    case 'full_season': return simulateFullSeasonOnBranch(runId, branchId, payload)
    case 'world_tour_finals': return simulateWorldTourFinalsOnBranch(runId, branchId, payload)
  }
}

export function simulationEligibility(run: RunContainer | undefined, branch: RunBranch, state: BranchState | undefined, checkpoints: BranchCheckpoint[]): string | null {
  if (!run) return 'Product Run is missing.'
  if (run.status !== 'active') return 'Product Run must be active.'
  if (run.read_only) return 'Product Run is read-only.'
  if (run.storage_kind === 'built_in') return 'Built-in Product Runs cannot execute simulation.'
  if (branch.run_id !== run.run_id) return 'Branch belongs to another Product Run.'
  if (branch.status !== 'active') return 'Branch must be active.'
  if (branch.read_only) return 'Branch is read-only.'
  if (!branch.legacy_simulation_run_id?.trim()) return 'Branch has no legacy simulation run binding.'
  if (!branch.head_checkpoint_id?.trim()) return 'Branch has no head checkpoint.'
  if (!state) return 'BranchState is missing.'
  if (state.run_id !== run.run_id) return 'BranchState belongs to another Product Run.'
  if (state.branch_id !== branch.branch_id) return 'BranchState belongs to another Branch.'
  if (state.head_checkpoint_id !== branch.head_checkpoint_id) return 'Branch and BranchState heads disagree.'
  const checkpoint = checkpoints.find(item => item.checkpoint_id === branch.head_checkpoint_id)
  if (!checkpoint) return 'Effective head checkpoint is missing.'
  if (checkpoint.branch_id !== branch.branch_id) return 'Checkpoint belongs to another Branch.'
  if (checkpoint.run_id !== run.run_id) return 'Checkpoint belongs to another Product Run.'
  if (!executionHeadKinds.has(checkpoint.kind)) return 'Checkpoint kind is not supported for Branch simulation execution.'
  return null
}

export function responseMode(result: AdminBranchExecutionResponse): string {
  return 'finals' in result ? 'simulate_world_tour_finals' : result.simulation_result.mode
}

export function validExecutionResponse(result: AdminBranchExecutionResponse, action: BranchSimulationAction, runId: string, branchId: string, reviewedHead: string): boolean {
  return result.product_run_id === runId && result.branch_id === branchId
    && result.previous_head_checkpoint_id === reviewedHead && Boolean(result.new_head_checkpoint_id)
    && result.official_branch_changed === false && responseMode(result) === simulationActions[action].expectedMode
}

export function newCommandId(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') return crypto.randomUUID()
  return `simulation-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 12)}`
}
