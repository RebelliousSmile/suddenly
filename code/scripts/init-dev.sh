#!/bin/bash
# =================================================================
# Suddenly - Script d'initialisation du développement
# =================================================================
# Usage: ./scripts/init-dev.sh
#
# Ce script prépare l'environnement de développement:
# 1. Génère les migrations
# 2. Applique les migrations
# 3. Crée un superuser si nécessaire
# 4. Génère les clés ActivityPub

set -e

# Couleurs
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

info() { echo -e "${BLUE}ℹ${NC} $1"; }
success() { echo -e "${GREEN}✓${NC} $1"; }

echo ""
echo "🎭 Initialisation de Suddenly (développement)"
echo ""

# Vérifier qu'on est dans le bon dossier
if [ ! -f "manage.py" ]; then
    echo "Erreur: Exécutez ce script depuis la racine du projet"
    exit 1
fi

# Générer les migrations
info "Génération des migrations..."
python manage.py makemigrations users
python manage.py makemigrations games
python manage.py makemigrations characters
success "Migrations générées"

# Appliquer les migrations
info "Application des migrations..."
python manage.py migrate
success "Base de données initialisée"

# Créer le dossier pour les clés
info "Création des clés ActivityPub..."
mkdir -p keys
python -c "
from suddenly.activitypub.signatures import ensure_instance_keys
ensure_instance_keys()
print('Clés générées')
"
success "Clés ActivityPub créées"

# Collecter les fichiers statiques
info "Collecte des fichiers statiques..."
python manage.py collectstatic --noinput
success "Fichiers statiques collectés"

# Proposer de créer un superuser
echo ""
read -p "Créer un compte administrateur ? (o/n) " CREATE_ADMIN
if [[ "$CREATE_ADMIN" == "o" || "$CREATE_ADMIN" == "O" ]]; then
    python manage.py createsuperuser
fi

echo ""
success "Initialisation terminée !"
echo ""
echo "  Démarrer le serveur de développement:"
echo "    python manage.py runserver"
echo ""
echo "  Ou avec Docker:"
echo "    docker compose -f docker-compose.dev.yml up"
echo ""
