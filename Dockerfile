FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates && rm -rf /var/lib/apt/lists/*

# uv : gestionnaire de paquets et d'environnement du projet
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY pyproject.toml uv.lock .python-version ./
COPY src ./src
RUN uv sync --frozen

ENV PATH="/app/.venv/bin:$PATH"

# Le répertoire database/ est créé automatiquement par database.py au démarrage.
# Monter /app/database comme volume pour persister la base SQLite entre les redémarrages.
# Le fichier .env ne doit PAS être copié dans l'image : fournir les secrets via
# --env-file .env au lancement (docker run) ou via les variables d'environnement.
#
# LOCAL_DATABASE_DIR est fixée explicitement : une fois le paquet installé,
# remonter depuis le fichier source (core/database.py) ne retrouve plus la
# racine du dépôt cloné, qui n'existe pas dans l'image.
ENV LOCAL_DATABASE_DIR=/app/database

CMD ["oceens"]
