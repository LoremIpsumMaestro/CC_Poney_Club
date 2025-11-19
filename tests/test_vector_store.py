"""
Tests pour le vector store manager
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.core.vector_store import VectorStoreManager


@pytest.mark.unit
class TestVectorStoreManager:
    """Tests du gestionnaire de vector store"""

    @pytest.fixture
    def mock_chroma_client(self):
        """Mock du client ChromaDB"""
        mock = MagicMock()
        mock_collection = MagicMock()
        mock_collection.count = MagicMock(return_value=10)
        mock_collection.metadata = {}
        mock.get_or_create_collection = MagicMock(return_value=mock_collection)
        mock.list_collections = MagicMock(return_value=[])
        return mock

    @pytest.fixture
    async def vector_store(self, mock_chroma_client, mock_embeddings_handler):
        """Instance du vector store manager avec mocks"""
        with patch("chromadb.PersistentClient", return_value=mock_chroma_client):
            with patch(
                "app.core.vector_store.get_embeddings_handler",
                return_value=mock_embeddings_handler,
            ):
                manager = VectorStoreManager()
                await manager.initialize()
                yield manager

    @pytest.mark.asyncio
    async def test_initialization(self, vector_store):
        """Test initialisation du vector store"""
        assert vector_store.client is not None
        assert vector_store.embeddings_handler is not None

    def test_get_or_create_collection(self, vector_store):
        """Test récupération/création de collection"""
        collection = vector_store.get_or_create_collection(
            "test_collection", metadata={"type": "test"}
        )

        assert collection is not None
        vector_store.client.get_or_create_collection.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_documents(self, vector_store, mock_embeddings_handler):
        """Test ajout de documents"""
        documents = ["Document 1", "Document 2", "Document 3"]
        metadatas = [{"source": f"Source {i}"} for i in range(3)]

        ids = await vector_store.add_documents(
            collection_name="test", documents=documents, metadatas=metadatas
        )

        assert len(ids) == 3
        mock_embeddings_handler.embed_texts.assert_called_once_with(documents)

    @pytest.mark.asyncio
    async def test_query(self, vector_store, mock_embeddings_handler):
        """Test recherche dans une collection"""
        # Mock des résultats ChromaDB
        mock_collection = vector_store.client.get_or_create_collection.return_value
        mock_collection.query = MagicMock(
            return_value={
                "ids": [["id1", "id2"]],
                "documents": [["Doc 1", "Doc 2"]],
                "metadatas": [[{"source": "Test"}, {"source": "Test2"}]],
                "distances": [[0.2, 0.3]],
            }
        )

        results = await vector_store.query(
            collection_name="test", query_text="Test query", n_results=2
        )

        assert len(results) == 2
        assert results[0]["document"] == "Doc 1"
        assert results[0]["relevance_score"] == 1 - 0.2
        mock_embeddings_handler.embed_query.assert_called_once()

    def test_delete_documents(self, vector_store):
        """Test suppression de documents"""
        mock_collection = vector_store.client.get_or_create_collection.return_value
        mock_collection.count = MagicMock(side_effect=[10, 8])  # Avant/après

        deleted = vector_store.delete_documents(
            collection_name="test", ids=["id1", "id2"]
        )

        assert deleted == 2
        mock_collection.delete.assert_called_once()

    def test_delete_collection(self, vector_store):
        """Test suppression d'une collection"""
        result = vector_store.delete_collection("test_collection")

        assert result is True
        vector_store.client.delete_collection.assert_called_once_with(
            name="test_collection"
        )

    def test_list_collections(self, vector_store):
        """Test listage des collections"""
        mock_col1 = MagicMock()
        mock_col1.name = "collection1"
        mock_col2 = MagicMock()
        mock_col2.name = "collection2"

        vector_store.client.list_collections = MagicMock(
            return_value=[mock_col1, mock_col2]
        )

        collections = vector_store.list_collections()

        assert len(collections) == 2
        assert "collection1" in collections
        assert "collection2" in collections

    def test_get_collection_stats(self, vector_store):
        """Test récupération des statistiques"""
        stats = vector_store.get_collection_stats("test")

        assert "name" in stats
        assert "count" in stats
        assert stats["count"] == 10


