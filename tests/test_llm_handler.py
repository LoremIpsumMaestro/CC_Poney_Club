"""
Tests pour le gestionnaire LLM
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.core.llm_handler import LLMHandler


@pytest.mark.unit
class TestLLMHandler:
    """Tests du gestionnaire LLM"""

    @pytest.fixture
    def mock_httpx_client(self):
        """Mock du client HTTP"""
        mock = AsyncMock()

        # Mock de la réponse pour /api/tags
        mock_tags = AsyncMock()
        mock_tags.json = MagicMock(
            return_value={"models": [{"name": "qwen2.5:14b"}]}
        )
        mock_tags.raise_for_status = MagicMock()

        # Mock de la réponse pour /api/chat
        mock_chat = AsyncMock()
        mock_chat.json = MagicMock(
            return_value={
                "message": {"content": "Réponse du LLM"}
            }
        )
        mock_chat.raise_for_status = MagicMock()

        # Configurer les retours selon l'endpoint
        async def get_side_effect(endpoint):
            if "tags" in endpoint:
                return mock_tags
            return None

        async def post_side_effect(endpoint, **kwargs):
            if "chat" in endpoint:
                return mock_chat
            return None

        mock.get = get_side_effect
        mock.post = post_side_effect

        return mock

    @pytest.fixture
    async def llm_handler(self, mock_httpx_client):
        """Instance du LLM handler avec mock"""
        with patch("httpx.AsyncClient", return_value=mock_httpx_client):
            handler = LLMHandler(
                model_name="qwen2.5:14b",
                base_url="http://localhost:11434",
                temperature=0.7,
                max_tokens=2048,
            )
            await handler.initialize()
            yield handler

    @pytest.mark.asyncio
    async def test_initialization(self, llm_handler):
        """Test initialisation du LLM handler"""
        assert llm_handler.client is not None
        assert llm_handler.model_name == "qwen2.5:14b"
        assert llm_handler.temperature == 0.7
        assert llm_handler.max_tokens == 2048

    @pytest.mark.asyncio
    async def test_generate(self, llm_handler, sample_query):
        """Test génération de réponse"""
        response = await llm_handler.generate(prompt=sample_query)

        assert isinstance(response, str)
        assert len(response) > 0
        assert response == "Réponse du LLM"

    @pytest.mark.asyncio
    async def test_generate_with_system_prompt(self, llm_handler, sample_query):
        """Test génération avec prompt système custom"""
        system_prompt = "Tu es un assistant juridique spécialisé."
        response = await llm_handler.generate(
            prompt=sample_query, system_prompt=system_prompt
        )

        assert isinstance(response, str)

    @pytest.mark.asyncio
    async def test_generate_with_custom_temperature(self, llm_handler, sample_query):
        """Test génération avec température custom"""
        response = await llm_handler.generate(
            prompt=sample_query, temperature=0.5
        )

        assert isinstance(response, str)

    @pytest.mark.asyncio
    async def test_generate_with_custom_max_tokens(self, llm_handler, sample_query):
        """Test génération avec max_tokens custom"""
        response = await llm_handler.generate(
            prompt=sample_query, max_tokens=1024
        )

        assert isinstance(response, str)

    @pytest.mark.asyncio
    async def test_generate_with_context(self, llm_handler, sample_query):
        """Test génération avec contexte RAG"""
        context = "Article 1240 du Code Civil : Tout fait quelconque de l'homme..."
        history = [
            {"role": "user", "content": "Question précédente"},
            {"role": "assistant", "content": "Réponse précédente"},
        ]

        response = await llm_handler.generate_with_context(
            query=sample_query, context=context, history=history
        )

        assert isinstance(response, str)

    @pytest.mark.asyncio
    async def test_generate_stream(self, llm_handler, sample_query):
        """Test génération en mode streaming"""
        # Mock du streaming
        async def mock_aiter_lines():
            import json

            for chunk in ["Réponse ", "du ", "LLM"]:
                yield json.dumps({"message": {"content": chunk}, "done": False})
            yield json.dumps({"message": {"content": ""}, "done": True})

        mock_response = AsyncMock()
        mock_response.aiter_lines = mock_aiter_lines
        mock_response.raise_for_status = MagicMock()

        with patch.object(
            llm_handler.client,
            "stream",
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response)),
        ):
            chunks = []
            async for chunk in llm_handler.generate_stream(prompt=sample_query):
                chunks.append(chunk)

            assert len(chunks) == 3
            assert "".join(chunks) == "Réponse du LLM"

    @pytest.mark.asyncio
    async def test_close(self, llm_handler):
        """Test fermeture du client"""
        await llm_handler.close()

        llm_handler.client.aclose.assert_called_once()


@pytest.mark.unit
class TestLLMHandlerEdgeCases:
    """Tests des cas limites du LLM handler"""

    @pytest.fixture
    async def llm_handler(self, mock_httpx_client):
        """Instance du LLM handler"""
        with patch("httpx.AsyncClient", return_value=mock_httpx_client):
            handler = LLMHandler()
            await handler.initialize()
            yield handler

    @pytest.mark.asyncio
    async def test_generate_empty_prompt(self, llm_handler):
        """Test génération avec prompt vide"""
        response = await llm_handler.generate(prompt="")

        # Devrait quand même retourner quelque chose
        assert isinstance(response, str)

    @pytest.mark.asyncio
    async def test_generate_very_long_prompt(self, llm_handler):
        """Test génération avec prompt très long"""
        long_prompt = "Question juridique " * 1000

        response = await llm_handler.generate(prompt=long_prompt)

        assert isinstance(response, str)

    @pytest.mark.asyncio
    async def test_generate_http_error(self, llm_handler):
        """Test gestion d'erreur HTTP"""
        # Mock une erreur HTTP
        llm_handler.client.post = AsyncMock(
            side_effect=Exception("HTTP Error 500")
        )

        with pytest.raises(Exception):
            await llm_handler.generate(prompt="Test")

    @pytest.mark.asyncio
    async def test_model_not_available(self):
        """Test quand le modèle n'est pas disponible"""
        mock_client = AsyncMock()
        mock_tags = AsyncMock()
        mock_tags.json = MagicMock(
            return_value={"models": []}  # Aucun modèle
        )
        mock_tags.raise_for_status = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_tags)

        with patch("httpx.AsyncClient", return_value=mock_client):
            handler = LLMHandler(model_name="nonexistent:model")
            # Devrait quand même s'initialiser (juste un warning)
            await handler.initialize()

            assert handler.client is not None


@pytest.mark.unit
class TestLLMHandlerConfiguration:
    """Tests de configuration du LLM handler"""

    @pytest.mark.asyncio
    async def test_default_configuration(self):
        """Test configuration par défaut"""
        with patch("httpx.AsyncClient"):
            handler = LLMHandler()

            assert handler.model_name == "qwen2.5:14b"
            assert handler.base_url == "http://localhost:11434"
            assert 0 <= handler.temperature <= 2
            assert handler.max_tokens > 0

    @pytest.mark.asyncio
    async def test_custom_configuration(self):
        """Test configuration personnalisée"""
        with patch("httpx.AsyncClient"):
            handler = LLMHandler(
                model_name="custom-model",
                base_url="http://custom-url:8080",
                temperature=0.5,
                max_tokens=512,
            )

            assert handler.model_name == "custom-model"
            assert handler.base_url == "http://custom-url:8080"
            assert handler.temperature == 0.5
            assert handler.max_tokens == 512
