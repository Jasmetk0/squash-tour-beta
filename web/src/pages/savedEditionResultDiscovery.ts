/** Read-only filtering of independently validated Saved Edition publication evidence. */
import type {SavedTourResult} from '../api/savedTour'

export type PublishedEditionMatch=SavedTourResult['matches'][number]
const norm=(value:unknown)=>String(typeof value==='string'?value:'').normalize('NFD')
  .replace(/[\u0300-\u036f]/g,'').toLocaleLowerCase().trim()
/** Keep the server's original canonical ordering; never infer a Match Day or result. */
export function filterSavedEditionMatches(
  matches:readonly PublishedEditionMatch[],search:string
):PublishedEditionMatch[]{
  const term=norm(search)
  if(!term)return [...matches]
  return matches.filter(match=>[match.match_id,match.winner_player_id,
    match.loser_player_id,match.scoreline].some(value=>norm(value).includes(term)))
}
