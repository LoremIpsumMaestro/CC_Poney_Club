"""
Pipeline RAG (Retrieval-Augmented Generation)
Orchestration complète : retrieval + génération
"""

import time
from datetime import datetime
from typing import Any, AsyncGenerator, Dict, List, Optional

from app.config.prompts import build_context_from_results, build_rag_prompt
from app.config.settings import settings
from app.core.llm_handler import get_llm_handler
from app.core.vector_store import get_vector_store
from app.utils.logger import log_llm_request, logger
from app.utils.validators import validate_query


class RAGPipeline:
    """
    Pipeline RAG complet pour Coda2z
    """

    def __init__(self):
        """Initialise le pipeline RAG"""
        self.vector_store = None
        self.llm = None

        self.top_k = settings.rag_top_k
        self.similarity_threshold = settings.rag_similarity_threshold

        logger.info(f"RAGPipeline initialisé - TopK: {self.top_k}")

    async def initialize(self):
        """Initialise les composants du pipeline"""
        try:
            logger.info("Initialisation du pipeline RAG...")

            # Initialiser vector store
            self.vector_store = await get_vector_store()

            # Initialiser LLM
            self.llm = await get_llm_handler()

            logger.info("Pipeline RAG initialisé avec succès")

        except Exception as e:
            logger.error(f"Erreur initialisation pipeline RAG: {e}")
            raise

    async def process_query(
        self,
        query: str,
        user_id: str,
        conversation_id: Optional[str] = None,
        history: Optional[List[Dict[str, str]]] = None,
        stream: bool = False,
    ) -> Dict[str, Any]:
        """
        Traite une requête utilisateur avec RAG

        Args:
            query: Question de l'utilisateur
            user_id: ID de l'utilisateur
            conversation_id: ID de la conversation
            history: Historique de conversation
            stream: Mode streaming

        Returns:
            Résultat avec réponse et sources
        """
        start_time = time.time()

        try:
            # Validation
            is_valid, error_msg = validate_query(query)
            if not is_valid:
                return {"error": error_msg, "response": None}

            # 1. RETRIEVAL : Recherche dans les différentes sources
            logger.debug(f"Retrieval pour user {user_id}: '{query[:50]}...'")

            # Recherche parallèle dans toutes les sources
            law_results, user_docs_results, history_results = await self._retrieve_context(
                query, user_id
            )

            # 2. FILTRAGE : Garder uniquement les résultats pertinents
            law_results = self._filter_by_relevance(law_results)
            user_docs_results = self._filter_by_relevance(user_docs_results)

            # 3. CONSTRUCTION DU CONTEXTE
            context = build_context_from_results(
                law_results=law_results,
                user_doc_results=user_docs_results,
                history_results=history_results,
            )

            # 4. GÉNÉRATION avec le LLM
            logger.debug("Génération de la réponse...")

            if stream:
                # Mode streaming (pour l'interface)
                return await self._generate_stream(query, context, history)
            else:
                # Mode standard
                response = await self._generate(query, context, history)

            # 5. POST-PROCESSING
            result = {
                "response": response,
                "sources": self._format_sources(law_results, user_docs_results),
                "context_used": {
                    "laws": len(law_results),
                    "user_documents": len(user_docs_results),
                    "history": len(history_results),
                },
                "metadata": {
                    "query_length": len(query),
                    "response_length": len(response),
                    "processing_time": time.time() - start_time,
                    "timestamp": datetime.utcnow().isoformat(),
                },
            }

            # Log
            log_llm_request(user_id, query, result["metadata"]["processing_time"])

            logger.info(
                f"Query traitée en {result['metadata']['processing_time']:.2f}s - "
                f"{result['context_used']['laws']} lois, "
                f"{result['context_used']['user_documents']} docs"
            )

            return result

        except Exception as e:
            logger.error(f"Erreur process_query: {e}")
            return {
                "error": str(e),
                "response": "Une erreur est survenue lors du traitement de votre question.",
                "sources": [],
            }

    async def _retrieve_context(
        self, query: str, user_id: str
    ) -> tuple[List[Dict], List[Dict], List[Dict]]:
        """
        Récupère le contexte depuis les différentes sources EN PARALLELE (OPTIMISÉ)

        Args:
            query: Requête utilisateur
            user_id: ID utilisateur

        Returns:
            (law_results, user_docs_results, history_results)
        """
        # OPTIMISATION : Lancer les 3 recherches en parallèle au lieu de séquentiellement
        # Gain estimé : 60-70% de réduction du temps de retrieval
        tasks = [
            self.vector_store.query_knowledge_base(
                query_text=query, n_results=self.top_k
            ),
            self.vector_store.query_user_documents(
                user_id=user_id, query_text=query, n_results=min(3, self.top_k)
            ),
            self.vector_store.query_user_history(
                user_id=user_id, query_text=query, n_results=2
            ),
        ]

        # Exécuter en parallèle avec gestion d'erreurs individuelles
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Traiter les résultats et gérer les exceptions
        law_results = results[0] if not isinstance(results[0], Exception) else []
        user_docs_results = results[1] if not isinstance(results[1], Exception) else []
        history_results = results[2] if not isinstance(results[2], Exception) else []

        # Logger les erreurs si nécessaire
        if isinstance(results[0], Exception):
            logger.warning(f"Erreur recherche lois: {results[0]}")
        if isinstance(results[1], Exception):
            logger.warning(f"Erreur recherche docs user: {results[1]}")
        if isinstance(results[2], Exception):
            logger.warning(f"Erreur recherche historique: {results[2]}")

        return law_results, user_docs_results, history_results

    def _filter_by_relevance(
        self, results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Filtre les résultats selon le seuil de pertinence

        Args:
            results: Résultats de recherche

        Returns:
            Résultats filtrés
        """
        filtered = []

        for result in results:
            relevance_score = result.get("relevance_score")

            if relevance_score is not None and relevance_score >= self.similarity_threshold:
                filtered.append(result)

        logger.debug(
            f"Filtrage: {len(results)} résultats -> {len(filtered)} retenus "
            f"(seuil: {self.similarity_threshold})"
        )

        return filtered

    async def _generate(
        self, query: str, context: str, history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """
        Génère la réponse avec le LLM

        Args:
            query: Question utilisateur
            context: Contexte récupéré
            history: Historique de conversation

        Returns:
            Réponse générée
        """
        # Construire le prompt complet
        prompt = build_rag_prompt(
            query=query,
            context=context,
            history=self._format_history(history) if history else "",
        )

        # Générer avec le LLM
        response = await self.llm.generate(prompt=prompt)

        return response

    async def _generate_stream(
        self, query: str, context: str, history: Optional[List[Dict[str, str]]] = None
    ) -> AsyncGenerator[str, None]:
        """
        Génère la réponse en mode streaming

        Args:
            query: Question utilisateur
            context: Contexte récupéré
            history: Historique

        Yields:
            Chunks de texte
        """
        prompt = build_rag_prompt(
            query=query,
            context=context,
            history=self._format_history(history) if history else "",
        )

        async for chunk in self.llm.generate_stream(prompt=prompt):
            yield chunk

    def _format_history(self, history: List[Dict[str, str]]) -> str:
        """
        Formate l'historique pour le prompt

        Args:
            history: Liste de messages

        Returns:
            Historique formaté
        """
        if not history:
            return ""

        formatted = []
        for msg in history[-5:]:  # Garder les 5 derniers
            role = msg.get("role", "user")
            content = msg.get("content", "")
            formatted.append(f"{role}: {content}")

        return "\n".join(formatted)

    def _format_sources(
        self, law_results: List[Dict], user_docs_results: List[Dict]
    ) -> List[Dict[str, Any]]:
        """
        Formate les sources pour l'affichage

        Args:
            law_results: Résultats de lois
            user_docs_results: Résultats de documents utilisateur

        Returns:
            Sources formatées
        """
        sources = []

        # Lois
        for result in law_results:
            metadata = result.get("metadata", {})
            sources.append(
                {
                    "type": "law",
                    "name": metadata.get("source", "Source inconnue"),
                    "article": metadata.get("article", ""),
                    "relevance_score": result.get("relevance_score", 0),
                    "excerpt": result.get("document", "")[:200] + "...",
                }
            )

        # Documents utilisateur
        for result in user_docs_results:
            metadata = result.get("metadata", {})
            sources.append(
                {
                    "type": "user_document",
                    "name": metadata.get("filename", "Document sans nom"),
                    "category": metadata.get("category", ""),
                    "relevance_score": result.get("relevance_score", 0),
                    "excerpt": result.get("document", "")[:200] + "...",
                }
            )

        return sources

    async def save_to_history(
        self, user_id: str, conversation_id: str, query: str, response: str
    ) -> bool:
        """
        Sauvegarde la conversation dans l'historique

        Args:
            user_id: ID utilisateur
            conversation_id: ID conversation
            query: Question
            response: Réponse

        Returns:
            True si sauvegardé
        """
        try:
            timestamp = datetime.utcnow().isoformat()

            # Sauvegarder question
            await self.vector_store.add_to_user_history(
                user_id=user_id,
                documents=[query],
                metadatas=[
                    {
                        "role": "user",
                        "conversation_id": conversation_id,
                        "timestamp": timestamp,
                    }
                ],
            )

            # Sauvegarder réponse
            await self.vector_store.add_to_user_history(
                user_id=user_id,
                documents=[response],
                metadatas=[
                    {
                        "role": "assistant",
                        "conversation_id": conversation_id,
                        "timestamp": timestamp,
                    }
                ],
            )

            logger.debug(f"Conversation sauvegardée dans l'historique : {conversation_id}")
            return True

        except Exception as e:
            logger.error(f"Erreur sauvegarde historique: {e}")
            return False

    async def classify_query(self, query: str) -> str:
        """
        Classifie une requête (juridique, hors-sujet, salutation, etc.)

        Args:
            query: Requête utilisateur

        Returns:
            Type de requête
        """
        # Classification simple basée sur des mots-clés
        query_lower = query.lower()

        # Salutations
        greetings = ["bonjour", "salut", "hello", "bonsoir", "hey"]
        if any(word in query_lower for word in greetings) and len(query.split()) < 5:
            return "greeting"

        # Mots-clés juridiques
        legal_keywords = [
            "article",
            "code",
            "loi",
            "jurisprudence",
            "contrat",
            "droit",
            "tribunal",
            "avocat",
            "procédure",
        ]
        if any(word in query_lower for word in legal_keywords):
            return "legal"

        # Par défaut, on considère que c'est juridique
        return "legal"


# Instance globale (singleton)
_rag_pipeline: Optional[RAGPipeline] = None


async def get_rag_pipeline() -> RAGPipeline:
    """
    Récupère l'instance globale du pipeline RAG

    Returns:
        Instance initialisée de RAGPipeline
    """
    global _rag_pipeline

    if _rag_pipeline is None:
        _rag_pipeline = RAGPipeline()
        await _rag_pipeline.initialize()

    return _rag_pipeline


__all__ = ["RAGPipeline", "get_rag_pipeline"]
