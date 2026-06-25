from app.models.tournament import Deck
from app.services.twd_features.constants import CardFeatures
from app.services.twd_features.cross_features import cross_features
from app.services.twd_features.crypt_features import crypt_deck_features
from app.services.twd_features.deck_features import library_deck_features


def deck_features(deck: Deck) -> CardFeatures:
    """Extract a flat feature dict for a tournament-winning deck.

    Combines crypt aggregation, library aggregation, and cross-deck
    interaction features into a single dict ready for ML pipelines.

    Parameters
    ----------
    deck : Deck
        ORM instance with `.crypt_cards` and `.library_cards` already
        loaded (e.g. via selectinload in the calling session).

    Returns
    -------
    dict[str, bool | int | float]
        Flat feature dict. All keys are strings; values are numeric or
        boolean. No nested structures.
    """
    crypt_feats = crypt_deck_features(deck.crypt_cards)
    lib_feats = library_deck_features(deck.library_cards)
    cross_feats = cross_features(crypt_feats, lib_feats)

    return {**crypt_feats, **lib_feats, **cross_feats}


__all__ = ["crypt_deck_features", "library_deck_features", "cross_features", "deck_features"]
