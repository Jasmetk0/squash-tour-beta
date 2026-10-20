import { Link } from 'react-router-dom'
import { PageIntro, SectionCard } from '../components/RunScopedUi'
import { useLanguage } from '../i18n/LanguageContext'

const copy = {
  cs: {
    title: 'Simulace',
    subtitle: 'Simulace patří ke konkrétnímu Runu a jeho aktivní větvi.',
    choose: 'Vybrat Run',
    context: 'Globální Admin nemá aktivní Run, větev ani čas. Nejdřív otevři Run a vyber větev.',
    runs: 'Otevřít Runy',
    scopes: 'Rozsahy simulace v Runu',
    commands: ['Další zápas', 'Další slot', 'Další zápasový den', 'Další kolo', 'Další turnaj', 'Další týden', 'Další sezona', 'Full Simulation'],
    availability: 'Dostupnost každého příkazu se ověřuje podle uloženého stavu a podporovaných funkcí vybrané větve. Překážky uvidíš přímo v Runu.',
    controls: 'Cíl a průběh',
    detail: 'V Runu lze u podporovaných simulací zvolit cíl, prověřit jej a řídit průběh. Prohlížení historie nemění cíl ani nespouští simulaci. Uložení výsledků zůstává samostatnou ruční akcí.',
    tasks: 'Centrum simulací',
    recovery: 'Uložené úlohy a podklady k obnovení jsou v Centru simulací. Otevření přehledu ani návrat do Runu nic automaticky nespouští.',
    legacy: 'Starší nástroje',
    legacyDetail: 'Kompatibilní příkazy a World Tour Finals jsou v příslušném Runu oddělené od autoritativního ovládání.'
  },
  en: {
    title: 'Simulate',
    subtitle: 'Simulation is a Run-scoped, Branch-aware Admin workflow.',
    choose: 'Choose a Run',
    context: 'Global Admin has no active Run, Branch or Time. Open a Run and select its Branch first.',
    runs: 'Open Runs',
    scopes: 'Run simulation scopes',
    commands: ['Next Match', 'Next Slot', 'Next Match Day', 'Next Round', 'Next Tournament', 'Next Week', 'Next Season', 'Full Simulation'],
    availability: 'Each command is checked against the saved state and supported capabilities of the selected Branch. Blockers are explained inside the Run.',
    controls: 'Target and progress',
    detail: 'Inside a Run, supported simulations let you choose and review a target and control progress. Browsing history changes neither the target nor simulation state. Saving results remains a separate manual action.',
    tasks: 'Simulation Task Center',
    recovery: 'Persisted tasks and recovery evidence are in the Simulation Task Center. Opening the inventory or returning to a Run never starts simulation automatically.',
    legacy: 'Legacy tools',
    legacyDetail: 'Compatibility commands and World Tour Finals remain separate from authoritative controls inside the relevant Run.'
  }
} as const

export function AdminSimulatePage(): JSX.Element {
  const { language } = useLanguage()
  const text = copy[language]
  return <section className="panel">
    <PageIntro title={text.title} subtitle={text.subtitle} />
    <SectionCard title={text.choose}>
      <p>{text.context}</p><p><Link to="/admin/runs">{text.runs}</Link></p>
    </SectionCard>
    <SectionCard title={text.scopes}>
      <ul className="dashboard-help-list">{text.commands.map(command => <li key={command}>{command}</li>)}</ul>
      <p className="status">{text.availability}</p>
    </SectionCard>
    <SectionCard title={text.controls}><p>{text.detail}</p></SectionCard>
    <SectionCard title={text.tasks}>
      <p>{text.recovery}</p><p><Link to="/admin/operations">{text.tasks}</Link></p>
    </SectionCard>
    <SectionCard title={text.legacy}><p>{text.legacyDetail}</p></SectionCard>
  </section>
}
