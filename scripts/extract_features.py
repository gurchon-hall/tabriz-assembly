"""
Generate deck features for the last 5 TWDs and export to JSON for review.

Run from the project root:
    python scripts/extract_features.py
"""

import asyncio
import datetime
import json
import sys
from pathlib import Path
from typing import Any, cast

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.config import settings
from app.models import CryptCard, Deck, DeckCryptCard, DeckLibraryCard, LibraryCard, Tournament
from app.services.twd_features import deck_features
from app.services.twd_features.constants import CardFeatures


def _render_features(features: CardFeatures) -> dict[str, CardFeatures]:
    """Split a flat feature dict into named groups for readability."""
    groups: dict[str, CardFeatures] = {
        "crypt_scalars": {},
        "crypt_clans": {},
        "crypt_groups": {},
        "crypt_disciplines_base": {},
        "crypt_disciplines_superior": {},
        "crypt_bonuses": {},
        "crypt_era": {},
        "library_scalars": {},
        "library_types": {},
        "library_disciplines": {},
        "library_clan_req": {},
        "library_traits": {},
        "library_era": {},
        "cross": {},
    }

    for k, v in sorted(features.items()):
        if k.startswith("crypt_clan_"):
            groups["crypt_clans"][k] = v
        elif k.startswith("crypt_group_"):
            groups["crypt_groups"][k] = v
        elif k.startswith("crypt_disc_"):
            groups["crypt_disciplines_base"][k] = v
        elif k.startswith("crypt_sup_"):
            groups["crypt_disciplines_superior"][k] = v
        elif k.startswith("crypt_pct_") and (
            "bleed" in k or "stealth" in k or "intercept" in k or "strength" in k
        ):
            groups["crypt_bonuses"][k] = v
        elif k.startswith("crypt_pct_era") or k.startswith("crypt_pct_printed_"):
            groups["crypt_era"][k] = v
        elif k.startswith("crypt_"):
            groups["crypt_scalars"][k] = v
        elif k.startswith("lib_type_"):
            groups["library_types"][k] = v
        elif k.startswith("lib_disc_"):
            groups["library_disciplines"][k] = v
        elif k.startswith("lib_req_clan_"):
            groups["library_clan_req"][k] = v
        elif k.startswith("lib_trait_"):
            groups["library_traits"][k] = v
        elif k.startswith("lib_pct_era") or k.startswith("lib_pct_printed_"):
            groups["library_era"][k] = v
        elif k.startswith("lib_"):
            groups["library_scalars"][k] = v
        else:
            groups["cross"][k] = v

    # Drop empty groups
    return {g: vals for g, vals in groups.items() if vals}


def _round_floats(obj: Any, ndigits: int = 4) -> Any:
    """Recursively round floats for readable JSON output."""
    if isinstance(obj, float):
        return round(obj, ndigits)
    if isinstance(obj, dict):
        return {k: _round_floats(v, ndigits) for k, v in cast(dict[str, Any], obj).items()}
    if isinstance(obj, list):
        return [_round_floats(v, ndigits) for v in cast(list[Any], obj)]
    return obj


