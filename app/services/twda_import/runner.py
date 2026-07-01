"""Import des tournois eternal-vigilance vers la base de données.

Logique : upsert par ``event_id``, avec comparaison champ-à-champ des scalaires
(tournoi + deck) et comparaison ensembliste des cartes. Les noms de cartes sont
résolus une seule fois via des maps construites au démarrage ; la résolution est
opportuniste (FK nullable, ``raw_name`` toujours conservé).
"""

import re
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.models.tournament import Deck, DeckCryptCard, DeckLibraryCard, Tournament
from app.models.vtes import CryptCard, LibraryCard
from app.schemas.tournament import YamlDeck, YamlTournament
from app.services.twda_import.fetcher import (
    fetch_tournament_yaml,
    list_tournament_yaml_paths,
)
from app.services.vtes_data.runner import ImportCounters

logger = settings.log.get_logger(__name__)

CryptKey = tuple[str, str, bool]  # (clean_name.lower(), group_str, adv)
CryptRef = tuple[int, str, bool]  # (id, group, adv)
CryptRow = tuple[int, str, str, int | None, str | None, bool | None]
LibraryRow = tuple[str, int, str, int | None]

# Article en tête de nom, ex. "The Horde" → groupe 1 = "Horde".
_LEADING_THE_RE = re.compile(r"^[Tt]he\s+(.+)$")


def _canonical_name(name: str) -> str:
    """Réécrit un nom de carte vers la forme des données de référence (vtescsv).

    Les noms reçus suivent la nomenclature officielle krcg (eternal-vigilance) ;
    les cartes en base suivent celle de vteslib.csv / vtescrypt.csv. Deux écarts
    de convention sont réconciliés ici, côté consommateur :
      - article en tête : ``The Horde`` → ``Horde, The`` (ordre de tri vtescsv) ;
      - symbole ``™``    : ``Pentex™ Subversion`` → ``Pentex(TM) Subversion``.
    """
    m = _LEADING_THE_RE.match(name)
    if m:
        name = f"{m.group(1)}, The"
    return name.replace("™", "(TM)")


def _name_candidates(name: str) -> tuple[str, ...]:
    """Nom brut puis, si différente, sa forme canonique (essayés dans l'ordre)."""
    if name == "KuyÃ©n":
        return (name, _canonical_name("Kuyén"))
    canonical = _canonical_name(name)
    return (name,) if canonical == name else (name, canonical)


@dataclass
class TournamentImportResult:
    tournaments: ImportCounters = field(default_factory=ImportCounters)
    unresolved_crypt: int = 0
    unresolved_library: int = 0
    skipped: int = 0

    def __str__(self) -> str:
        return (
            "Résultat de l'import des tournois :\n"
            f"  tournois: {self.tournaments}\n"
            f"  cartes crypt non résolues: {self.unresolved_crypt}\n"
            f"  cartes library non résolues: {self.unresolved_library}\n"
            f"  fichiers ignorés (invalides): {self.skipped}"
        )


# ----------------------------------------------------------------------------
#  Maps de résolution (construites une fois)
# ----------------------------------------------------------------------------
async def _build_crypt_map(
    session: AsyncSession,
) -> tuple[dict[CryptKey, CryptRef], set[CryptRef]]:
    result = await session.execute(
        select(CryptCard.id, CryptCard.group, CryptCard.adv, CryptCard.name)
    )
    crypt_map: dict[CryptKey, CryptRef] = {}
    crypt_refs: set[CryptRef] = set()
    for card_id, group, adv, name in result.all():
        ref: CryptRef = (card_id, str(group), bool(adv))
        # Clé en minuscules : la résolution par nom est insensible à la casse (cf. _resolve_*).
        crypt_map[(name.lower(), str(group), bool(adv))] = ref
        crypt_refs.add(ref)
    return crypt_map, crypt_refs


async def _build_library_map(session: AsyncSession) -> tuple[dict[str, int], set[int]]:
    result = await session.execute(select(LibraryCard.id, LibraryCard.name))
    library_map: dict[str, int] = {}
    library_ids: set[int] = set()
    for card_id, name in result.all():
        library_ids.add(card_id)
        key = name.lower()
        if key in library_map:
            logger.warning(
                "Library: nom dupliqué %r (ids %s et %s) — premier conservé",
                name,
                library_map[key],
                card_id,
            )
            continue
        library_map[key] = card_id
    return library_map, library_ids


