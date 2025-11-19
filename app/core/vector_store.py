"""
Gestionnaire de Vector Store avec ChromaDB
Double store : base commune + historiques utilisateurs
"""

import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.config.settings import settings
from app.core.embeddings_handler import get_embeddings_handler
from app.utils.logger import log_vector_store_operation, logger


class VectorStoreManager:
    """
    Gère les interactions avec ChromaDB
    """

    def __init__(self, persist_directory: Optional[Path] = None):
        """
        Initialise le gestionnaire de vector store

        Args:
            persist_directory: Répertoire de persistance
        """
        self.persist_directory = persist_directory or settings.vector_store_path
        self.persist_directory.mkdir(parents=True, exist_ok=True)

        self.client: Optional[chromadb.Client] = None
        self.embeddings_handler = None

        logger.info(f"Initialisation VectorStoreManager - Path: {self.persist_directory}")

    async def initialize(self):
        """Initialise ChromaDB et le gestionnaire d'embeddings"""
        try:
            # Initialiser ChromaDB en mode persistant
            self.client = chromadb.PersistentClient(
                path=str(self.persist_directory),
                settings=ChromaSettings(
                    anonymized_telemetry=False,
                    allow_reset=True,
                ),
            )

            # Initialiser le gestionnaire d'embeddings
            self.embeddings_handler = await get_embeddings_handler()

            logger.info("ChromaDB initialisé avec succès")

        except Exception as e:
            logger.error(f"Erreur initialisation ChromaDB: {e}")
            raise

    def get_or_create_collection(
        self,
        collection_name: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> chromadb.Collection:
        """
        Récupère ou crée une collection

        Args:
            collection_name: Nom de la collection
            metadata: Métadonnées de la collection

        Returns:
            Collection ChromaDB
        """
        try:
            collection = self.client.get_or_create_collection(
                name=collection_name, metadata=metadata or {}
            )

            logger.debug(f"Collection '{collection_name}' récupérée/créée")
            return collection

        except Exception as e:
            logger.error(f"Erreur get_or_create_collection: {e}")
            raise

    async def add_documents(
        self,
        collection_name: str,
        documents: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None,
    ) -> List[str]:
        """
        Ajoute des documents à une collection

        Args:
            collection_name: Nom de la collection
            documents: Liste de textes
            metadatas: Métadonnées associées
            ids: IDs personnalisés (sinon auto-générés)

        Returns:
            Liste des IDs ajoutés
        """
        start_time = time.time()

        try:
            collection = self.get_or_create_collection(collection_name)

            # Générer les embeddings
            embeddings = await self.embeddings_handler.embed_texts(documents)

            # Générer des IDs si non fournis
            if ids is None:
                ids = [str(uuid4()) for _ in documents]

            # Ajouter à ChromaDB
            collection.add(
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas or [{}] * len(documents),
                ids=ids,
            )

            duration = time.time() - start_time
            log_vector_store_operation("add", collection_name, duration)

            logger.info(
                f"Ajouté {len(documents)} documents à '{collection_name}' en {duration:.2f}s"
            )

            return ids

        except Exception as e:
            logger.error(f"Erreur add_documents: {e}")
            raise

    async def query(
        self,
        collection_name: str,
        query_text: str,
        n_results: int = 5,
        where: Optional[Dict[str, Any]] = None,
        include: List[str] = None,
    ) -> Dict[str, Any]:
        """
        Recherche dans une collection

        Args:
            collection_name: Nom de la collection
            query_text: Texte de recherche
            n_results: Nombre de résultats
            where: Filtres sur les métadonnées
            include: Champs à inclure (documents, metadatas, distances)

        Returns:
            Résultats de la recherche
        """
        start_time = time.time()

        try:
            collection = self.get_or_create_collection(collection_name)

            # Générer l'embedding de la requête
            query_embedding = await self.embeddings_handler.embed_query(query_text)

            # Recherche
            include = include or ["documents", "metadatas", "distances"]

            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=where,
                include=include,
            )

            duration = time.time() - start_time
            log_vector_store_operation("query", collection_name, duration)

            # Formatter les résultats
            formatted_results = self._format_query_results(results)

            logger.debug(
                f"Query '{collection_name}' - {len(formatted_results)} résultats en {duration:.2f}s"
            )

            return formatted_results

        except Exception as e:
            logger.error(f"Erreur query: {e}")
            raise

    def _format_query_results(self, results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Formate les résultats de recherche ChromaDB

        Args:
            results: Résultats bruts de ChromaDB

        Returns:
            Liste de résultats formatés
        """
        formatted = []

        # ChromaDB retourne des listes de listes
        ids = results.get("ids", [[]])[0]
        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        for i in range(len(ids)):
            formatted.append(
                {
                    "id": ids[i],
                    "document": documents[i],
                    "metadata": metadatas[i] if metadatas else {},
                    "distance": distances[i] if distances else None,
                    "relevance_score": 1 - distances[i] if distances else None,  # Similarité
                }
            )

        return formatted

    def delete_documents(
        self,
        collection_name: str,
        ids: Optional[List[str]] = None,
        where: Optional[Dict[str, Any]] = None,
    ) -> int:
        """
        Supprime des documents d'une collection

        Args:
            collection_name: Nom de la collection
            ids: IDs à supprimer
            where: Filtre sur métadonnées

        Returns:
            Nombre de documents supprimés
        """
        try:
            collection = self.get_or_create_collection(collection_name)

            # Obtenir le nombre avant suppression
            count_before = collection.count()

            # Supprimer
            collection.delete(ids=ids, where=where)

            count_after = collection.count()
            deleted = count_before - count_after

            logger.info(f"Supprimé {deleted} documents de '{collection_name}'")
            return deleted

        except Exception as e:
            logger.error(f"Erreur delete_documents: {e}")
            raise

    def delete_collection(self, collection_name: str) -> bool:
        """
        Supprime une collection entière

        Args:
            collection_name: Nom de la collection

        Returns:
            True si supprimé
        """
        try:
            self.client.delete_collection(name=collection_name)
            logger.info(f"Collection '{collection_name}' supprimée")
            return True

        except Exception as e:
            logger.error(f"Erreur delete_collection: {e}")
            return False

    def list_collections(self) -> List[str]:
        """
        Liste toutes les collections

        Returns:
            Noms des collections
        """
        try:
            collections = self.client.list_collections()
            names = [col.name for col in collections]
            logger.debug(f"Collections trouvées: {names}")
            return names

        except Exception as e:
            logger.error(f"Erreur list_collections: {e}")
            return []

    def get_collection_stats(self, collection_name: str) -> Dict[str, Any]:
        """
        Récupère les statistiques d'une collection

        Args:
            collection_name: Nom de la collection

        Returns:
            Statistiques
        """
        try:
            collection = self.get_or_create_collection(collection_name)

            stats = {
                "name": collection_name,
                "count": collection.count(),
                "metadata": collection.metadata,
            }

            return stats

        except Exception as e:
            logger.error(f"Erreur get_collection_stats: {e}")
            return {}

    # ============================================================================
    # MÉTHODES SPÉCIFIQUES CODA2Z
    # ============================================================================

    async def add_to_knowledge_base(
        self,
        documents: List[str],
        metadatas: List[Dict[str, Any]],
    ) -> List[str]:
        """
        Ajoute des documents à la base de connaissances commune

        Args:
            documents: Liste de textes
            metadatas: Métadonnées (source, article, etc.)

        Returns:
            IDs ajoutés
        """
        return await self.add_documents(
            collection_name="french_laws", documents=documents, metadatas=metadatas
        )

    async def add_to_user_history(
        self,
        user_id: str,
        documents: List[str],
        metadatas: List[Dict[str, Any]],
    ) -> List[str]:
        """
        Ajoute des messages à l'historique d'un utilisateur

        Args:
            user_id: ID utilisateur
            documents: Messages
            metadatas: Métadonnées (timestamp, role, etc.)

        Returns:
            IDs ajoutés
        """
        collection_name = settings.get_user_collection_name(user_id, "history")

        # Ajouter user_id dans les métadonnées pour sécurité
        for metadata in metadatas:
            metadata["user_id"] = user_id

        return await self.add_documents(
            collection_name=collection_name, documents=documents, metadatas=metadatas
        )

    async def add_user_document(
        self,
        user_id: str,
        document: str,
        metadata: Dict[str, Any],
    ) -> str:
        """
        Ajoute un document privé d'un utilisateur

        Args:
            user_id: ID utilisateur
            document: Contenu du document
            metadata: Métadonnées (filename, category, etc.)

        Returns:
            ID du document ajouté
        """
        collection_name = settings.get_user_collection_name(user_id, "documents")

        metadata["user_id"] = user_id

        ids = await self.add_documents(
            collection_name=collection_name, documents=[document], metadatas=[metadata]
        )

        return ids[0]

    async def query_knowledge_base(
        self, query_text: str, n_results: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Recherche dans la base de connaissances commune

        Args:
            query_text: Requête
            n_results: Nombre de résultats

        Returns:
            Résultats formatés
        """
        results = await self.query(
            collection_name="french_laws", query_text=query_text, n_results=n_results
        )
        return results

    async def query_user_history(
        self, user_id: str, query_text: str, n_results: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Recherche dans l'historique d'un utilisateur

        Args:
            user_id: ID utilisateur
            query_text: Requête
            n_results: Nombre de résultats

        Returns:
            Résultats formatés
        """
        collection_name = settings.get_user_collection_name(user_id, "history")

        results = await self.query(
            collection_name=collection_name,
            query_text=query_text,
            n_results=n_results,
            where={"user_id": user_id},  # Filtre de sécurité
        )

        return results

    async def query_user_documents(
        self, user_id: str, query_text: str, n_results: int = 2
    ) -> List[Dict[str, Any]]:
        """
        Recherche dans les documents privés d'un utilisateur

        Args:
            user_id: ID utilisateur
            query_text: Requête
            n_results: Nombre de résultats

        Returns:
            Résultats formatés
        """
        collection_name = settings.get_user_collection_name(user_id, "documents")

        results = await self.query(
            collection_name=collection_name,
            query_text=query_text,
            n_results=n_results,
            where={"user_id": user_id},
        )

        return results

    def delete_user_data(self, user_id: str) -> Dict[str, bool]:
        """
        Supprime toutes les données d'un utilisateur (RGPD)

        Args:
            user_id: ID utilisateur

        Returns:
            Statut de suppression par type
        """
        results = {}

        # Supprimer l'historique
        history_collection = settings.get_user_collection_name(user_id, "history")
        results["history"] = self.delete_collection(history_collection)

        # Supprimer les documents
        docs_collection = settings.get_user_collection_name(user_id, "documents")
        results["documents"] = self.delete_collection(docs_collection)

        logger.info(f"Données utilisateur {user_id} supprimées : {results}")
        return results


# Instance globale (singleton)
_vector_store_manager: Optional[VectorStoreManager] = None


async def get_vector_store() -> VectorStoreManager:
    """
    Récupère l'instance globale du gestionnaire de vector store

    Returns:
        Instance initialisée de VectorStoreManager
    """
    global _vector_store_manager

    if _vector_store_manager is None:
        _vector_store_manager = VectorStoreManager()
        await _vector_store_manager.initialize()

    return _vector_store_manager


__all__ = ["VectorStoreManager", "get_vector_store"]
