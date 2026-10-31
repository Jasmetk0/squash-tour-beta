import { useQueries, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'

import {
  getAuthoritativeSimulationPosition,
  getPreAlphaFaxEntryValidationPolicyGate,
  getSavedRevision
} from '../api/client'
import type {
  AuthoritativeSimulationPosition,
  PreAlphaFaxEntryValidationPolicyGate,
  RunBranch,
  RunContainer,
  SavedRevisionHistoryDetail
} from '../api/types'
import { formatApiError } from '../utils/apiErrors'
import { EmptyState, MetadataList, SectionCard } from './RunScopedUi'

type BranchReadinessPanelProps = {
  run: RunContainer
  branches: RunBranch[]
  locale?: 'cs' | 'en'
}

const content = {
  cs: {
    heading: "Stav starší simulace pro jednotlivé branche",
    description: "Tento přehled kontroluje pozici starší FAX simulace (50 sezón, 61 týdnů) a uloženou revizi každé branche. Chybějící pozice starší simulace neznamená, že nativní operace nad kalendářem Runu není dostupná. Každá operace vyžaduje vlastní kontrolu; zde se žádná simulace nespouští.",
    refresh: "Obnovit stav branchí",
    noBranches: "Tento Run zatím nemá žádné branche.",
    invalidInventory: "Identita seznamu branchí je neplatná nebo nejednoznačná.",
    viewer: "Viewer Branch",
    season: "Sezóna",
    week: "Týden",
    slot: "Aktuální slot",
    head: "Uložená revize HEAD",
    kind: "Typ uložené revize",
    transition: "Přechod týdne",
    notVerified: "Neověřeno",
    noSlot: "Žádný / nedostupný",
    none: "Žádná",
    transitionReady: "Engine hlásí připravenost",
    transitionNotReady: "Nepřipraveno",
    foreignRun: "Branch patří jinému Runu.",
    inactiveRun: "Run není aktivní.",
    readOnlyRun: "Run je pouze ke čtení.",
    inactiveBranch: "Branch není aktivní.",
    readOnlyBranch: "Branch je pouze ke čtení.",
    noHead: "Branch nemá uloženou hlavní revizi.",
    noRevision: "Bez uložené revize nelze zkontrolovat pozici starší simulace.",
    positionLoading: "Načítání pozice starší simulace…",
    positionError: "Pozice starší simulace není dostupná",
    positionInvalid: "Pozice starší simulace neodpovídá Runu, branchi nebo rozsahu 50 sezón a 61 týdnů.",
    revisionLoading: "Načítání uložené hlavní revize…",
    revisionError: "Uložená revize není dostupná",
    revisionInvalid: "Identita nebo stav hlavní uložené revize nesouhlasí.",
    gateLoading: "Kontrola pravidel přihlášek…",
    gateError: "Pravidla přihlášek nejsou dostupná",
    gateInvalid: "Identita pravidel přihlášek nesouhlasí.",
    branchUnavailable: "Branch není dostupná",
    blockers: "Překážky přechodu týdne",
    unresolved: "Vyhodnocení přihlášek vyžaduje výslovnou kontrolu Admina; pravidla automatické způsobilosti nejsou uzavřena.",
    inspect: "Otevřít kontrolu simulace a dostupných akcí",
    notInspected: "Připravenost simulace nebyla ověřena. Zkontroluj upozornění výše; tento přehled nespouští žádnou akci.",
    ariaPrefix: "Stav branche",
  },
  en: {
    heading: "Legacy Branch simulation status",
    description: "This view checks the legacy FAX 50-season, 61-week simulation position and each Branch's Saved Revision. A missing legacy position does not prove that a native Run-calendar operation is unavailable. Every action needs its own Branch-specific preflight; this view never starts a simulation.",
    refresh: "Refresh Branch operating status",
    noBranches: "No Branches exist in this Run.",
    invalidInventory: "Branch inventory identity is invalid or ambiguous.",
    viewer: "Viewer Branch",
    season: "Season",
    week: "Week",
    slot: "Current slot",
    head: "Saved Revision HEAD",
    kind: "Saved revision type",
    transition: "Week Transition",
    notVerified: "Not verified",
    noSlot: "None / unavailable",
    none: "None",
    transitionReady: "Reported ready by the engine",
    transitionNotReady: "Not ready",
    foreignRun: "Branch belongs to another Run.",
    inactiveRun: "Run is not active.",
    readOnlyRun: "Run is read-only.",
    inactiveBranch: "Branch is not active.",
    readOnlyBranch: "Branch is read-only.",
    noHead: "Branch has no saved head revision.",
    noRevision: "No saved revision; authoritative position cannot be inspected.",
    positionLoading: "Loading authoritative position…",
    positionError: "Authoritative position unavailable",
    positionInvalid: "Legacy simulation position does not match this Run, Branch, or its 50-season / 61-week bounds.",
    revisionLoading: "Loading saved revision head…",
    revisionError: "Saved revision head unavailable",
    revisionInvalid: "Saved revision head identity or head status is inconsistent.",
    gateLoading: "Checking entry-validation policy…",
    gateError: "Entry-validation policy unavailable",
    gateInvalid: "Entry-validation policy identity is inconsistent.",
    branchUnavailable: "Branch unavailable",
    blockers: "Week Transition blockers",
    unresolved: "Application validation requires explicit Admin review; automatic eligibility policy remains unresolved.",
    inspect: "Inspect authoritative simulation and available actions",
    notInspected: "Simulation readiness is not verified. Review the warnings above; no action is executed from this panel.",
    ariaPrefix: "Operating status for",
  }
} as const

const positionKey = (runId: string, branchId: string) =>
  ['admin-branch-operational-position', runId, branchId] as const
const revisionKey = (runId: string, branchId: string, revisionId: string | null) =>
  ['admin-branch-operational-revision', runId, branchId, revisionId] as const
const entryGateKey = (runId: string, branchId: string) =>
  ['admin-branch-operational-entry-gate', runId, branchId] as const

function validPosition(
  value: AuthoritativeSimulationPosition | undefined,
  runId: string,
  branchId: string
): value is AuthoritativeSimulationPosition {
  return Boolean(
    value && value.run_id === runId && value.branch_id === branchId &&
    Number.isInteger(value.current_week?.season_index) &&
    value.current_week.season_index >= 0 && value.current_week.season_index < 50 &&
    Number.isInteger(value.current_week?.week) &&
    value.current_week.week >= 1 && value.current_week.week <= 61 &&
    Array.isArray(value.transition_blockers) && value.transition_blockers.every(item => typeof item === 'string') &&
    typeof value.week_ready_for_transition === 'boolean' &&
    typeof value.current_slot_complete === 'boolean' &&
    typeof value.supported_tournament_complete === 'boolean' &&
    (value.current_slot_kind === 'entry' || value.current_slot_kind === 'match' || value.current_slot_kind === null) &&
    (value.slot_ordinal === null || (Number.isSafeInteger(value.slot_ordinal) && value.slot_ordinal! >= 0)) &&
    [value.unresolved_group_ids, value.eligible_match_ids, value.blocked_match_ids]
      .every(items => Array.isArray(items) && items.every(item => typeof item === 'string')) &&
    typeof value.position_fingerprint === 'string' && /^[0-9a-f]{64}$/.test(value.position_fingerprint) &&
    (value.terminal_sporting_fingerprint === null || (typeof value.terminal_sporting_fingerprint === 'string' && /^[0-9a-f]{64}$/.test(value.terminal_sporting_fingerprint)))
  )
}

function validRevision(
  value: SavedRevisionHistoryDetail | undefined,
  runId: string,
  branchId: string,
  revisionId: string | null
): value is SavedRevisionHistoryDetail {
  return Boolean(
    value && value.run_id === runId && value.branch_id === branchId &&
    value.revision_id === revisionId &&
    // The selected context can legitimately contain a source-owned fork HEAD.
    typeof value.revision_branch_id === 'string' && Boolean(value.revision_branch_id.trim()) &&
    value.is_branch_head === true &&
    typeof value.content_hash === 'string' && /^[0-9a-f]{64}$/.test(value.content_hash) &&
    value.content_hash_algorithm === 'sha256'
  )
}

function validEntryGate(
  value: PreAlphaFaxEntryValidationPolicyGate | undefined,
  runId: string,
  branchId: string,
  position: AuthoritativeSimulationPosition
): value is PreAlphaFaxEntryValidationPolicyGate {
  return Boolean(
    value && value.run_id === runId && value.branch_id === branchId &&
    value.current_week.season_index === position.current_week.season_index &&
    value.current_week.week === position.current_week.week &&
    value.current_position_fingerprint === position.position_fingerprint &&
    value.schema_version === 'pre_alpha_fax_entry_validation_policy_gate.v1' &&
    value.policy_id === 'automatic_application_eligibility_deadline.v1' &&
    value.policy_status === 'unresolved' &&
    value.master_status === 'open' &&
    value.blocks_unattended_release === true &&
    value.current_slot_kind === 'entry' &&
    value.current_slot_ordinal === position.slot_ordinal &&
    value.current_blocker_code !== 'current_slot_not_entry' &&
    typeof value.gate_fingerprint === 'string' && value.gate_fingerprint.length === 64
  )
}

function readinessReason(run: RunContainer, branch: RunBranch, locale: 'cs' | 'en'): string | null {
  const l = content[locale]
  if (branch.run_id !== run.run_id) return l.foreignRun
  if (run.status !== 'active') return l.inactiveRun
  if (run.read_only) return l.readOnlyRun
  if (branch.status !== 'active') return l.inactiveBranch
  if (branch.read_only) return l.readOnlyBranch
  if (!branch.saved_head_revision_id) return l.noHead
  return null
}

/** Read-only inspection. No mutation or simulated readiness inferred from legacy checkpoints. */
export function RunBranchReadinessPanel({ run, branches, locale = 'en' }: BranchReadinessPanelProps): JSX.Element {
  const l = content[locale]
  const client = useQueryClient()
  const inventoryValid = Array.isArray(branches) && branches.every(branch =>
    branch && typeof branch.branch_id === 'string' && Boolean(branch.branch_id.trim())
  ) && new Set(branches.map(branch => branch.branch_id)).size === branches.length
  const validBranches = inventoryValid ? branches : []
  const positions = useQueries({
    queries: validBranches.map(branch => ({
      queryKey: positionKey(run.run_id, branch.branch_id),
      queryFn: () => getAuthoritativeSimulationPosition(run.run_id, branch.branch_id),
      enabled: branch.run_id === run.run_id && Boolean(branch.saved_head_revision_id),
      retry: false
    }))
  })
  const revisions = useQueries({
    queries: validBranches.map(branch => ({
      queryKey: revisionKey(run.run_id, branch.branch_id, branch.saved_head_revision_id ?? null),
      queryFn: () => getSavedRevision(run.run_id, branch.branch_id, branch.saved_head_revision_id!),
      enabled: branch.run_id === run.run_id && Boolean(branch.saved_head_revision_id),
      retry: false
    }))
  })
  const gates = useQueries({
    queries: validBranches.map((branch, index) => {
      const position = positions[index]?.data
      return {
        queryKey: entryGateKey(run.run_id, branch.branch_id),
        queryFn: () => getPreAlphaFaxEntryValidationPolicyGate(run.run_id, branch.branch_id),
        enabled: validPosition(position, run.run_id, branch.branch_id) &&
          position.current_slot_kind === 'entry',
        retry: false
      }
    })
  })

  return (
    <SectionCard title={l.heading}>
      <p className="status">{l.description}</p>
      <button type="button" onClick={() => {
        void Promise.all([
          client.invalidateQueries({ queryKey: ['admin-branch-operational-position', run.run_id] }),
          client.invalidateQueries({ queryKey: ['admin-branch-operational-revision', run.run_id] }),
          client.invalidateQueries({ queryKey: ['admin-branch-operational-entry-gate', run.run_id] })
        ])
      }}>{l.refresh}</button>
      {!inventoryValid && <p role="alert" className="error">{l.invalidInventory}</p>}
      {inventoryValid && validBranches.length === 0 && <EmptyState message={l.noBranches} />}
      {validBranches.map((branch, index) => {
        const positionQuery = positions[index]
        const revisionQuery = revisions[index]
        const gateQuery = gates[index]
        const hasPosition = validPosition(positionQuery.data, run.run_id, branch.branch_id)
        const position = hasPosition ? positionQuery.data : null
        const hasRevision = validRevision(
          revisionQuery.data, run.run_id, branch.branch_id, branch.saved_head_revision_id ?? null
        )
        const revision = hasRevision ? revisionQuery.data : null
        const needsGate = position?.current_slot_kind === 'entry'
        const hasGate = Boolean(position && validEntryGate(gateQuery.data, run.run_id, branch.branch_id, position))
        const gate = hasGate ? gateQuery.data : null
        const blocker = readinessReason(run, branch, locale)
        const positionWarning = !branch.saved_head_revision_id
          ? l.noRevision
          : positionQuery.isPending
            ? l.positionLoading
            : positionQuery.error
              ? `${l.positionError}: ${formatApiError(positionQuery.error)}`
              : !position
                ? l.positionInvalid
                : null
        const revisionWarning = !branch.saved_head_revision_id
          ? null
          : revisionQuery.isPending
            ? l.revisionLoading
            : revisionQuery.error
              ? `${l.revisionError}: ${formatApiError(revisionQuery.error)}`
              : !revision
                ? l.revisionInvalid
                : null
        const gateWarning = !needsGate
          ? null
          : gateQuery.isPending
            ? l.gateLoading
            : gateQuery.error
              ? `${l.gateError}: ${formatApiError(gateQuery.error)}`
              : !gate
                ? l.gateInvalid
                : null
        const canInspect = !blocker && position && revision && (!needsGate || gate)
        return (
          <article className="panel nested-panel" aria-label={`${l.ariaPrefix} ${branch.branch_id}`} key={branch.branch_id}>
            <h4>{branch.display_name} {branch.branch_id === (run.viewer_branch_id ?? run.official_branch_id) && <span className="status">{l.viewer}</span>}</h4>
            <MetadataList items={[
              { label: 'Branch ID', value: branch.branch_id },
              { label: l.season, value: position ? `${2000 + position.current_week.season_index}/${2001 + position.current_week.season_index}` : l.notVerified },
              { label: l.week, value: position ? `W${position.current_week.week} / 61` : l.notVerified },
              { label: l.slot, value: position?.current_slot_kind ?? l.noSlot },
              { label: l.head, value: branch.saved_head_revision_id ?? l.none },
              { label: l.kind, value: revision?.kind ?? l.notVerified },
              { label: l.transition, value: position ? (
                position.week_ready_for_transition && position.transition_blockers.length === 0
                  ? l.transitionReady
                  : l.transitionNotReady
              ) : l.notVerified }
            ]} />
            {blocker && <p role="alert" className="error">{l.branchUnavailable}: {blocker}</p>}
            {positionWarning && <p role="status">{positionWarning}</p>}
            {revisionWarning && <p role="status">{revisionWarning}</p>}
            {gateWarning && <p role="status">{gateWarning}</p>}
            {position?.transition_blockers.length ? (
              <div>
                <strong>{l.blockers}</strong>
                <ul>{position.transition_blockers.map((reason, index) => <li key={index}>{reason}</li>)}</ul>
              </div>
            ) : null}
            {needsGate && gate && gate.current_blocker_code === 'application_validation_policy_unresolved' && (
              <p role="alert" className="error">
                {l.unresolved}
              </p>
            )}
            {canInspect ? (
              <Link to={`/admin/runs/${encodeURIComponent(run.run_id)}/simulate?branch=${encodeURIComponent(branch.branch_id)}`}>
                {l.inspect}
              </Link>
            ) : (
              <p className="status">{l.notInspected}</p>
            )}
          </article>
        )
      })}
    </SectionCard>
  )
}
