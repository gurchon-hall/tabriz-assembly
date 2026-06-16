import csv
import urllib.error
import urllib.request
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from app.config import settings

logger = settings.log.get_logger(__name__)

T = TypeVar("T", bound=BaseModel)


def download_file(url: str, destination: Path, timeout: int = 30) -> None:
    """Télécharge un fichier depuis une URL vers un chemin local."""
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = response.read()
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Échec du téléchargement de {url} : {exc}") from exc

    destination.write_bytes(data)


def parse_file_as[T: BaseModel](path: Path | str, model: type[T]) -> list[T]:
    """Parse un fichier CSV en liste d'instances du modèle Pydantic donné.

    Les lignes invalides sont ignorées et loggées avec leur numéro de ligne
    et les champs identifiants disponibles (Id, Name).
    """
    path = Path(path)
    results: list[T] = []

    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for line_number, row in enumerate(reader, start=2):  # start=2 : ligne 1 = headers
            try:
                results.append(model.model_validate(row))
            except ValidationError as exc:
                card_id = row.get("Id", "?")
                card_name = row.get("Name", "?")
                logger.warning(
                    "%s ligne %d (Id=%s, Name=%s) : validation échouée — %s",
                    path.name,
                    line_number,
                    card_id,
                    card_name,
                    exc,
                )

    return results
