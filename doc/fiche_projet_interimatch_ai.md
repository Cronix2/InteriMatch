# Fiche projet — **InteriMatch AI**
## Application métier intelligente pour les entreprises d’intérim

---

## 1. Résumé du projet

**InteriMatch AI** est une application métier destinée aux **entreprises d’intérim**.  
Son objectif est d’**automatiser et accélérer la mise en relation entre un candidat et une offre d’emploi**, à partir de :

- l’**import d’un CV** candidat,
- la **récupération d’offres d’emploi** via l’API de **France Travail**,
- l’**extraction automatique des informations clés** du CV,
- l’**analyse de compatibilité** entre le profil candidat et les offres disponibles,
- la **sélection du poste le plus adapté**,
- la **rédaction automatique d’un mail professionnel** à destination de l’entreprise proposant le poste.

Le projet combine ainsi **traitement documentaire**, **IA/NLP**, **moteur de matching**, **intégration API métier** et **génération assistée de contenu**.

---

## 2. Nom du projet

### Nom retenu : **InteriMatch AI**

### Pourquoi ce nom ?
- **Interi** : rappelle le secteur de l’**intérim**.
- **Match** : met en avant la **mise en correspondance candidat / offre**.
- **AI** : souligne l’usage de l’**intelligence artificielle**.

### Noms alternatifs possibles
- **TalentBridge AI**
- **CV2Mission**
- **Interim Copilot**
- **Mission Finder AI**

---

## 3. Contexte et besoin métier

Les agences d’intérim traitent un grand volume de CV et doivent répondre rapidement aux besoins de recrutement de leurs clients.  
Cette activité implique souvent :

- une lecture manuelle de CV,
- une recherche d’offres adaptées,
- une comparaison profil / poste chronophage,
- une rédaction répétitive de mails de candidature ou de proposition.

Le projet vise à réduire cette charge manuelle en proposant une solution capable de :

1. **lire un CV automatiquement**,
2. **structurer les informations utiles**,
3. **consulter les offres d’emploi disponibles**,
4. **calculer le meilleur matching**,
5. **aider les équipes à agir vite** avec un mail déjà prêt.

---

## 4. Objectifs clairs du projet

## 4.1 Objectif principal
Développer une application métier capable d’**identifier automatiquement le poste le plus pertinent pour un candidat** à partir de son CV et des offres issues de l’API France Travail, puis de **générer un mail professionnel prêt à être relu et envoyé**.

## 4.2 Objectifs fonctionnels
- Permettre l’**upload de CV** (PDF, DOCX, éventuellement image scannée).
- Extraire les informations clés du candidat :
  - identité,
  - coordonnées,
  - expériences,
  - compétences,
  - diplômes,
  - langues,
  - mobilité,
  - certifications,
  - disponibilité.
- Interroger l’**API France Travail** pour récupérer les offres pertinentes.
- Calculer un **score de correspondance** entre le CV et les offres.
- Proposer :
  - le **meilleur poste**,
  - un **top 3** ou **top 5** des postes les plus adaptés.
- Générer un **mail professionnel contextualisé** :
  - à destination de l’entreprise,
  - basé sur le poste retenu,
  - prenant en compte le profil du candidat.
- Fournir une **interface claire** pour les recruteurs / chargés de mission.
- Permettre la **validation humaine** avant envoi.

## 4.3 Objectifs techniques
- Construire une architecture web moderne, modulaire et scalable.
- Intégrer un pipeline IA fiable pour l’extraction et le matching.
- Garantir la traçabilité des traitements.
- Sécuriser les données personnelles (CV, coordonnées, parcours pro).
- Prévoir une base propre pour des évolutions futures.

## 4.4 Objectifs business
- Réduire le temps de traitement d’un CV.
- Améliorer la réactivité des agences d’intérim.
- Uniformiser la qualité des mails envoyés.
- Augmenter le taux de positionnement pertinent candidat / mission.
- Améliorer la productivité des recruteurs.

---

## 5. Périmètre du projet

## 5.1 Dans le périmètre
- Upload et stockage temporaire des CV
- Parsing de CV
- Extraction d’informations via IA / NLP
- Intégration API France Travail
- Récupération, filtrage et normalisation des offres
- Algorithme de matching
- Génération de mail
- Interface utilisateur métier
- Historique des traitements
- Tableau de bord simple
- Authentification des utilisateurs internes

