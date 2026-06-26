import datetime as dt
import re

from app.models import Set

# --------------------------------
# Types
# --------------------------------
CardFeatures = dict[str, bool | int | float]

# ---------------------------------------------------------------------------
# Discipline code → full name mapping
# Source of truth: verified against vtescrypt.csv + live DB queries
# (tha/thn order confirmed: THA = Thaumaturgy, THN = Thanatosis)
# ---------------------------------------------------------------------------
DISC_CODE_NAME: dict[str, str] = {
    "abo": "Abombwe",
    "ani": "Animalism",
    "aus": "Auspex",
    "cel": "Celerity",
    "chi": "Chimerstry",
    "dai": "Daimoinon",
    "dem": "Dementation",
    "dom": "Dominate",
    "for": "Fortitude",
    "mal": "Maleficia",
    "mel": "Melpominee",
    "myt": "Mytherceria",
    "nec": "Necromancy",
    "obe": "Obeah",
    "obf": "Obfuscate",
    "obl": "Oblivion",
    "obt": "Obtenebration",
    "pot": "Potence",
    "pre": "Presence",
    "pro": "Protean",
    "qui": "Quietus",
    "san": "Sanguinus",
    "ser": "Serpentis",
    "spi": "Spiritus",
    "str": "Striga",
    "tem": "Temporis",
    "tha": "Thaumaturgy",
    "thn": "Thanatosis",
    "val": "Valeren",
    "vic": "Vicissitude",
    "vis": "Visceratika",
}
DISC_NAME_CODE: dict[str, str] = {v: k for k, v in DISC_CODE_NAME.items()}

# --------------------------------
# Sets and Dates
# --------------------------------
V5_RELEASE_DATE = dt.date(2020, 11, 30)
DATE = dt.date.today()
DUMMY_SET = Set(
    id=399999,
    release_date=DATE,
    full_name="Dummy Set",
    abbrev="Dummy",
    company="Gurchon Hall",
)

# --------------------------------
# Titles and votes
# --------------------------------
TITLE_TO_VOTES = {
    "primogen": 1,
    "prince": 2,
    "justicar": 3,
    "inner circle": 4,
    "baron": 2,
    "1 vote": 1,
    "2 votes": 2,
    "bishop": 1,
    "archbishop": 2,
    "priscus": 3,
    "cardinal": 3,
    "regent": 4,
    "magaji": 2,
}

# --------------------------------
# Regex
# --------------------------------
CONDITIONS_RE: list[re.Pattern[str]] = [re.compile(r"\bif\b"), re.compile(r"\bagainst\b")]
BONUS_RE = [
    ("bleed_bonus", re.compile(r"\+\d+ bleed")),
    ("stealth_bonus", re.compile(r"\+\d+ stealth")),
    ("intercept_bonus", re.compile(r"\+\d+ intercept")),
    ("strength_bonus", re.compile(r"\+\d+ strength")),
]
LINE_START_TAG_RE = re.compile(
    r"(?:^|\n)[ \t]*\[([A-Za-z]{2,4})\](?=[ \t]|$)",
    re.MULTILINE,
)

# ---------------------------------------------------------------------------
# LibraryTraitsRegexMap — direct translation from traitsRegexMaps.js
#
# Source: smeea/vdb @ frontend/src/utils/traitsRegexMaps.js
# Each entry maps a trait name to a compiled regex that is tested against
# the card's card_text (case-insensitive, same as JS's /i flag).
# ---------------------------------------------------------------------------
# --------------------------------
# Sects
# --------------------------------
KNOWN_SECTS: set[str] = {"independent", "sabbat", "camarilla", "anarch", "laibon"}

REQUIREMENT_TO_SECT: dict[str, str] = {
    "baron": "anarch",
    "prince": "camarilla",
    "primogen": "camarilla",
    "justicar": "camarilla",
    "inner circle": "camarilla",
    "bishop": "sabbat",
    "archbishop": "sabbat",
    "priscus": "sabbat",
    "cardinal": "sabbat",
    "regent": "sabbat",
    "magaji": "laibon",
}

# ---------------------------------------------------------------------------
# LibraryTraitsRegexMap — direct translation from traitsRegexMaps.js
#
# Source: smeea/vdb @ frontend/src/utils/traitsRegexMaps.js
# Each entry maps a trait name to a compiled regex that is tested against
# the card's card_text (case-insensitive, same as JS's /i flag).
# ---------------------------------------------------------------------------
LIBRARY_TRAITS_REGEX: dict[str, re.Pattern[str]] = {
    # "+Intercept / -Stealth": intercept cards or stealth-denial cards
    "intercept": re.compile(
        (
            r"-\d+ stealth(?! \(d\))(?! \w)(?! action)|\+\d+ intercept"
            r"|gets -(\d|x)+ stealth|stealth to 0"
        ),
        re.IGNORECASE,
    ),
    # "+Stealth / -Intercept": stealth cards or intercept-denial cards
    "stealth": re.compile(
        r"\+\d+ stealth(?! (action|equip|hunt|employ|political|\(d\)))|-\d+ intercept",
        re.IGNORECASE,
    ),
    # "+Bleed": any bleed bonus
    "bleed": re.compile(r"\+(\d+|X) bleed", re.IGNORECASE),
    # "Block Denial": cannot block effects
    "block_denial": re.compile(r"cannot (attempt to )?block", re.IGNORECASE),
    # "+Strength": strength bonus
    "strength": re.compile(r"\+\d+ strength", re.IGNORECASE),
    # "Dodge": dodge
    "dodge": re.compile(r"\bdodge\b", re.IGNORECASE),
    # "Maneuver"
    "maneuver": re.compile(r"\bmaneuver\b", re.IGNORECASE),
    # "Additional Strike"
    "additional_strike": re.compile(r"additional strike", re.IGNORECASE),
    # "Aggravated" damage
    "aggravated": re.compile(r"(?<!\bnon-)aggravated", re.IGNORECASE),
    # "Prevent" damage
    "prevent": re.compile(r"(?<!\bun)prevent(?!able)", re.IGNORECASE),
    # "Press"
    "press": re.compile(r"\bpress\b", re.IGNORECASE),
    # "Combat Ends"
    "combat_ends": re.compile(r"combat ends", re.IGNORECASE),
    # "Enter Combat": force combat
    "enter_combat": re.compile(r"\benter combat\b", re.IGNORECASE),
    # "Create Vampire" (Embrace)
    "embrace": re.compile(r"becomes a.*(\d[ -]|same.*)capacity", re.IGNORECASE),
    # "Blood to Uncontrolled": put blood on uncontrolled vampire
    "put_blood": re.compile(
        r"(move|add) .* blood (from the blood bank )?to .* in your uncontrolled region",
        re.IGNORECASE,
    ),
    # "Bounce Bleed": redirect bleeds
    "bounce_bleed": re.compile(r"change the target of the bleed|is now bleeding", re.IGNORECASE),
    # "Reduce Bleed"
    "reduce_bleed": re.compile(
        r"reduce (a|the)(.*) bleed (amount)?|bleed amount is reduced", re.IGNORECASE
    ),
    # "Wake / Unlock"
    "unlock": re.compile(r"(?<!not )unlock(?! phase|ed)|wakes", re.IGNORECASE),
    # "+Votes / Title"
    "votes_title": re.compile(
        r"receive .* title|gains . vote|\+. vote|additional vote|represent the .* title",
        re.IGNORECASE,
    ),
}
