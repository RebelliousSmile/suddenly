#!/bin/bash
# =================================================================
# Suddenly - Script de restauration
# =================================================================
# Usage: ./scripts/restore.sh /chemin/vers/backup/suddenly_backup_20240101_120000

set -euo pipefail

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info() { echo -e "${BLUE}ℹ${NC} $1"; }
success() { echo -e "${GREEN}✓${NC} $1"; }
warn() { echo -e "${YELLOW}⚠${NC} $1"; }
error() { echo -e "${RED}✗${NC} $1"; exit 1; }

# Vérifier les arguments
if [[ $# -lt 1 ]]; then
    echo "Usage: $0 <préfixe_backup>"
    echo "Exemple: $0 ./backups/suddenly_backup_20240101_120000"
    exit 1
fi

BACKUP_PREFIX="$1"

# Vérifier que les fichiers existent
DB_BACKUP="${BACKUP_PREFIX}_db.sql.gz"
MEDIA_BACKUP="${BACKUP_PREFIX}_media.tar.gz"

if [[ ! -f "$DB_BACKUP" ]]; then
    error "Fichier non trouvé: $DB_BACKUP"
fi

# Déterminer la commande compose
if docker compose version &> /dev/null; then
    COMPOSE="docker compose"
else
    COMPOSE="docker-compose"
fi

# =================================================================
# Confirmation
# =================================================================
echo ""
warn "ATTENTION: Cette opération va écraser les données actuelles !"
echo ""
echo "  Fichiers à restaurer:"
echo "    - Base de données: $DB_BACKUP"
[[ -f "$MEDIA_BACKUP" ]] && echo "    - Media: $MEDIA_BACKUP"
echo ""
read -p "Continuer ? (oui/non) " CONFIRM

if [[ "$CONFIRM" != "oui" ]]; then
    echo "Annulé."
    exit 0
fi

# =================================================================
# Arrêt des services (sauf DB)
# =================================================================
info "Arrêt des services..."

$COMPOSE stop web celery celery-beat nginx 2>/dev/null || true

# =================================================================
# Restauration de la base de données
# =================================================================
info "Restauration de la base de données..."

# Supprimer et recréer la base
$COMPOSE exec -T db psql -U suddenly -c "DROP DATABASE IF EXISTS suddenly;"
$COMPOSE exec -T db psql -U suddenly -c "CREATE DATABASE suddenly;"

# Restaurer
gunzip -c "$DB_BACKUP" | $COMPOSE exec -T db psql -U suddenly suddenly

success "Base de données restaurée"

# =================================================================
# Restauration des fichiers media
# =================================================================
if [[ -f "$MEDIA_BACKUP" ]]; then
    info "Restauration des fichiers media..."
    
    docker run --rm \
        -v suddenly_media:/dest \
        -v "$(realpath "$(dirname "$MEDIA_BACKUP")")":/backup \
        alpine sh -c "rm -rf /dest/* && tar xzf /backup/$(basename "$MEDIA_BACKUP") -C /dest"
    
    success "Fichiers media restaurés"
else
    warn "Pas de backup media trouvé, ignoré"
fi

# =================================================================
# Redémarrage
# =================================================================
info "Redémarrage des services..."

$COMPOSE up -d

# =================================================================
# Terminé
# =================================================================
echo ""
success "Restauration terminée !"
echo ""
echo "  Vérifiez que tout fonctionne: $COMPOSE logs -f"
echo ""