## 5.2 Hors périmètre initial
- Envoi automatique du mail sans validation humaine
- Signature électronique
- ATS complet
- Gestion complète RH / paie / contrats
- Matching multi-plateformes (LinkedIn, Apec, Indeed, etc.)
- Application mobile native
- OCR avancé sur scans très dégradés en V1
- Analyse vidéo / entretien automatisé

---

## 6. Utilisateurs cibles

- **Chargé de recrutement**
- **Consultant en intérim**
- **Responsable d’agence**
- **Administrateur métier**
- **Support technique / administrateur système**

---

## 7. Fonctionnalités principales

## 7.1 Gestion des CV
- Import de CV en PDF / DOCX
- Prévisualisation
- Détection du type de document
- Extraction texte
- Historisation du traitement

## 7.2 Extraction intelligente des données
- Parsing du CV
- Détection des compétences
- Détection des postes occupés
- Détection des années d’expérience
- Détection des diplômes / certifications
- Détection des coordonnées et de la localisation
- Structuration du profil candidat

## 7.3 Intégration offres d’emploi
- Connexion à l’API France Travail
- Recherche d’offres par mots-clés / zone / métier
- Normalisation des données reçues
- Suppression des doublons éventuels
- Mise en cache des résultats pour éviter les appels inutiles

## 7.4 Matching candidat / offre
- Calcul d’un score global
- Pondération sur :
  - compétences,
  - expérience,
  - localisation,
  - disponibilité,
  - niveau d’étude,
  - mobilité,
  - cohérence métier.
- Restitution des meilleures offres
- Affichage des raisons du matching

## 7.5 Génération de mail
- Rédaction d’un mail professionnel
- Personnalisation selon :
  - poste,
  - entreprise,
  - candidat,
  - compétences clés,
  - disponibilité.
- Possibilité d’édition manuelle avant validation
- Historique des mails générés

## 7.6 Interface métier
- Tableau de bord
- Vue candidat
- Vue offres recommandées
- Vue détail du scoring
- Vue génération / édition du mail
- Historique des actions

## 7.7 Administration
- Gestion des comptes
- Gestion des rôles
- Gestion des paramètres de scoring
- Journalisation
- Supervision des erreurs API

---

## 8. Stack technique recommandée

## 8.1 Front-end
### Recommandation
- **React**
- **Next.js**
- **TypeScript**
- **Tailwind CSS**
- **Shadcn/ui** ou **MUI**

### Pourquoi
- Excellente expérience utilisateur
- Composants modernes
- Bonne maintenabilité
- Typage fort avec TypeScript
- Facile pour construire une interface métier propre et rapide

## 8.2 Back-end
### Recommandation
- **Python**
- **FastAPI**

### Pourquoi
- Très bon choix pour l’IA, le NLP et les APIs
- Rapide à développer
- Documentation Swagger native
- Bonne performance pour les services métier

## 8.3 Moteur IA / NLP
### Recommandation
- **spaCy** pour le NLP structuré
- **transformers / sentence-transformers** pour les embeddings et similarités
- **LLM** pour la rédaction de mail et l’interprétation avancée
- **OCR optionnel** : Tesseract ou service spécialisé si besoin

### Usages possibles
- extraction d’entités,
- classification métier,
- rapprochement sémantique entre CV et offre,
- génération assistée de mails.

## 8.4 Base de données
### Recommandation principale
- **PostgreSQL**

### Pourquoi
- robuste,
- relationnelle,
- adaptée aux données métier,
- excellente compatibilité avec les applications web modernes.

### Complément possible
- **Redis**
  - cache API,
  - gestion de sessions,
  - files de tâches simples.

## 8.5 Stockage de fichiers
- **S3 compatible** (MinIO en dev / stockage objet cloud en prod)
- ou stockage local en environnement de test

## 8.6 Authentification / sécurité
- **JWT**
- **OAuth2**
- **RBAC** (gestion des rôles)
- chiffrement TLS
- hash des mots de passe avec **Argon2** ou **bcrypt**

## 8.7 Tâches asynchrones
- **Celery** + **Redis**
ou
- **RQ** si on veut plus simple

### Cas d’usage
- parsing de CV,
- appels API massifs,
- génération différée,
- logs et traitements longs.