def _resolve_crypt(
    entry_id: int | None,
    name: str,
    group: str,
    adv: bool,
    crypt_map: dict[CryptKey, CryptRef],
    crypt_refs: set[CryptRef],
) -> CryptRef | None:
    # Résolution directe par id krcg (channel-ten >= 0.9.0) : fiable, sans heuristique de nom.
    if entry_id is not None:
        id_ref: CryptRef = (entry_id, group, adv)
        if id_ref in crypt_refs:
            return id_ref
        id_ref = (entry_id, "ANY", adv)
        if id_ref in crypt_refs:
            return id_ref
    for candidate in _name_candidates(name):
        key = candidate.lower()
        name_ref = crypt_map.get((key, group, adv))
        if name_ref is None:
            # Certaines cartes de crypt sont stockées avec le groupe "ANY".
            name_ref = crypt_map.get((key, "ANY", adv))
        if name_ref is not None:
            return name_ref
    return None


def _resolve_library(
    entry_id: int | None, name: str, library_map: dict[str, int], library_ids: set[int]
) -> int | None:
    if entry_id is not None and entry_id in library_ids:
        return entry_id
    for candidate in _name_candidates(name):
        card_id = library_map.get(candidate.lower())
        if card_id is not None:
            return card_id
    return None


# ----------------------------------------------------------------------------
#  Construction des lignes "désirées" à partir du YAML
# ----------------------------------------------------------------------------
def _desired_crypt_rows(
    deck: YamlDeck, crypt_map: dict[CryptKey, CryptRef], crypt_refs: set[CryptRef]
) -> tuple[list[CryptRow], int]:
    rows: list[CryptRow] = []
    unresolved = 0
    for entry in deck.crypt:
        ref = _resolve_crypt(
            entry.id, entry.clean_name, str(entry.grouping), entry.is_adv, crypt_map, crypt_refs
        )
        if ref is None:
            unresolved += 1
            logger.warning(
                "Crypt non résolue: %r (group=%s adv=%s)",
                entry.clean_name,
                entry.grouping,
                entry.is_adv,
            )
            card_id, group, adv = None, None, None
        else:
            card_id, group, adv = ref
        rows.append((entry.count, entry.name, str(entry.grouping), card_id, group, adv))
    return rows, unresolved


def _desired_library_rows(
    deck: YamlDeck, library_map: dict[str, int], library_ids: set[int]
) -> tuple[list[LibraryRow], int]:
    rows: list[LibraryRow] = []
    unresolved = 0
    for section in deck.library_sections:
        for card in section.cards:
            card_id = _resolve_library(card.id, card.name, library_map, library_ids)
            if card_id is None:
                unresolved += 1
                logger.warning("Library non résolue: %r (section=%s)", card.name, section.name)
            rows.append((section.name, card.count, card.name, card_id))
    return rows, unresolved


def _make_crypt_models(rows: list[CryptRow]) -> list[DeckCryptCard]:
    return [
        DeckCryptCard(
            count=count,
            raw_name=raw_name,
            raw_grouping=raw_grouping,
            crypt_card_id=card_id,
            crypt_card_group=group,
            crypt_card_adv=adv,
        )
        for (count, raw_name, raw_grouping, card_id, group, adv) in rows
    ]


def _make_library_models(rows: list[LibraryRow]) -> list[DeckLibraryCard]:
    return [
        DeckLibraryCard(
            section=section,
            count=count,
            raw_name=raw_name,
            library_card_id=card_id,
        )
        for (section, count, raw_name, card_id) in rows
    ]


# ----------------------------------------------------------------------------
#  Upsert
# ----------------------------------------------------------------------------
def _deck_scalar_values(deck: YamlDeck) -> dict[str, object]:
    return {
        "name": deck.name,
        "created_by": deck.created_by,
        "description": deck.description,
        "crypt_count": deck.crypt_count,
        "crypt_min": deck.crypt_min,
        "crypt_max": deck.crypt_max,
        "crypt_avg": deck.crypt_avg,
        "library_count": deck.library_count,
    }


