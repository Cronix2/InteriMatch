#!/usr/bin/env bash
# =============================================================================
# InteriMatch AI — Script de déploiement interactif (WSL / Linux)
#
# Usage: ./deploy.sh [OPTIONS]
#   --mode <0|1|2>       Mode de déploiement (0=Docker, 1=Local, 2=Hybride)
#   --reconfigure-env    Reconfigurer le fichier .env
#   --build              Reconstruire les images Docker (mode Docker)
#   --no-build           Ne pas reconstruire les images Docker
#   --auto               Mode non-interactif (utilise les valeurs par défaut)
#   -h, --help           Afficher l'aide
#
# Sans options, le script fonctionne en mode interactif.
# =============================================================================
set -euo pipefail

# ─── Couleurs ────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# ─── Helpers ─────────────────────────────────────────────────────────────────
info()    { echo -e "${BLUE}[INFO]${NC} $*"; }
success() { echo -e "${GREEN}[OK]${NC} $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC} $*"; }
error()   { echo -e "${RED}[ERREUR]${NC} $*"; }
header()  { echo -e "\n${BOLD}${CYAN}═══ $* ═══${NC}\n"; }

ask_yes_no() {
    local prompt="$1"
    local default="${2:-o}"
    if [[ "$AUTO_MODE" -eq 1 ]]; then
        [[ "$default" == "o" ]] && return 0 || return 1
    fi
    local choices
    if [[ "$default" == "o" ]]; then choices="[O/n]"; else choices="[o/N]"; fi
    while true; do
        read -rp "$(echo -e "${YELLOW}▸${NC} ${prompt} ${choices} ")" yn
        yn="${yn:-$default}"
        case "${yn,,}" in
            o|oui|y|yes) return 0 ;;
            n|non|no)    return 1 ;;
            *) echo "  Répondez par o (oui) ou n (non)." ;;
        esac
    done
}

ask_choice() {
    local prompt="$1"
    shift
    local options=("$@")
    if [[ "$AUTO_MODE" -eq 1 ]]; then
        return 0
    fi
    echo -e "${YELLOW}▸${NC} ${prompt}"
    for i in "${!options[@]}"; do
        echo -e "  ${BOLD}$((i+1)))${NC} ${options[$i]}"
    done
    while true; do
        read -rp "$(echo -e "  ${CYAN}Choix [1-${#options[@]}]:${NC} ")" choice
        if [[ "$choice" =~ ^[0-9]+$ ]] && (( choice >= 1 && choice <= ${#options[@]} )); then
            return $((choice - 1))
        fi
        echo "  Choix invalide."
    done
}

ask_input() {
    local prompt="$1"
    local default="${2:-}"
    if [[ "$AUTO_MODE" -eq 1 ]]; then
        echo "$default"
        return
    fi
    local hint=""
    if [[ -n "$default" ]]; then hint=" (défaut: ${default})"; fi
    read -rp "$(echo -e "${YELLOW}▸${NC} ${prompt}${hint}: ")" value
    echo "${value:-$default}"
}

# ─── Parsing des arguments CLI ───────────────────────────────────────────────
AUTO_MODE=0
CLI_DEPLOY_MODE=""
CLI_RECONFIG_ENV=""
CLI_BUILD=""

show_help() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options :"
    echo "  --mode <0|1|2>       Mode de déploiement"
    echo "                         0 = Docker Compose (recommandé)"
    echo "                         1 = Local (Python venv + npm)"
    echo "                         2 = Hybride (DB Docker + app locale)"
    echo "  --reconfigure-env    Reconfigurer le fichier .env"
    echo "  --build              Reconstruire les images Docker"
    echo "  --no-build           Ne pas reconstruire les images Docker"
    echo "  --auto               Mode non-interactif (valeurs par défaut)"
    echo "  -h, --help           Afficher cette aide"
    echo ""
    echo "Exemples :"
    echo "  $0                              # Mode interactif"
    echo "  $0 --mode 0 --build             # Docker Compose avec rebuild"
    echo "  $0 --mode 0 --no-build --auto   # Docker rapide, sans interaction"
    exit 0
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --mode)
            if [[ -z "${2:-}" ]] || [[ ! "$2" =~ ^[012]$ ]]; then
                error "--mode doit être 0, 1 ou 2"
                exit 1
            fi
            CLI_DEPLOY_MODE="$2"
            shift 2
            ;;
        --reconfigure-env)
            CLI_RECONFIG_ENV="1"
            shift
            ;;
        --build)
            CLI_BUILD="1"
            shift
            ;;
        --no-build)
            CLI_BUILD="0"
            shift
            ;;
        --auto)
            AUTO_MODE=1
            shift
            ;;
        -h|--help)
            show_help
            ;;
        *)
            error "Option inconnue : $1"
            echo "Utilisez --help pour voir les options disponibles."
            exit 1
            ;;
    esac