## 8.8 API externes
- **API France Travail**
- éventuellement un **service LLM**
- éventuellement un service d’emailing / SMTP interne plus tard

## 8.9 DevOps / Infra
- **Docker**
- **Docker Compose**
- **GitHub** ou **GitLab**
- **CI/CD**
- **Nginx** comme reverse proxy
- hébergement :
  - cloud public,
  - VM privée,
  - ou infrastructure interne.

## 8.10 Observabilité
- **Prometheus**
- **Grafana**
- **Sentry**
- logs centralisés

---

## 9. Architecture applicative cible

## 9.1 Vue logique
1. L’utilisateur importe un CV
2. Le back-end extrait le texte
3. Le module IA structure le profil
4. Le service offres interroge l’API France Travail
5. Le moteur de matching calcule les scores
6. L’application retourne les meilleures offres
7. Le module de génération rédige le mail
8. L’utilisateur relit, corrige et valide

## 9.2 Découpage en modules
- **Front web**
- **API back-end**
- **Service parsing CV**
- **Service matching**
- **Service génération de mail**
- **Service intégration France Travail**
- **Base PostgreSQL**
- **Stockage fichiers**
- **Cache / file de tâches**

---

## 10. Modèle de données simplifié

### Entités principales
- **User**
- **Candidate**
- **Resume**
- **ExtractedProfile**
- **JobOffer**
- **MatchingResult**
- **GeneratedEmail**
- **AuditLog**

### Exemples de champs importants
#### Candidate
- id
- nom
- prénom
- email
- téléphone
- localisation
- disponibilité

#### Resume
- id
- candidate_id
- fichier_source
- type_fichier
- texte_brut
- date_import

#### ExtractedProfile
- compétences
- expériences
- diplômes
- certifications
- langues
- mobilité
- résumé_profil

#### JobOffer
- api_source_id
- intitulé
- entreprise
- localisation
- description
- compétences_requises
- type_contrat
- date_publication

#### MatchingResult
- candidate_id
- job_offer_id
- score_global
- score_compétences
- score_expérience
- score_localisation
- explication

#### GeneratedEmail
- candidate_id
- job_offer_id
- objet
- corps
- statut_validation
- date_génération

---

## 11. Stratégie IA recommandée

## 11.1 Extraction de CV
Approche hybride :
- **règles** pour les données simples (email, téléphone, dates),
- **NLP** pour les compétences, postes, formations,
- **LLM** pour enrichir ou corriger la structuration si nécessaire.

## 11.2 Matching
Approche en 2 couches :
1. **Règles métier pondérées**
2. **Similarité sémantique** via embeddings

### Exemple de pondération
- compétences : 35 %
- expérience : 25 %
- métier / intitulé : 20 %
- localisation / mobilité : 10 %
- diplômes / certifications : 10 %

## 11.3 Génération de mail
Le mail doit :
- rester professionnel,
- être factuel,
- éviter les hallucinations,
- être relu par un humain avant envoi,
- s’appuyer uniquement sur les données validées.

---

## 12. Exigences non fonctionnelles

- **Performance** : réponse rapide sur les cas standards
- **Sécurité** : protection des données personnelles
- **Traçabilité** : journalisation des traitements
- **Scalabilité** : support de plusieurs utilisateurs/agences
- **Maintenabilité** : code modulaire et documenté
- **Disponibilité** : application stable en heures ouvrées
- **Conformité** : respect RGPD et minimisation des données

---

## 13. Sécurité, conformité et données personnelles

Le projet manipule des **données personnelles sensibles d’un point de vue RH**.  
Il faudra prévoir :

- minimisation des données stockées,
- durée de conservation limitée,
- gestion du consentement si nécessaire,
- suppression des CV non nécessaires,
- journalisation des accès,
- contrôle d’accès strict,
- chiffrement en transit,
- sauvegardes sécurisées,
- clauses de confidentialité,
- revue juridique / RGPD avant production.

---

## 14. Calendrier prévisionnel

> Hypothèse : projet mené sur **16 semaines** pour une V1.

