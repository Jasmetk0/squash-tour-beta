import { Link } from 'react-router-dom'

const workflowSteps = [
  'Select Season',
  'View Expected Intake',
  'Generate Preview',
  'Review Preview',
  'Lock / edit / customize',
  'Persist Intake',
  'Regenerate Unlocked'
]

const statuses = ['Not generated', 'Preview generated', 'Persisted', 'Locked / finalized']

const rules = [
  'Preview does not write final player records.',
  'Persist writes players into Player Database / run data.',
  'Custom players default locked.',
  'Custom/locked players count against country-season talent budget.',
  'Custom/locked players should strongly reduce another same-cohort top-tier output chance, but not force absolute zero.'
]

export function TalentIntakePage(): JSX.Element {
  return (
    <section className="panel">
      <div className="page-intro">
        <h2>Talent Intake</h2>
        <p className="subtitle">Seasonal 15-year-old player cohort workflow for turning country-level talent forecasts into concrete generated players.</p>
      </div>
      <p>
        Talent Intake is season-based, not random weekly generation. A selected season&apos;s intake includes players who turn 15 during that season.
        Each future player may have an eligible_week, and admin can review the whole cohort before all players are eligible.
      </p>
      <p className="status">This page is a planning shell and does not yet run the future seasonal intake engine.</p>

      <section className="panel nested-panel">
        <h3>Planned workflow</h3>
        <ol>
          {workflowSteps.map((step) => (
            <li key={step}>{step}</li>
          ))}
        </ol>
      </section>

      <section className="panel nested-panel">
        <h3>Statuses</h3>
        <ul>
          {statuses.map((status) => (
            <li key={status}>{status}</li>
          ))}
        </ul>
      </section>

      <section className="panel nested-panel">
        <h3>Rules</h3>
        <ul>
          {rules.map((rule) => (
            <li key={rule}>{rule}</li>
          ))}
        </ul>
      </section>

      <p>
        For currently available generation/edit/lock workflows, use <Link to="/admin/players/database">Current initial pool tooling</Link>.
      </p>
    </section>
  )
}
