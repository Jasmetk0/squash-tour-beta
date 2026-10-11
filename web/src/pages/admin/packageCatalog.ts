import type { WorldPackage } from '../../api/types'

export const packageCategories = ['world','countries','category','series','calendar','setup','players','hybrid'] as const
export type PackageCategory = typeof packageCategories[number]
export type PackageFilter = PackageCategory | 'all'
export type CatalogItem = {
  key: string; name: string; description: string; kind: 'world'; version: string
  origin: WorldPackage['source']; editable: boolean; status: string; countryCount: number
  categories: PackageCategory[]
}
/** A dependency does not constitute contained data. Never synthesize a hybrid manifest. */
export function catalogFromWorlds(packages: WorldPackage[]): CatalogItem[] {
  const ids = new Map<string,CatalogItem>()
  for (const world of packages) {
    const key = 'world:' + world.world_id
    if (!ids.has(key)) ids.set(key, {
      key, name: world.name, description: world.description, kind: 'world',
      version: world.version, origin: world.source, editable: world.editable,
      status: world.status, countryCount: world.country_count,
      categories: world.country_count > 0 ? ['world','countries'] : ['world']
    })
  }
  return [...ids.values()]
}
export function inCategory(items: CatalogItem[], category: PackageFilter): CatalogItem[] {
  return category === 'all' ? items : items.filter(item => item.categories.includes(category))
}
export function catalogPath(item: CatalogItem): string {
  return '/admin/packages/world/' + encodeURIComponent(item.key.slice('world:'.length))
}