def _tournament_scalar_values(tour: YamlTournament) -> dict[str, object]:
    return {
        "name": tour.name,
        "location": tour.location,
        "date_start": tour.date_start,
        "date_end": tour.date_end,
        "rounds_format": tour.rounds_format,
        "players_count": tour.players_count,
        "winner": tour.winner,
        "vekn_number": tour.vekn_number,
        "event_url": tour.event_url,
        "forum_post_url": tour.forum_post_url,
        "vp_comment": tour.vp_comment,
    }


def _apply_scalars(obj: object, values: dict[str, object]) -> bool:
    changed = False
    for attr, value in values.items():
        if getattr(obj, attr) != value:
            setattr(obj, attr, value)
            changed = True
    return changed


async def _upsert_tournament(
    session: AsyncSession,
    tour: YamlTournament,
    crypt_map: dict[CryptKey, CryptRef],
    crypt_refs: set[CryptRef],
    library_map: dict[str, int],
    library_ids: set[int],
    result: TournamentImportResult,
) -> None:
    crypt_rows, unresolved_c = _desired_crypt_rows(tour.deck, crypt_map, crypt_refs)
    library_rows, unresolved_l = _desired_library_rows(tour.deck, library_map, library_ids)
    result.unresolved_crypt += unresolved_c
    result.unresolved_library += unresolved_l

    stmt = (
        select(Tournament)
        .where(Tournament.event_id == tour.event_id)
        .options(
            selectinload(Tournament.deck).selectinload(Deck.crypt_cards),
            selectinload(Tournament.deck).selectinload(Deck.library_cards),
        )
    )
    existing = (await session.execute(stmt)).scalar_one_or_none()

    if existing is None:
        new_deck = Deck(
            **_deck_scalar_values(tour.deck),
            crypt_cards=_make_crypt_models(crypt_rows),
            library_cards=_make_library_models(library_rows),
        )
        session.add(
            Tournament(
                event_id=tour.event_id,
                **_tournament_scalar_values(tour),
                deck=new_deck,
            )
        )
        result.tournaments.created += 1
        return

    changed = _apply_scalars(existing, _tournament_scalar_values(tour))

    deck = existing.deck
    if deck is None:
        existing.deck = Deck(
            **_deck_scalar_values(tour.deck),
            crypt_cards=_make_crypt_models(crypt_rows),
            library_cards=_make_library_models(library_rows),
        )
        changed = True
    else:
        changed |= _apply_scalars(deck, _deck_scalar_values(tour.deck))

        current_crypt = sorted(
            (
                r.count,
                r.raw_name,
                r.raw_grouping,
                r.crypt_card_id,
                r.crypt_card_group,
                r.crypt_card_adv,
            )
            for r in deck.crypt_cards
        )
        if current_crypt != sorted(crypt_rows):
            deck.crypt_cards = _make_crypt_models(crypt_rows)
            changed = True

        current_library = sorted(
            (r.section, r.count, r.raw_name, r.library_card_id) for r in deck.library_cards
        )
        if current_library != sorted(library_rows):
            deck.library_cards = _make_library_models(library_rows)
            changed = True

    if changed:
        result.tournaments.updated += 1
    else:
        result.tournaments.unchanged += 1


# ----------------------------------------------------------------------------
#  Orchestration
# ----------------------------------------------------------------------------
async def run_import() -> TournamentImportResult:
    """Énumère, télécharge et importe l'ensemble des tournois valides."""
    cfg = settings.tournament
    result = TournamentImportResult()

    paths = list_tournament_yaml_paths(cfg.source_repo, cfg.source_branch, cfg.github_token)
    logger.info("%d fichiers de tournois trouvés", len(paths))

    async with settings.db.async_session_local() as session:
        crypt_map, crypt_refs = await _build_crypt_map(session)
        library_map, library_ids = await _build_library_map(session)
        logger.info(
            "Maps de résolution: %d cartes crypt, %d cartes library",
            len(crypt_map),
            len(library_map),
        )

        for index, path in enumerate(paths, start=1):
            tour = fetch_tournament_yaml(cfg.source_repo, cfg.source_branch, path, cfg.github_token)
            if tour is None:
                result.skipped += 1
                continue

            await _upsert_tournament(
                session, tour, crypt_map, crypt_refs, library_map, library_ids, result
            )

            if index % cfg.commit_batch_size == 0:
                await session.commit()
                logger.info("Progression: %d/%d (%s)", index, len(paths), result.tournaments)

        await session.commit()

    logger.info("Import terminé: %s", result.tournaments)
    return result
