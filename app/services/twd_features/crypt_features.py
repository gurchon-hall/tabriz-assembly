import re
from collections import defaultdict

from app.models import CryptCard, DeckCryptCard
from app.services.twd_features.constants import (
    BONUS_RE,
    CONDITIONS_RE,
    TITLE_TO_VOTES,
    CardFeatures,
)
from app.services.twd_features.helpers import classify_era, get_crypt_sect, safe_ratio


def crypt_deck_features(
    dc_rows: list[DeckCryptCard],
) -> CardFeatures:
    """Aggregate crypt card features into deck-level crypt features.

    All features are prefixed with `crypt_` to avoid collisions with
    library features when the two dicts are merged.
    """
    feats: CardFeatures = {}

    # Only rows that resolved to a known crypt card.
    resolved = [
        (dc.crypt_card, dc.count) for dc in dc_rows if dc.crypt_card is not None and dc.count > 0
    ]
    if not resolved:
        return feats

    total_slots = sum(count for _, count in resolved)
    feats["crypt_total"] = total_slots

    # Accumulators
    capacity_sum = 0.0
    sup_disc_sum = 0.0
    nb_disc_sum = 0.0
    nb_votes_sum = 0.0
    card_points_sum = 0.0
    clan_counts: dict[str, int] = defaultdict(int)
    sect_counts: dict[str, int] = defaultdict(int)
    path_counts: dict[str, int] = defaultdict(int)
    group_counts: dict[str, int] = defaultdict(int)
    disc_base_counts: dict[str, int] = defaultdict(int)  # inferior or superior
    disc_sup_counts: dict[str, int] = defaultdict(int)  # superior only
    era_pre_slots = 0
    era_post_slots = 0
    uncond_bleed = 0
    uncond_stealth = 0
    uncond_intercept = 0
    uncond_strength = 0
    cond_bleed = 0
    cond_stealth = 0
    cond_intercept = 0
    cond_strength = 0

    for card, count in resolved:
        cf = _crypt_card_features(card)

        capacity_sum += card.capacity * count
        nb_disc_sum += cf.get("nb_disc", 0) * count
        sup_disc_sum += cf.get("nb_sup_disc", 0) * count
        nb_votes_sum += cf.get("nb_votes", 0) * count
        card_points_sum += cf.get("card_points_for_capacity", 0.0) * count

        # Clan / group / sect / path
        clan_key = card.clan.lower().replace(" ", "_")
        clan_counts[clan_key] += count
        group_counts[str(card.group).lower()] += count
        sect_counts[get_crypt_sect(card.card_text)] += count
        path_key = card.path.strip().lower().replace(" ", "_") if card.path.strip() else "none"
        path_counts[path_key] += count

        # Disciplines
        for tok in card.disciplines.split():
            tok = tok.strip()
            if not tok:
                continue
            code = tok.lower()
            disc_base_counts[code] += count
            if tok == tok.upper():
                disc_sup_counts[code] += count

        # Era
        era = classify_era(card)
        if era.get("firstprint"):  # first_print is V5+
            era_post_slots += count
        else:
            era_pre_slots += count

        # Conditional / unconditional bonuses
        text = card.card_text.strip().lower()
        is_cond = all(c.search(text) for c in CONDITIONS_RE)
        if is_cond:
            cond_bleed += count if re.search(r"\+\d+ bleed", text) else 0
            cond_stealth += count if re.search(r"\+\d+ stealth", text) else 0
            cond_intercept += count if re.search(r"\+\d+ intercept", text) else 0
            cond_strength += count if re.search(r"\+\d+ strength", text) else 0
        else:
            uncond_bleed += count if re.search(r"\+\d+ bleed", text) else 0
            uncond_stealth += count if re.search(r"\+\d+ stealth", text) else 0
            uncond_intercept += count if re.search(r"\+\d+ intercept", text) else 0
            uncond_strength += count if re.search(r"\+\d+ strength", text) else 0

    # --- Ratios and averages ---
    feats["crypt_avg_capacity"] = safe_ratio(capacity_sum, total_slots)
    feats["crypt_avg_nb_disc"] = safe_ratio(nb_disc_sum, total_slots)
    feats["crypt_avg_nb_sup_disc"] = safe_ratio(sup_disc_sum, total_slots)
    feats["crypt_avg_nb_votes"] = safe_ratio(nb_votes_sum, total_slots)
    feats["crypt_avg_card_points_for_capacity"] = safe_ratio(card_points_sum, total_slots)

    feats["crypt_pct_era_v5plus"] = safe_ratio(era_post_slots, total_slots)
    feats["crypt_pct_era_pre_v5"] = safe_ratio(era_pre_slots, total_slots)

    feats["crypt_pct_uncond_bleed"] = safe_ratio(uncond_bleed, total_slots)
    feats["crypt_pct_uncond_stealth"] = safe_ratio(uncond_stealth, total_slots)
    feats["crypt_pct_uncond_intercept"] = safe_ratio(uncond_intercept, total_slots)
    feats["crypt_pct_uncond_strength"] = safe_ratio(uncond_strength, total_slots)
    feats["crypt_pct_cond_bleed"] = safe_ratio(cond_bleed, total_slots)
    feats["crypt_pct_cond_stealth"] = safe_ratio(cond_stealth, total_slots)
    feats["crypt_pct_cond_intercept"] = safe_ratio(cond_intercept, total_slots)
    feats["crypt_pct_cond_strength"] = safe_ratio(cond_strength, total_slots)

    # Clan and group shares (ratio of crypt slots)
    for clan, cnt in clan_counts.items():
        feats[f"crypt_clan_{clan}"] = safe_ratio(cnt, total_slots)
    for group, cnt in group_counts.items():
        feats[f"crypt_group_{group}"] = safe_ratio(cnt, total_slots)

    # Discipline shares (base level = inferior or superior present)
    for code, cnt in disc_base_counts.items():
        feats[f"crypt_disc_{code}"] = safe_ratio(cnt, total_slots)
    # Superior level shares
    for code, cnt in disc_sup_counts.items():
        feats[f"crypt_sup_{code}"] = safe_ratio(cnt, total_slots)

    # Sect shares
    for sect, cnt in sect_counts.items():
        feats[f"crypt_sect_{sect}"] = safe_ratio(cnt, total_slots)
    feats["crypt_is_monosect"] = len(sect_counts) == 1

    # Path shares
    for path, cnt in path_counts.items():
        feats[f"crypt_path_{path}"] = safe_ratio(cnt, total_slots)

    # Dominant clan detection (>50% of slots)
    dominant_clans = [
        clan for clan, cnt in clan_counts.items() if safe_ratio(cnt, total_slots) > 0.50
    ]
    feats["crypt_is_monoclan"] = len(clan_counts) == 1
    feats["crypt_has_dominant_clan"] = len(dominant_clans) > 0

    # Star vampire detection (one vampire > 33% of slots)
    feats["crypt_has_star_vampire"] = any(
        safe_ratio(cnt, total_slots) > 0.33
        for cnt in {card.id: 0 for card, _ in resolved}.values()  # placeholder
    )
    # Recompute properly: group by card identity
    per_card_count: dict[tuple[int, str, bool], int] = defaultdict(int)
    for card, count in resolved:
        per_card_count[(card.id, card.group, card.adv)] += count
    feats["crypt_has_star_vampire"] = any(
        safe_ratio(cnt, total_slots) > 0.33 for cnt in per_card_count.values()
    )

    return feats


