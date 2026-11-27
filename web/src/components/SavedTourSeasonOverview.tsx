import type {SavedTourCalendar,SavedTourEvent} from '../api/savedTour'

type Props={model:SavedTourCalendar;displayed:readonly SavedTourEvent[];cs:boolean;
  selectedWeek:number|null;categoryFilter:string;onWeek:(week:number)=>void;
  onCategory:(category:string)=>void}

export function SavedTourSeasonOverview({model,displayed,cs,selectedWeek,categoryFilter,onWeek,onCategory}:Props){
  if(model.calendar_status!=='ready')return null
  const events=model.editions
  const weeks=Array.from({length:model.week_count},(_,i)=>({week:i+1,total:0,published:0}))
  const categories=new Map<string,{total:number;published:number}>()
  for(const edition of events){
    const week=weeks[edition.season_week-1]
    week.total++
    if(edition.result_published)week.published++
    const category=typeof edition.category==='string'?edition.category.trim():''
    const counts=categories.get(category)??{total:0,published:0}
    counts.total++
    if(edition.result_published)counts.published++
    categories.set(category,counts)
  }
  const published=weeks.reduce((sum,week)=>sum+week.published,0)
  const occupied=weeks.filter(week=>week.total>0).length
  const shownPublished=displayed.filter(edition=>edition.result_published).length
  return <section aria-label={cs?'Přehled uložené sezony':'Saved season overview'} data-run-navigation-readonly>
    <h3>{cs?'Přehled sezony':'Season overview'}</h3>
    <p className="status">{model.season} · {model.week_count} {cs?'týdnů uložené projekce':'weeks in Saved projection'}</p>
    <div className="grid">
      <div className="section-subtle"><p>{cs?'Uložené edice':'Saved Editions'}</p><strong>{events.length}</strong></div>
      <div className="section-subtle"><p>{cs?'Publikované výsledky':'Published results'}</p><strong>{published}</strong></div>
      <div className="section-subtle"><p>{cs?'Bez publikovaného výsledku':'Without published result'}</p><strong>{events.length-published}</strong></div>
      <div className="section-subtle"><p>{cs?'Týdny s edicí':'Weeks with an Edition'}</p><strong>{occupied} / {model.week_count}</strong></div>
    </div>
    <p className="status">{cs?'Celá uložená sezona; aktivní filtry a zaměření na týden mění jen výběr níže.':
      'Whole Saved season; active filters and week focus change only the selection below.'}</p>
    <p>{cs?'Zobrazený výběr':'Displayed selection'}: {displayed.length} · {cs?'publikováno':'published'}: {shownPublished}</p>
    <details>
      <summary>{cs?'Obsazenost týdnů a kategorie':'Week occupancy and categories'}</summary>
      <p className="status">{cs?'Každá Edition je započtena jen v týdnu evidovaném v tomto zdroji; nejde o vícedenní rozpis, kvalifikační fáze ani vytížení kurtů.':
        'Each Edition is counted only in its recorded week; not a multi-day schedule, qualification phases or court utilization.'}</p>
      <div className="table-responsive"><table aria-label={cs?'Obsazenost uložených týdnů':'Saved week occupancy'}>
        <thead><tr><th>{cs?'Týden':'Week'}</th><th>{cs?'Edice':'Editions'}</th><th>{cs?'Publikováno':'Published'}</th></tr></thead>
        <tbody>{weeks.filter(w=>w.total>0).map(w=><tr key={w.week}>
          <th scope="row"><button type="button" aria-pressed={selectedWeek===w.week}
            onClick={()=>onWeek(w.week)}>W{w.week}</button></th>
          <td>{w.total}</td><td>{w.published}</td>
        </tr>)}</tbody></table></div>
      {occupied===0&&<p>{cs?'Žádný týden nemá uloženou edici.':'No week has a Saved Edition.'}</p>}
      <div className="table-responsive"><table aria-label={cs?'Kategorie uložených edic':'Saved Edition categories'}>
        <thead><tr><th>{cs?'Kategorie':'Category'}</th><th>{cs?'Edice':'Editions'}</th><th>{cs?'Publikováno':'Published'}</th></tr></thead>
        <tbody>{[...categories.entries()].sort(([a],[b])=>a.localeCompare(b)).map(([category,count])=><tr key={category}>
          <th scope="row">{category?<button type="button" aria-pressed={categoryFilter===category}
            onClick={()=>onCategory(categoryFilter===category?'':category)}>{category}</button>:(cs?'Neuvedeno':'Unspecified')}</th>
          <td>{count.total}</td><td>{count.published}</td>
        </tr>)}</tbody></table></div>
    </details>
    <p className="status">{cs?'Nepublikovaný výsledek neznamená automaticky neodehraný turnaj. Dostupnost losu, kvalifikace, zápasů ani hratelnost tato projekce nepotvrzuje.':
      'An unpublished result does not necessarily mean unplayed. This projection does not establish draw, qualification, match or playability readiness.'}</p>
  </section>
}
