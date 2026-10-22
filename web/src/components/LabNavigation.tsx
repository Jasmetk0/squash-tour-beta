import { Link } from 'react-router-dom'

const labs = [
  { id: 'home', href: '/admin/labs', label: 'Test Lab' },
  { id: 'match', href: '/admin/labs/match', label: 'Match Lab' },
  { id: 'tournament', href: '/admin/labs/tournament', label: 'Tournament Lab' },
  { id: 'player', href: '/admin/labs/player', label: 'Player Lab' }
] as const

type LabId = (typeof labs)[number]['id']

/** Only navigation: switching labs never runs a scenario or persists its draft. */
export function LabNavigation({ active }: { active: LabId }): JSX.Element {
  return <nav className="actions" aria-label="Test Lab navigation">
    {labs.map(lab => active === lab.id
      ? <span key={lab.id} aria-current="page"><strong>{lab.label}</strong></span>
      : <Link key={lab.id} to={lab.href}>{lab.label}</Link>)}
  </nav>
}
