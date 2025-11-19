"""
Tests pour le pipeline RAG
"""

import pytest
from unittest.mock import AsyncMock, patch
from app.core.rag_pipeline import RAGPipeline


@pytest.mark.unit
class TestRAGPipeline:
    """Tests du pipeline RAG"""

    @pytest.fixture
    async def rag_pipeline(self, mock_llm_handler, mock_vector_store):
        """Instance du pipeline RAG avec mocks"""
        with patch(
            "app.core.rag_pipeline.get_llm_handler", return_value=mock_llm_handler
        ):
            with patch(
                "app.core.rag_pipeline.get_vector_store", return_value=mock_vector_store
            ):
                pipeline = RAGPipeline()
                await pipeline.initialize()
                yield pipeline

    @pytest.mark.asyncio
    async def test_initialization(self, rag_pipeline):
        """Test initialisation du pipeline"""
        assert rag_pipeline.llm is not None
        assert rag_pipeline.vector_store is not None
        assert rag_pipeline.top_k == 5

    @pytest.mark.asyncio
    async def test_process_query_success(
        self, rag_pipeline, test_user_id, sample_query
    ):
        """Test traitement d'une requête réussie"""
        result = await rag_pipeline.process_query(
            query=sample_query, user_id=test_user_id, conversation_id="conv123"
        )

        assert "response" in result
        assert "sources" in result
        assert "context_used" in result
        assert "metadata" in result
        assert result["response"] is not None

    @pytest.mark.asyncio
    async def test_process_query_invalid(self, rag_pipeline, test_user_id):
        """Test traitement d'une requête invalide"""
        result = await rag_pipeline.process_query(
            query="ab",  # Trop court
            user_id=test_user_id,
        )

        assert "error" in result
        assert result["response"] is None

    @pytest.mark.asyncio
    async def test_retrieve_context(self, rag_pipeline, test_user_id, sample_query):
        """Test récupération du contexte"""
        law_results, user_docs, history = await rag_pipeline._retrieve_context(
            sample_query, test_user_id
        )

        assert isinstance(law_results, list)
        assert isinstance(user_docs, list)
        assert isinstance(history, list)
        # Devrait avoir des résultats de lois
        assert len(law_results) > 0

    def test_filter_by_relevance(self, rag_pipeline):
        """Test filtrage par pertinence"""
        results = [
            {"relevance_score": 0.9},  # Garde
            {"relevance_score": 0.8},  # Garde
            {"relevance_score": 0.5},  # Filtre
            {"relevance_score": 0.3},  # Filtre
        ]

        # Seuil par défaut = 0.7
        filtered = rag_pipeline._filter_by_relevance(results)

        assert len(filtered) == 2
        assert all(r["relevance_score"] >= 0.7 for r in filtered)

    def test_filter_by_relevance_all_below_threshold(self, rag_pipeline):
        """Test filtrage quand tous sont sous le seuil"""
        results = [
            {"relevance_score": 0.3},
            {"relevance_score": 0.4},
        ]

        filtered = rag_pipeline._filter_by_relevance(results)

        assert len(filtered) == 0

    @pytest.mark.asyncio
    async def test_generate(self, rag_pipeline, sample_query):
        """Test génération de réponse"""
        context = "Article 1240 du Code Civil..."
        response = await rag_pipeline._generate(sample_query, context)

        assert isinstance(response, str)
        assert len(response) > 0

    @pytest.mark.asyncio
    async def test_generate_with_history(self, rag_pipeline, sample_query):
        """Test génération avec historique"""
        context = "Article 1240..."
        history = [
            {"role": "user", "content": "Question précédente ?"},
            {"role": "assistant", "content": "Réponse précédente."},
        ]

        response = await rag_pipeline._generate(sample_query, context, history)

        assert isinstance(response, str)

    def test_format_history(self, rag_pipeline):
        """Test formatage de l'historique"""
        history = [
            {"role": "user", "content": "Question 1"},
            {"role": "assistant", "content": "Réponse 1"},
            {"role": "user", "content": "Question 2"},
        ]

        formatted = rag_pipeline._format_history(history)

        assert isinstance(formatted, str)
        assert "user: Question 1" in formatted
        assert "assistant: Réponse 1" in formatted

    def test_format_history_empty(self, rag_pipeline):
        """Test formatage d'historique vide"""
        formatted = rag_pipeline._format_history([])

        assert formatted == ""

    def test_format_history_keeps_last_5(self, rag_pipeline):
        """Test que seuls les 5 derniers messages sont gardés"""
        history = [{"role": "user", "content": f"Message {i}"} for i in range(10)]

        formatted = rag_pipeline._format_history(history)

        # Devrait contenir les messages 5-9
        assert "Message 5" in formatted
        assert "Message 9" in formatted
        # Ne devrait pas contenir les messages 0-4
        assert "Message 0" not in formatted

    def test_format_sources(self, rag_pipeline):
        """Test formatage des sources"""
        law_results = [
            {
                "metadata": {
                    "source": "Code Civil",
                    "article": "Art. 1240",
                },
                "relevance_score": 0.85,
                "document": "Long texte juridique " * 30,
            }
        ]

        user_docs = [
            {
                "metadata": {
                    "filename": "contrat.pdf",
                    "category": "contrat",
                },
                "relevance_score": 0.75,
                "document": "Contenu du contrat " * 30,
            }
        ]

        sources = rag_pipeline._format_sources(law_results, user_docs)

        assert len(sources) == 2
        assert sources[0]["type"] == "law"
        assert sources[0]["name"] == "Code Civil"
        assert sources[1]["type"] == "user_document"
        assert sources[1]["name"] == "contrat.pdf"
        # Vérifier que l'excerpt est tronqué
        assert len(sources[0]["excerpt"]) < 250

    @pytest.mark.asyncio
    async def test_save_to_history(
        self, rag_pipeline, test_user_id, sample_query
    ):
        """Test sauvegarde dans l'historique"""
        success = await rag_pipeline.save_to_history(
            user_id=test_user_id,
            conversation_id="conv123",
            query=sample_query,
            response="Réponse de l'assistant",
        )

        assert success is True
        # Devrait appeler add_to_user_history deux fois (question + réponse)
        assert rag_pipeline.vector_store.add_to_user_history.call_count == 2

    def test_classify_query_greeting(self, rag_pipeline):
        """Test classification d'une salutation"""
        query_type = rag_pipeline.classify_query("Bonjour")

        assert query_type == "greeting"

    def test_classify_query_legal(self, rag_pipeline):
        """Test classification d'une question juridique"""
        query_type = rag_pipeline.classify_query(
            "Qu'est-ce que l'article 1240 du code civil ?"
        )

        assert query_type == "legal"

    def test_classify_query_default_legal(self, rag_pipeline):
        """Test classification par défaut (juridique)"""
        query_type = rag_pipeline.classify_query(
            "Question sans mots-clés spécifiques"
        )

        # Par défaut, on considère juridique
        assert query_type == "legal"


