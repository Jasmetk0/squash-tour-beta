import { Link } from 'react-router-dom'
import type { SavedHomePlayerIdentity } from '../api/types'

export function HomePlayerIdentityLink({
  runId, playerId, identity
}: { runId: string; playerId: string; identity?: SavedHomePlayerIdentity }): JSX.Element {
  if (!identity || identity.player_id !== playerId) return <code title="Saved name unavailable">{playerId}</code>
  return <Link to={'/admin/runs/' + encodeURIComponent(runId) + '/people/' + encodeURIComponent(playerId)}
    title={playerId + ' · ' + identity.identity_source}>
    {identity.display_name} <small>({identity.country_code})</small>
  </Link>
}
