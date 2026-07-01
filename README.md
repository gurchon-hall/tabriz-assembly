# Tabriz Assembly

VTES data ingestion, feature extraction and ML exploration — with a FastAPI
backend that will also serve as the BFF (backend-for-frontend) for an
upcoming frontend built to browse and visualize the data explored here.

## What this is

Tabriz Assembly sits at the end of the [Gurchon Hall](https://github.com/gurchon-hall)
VTES data pipeline:

```text
VEKN forum ──(channel-ten)──> eternal-vigilance (tournament YAML)
                                        │
GiottoVerducci/vtescsv (card data)  ────┼───> tabriz-assembly
                                        │       │
                                        │       ├─ import reference card data (vtes_data)
                                        │       ├─ import tournament-winning decks (twda_import)
                                        │       ├─ extract ML features per deck (twd_features)
                                        │       └─ FastAPI app / BFF (upcoming)
                                        │
                                notebooks/ (exploration, feature evaluation)
```

- **Reference card data** (`app/services/vtes_data/`): imports the official
  VEKN card export (`vtescrypt.csv`, `vteslib.csv`, `vtessets.csv`,
  `vteslibmeta.csv` from `GiottoVerducci/vtescsv`) into `Set`, `CryptCard`
  and `LibraryCard` tables, with first-print tracking per card.
- **Tournament import** (`app/services/twda_import/`): pulls
  tournament-winning-deck YAML files from
  [`gurchon-hall/eternal-vigilance`](https://github.com/gurchon-hall/eternal-vigilance)
  (populated by [`gurchon-hall/channel-ten`](https://github.com/gurchon-hall/channel-ten))
  and upserts them into `Tournament`/`Deck`/`DeckCryptCard`/`DeckLibraryCard`
  tables, resolving each card against the reference data by krcg id (falling
  back to name heuristics for older, un-enriched files).
- **Feature extraction** (`app/services/twd_features/`): turns each deck into
  a flat, ML-ready feature vector — clan/discipline/sect/path shares, era
  distribution, capacity/vote/bonus statistics, crypt↔library cross features.
- **Notebooks** (`notebooks/`): exploration of the imported data and
  evaluation of the extracted features.
- **API** (`app/main.py`, `app/routes/`): FastAPI application. Currently a
  bare skeleton (auth, CORS, request logging); it will grow into the BFF that
  serves this data to the upcoming frontend.

See [CHANGELOG.rst](CHANGELOG.rst) for the version history.

## Setup

Requires Python ≥ 3.14 and a PostgreSQL database.

```bash
python -m venv .venv
.venv/Scripts/activate            # Windows; use `source .venv/bin/activate` on Unix
pip install -e ".[dev]"           # add ",machine-learning" for the notebooks

cp .env.ini .env                  # then fill in DATABASE_URL, SECRET_KEY, etc.
alembic upgrade head
```

## Usage

```bash
# Run the API
uvicorn app.main:app --reload

# Import/refresh the official VTES card reference data
python scripts/import_files.py

# Import tournament-winning decks from eternal-vigilance
python scripts/import_twda.py

# Extract and preview deck features for the most recent tournaments
python scripts/extract_features.py
```

## Development

```bash
ruff check .
ruff format .
mypy .
```