done

# ─── Détection du dossier projet ─────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

header "InteriMatch AI — Déploiement"
info "Dossier projet : ${BOLD}$SCRIPT_DIR${NC}"
echo ""

# ─── Vérification des prérequis ──────────────────────────────────────────────
header "Vérification des prérequis"

check_cmd() {
    if command -v "$1" &>/dev/null; then
        success "$1 trouvé ($(command -v "$1"))"
        return 0
    else
        error "$1 non trouvé"
        return 1
    fi
}

MISSING=0
check_cmd docker   || MISSING=1
docker compose version &>/dev/null && success "docker compose disponible" || { error "docker compose non disponible"; MISSING=1; }
check_cmd git      || true  # optionnel

if [[ "$MISSING" -eq 1 ]]; then
    error "Prérequis manquants. Installez Docker et Docker Compose avant de continuer."
    exit 1
fi

# Vérifier que le daemon Docker tourne
if ! docker info &>/dev/null 2>&1; then
    error "Le daemon Docker ne tourne pas."
    if ask_yes_no "Tenter de démarrer Docker ?"; then
        sudo service docker start 2>/dev/null || sudo systemctl start docker 2>/dev/null || true
        sleep 2
        if ! docker info &>/dev/null 2>&1; then
            error "Impossible de démarrer Docker. Lancez-le manuellement."
            exit 1
        fi
        success "Docker démarré"
    else
        exit 1
    fi
fi

# ─── Mode de déploiement ─────────────────────────────────────────────────────
header "Mode de déploiement"

if [[ -n "$CLI_DEPLOY_MODE" ]]; then
    DEPLOY_MODE=$CLI_DEPLOY_MODE
    local_names=("Docker Compose" "Local" "Hybride")
    info "Mode sélectionné via CLI : ${BOLD}${local_names[$DEPLOY_MODE]}${NC}"
else
    ask_choice "Comment voulez-vous déployer ?" \
        "Docker Compose (recommandé — tout en conteneurs)" \
        "Local (Python venv + npm — sans Docker pour backend/frontend)" \
        "Docker uniquement DB + Redis, backend/frontend en local"
    DEPLOY_MODE=$?
fi

# ─── Configuration .env ──────────────────────────────────────────────────────
header "Configuration de l'environnement"

if [[ -f .env ]]; then
    if [[ "$CLI_RECONFIG_ENV" == "1" ]]; then
        CONFIGURE_ENV=1
        info "Reconfiguration du .env (option CLI)"
    elif [[ "$AUTO_MODE" -eq 1 ]]; then
        CONFIGURE_ENV=0
        success "Conservation du .env existant (mode auto)"
    else
        warn "Un fichier .env existe déjà."
        if ask_yes_no "Reconfigurer le .env ?" "n"; then
            CONFIGURE_ENV=1
        else
            CONFIGURE_ENV=0
            success "Conservation du .env existant"
        fi
    fi
else
    info "Pas de .env trouvé, création à partir du template."
    CONFIGURE_ENV=1
fi

