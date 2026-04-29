#!/bin/bash
# =================================================================
# Suddenly — Script de déploiement Alwaysdata
# =================================================================
# Usage : ./scripts/deploy-alwaysdata.sh
# Lancer depuis la racine du projet après un git pull.
#
# Ce script suppose que :
#   - Le virtualenv existe à <projet>/venv/
#   - Les variables d'env sont dans <projet>/.env (format KEY=VALUE)
#     (les vars du panel Alwaysdata ne sont pas disponibles en SSH)

set -euo pipefail

# ------------------------------------------------------------------
# Utilitaires
# ------------------------------------------------------------------
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

step()  { echo -e "${GREEN}==>${NC} $1"; }
warn()  { echo -e "${YELLOW}[warn]${NC} $1"; }
error() { echo -e "${RED}[error]${NC} $1"; exit 1; }

# ------------------------------------------------------------------
# Chemins
# ------------------------------------------------------------------
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="$APP_DIR/venv"
PYTHON="$VENV/bin/python"
PIP="$VENV/bin/pip"

cd "$APP_DIR"

# ------------------------------------------------------------------
# Vérifications
# ------------------------------------------------------------------
[ -f "$PYTHON" ] || error "Virtualenv introuvable à $VENV. Créez-le d'abord : python3.12 -m venv venv"

# ------------------------------------------------------------------
# Variables d'environnement
# Les vars du panel Alwaysdata ne sont pas disponibles en SSH.
# Chargez-les depuis un fichier .env (non versionné).
# ------------------------------------------------------------------
if [ -f "$APP_DIR/.env" ]; then
    step "Chargement des variables d'environnement (.env)"
    set -a
    # shellcheck disable=SC1091
    source "$APP_DIR/.env"
    set +a
else
    warn "Fichier .env introuvable — les variables doivent être déjà exportées dans le shell."
fi

# ------------------------------------------------------------------
# 1. Dépendances Python
# ------------------------------------------------------------------
step "Mise à jour des dépendances Python"
"$PIP" install --quiet --upgrade pip
"$PIP" install --quiet -e '.[federation]'

# ------------------------------------------------------------------
# 2. Migrations base de données
# ------------------------------------------------------------------
step "Migrations Django"
"$PYTHON" manage.py migrate --noinput

# ------------------------------------------------------------------
# 3. Table de cache DB (pas de Redis sur Alwaysdata)
# ------------------------------------------------------------------
step "Table de cache DB"
"$PYTHON" manage.py createcachetable 2>/dev/null || true

# ------------------------------------------------------------------
# 4. Fichiers statiques
# ------------------------------------------------------------------
step "Collecte des fichiers statiques"
"$PYTHON" manage.py collectstatic --noinput --clear

# ------------------------------------------------------------------
# 5. Redémarrage de l'application
# Touch sur wsgi.py déclenche le rechargement par Alwaysdata.
# ------------------------------------------------------------------
step "Redémarrage (touch wsgi.py)"
touch "$APP_DIR/suddenly/wsgi.py"

# ------------------------------------------------------------------
echo ""
echo -e "${GREEN}Déploiement terminé.${NC}"
echo ""
echo "  Vérifications rapides :"
echo "    curl https://\$DOMAIN/health/"
echo "    curl https://\$DOMAIN/.well-known/nodeinfo"
