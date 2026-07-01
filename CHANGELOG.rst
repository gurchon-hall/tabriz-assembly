Changelog
=========

All notable changes to this project are documented here. Versions follow
`Semantic Versioning <https://semver.org/>`_ (``MAJOR.MINOR.PATCH``); while the
project is ``0.y.z``, a ``MINOR`` bump marks a new capability (API surface,
data domain, pipeline stage) and a ``PATCH`` bump marks fixes/polish within an
already-shipped capability.

.. contents:: Versions
   :local:
   :depth: 1

----

v0.5.0 — 2026-07-01
====================

Card-ID resolution and ``ANY``-grouping support, brought in to match the data
quality of `channel-ten v0.9.1 <https://github.com/gurchon-hall/channel-ten>`_
(krcg card IDs now embedded in every tournament YAML file).

Added
-----

- ``id: int | None`` on ``YamlCryptEntry`` and ``YamlLibraryCardEntry``
  (``app/schemas/tournament.py``): carries the canonical krcg card id emitted
  by channel-ten >= 0.9.0, when present in the source YAML.
- Id-based card resolution in ``app/services/twda_import/runner.py``:
  ``_resolve_crypt``/``_resolve_library`` now match a card by its krcg id
  first (exact, against the ``(id, group, adv)`` composite key for crypt and
  the plain ``id`` for library), falling back to the existing name-heuristic
  path (``The X`` swap, ``™`` normalization, the ``Kuyén`` mojibake
  special-case) only for older files predating id enrichment.

Changed
-------

- ``YamlCryptEntry.grouping`` widened from ``int`` to ``int | Literal["ANY"]``
  with a normalizing validator, mirroring the ``CryptCard.group`` field in
  ``app/schemas/vtes.py``.
- ``DeckCryptCard.raw_grouping`` (``app/models/tournament.py``) changed from
  ``Integer`` to ``String`` to hold the literal ``"ANY"``; migrated in
  ``alembic/versions/1ffa76760842_deck_crypt_cards_raw_grouping_as_str.py``.

Fixed
-----

- Tournament files containing a group-independent (``ANY``-grouping) vampire
  previously failed ``YamlTournament`` validation in ``fetch_tournament_yaml``
  and were silently dropped in their entirety (not just the offending card).
  These now import correctly.

----

v0.4.0 — 2026-07-01
====================

Deck-level feature extraction: the crypt/library card data is turned into a
flat, ML-ready feature vector per tournament-winning deck, plus exploratory
notebooks over the results.

Added
-----

- ``app/services/twd_features/``: ``crypt_features.py`` and
  ``deck_features.py`` compute per-deck aggregates (clan/discipline/sect/path
  shares, era distribution, capacity/vote/bonus statistics, star-vampire and
  dominant-clan detection) from ``DeckCryptCard``/``DeckLibraryCard`` rows;
  ``cross_features.py`` adds crypt↔library cross features; ``constants.py``
  and ``helpers.py`` hold the shared regexes, trait maps and era/cost/sect
  parsing helpers.
- ``scripts/extract_features.py``: generates features for the most recent
  tournaments, prints a grouped console summary, and exports the result to
  ``scripts/deck_features_sample.json`` for review.
- Sect and V5 Sabbat path requirements folded into both crypt and cross
  features (clan/discipline requirements were not enough to separate
  Camarilla/Sabbat/Anarch archetypes).
- Printed-era percentage features (``*_pct_printed_pre_v5`` /
  ``*_pct_printed_post_v5``), distinguishing a card's original printing era
  from its first V5-legal reprint.
- Notebooks ``05_feature_extraction`` and ``06_feature_evaluation``: first
  round of feature visualization and validation against the extracted data.

Changed
-------

- Notebooks renamed for clarity (``01_data`` → ``01_data_loading``,
  ``02_decks`` → ``02_decks_exploration``, ``03_crypt`` →
  ``03_crypt_exploration``, ``04_library`` → ``04_library_exploration``) and
  moved to simplify re-imports between them.

----

v0.3.0 — 2026-06-23
====================

Tournament-winning deck (TWD) import from the sibling
`gurchon-hall/eternal-vigilance <https://github.com/gurchon-hall/eternal-vigilance>`_
repository, resolved against the VTES reference card data added in v0.2.0.

Added
-----

- ``app/models/tournament.py``: ``Tournament`` / ``Deck`` / ``DeckCryptCard`` /
  ``DeckLibraryCard`` tables. Card resolution is opportunistic — foreign keys
  are nullable and ``raw_name``/``raw_grouping`` are always kept, so a
  tournament is never dropped just because a card can't yet be resolved
  against the reference tables.
- ``app/services/twda_import/``: ``fetcher.py`` enumerates and downloads
  tournament YAML files from eternal-vigilance via the GitHub API;
  ``runner.py`` upserts them by ``event_id`` with field-level scalar diffing
  and set-based card-row diffing.
- Card-name resolution heuristics: case-insensitive matching, a leading
  ``"The "`` article rewrite (``The Horde`` → ``Horde, The``, matching
  vtescsv sort order), a ``™`` → ``(TM)`` normalization, and a hardcoded
  special-case for the ``Kuyén`` mojibake variant.

Fixed
-----

- Invalid YAML files now log a clear warning and are skipped instead of
  aborting the whole import run.

----

v0.2.0 — 2026-06-18
====================

VTES reference card database: sets and crypt/library cards imported from the
official VEKN CSV export, with first-print tracking.

Added
-----

- ``app/models/vtes.py`` / ``app/schemas/vtes.py``: ``Set``, ``CryptCard``,
  ``LibraryCard`` tables and their CSV-import schemas.
- ``app/services/vtes_data/``: importer that loads the official VEKN
  ``vtescrypt.csv`` / ``vteslib.csv`` / ``vtescsv`` set data into the
  database.
- ``first_print_set_id`` on ``CryptCard`` and ``LibraryCard``, with logic to
  compute and backfill each card's earliest printing across its known sets.
- Machine-learning optional dependency group (pandas, scikit-learn, plotly,
  jupyter, ...) for the analysis notebooks.

Changed
-------

- ``Set`` ↔ card relationship changed from one-to-many to many-to-many
  (``LibraryCardSet`` / ``CryptCardSet`` association tables), reflecting that
  a card can appear across multiple sets.
- ``CryptCard`` primary key changed to the composite ``(id, group, adv)`` key
  used throughout the codebase (a single krcg id spans multiple
  group/advanced printings).

----

v0.1.0 — 2026-06-15
====================

Initial project scaffold: FastAPI application skeleton, Alembic migrations,
and a user table.

Added
-----

- Base FastAPI application (``app/main.py``) with config, database session
  and logging setup.
- Alembic wired up for schema migrations.
- ``User`` table.
