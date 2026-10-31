import { render, screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import type { CanonicalTournamentPreparationState } from '../api/types'
import { RunTournamentNextActionPanel } from './RunTournamentNextActionPanel'
import { verifiedTournamentNavigation, type TournamentNavigationSections } from './runTournamentNextAction'

const fingerprint = 'ab'.repeat(32)
const evidence: CanonicalTournamentPreparationState = {
  schema_version: 'canonical_tournament_preparation_state.v1',
  run_id: 'run-1', branch_id: 'branch-1', event_id: 'edition-1',
  preparation_fingerprint: fingerprint,
  authority_source: 'run_owned_db_authorities.v1',
  phase: 'entry_field_required', next_required_action: 'build_entry_field',
  blockers: ['validated_submissions_missing'], ranking_snapshot_ready: true,
  entry_field_ready: false, draw_ready: false,
  ready_for_match_schedule: false, effective_draw_fingerprint: null
}
const mounted: TournamentNavigationSections = {
  'canonical-entry-timing': true, 'canonical-preparation': true,
  'canonical-entry-review': true, 'canonical-reviewed-entry-field': true,
  'canonical-main-draw-preflight': true, 'canonical-wc-review': true,
  'canonical-draw-authority': true, 'canonical-first-match': true,
  'finals-race-replacement': true
}
const derive = (source: CanonicalTournamentPreparationState, sections = mounted,
  lang: 'cs' | 'en' = 'en') =>
  verifiedTournamentNavigation(source, 'run-1', 'branch-1', 'edition-1', sections, lang)

const mount = (source: CanonicalTournamentPreparationState, sections = mounted,
  language: 'cs' | 'en' = 'en') => render(
    <RunTournamentNextActionPanel runId="run-1" branchId="branch-1"
      eventId="edition-1" preparation={source} sections={sections} language={language}/>
  )

describe('canonical tournament next-action navigation', () => {
  it('links the exact backend next action to its actual mounted Admin section', () => {
    const x = derive(evidence)
    expect(x?.next).toEqual({
      label: 'Build the field from reviewed applications', target: 'canonical-preparation'
    })
    mount(evidence)
    const link = screen.getByRole('link', {name:'Go to: Build the field from reviewed applications'})
    expect(link).toHaveAttribute('href','#canonical-preparation')
    expect(screen.getByText('validated_submissions_missing')).toBeInTheDocument()
    const milestones = screen.getByRole('list', {name:'Verified tournament milestones'})
    expect(within(milestones).getByText('Ranking Snapshot: confirmed')).toBeInTheDocument()
    expect(within(milestones).getByText('Entry Field: not confirmed')).toBeInTheDocument()
  })

  it('never advertises readiness merely because the backend next action is none', () => {
    const noAction = {...evidence, next_required_action:'none' as const}
    expect(derive(noAction)?.scheduleReady).toBe(false)
    expect(derive(noAction)?.next).toBeNull()
    mount(noAction)
    expect(screen.queryByRole('link', {name:/Open match preparation/})).not.toBeInTheDocument()
    expect(screen.getByText(/awaiting prerequisites/)).toBeInTheDocument()
  })

  it('shows a match-preparation link only with explicit ready evidence and a mounted target', () => {
    const ready = {...evidence, next_required_action:'none' as const,
      blockers:[], ready_for_match_schedule:true, phase:'draw_ready' as const}
    expect(derive(ready)?.next?.target).toBe('canonical-first-match')
    expect(derive(ready, {...mounted, 'canonical-first-match':false})?.next).toBeNull()
    mount(ready)
    expect(screen.getByRole('link',{name:'Go to: Open match preparation'}))
      .toHaveAttribute('href','#canonical-first-match')
  })

  it.each([
    ['adopt_ranking_snapshot','canonical-preparation'],
    ['review_finals_replacement','finals-race-replacement'],
    ['review_wild_cards','canonical-wc-review'],
    ['review_pre_draw_or_commit_draw_input','canonical-main-draw-preflight'],
    ['configure_tournament_format','canonical-preparation'],
    ['generate_tournament_topology','canonical-preparation'],
    ['prepare_group_match_schedule','canonical-preparation'],
    ['generate_draw','canonical-draw-authority']
  ] as const)('routes %s only to the matching mounted source section', (action, target) => {
    const t = {...evidence, next_required_action:action}
    expect(derive(t)?.next?.target).toBe(target)
    expect(derive(t,{...mounted,[target]:false})?.next).toBeNull()
  })

  it('never offers a link for a foreign Run, Branch, Edition or schema',()=>{
    const forgeries: CanonicalTournamentPreparationState[] = [
      {...evidence,run_id:'other'},
      {...evidence,branch_id:'other'},
      {...evidence,event_id:'other'},
      {...evidence,authority_source:'foreign' as CanonicalTournamentPreparationState['authority_source']},
      {...evidence,schema_version:'untrusted' as CanonicalTournamentPreparationState['schema_version']},
      {...evidence,preparation_fingerprint:'not-a-hash'},
      {...evidence,blockers:['']},
      {...evidence,next_required_action:'auto_accept_all' as CanonicalTournamentPreparationState['next_required_action']}
    ]
    for(const data of forgeries) expect(derive(data)).toBeNull()
    mount(forgeries[0])
    expect(screen.getByRole('alert')).toHaveTextContent('does not match this Run')
    expect(screen.queryByRole('link')).not.toBeInTheDocument()
  })

  it('renders Czech links without auto Save, approval or invented eligibility claims',()=>{
    mount({...evidence,next_required_action:'review_wild_cards'},mounted,'cs')
    expect(screen.getByRole('link',{name:/Otevřít: Prověřit divoké karty/}))
      .toHaveAttribute('href','#canonical-wc-review')
    expect(screen.getByText(/Nic neukládá ani nespouští/)).toBeInTheDocument()
    expect(screen.queryByRole('button')).not.toBeInTheDocument()
    expect(screen.queryByRole('form')).not.toBeInTheDocument()
  })

  it('does not link to hidden sections even when their ID is known',()=>{
    const sections = {...mounted, 'canonical-wc-review':false,'canonical-entry-timing':false}
    mount({...evidence,next_required_action:'review_wild_cards'},sections)
    expect(screen.queryByRole('link',{name:/Review Wild Cards/})).not.toBeInTheDocument()
    const nav = screen.getByRole('navigation',{name:'Go to tournament section'})
    expect(within(nav).queryByRole('link',{name:'Entry timing'})).not.toBeInTheDocument()
    expect(within(nav).queryByRole('link',{name:'Tournament preparation'})).toBeInTheDocument()
  })
})
