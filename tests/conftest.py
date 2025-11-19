"""
Fixtures pytest pour les tests
"""

import sys
from pathlib import Path
from typing import Generator
from uuid import uuid4

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# Ajouter le répertoire parent au PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))


# ============================================================================
# FIXTURES DE BASE
# ============================================================================


@pytest.fixture
def test_user_id() -> str:
    """UUID d'utilisateur de test"""
    return str(uuid4())


@pytest.fixture
def test_conversation_id() -> str:
    """UUID de conversation de test"""
    return str(uuid4())


@pytest.fixture
def sample_legal_text() -> str:
    """Texte juridique de test"""
    return """
    Article 1240 du Code Civil

    Tout fait quelconque de l'homme, qui cause à autrui un dommage,
    oblige celui par la faute duquel il est arrivé à le réparer.

    Article 1241 du Code Civil

    Chacun est responsable du dommage qu'il a causé non seulement par son fait,
    mais encore par sa négligence ou par son imprudence.
    """


@pytest.fixture
def sample_query() -> str:
    """Requête de test"""
    return "Qu'est-ce que la responsabilité civile ?"


# ============================================================================
# FIXTURES POUR EMBEDDINGS
# ============================================================================


@pytest.fixture
def mock_embeddings_handler():
    """Mock du gestionnaire d'embeddings"""
    mock = AsyncMock()
    mock.embed_text = AsyncMock(return_value=[0.1] * 768)
    mock.embed_texts = AsyncMock(return_value=[[0.1] * 768, [0.2] * 768])
    mock.embed_query = AsyncMock(return_value=[0.15] * 768)
    mock.get_dimension = MagicMock(return_value=768)
    return mock


# ============================================================================
# FIXTURES POUR LLM
# ============================================================================


@pytest.fixture
def mock_llm_handler():
    """Mock du gestionnaire LLM"""
    mock = AsyncMock()
    mock.generate = AsyncMock(
        return_value="Réponse du LLM sur la responsabilité civile."
    )

    async def mock_stream():
        for chunk in ["Réponse ", "du ", "LLM"]:
            yield chunk

    mock.generate_stream = mock_stream
    mock.generate_with_context = AsyncMock(
        return_value="Réponse avec contexte."
    )
    return mock


# ============================================================================
# FIXTURES POUR VECTOR STORE
# ============================================================================


@pytest.fixture
def mock_vector_store():
    """Mock du vector store"""
    mock = AsyncMock()

    # Mock des résultats de recherche
    mock_results = [
        {
            "id": "doc1",
            "document": "Article 1240 du Code Civil...",
            "metadata": {
                "source": "Code Civil",
                "article": "Art. 1240",
            },
            "distance": 0.2,
            "relevance_score": 0.8,
        },
        {
            "id": "doc2",
            "document": "Article 1241 du Code Civil...",
            "metadata": {
                "source": "Code Civil",
                "article": "Art. 1241",
            },
            "distance": 0.3,
            "relevance_score": 0.7,
        },
    ]

    mock.query = AsyncMock(return_value=mock_results)
    mock.query_knowledge_base = AsyncMock(return_value=mock_results)
    mock.query_user_history = AsyncMock(return_value=[])
    mock.query_user_documents = AsyncMock(return_value=[])
    mock.add_documents = AsyncMock(return_value=["id1", "id2"])
    mock.add_to_knowledge_base = AsyncMock(return_value=["id1"])
    mock.add_to_user_history = AsyncMock(return_value=["id1"])
    mock.delete_user_data = MagicMock(
        return_value={"history": True, "documents": True}
    )
    mock.get_collection_stats = MagicMock(
        return_value={"name": "test", "count": 10}
    )

    return mock


# ============================================================================
# FIXTURES POUR SUPABASE
# ============================================================================


@pytest.fixture
def mock_supabase_client():
    """Mock du client Supabase"""
    mock = MagicMock()

    # Mock auth
    mock.sign_up = MagicMock(return_value={"user": {"id": str(uuid4())}})
    mock.sign_in = MagicMock(
        return_value={
            "session": {"access_token": "test_token"},
            "user": {"id": str(uuid4())},
        }
    )

    # Mock CRUD
    from datetime import datetime
    from app.database.models import (
        UserProfile,
        Conversation,
        Message,
        Document,
        UserRole,
        MessageRole,
    )

    mock_profile = UserProfile(
        id=uuid4(),
        full_name="Test User",
        law_firm="Test Firm",
        role=UserRole.USER,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    mock_conversation = Conversation(
        id=uuid4(),
        user_id=uuid4(),
        title="Test Conversation",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        is_archived=False,
    )

    mock.get_profile = MagicMock(return_value=mock_profile)
    mock.create_conversation = MagicMock(return_value=mock_conversation)
    mock.list_user_conversations = MagicMock(return_value=[])
    mock.get_conversation_messages = MagicMock(return_value=[])
    mock.delete_all_user_data = MagicMock(return_value=True)

    return mock


# ============================================================================
# FIXTURES POUR DOCUMENT PROCESSOR
# ============================================================================


@pytest.fixture
def temp_pdf_file(tmp_path):
    """Fichier PDF temporaire pour tests"""
    pdf_path = tmp_path / "test_document.pdf"
    # Créer un PDF minimal (mock)
    pdf_path.write_text("Mock PDF content")
    return pdf_path


@pytest.fixture
def temp_txt_file(tmp_path):
    """Fichier TXT temporaire pour tests"""
    txt_path = tmp_path / "test_document.txt"
    txt_path.write_text("Contenu de test en français.\nArticle 1 de la loi.")
    return txt_path


# ============================================================================
# FIXTURES POUR RAG PIPELINE
# ============================================================================


@pytest.fixture
def mock_rag_pipeline(mock_llm_handler, mock_vector_store):
    """Mock du pipeline RAG complet"""
    with patch("app.core.rag_pipeline.get_llm_handler", return_value=mock_llm_handler):
        with patch(
            "app.core.rag_pipeline.get_vector_store", return_value=mock_vector_store
        ):
            from app.core.rag_pipeline import RAGPipeline

            pipeline = RAGPipeline()
            pipeline.llm = mock_llm_handler
            pipeline.vector_store = mock_vector_store

            yield pipeline


# ============================================================================
# FIXTURES DE CONFIGURATION
# ============================================================================


@pytest.fixture
def mock_settings():
    """Mock des settings"""
    from app.config.settings import Settings

    settings = Settings(
        supabase_url="http://test.supabase.co",
        supabase_key="test_key",
        llm_model_name="test-model",
        llm_base_url="http://localhost:11434",
        secret_key="test-secret-key-for-testing-only",
    )

    return settings


# ============================================================================
# MARKERS
# ============================================================================


def pytest_configure(config):
    """Configuration des markers pytest"""
    config.addinivalue_line("markers", "unit: mark test as unit test")
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "slow: mark test as slow")
