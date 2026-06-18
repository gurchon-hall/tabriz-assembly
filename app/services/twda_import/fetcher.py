"""Récupération des tournois depuis le dépôt GitHub eternal-vigilance.

Deux étapes :
    1. ``list_tournament_yaml_paths`` énumère les fichiers YAML valides via
       l'API GitHub *git trees* (une requête, authentifiée si un token est fourni).
    2. ``fetch_tournament_yaml`` télécharge le contenu brut d'un fichier
       (non soumis à la limite de débit de l'API) et le valide en YamlTournament.
"""

import json
import urllib.error
import urllib.request

import yaml
from pydantic import ValidationError

from app.config import settings
from app.schemas.tournament import YamlTournament
from app.services.twda_import.constants import (
    RAW_URL_TEMPLATE,
    TREES_URL_TEMPLATE,
    VALID_PATH_RE,
)

logger = settings.log.get_logger(__name__)


def _get(url: str, token: str | None, accept: str, timeout: int = 30) -> bytes:
    """Effectue une requête GET et retourne le corps de la réponse."""
    headers = {"User-Agent": "tabriz-assembly", "Accept": accept}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read()  # type: ignore[no-any-return]
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")[:300]
        raise RuntimeError(f"Échec GET {url} : HTTP {exc.code} — {body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Échec GET {url} : {exc}") from exc


def list_tournament_yaml_paths(repo: str, branch: str, token: str | None) -> list[str]:
    """Liste les chemins des YAML de tournois valides via l'API git trees.

    Filtre sur ``^\\d{4}/\\d{2}/\\d+\\.yaml$`` (exclut errors/ et changes_required/).
    """
    url = TREES_URL_TEMPLATE.format(repo=repo, branch=branch)
    data = json.loads(_get(url, token, "application/vnd.github+json"))

    if data.get("truncated"):
        raise RuntimeError(
            f"L'arbre git de {repo}@{branch} est tronqué (limite API GitHub). "
            "Une énumération paginée est nécessaire."
        )

    paths = [
        entry["path"]
        for entry in data.get("tree", [])
        if entry.get("type") == "blob" and VALID_PATH_RE.match(entry.get("path", ""))
    ]
    paths.sort()
    return paths


def fetch_tournament_yaml(
    repo: str, branch: str, path: str, token: str | None
) -> YamlTournament | None:
    """Télécharge et valide un fichier YAML de tournoi.

    Retourne ``None`` (avec un log) si le contenu est invalide, pour qu'un
    fichier corrompu n'interrompe pas l'import global.
    """
    url = RAW_URL_TEMPLATE.format(repo=repo, branch=branch, path=path)
    raw = _get(url, token, "*/*")

    try:
        payload = yaml.safe_load(raw)
        return YamlTournament.model_validate(payload)
    except (ValidationError, yaml.YAMLError) as exc:
        logger.warning("%s : YAML invalide, ignoré — %s", path, exc)
        return None
