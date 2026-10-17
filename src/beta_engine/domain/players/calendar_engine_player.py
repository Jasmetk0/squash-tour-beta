"""Pure, historical seven-value InitialWorld → MatchEngine compatibility adapter."""
from beta_engine.domain.players.models import Player


def calendar_engine_player(profile) -> Player:
    # v2 initial population is currently seven-value, rather than a
    # sporting 57-attribute week state. The conversion is an explicit
    # compatibility projection, not claims of completed development.
    a = profile.attributes
    return Player(
        player_id=profile.player_id,
        name=profile.name,
        age=profile.age_years_at_season_start,
        nationality=profile.nationality,
        technique=max(1, min(99, a.technique)),
        movement=max(1, min(99, a.movement)),
        physical=max(1, min(99, a.physical)),
        mental=max(1, min(99, a.mental)),
        consistency=max(1, min(99, a.consistency)),
        clutch=max(1, min(99, a.clutch)),
        recovery=max(1, min(99, a.recovery)),
        play_style=profile.play_style,
        archetype=profile.archetype,
        hidden_career_traits=profile.hidden_career_traits,
    )
