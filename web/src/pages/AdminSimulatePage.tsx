import { Link } from 'react-router-dom'

import { LinkCard, LinkCardGrid } from '../components/LinkCardGrid'
import { SectionCard } from '../components/RunScopedUi'

export function AdminSimulatePage(): JSX.Element {
  const lastRunId = typeof window === 'undefined' ? null : window.localStorage.getItem('beta_engine:last_run_id')

  const levelCards: LinkCard[] = [
    {
      title: 'Match',
      description:
        'Simulate or manually enter one match result. Future controls support lock/unlock and downstream invalidation.',
      to: lastRunId ? `/admin/runs/${lastRunId}` : '/admin/runs#match'
    },
    {
      title: 'Round',
      description: 'Simulate all unlocked matches in a tournament round.',
      to: lastRunId ? `/admin/runs/${lastRunId}/events` : '/admin/runs#round'
    },
    {
      title: 'Tournament',
      description: 'Simulate or resimulate a tournament/event block, respecting locked/manual results.',
      to: lastRunId ? `/admin/runs/${lastRunId}/events` : '/admin/runs#tournament'
    },
    {
      title: 'Week',
      description: 'Simulate a season week. Multi-week tournaments may only advance the portion assigned to that week.',
      to: lastRunId ? `/admin/runs/${lastRunId}/calendar` : '/admin/runs#week'
    },
    {
      title: 'Season',
      description: 'Simulate rest of season or selected season-week range.',
      to: lastRunId ? `/admin/runs/${lastRunId}` : '/admin/runs#season'
    },
    {
      title: 'Full Timeline',
      description: 'Future high-risk action to simulate through 2039/40. Requires explicit confirmation when implemented.',
      to: '/admin/runs#timeline'
    }
  ]

  return (
    <section className="panel">
      <div className="page-intro">
        <h2>Simulate</h2>
        <p className="subtitle">Simulation launcher for match, round, tournament, week, season, and full timeline workflows.</p>
      </div>

      <SectionCard title="Transitional note">
        <p className="status">
          Top-level launcher is being aligned with the target simulation model. Real deterministic commands currently remain run-scoped in Run Detail and related run pages.
        </p>
      </SectionCard>

      <SectionCard title="Choose active run">
        <p>Open a run first. Simulation commands operate against an explicit run context.</p>
        <p>
          <Link to="/admin/runs">Open Runs</Link>
          {lastRunId ? (
            <>
              {' '}· Last opened run:{' '}
              <Link to={`/admin/runs/${lastRunId}`}>{lastRunId}</Link>
            </>
          ) : (
            <> · No run has been opened in this browser yet.</>
          )}
        </p>
      </SectionCard>

      <SectionCard title="Simulation levels">
        <LinkCardGrid cards={levelCards} />
      </SectionCard>

      <SectionCard title="Shortcut concepts">
        <ul className="dashboard-help-list">
          <li><strong>Next Match</strong> — Status: Existing in run detail. Advances one deterministic match in the selected run.</li>
          <li><strong>Next Round</strong> — Status: Existing in run detail. Advances all eligible matches in the current round.</li>
          <li><strong>Next Tournament</strong> — Status: Existing in run detail. Advances tournament scope within run context.</li>
          <li><strong>Next Week</strong> — Status: Existing in run detail. Needed separately because tournaments can span multiple weeks.</li>
          <li><strong>Rest of Season</strong> — Status: Run-scoped today. Full season command is available from run detail quick actions.</li>
          <li><strong>Full Timeline</strong> — Status: Planned. Not implemented as a top-level launcher action yet.</li>
        </ul>
      </SectionCard>

      <SectionCard title="Manual controls / locks (planned model)">
        <p className="status">
          Manual results and locks are future central launcher concepts unless already supported in run-scoped event/run pages.
        </p>
        <ul className="dashboard-help-list">
          <li>simulate</li>
          <li>resimulate</li>
          <li>resimulate unlocked</li>
          <li>enter manual result</li>
          <li>lock result</li>
          <li>unlock</li>
          <li>downstream invalidation</li>
        </ul>
      </SectionCard>

      <SectionCard title="Narrative / Outcome Locks (planned)">
        <p>Future narrative tooling will support deterministic guardrails and pre-simulation constraint previews.</p>
        <ul className="dashboard-help-list">
          <li>Soft Lock</li>
          <li>Hard Lock</li>
          <li>Winner Lock</li>
          <li>Round Lock</li>
          <li>Exact Match Lock</li>
          <li>Path Lock</li>
          <li>Estimated natural probability (future)</li>
        </ul>
        <p className="status">Example: Arebady must win Némarque Open 2030/31. Estimated natural probability: 42%. Status: Plausible.</p>
      </SectionCard>
    </section>
  )
}
