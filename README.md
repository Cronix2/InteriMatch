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
| **IA / LLM**        | LangChain + API OpenAI-compatible (alfred-4.2 via Orange Business) |
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

### 1. Configuration

```bash
cp .env.example .env
# Éditez .env avec vos clés :
# - AI_API_KEY (si nécessaire)
# - FRANCE_TRAVAIL_CLIENT_ID et SECRET
# - SECRET_KEY (pour JWT)
```

### 2. Lancement avec Docker

```bash
docker compose up -d
```

- **Frontend** : [http://localhost:3000](http://localhost:3000)
- **Backend API** : [http://localhost:8000](http://localhost:8000)
- **Swagger docs** : [http://localhost:8000/docs](http://localhost:8000/docs)

### 3. Lancement en dev local (sans Docker)

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

---

## Structure du projet

```text
InteriMatch/
├── .env.example                 # Variables d'environnement
├── docker-compose.yml           # Orchestration Docker
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
│           ├── candidates.py    # CRUD candidats
│           ├── cv.py            # Upload & parsing CV
│           ├── job_offers.py    # Recherche offres
│           ├── matching.py      # Calcul de matching
│           └── emails.py        # Génération emails
│
└── frontend/
    ├── Dockerfile
    ├── package.json
    └── src/
        ├── app/
        │   ├── layout.tsx
        │   └── page.tsx         # Workflow en 4 étapes
        ├── components/
        │   ├── CVUpload.tsx
        │   ├── CandidateProfile.tsx
        │   ├── MatchingResults.tsx
        │   └── EmailPreview.tsx
        └── lib/
            └── api.ts           # Client API axios
```

---

## API Endpoints

| Méthode  | Route                             | Description                       |
| -------- | --------------------------------- | --------------------------------- |
| POST     | `/api/v1/auth/register`           | Inscription                       |
| POST     | `/api/v1/auth/login`              | Connexion (retourne JWT)          |
| POST     | `/api/v1/cv/upload`               | Upload et analyse d'un CV         |
| GET      | `/api/v1/cv/profile/{resume_id}`  | Profil extrait d'un CV            |
| GET      | `/api/v1/candidates/`             | Liste des candidats               |
| POST     | `/api/v1/job-offers/search`       | Recherche offres France Travail   |
| POST     | `/api/v1/matching/compute`        | Lance le matching candidat/offres |
| GET      | `/api/v1/matching/candidate/{id}` | Résultats de matching             |
| POST     | `/api/v1/emails/generate`         | Génère un email                   |
| PUT      | `/api/v1/emails/{id}`             | Édite / valide un email           |

---

## Configuration IA (LLM)

Le LLM est appelé via **LangChain** avec un client **OpenAI-compatible**. Configuration dans `.env` :

```env
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
