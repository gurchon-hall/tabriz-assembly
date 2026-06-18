"""Import des données VTES depuis les fichiers CSV vers la base de données.

Pour chaque type d'entité, la logique est : upsert par id, avec une
comparaison champ par champ pour détecter si une mise à jour est nécessaire.

Ordre d'import (cf. constants.IMPORT_ORDER) :
    0. Seeds        - sets absents de vtessets.csv (ex: POD)
    1. Set          - indépendant
    2. CryptCard    - dépend de Set (relation many-to-many)
    3. LibraryCard  - dépend de Set (relation many-to-many)
    4. LibraryMeta  - met à jour LibraryCard.requirement (par id + name)
"""

import tempfile
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

import app.models.vtes as vtes_models
import app.schemas.vtes as vtes_schemas
from app.config import settings
from app.services.vtes_data.constants import CSV_SCHEMAS, CSV_SOURCES, IMPORT_ORDER, SEED_SETS
from app.services.vtes_data.fetcher import download_file, parse_file_as

logger = settings.log.get_logger(__name__)


def _clean_str(value: str) -> str:
    """Retire les guillemets simples et doubles excédentaires en début/fin de chaîne."""
    return value.strip().strip("'\"")


def dict_factory[K, V](
    _k: type[K] | None = None, _v: type[V] | None = None
) -> Callable[[], dict[K, V]]:
    """Retourne une factory de dict typée pour ``Field(default_factory=...)``."""

    def _factory() -> dict[K, V]:
        return {}

    return _factory


@dataclass
class ImportCounters:
    created: int = 0
    updated: int = 0
    unchanged: int = 0

    def __str__(self) -> str:
        return f"created={self.created}, updated={self.updated}, unchanged={self.unchanged}"


@dataclass
class ImportResult:
    counters: dict[str, ImportCounters] = field(default_factory=dict_factory(str, ImportCounters))

    def __str__(self) -> str:
        lines = [f"  {filename}: {counters}" for filename, counters in self.counters.items()]
        return "Résultat de l'import :\n" + "\n".join(lines)


async def _seed_sets(session: AsyncSession) -> None:
    """Insère les sets absents de vtessets.csv s'ils n'existent pas déjà."""
    counter = ImportCounters()

    for seed in SEED_SETS:
        await _upsert_set(session, vtes_schemas.Set.model_validate(seed), counter)
    await session.commit()

    logger.info(f"seed_sets importé: {counter}")


def _compute_first_print_set_id(
    target_sets: list[vtes_models.Set],
) -> int | None:
    """Retourne l'id du set avec la release_date la plus ancienne, ou None."""
    dated = [s for s in target_sets if s.release_date is not None]
    if not dated:
        return None
    return min(dated, key=lambda s: s.release_date).id  # type: ignore[arg-type]


async def _upsert_set(
    session: AsyncSession,
    row: vtes_schemas.Set,
    counters: ImportCounters,
) -> None:
    existing = await session.get(vtes_models.Set, row.id)

    company = _clean_str(row.company)

    if existing is None:
        session.add(
            vtes_models.Set(
                id=row.id,
                release_date=row.release_date,
                full_name=row.full_name,
                abbrev=row.abbrev,
                company=company,
            )
        )
        counters.created += 1
        return

    changed = False
    if row.release_date is not None and existing.release_date != row.release_date:
        existing.release_date = row.release_date
        changed = True
    if existing.full_name != row.full_name:
        existing.full_name = row.full_name
        changed = True
    if existing.abbrev != row.abbrev:
        existing.abbrev = row.abbrev
        changed = True
    if existing.company != company:
        existing.company = company
        changed = True

    counters.updated += 1 if changed else 0
    counters.unchanged += 0 if changed else 1


async def _get_sets_by_abbrev(
    session: AsyncSession, abbrevs: list[str]
) -> dict[str, vtes_models.Set]:
    if not abbrevs:
        return {}
    result = await session.execute(
        select(vtes_models.Set).where(vtes_models.Set.abbrev.in_(abbrevs))
    )
    return {s.abbrev: s for s in result.scalars().all()}


def _sync_sets_relation(
    existing_sets: list[vtes_models.Set],
    target_sets: list[vtes_models.Set],
) -> bool:
    """Synchronise la liste M2M en place. Retourne True si modifiée."""
    existing_ids = {s.id for s in existing_sets}
    target_ids = {s.id for s in target_sets}

    if existing_ids == target_ids:
        return False

    existing_sets[:] = target_sets
    return True


