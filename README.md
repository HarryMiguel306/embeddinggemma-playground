# EmbeddingGemma Playground

Prototype expérimental de recherche sémantique multimodale de produits.

## Objectif

Permettre à un utilisateur de rechercher un produit dans un catalogue soit en décrivant ce qu'il souhaite en langage naturel, soit en important directement une image. Le système comprend le sens de la requête et retourne les produits les plus pertinents, même lorsque les termes utilisés ne correspondent pas exactement aux descriptions des produits.

Le catalogue contient **500 produits synthétiques**, majoritairement africains, répartis dans **9 catégories** et issus de plusieurs pays (Bénin, Côte d'Ivoire, Sénégal, Togo, Ghana, Nigeria, Cameroun, Burkina Faso, Mali, Niger, France). 250 produits disposent d'images ; les 250 autres sont uniquement textuels.

## Architecture

- **Backend** : Django + Django REST Framework
- **Base relationnelle** : SQLite (catalogue, métadonnées des embeddings)
- **Moteur de recherche vectorielle** : Elasticsearch (champ dense_vector 256 dimensions, HNSW, similarité cosinus)
- **Modèle d'embedding actuel** : `sentence-transformers/all-MiniLM-L6-v2` (texte uniquement, CPU, float32)
- **Modèle cible** : `google/embeddinggemma-2` (multimodal texte + image, à intégrer ultérieurement)
- **Génération de données textuelles** : Gemini API ou génération locale sans API
- **Génération d'images** : Stable Diffusion (Google Colab)
- **Traitement des images** : Pillow
- **Frontend** : Next.js 16 (App Router, TypeScript, Tailwind CSS)

## Applications Django

| App | Rôle |
|-----|------|
| `catalog` | Catégories, produits, images, API de consultation et création |
| `embeddings` | Suivi des embeddings générés (statut, vecteur stocké, ID Elasticsearch, erreurs) |
| `indexing` | Coordination de l'indexation des produits dans Elasticsearch |
| `search` | Logique de recherche textuelle et par image, endpoints API |

## Prérequis

- Python 3.11+
- Node.js + pnpm (pour le frontend)
- Elasticsearch 8.x (local ou Docker)
- Une clé API Gemini (Google AI Studio) — optionnelle si génération locale

## Installation

### 1. Cloner le dépôt

```bash
git clone https://github.com/HarryMiguel306/embeddinggemma-playground.git
cd embeddinggemma-playground
```

### 2. Configurer les variables d'environnement

Copier le fichier exemple :

```bash
cp .env.example .env
```

Éditer `.env` et y ajouter votre vraie `GEMINI_API_KEY` (optionnelle si vous utilisez la génération locale) ainsi que les réglages Elasticsearch.

> **⚠️ Sécurité** : ne jamais committer le fichier `.env` contenant une vraie clé API. Seule `.env.example` doit être versionnée.

### 3. Backend Django

```bash
cd backend
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux / macOS
source .venv/bin/activate

pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

L'API est accessible sur `http://127.0.0.1:8000/`.

### 4. Frontend Next.js

```bash
cd frontend
pnpm install
pnpm dev
```

Le frontend est accessible sur `http://localhost:3000`.

### 5. Elasticsearch (via Docker)

Depuis la racine du projet :

```bash
docker-compose up -d elasticsearch
```

Elasticsearch sera disponible sur `http://localhost:9200`.

### 6. Générer le catalogue (optionnel)

Génération locale sans API Gemini :

```bash
cd backend
python manage.py generate_catalog_local --total 500
```

Ou avec l'API Gemini :

```bash
python manage.py generate_catalog --total 500 --batch-size 10
```

### 7. Générer les embeddings

Par lots pour éviter la saturation mémoire sur CPU :

```bash
python manage.py generate_all_embeddings --force --batch-size 10
```

### 8. Indexer dans Elasticsearch

```powershell
Invoke-RestMethod -Uri "http://localhost:8000/api/indexing/run/" -Method Post -ContentType "application/json"
```

Ou via curl :

```bash
curl -X POST http://localhost:8000/api/indexing/run/
```

## Endpoints API

| Méthode | URL | Description |
|---------|-----|-------------|
| GET | `/api/catalog/categories/` | Liste des catégories |
| GET | `/api/catalog/products/` | Liste des produits (filtres : `category`, `country_code`, `is_active`, `search`, `ordering`) |
| GET | `/api/catalog/products/<uuid>/` | Détail d'un produit |
| POST | `/api/catalog/products/create/` | Créer une fiche produit (JSON ou multipart avec image) — génère l'embedding et indexe automatiquement |
| POST | `/api/search/text/` | Recherche sémantique par texte (`{"query": "...", "k": 10}`) |
| POST | `/api/search/image/` | Recherche par image (multipart avec champ `image`) |
| GET | `/api/embeddings/` | Liste des embeddings et leur statut |
| POST | `/api/indexing/run/` | Indexation des produits dans Elasticsearch |

## Pays supportés

BJ = Bénin, CI = Côte d'Ivoire, SN = Sénégal, TG = Togo, GH = Ghana, NG = Nigeria, CM = Cameroun, BF = Burkina Faso, ML = Mali, NE = Niger, FR = France

## Catégories

Vêtements & mode, Chaussures & accessoires, Beauté & soins, Bijoux & artisanat, Maison & décoration, Électronique & gadgets, Alimentation & épicerie, Sport & loisirs, Livres & papeterie

## Limites actuelles (prototype)

- Le modèle d'embedding actuel (`all-MiniLM-L6-v2`) est texte uniquement. La recherche par image est acceptée par l'API mais n'utilise pas encore l'image (modèle multimodal à intégrer : EmbeddingGemma 2).
- Certaines recherches peuvent retourner des résultats approximatifs en raison de la nature synthétique des descriptions et de la troncature à 256 dimensions.

## Évaluation (à venir)

Cette phase n'est pas encore implémentée dans le prototype actuel. Elle consistera à :
- Constituer un jeu de requêtes représentatif (français standard, formulations locales, recherche par image)
- Définir les produits pertinents pour chaque requête
- Mesurer la qualité du classement avec Precision@K, Recall@K, MRR et nDCG@K

## Licence

Usage expérimental et pédagogique.