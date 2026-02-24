#!/bin/bash
# =================================================================
# Suddenly - Script de sauvegarde
# =================================================================
# Usage: ./scripts/backup.sh
#        ./scripts/backup.sh /chemin/vers/backup

set -euo pipefail

# Configuration
BACKUP_DIR="${1:-./backups}"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="suddenly_backup_${DATE}"

# Couleurs
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

info() { echo -e "${BLUE}ℹ${NC} $1"; }
success() { echo -e "${GREEN}✓${NC} $1"; }

# Créer le dossier de backup
mkdir -p "$BACKUP_DIR"

info "Démarrage de la sauvegarde..."

# =================================================================
# Sauvegarde de la base de données
# =================================================================
info "Sauvegarde PostgreSQL..."

# Déterminer la commande compose
if docker compose version &> /dev/null; then
    COMPOSE="docker compose"
else
    COMPOSE="docker-compose"
fi

$COMPOSE exec -T db pg_dump -U suddenly suddenly | gzip > "$BACKUP_DIR/${BACKUP_NAME}_db.sql.gz"

success "Base de données sauvegardée"

# =================================================================
# Sauvegarde des fichiers media
# =================================================================
info "Sauvegarde des fichiers media..."

# Copier depuis le volume Docker
docker run --rm \
    -v suddenly_media:/source:ro \
    -v "$(realpath "$BACKUP_DIR")":/backup \
    alpine tar czf "/backup/${BACKUP_NAME}_media.tar.gz" -C /source .

success "Fichiers media sauvegardés"

# =================================================================
# Sauvegarde de la configuration
# =================================================================
info "Sauvegarde de la configuration..."

tar czf "$BACKUP_DIR/${BACKUP_NAME}_config.tar.gz" \
    .env \
    docker-compose.yml \
    nginx/ \
    2>/dev/null || true

success "Configuration sauvegardée"

# =================================================================
# Nettoyage des anciennes sauvegardes (garder 7 jours)
# =================================================================
info "Nettoyage des anciennes sauvegardes..."

find "$BACKUP_DIR" -name "suddenly_backup_*" -mtime +7 -delete 2>/dev/null || true

# =================================================================
# Résumé
# =================================================================
echo ""
success "Sauvegarde terminée !"
echo ""
echo "  Fichiers créés dans $BACKUP_DIR:"
ls -lh "$BACKUP_DIR"/${BACKUP_NAME}* 2>/dev/null | awk '{print "    " $9 " (" $5 ")"}'
echo ""
echo "  Pour restaurer:"
echo "    1. Base de données: gunzip -c ${BACKUP_NAME}_db.sql.gz | docker compose exec -T db psql -U suddenly suddenly"
echo "    2. Media: docker run --rm -v suddenly_media:/dest -v \$(pwd):/backup alpine tar xzf /backup/${BACKUP_NAME}_media.tar.gz -C /dest"
echo ""
