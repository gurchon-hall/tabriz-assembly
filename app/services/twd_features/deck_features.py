import re
from collections import defaultdict

from app.models.tournament import DeckLibraryCard
from app.models.vtes import LibraryCard
from app.services.twd_features.constants import LIBRARY_TRAITS_REGEX, CardFeatures
from app.services.twd_features.helpers import (
    classify_era,
    get_lib_sect_req,
    parse_cost,
    parse_disc_names,
    parse_disc_tags,
    safe_ratio,
)


def library_deck_features(
    dl_rows: list[DeckLibraryCard],
) -> CardFeatures:
    """Aggregate library card features into deck-level library features.

    All features are prefixed with `lib_` to avoid collisions.
    """
    feats: CardFeatures = {}

    resolved = [
        (dl.library_card, dl.count)
        for dl in dl_rows
        if dl.library_card is not None and dl.count > 0
    ]
    if not resolved:
        return feats

    total_slots = sum(count for _, count in resolved)
    feats["lib_total"] = total_slots

    # Accumulators
    type_counts: dict[str, int] = defaultdict(int)
    pool_cost_sum = 0
    blood_cost_sum = 0
    pool_cost_x_slots = 0
    blood_cost_x_slots = 0
    free_slots = 0
    disc_name_counts: dict[str, int] = defaultdict(int)
    alt_disc_slots = 0
    multi_disc_slots = 0
    no_req_slots = 0
    trifle_slots = 0
    burn_option_slots = 0
    clan_req_counts: dict[str, int] = defaultdict(int)
    sect_req_counts: dict[str, int] = defaultdict(int)
    path_req_counts: dict[str, int] = defaultdict(int)
    era_pre_slots = 0
    era_post_slots = 0
    printed_pre_slots = 0
    printed_post_slots = 0
    trait_counts: dict[str, int] = defaultdict(int)
    multi_type_slots = 0

    for card, count in resolved:
        lf = _library_card_features(card)

        # Types
        types = [t.strip() for t in card.type.split("/") if t.strip()] if card.type else []
        for t in types:
            type_counts[t.lower().replace(" ", "_")] += count
        if len(types) > 1:
            multi_type_slots += count

        # Costs
        pool = parse_cost(card.pool_cost)
        blood = parse_cost(card.blood_cost)
        if pool == "X":
            pool_cost_x_slots += count
        elif isinstance(pool, int) and pool > 0:
            pool_cost_sum += pool * count
        if blood == "X":
            blood_cost_x_slots += count
        elif isinstance(blood, int) and blood > 0:
            blood_cost_sum += blood * count

        if lf.get("is_free"):
            free_slots += count

        # Discipline requirements
        disc_raw = card.discipline or ""
        disc_names = parse_disc_names(disc_raw)
        for name in disc_names:
            disc_name_counts[name] += count
        if "&" in disc_raw:
            alt_disc_slots += count
        if "/" in disc_raw:
            multi_disc_slots += count

        # Other booleans
        if lf.get("no_requirements"):
            no_req_slots += count
        if lf.get("trifle"):
            trifle_slots += count
        if lf.get("has_burn_option"):
            burn_option_slots += count

        # Clan requirement
        if card.clan and card.clan.strip():
            clan_key = card.clan.lower().replace(" ", "_")
            clan_req_counts[clan_key] += count

        # Sect requirement (from LibraryMeta requirement field)
        sect_req = get_lib_sect_req(card.requirement or "")
        if sect_req != "none":
            sect_req_counts[sect_req] += count

        # Path requirement
        path_key = card.path.strip().lower().replace(" ", "_") if card.path.strip() else "none"
        path_req_counts[path_key] += count

        # Era
        era = classify_era(card)
        if era.get("firstprint"):
            era_post_slots += count
        else:
            era_pre_slots += count
        if era.get("n_print_pre", 0) > 0:
            printed_pre_slots += count
        if era.get("n_print_post", 0) > 0:
            printed_post_slots += count

        # Traits (VDB regex map)
        card_text = (card.card_text or "").strip()
        for trait_name, pattern in LIBRARY_TRAITS_REGEX.items():
            if pattern.search(card_text):
                trait_counts[trait_name] += count

    # --- Ratios ---
    feats["lib_avg_pool_cost"] = safe_ratio(pool_cost_sum, total_slots)
    feats["lib_avg_blood_cost"] = safe_ratio(blood_cost_sum, total_slots)
    feats["lib_pct_pool_cost_x"] = safe_ratio(pool_cost_x_slots, total_slots)
    feats["lib_pct_blood_cost_x"] = safe_ratio(blood_cost_x_slots, total_slots)
    feats["lib_pct_free"] = safe_ratio(free_slots, total_slots)
    feats["lib_pct_no_requirements"] = safe_ratio(no_req_slots, total_slots)
    feats["lib_pct_trifle"] = safe_ratio(trifle_slots, total_slots)
    feats["lib_pct_burn_option"] = safe_ratio(burn_option_slots, total_slots)
    feats["lib_pct_multi_type"] = safe_ratio(multi_type_slots, total_slots)
    feats["lib_pct_alt_disc"] = safe_ratio(alt_disc_slots, total_slots)
    feats["lib_pct_multi_disc"] = safe_ratio(multi_disc_slots, total_slots)
    feats["lib_pct_era_v5plus"] = safe_ratio(era_post_slots, total_slots)
    feats["lib_pct_era_pre_v5"] = safe_ratio(era_pre_slots, total_slots)
    feats["lib_pct_printed_pre_v5"] = safe_ratio(printed_pre_slots, total_slots)
    feats["lib_pct_printed_post_v5"] = safe_ratio(printed_post_slots, total_slots)

    # Type shares
    for type_name, cnt in type_counts.items():
        feats[f"lib_type_{type_name}"] = safe_ratio(cnt, total_slots)

    # Discipline requirement shares
    for name, cnt in disc_name_counts.items():
        feats[f"lib_disc_{name.replace(' ', '_')}"] = safe_ratio(cnt, total_slots)

    # Clan requirement shares
    for clan, cnt in clan_req_counts.items():
        feats[f"lib_req_clan_{clan}"] = safe_ratio(cnt, total_slots)

    # Sect requirement shares
    for sect, cnt in sect_req_counts.items():
        feats[f"lib_req_sect_{sect}"] = safe_ratio(cnt, total_slots)

    # Path requirement shares
    for path, cnt in path_req_counts.items():
        feats[f"lib_req_path_{path}"] = safe_ratio(cnt, total_slots)

    # Trait shares
    for trait_name, cnt in trait_counts.items():
        feats[f"lib_trait_{trait_name}"] = safe_ratio(cnt, total_slots)

    return feats


