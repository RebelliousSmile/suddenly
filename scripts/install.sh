#!/bin/bash
# =================================================================
# Suddenly - Script d'installation
# =================================================================
# Usage: curl -sSL https://suddenly.social/install.sh | bash
#        ou: ./scripts/install.sh

set -euo pipefail

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Fonctions utilitaires
info() { echo -e "${BLUE}ℹ${NC} $1"; }
success() { echo -e "${GREEN}✓${NC} $1"; }
warn() { echo -e "${YELLOW}⚠${NC} $1"; }
error() { echo -e "${RED}✗${NC} $1"; exit 1; }

# =================================================================
# Vérifications préalables
# =================================================================
echo ""
echo -e "${BLUE}🎭 Installation de Suddenly${NC}"
echo "   Réseau fédéré de fiction partagée"
echo ""

# Vérifier Docker
if ! command -v docker &> /dev/null; then
    error "Docker n'est pas installé. Installez-le d'abord: https://docs.docker.com/get-docker/"
fi

# Vérifier Docker Compose
if ! docker compose version &> /dev/null && ! command -v docker-compose &> /dev/null; then
    error "Docker Compose n'est pas installé."
fi

# Déterminer la commande compose
if docker compose version &> /dev/null; then
    COMPOSE="docker compose"
else
    COMPOSE="docker-compose"
fi

info "Docker trouvé: $(docker --version)"
info "Compose: $COMPOSE"
echo ""

# =================================================================
# Configuration
# =================================================================
info "Configuration de votre instance..."
echo ""

# Domaine
read -p "Domaine de votre instance (ex: suddenly.example.com): " DOMAIN
if [[ -z "$DOMAIN" ]]; then
    error "Le domaine est requis"
fi

# Email admin (pour Let's Encrypt)
read -p "Email administrateur (pour les certificats SSL): " ADMIN_EMAIL
if [[ -z "$ADMIN_EMAIL" ]]; then
    error "L'email est requis pour Let's Encrypt"
fi

# Générer les secrets
SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_urlsafe(50))' 2>/dev/null || openssl rand -base64 50 | tr -d '\n')
POSTGRES_PASSWORD=$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))' 2>/dev/null || openssl rand -base64 32 | tr -d '\n')

success "Secrets générés"

# =================================================================
# Création des fichiers de configuration
# =================================================================
info "Création de la configuration..."

# Créer .env
cat > .env << EOF
# Suddenly - Configuration générée le $(date)
DOMAIN=${DOMAIN}
SECRET_KEY=${SECRET_KEY}
POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
POSTGRES_USER=suddenly
POSTGRES_DB=suddenly
DEBUG=false
ADMIN_EMAIL=${ADMIN_EMAIL}
EOF

success "Fichier .env créé"

# Remplacer ${DOMAIN} dans la config nginx
if [[ -f nginx/conf.d/suddenly.conf.template ]]; then
    envsubst '${DOMAIN}' < nginx/conf.d/suddenly.conf.template > nginx/conf.d/suddenly.conf
    success "Configuration Nginx générée"
fi

# =================================================================
# Obtention des certificats SSL
# =================================================================
info "Obtention des certificats SSL..."

# Créer une config nginx temporaire pour le challenge ACME
cat > nginx/conf.d/temp-acme.conf << 'EOF'
server {
    listen 80;
    listen [::]:80;
    server_name _;
    
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }
    
    location / {
        return 200 'Suddenly installation in progress...';
        add_header Content-Type text/plain;
    }
}
EOF

# Démarrer nginx temporairement
$COMPOSE up -d nginx

# Obtenir les certificats
docker run --rm \
    -v "$(pwd)/certs:/etc/letsencrypt" \
    -v "$(pwd)/certbot-webroot:/var/www/certbot" \
    certbot/certbot certonly \
    --webroot \
    --webroot-path=/var/www/certbot \
    --email "$ADMIN_EMAIL" \
    --agree-tos \
    --no-eff-email \
    -d "$DOMAIN"

# Supprimer la config temporaire
rm -f nginx/conf.d/temp-acme.conf

$COMPOSE down

success "Certificats SSL obtenus"

# =================================================================
# Démarrage des services
# =================================================================
info "Démarrage des services..."

$COMPOSE pull
$COMPOSE up -d

success "Services démarrés"

# =================================================================
# Initialisation de la base de données
# =================================================================
info "Initialisation de la base de données..."

# Attendre que la DB soit prête
sleep 5

$COMPOSE exec -T web python manage.py migrate

success "Base de données initialisée"

# =================================================================
# Création du compte admin
# =================================================================
echo ""
info "Création du compte administrateur..."
$COMPOSE exec web python manage.py createsuperuser

# =================================================================
# Terminé !
# =================================================================
echo ""
echo -e "${GREEN}════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✓ Suddenly est installé !${NC}"
echo -e "${GREEN}════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "  🌐 Votre instance: ${BLUE}https://${DOMAIN}${NC}"
echo -e "  🔧 Admin:          ${BLUE}https://${DOMAIN}/admin/${NC}"
echo ""
echo -e "  📋 Commandes utiles:"
echo -e "     ${YELLOW}$COMPOSE logs -f${NC}        # Voir les logs"
echo -e "     ${YELLOW}$COMPOSE restart${NC}        # Redémarrer"
echo -e "     ${YELLOW}$COMPOSE down${NC}           # Arrêter"
echo -e "     ${YELLOW}./scripts/backup.sh${NC}     # Sauvegarder"
echo ""
echo -e "  📚 Documentation: https://github.com/votre-repo/suddenly"
echo ""
