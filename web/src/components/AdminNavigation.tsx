import { useState } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import { globalAdminNav, globalAdminBottomNav, runAdminNavFor, runAdminBottomNavFor } from '../navigation/adminNavigation'
import type { AdminNavItem } from '../navigation/adminNavigation'
import type { AdminScope } from '../navigation/appShellMode'
import { useLanguage } from '../i18n/LanguageContext'

type AdminNavigationProps = { scope: AdminScope }

function isItemActive(path: string, item: AdminNavItem, root: string): boolean {
  if (item.to === root) return path === root || path === root + '/'
  return path === item.to || path.startsWith(item.to + '/') ||
    (item.children?.some(child => path === child.to || path.startsWith(child.to + '/')) ?? false)
}

export function AdminNavigation({ scope }: AdminNavigationProps): JSX.Element {
  const { t, language } = useLanguage()
  const { pathname } = useLocation()
  const [collapsed, setCollapsed] = useState(false)
  const [pinned, setPinned] = useState(true)
  const [openCategory, setOpenCategory] = useState<string | null>(null)
  const isRun = scope.kind === 'run'
  const root = isRun ? '/admin/runs/' + encodeURIComponent(scope.runId) : '/admin'
  const nav = isRun ? runAdminNavFor(scope.runId) : globalAdminNav
  const bottom = isRun ? runAdminBottomNavFor(scope.runId) : globalAdminBottomNav
  const describe = (item: AdminNavItem) => t(item.label)
  const links = (items: AdminNavItem[]) => items.map(item => {
    const active = isItemActive(pathname, item, root)
    const expanded = openCategory === item.to || (openCategory === null && active)
    return <div className="side-nav__group" key={item.to}>
      <div className="side-nav__line">
        <NavLink to={item.to} end={item.to === root} title={describe(item)}
          aria-current={active ? 'page' : undefined} className={active ? 'active' : ''}>
          <span className="side-nav__marker" aria-hidden="true">{item.label.slice(0, 1)}</span>
          <span className="side-nav__text">{describe(item)}</span>
        </NavLink>
        {item.children && <button type="button" aria-label={describe(item) + ' submenu'}
          aria-expanded={expanded} className="side-nav__expand"
          onClick={() => setOpenCategory(expanded ? '' : item.to)}>{expanded ? '−' : '+'}</button>}
      </div>
      {item.children && expanded && <div className="side-nav__children">
        {item.children.map(child => <NavLink key={child.to} to={child.to}
          className={pathname === child.to ? 'active' : ''} end={true}>{child.label}</NavLink>)}
      </div>}
    </div>
  })
  return <aside className={'side-nav' + (collapsed ? ' side-nav--collapsed' : '') + (pinned ? ' side-nav--pinned' : '')}>
    <div className="side-nav__top">
      <button type="button" className="side-nav__toggle" aria-label={collapsed ? t('Expand sidebar') : t('Collapse sidebar')}
        onClick={() => setCollapsed(value => !value)}>{collapsed ? '☰' : '☷'}</button>
      <button type="button" className="side-nav__pin" aria-label={pinned ? t('Unpin sidebar') : t('Pin sidebar')}
        aria-pressed={pinned} onClick={() => setPinned(value => !value)}>{pinned ? '📌' : '○'}</button>
      <span className="side-nav__scope">{isRun ? (language === 'cs' ? 'Navigace Runu' : 'Run navigation') : (language === 'cs' ? 'Hlavní nabídka' : 'Global navigation')}</span>
    </div>
    <nav className={isRun ? 'run-nav side-nav__links' : 'primary-nav side-nav__links'}
      aria-label={isRun ? 'Run Admin navigation' : 'Global Admin navigation'}>{links(nav)}</nav>
    <nav className="side-nav__bottom" aria-label={isRun ? 'Run management navigation' : 'Application settings navigation'}>
      {links(bottom)}
    </nav>
  </aside>
}
