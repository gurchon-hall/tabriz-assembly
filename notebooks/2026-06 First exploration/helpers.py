"""
helpers.py — shared parsing utilities for the VTES exploration notebooks.

Import from any notebook with:
    import sys; sys.path.insert(0, str(Path.cwd()))
    from helpers import *
"""

import re
from collections.abc import Iterable
from pathlib import Path
from typing import Any
from urllib.parse import quote

import numpy as np
import pandas as pd

SEED = 19940822  # First release of the game

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


# ---------------------------------------------------------------------------
# Crypt discipline parsing
# Format confirmed by DB query: space-separated codes, case = level.
# Placeholder "-none-" = no disciplines.
# ---------------------------------------------------------------------------
_DISCIPLINE_SEP_RE = re.compile(r"[,/\s]+")
_EMPTY_DISCIPLINE_TOKENS = {"", "-none-", "none", "n/a"}


def _split_discipline_codes(raw: str) -> list[str]:
    """Tokenize the crypt `disciplines` field into individual codes."""
    if not raw or raw.strip().lower() in _EMPTY_DISCIPLINE_TOKENS:
        return []
    return [t for t in _DISCIPLINE_SEP_RE.split(raw.strip()) if t]


def parse_crypt_disciplines(raw: str) -> tuple[set[str], set[str]]:
    """Parse crypt `disciplines` into (base_codes, superior_codes).

    base    = discipline present at any level (lowercase code)
    superior = discipline present at the superior level (originally uppercase)
    AUS == True implies aus == True; aus == True does NOT imply AUS == True.
    """
    base: set[str] = set()
    superior: set[str] = set()
    for tok in _split_discipline_codes(raw):
        code = tok.lower()
        base.add(code)
        if tok == tok.upper():
            superior.add(code)
    return base, superior


def discipline_boolean_matrix(base_sets: pd.Series, superior_sets: pd.Series) -> pd.DataFrame:
    """Build base (lowercase) + superior (UPPERCASE) boolean columns."""

    def _contains(s: set[str], c: str) -> bool:
        return c in s

    all_codes: set[str] = set()
    for s in base_sets:
        all_codes |= s
    data: dict[str, pd.Series[Any]] = {}
    for code in sorted(all_codes):
        data[code] = base_sets.apply(_contains, args=(code,))
        data[code.upper()] = superior_sets.apply(_contains, args=(code,))
    return pd.DataFrame(data, index=base_sets.index)


# ---------------------------------------------------------------------------
# Library discipline parsing
# Format confirmed by DB query: full Title-Case names separated by "&" or "/".
#
# Bracket tags in card_text ([dom], [AUS] …) have two distinct uses:
#   • Start of line → alternate-discipline version marker (structural).
#     Same uppercase = superior convention as crypt disciplines.
#     → USED via parse_line_start_discipline_tags().
#   • Mid-line      → inline discipline icon in effect text (e.g. "React
#     with Conviction": "requires Chimerstry [chi], Dominate [dom]…").
#     Describes other cards/minions, NOT this card.
#     → IGNORED by the regex.
# ---------------------------------------------------------------------------
_LIBRARY_DISCIPLINE_NAME_SEP_RE = re.compile(r"[&/,]+")

_LINE_START_TAG_RE = re.compile(
    r"(?:^|\n)[ \t]*\[([A-Za-z]{2,4})\](?=[ \t]|$)",
    re.MULTILINE,
)


def parse_library_discipline_names(raw: str) -> set[str]:
    """Parse library `discipline` field into a set of lowercased full names.

    No code abbreviation is attempted: the name→code mapping is stored in
    DISC_NAME_CODE for reference, but full names are used as column labels
    in library_disc_df to stay unambiguous.
    """
    if not raw or raw.strip().lower() in _EMPTY_DISCIPLINE_TOKENS:
        return set()
    return {
        t.strip().lower() for t in _LIBRARY_DISCIPLINE_NAME_SEP_RE.split(raw.strip()) if t.strip()
    }


