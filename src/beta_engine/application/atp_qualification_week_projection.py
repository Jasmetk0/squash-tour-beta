"""Project sourced Q dates into week labels, without authoring execution slots."""

from datetime import date, timedelta


def project_qualification_window(calendar, profile):
    evidence = profile.qualification_date_evidence
    if evidence is None:
        return None
    if calendar.weeks_per_year != 52:
        raise ValueError('ATP Qualification ISO labels require a W52 Run')
    start, end = date.fromisoformat(evidence.start_date), date.fromisoformat(evidence.end_date)
    monday = start - timedelta(days=start.weekday())
    labels, weeks, ordinals, conflicts = [], [], [], []
    while monday <= end:
        year, week, _ = monday.isocalendar()
        label = {'calendar_year': year, 'year_week': week}
        labels.append(label)
        position = calendar.calendar_to_season(year, week) if week <= 52 else None
        if position is None:
            conflicts.append({**label, 'reason': 'iso_week_53_not_representable' if week == 53 else 'outside_run_horizon'})
        else:
            weeks.append({'season_index': position.season_index, 'season_week': position.season_week})
            ordinals.append(calendar.ordinal(position.season_index, position.season_week))
        monday += timedelta(days=7)
    result = {
        'schema_version': 'atp_qualification_week_projection.v1',
        'source_start_date': evidence.start_date, 'source_end_date': evidence.end_date,
        'source_urls': list(evidence.source_urls), 'source_published_dates': list(evidence.published_dates),
        'iso_year_weeks': labels, 'outside_year_weeks': conflicts,
        'mapping_policy': 'iso_week_label_to_W52_not_date_authority.v1',
        'sporting_execution_ready': False,
    }
    # A partially represented phase is not an executable whole-phase schedule.
    if not conflicts:
        result.update(run_weeks=weeks, run_ordinals=ordinals)
    return result
