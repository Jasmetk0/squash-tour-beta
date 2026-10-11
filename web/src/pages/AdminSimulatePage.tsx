import { Link } from 'react-router-dom'
import { PageIntro, SectionCard } from '../components/RunScopedUi'

export function AdminSimulatePage(): JSX.Element {
  return <section className="panel">
    <PageIntro title="Simulate" subtitle="Simulation is a Run-scoped, Branch-aware Admin workflow." />
    <SectionCard title="Choose a Run"><p>Global Admin has no active Run, Active Admin Branch, or season/week context. Open a Run before choosing a deterministic simulation command.</p><p><Link to="/admin/runs">Open Runs</Link></p></SectionCard>
    <SectionCard title="Available Run simulation scopes"><ul className="dashboard-help-list"><li>Next Match</li><li>Next Round</li><li>Next Tournament</li><li>Next Week</li><li>Full Season (regular season only)</li><li>World Tour Finals (explicit separate command)</li></ul><p className="status">Time browsing, custom ranges, and Full Timeline simulation are deferred.</p></SectionCard>
  </section>
}
