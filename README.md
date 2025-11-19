# Coda2z - Assistant Juridique Intelligent

**Version 1.0 (MVP)** - Assistant IA pour avocats français

## 📋 Vue d'ensemble

Coda2z est un assistant juridique basé sur l'IA, conçu pour les avocats et cabinets d'avocats français. Il combine :

- ⚖️ **Base de connaissances juridique** : Codes français, jurisprudence
- 🤖 **LLM Open Source** : Qwen2.5:14b pour génération de réponses
- 🔍 **RAG (Retrieval-Augmented Generation)** : Contexte hybride
- 🔒 **Sécurité & Confidentialité** : Isolation stricte des données utilisateurs
- 📄 **Gestion de documents** : Upload et indexation de documents privés

## 🏗️ Architecture

```
┌─────────────────┐
│  Streamlit UI   │  Interface utilisateur
└────────┬────────┘
         │
┌────────▼────────┐
│  RAG Pipeline   │  Orchestration
└────────┬────────┘
         │
    ┌────┴────┬──────────┬───────────┐
    │         │          │           │
┌───▼──┐  ┌──▼───┐  ┌───▼───┐  ┌────▼────┐
│ LLM  │  │Vector│  │Supabase│  │Embeddings│
│Qwen  │  │Store │  │  DB   │  │ Snowflake│
└──────┘  └──────┘  └────────┘  └──────────┘
```

### Stack technique

- **Frontend** : Streamlit
- **LLM** : Qwen2.5:14b (via Ollama)
- **Embeddings** : Snowflake Arctic Embed 2
- **Vector Store** : ChromaDB (double store : base commune + historiques utilisateurs)
- **Base de données** : Supabase (PostgreSQL + Auth)
- **Déploiement** : Azure VM (Nvidia T4 GPU 16GB)

## 🚀 Installation

### Prérequis

- Python 3.11+
- GPU Nvidia (16GB minimum) ou accès à une API Ollama
- Compte Supabase (gratuit)

### 1. Cloner le repository

```bash
git clone https://github.com/votre-org/coda2z.git
cd coda2z
```

### 2. Créer un environnement virtuel

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows
```

### 3. Installer les dépendances

```bash
pip install -r requirements.txt
```

### 4. Configuration

#### 4.1 Variables d'environnement

Copier le fichier d'exemple :

```bash
cp .env.example .env
```

Éditer `.env` et remplir les variables :

```env
# Supabase
SUPABASE_URL="https://votre-projet.supabase.co"
SUPABASE_KEY="votre-anon-key"

# LLM (Ollama)
LLM_MODEL_NAME="qwen2.5:14b"
LLM_BASE_URL="http://localhost:11434"

# Embeddings
EMBEDDINGS_MODEL_NAME="snowflake-arctic-embed2"

# Security
SECRET_KEY="votre-cle-secrete-unique-et-longue"
```

#### 4.2 Installer Ollama et les modèles

```bash
# Installer Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Télécharger les modèles
ollama pull qwen2.5:14b
ollama pull snowflake-arctic-embed2
```

### 5. Initialisation de la base de données

#### 5.1 Créer un projet Supabase

1. Allez sur [supabase.com](https://supabase.com)
2. Créez un nouveau projet
3. Copiez l'URL et la clé API dans `.env`

#### 5.2 Exécuter le script d'initialisation

```bash
python scripts/init_db.py
```

Ce script affichera le SQL à exécuter dans Supabase Dashboard.

1. Copiez le SQL généré
2. Allez dans **Supabase Dashboard > SQL Editor**
3. Créez une nouvelle query et collez le SQL
4. Exécutez (RUN)

#### 5.3 Créer les utilisateurs de test

```bash
python scripts/create_test_users.py
```

Utilisateurs créés :
- **Admin** : `admin@coda2z.com` / `Admin123!@#`
- **User** : `user@coda2z.com` / `User123!@#`

### 6. Charger les documents juridiques

Placez vos fichiers de lois dans `data/legal_documents/french_laws/` puis :

```bash
python scripts/load_legal_docs.py
```

Formats supportés : `.pdf`, `.md`, `.txt`, `.docx`

## 🎯 Utilisation

### Lancer l'application

```bash
streamlit run app/main.py
```

L'application sera disponible sur `http://localhost:8501`

### Fonctionnalités principales

#### 1. Chat avec l'assistant

- Posez des questions juridiques
- Obtenez des réponses contextualisées avec citations de sources
- Historique de conversation sauvegardé

#### 2. Upload de documents privés

- Uploadez vos propres documents (contrats, consultations, etc.)
- Indexation automatique dans votre espace privé
- Recherche dans vos documents + base commune

#### 3. Gestion des conversations

- Créer, archiver, supprimer des conversations
- Historique complet des échanges
- Export des données (RGPD)

## 📁 Structure du projet

```
coda2z/
├── app/
│   ├── main.py                 # Point d'entrée Streamlit
│   ├── pages/                  # Pages de l'interface
│   ├── core/                   # Logique métier (LLM, RAG, Vector Store)
│   ├── database/               # Supabase client & models
│   ├── utils/                  # Utilitaires (logger, security, validators)
│   └── config/                 # Configuration & prompts
├── scripts/                    # Scripts d'initialisation
├── data/                       # Données (documents, uploads)
├── vector_stores/              # Persistance ChromaDB
├── tests/                      # Tests unitaires
├── docker/                     # Configuration Docker
└── docs/                       # Documentation
```