def parse_line_start_discipline_tags(card_text: str) -> tuple[set[str], set[str]]:
    """Extract discipline tags at the START of a line in card_text.

    These mark alternate-discipline versions of the card (structural format).
    Same uppercase = superior convention as parse_crypt_disciplines:
      [dom] → inferior Dominate version
      [DOM] → superior Dominate version

    Mid-line tags (inline icons referencing other cards/minions) are excluded
    by the regex. Returns (base_codes, superior_codes).
    """
    base: set[str] = set()
    superior: set[str] = set()
    if not card_text:
        return base, superior
    for tok in _LINE_START_TAG_RE.findall(card_text):
        code = tok.lower()
        base.add(code)
        if tok == tok.upper():
            superior.add(code)
    return base, superior


# ---------------------------------------------------------------------------
# Shared utilities
# ---------------------------------------------------------------------------
def fit_transform(model: Any, data: Iterable[Any]) -> np.ndarray:
    result = model.fit_transform(data)
    if hasattr(result, "toarray"):
        return result.toarray()
    return np.asarray(result)


def fit_supervised(model: Any, X: Any, y: Any, **kwargs: Any) -> Any:
    return model.fit(X, y, **kwargs)


def normalize_rows(df: pd.DataFrame) -> pd.DataFrame:
    return df.div(df.sum(axis=1), axis=0)


def weighted_mean(df: pd.DataFrame, values: str, weights: str) -> float:
    return (df[values] * df[weights]).sum() / df[weights].sum()


def tolist(obj: Any) -> list[Any]:
    return list(obj)


def split_multi(raw: str, pattern: str = r"[/,]") -> list[str]:
    """Split a multi-valued string field that may contain spaces within values
    (e.g. library `type`: 'Action Modifier', 'Political Action').
    Does NOT split on whitespace — use _split_discipline_codes for that."""
    if not raw:
        return []
    return [t.strip() for t in re.split(pattern, raw) if t.strip()]


def classify_era(n_pre: float, n_post: float) -> str:
    """Classify a card's print history relative to V5."""
    n_pre = 0 if pd.isna(n_pre) else n_pre
    n_post = 0 if pd.isna(n_post) else n_post
    if n_pre > 0 and n_post > 0:
        return "both"
    if n_post > 0:
        return "V5+"
    if n_pre > 0:
        return "pre-V5"
    return "unknown"


def cost_to_numeric(value: object) -> float:
    if value is None:
        return float("nan")
    v = str(value).strip()
    if v == "" or v.upper() == "NONE":
        return float("nan")
    if v.upper() == "X":
        return -1.0
    try:
        return float(v)
    except ValueError:
        return float("nan")


def build_vdb_url(
    deck_id: str,
    df_decks: pd.DataFrame,
    df_deck_crypt: pd.DataFrame,
    df_deck_library: pd.DataFrame,
) -> tuple[str, int]:
    """Build a VDB deck-in-url link (#id=qty;...) from resolved card rows.

    Returns (url, n_skipped) where n_skipped is the number of rows that
    could not be resolved to a known card id and were therefore omitted.
    """
    deck_row = df_decks.loc[df_decks["id"] == deck_id].iloc[0]
    name = deck_row["name"] or "Untitled deck"
    author = deck_row["created_by"] or "Unknown"

    crypt_rows = df_deck_crypt[df_deck_crypt["deck_id"] == deck_id]
    crypt_ok = crypt_rows[crypt_rows["crypt_card_id"].notna() & (crypt_rows["count"] > 0)]
    crypt_items = sorted({(int(r.crypt_card_id), int(r["count"])) for _, r in crypt_ok.iterrows()})

    lib_rows = df_deck_library[df_deck_library["deck_id"] == deck_id]
    lib_ok = lib_rows[lib_rows["library_card_id"].notna() & (lib_rows["count"] > 0)]
    lib_items = sorted({(int(r.library_card_id), int(r["count"])) for _, r in lib_ok.iterrows()})

    n_skipped = (len(crypt_rows) - len(crypt_ok)) + (len(lib_rows) - len(lib_ok))
    fragment = ";".join(f"{cid}={qty}" for cid, qty in crypt_items + lib_items)
    url = (
        f"https://vdb.im/decks/deck?name={quote(str(name))}&author={quote(str(author))}#{fragment}"
    )
    return url, n_skipped


# ---------------------------------------------------------------------------
# Artifact I/O — paths shared across notebooks
# ---------------------------------------------------------------------------
DATA_DIR = Path(__file__).parent / "data"


def artifact_path(name: str) -> Path:
    return DATA_DIR / name