@pytest.mark.unit
class TestVectorStoreCoda2zMethods:
    """Tests des méthodes spécifiques Coda2z"""

    @pytest.fixture
    async def vector_store(self, mock_chroma_client, mock_embeddings_handler):
        """Instance du vector store manager avec mocks"""
        with patch("chromadb.PersistentClient", return_value=mock_chroma_client):
            with patch(
                "app.core.vector_store.get_embeddings_handler",
                return_value=mock_embeddings_handler,
            ):
                manager = VectorStoreManager()
                await manager.initialize()
                yield manager

    @pytest.mark.asyncio
    async def test_add_to_knowledge_base(self, vector_store):
        """Test ajout à la base de connaissances"""
        documents = ["Article 1240 du Code Civil"]
        metadatas = [{"source": "Code Civil", "article": "Art. 1240"}]

        ids = await vector_store.add_to_knowledge_base(
            documents=documents, metadatas=metadatas
        )

        assert len(ids) > 0

    @pytest.mark.asyncio
    async def test_add_to_user_history(self, vector_store, test_user_id):
        """Test ajout à l'historique utilisateur"""
        documents = ["Question de l'utilisateur"]
        metadatas = [{"role": "user", "timestamp": "2024-11-19"}]

        ids = await vector_store.add_to_user_history(
            user_id=test_user_id, documents=documents, metadatas=metadatas
        )

        assert len(ids) > 0
        # Vérifier que user_id a été ajouté aux métadonnées
        assert metadatas[0]["user_id"] == test_user_id

    @pytest.mark.asyncio
    async def test_add_user_document(self, vector_store, test_user_id):
        """Test ajout d'un document privé utilisateur"""
        document = "Contenu du contrat"
        metadata = {"filename": "contrat.pdf", "category": "contrat"}

        doc_id = await vector_store.add_user_document(
            user_id=test_user_id, document=document, metadata=metadata
        )

        assert doc_id is not None
        assert metadata["user_id"] == test_user_id

    @pytest.mark.asyncio
    async def test_query_knowledge_base(self, vector_store):
        """Test recherche dans la base de connaissances"""
        # Mock des résultats
        mock_collection = vector_store.client.get_or_create_collection.return_value
        mock_collection.query = MagicMock(
            return_value={
                "ids": [["id1"]],
                "documents": [["Article du code"]],
                "metadatas": [[{"source": "Code Civil"}]],
                "distances": [[0.2]],
            }
        )

        results = await vector_store.query_knowledge_base("responsabilité civile")

        assert len(results) == 1
        assert "Article du code" in results[0]["document"]

    @pytest.mark.asyncio
    async def test_query_user_history(self, vector_store, test_user_id):
        """Test recherche dans l'historique utilisateur"""
        mock_collection = vector_store.client.get_or_create_collection.return_value
        mock_collection.query = MagicMock(
            return_value={
                "ids": [["id1"]],
                "documents": [["Message précédent"]],
                "metadatas": [[{"user_id": test_user_id}]],
                "distances": [[0.3]],
            }
        )

        results = await vector_store.query_user_history(
            user_id=test_user_id, query_text="question similaire"
        )

        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_query_user_documents(self, vector_store, test_user_id):
        """Test recherche dans les documents privés"""
        mock_collection = vector_store.client.get_or_create_collection.return_value
        mock_collection.query = MagicMock(
            return_value={
                "ids": [["id1"]],
                "documents": [["Contenu du document privé"]],
                "metadatas": [[{"user_id": test_user_id, "filename": "doc.pdf"}]],
                "distances": [[0.25]],
            }
        )

        results = await vector_store.query_user_documents(
            user_id=test_user_id, query_text="recherche dans mes docs"
        )

        assert len(results) == 1

    def test_delete_user_data(self, vector_store, test_user_id):
        """Test suppression des données utilisateur (RGPD)"""
        results = vector_store.delete_user_data(test_user_id)

        assert "history" in results
        assert "documents" in results
        # Devrait appeler delete_collection deux fois
        assert vector_store.client.delete_collection.call_count == 2


@pytest.mark.unit
class TestVectorStoreFormatting:
    """Tests du formatage des résultats"""

    @pytest.fixture
    async def vector_store(self, mock_chroma_client, mock_embeddings_handler):
        """Instance du vector store manager"""
        with patch("chromadb.PersistentClient", return_value=mock_chroma_client):
            with patch(
                "app.core.vector_store.get_embeddings_handler",
                return_value=mock_embeddings_handler,
            ):
                manager = VectorStoreManager()
                await manager.initialize()
                yield manager

    def test_format_query_results(self, vector_store):
        """Test formatage des résultats de requête"""
        raw_results = {
            "ids": [["id1", "id2", "id3"]],
            "documents": [["Doc 1", "Doc 2", "Doc 3"]],
            "metadatas": [
                [{"source": "S1"}, {"source": "S2"}, {"source": "S3"}]
            ],
            "distances": [[0.1, 0.2, 0.3]],
        }

        formatted = vector_store._format_query_results(raw_results)

        assert len(formatted) == 3
        assert formatted[0]["id"] == "id1"
        assert formatted[0]["document"] == "Doc 1"
        assert formatted[0]["metadata"]["source"] == "S1"
        assert formatted[0]["distance"] == 0.1
        assert formatted[0]["relevance_score"] == 0.9  # 1 - 0.1

    def test_format_query_results_empty(self, vector_store):
        """Test formatage de résultats vides"""
        raw_results = {
            "ids": [[]],
            "documents": [[]],
            "metadatas": [[]],
            "distances": [[]],
        }

        formatted = vector_store._format_query_results(raw_results)

        assert len(formatted) == 0