async def main() -> None:
    async with settings.db.async_session_local() as session:
        stmt = (
            select(Tournament)
            .order_by(Tournament.date_start.desc())
            .limit(5)
            .options(
                selectinload(Tournament.deck)
                .selectinload(Deck.crypt_cards)
                .selectinload(DeckCryptCard.crypt_card)
                .selectinload(CryptCard.sets),
                selectinload(Tournament.deck)
                .selectinload(Deck.crypt_cards)
                .selectinload(DeckCryptCard.crypt_card)
                .selectinload(CryptCard.first_print),
                selectinload(Tournament.deck)
                .selectinload(Deck.library_cards)
                .selectinload(DeckLibraryCard.library_card)
                .selectinload(LibraryCard.sets),
                selectinload(Tournament.deck)
                .selectinload(Deck.library_cards)
                .selectinload(DeckLibraryCard.library_card)
                .selectinload(LibraryCard.first_print),
            )
        )
        result = await session.execute(stmt)
        tournaments = result.scalars().all()

    records: list[dict[str, Any]] = []
    for tournament in tournaments:
        deck = tournament.deck
        if deck is None:
            print(f"[SKIP] {tournament.name} — no deck")
            continue

        print(f"Processing: {tournament.name} ({tournament.date_start})")

        try:
            features = deck_features(deck)
        except Exception as exc:
            print(f"  ERROR: {exc}")
            import traceback

            traceback.print_exc()
            continue

        unresolved_crypt = sum(1 for dc in deck.crypt_cards if dc.crypt_card is None)
        unresolved_lib = sum(1 for dl in deck.library_cards if dl.library_card is None)

        records.append(
            {
                "tournament": tournament.name,
                "date_start": str(tournament.date_start),
                "winner": tournament.winner,
                "deck_name": deck.name,
                "crypt_count": deck.crypt_count,
                "library_count": deck.library_count,
                "unresolved_crypt_rows": unresolved_crypt,
                "unresolved_library_rows": unresolved_lib,
                "feature_count": len(features),
                "features": _round_floats(_render_features(features)),
            }
        )

    # -----------------------------------------------------------------
    # Console summary
    # -----------------------------------------------------------------
    print(f"\n{'=' * 68}")
    for rec in records:
        print(f"\n{rec['tournament']}  |  {rec['date_start']}  |  {rec['winner']}")
        print(f"  deck: {rec['deck_name'] or '(unnamed)'}")
        print(f"  total features: {rec['feature_count']}")
        if rec["unresolved_crypt_rows"] or rec["unresolved_library_rows"]:
            print(
                f"  unresolved rows: {rec['unresolved_crypt_rows']} crypt, "
                f"{rec['unresolved_library_rows']} library"
            )

        feats = rec["features"]

        # Cross features
        if cross := feats.get("cross"):
            print("  cross:  " + "  ".join(f"{k}={v}" for k, v in cross.items()))

        # Crypt scalars
        if sc := feats.get("crypt_scalars"):
            keys = [
                "crypt_total",
                "crypt_avg_capacity",
                "crypt_avg_nb_disc",
                "crypt_avg_nb_sup_disc",
                "crypt_avg_nb_votes",
                "crypt_avg_card_points_for_capacity",
                "crypt_is_monoclan",
                "crypt_has_star_vampire",
            ]
            print(
                "  crypt:  "
                + "  ".join(f"{k.removeprefix('crypt_')}={sc[k]}" for k in keys if k in sc)
            )

        # Dominant clan
        if clans := feats.get("crypt_clans"):
            top = sorted(clans.items(), key=lambda x: -x[1])[:3]
            print(
                "  clans:  " + "  ".join(f"{k.removeprefix('crypt_clan_')}={v:.2f}" for k, v in top)
            )

        # Top disciplines (base)
        if discs := feats.get("crypt_disciplines_base"):
            top = sorted(discs.items(), key=lambda x: -x[1])[:6]
            print(
                "  discs:  " + "  ".join(f"{k.removeprefix('crypt_disc_')}={v:.2f}" for k, v in top)
            )

        # Library scalars
        if lsc := feats.get("library_scalars"):
            keys = [
                "lib_total",
                "lib_avg_pool_cost",
                "lib_avg_blood_cost",
                "lib_pct_free",
                "lib_pct_no_requirements",
                "lib_pct_trifle",
            ]
            print(
                "  lib:    "
                + "  ".join(f"{k.removeprefix('lib_')}={lsc.get(k, '?')}" for k in keys if k in lsc)
            )

        # Top library types
        if ltypes := feats.get("library_types"):
            top = sorted(ltypes.items(), key=lambda x: -x[1])[:5]
            print(
                "  types:  " + "  ".join(f"{k.removeprefix('lib_type_')}={v:.2f}" for k, v in top)
            )

        # Top library traits (non-zero)
        if ltraits := feats.get("library_traits"):
            active = sorted(
                ((k, v) for k, v in ltraits.items() if v > 0),
                key=lambda x: -x[1],
            )[:8]
            if active:
                print(
                    "  traits: "
                    + "  ".join(f"{k.removeprefix('lib_trait_')}={v:.2f}" for k, v in active)
                )

    # -----------------------------------------------------------------
    # JSON export
    # -----------------------------------------------------------------
    out_path = Path(__file__).parent / "deck_features_sample.json"
    out_path.write_text(
        json.dumps(
            {
                "generated_at": datetime.datetime.now(datetime.UTC).isoformat(),
                "deck_count": len(records),
                "records": records,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    print(f"\nJSON exported → {out_path}")


if __name__ == "__main__":
    asyncio.run(main())