if [[ "$CONFIGURE_ENV" -eq 1 ]]; then
    cp .env.example .env
    success "Fichier .env créé depuis .env.example"
    echo ""

    # Secret Key
    if ask_yes_no "Générer une SECRET_KEY aléatoire sécurisée ?" ; then
        NEW_SECRET=$(openssl rand -hex 32 2>/dev/null || python3 -c "import secrets; print(secrets.token_hex(32))")
        sed -i "s|^SECRET_KEY=.*|SECRET_KEY=${NEW_SECRET}|" .env
        success "SECRET_KEY générée"
    fi

    # AI config
    echo ""
    info "Configuration IA :"
    AI_KEY=$(ask_input "Clé API du LLM (laisser vide si pas nécessaire)" "")
    if [[ -n "$AI_KEY" ]]; then
        sed -i "s|^AI_API_KEY=.*|AI_API_KEY=${AI_KEY}|" .env
    fi

    AI_URL=$(ask_input "URL du serveur LLM" "https://trust.liveintelligence.orange-business.com")
    sed -i "s|^AI_SERVER_URL=.*|AI_SERVER_URL=${AI_URL}|" .env

    AI_MODEL=$(ask_input "Modèle IA" "alfred-4.2")
    sed -i "s|^AI_MODEL=.*|AI_MODEL=${AI_MODEL}|" .env

    # France Travail
    echo ""
    info "Configuration API France Travail :"
    FT_ID=$(ask_input "Client ID France Travail (laisser vide pour plus tard)" "")
    FT_SECRET=$(ask_input "Client Secret France Travail (laisser vide pour plus tard)" "")
    if [[ -n "$FT_ID" ]]; then
        sed -i "s|^FRANCE_TRAVAIL_CLIENT_ID=.*|FRANCE_TRAVAIL_CLIENT_ID=${FT_ID}|" .env
    fi
    if [[ -n "$FT_SECRET" ]]; then
        sed -i "s|^FRANCE_TRAVAIL_CLIENT_SECRET=.*|FRANCE_TRAVAIL_CLIENT_SECRET=${FT_SECRET}|" .env
    fi

    # PostgreSQL
    echo ""
    if ask_yes_no "Personnaliser les identifiants PostgreSQL ?" "n"; then
        PG_USER=$(ask_input "Utilisateur PostgreSQL" "interimatch")
        PG_PASS=$(ask_input "Mot de passe PostgreSQL" "interimatch")
        PG_DB=$(ask_input "Nom de la base" "interimatch")
        sed -i "s|^POSTGRES_USER=.*|POSTGRES_USER=${PG_USER}|" .env
        sed -i "s|^POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=${PG_PASS}|" .env
        sed -i "s|^POSTGRES_DB=.*|POSTGRES_DB=${PG_DB}|" .env
        sed -i "s|^DATABASE_URL=.*|DATABASE_URL=postgresql+asyncpg://${PG_USER}:${PG_PASS}@localhost:5432/${PG_DB}|" .env
    fi

    success "Configuration .env terminée"
fi

echo ""

# ─── Déploiement ─────────────────────────────────────────────────────────────

deploy_docker_compose() {
    header "Déploiement Docker Compose"

    if [[ "$CLI_BUILD" == "1" ]]; then
        BUILD_FLAG="--build"
        info "Reconstruction des images (option CLI)"
    elif [[ "$CLI_BUILD" == "0" ]]; then
        BUILD_FLAG=""
        info "Pas de reconstruction (option CLI)"
    elif ask_yes_no "Reconstruire les images Docker (--build) ?" ; then
        BUILD_FLAG="--build"
    else
        BUILD_FLAG=""
    fi

    info "Lancement des conteneurs..."
    docker compose up -d $BUILD_FLAG

    echo ""
    info "Attente du démarrage des services..."
    sleep 5

    # Vérifier les conteneurs
    echo ""
    info "État des conteneurs :"
    docker compose ps
    echo ""

    # Vérifier la santé
    local retries=0
    local max_retries=30
    info "Vérification de la santé du backend..."
    while (( retries < max_retries )); do
        if curl -sf http://localhost:8000/health &>/dev/null; then
            success "Backend opérationnel"
            break
        fi
        retries=$((retries + 1))
        sleep 2
    done
    if (( retries >= max_retries )); then
        warn "Le backend ne répond pas encore. Vérifiez les logs : docker compose logs backend"
    fi
}

deploy_local() {
    header "Déploiement local"

    # Backend
    info "Installation du backend Python..."
    cd "$SCRIPT_DIR/backend"

    if [[ ! -d venv ]]; then
        info "Création du virtualenv..."
        python3 -m venv venv
    fi
    source venv/bin/activate
    pip install -q -r requirements.txt
    success "Dépendances Python installées"

    # Frontend
    info "Installation du frontend Node.js..."
    cd "$SCRIPT_DIR/frontend"

    if [[ ! -d node_modules ]]; then
        npm install
    else
        if ask_yes_no "node_modules existe. Réinstaller les dépendances ?" "n"; then
            rm -rf node_modules
            npm install
        fi
    fi
    success "Dépendances Node.js installées"

    # Créer .env.local frontend
    echo "NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1" > "$SCRIPT_DIR/frontend/.env.local"
    success "frontend/.env.local configuré"

    cd "$SCRIPT_DIR"

    echo ""
    info "Pour lancer PostgreSQL et Redis, vous avez besoin de Docker :"
    echo -e "  ${CYAN}docker compose up db redis -d${NC}"
    echo ""
    info "Puis lancez dans deux terminaux séparés :"
    echo -e "  ${CYAN}Terminal 1 (backend):${NC}  cd backend && source venv/bin/activate && uvicorn app.main:app --reload"
    echo -e "  ${CYAN}Terminal 2 (frontend):${NC} cd frontend && npm run dev"
}

