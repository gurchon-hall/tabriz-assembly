from typing import Any

import app.schemas.vtes as vtes_schemas

# ----------------------------------
#  CSV source files
# ----------------------------------
CSV_SOURCES: dict[str, str] = {
    "vtessets.csv": "https://github.com/GiottoVerducci/vtescsv/raw/refs/heads/main/vtessets.csv",
    "vtescrypt.csv": "https://github.com/GiottoVerducci/vtescsv/raw/refs/heads/main/vtescrypt.csv",
    "vteslib.csv": "https://github.com/GiottoVerducci/vtescsv/raw/refs/heads/main/vteslib.csv",
    "vteslibmeta.csv": "https://github.com/GiottoVerducci/vtescsv/raw/refs/heads/main/vteslibmeta.csv",
}

CSV_SCHEMAS: dict[str, Any] = {
    "vtessets.csv": vtes_schemas.Set,
    "vtescrypt.csv": vtes_schemas.CryptCard,
    "vteslib.csv": vtes_schemas.LibraryCard,
    "vteslibmeta.csv": vtes_schemas.LibraryMeta,
}

IMPORT_ORDER: list[str] = [
    "vtessets.csv",
    "vtescrypt.csv",
    "vteslib.csv",
    "vteslibmeta.csv",
]

# ----------------------------------
#  Sets absents de vtessets.csv
# ----------------------------------
SEED_SETS: list[vtes_schemas.Set] = [
    vtes_schemas.Set.model_validate(
        {
            "Id": 390001,
            "Release Date": None,
            "Full Name": "Print on Demand",
            "Abbrev": "POD",
            "Company": "Paradox Interactive AB",
        }
    ),
    vtes_schemas.Set.model_validate(
        {
            "Id": 390002,
            "Release Date": None,
            "Full Name": "Promo",
            "Abbrev": "Promo",
            "Company": "Paradox Interactive AB",
        }
    ),
    vtes_schemas.Set.model_validate(
        {
            "Id": 392201,
            "Release Date": "20221022",
            "Full Name": "2022 Promo",
            "Abbrev": "Promo-20221022",
            "Company": "Paradox Interactive AB",
        }
    ),
    vtes_schemas.Set.model_validate(
        {
            "Id": 392202,
            "Release Date": "20221101",
            "Full Name": "2022 Promo",
            "Abbrev": "Promo-20221101",
            "Company": "Paradox Interactive AB",
        }
    ),
    vtes_schemas.Set.model_validate(
        {
            "Id": 392203,
            "Release Date": "20221105",
            "Full Name": "2022 Promo",
            "Abbrev": "Promo-20221105",
            "Company": "Paradox Interactive AB",
        }
    ),
    vtes_schemas.Set.model_validate(
        {
            "Id": 392301,
            "Release Date": "20230325",
            "Full Name": "2023 Promo",
            "Abbrev": "Promo-20230325",
            "Company": "Paradox Interactive AB",
        }
    ),
    vtes_schemas.Set.model_validate(
        {
            "Id": 392302,
            "Release Date": "20230507",
            "Full Name": "2023 Promo",
            "Abbrev": "Promo-20230507",
            "Company": "Paradox Interactive AB",
        }
    ),
    vtes_schemas.Set.model_validate(
        {
            "Id": 392303,
            "Release Date": "20230531",
            "Full Name": "2023 Promo",
            "Abbrev": "Promo-20230531",
            "Company": "Paradox Interactive AB",
        }
    ),
    vtes_schemas.Set.model_validate(
        {
            "Id": 392304,
            "Release Date": "20230603",
            "Full Name": "2023 Promo",
            "Abbrev": "Promo-20230603",
            "Company": "Paradox Interactive AB",
        }
    ),
    vtes_schemas.Set.model_validate(
        {
            "Id": 392305,
            "Release Date": "20230501",
            "Full Name": "2023 Promo",
            "Abbrev": "Promo-20230501",
            "Company": "Paradox Interactive AB",
        }
    ),
    vtes_schemas.Set.model_validate(
        {
            "Id": 392306,
            "Release Date": "20230729",
            "Full Name": "2023 Promo",
            "Abbrev": "Promo-20230729",
            "Company": "Paradox Interactive AB",
        }
    ),
    vtes_schemas.Set.model_validate(
        {
            "Id": 392307,
            "Release Date": "20230916",
            "Full Name": "2023 Promo",
            "Abbrev": "Promo-20230916",
            "Company": "Paradox Interactive AB",
        }
    ),
    vtes_schemas.Set.model_validate(
        {
            "Id": 392308,
            "Release Date": "20231007",
            "Full Name": "2023 Promo",
            "Abbrev": "Promo-20231007",
            "Company": "Paradox Interactive AB",
        }
    ),
]
