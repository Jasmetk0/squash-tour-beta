import { Link } from 'react-router-dom'
import { useLanguage } from '../../i18n/LanguageContext'
import { LabNavigation } from '../../components/LabNavigation'

export function TestLabHomePage(): JSX.Element {
  const { language, t } = useLanguage()
  const modules = [
    { name: language === 'cs' ? 'Laboratoř zápasů' : 'Match Test Lab', href: '/admin/labs/match', description: language === 'cs' ? 'Deterministické samostatné scénáře zápasů.' : 'Deterministic isolated match scenarios.' },
    { name: language === 'cs' ? 'Laboratoř turnajů' : 'Tournament Test Lab', href: '/admin/labs/tournament', description: language === 'cs' ? 'Formáty, losy, postup a turnajové dávky.' : 'Formats, draws, progression and tournament batches.' },
    { name: language === 'cs' ? 'Laboratoř hráčů' : 'Player Test Lab', href: '/admin/labs/player', description: language === 'cs' ? 'Testy generování a vývoje hráčů.' : 'Player generation and development tests.' }
  ]
  return <section className="panel">
    <div className="page-intro"><h2>{t('Test Lab')}</h2><p className="subtitle">
      {language === 'cs' ? 'Oddělené testovací nástroje. Nemusíš mít otevřený Run.' : 'Isolated testing tools. No open Run required.'}
    </p></div>
    <LabNavigation active="home" />
    <div className="home-entry-grid">{modules.map(module =>
      <article className="home-entry" key={module.href}><h3>{module.name}</h3><p>{module.description}</p>
        <Link to={module.href}>{language === 'cs' ? 'Otevřít laboratoř' : 'Open Lab'} →</Link></article>
    )}</div>
  </section>
}