@pytest.mark.unit
class TestRAGPipelineIntegration:
    """Tests d'intégration du pipeline RAG"""

    @pytest.fixture
    async def rag_pipeline(self, mock_llm_handler, mock_vector_store):
        """Instance du pipeline RAG"""
        with patch(
            "app.core.rag_pipeline.get_llm_handler", return_value=mock_llm_handler
        ):
            with patch(
                "app.core.rag_pipeline.get_vector_store", return_value=mock_vector_store
            ):
                pipeline = RAGPipeline()
                await pipeline.initialize()
                yield pipeline

    @pytest.mark.asyncio
    async def test_full_pipeline_flow(
        self, rag_pipeline, test_user_id, sample_query
    ):
        """Test du flux complet du pipeline"""
        # Simuler une requête complète
        result = await rag_pipeline.process_query(
            query=sample_query,
            user_id=test_user_id,
            conversation_id="conv123",
            history=[],
        )

        # Vérifier tous les éléments de la réponse
        assert result is not None
        assert "response" in result
        assert "sources" in result
        assert "context_used" in result
        assert "metadata" in result

        # Vérifier le contexte utilisé
        context = result["context_used"]
        assert "laws" in context
        assert "user_documents" in context
        assert "history" in context
        assert context["laws"] > 0  # Au moins des lois trouvées

        # Vérifier les métadonnées
        metadata = result["metadata"]
        assert "query_length" in metadata
        assert "response_length" in metadata
        assert "processing_time" in metadata
        assert "timestamp" in metadata

    @pytest.mark.asyncio
    async def test_pipeline_with_no_results(self, rag_pipeline, test_user_id):
        """Test du pipeline sans résultats de recherche"""
        # Mock pour retourner des résultats vides
        rag_pipeline.vector_store.query_knowledge_base = AsyncMock(return_value=[])
        rag_pipeline.vector_store.query_user_documents = AsyncMock(return_value=[])
        rag_pipeline.vector_store.query_user_history = AsyncMock(return_value=[])

        result = await rag_pipeline.process_query(
            query="Question sans réponse",
            user_id=test_user_id,
        )

        # Devrait quand même retourner une réponse
        assert "response" in result
        assert result["context_used"]["laws"] == 0

    @pytest.mark.asyncio
    async def test_pipeline_error_handling(self, rag_pipeline, test_user_id):
        """Test gestion des erreurs dans le pipeline"""
        # Simuler une erreur dans le vector store
        rag_pipeline.vector_store.query_knowledge_base = AsyncMock(
            side_effect=Exception("Erreur de base de données")
        )

        result = await rag_pipeline.process_query(
            query="Question qui causera une erreur",
            user_id=test_user_id,
        )

        # Devrait gérer l'erreur gracieusement
        assert "response" in result
        # La réponse devrait indiquer une erreur
        assert "erreur" in result["response"].lower() or "error" in result


@pytest.mark.unit
class TestRAGPipelineStreaming:
    """Tests du mode streaming"""

    @pytest.fixture
    async def rag_pipeline(self, mock_llm_handler, mock_vector_store):
        """Instance du pipeline RAG"""
        with patch(
            "app.core.rag_pipeline.get_llm_handler", return_value=mock_llm_handler
        ):
            with patch(
                "app.core.rag_pipeline.get_vector_store", return_value=mock_vector_store
            ):
                pipeline = RAGPipeline()
                await pipeline.initialize()
                yield pipeline

    @pytest.mark.asyncio
    async def test_generate_stream(self, rag_pipeline, sample_query):
        """Test génération en mode streaming"""
        context = "Article 1240..."

        chunks = []
        async for chunk in rag_pipeline._generate_stream(sample_query, context):
            chunks.append(chunk)

        assert len(chunks) > 0
        assert all(isinstance(chunk, str) for chunk in chunks)
