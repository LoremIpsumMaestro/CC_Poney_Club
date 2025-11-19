"""
Tests pour le gestionnaire d'embeddings
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.core.embeddings_handler import EmbeddingsHandler


@pytest.mark.unit
class TestEmbeddingsHandler:
    """Tests du gestionnaire d'embeddings"""

    @pytest.fixture
    def mock_sentence_transformer(self):
        """Mock du modèle SentenceTransformer"""
        mock = MagicMock()
        mock.encode = MagicMock(return_value=[[0.1] * 768])
        mock.get_sentence_embedding_dimension = MagicMock(return_value=768)
        return mock

    @pytest.fixture
    async def embeddings_handler_local(self, mock_sentence_transformer):
        """Instance du handler en mode local"""
        with patch(
            "app.core.embeddings_handler.SentenceTransformer",
            return_value=mock_sentence_transformer,
        ):
            handler = EmbeddingsHandler(use_local=True)
            await handler.initialize()
            yield handler

    @pytest.fixture
    def mock_httpx_client(self):
        """Mock du client HTTP pour mode API"""
        mock = AsyncMock()
        mock_response = AsyncMock()
        mock_response.json = MagicMock(return_value={"embedding": [0.1] * 768})
        mock_response.raise_for_status = MagicMock()
        mock.post = AsyncMock(return_value=mock_response)
        return mock

    @pytest.fixture
    async def embeddings_handler_api(self, mock_httpx_client):
        """Instance du handler en mode API"""
        with patch("httpx.AsyncClient", return_value=mock_httpx_client):
            handler = EmbeddingsHandler(use_local=False)
            await handler.initialize()
            yield handler

    @pytest.mark.asyncio
    async def test_initialization_local(self, embeddings_handler_local):
        """Test initialisation en mode local"""
        assert embeddings_handler_local.model is not None
        assert embeddings_handler_local.use_local is True
        assert embeddings_handler_local.dimension == 768

    @pytest.mark.asyncio
    async def test_initialization_api(self, embeddings_handler_api):
        """Test initialisation en mode API"""
        assert embeddings_handler_api.client is not None
        assert embeddings_handler_api.use_local is False

    @pytest.mark.asyncio
    async def test_embed_text_local(self, embeddings_handler_local):
        """Test embedding d'un texte en mode local"""
        text = "Article 1240 du Code Civil"
        embedding = await embeddings_handler_local.embed_text(text)

        assert isinstance(embedding, list)
        assert len(embedding) == 768
        assert all(isinstance(x, float) for x in embedding)

    @pytest.mark.asyncio
    async def test_embed_text_api(self, embeddings_handler_api):
        """Test embedding d'un texte en mode API"""
        text = "Article 1240 du Code Civil"
        embedding = await embeddings_handler_api.embed_text(text)

        assert isinstance(embedding, list)
        assert len(embedding) == 768

    @pytest.mark.asyncio
    async def test_embed_texts_local(self, embeddings_handler_local):
        """Test embedding de plusieurs textes en mode local"""
        texts = [
            "Premier texte juridique",
            "Deuxième texte de loi",
            "Troisième article",
        ]

        embeddings_handler_local.model.encode = MagicMock(
            return_value=[[0.1] * 768, [0.2] * 768, [0.3] * 768]
        )

        embeddings = await embeddings_handler_local.embed_texts(texts)

        assert isinstance(embeddings, list)
        assert len(embeddings) == 3
        assert all(len(emb) == 768 for emb in embeddings)

    @pytest.mark.asyncio
    async def test_embed_texts_api(self, embeddings_handler_api):
        """Test embedding de plusieurs textes en mode API"""
        texts = ["Text 1", "Text 2"]

        embeddings = await embeddings_handler_api.embed_texts(texts)

        assert isinstance(embeddings, list)
        assert len(embeddings) == 2

    @pytest.mark.asyncio
    async def test_embed_texts_with_batch_size(self, embeddings_handler_local):
        """Test embedding avec batch size personnalisé"""
        texts = ["Text " + str(i) for i in range(100)]

        embeddings_handler_local.model.encode = MagicMock(
            return_value=[[0.1] * 768] * 100
        )

        embeddings = await embeddings_handler_local.embed_texts(texts, batch_size=16)

        assert len(embeddings) == 100
        # Vérifier que batch_size a été utilisé
        embeddings_handler_local.model.encode.assert_called_once()

    @pytest.mark.asyncio
    async def test_embed_query(self, embeddings_handler_local):
        """Test embedding d'une requête (alias de embed_text)"""
        query = "Qu'est-ce que la responsabilité civile ?"
        embedding = await embeddings_handler_local.embed_query(query)

        assert isinstance(embedding, list)
        assert len(embedding) == 768

    def test_get_dimension(self, embeddings_handler_local):
        """Test récupération de la dimension"""
        dimension = embeddings_handler_local.get_dimension()

        assert dimension == 768

    @pytest.mark.asyncio
    async def test_close(self, embeddings_handler_api):
        """Test fermeture du client API"""
        await embeddings_handler_api.close()

        embeddings_handler_api.client.aclose.assert_called_once()