async def _upsert_crypt_card(
    session: AsyncSession,
    row: vtes_schemas.CryptCard,
    sets_by_abbrev: dict[str, vtes_models.Set],
    counters: ImportCounters,
) -> None:
    target_sets = [sets_by_abbrev[a] for a in row.set_abbrevs if a in sets_by_abbrev]

    missing = [a for a in row.set_abbrevs if a not in sets_by_abbrev]
    if missing:
        logger.warning("CryptCard %s: set(s) inconnu(s) ignoré(s) : %s", row.id, missing)

    existing = await session.get(vtes_models.CryptCard, row.id, options=[])

    if existing is None:
        session.add(
            vtes_models.CryptCard(
                id=row.id,
                name=row.name,
                clan=row.clan,
                type=row.type_,
                artist=row.artist,
                group=str(row.group),
                capacity=row.capacity,
                path=row.path,
                title=row.title,
                disciplines=row.disciplines,
                card_text=row.card_text,
                banned=row.banned,
                adv=row.adv,
                sets=target_sets,
                first_print_set_id=_compute_first_print_set_id(target_sets),
            )
        )
        counters.created += 1
        return

    changed = False
    if existing.name != row.name:
        existing.name = row.name
        changed = True
    if existing.clan != row.clan:
        existing.clan = row.clan
        changed = True
    if existing.type != row.type_:
        existing.type = row.type_
        changed = True
    if existing.artist != row.artist:
        existing.artist = row.artist
        changed = True
    if existing.group != str(row.group):
        existing.group = str(row.group)
        changed = True
    if existing.capacity != row.capacity:
        existing.capacity = row.capacity
        changed = True
    if existing.path != row.path:
        existing.path = row.path
        changed = True
    if existing.title != row.title:
        existing.title = row.title
        changed = True
    if existing.disciplines != row.disciplines:
        existing.disciplines = row.disciplines
        changed = True
    if existing.card_text != row.card_text:
        existing.card_text = row.card_text
        changed = True
    if existing.banned != row.banned:
        existing.banned = row.banned
        changed = True
    if existing.adv != row.adv:
        existing.adv = row.adv
        changed = True

    await session.refresh(existing, attribute_names=["sets"])
    if _sync_sets_relation(existing.sets, target_sets):
        changed = True
        new_fp = _compute_first_print_set_id(target_sets)
        if existing.first_print_set_id != new_fp:
            existing.first_print_set_id = new_fp

    counters.updated += 1 if changed else 0
    counters.unchanged += 0 if changed else 1


async def _upsert_library_card(
    session: AsyncSession,
    row: vtes_schemas.LibraryCard,
    sets_by_abbrev: dict[str, vtes_models.Set],
    counters: ImportCounters,
) -> None:
    target_sets = [sets_by_abbrev[a] for a in row.set_abbrevs if a in sets_by_abbrev]

    missing = [a for a in row.set_abbrevs if a not in sets_by_abbrev]
    if missing:
        logger.warning("LibraryCard %s: set(s) inconnu(s) ignoré(s) : %s", row.id, missing)

    existing = await session.get(vtes_models.LibraryCard, row.id)

    if existing is None:
        session.add(
            vtes_models.LibraryCard(
                id=row.id,
                name=row.name,
                type=row.type_,
                artist=row.artist,
                capacity=row.capacity,
                pool_cost=row.pool_cost,
                blood_cost=row.blood_cost,
                conviction_cost=row.conviction_cost,
                clan=row.clan,
                path=row.path,
                requirement="",  # géré par LibraryMeta
                flavor_text=row.flavor_text,
                card_text=row.card_text,
                discipline=row.discipline,
                banned=row.banned,
                burn_option=row.burn_option,
                sets=target_sets,
                first_print_set_id=_compute_first_print_set_id(target_sets),
            )
        )
        counters.created += 1
        return

    assert existing is not None
    changed = False
    if existing.name != row.name:
        existing.name = row.name
        changed = True
    if existing.type != row.type_:
        existing.type = row.type_
        changed = True
    if existing.artist != row.artist:
        existing.artist = row.artist
        changed = True
    if existing.capacity != str(row.capacity):
        existing.capacity = str(row.capacity)
        changed = True
    if existing.pool_cost != str(row.pool_cost):
        existing.pool_cost = str(row.pool_cost)
        changed = True
    if existing.blood_cost != str(row.blood_cost):
        existing.blood_cost = str(row.blood_cost)
        changed = True
    if existing.conviction_cost != str(row.conviction_cost):
        existing.conviction_cost = str(row.conviction_cost)
        changed = True
    if existing.clan != row.clan:
        existing.clan = row.clan
        changed = True
    if existing.path != row.path:
        existing.path = row.path
        changed = True
    if existing.flavor_text != row.flavor_text:
        existing.flavor_text = row.flavor_text
        changed = True
    if existing.card_text != row.card_text:
        existing.card_text = row.card_text
        changed = True
    if existing.discipline != row.discipline:
        existing.discipline = row.discipline
        changed = True
    if existing.banned != row.banned:
        existing.banned = row.banned
        changed = True
    if existing.burn_option != row.burn_option:
        existing.burn_option = row.burn_option
        changed = True

    await session.refresh(existing, attribute_names=["sets"])
    if _sync_sets_relation(existing.sets, target_sets):
        changed = True
        new_fp = _compute_first_print_set_id(target_sets)
        if existing.first_print_set_id != new_fp:
            existing.first_print_set_id = new_fp

    counters.updated += 1 if changed else 0
    counters.unchanged += 0 if changed else 1


