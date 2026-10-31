import type { CanonicalTournamentPreparationState } from '../api/types'
import { verifiedTournamentNavigation, type TournamentNavigationSections, type TournamentSectionId } from './runTournamentNextAction'
import { SectionCard } from './RunScopedUi'

const sectionLabels: Array<{ id: TournamentSectionId; cs: string; en: string }> = [
  {id:'canonical-entry-timing',cs:'Časování Entry',en:'Entry timing'},
  {id:'canonical-preparation',cs:'Příprava turnaje',en:'Tournament preparation'},
  {id:'canonical-entry-review',cs:'Kontrola přihlášek',en:'Application review'},
  {id:'canonical-reviewed-entry-field',cs:'Turnajové pole',en:'Entry field'},
  {id:'canonical-draw-authority',cs:'Losování',en:'Draw'},
  {id:'canonical-first-match',cs:'Zápasy',en:'Matches'}
]

/** UI only: every link points to a mounted panel for this exact Present Run. */
export function RunTournamentNextActionPanel({
  runId, branchId, eventId, preparation, sections, language
}: {
  runId: string
  branchId: string
  eventId: string
  preparation: CanonicalTournamentPreparationState | null | undefined
  sections: TournamentNavigationSections
  language: 'cs' | 'en'
}): JSX.Element {
  const cs = language === 'cs'
  const review = verifiedTournamentNavigation(
    preparation, runId, branchId, eventId, sections, language
  )
  return <SectionCard title={cs ? 'Postup turnajem · další krok' : 'Tournament workflow · next step'}>
    <p className="status">{cs
      ? 'Navigace vychází pouze z ověřeného Runu, Branche a autoritativního stavu turnaje. Nic neukládá ani nespouští.'
      : 'Navigation uses only the verified Run, Branch and canonical tournament state. It never saves or executes a command.'}</p>
    {!preparation ? (
      <p role="status">{cs?'Čekám na skutečný stav turnaje…':'Waiting for canonical tournament state…'}</p>
    ) : !review ? (
      <p role="alert" className="error">{cs
        ? 'Stav turnaje neodpovídá tomuto Runu, Branchi nebo turnaji. Žádný další krok nelze doporučit.'
        : 'Tournament evidence does not match this Run, Branch or event. No next step can be recommended.'}</p>
    ) : <>
      <p><strong>{cs?'Další krok serveru:':'Server next action:'}</strong>{' '}
        <code>{review.action}</code></p>
      {review.next ? (
        <p><a href={'#' + review.next.target}>
          {cs ? 'Otevřít: ' : 'Go to: '}{review.next.label}
        </a></p>
      ) : (
        <p role="status">{review.scheduleReady
          ? (cs?'Příprava rozpisu je serverem potvrzena. Příslušný panel na této obrazovce není otevřen.':'The server reports schedule preparation ready. Its panel is not mounted on this screen.')
          : (cs?'Odpovídající další krok zde zatím není dostupný nebo čeká na další předpoklady.':'The corresponding next action is not mounted here or is awaiting prerequisites.')}</p>
      )}
      <ul aria-label={cs?'Doložený postup turnaje':'Verified tournament milestones'}>
        <li>{cs?'Ranking Snapshot':'Ranking Snapshot'}: {review.rankingPublished ? (cs?'potvrzený':'confirmed') : (cs?'nepotvrzený':'not confirmed')}</li>
        <li>{cs?'Entry Field':'Entry Field'}: {review.entryFieldStored ? (cs?'uložený':'stored') : (cs?'nepotvrzený':'not confirmed')}</li>
        <li>{cs?'Draw':'Draw'}: {review.drawStored ? (cs?'uložený':'stored') : (cs?'nepotvrzený':'not confirmed')}</li>
        <li>{cs?'Příprava rozpisu':'Schedule preparation'}: {review.scheduleReady ? (cs?'potvrzená':'confirmed') : (cs?'nepotvrzená':'not confirmed')}</li>
      </ul>
      {review.sourceBlockers.length > 0 && <>
        <p><strong>{cs?'Blokátory serveru':'Server blockers'}:</strong></p>
        <ul>{review.sourceBlockers.map((item,i)=><li key={i}><code>{item}</code></li>)}</ul>
      </>}
      <nav aria-label={cs?'Přejít na sekci turnaje':'Go to tournament section'}>
        <p>{cs?'Přejít k existujícím ovládacím panelům:':'Jump to available controls:'}</p>
        <ul>{sectionLabels.filter(item=>sections[item.id] === true).map(item=>
          <li key={item.id}><a href={'#'+item.id}>{cs?item.cs:item.en}</a></li>
        )}</ul>
      </nav>
      <p className="status">{cs
        ? 'Hotový krok neznamená, že bylo turnajové pole, zápasy nebo Saved Revision automaticky potvrzené.'
        : 'A completed prerequisite does not automatically approve participants, play matches or Save a Revision.'}</p>
    </>}
  </SectionCard>
}
