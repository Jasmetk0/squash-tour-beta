import { Link } from 'react-router-dom'
import { useLanguage } from '../i18n/LanguageContext'

const labs = [
  { id: 'home', href: '/admin/labs', label: 'Test Lab' },
  { id: 'match', href: '/admin/labs/match', label: 'Match Lab' },
  { id: 'tournament', href: '/admin/labs/tournament', label: 'Tournament Lab' },
  { id: 'player', href: '/admin/labs/player', label: 'Player Lab' }
] as const

type LabId = (typeof labs)[number]['id']

/** Only navigation: switching labs never runs a scenario or persists its draft. */
export function LabNavigation({ active }: { active: LabId }): JSX.Element {
  const {language} = useLanguage(), cs = language === 'cs'
  const label = (id: LabId) => cs ? ({home: 'Rozcestník Labů', match: 'Laboratoř zápasů', tournament: 'Laboratoř turnajů', player: 'Laboratoř hráčů'})[id] : labs.find(lab => lab.id === id)!.label
  return <nav className="actions" aria-label={cs ? 'Navigace Test Labů' : 'Test Lab navigation'}>
    {labs.map(lab => active === lab.id
      ? <span key={lab.id} aria-current="page"><strong>{label(lab.id)}</strong></span>
      : <Link key={lab.id} to={lab.href}>{label(lab.id)}</Link>)}
  </nav>
}