## 🔧 Configuration avancée

### Ajuster les paramètres RAG

Dans `.env` :

```env
RAG_TOP_K=5                      # Nombre de documents récupérés
RAG_SIMILARITY_THRESHOLD=0.7     # Seuil de pertinence
RAG_CHUNK_SIZE=1000              # Taille des chunks
RAG_CHUNK_OVERLAP=200            # Overlap entre chunks
```

### Modifier les prompts système

Éditer `app/config/prompts.py` :

```python
SYSTEM_PROMPT = """
Ton nouveau prompt système ici...
"""
```

### Changer les modèles

```env
# Utiliser un autre LLM
LLM_MODEL_NAME="mistral:7b"

# Utiliser un autre modèle d'embeddings
EMBEDDINGS_MODEL_NAME="all-MiniLM-L6-v2"
```

## 🧪 Tests

### Exécuter les tests

```bash
pytest tests/
```

### Tests spécifiques

```bash
# Tests unitaires core
pytest tests/test_vector_store.py
pytest tests/test_rag_pipeline.py

# Tests d'intégration
pytest tests/ -m integration
```

## 🔒 Sécurité et Conformité

### Mesures de sécurité implémentées

- ✅ **Row Level Security (RLS)** : Isolation stricte des données entre utilisateurs
- ✅ **Authentification JWT** : Tokens sécurisés via Supabase Auth
- ✅ **Validation des inputs** : Protection contre injections
- ✅ **Chiffrement** : HTTPS obligatoire en production
- ✅ **Logs d'audit** : Traçabilité des actions

### Conformité RGPD

- ✅ **Droit d'accès** : Export de toutes les données utilisateur
- ✅ **Droit à l'oubli** : Suppression complète des données
- ✅ **Rétention limitée** : Suppression auto après 90 jours (configurable)
- ✅ **Logs anonymisés** : Pas de contenu sensible dans les logs

### Export des données utilisateur

```python
from app.database.supabase_client import get_supabase_client

client = get_supabase_client()
# Export complet
data = client.export_user_data(user_id)
```

### Suppression des données (RGPD)

```python
# Supprimer toutes les données d'un utilisateur
client.delete_all_user_data(user_id)
```

## 📊 Monitoring et Logs

### Logs

Les logs sont stockés dans `logs/coda2z.log` avec rotation automatique.

Niveaux de log :
- `DEBUG` : Détails techniques
- `INFO` : Informations générales
- `WARNING` : Avertissements
- `ERROR` : Erreurs
- `CRITICAL` : Erreurs critiques

### Consulter les logs

```bash
tail -f logs/coda2z.log
```

### Statistiques utilisateur

```python
stats = client.get_user_statistics(user_id)
print(f"Conversations: {stats.total_conversations}")
print(f"Messages: {stats.total_messages}")
print(f"Documents: {stats.total_documents}")
```

## 🐳 Docker (optionnel)

### Build de l'image

```bash
cd docker
docker-compose up --build
```

### Configuration

Éditer `docker/docker-compose.yml` pour ajuster les ressources GPU.

## 🚧 Roadmap

### V1 (MVP) - ✅ Complété

- [x] Architecture de base
- [x] RAG Pipeline complet
- [x] Authentification Supabase
- [x] Interface Streamlit
- [x] Double vector store
- [x] Upload de documents

### V2 (À venir)

- [ ] Interface admin complète
- [ ] Export PDF/DOCX des conversations
- [ ] Gestion avancée des rôles
- [ ] Analytics d'usage
- [ ] Intégration Légifrance API
- [ ] Mode collaboratif (partage de conversations)
- [ ] Support multilingue

### V3 (Futur)

- [ ] Migration vers Modal (serverless)
- [ ] Upgrade GPU L4 (contexte 32k)
- [ ] Fine-tuning du modèle
- [ ] Plugin pour logiciels métier
- [ ] Mobile app

## 🐛 Dépannage

### Problème : Ollama ne répond pas

```bash
# Vérifier qu'Ollama tourne
curl http://localhost:11434/api/tags

# Relancer Ollama
ollama serve
```

### Problème : Erreur Supabase "Invalid API key"

Vérifiez que vous utilisez la **clé anonyme** (anon key) et non la clé service role dans `.env`.

### Problème : GPU out of memory

Réduire le batch size dans `.env` :

```env
LLM_MAX_TOKENS=1024  # Réduire de 2048 à 1024
```

### Problème : ChromaDB ne persiste pas

Vérifier que `VECTOR_STORE_PERSIST=true` dans `.env`.

## 📚 Documentation complète

- [Architecture détaillée](docs/ARCHITECTURE.md)
- [Guide d'utilisation](docs/USER_GUIDE.md)
- [API Reference](docs/API_REFERENCE.md)
- [Installation avancée](docs/INSTALLATION.md)

## 🤝 Contribution

Les contributions sont les bienvenues !

1. Fork le projet
2. Créez une branche (`git checkout -b feature/ma-fonctionnalité`)
3. Committez (`git commit -m 'Ajout de ma fonctionnalité'`)
4. Push (`git push origin feature/ma-fonctionnalité`)
5. Ouvrez une Pull Request

## 📄 Licence

Propriétaire - © 2024 Coda2z

## 📞 Support

- Email : support@coda2z.com
- Documentation : https://docs.coda2z.com
- Issues : https://github.com/votre-org/coda2z/issues

---

**Fait avec ❤️ pour les avocats français**
