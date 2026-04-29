#!/bin/bash
# =================================================================
# Suddenly — Vérification de la configuration email
# =================================================================
# Usage : ./scripts/check-email.sh [destinataire@exemple.com]
# Lancer depuis la racine du projet.

set -euo pipefail

# ------------------------------------------------------------------
# Utilitaires
# ------------------------------------------------------------------
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

ok()    { echo -e "${GREEN}  ✓${NC} $1"; }
warn()  { echo -e "${YELLOW}  !${NC} $1"; }
error() { echo -e "${RED}  ✗${NC} $1"; }
step()  { echo -e "\n${GREEN}==>${NC} $1"; }

DEST="${1:-}"

# ------------------------------------------------------------------
# Chemins
# ------------------------------------------------------------------
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="$APP_DIR/venv"
PYTHON="$VENV/bin/python"

cd "$APP_DIR"

[ -f "$PYTHON" ] || { error "Virtualenv introuvable à $VENV"; exit 1; }

# ------------------------------------------------------------------
# Chargement .env
# ------------------------------------------------------------------
if [ -f "$APP_DIR/.env" ]; then
    step "Chargement des variables d'environnement (.env)"
    set -a
    # shellcheck disable=SC1091
    source "$APP_DIR/.env"
    set +a
    ok ".env chargé"
else
    warn "Aucun fichier .env trouvé — les variables doivent être définies dans l'environnement"
fi

# ------------------------------------------------------------------
# Vérification des variables
# ------------------------------------------------------------------
step "Vérification des variables EMAIL_*"

MISSING=0

check_var() {
    local name="$1"
    local required="${2:-false}"
    local val="${!name:-}"
    if [ -n "$val" ]; then
        if [[ "$name" == *PASSWORD* ]]; then
            ok "$name = ****"
        else
            ok "$name = $val"
        fi
    elif [ "$required" = "true" ]; then
        error "$name non définie (obligatoire)"
        MISSING=$((MISSING + 1))
    else
        warn "$name non définie (optionnelle)"
    fi
}

check_var EMAIL_HOST        true
check_var EMAIL_PORT        false
check_var EMAIL_HOST_USER   false
check_var EMAIL_HOST_PASSWORD false
check_var EMAIL_USE_TLS     false
check_var DEFAULT_FROM_EMAIL false

if [ "$MISSING" -gt 0 ]; then
    echo -e "\n${RED}[ÉCHEC]${NC} $MISSING variable(s) obligatoire(s) manquante(s). Arrêt."
    exit 1
fi

# ------------------------------------------------------------------
# Test d'envoi
# ------------------------------------------------------------------
if [ -z "$DEST" ]; then
    echo -e "\n${YELLOW}Aucun destinataire fourni — test d'envoi ignoré.${NC}"
    echo "  Pour tester l'envoi : $0 votre@email.com"
    exit 0
fi

step "Envoi d'un email de test à $DEST"

DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-config.settings.production}"
export DJANGO_SETTINGS_MODULE

$PYTHON - <<EOF
import os, sys, django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "$DJANGO_SETTINGS_MODULE")

try:
    django.setup()
except Exception as e:
    print(f"[ERREUR] Django setup : {e}", file=sys.stderr)
    sys.exit(1)

from django.conf import settings
from django.core.mail import send_mail

backend = settings.EMAIL_BACKEND
print(f"  Backend  : {backend}")
print(f"  Host     : {getattr(settings, 'EMAIL_HOST', '(non défini)')}")
print(f"  Port     : {getattr(settings, 'EMAIL_PORT', '(non défini)')}")
print(f"  TLS      : {getattr(settings, 'EMAIL_USE_TLS', '(non défini)')}")
print(f"  From     : {getattr(settings, 'DEFAULT_FROM_EMAIL', '(non défini)')}")

if "dummy" in backend or "console" in backend:
    print(f"\n[AVERT] Le backend actuel ({backend}) n'envoie pas réellement d'email.", file=sys.stderr)
    sys.exit(1)

try:
    sent = send_mail(
        subject="[Suddenly] Test de configuration email",
        message="Ce message confirme que la configuration SMTP de Suddenly est opérationnelle.",
        from_email=None,
        recipient_list=["$DEST"],
        fail_silently=False,
    )
    if sent:
        print(f"\n[OK] Email envoyé à $DEST")
    else:
        print(f"\n[ÉCHEC] send_mail a retourné 0", file=sys.stderr)
        sys.exit(1)
except Exception as e:
    print(f"\n[ERREUR] {e}", file=sys.stderr)
    sys.exit(1)
EOF

echo -e "\n${GREEN}[SUCCÈS]${NC} Configuration email opérationnelle."