def _crypt_card_features(card: CryptCard) -> CardFeatures:
    features: CardFeatures = {}
    features.update(**classify_era(card))

    features[f"clan_{card.clan.lower().replace(' ', '_')}"] = True
    features[f"group_{card.group.lower()}"] = True

    features["capacity"] = card.capacity

    disciplines = [d.strip() for d in card.disciplines.split() if d.strip()]
    features["nb_disc"] = len(disciplines)
    features["nb_sup_disc"] = len([d for d in disciplines if d == d.upper()])
    for disc in disciplines:
        features[f"disc_{disc.lower()}"] = 1
        if disc.isupper():
            features[f"has_sup_{disc.lower()}"] = True

    features["nb_votes"] = TITLE_TO_VOTES.get(card.title.lower().strip(), 0)

    card_text = card.card_text.strip().lower()
    is_conditional = all(c.search(card_text) for c in CONDITIONS_RE)
    prefix = "cond" if is_conditional else "uncond"
    for name, pattern in BONUS_RE:
        features[f"has_{prefix}_{name}"] = bool(pattern.search(card_text))

    features["sup_disc_for_capacity"] = features["nb_sup_disc"] / max(features["capacity"], 1)
    features["nb_votes_for_capacity"] = features["nb_votes"] / max(features["capacity"], 1)

    features["card_points_for_capacity"] = (
        features["nb_disc"]  # 1 level of disc = 1 point
        + features["nb_sup_disc"]  # 1 level of disc = 1 point
        + features["nb_votes"]  # 1 vote = 1 point
        + int(features.get("has_uncond_bleed_bonus", False))  # 1 unconditional bonus = 1 point
        + int(features.get("has_uncond_strength_bonus", False))  # 1 unconditional bonus = 1 point
        + int(features.get("has_uncond_stealth_bonus", False))  # 1 unconditional bonus = 1 point
        + int(features.get("has_uncond_intercept_bonus", False))  # 1 unconditional bonus = 1 point
    ) / max(features["capacity"], 1)

    return features
