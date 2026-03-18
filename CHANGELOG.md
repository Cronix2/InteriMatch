# Changelog

Toutes les modifications notables de ce projet sont documentées ici.

## [1.4.0] - 2025-01-XX

### Ajouté

- Recherche améliorée de l'email du recruteur (parsing coordonnées et URL de postulation)
- Pré-remplissage de l'email du recruteur comme destinataire du mail
- Téléchargement automatique du CV anonymisé lors de la validation du mail
- Indicateur visuel du destinataire dans l'aperçu du mail
- Notice de rappel pour joindre le CV au mail
- Variable `CORS_ORIGINS` configurable depuis .env

### Corrigé

- Secrets et URLs de connexion retirés des valeurs par défaut de la configuration
- Liens de documentation corrigés dans le README
- README complété avec sections Installation et Usage

### Sécurité

- Suppression des valeurs par défaut hardcodées pour `database_url`, `redis_url`, `secret_key`
- Origines CORS configurables via variable d'environnement

## [1.3.0] - 2025-01-XX

### Ajouté - 1

- Système 2FA complet (TOTP) avec QR code
- Pipeline CV complet (CVPipeline) remplaçant MatchFlow
- Upload groupé de CVs via ZIP avec pause/reprise/annulation
- CV anonymisé téléchargeable en PDF
- Métriques d'utilisation API sur le dashboard
- Recherche de recruteur depuis les données France Travail
- Suivi des propositions envoyées
- Modèle d'email personnalisable

### Corrigé - 1  

- Extraction des mots-clés (un seul mot du domaine professionnel)
- Pré-remplissage de la localisation avec le code postal
- Erreur 500 sur la génération de CV anonymisé

## [1.2.0] - 2025-01-XX

### Ajouté - 2

- Dashboard avec statistiques et graphiques
- Paramètres utilisateur (agence, thème, IA)
- Système d'authentification JWT
- Sidebar navigation

## [1.1.0] - 2025-01-XX

### Ajouté - 3

- Matching candidat/offres via IA (scoring multicritère)
- Génération de mail professionnel via LLM
- Recherche offres France Travail (API v2)

## [1.0.0] - 2025-01-XX

### Ajouté - 4

- Upload et parsing de CV (PDF, DOCX)
- Extraction structurée du profil via LLM
- Architecture backend FastAPI + PostgreSQL
- Frontend Next.js / React / Tailwind
- Docker Compose pour le déploiement
