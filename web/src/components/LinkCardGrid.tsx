import { Link } from 'react-router-dom'

export type LinkCard = {
  title: string
  description: string
  to: string
}

export function LinkCardGrid({ cards }: { cards: LinkCard[] }): JSX.Element {
  return (
    <div className="mode-card-grid">
      {cards.map((card) => (
        <Link className="mode-card" to={card.to} key={card.to}>
          <strong>{card.title}</strong>
          <span>{card.description}</span>
        </Link>
      ))}
    </div>
  )
}
