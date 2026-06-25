from app.services.twd_features.constants import DISC_NAME_CODE, CardFeatures
from app.services.twd_features.helpers import safe_ratio


def cross_features(
    crypt_feats: CardFeatures,
    lib_feats: CardFeatures,
) -> CardFeatures:
    """Features that combine crypt and library information.

    The most important cross-feature is discipline overlap: how well the
    library's discipline requirements match the disciplines actually
    available in the crypt. A high overlap means the library cards can
    actually be played by the crypt's vampires.
    """
    feats: CardFeatures = {}

    crypt_total = int(crypt_feats.get("crypt_total", 0))
    lib_total = int(lib_feats.get("lib_total", 0))
    total = crypt_total + lib_total

    feats["crypt_library_ratio"] = safe_ratio(crypt_total, lib_total)

    if not total:
        return feats

    # Discipline overlap: for each discipline in the library, check if the
    # crypt has it at any level. Weighted by library discipline slot count.
    lib_disc_keys = {
        k[len("lib_disc_") :]: v
        for k, v in lib_feats.items()
        if k.startswith("lib_disc_") and isinstance(v, float)
    }

    if lib_disc_keys:
        total_lib_disc_weight = sum(lib_disc_keys.values())
        overlap_weight = 0.0
        for disc_name, lib_share in lib_disc_keys.items():
            code = DISC_NAME_CODE.get(disc_name)  # lookup exacte
            if code is not None and crypt_feats.get(f"crypt_disc_{code}", 0.0) > 0:
                overlap_weight += lib_share
        feats["disc_overlap_ratio"] = safe_ratio(overlap_weight, total_lib_disc_weight)
    else:
        feats["disc_overlap_ratio"] = 1.0  # no disc requirement = always playable

    # Strategy signals derived from trait combinations
    # These are intentionally coarse — they label broad archetypes.
    stealth = float(lib_feats.get("lib_trait_stealth", 0.0))
    intercept = float(lib_feats.get("lib_trait_intercept", 0.0))
    bleed = float(lib_feats.get("lib_trait_bleed", 0.0))
    votes = float(lib_feats.get("lib_trait_votes_title", 0.0))
    unlock = float(lib_feats.get("lib_trait_unlock", 0.0))
    bounce = float(lib_feats.get("lib_trait_bounce_bleed", 0.0))
    block_denial = float(lib_feats.get("lib_trait_block_denial", 0.0))
    combat = (
        float(lib_feats.get("lib_trait_aggravated", 0.0))
        + float(lib_feats.get("lib_trait_additional_strike", 0.0))
        + float(lib_feats.get("lib_trait_strength", 0.0))
        + float(lib_feats.get("lib_trait_maneuver", 0.0))
    )

    feats["signal_stealth_bleed"] = stealth + bleed
    feats["signal_intercept_rush"] = intercept + combat
    feats["signal_vote"] = votes
    feats["signal_wall"] = intercept + unlock
    feats["signal_bounce"] = bounce + block_denial

    return feats
