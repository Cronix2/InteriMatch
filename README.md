<p align="center"><img src="interimatch_logo.png" alt="Interimatch" width="300"></p>


# InteriMatch AI

> Application métier intelligente pour les entreprises d'intérim — matching CV / offres d'emploi avec IA

[![Licence](https://img.shields.io/badge/licence-Propri%C3%A9taire-red)](#licence)

## Présentation

**InteriMatch AI** automatise la mise en relation candidat / offre d'emploi :

1. **Upload de CV** (PDF, DOCX) — extraction du texte
2. **Analyse IA** — extraction structurée du profil (compétences, expériences, formation…)
3. **Recherche d'offres** via l'API France Travail
4. **Matching intelligent** — scoring multicritère candidat ↔ offre via LLM
5. **Génération de mail** professionnel prêt à être relu et envoyé

---

## Stack technique

| Couche              | Technologie                                                        |
| ------------------- | ------------------------------------------------------------------ |
| **Frontend**        | Next.js 15, React 19, TypeScript, Tailwind CSS                     |
| **Backend**         | Python 3.12+, FastAPI                                              |
| **IA / LLM**        | LangChain + LLM OpenAI-compatible (Groq, Mistral, OpenAI, Ollama local, ou serveur privé) |
| **Base de données** | PostgreSQL 16                                                      |
| **Cache**           | Redis 7                                                            |
| **CV Parsing**      | pdfplumber, python-docx                                            |
| **API externe**     | France Travail (Offres d'emploi v2)                                |
| **Infra**           | Docker, Docker Compose                                             |

---

## Architecture

```text
┌─────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Frontend   │──▶│  Backend (API)    │──▶│  PostgreSQL     │
│  Next.js    │     │  FastAPI         │     │                 │
└─────────────┘     ├──────────────────┤     └─────────────────┘
                    │  Services :      │
                    │  • CV Parser     │────▶ pdfplumber / docx
                    │  • AI Service    │────▶ LangChain → LLM
                    │  • France Travail│────▶ API France Travail
                    │  • Matching      │
                    │  • Email Gen.    │
                    └──────────────────┘
```

---

## Démarrage rapide

### Prérequis

- Docker & Docker Compose
- (ou) Python 3.12+ et Node.js 20+ pour le dev local

### Installation

#### 1. Cloner le dépôt

```bash
git clone <url-du-repo>
cd InteriMatch
```

#### 2. Configurer les variables d'environnement

```bash
cp .env.example .env
# Éditez .env avec vos clés :
# - DATABASE_URL, REDIS_URL (si dev local sans Docker)
# - SECRET_KEY (chaîne aléatoire — openssl rand -hex 32)
# - AI_API_KEY (si nécessaire)
# - FRANCE_TRAVAIL_CLIENT_ID et FRANCE_TRAVAIL_CLIENT_SECRET
# - CORS_ORIGINS (origines autorisées, ex: http://localhost:3000)
```

### Lancement avec Docker

```bash
docker compose up -d
```

### Lancement en dev local (sans Docker)

**Backend :**

```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux/Mac
pip install -r requirements.txt
uvicorn app.main:app --reload
```

**Frontend :**

```bash
cd frontend
npm install
npm run dev
```

### Usage

Une fois lancée, l'application est accessible sur :

- **Frontend** : <http://localhost:3000>
- **Backend API** : <http://localhost:8000>
- **Documentation Swagger** : <http://localhost:8000/docs> (accessible uniquement quand le backend tourne)

Workflow typique :

1. Créer un compte ou se connecter
2. Uploadez un ou plusieurs CV (PDF/DOCX) — l'IA extrait le profil automatiquement
3. Lancez un matching : l'IA recherche les offres France Travail compatibles
4. Sélectionnez un match et générez un mail de proposition professionnel
5. Validez, le CV anonymisé est téléchargé automatiquement et le mail s'ouvre dans votre messagerie

---

## Structure du projet

```text
InteriMatch/
├── .env.example                 # Variables d'environnement
├── docker-compose.yml           # Orchestration Docker
├── CHANGELOG.md                 # Journal des modifications
├── LICENSE                      # Licence propriétaire
│
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── main.py              # Point d'entrée FastAPI
│       ├── core/
│       │   ├── config.py        # Configuration (pydantic-settings)
│       │   ├── database.py      # Connexion async PostgreSQL
│       │   └── security.py      # JWT, auth, hashing
│       ├── models/
│       │   └── models.py        # Modèles SQLAlchemy
│       ├── schemas/
│       │   └── schemas.py       # Schémas Pydantic
│       ├── services/
│       │   ├── ai_service.py    # LangChain + LLM
│       │   ├── cv_parser.py     # Parsing PDF/DOCX
│       │   ├── france_travail.py# Client API France Travail
│       │   ├── matching.py      # Moteur de matching
│       │   └── email_generator.py
│       └── api/routes/
│           ├── auth.py          # Inscription / connexion
│           ├── two_factor.py    # 2FA (TOTP)
│           ├── candidates.py    # CRUD candidats
│           ├── cv.py            # Upload & parsing CV
│           ├── job_offers.py    # Recherche offres
│           ├── matching.py      # Calcul de matching
│           ├── emails.py        # Génération emails
│           ├── recruiter.py     # Lookup recruteur
│           ├── bulk_upload.py   # Upload groupé (ZIP)
│           ├── dashboard.py     # Statistiques & métriques
│           └── settings.py      # Paramètres utilisateur
│
└── frontend/
    ├── Dockerfile
    ├── package.json
    └── src/
        ├── app/
        │   ├── layout.tsx
        │   └── page.tsx
        ├── components/
        │   ├── AuthScreen.tsx
        │   ├── Sidebar.tsx
        │   ├── Dashboard.tsx
        │   ├── CVPipeline.tsx     # Pipeline matching complet
        │   ├── CVUpload.tsx
        │   ├── CandidateProfile.tsx
        │   ├── MatchingResults.tsx
        │   ├── EmailPreview.tsx
        │   └── Settings.tsx
        └── lib/
            └── api.ts           # Client API axios
```

---

## API Endpoints

| Méthode  | Route                                     | Description                       |
| -------- | ----------------------------------------- | --------------------------------- |
| POST     | `/api/v1/auth/register`                   | Inscription                       |
| POST     | `/api/v1/auth/login`                      | Connexion (retourne JWT)          |
| POST     | `/api/v1/auth/2fa/setup`                  | Initialiser la 2FA (TOTP)         |
| POST     | `/api/v1/auth/2fa/verify`                 | Vérifier et activer la 2FA        |
| POST     | `/api/v1/auth/2fa/disable`                | Désactiver la 2FA                 |
| POST     | `/api/v1/cv/upload`                       | Upload et analyse d'un CV         |
| GET      | `/api/v1/cv/profile/{resume_id}`          | Profil extrait d'un CV            |
| GET      | `/api/v1/cv/candidate/{id}/anonymized-cv` | Télécharger le CV anonymisé       |
| GET      | `/api/v1/candidates/`                     | Liste des candidats               |
| GET      | `/api/v1/candidates/pipeline`             | Candidats avec statut pipeline    |
| POST     | `/api/v1/job-offers/search`               | Recherche offres France Travail   |
| POST     | `/api/v1/matching/compute`                | Lance le matching candidat/offres |
| GET      | `/api/v1/matching/candidate/{id}`         | Résultats de matching             |
| GET      | `/api/v1/matching/history`                | Historique des matchings          |
| POST     | `/api/v1/emails/generate`                 | Génère un email                   |
| PUT      | `/api/v1/emails/{id}`                     | Édite / valide un email           |
| GET      | `/api/v1/recruiter/job/{id}`              | Lookup contact recruteur          |
| POST     | `/api/v1/bulk-upload/upload-zip`          | Upload groupé de CVs (ZIP)        |
| GET      | `/api/v1/dashboard/stats`                 | Statistiques du tableau de bord   |
| GET      | `/api/v1/dashboard/api-metrics`           | Métriques d'utilisation API       |
| GET      | `/api/v1/settings/me`                     | Paramètres utilisateur            |
| PUT      | `/api/v1/settings/me`                     | Mettre à jour les paramètres      |

---

## Configuration IA (LLM)

Le LLM est appelé via **LangChain** avec un client **OpenAI-compatible**. Plusieurs fournisseurs sont supportés : Groq, Mistral AI, OpenRouter, Together AI, OpenAI, Ollama (local), ou tout endpoint personnalisé.

Configuration dans `.env` :

```env
AI_PROVIDER=custom            # groq | openrouter | mistral | together | ollama | openai | custom
AI_MODEL=alfred-4.2
AI_SERVER_URL=https://trust.liveintelligence.orange-business.com
AI_API_KEY=
AI_TEMPERATURE=0.3
AI_MAX_TOKENS=2000
```

Le service IA est utilisé pour 3 tâches :

- **Extraction de CV** : extraction structurée des informations du candidat
- **Scoring de matching** : évaluation de la compatibilité candidat/offre
- **Génération de mail** : rédaction d'un mail professionnel contextuel

### Option : LLM local via Ollama (gratuit, hors ligne)

Si vous préférez ne pas dépendre d'un service en ligne, vous pouvez activer **Ollama** — il sera alors déployé dans un conteneur Docker dédié et le modèle téléchargé automatiquement.

> **⚠️** Le service Ollama n'est déployé que si vous l'activez explicitement (profil Docker `ollama`). Sans cette activation, aucun modèle n'est téléchargé et l'application utilise le LLM en ligne configuré dans `.env`.

**Activation :**

```bash
# Démarrer l'application avec Ollama
docker compose --profile ollama up -d
```

Le conteneur `ollama-init` télécharge automatiquement le modèle au premier démarrage (~5 minutes selon la connexion), puis s'arrête. Le modèle est conservé dans le volume Docker `ollama_data` pour les démarrages suivants.

**Modèle par défaut : `qwen2.5:7b`** (~4.7 Go)

Choisi pour son excellent rapport intelligence/taille : très bon en français, fiable pour la sortie JSON structurée (nécessaire à l'extraction de CV et au scoring de matching), tout en restant raisonnable en espace disque.

Vous pouvez changer le modèle via `.env` :

```env
OLLAMA_MODEL=qwen2.5:7b      # par défaut, recommandé
# OLLAMA_MODEL=qwen2.5:3b    # plus léger (~2 Go), un peu moins précis
# OLLAMA_MODEL=llama3.1:8b   # alternative (~4.9 Go)
# OLLAMA_MODEL=mistral:7b    # alternative française (~4.1 Go)
```

**Configuration côté application** : dans **Paramètres > IA**, sélectionnez le provider `Ollama (local Docker, 100% gratuit)`. L'URL et le modèle sont pré-remplis automatiquement.

**Arrêter Ollama et libérer l'espace :**

```bash
docker compose --profile ollama down
docker volume rm interimatch_ollama_data   # supprime aussi le modèle téléchargé
```

---

## Licence

**Ce projet est sous licence propriétaire.**

Copyright (c) 2025-2026 Clément Linossier. Tous droits réservés.

Toute utilisation, copie, modification ou distribution de ce code source est
**strictement interdite** sans autorisation écrite préalable de l'auteur.

Voir le fichier [LICENSE](LICENSE) pour les conditions complètes.

---

## Auteur

**Clément Linossier** — [clement.linossier@efrei.net](mailto:clement.linossier@efrei.net)

GitHub : [Cronix2](https://github.com/Cronix2)
