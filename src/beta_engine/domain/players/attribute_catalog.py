"""The single canonical pre-alpha player attribute catalogue."""

from __future__ import annotations

ATTRIBUTE_GROUPS: dict[str, tuple[str, ...]] = {
    "Technical": (
        "Forehand",
        "Backhand",
        "Volley",
        "Drop Shot",
        "Lob",
        "Boast",
        "Precision",
        "Variability",
        "Power",
        "Control",
    ),
    "Move": (
        "Footwork",
        "Range",
        "Positioning",
        "Efficiency",
        "Balance",
        "Explosiveness",
        "Hustle",
        "Court Dominance",
        "Blocking",
    ),
    "Tactics": (
        "Anticipation",
        "Shot Selection",
        "Pace",
        "Adaptability",
        "Analysis",
        "Offense",
        "Defense",
        "Listening",
        "Vision",
    ),
    "Mental": (
        "Focus",
        "Composure",
        "Consistency",
        "Patience",
        "Aggressiveness",
        "Confidence",
        "Self Control",
        "Discipline",
        "Motivation",
        "Toughness",
    ),
    "Physical": (
        "Speed",
        "Stamina",
        "Endurance",
        "Strength",
        "Flexibility",
        "Reflexes",
        "Coordination",
        "Agility",
        "Durability",
    ),
    "Creativity": (
        "Improvisation",
        "Risk Taking",
        "Unpredictability",
        "Flair",
        "Winner",
        "Deception",
        "Trick shots",
        "Racket skill",
        "Spin",
        "Touch",
    ),
}

CANONICAL_PLAYER_ATTRIBUTES: tuple[str, ...] = tuple(
    attribute for attributes in ATTRIBUTE_GROUPS.values() for attribute in attributes
)
ATTRIBUTE_TO_GROUP = {
    attribute: group
    for group, attributes in ATTRIBUTE_GROUPS.items()
    for attribute in attributes
}

assert len(CANONICAL_PLAYER_ATTRIBUTES) == len(set(CANONICAL_PLAYER_ATTRIBUTES)) == 57
