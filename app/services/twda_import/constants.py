import re

# Seuls les fichiers `YYYY/MM/<event_id>.yaml` sont des tournois valides.
# Les répertoires errors/ et changes_required/ sont ainsi exclus.
VALID_PATH_RE: re.Pattern[str] = re.compile(r"^\d{4}/\d{2}/\d+\.ya?ml$")

# API GitHub : arbre récursif d'une branche (1 seule requête).
TREES_URL_TEMPLATE = "https://api.github.com/repos/{repo}/git/trees/{branch}?recursive=1"

# Contenu brut d'un fichier (non soumis à la limite de débit de l'API).
RAW_URL_TEMPLATE = "https://raw.githubusercontent.com/{repo}/{branch}/{path}"
