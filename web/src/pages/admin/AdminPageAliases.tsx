import { AdminPlayersPage as InitialPoolAdminPlayersPage } from '../AdminPlayersPage'
import { AdminPlayersHubPage } from '../AdminPlayersHubPage'
import { AdminSeasonsPage as SeasonBootstrapAdminSeasonsPage } from '../AdminSeasonsPage'
import { TournamentTemplatesPage } from '../TournamentTemplatesPage'
import { LinkCardGrid } from '../../components/LinkCardGrid'
import { describeCalendarEventTiming } from '../../tour/calendarEventModel'
import type { CalendarEventDraft } from '../../tour/calendarEventModel'


const futureCalendarPlanningExamples: CalendarEventDraft[] = [
  {
    id: 'future-planning-nemarque-open',
    name: 'Némarque Open',
    categoryCode: 'DIAMOND',
    qualificationWeeks: [5],
    weeks: [6, 7],
    locked: true,
    status: 'template'
  },
  {
    id: 'future-planning-world-tour-finals',
    name: 'World Tour Finals',
    categoryCode: 'WORLD_TOUR_FINALS',
    qualificationWeeks: [],
    weeks: [55],
    locked: true,
    status: 'template'
  }
]

export function AdminWorldPage(): JSX.Element {
  return (
    <section className="panel">
      <div className="page-intro">
        <h2>World</h2>
        <p className="subtitle">Manage country inputs and expected talent output used by the FAX squash simulation engine.</p>
      </div>
      <LinkCardGrid
        cards={[
          {
            title: 'Countries',
            description: 'Edit country inputs, country model data, style DNA, and future country profiles.',
            to: '/admin/world/countries'
          },
          {
            title: 'Talent Preview',
            description: 'Preview expected Elite Talents, Tour Talents, and Pro Depth by country before generating player intakes.',
            to: '/admin/world/talent-preview'
          },
        ]}
      />
    </section>
  )
}

export function AdminTourSeasonsPage(): JSX.Element {
  return (
    <section className="panel">
      <div className="page-intro">
        <h2>Tour & Seasons</h2>
        <p className="subtitle">Manage categories, recurring tournaments, season templates, concrete season calendars, and validation workflows.</p>
      </div>
      <section className="section-card" aria-label="Future calendar planning model examples">
        <h3>Future calendar planning model</h3>
        <p className="status">Season calendar events will use weeks and qualificationWeeks. Qualification belongs to the main event. Locked events must be unlocked before move/delete/overwrite actions. Calendar templates will be Admin-only until copied into canonical seasons.</p>
        <p className="status"><strong>Examples only — future planning model, not persisted season data.</strong></p>
        <ul>
          {futureCalendarPlanningExamples.map((event) => (
            <li key={event.id}>{event.name} — {event.categoryCode} — {describeCalendarEventTiming(event)} — {event.locked ? 'Locked' : 'Unlocked'}</li>
          ))}
        </ul>
      </section>
      <LinkCardGrid
        cards={[
          {
            title: 'Categories',
            description: 'Rules packages valid across season ranges. Transitional: currently managed through Tournament Templates tooling.',
            to: '/admin/tour-seasons/categories'
          },
          {
            title: 'Tournaments',
            description: 'Reusable master tournament brands. Planned split from category/template tooling.',
            to: '/admin/tour-seasons/tournaments'
          },
          {
            title: 'Season Templates',
            description: 'Reusable calendar plans that can be copied into concrete seasons.',
            to: '/admin/tour-seasons/season-templates'
          },
          {
            title: 'Season Registry',
            description: 'Read-only fixed registry for seasons 2000/01 through 2039/40, 61 weeks per season, SW1 = YW37.',
            to: '/admin/tour-seasons/season-registry'
          },
          {
            title: 'Seasons',
            description: 'Concrete 61-week season calendars from 2000/01 through 2039/40.',
            to: '/admin/seasons'
          },
          {
            title: 'Calendar Compare / Apply',
            description: 'Planned workflow for comparing seasons/templates and applying event-level decisions.',
            to: '/admin/tour-seasons/compare'
          },
          {
            title: 'Calendar Validation',
            description: 'Planned validation hub for week blocks, draw footprints, mandatory events, and schedule conflicts.',
            to: '/admin/tour-seasons/validation'
          }
        ]}
      />
    </section>
  )
}

export function AdminTournamentTemplatesPage(): JSX.Element {
  return <TournamentTemplatesPage />
}

export function AdminSeasonsPage(): JSX.Element {
  return <SeasonBootstrapAdminSeasonsPage />
}

export function AdminPlayersPage(): JSX.Element {
  return <AdminPlayersHubPage />
}

export function AdminPlayersDatabasePage(): JSX.Element {
  return <InitialPoolAdminPlayersPage />
}
