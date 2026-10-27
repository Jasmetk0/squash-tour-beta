import type { CandidateWeek } from '../api/rankingCandidates'
import { useLanguage } from '../i18n/LanguageContext'
import type { Language } from '../i18n/LanguageContext'

/** Display-only vocabulary. Request enums, IDs, audit and fingerprints are never translated. */
const cs: Record<string, string> = {
  "Week": "Týden",
  "Prepare ranking": "Příprava žebříčku",
  "Prepare next ranking": "Připravit další žebříček",
  "Prepare initial ranking": "Připravit počáteční žebříček",
  "Candidate prepared. Review ranking changes below to save a recoverable revision.": "Kandidát je připraven. Níže zkontrolujte změny žebříčku a výslovně uložte obnovitelnou revizi.",
  "The final Run week is already prepared. No season 51 ranking can be created.": "Poslední týden Runu je již připraven. Žebříček pro 51. sezonu nelze vytvořit.",
  "Loading the previous roster and decisions…": "Načítání předchozí soupisky a rozhodnutí…",
  "Retry preparation inputs": "Znovu načíst vstupy přípravy",
  "The ranking head changed. Refresh history before preparing.": "Poslední kandidát se změnil. Před přípravou obnovte historii.",
  "This legacy candidate has no complete roster. Preparation requires a verified input history.": "Tento historický kandidát nemá úplnou soupisku. Příprava vyžaduje ověřenou historii vstupů.",
  "Caller-resolved zeros require an explicit history migration before using this form.": "Nuly dodané volajícím vyžadují před použitím formuláře výslovnou migraci historie.",
  "Review a preview first.": "Nejprve zkontrolujte náhled.",
  "Prepare": "Připravit",
  "using stored tournament results. Review the complete roster, policy and decisions for this boundary.": "z uložených turnajových výsledků. Zkontrolujte úplnou soupisku, pravidla a rozhodnutí pro tuto hranici.",
  "This creates an unpublished candidate. World time and Viewer selection stay at their saved state.": "Vznikne nezveřejněný kandidát, nikoli Official Ranking. Čas světa i výběr Viewer Branch zůstanou beze změny; uložená revize vznikne až po samostatném Save.",
  "Season boundary: explicitly review the incoming season’s policy before calculating.": "Hranice sezony: před výpočtem výslovně zkontrolujte pravidla nadcházející sezony.",
  "Ranking inputs": "Vstupy žebříčku",
  "Policy reference": "Reference pravidel (policy)",
  "Best N": "Nejlepších N",
  "Roster": "Soupiska",
  "An empty roster produces no ranked players.": "Prázdná soupiska nevytvoří žádné klasifikované hráče.",
  "Player": "Hráč",
  "Player ID": "ID hráče",
  "Stable tie-break token": "Stabilní token pro rozhodnutí shody",
  "Tour entry season (1–50)": "Sezona vstupu na Tour (1–50)",
  "Tour entry week": "Týden vstupu na Tour",
  "Retired at target week": "K cílovému týdnu ukončil kariéru",
  "Remove player": "Odebrat hráče",
  "Add player": "Přidat hráče",
  "Disciplinary zeros": "Disciplinární nuly",
  "New decisions apply at": "Nová rozhodnutí platí od",
  "Duration changes preserve each zero’s original start. Durations are explicit reviewed decisions.": "Změna délky zachová původní začátek nuly. Délku je třeba výslovně posoudit.",
  "Original start": "Původní začátek",
  "Duration": "Doba trvání",
  "weeks": "týdnů",
  "Change this duration": "Upravit tuto dobu trvání",
  "New duration in weeks": "Nová doba trvání v týdnech",
  "Correction reference": "Reference opravy",
  "New zero": "Nová nula",
  "Zero player": "Hráč s nulou",
  "Select player": "Vyberte hráče",
  "Duration in weeks": "Doba trvání v týdnech",
  "Decision reference": "Reference rozhodnutí",
  "Remove zero": "Odebrat nulu",
  "Add disciplinary zero": "Přidat disciplinární nulu",
  "Preparation audit": "Audit přípravy",
  "Operator label": "Označení operátora",
  "Reason": "Důvod změny",
  "I reviewed the roster, target policy and decisions for this week.": "Zkontroloval(a) jsem soupisku, cílová pravidla a rozhodnutí pro tento týden.",
  "Calculate preview": "Vypočítat náhled",
  "Calculating preview…": "Počítání náhledu…",
  "Ranking preview": "Náhled žebříčku",
  "Review": "Zkontrolovat",
  "Preview only": "Pouze náhled",
  "Best": "Nejlepších",
  "ranked players": "klasifikovaných hráčů",
  "zero changes": "změn disciplinárních nul",
  "result corrections": "oprav výsledků",
  "No players are classified at this boundary.": "V tomto týdnu není klasifikován žádný hráč.",
  "Rank": "Pořadí",
  "Points": "Body",
  "Active zeros": "Aktivní nuly",
  "Retry this exact preparation": "Zopakovat přesně stejnou přípravu",
  "Confirm candidate preparation": "Potvrdit přípravu kandidáta",
  "Edit inputs and recalculate": "Upravit vstupy a přepočítat",
  "Preparing candidate…": "Příprava kandidáta…",
  "The request is retained for an exact retry. If inputs changed, edit and recalculate.": "Příkaz zůstal zachován pro přesné opakování. Pokud se vstupy změnily, upravte je a přepočítejte.",
  "Result corrections": "Opravy výsledků",
  "Corrections affect the next candidate. Earlier rankings and the result’s original expiry remain unchanged.": "Opravy ovlivní až dalšího kandidáta. Dřívější žebříčky ani původní konec platnosti výsledku se nemění.",
  "Load stored results to correct": "Načíst uložené výsledky pro opravy",
  "Loading stored results…": "Načítání uložených výsledků…",
  "Retry result sources": "Znovu načíst zdroje výsledků",
  "No stored results are available to correct.": "Nejsou dostupné žádné uložené výsledky k opravě.",
  "Result sources no longer match the selected ranking. Refresh history.": "Zdroje výsledků již neodpovídají zvolenému žebříčku. Obnovte historii.",
  "Stored": "Uloženo",
  "Q": "Kvalifikace",
  "Main": "Hlavní soutěž",
  "Ranking eligible": "Započítává se do žebříčku",
  "Excluded": "Nezapočítává se",
  "Completed": "Dokončeno",
  "Abandoned": "Nedokončeno",
  "First publication": "První zveřejnění",
  "season": "sezona",
  "week": "týden",
  "Validity": "Platnost",
  "Correct": "Opravit",
  "Corrected qualification points": "Opravené kvalifikační body",
  "Corrected main points": "Opravené body hlavní soutěže",
  "Ranking eligible after correction": "Po opravě započítat do žebříčku",
  "Corrected terminal status": "Opravený konečný stav",
  "Result correction reference": "Reference opravy výsledku",
  "Save ranking preparation": "Uložit přípravu žebříčku",
  "Review ranking changes": "Zkontrolovat změny žebříčku",
  "Save the current Branch’s prepared ranking history as a recoverable revision. Rankings remain unpublished and the Viewer Branch stays selected.": "Uloží připravenou historii žebříčku aktuální větve do obnovitelné revize. Žebříčky zůstanou nezveřejněné a vybraná Viewer Branch se nezmění.",
  "Checking ranking changes…": "Kontrola změn žebříčku…",
  "Refresh the ranking review before saving.": "Před uložením obnovte kontrolu žebříčku.",
  "Ranking changes are ready to save.": "Změny žebříčku jsou připraveny k uložení.",
  "Saving is unavailable. Check Branch permissions and resolve pending draft changes.": "Uložení je zablokováno. Zkontrolujte oprávnění větve a nevyřízené změny konceptu.",
  "Ranking preparation is already saved.": "Příprava žebříčku je již uložená.",
  "Refresh ranking review": "Obnovit kontrolu žebříčku",
  "Ranking preparation saved.": "Příprava žebříčku byla uložena.",
  "Saving ranking preparation…": "Ukládání přípravy žebříčku…",
  "Save failed. Refresh the review and explicitly retry after resolving the error.": "Uložení selhalo. Obnovte kontrolu a po vyřešení chyby znovu výslovně potvrďte uložení.",
  "Ranking save review": "Kontrola uložení žebříčku",
  "Refresh required after failed save.": "Po neúspěšném uložení je nutná aktualizace kontroly.",
}

export function rankingWorkflowText(english: string, language: Language): string {
  return language === 'cs' ? cs[english] ?? english : english
}

/** Keeps the existing 61-week / 50-season legacy coordinate convention. */
export function rankingWorkflowWeekLabel(week: CandidateWeek, language: Language): string {
  return `${2000 + week.season_index}/${String(2001 + week.season_index).slice(-2)} · ${rankingWorkflowText('Week', language)} ${week.week}`
}

/** Supports legacy isolated component mounts without a Provider; normal Admin
 * navigation always gets the live language from LanguageContext. */
export function useRankingWorkflowLanguage(): Language {
  try {
    return useLanguage().language
  } catch (error) {
    if (error instanceof Error && error.message === 'useLanguage requires LanguageProvider') return 'en'
    throw error
  }
}