async def _apply_library_meta(
    session: AsyncSession,
    row: vtes_schemas.LibraryMeta,
    counters: ImportCounters,
) -> None:
    """Met à jour LibraryCard.requirement à partir d'une ligne vteslibmeta.csv."""
    existing = await session.get(vtes_models.LibraryCard, row.id)

    if existing is None:
        logger.warning(
            "LibraryMeta %s (%s): aucune LibraryCard correspondante, ignoré",
            row.id,
            row.name,
        )
        return

    if existing.name != row.name:
        logger.warning(
            "LibraryMeta %s: nom incohérent (meta=%r, card=%r), mise à jour requirement quand même",
            row.id,
            row.name,
            existing.name,
        )

    if existing.requirement != row.requirement:
        existing.requirement = row.requirement
        counters.updated += 1
    else:
        counters.unchanged += 1


async def _recompute_all_first_prints(session: AsyncSession) -> None:
    """Filet de sécurité : recalcule first_print_set_id pour toutes les cartes."""

    # CryptCard
    crypt_subq = (
        select(vtes_models.CryptCardSet.set_id)
        .join(vtes_models.Set, vtes_models.Set.id == vtes_models.CryptCardSet.set_id)
        .where(
            vtes_models.CryptCardSet.crypt_card_id == vtes_models.CryptCard.id,
            vtes_models.Set.release_date.is_not(None),
        )
        .order_by(vtes_models.Set.release_date.asc())
        .limit(1)
        .scalar_subquery()
        .correlate(vtes_models.CryptCard)
    )
    await session.execute(update(vtes_models.CryptCard).values(first_print_set_id=crypt_subq))

    # LibraryCard
    library_subq = (
        select(vtes_models.LibraryCardSet.set_id)
        .join(vtes_models.Set, vtes_models.Set.id == vtes_models.LibraryCardSet.set_id)
        .where(
            vtes_models.LibraryCardSet.library_card_id == vtes_models.LibraryCard.id,
            vtes_models.Set.release_date.is_not(None),
        )
        .order_by(vtes_models.Set.release_date.asc())
        .limit(1)
        .scalar_subquery()
        .correlate(vtes_models.LibraryCard)
    )
    await session.execute(update(vtes_models.LibraryCard).values(first_print_set_id=library_subq))

    await session.commit()
    logger.info("first_print_set_id recalculé pour toutes les cartes")


async def run_import() -> ImportResult:
    """Télécharge et importe l'ensemble des fichiers CSV VTES en base.

    Un commit est effectué après le traitement complet de chaque fichier CSV.
    Les sets seeds (absents de vtessets.csv) sont insérés en premier.
    """
    result = ImportResult()

    with tempfile.TemporaryDirectory() as tmpdirname:
        dir_path = Path(tmpdirname)

        async with settings.db.async_session_local() as session:
            await _seed_sets(session)

            for filename in IMPORT_ORDER:
                source_url = CSV_SOURCES[filename]
                schema = CSV_SCHEMAS[filename]

                file_path = dir_path / filename
                download_file(source_url, file_path)
                rows = parse_file_as(file_path, schema)

                counters = ImportCounters()

                if filename == "vtessets.csv":
                    for row in rows:
                        assert isinstance(row, vtes_schemas.Set)
                        await _upsert_set(session, row, counters)

                elif filename == "vtescrypt.csv":
                    all_abbrevs = {a for row in rows for a in row.set_abbrevs}  # type: ignore[union-attr]
                    sets_by_abbrev = await _get_sets_by_abbrev(session, list(all_abbrevs))
                    for row in rows:
                        assert isinstance(row, vtes_schemas.CryptCard)
                        await _upsert_crypt_card(session, row, sets_by_abbrev, counters)

                elif filename == "vteslib.csv":
                    all_abbrevs = {a for row in rows for a in row.set_abbrevs}  # type: ignore[union-attr]
                    sets_by_abbrev = await _get_sets_by_abbrev(session, list(all_abbrevs))
                    for row in rows:
                        assert isinstance(row, vtes_schemas.LibraryCard)
                        await _upsert_library_card(session, row, sets_by_abbrev, counters)

                elif filename == "vteslibmeta.csv":
                    for row in rows:
                        assert isinstance(row, vtes_schemas.LibraryMeta)
                        await _apply_library_meta(session, row, counters)

                else:
                    raise ValueError(f"Fichier CSV non géré : {filename}")

                await session.commit()
                result.counters[filename] = counters
                logger.info("%s importé : %s", filename, counters)

            await _recompute_all_first_prints(session)

    return result
