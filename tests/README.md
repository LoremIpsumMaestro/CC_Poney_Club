# Tests Unitaires Coda2z

Ce répertoire contient tous les tests unitaires pour le backend core de Coda2z.

## 📁 Structure

```
tests/
├── conftest.py                      # Fixtures pytest partagées
├── test_validators.py               # Tests des validateurs
├── test_document_processor.py       # Tests du traitement de documents
├── test_vector_store.py             # Tests du vector store
├── test_rag_pipeline.py             # Tests du pipeline RAG
├── test_llm_handler.py              # Tests du gestionnaire LLM
└── test_embeddings_handler.py       # Tests des embeddings
```

## 🚀 Exécution des tests

### Tous les tests

```bash
pytest
```

### Tests d'un fichier spécifique

```bash
pytest tests/test_validators.py
```

### Tests d'une classe spécifique

```bash
pytest tests/test_rag_pipeline.py::TestRAGPipeline
```

### Test d'une fonction spécifique

```bash
pytest tests/test_rag_pipeline.py::TestRAGPipeline::test_process_query_success
```

### Tests avec verbose

```bash
pytest -v
```

### Tests avec couverture de code

```bash
pytest --cov=app --cov-report=html
```

Puis ouvrir `htmlcov/index.html` dans un navigateur.

## 🏷️ Markers

Les tests utilisent des markers pour classification :

### Exécuter uniquement les tests unitaires

```bash
pytest -m unit
```

### Exécuter les tests d'intégration

```bash
pytest -m integration
```

### Exclure les tests lents

```bash
pytest -m "not slow"
```

## 📊 Couverture de code

### Générer un rapport de couverture complet

```bash
pytest --cov=app --cov-report=term-missing --cov-report=html
```

### Couverture cible

| Module | Couverture cible |
|--------|------------------|
| `app/core/` | > 90% |
| `app/utils/` | > 85% |
| `app/database/` | > 80% |
| `app/config/` | > 70% |

## 🐛 Debugging

### Exécuter avec pdb (debugger)

```bash
pytest --pdb
```

S'arrête au premier échec.

### Exécuter avec pdb immédiatement

```bash
pytest --pdb --maxfail=1
```

### Voir les print statements

```bash
pytest -s
```

### Voir les logs détaillés

```bash
pytest --log-cli-level=DEBUG
```

## ⚡ Exécution rapide

### Fail fast (arrêter au premier échec)

```bash
pytest -x
```

### Exécuter seulement les tests qui ont échoué la dernière fois

```bash
pytest --lf
```

### Exécuter les tests modifiés en premier

```bash
pytest --ff
```

### Exécution parallèle (avec pytest-xdist)

```bash
pytest -n auto
```

## 📝 Conventions

### Nommage

- Fichiers : `test_*.py`
- Classes : `Test*`
- Fonctions : `test_*`

### Structure d'un test

```python
@pytest.mark.unit
class TestMyComponent:
    """Tests pour MyComponent"""

    @pytest.fixture
    def my_component(self):
        """Instance du composant"""
        return MyComponent()

    def test_something(self, my_component):
        """Test de quelque chose"""
        # Arrange
        input_data = "test"

        # Act
        result = my_component.do_something(input_data)

        # Assert
        assert result == expected_value
```

### Tests asynchrones

```python
@pytest.mark.asyncio
async def test_async_function():
    """Test d'une fonction async"""
    result = await async_function()
    assert result is not None
```

## 🔍 Fixtures disponibles

Voir `conftest.py` pour toutes les fixtures partagées :

- `test_user_id` : UUID d'utilisateur de test
- `test_conversation_id` : UUID de conversation
- `sample_legal_text` : Texte juridique de test
- `sample_query` : Requête de test
- `mock_embeddings_handler` : Mock du gestionnaire d'embeddings
- `mock_llm_handler` : Mock du LLM
- `mock_vector_store` : Mock du vector store
- `mock_supabase_client` : Mock de Supabase
- `temp_pdf_file` : Fichier PDF temporaire
- `temp_txt_file` : Fichier TXT temporaire

## 📊 Statistiques des tests

### Nombre de tests par module

```bash
pytest --collect-only | grep "test_" | wc -l
```

### Temps d'exécution

```bash
pytest --durations=10
```

Affiche les 10 tests les plus lents.

## 🚨 CI/CD

### Commande pour CI

```bash
pytest --cov=app --cov-report=xml --cov-fail-under=80
```

Échoue si la couverture est < 80%.

## 🛠️ Dépannage

### Problème : Tests qui échouent à cause de dépendances manquantes

```bash
pip install -r requirements.txt
```

### Problème : Erreur d'import des modules

Vérifier que le PYTHONPATH inclut le répertoire racine :

```bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
pytest
```

### Problème : Tests asynchrones qui échouent

Vérifier que `pytest-asyncio` est installé :

```bash
pip install pytest-asyncio
```

## 📚 Ressources

- [Documentation pytest](https://docs.pytest.org/)
- [pytest-asyncio](https://github.com/pytest-dev/pytest-asyncio)
- [pytest-cov](https://pytest-cov.readthedocs.io/)
- [Best practices](https://docs.pytest.org/en/latest/goodpractices.html)

## ✅ Checklist avant commit

- [ ] Tous les tests passent : `pytest`
- [ ] Couverture > 80% : `pytest --cov=app`
- [ ] Pas de warnings : `pytest --strict-warnings`
- [ ] Code formaté : `black tests/`
- [ ] Linting OK : `ruff tests/`
