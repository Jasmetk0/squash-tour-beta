import { Link } from 'react-router-dom'

type PlayersCard = {
  title: string
  description: string
  to: string
}

const cards: PlayersCard[] = [
  {
    title: 'Player Database',
    description:
      'Current player generation and database tools. Long-term this becomes the main player list with search, filters, player detail links, and status controls.',
    to: '/admin/players/database'
  },
  {
    title: 'Talent Intake',
    description: 'Planned seasonal 15-year-old cohort workflow: Expected Intake → Generate Preview → Review → Persist → Regenerate Unlocked.',
    to: '/admin/players/intake'
  },
  {
    title: 'Custom Players',
    description: 'Planned workflow for manually created lore/custom players. Custom players default locked and count against country-season talent budget.',
    to: '/admin/players/database'
  },
  {
    title: 'Locks & Overrides',
    description: 'Planned control center for locked/custom players and manual overrides.',
    to: '/admin/players/database'
  },
  {
    title: 'Player Audit',
    description: 'Planned audit trail for player creation, edits, locks, regeneration skips, and manual changes.',
    to: '/admin/players/database'
  }
]

export function AdminPlayersHubPage(): JSX.Element {
  return (
    <section className="panel">
      <div className="page-intro">
        <h2>Players</h2>
        <p className="subtitle">Players module hub: transitional routing for Player Database, Talent Intake, custom players, locks/overrides, and audit workflows.</p>
      </div>
      <div className="mode-card-grid">
        {cards.map((card) => (
          <Link className="mode-card" to={card.to} key={card.title}>
            <strong>{card.title}</strong>
            <span>{card.description}</span>
          </Link>
        ))}
      </div>
    </section>
  )
}
