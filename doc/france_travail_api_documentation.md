
# Documentation – API Offres d'emploi (France Travail)

## Introduction

L’API **Offres d'emploi** permet d’accéder aux offres d’emploi publiées par France Travail et ses partenaires.
Elle peut être utilisée pour intégrer des offres dans un site web, une application mobile ou un service interne.

Les réponses sont retournées au format **JSON** et l’API fonctionne selon une architecture **REST**.

---

# Authentification

L’accès à l’API nécessite généralement :

- un compte développeur sur la plateforme France Travail
- une clé API
- un token OAuth2

Exemple d’en-tête :

```
Authorization: Bearer <access_token>
```

---

# Recherche d'offres

## Endpoint

```
GET /offres/search
```

## Paramètres

| Paramètre | Description |
|----------|-------------|
| motsCles | mot-clé recherché |
| commune | ville |
| departement | département |
| region | région |
| typeContrat | type de contrat (CDI, CDD, etc.) |
| experience | niveau d'expérience |
| distance | distance autour d’une localisation |
| page | pagination |

## Exemple de requête

```
GET /offres/search?motsCles=developpeur&commune=Paris
```

## Exemple de réponse

```json
{
  "resultats": [
    {
      "id": "123456",
      "intitule": "Développeur Python",
      "entreprise": "TechCorp",
      "lieuTravail": {
        "ville": "Paris",
        "codePostal": "75000"
      },
      "typeContrat": "CDI"
    }
  ],
  "pagination": {
    "page": 1,
    "totalPages": 25
  }
}
```

---

# Détail d'une offre

## Endpoint

```
GET /offres/{id}
```

## Exemple

```
GET /offres/123456
```

## Exemple de réponse

```json
{
  "id": "123456",
  "intitule": "Développeur Python",
  "description": "Développement d'applications backend.",
  "entreprise": {
    "nom": "TechCorp"
  },
  "lieuTravail": {
    "ville": "Paris",
    "codePostal": "75000"
  },
  "typeContrat": "CDI",
  "datePublication": "2026-01-10"
}
```

---

# Référentiels

L’API propose plusieurs référentiels utiles pour filtrer les résultats.

## Endpoint

```
GET /referentiels/{type}
```

## Référentiels disponibles

| Référentiel | Description |
|-------------|-------------|
| metiers | métiers (ROME) |
| contrats | types de contrats |
| secteurs | secteurs d’activité |
| lieux | informations géographiques |

---

# Pagination

Les résultats sont paginés.

Exemple :

```
GET /offres/search?page=2
```

Structure :

```json
{
  "page": 2,
  "nombreResultats": 150,
  "totalPages": 10
}
```

---

# Codes d'erreur

| Code | Signification |
|-----|---------------|
| 400 | Requête invalide |
| 401 | Authentification requise |
| 404 | Ressource introuvable |
| 500 | Erreur serveur |

---

# Bonnes pratiques

- Mettre en cache les résultats pour limiter les appels API.
- Implémenter une gestion d’erreur robuste.
- Respecter les limites de requêtes de l’API.

---

# Ressources

Plateforme développeur :  
https://francetravail.io