| Phase | Période | Durée estimée | Objectif |
|---|---:|---:|---|
| Cadrage & recueil des besoins | S1 à S2 | 2 semaines | Définir le besoin métier, le périmètre et les priorités |
| Conception fonctionnelle & technique | S3 à S4 | 2 semaines | Rédiger l’architecture, les parcours utilisateurs et les spécifications |
| Mise en place de l’environnement projet | S4 | 1 semaine | Dépôts Git, CI/CD, Docker, base initiale |
| Développement parsing CV | S5 à S6 | 2 semaines | Import, extraction texte, structuration initiale |
| Intégration API France Travail | S6 à S7 | 2 semaines | Connexion API, récupération et normalisation des offres |
| Développement moteur de matching | S8 à S9 | 2 semaines | Calcul des scores et classement des offres |
| Développement génération de mail | S10 | 1 semaine | Création du module de rédaction assistée |
| Développement interface front-end | S8 à S11 | 4 semaines | Tableau de bord, vues métier, restitution des résultats |
| Tests fonctionnels et techniques | S12 à S13 | 2 semaines | Corriger bugs, valider les scénarios clés |
| Sécurisation & conformité | S13 | 1 semaine | Revue sécurité, gestion des accès, conformité RGPD |
| Recette utilisateur | S14 | 1 semaine | Validation par les utilisateurs métier |
| Corrections finales | S15 | 1 semaine | Ajustements finaux avant livraison |
| Déploiement V1 & documentation | S16 | 1 semaine | Mise en production pilote et livrables projet |

---

## 15. Étapes clés / Milestones

| Milestone | Description | Critère d’atteinte |
|---|---|---|
| M1 - Cadrage validé | Le besoin, le périmètre et les objectifs sont validés | Document de cadrage approuvé |
| M2 - Architecture validée | La stack et l’architecture sont validées | Schéma technique et choix technos approuvés |
| M3 - Parsing CV opérationnel | Le système extrait correctement les données de base d’un CV | Démonstration sur plusieurs CV test |
| M4 - API France Travail intégrée | Les offres peuvent être récupérées et affichées | Appels API stables et données normalisées |
| M5 - Matching fonctionnel | Le moteur classe les offres par pertinence | Score affiché et top offres cohérent |
| M6 - Génération de mail disponible | Un mail exploitable est produit automatiquement | Mail généré, éditable, conforme au besoin |
| M7 - V1 testée | Les scénarios principaux sont validés | Recette fonctionnelle réussie |
| M8 - Déploiement pilote | La V1 est disponible pour un usage encadré | Environnement déployé et accessible |

---

## 16. Équipes et rôles nécessaires

| Rôle | Responsabilités principales | Charge estimée |
|---|---|---|
| Chef de projet / Product Owner | Pilotage, priorisation, suivi planning, validation métier | Forte |
| Expert métier intérim / recrutement | Définition des besoins, validation fonctionnelle, règles métier | Forte |
| Développeur front-end | Interface utilisateur, UX, intégration API front | Moyenne à forte |
| Développeur back-end | API, logique métier, intégration services | Forte |
| Ingénieur IA / NLP | Extraction CV, matching sémantique, génération assistée | Forte |
| Data engineer / DBA | Modèle de données, performance BDD, qualité des données | Moyenne |
| DevOps / Cloud engineer | CI/CD, conteneurisation, déploiement, supervision | Moyenne |
| QA / testeur | Scénarios de test, recette, non-régression | Moyenne |
| RSSI / référent sécurité | Revue sécurité, droits d’accès, conformité technique | Faible à moyenne |
| Référent juridique / RGPD | Encadrement des données personnelles | Faible à moyenne |

### Équipe minimale réaliste
Pour une V1, une équipe resserrée pourrait être :
- 1 chef de projet / PO
- 1 développeur full-stack
- 1 ingénieur IA / NLP
- 1 expert métier
- 1 QA partagé
- 1 DevOps partagé

---

## 17. Risques et mitigations

