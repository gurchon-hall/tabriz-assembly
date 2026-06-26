from app.models import CryptCard, LibraryCard
from app.services.twd_features.constants import (
    DATE,
    DUMMY_SET,
    KNOWN_SECTS,
    LINE_START_TAG_RE,
    REQUIREMENT_TO_SECT,
    V5_RELEASE_DATE,
)


def classify_era(card: CryptCard | LibraryCard) -> dict[str, int]:
    first_print = (card.first_print if card.first_print else DUMMY_SET).release_date or DATE

    classification: dict[str, int] = {}
    classification["firstprint"] = int(first_print >= V5_RELEASE_DATE)
    classification["n_print_pre"], classification["n_print_post"] = 0, 0
    for set_ in card.sets:
        if set_.release_date and set_.release_date < V5_RELEASE_DATE:
            classification["n_print_pre"] += 1
        elif set_.release_date and set_.release_date >= V5_RELEASE_DATE:
            classification["n_print_post"] += 1

    return classification


def weighted_mean(values_and_weights: list[tuple[float, int]]) -> float:
    """Weighted arithmetic mean. Returns 0.0 if total weight is 0."""
    total_w = sum(w for _, w in values_and_weights)
    if total_w == 0:
        return 0.0
    return sum(v * w for v, w in values_and_weights) / total_w


def safe_ratio(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def parse_cost(raw: str | None) -> int | str | None:
    if raw is None:
        return None
    v = str(raw).strip().upper()
    if v in ("", "NONE", "0"):
        return 0
    if v == "X":
        return "X"
    try:
        return int(v)
    except ValueError:
        return None


def parse_disc_names(discs: str) -> list[str]:
    if not discs or not discs.strip():
        return []
    if "/" in discs:
        return [d.strip().lower() for d in discs.split("/") if d.strip()]
    if "&" in discs:
        return [d.strip().lower() for d in discs.split(" & ") if d.strip()]
    return [discs.strip().lower()]


def get_crypt_sect(card_text: str) -> str:
    """Extract sect from crypt card_text prefix (e.g. 'Sabbat: ...' → 'sabbat')."""
    prefix = card_text.strip().split(":")[0].lower().strip()
    return prefix if prefix in KNOWN_SECTS else "none"


def get_lib_sect_req(requirement: str) -> str:
    """Derive sect from a library card's requirement field."""
    req = requirement.lower().strip()
    if req in KNOWN_SECTS:
        return req
    return REQUIREMENT_TO_SECT.get(req, "none")


def parse_disc_tags(card_text: str) -> tuple[set[str], set[str]]:
    base: set[str] = set()
    superior: set[str] = set()
    if not card_text:
        return base, superior
    for tok in LINE_START_TAG_RE.findall(card_text):
        code = tok.lower()
        base.add(code)
        if tok == tok.upper():
            superior.add(code)
    return base, superior
