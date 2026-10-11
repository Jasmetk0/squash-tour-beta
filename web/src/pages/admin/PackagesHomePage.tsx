import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { listWorldPackages } from '../../api/client'
import { useLanguage } from '../../i18n/LanguageContext'
import { formatApiError } from '../../utils/apiErrors'

export function PackagesHomePage(): JSX.Element {
  const { language, t } = useLanguage()
  const query = useQuery({ queryKey: ['world-packages'], queryFn: listWorldPackages, retry: false })
  return <section className="panel">
    <div className="page-intro"><h2>{t('Packages')}</h2><p className="subtitle">{language === 'cs'
      ? 'Zdrojové balíčky. Po použití v Runu vzniká nezávislá upravitelná kopie.'
      : 'Source packages. Applied content becomes an independent editable Run copy.'}</p></div>
    <div className="home-entry-grid">
      <article className="home-entry"><h3>World Packages</h3>
        <p>{query.isPending ? t('Loading') : query.isError ? formatApiError(query.error) : String(query.data.packages.length) + ' World Packages'}</p>
        <Link to="/admin/world/library">{language === 'cs' ? 'Procházet World balíčky' : 'Browse World packages'} →</Link>
      </article>
      <article className="home-entry"><h3>Category / Calendar</h3>
        <p>{language === 'cs' ? 'Existující zdrojové kategorie a kalendářové šablony.' : 'Existing category sources and calendar templates.'}</p>
        <Link to="/admin/tour-seasons">{language === 'cs' ? 'Otevřít zdrojové nástroje' : 'Open source tools'} →</Link>
      </article>
      <article className="home-entry"><h3>Player Packages</h3>
        <p>{language === 'cs' ? 'Schválený rozsah pre-alphy. Schéma a importní workflow dosud nejsou uzavřené.' : 'Approved pre-alpha scope. Payload and import workflow are not yet defined.'}</p>
        <span className="status">{t('Not implemented')}</span>
      </article>
    </div>
  </section>
}
