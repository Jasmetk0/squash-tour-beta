import {
  viewerHomePath,
  viewerPlayersPath,
  viewerSeasonCalendarPath,
  viewerTopCountriesPath,
  viewerTopPlayersPath,
  viewerTopTourPath
} from './viewerRoutes'

function safeDecodePathSegment(segment: string): string {
  try {
    return decodeURIComponent(segment)
  } catch {
    return segment
  }
}

export function getModeSwitcherTarget(pathname: string): { viewerTarget: string; adminTarget: string } {
  const runCalendarMatch = pathname.match(/^\/(viewer|admin)\/runs\/([^/]+)\/calendar$/)
  if (runCalendarMatch) {
    return {
      viewerTarget: viewerSeasonCalendarPath(safeDecodePathSegment(runCalendarMatch[2])),
      adminTarget: `/admin/runs/${runCalendarMatch[2]}/calendar`
    }
  }

  const runPlayersMatch = pathname.match(/^\/(viewer|admin)\/runs\/([^/]+)\/players$/)
  if (runPlayersMatch) {
    return {
      viewerTarget: viewerPlayersPath(safeDecodePathSegment(runPlayersMatch[2])),
      adminTarget: `/admin/runs/${runPlayersMatch[2]}/players`
    }
  }

  const mappings: Record<string, { viewerTarget: string; adminTarget: string }> = {
    [viewerHomePath()]: { viewerTarget: viewerHomePath(), adminTarget: '/admin' },
    '/admin': { viewerTarget: viewerHomePath(), adminTarget: '/admin' },
    [viewerTopPlayersPath()]: { viewerTarget: viewerTopPlayersPath(), adminTarget: '/admin/players' },
    '/admin/players': { viewerTarget: viewerTopPlayersPath(), adminTarget: '/admin/players' },
    [viewerTopCountriesPath()]: { viewerTarget: viewerTopCountriesPath(), adminTarget: '/admin/world/countries' },
    '/admin/world/countries': { viewerTarget: viewerTopCountriesPath(), adminTarget: '/admin/world/countries' },
    [viewerTopTourPath()]: { viewerTarget: viewerTopTourPath(), adminTarget: '/admin/tour-seasons' },
    '/admin/tour-seasons': { viewerTarget: viewerTopTourPath(), adminTarget: '/admin/tour-seasons' }
  }

  if (mappings[pathname]) return mappings[pathname]
  if (pathname.startsWith('/viewer')) return { viewerTarget: pathname, adminTarget: '/admin' }
  if (pathname.startsWith('/admin')) return { viewerTarget: viewerHomePath(), adminTarget: pathname }
  return { viewerTarget: viewerHomePath(), adminTarget: '/admin' }
}