@pytest.mark.unit
class TestEmbeddingsHandlerEdgeCases:
    """Tests des cas limites"""

    @pytest.fixture
    async def embeddings_handler(self, mock_sentence_transformer):
        """Instance du handler"""
        with patch(
            "app.core.embeddings_handler.SentenceTransformer",
            return_value=mock_sentence_transformer,
        ):
            handler = EmbeddingsHandler(use_local=True)
            await handler.initialize()
            yield handler

    @pytest.mark.asyncio
    async def test_embed_empty_text(self, embeddings_handler):
        """Test embedding d'un texte vide"""
        embedding = await embeddings_handler.embed_text("")

        assert isinstance(embedding, list)
        assert len(embedding) == 768

    @pytest.mark.asyncio
    async def test_embed_very_long_text(self, embeddings_handler):
        """Test embedding d'un texte très long"""
        long_text = "Texte juridique " * 10000

        embedding = await embeddings_handler.embed_text(long_text)

        assert isinstance(embedding, list)
        assert len(embedding) == 768

    @pytest.mark.asyncio
    async def test_embed_texts_empty_list(self, embeddings_handler):
        """Test embedding d'une liste vide"""
        embeddings_handler.model.encode = MagicMock(return_value=[])

        embeddings = await embeddings_handler.embed_texts([])

        assert isinstance(embeddings, list)
        assert len(embeddings) == 0

    @pytest.mark.asyncio
    async def test_embed_text_special_characters(self, embeddings_handler):
        """Test embedding avec caractères spéciaux"""
        text = "Art. 1240 : € & @ # % 🇫🇷"

        embedding = await embeddings_handler.embed_text(text)

        assert isinstance(embedding, list)
        assert len(embedding) == 768

    @pytest.mark.asyncio
    async def test_initialization_error(self):
        """Test gestion d'erreur à l'initialisation"""
        with patch(
            "app.core.embeddings_handler.SentenceTransformer",
            side_effect=Exception("Model not found"),
        ):
            handler = EmbeddingsHandler(use_local=True)

            with pytest.raises(Exception):
                await handler.initialize()


@pytest.mark.unit
class TestEmbeddingsHandlerConfiguration:
    """Tests de configuration"""

    @pytest.mark.asyncio
    async def test_custom_model_name(self):
        """Test avec nom de modèle personnalisé"""
        mock_model = MagicMock()
        mock_model.get_sentence_embedding_dimension = MagicMock(return_value=384)

        with patch(
            "app.core.embeddings_handler.SentenceTransformer",
            return_value=mock_model,
        ):
            handler = EmbeddingsHandler(
                model_name="all-MiniLM-L6-v2", use_local=True
            )
            await handler.initialize()

            assert handler.model_name == "all-MiniLM-L6-v2"

    @pytest.mark.asyncio
    async def test_custom_base_url(self):
        """Test avec URL de base personnalisée"""
        mock_client = AsyncMock()

        with patch("httpx.AsyncClient", return_value=mock_client):
            handler = EmbeddingsHandler(
                base_url="http://custom-server:8080", use_local=False
            )
            await handler.initialize()

            assert handler.base_url == "http://custom-server:8080"

    @pytest.mark.asyncio
    async def test_default_configuration(self):
        """Test configuration par défaut"""
        handler = EmbeddingsHandler()

        assert handler.model_name == "snowflake-arctic-embed2"
        assert handler.base_url == "http://localhost:11434"
        assert handler.dimension == 768


@pytest.mark.unit
class TestEmbeddingsHandlerSingleton:
    """Tests du pattern singleton"""

    @pytest.mark.asyncio
    async def test_get_embeddings_handler(self):
        """Test récupération de l'instance globale"""
        from app.core.embeddings_handler import get_embeddings_handler

        mock_model = MagicMock()
        mock_model.get_sentence_embedding_dimension = MagicMock(return_value=768)

        with patch(
            "app.core.embeddings_handler.SentenceTransformer",
            return_value=mock_model,
        ):
            # Reset le singleton
            import app.core.embeddings_handler as emb_module

            emb_module._embeddings_handler = None

            handler1 = await get_embeddings_handler()
            handler2 = await get_embeddings_handler()

            # Devrait retourner la même instance
            assert handler1 is handler2