def _library_card_features(card: LibraryCard) -> CardFeatures:
    features: CardFeatures = {}
    features.update(**classify_era(card))

    # --- Card type ---
    types = [t.strip() for t in card.type.split("/") if t.strip()] if card.type else []
    for t in types:
        features[f"type_{t.lower().replace(' ', '_')}"] = True
    features["nb_types"] = len(types)

    # --- Cost ---
    pool_cost = parse_cost(card.pool_cost)
    blood_cost = parse_cost(card.blood_cost)
    conviction_cost = parse_cost(card.conviction_cost)

    features["pool_cost"] = (
        pool_cost if isinstance(pool_cost, int) else (-1 if pool_cost == "X" else 0)
    )
    features["blood_cost"] = (
        blood_cost if isinstance(blood_cost, int) else (-1 if blood_cost == "X" else 0)
    )
    features["conviction_cost"] = (
        conviction_cost
        if isinstance(conviction_cost, int)
        else (-1 if conviction_cost == "X" else 0)
    )
    features["pool_cost_is_x"] = pool_cost == "X"
    features["blood_cost_is_x"] = blood_cost == "X"
    features["is_free"] = (
        (pool_cost is None or pool_cost == 0)
        and (blood_cost is None or blood_cost == 0)
        and (conviction_cost is None or conviction_cost == 0)
    )

    # --- Discipline requirement ---
    disc_raw = card.discipline or ""
    disc_names = parse_disc_names(disc_raw)
    features["has_discipline"] = len(disc_names) > 0
    features["nb_disciplines"] = len(disc_names)
    features["has_superior"] = len(parse_disc_tags(card.card_text)[1]) > 0
    features["has_alt_disc"] = "&" in disc_raw  # either-or requirement
    features["has_multi_disc"] = "/" in disc_raw  # requires all listed disciplines
    for name in disc_names:
        features[f"discipline_{name.lower().replace(' ', '_')}"] = True

    # --- Clan / requirement restriction ---
    features["has_clan_req"] = False
    if req_clan := card.clan.lower().strip():
        features[f"req_clan_{req_clan}"] = True
        features["has_clan_req"] = True
    features["has_requirement"] = bool(card.requirement and card.requirement.strip())

    # --- Burn option ---
    features["has_burn_option"] = bool(card.burn_option)

    # --- No requirements (VDB NO_REQUIREMENTS filter logic from cardFilters.js) ---
    # A card has NO_REQUIREMENTS if it has no clan, no discipline, no 'requires a' in text.
    card_text = (card.card_text or "").strip()
    features["no_requirements"] = (
        not features["has_clan_req"]
        and not features["has_discipline"]
        and not re.search(r"requires a", card_text, re.IGNORECASE)
    )

    # --- Trifle (Master only) ---
    is_master = "master" in card.type.lower() if card.type else False
    features["trifle"] = is_master and bool(re.search(r"\btrifle\b", card_text, re.IGNORECASE))

    # --- Multi-type / multi-discipline (VDB MULTI_TYPE / MULTI_DISCIPLINE) ---
    features["multi_type"] = "/" in (card.type or "")
    features["multi_discipline"] = "/" in disc_raw or "&" in disc_raw

    # --- Trait booleans from card_text (VDB LibraryTraitsRegexMap) ---
    for trait_name, pattern in LIBRARY_TRAITS_REGEX.items():
        features[f"trait_{trait_name}"] = bool(pattern.search(card_text))

    return features