deploy_hybrid() {
    header "Déploiement hybride (DB + Redis en Docker, app en local)"

    info "Lancement de PostgreSQL et Redis..."
    docker compose up db redis -d

    sleep 3
    info "État des conteneurs :"
    docker compose ps db redis
    echo ""

    # Attendre que PostgreSQL soit prêt
    local retries=0
    info "Attente de PostgreSQL..."
    while (( retries < 20 )); do
        if docker compose exec -T db pg_isready -U interimatch &>/dev/null 2>&1; then
            success "PostgreSQL prêt"
            break
        fi
        retries=$((retries + 1))
        sleep 2
    done
    if (( retries >= 20 )); then
        warn "PostgreSQL ne répond pas encore."
    fi

    # Backend
    info "Installation du backend Python..."
    cd "$SCRIPT_DIR/backend"

    if [[ ! -d venv ]]; then
        info "Création du virtualenv..."
        python3 -m venv venv
    fi
    source venv/bin/activate
    pip install -q -r requirements.txt
    success "Dépendances Python installées"

    # Frontend
    info "Installation du frontend Node.js..."
    cd "$SCRIPT_DIR/frontend"

    if [[ ! -d node_modules ]]; then
        npm install
    else
        if ask_yes_no "node_modules existe. Réinstaller les dépendances ?" "n"; then
            rm -rf node_modules
            npm install
        fi
    fi
    success "Dépendances Node.js installées"

    echo "NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1" > "$SCRIPT_DIR/frontend/.env.local"
    success "frontend/.env.local configuré"

    cd "$SCRIPT_DIR"

    echo ""
    if ask_yes_no "Lancer le backend et le frontend maintenant ?"; then
        info "Démarrage du backend..."
        cd "$SCRIPT_DIR/backend"
        source venv/bin/activate
        uvicorn app.main:app --reload &
        BACKEND_PID=$!
        success "Backend lancé (PID: $BACKEND_PID)"

        info "Démarrage du frontend..."
        cd "$SCRIPT_DIR/frontend"
        npm run dev &
        FRONTEND_PID=$!
        success "Frontend lancé (PID: $FRONTEND_PID)"

        cd "$SCRIPT_DIR"

        echo ""
        success "Services lancés en arrière-plan !"
        echo -e "  ${CYAN}Backend PID:${NC}  $BACKEND_PID"
        echo -e "  ${CYAN}Frontend PID:${NC} $FRONTEND_PID"
        echo -e "  Pour arrêter : ${BOLD}kill $BACKEND_PID $FRONTEND_PID${NC}"

        # Trap pour cleanup
        trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM

        echo ""
        info "Appuyez sur Ctrl+C pour tout arrêter."
        wait
    else
        echo ""
        info "Lancez manuellement dans deux terminaux :"
        echo -e "  ${CYAN}Terminal 1 (backend):${NC}  cd backend && source venv/bin/activate && uvicorn app.main:app --reload"
        echo -e "  ${CYAN}Terminal 2 (frontend):${NC} cd frontend && npm run dev"
    fi
}

# ─── Exécution du mode choisi ────────────────────────────────────────────────

case $DEPLOY_MODE in
    0) deploy_docker_compose ;;
    1) deploy_local ;;
    2) deploy_hybrid ;;
esac

# ─── Résumé final ────────────────────────────────────────────────────────────

echo ""
header "Déploiement terminé"
echo -e "  ${GREEN}▸${NC} Frontend  : ${BOLD}http://localhost:3000${NC}"
echo -e "  ${GREEN}▸${NC} Backend   : ${BOLD}http://localhost:8000${NC}"
echo -e "  ${GREEN}▸${NC} Swagger   : ${BOLD}http://localhost:8000/docs${NC}"
echo ""
echo -e "  ${CYAN}Commandes utiles :${NC}"
echo -e "    docker compose logs -f       — Voir les logs"
echo -e "    docker compose ps            — État des services"
echo -e "    docker compose down          — Tout arrêter"
echo -e "    docker compose down -v       — Arrêter + supprimer les données"
echo ""
