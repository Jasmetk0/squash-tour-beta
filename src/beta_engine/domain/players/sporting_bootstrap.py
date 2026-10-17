"""Pure existing provisional 7→57 bootstrap adapter, separate from any time axis."""
import hashlib
import json
from beta_engine.domain.players.attribute_catalog import ATTRIBUTE_GROUPS
from beta_engine.domain.players.sporting import PlayerSportingRecord, PlayerSportingBootstrapPolicy

def _legacy_group_value(player, group: str) -> int:
    values = player.attributes
    return {
        "Technical": values.technique,
        "Move": values.movement,
        "Tactics": round((values.technique + values.mental) / 2),
        "Mental": values.mental,
        "Physical": values.physical,
        "Creativity": round((values.technique + values.clutch) / 2),
    }[group]



def derive_bootstrap_record(player, policy: PlayerSportingBootstrapPolicy):
    """Materialize current owned source facts; no historical/annual development."""
    attributes = {}
    for group, names in ATTRIBUTE_GROUPS.items():
        source = _legacy_group_value(player, group)
        for name in names:
            digest = hashlib.blake2b(
                f"{policy.policy_id}|{player.source_generation_fingerprint}|{name}".encode(),
                digest_size=8,
            ).digest()
            width = policy.deterministic_jitter
            jitter = int.from_bytes(digest, "big") % (width * 2 + 1) - width
            attributes[name] = min(
                200,
                max(
                    0,
                    round(
                        source
                        * policy.scale_numerator
                        / policy.scale_denominator
                    )
                    + jitter,
                ),
            )
    growth = player.hidden_career_traits.growth_curve.lower()
    timing = (
        "Early Bloomer"
        if "early" in growth
        else "Late Bloomer"
        if "late" in growth
        else "Standard"
    )
    potential_payload = {
        "player_id": player.player_id,
        "source": player.source_generation_fingerprint,
        "legacy_potential": player.potential_ability,
        "bootstrap_policy": policy.model_dump(mode="json"),
    }
    potential_provenance = json.dumps(
        potential_payload, sort_keys=True, separators=(",", ":")
    )
    return PlayerSportingRecord(
        player_id=player.player_id,
        attributes=tuple(attributes.items()),
        potential_ovr=min(200, round(player.potential_ability * 200 / 99)),
        potential_identity=hashlib.sha256(
            potential_provenance.encode()
        ).hexdigest(),
        potential_provenance=potential_provenance,
        development_timing=timing,
        current_form=policy.default_form,
        long_term_form_norm=policy.default_form_norm,
        match_sharpness=policy.default_match_sharpness,
        long_term_fatigue=policy.default_fatigue,
    )