| Risque | Impact | Probabilité | Mitigation |
|---|---|---|---|
| CV très hétérogènes ou mal structurés | Élevé | Élevée | Prévoir parsing hybride, jeux de tests variés, fallback manuel |
| Offres API France Travail incomplètes ou changeantes | Élevé | Moyenne | Mettre une couche d’adaptation, versionner le connecteur, monitorer les erreurs |
| Mauvais matching entre CV et offres | Élevé | Moyenne | Combiner règles métier + similarité sémantique + validation utilisateur |
| Hallucination ou imprécision dans les mails générés | Élevé | Moyenne | Génération basée uniquement sur données extraites + validation humaine obligatoire |
| Données personnelles mal protégées | Très élevé | Moyenne | RBAC, chiffrement, logs, minimisation, revue sécurité et RGPD |
| Dépendance trop forte à un fournisseur IA externe | Moyen | Moyenne | Prévoir abstraction provider et option locale / remplaçable |
| Délais de projet sous-estimés | Élevé | Élevée | Prioriser une V1 simple, découper en lots, arbitrer tôt |
| Faible adoption par les utilisateurs métier | Élevé | Moyenne | Impliquer les utilisateurs dès le cadrage et pendant la recette |
| Coût API / IA plus élevé que prévu | Moyen | Moyenne | Suivi des coûts, cache, limitation des appels, choix de modèles adaptés |
| Performance insuffisante sur gros volumes | Moyen | Faible à moyenne | Tâches asynchrones, cache, indexation BDD, monitoring |
| Non-conformité RGPD | Très élevé | Faible à moyenne | Analyse juridique, politique de conservation, droit à suppression |
| Mauvaise qualité OCR sur scans | Moyen | Moyenne | Limiter le support OCR en V1 ou imposer une qualité minimale de document |

---

## 18. Critères de succès

Le projet sera considéré comme réussi si les critères suivants sont atteints :

| Critère de succès | Indicateur attendu |
|---|---|
| Upload de CV fonctionnel | 100 % des CV de test valides importés |
| Extraction d’informations correcte | Taux de précision satisfaisant sur les champs clés |
| Connexion API France Travail stable | Offres récupérées sans erreur bloquante sur les scénarios de test |
| Matching pertinent | Le top 3 proposé est jugé cohérent par les utilisateurs métier dans la majorité des cas |
| Génération de mail exploitable | Le mail nécessite peu de retouches dans un grand nombre de cas |
| Interface utilisable | Les recruteurs peuvent traiter un dossier de bout en bout sans blocage |
| Sécurité minimale atteinte | Authentification, rôles, journalisation et protection des accès en place |
| Recette validée | Les scénarios critiques sont validés par les parties prenantes |
| Déploiement pilote réalisé | Application accessible dans un environnement de test ou pilote |

---

## 19. KPIs de suivi recommandés

- Temps moyen de traitement d’un CV
- Taux de parsing réussi
- Taux de complétude des profils extraits
- Taux de disponibilité de l’API France Travail
- Nombre moyen d’offres pertinentes retournées
- Taux de validation du top 1 proposé
- Taux de modification manuelle des mails générés
- Temps gagné par dossier
- Taux d’usage par les recruteurs
- Nombre d’erreurs applicatives par semaine

---

## 20. Proposition de découpage MVP / V1 / V2

## MVP
- Upload CV
- Extraction de base
- Appel API France Travail
- Scoring simple
- Top 3 offres
- Génération de mail simple
- Interface minimale

## V1
- Scoring enrichi
- Historique
- Authentification / rôles
- Journalisation
- Tableau de bord
- Validation métier plus poussée

## V2
- Boucle d’amélioration via retours utilisateurs
- Personnalisation fine par agence
- Intégration emailing
- Matching multi-sources
- Suggestions d’amélioration du CV
- Statistiques avancées

---

## 21. Recommandation finale

Pour limiter les risques, il est recommandé de démarrer avec une **V1 pragmatique** :

1. **extraire les informations clés du CV**,
2. **récupérer des offres France Travail**,
3. **calculer un matching explicable**,
4. **générer un mail relisible par un humain**,
5. **faire valider chaque étape par les utilisateurs métier**.

La vraie valeur du projet ne repose pas seulement sur l’IA, mais sur la combinaison de :
- **règles métier solides**,
- **données bien structurées**,
- **interface simple**,
- **validation humaine**,
- **intégration fluide dans le quotidien des agences d’intérim**.

---

## 22. Conclusion

**InteriMatch AI** est un projet à forte valeur métier pour le secteur de l’intérim.  
Il répond à un besoin concret : **traiter plus vite les candidatures, améliorer la pertinence des propositions et gagner du temps sur les tâches répétitives**.

Avec une architecture moderne, un cadrage clair et une V1 bien priorisée, ce projet peut devenir un véritable **assistant métier intelligent pour les recruteurs en intérim**.
