from __future__ import annotations


def write_complete_templates(path):
    path.write_text(
        '{"templates":[{"template_id":"wt_complete","tour_level":"WORLD_TOUR","category":"PLATINUM","event_name":"World Complete","region":"EUROPE","host_country":"AAA","main_draw_size":4,"qualification_draw_size":0,"seeds_count":2,"qualifier_spots":0,"wild_cards":0,"byes":0,"lucky_loser_rules":{"enabled":false,"max_spots":0,"replacement_window":"pre_main_draw_round_1"},"point_distribution_ref":"world","prize_money":100000,"prestige":9,"event_duration_days":4,"qualification_duration_days":0,"duration_in_season_weeks":1,"active":true}]}',
        encoding='utf-8',
    )
