"""
Client Supabase pour toutes les interactions avec la base de données
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from supabase import Client, create_client

from app.config.settings import settings
from app.database.models import (
    ActionType,
    Conversation,
    ConversationCreate,
    ConversationSummary,
    ConversationUpdate,
    ConversationWithMessages,
    Document,
    DocumentCreate,
    DocumentUpdate,
    Message,
    MessageCreate,
    UsageLog,
    UsageLogCreate,
    UserProfile,
    UserProfileCreate,
    UserProfileUpdate,
    UserStatistics,
)
from app.utils.logger import logger


class SupabaseClient:
    """
    Client Supabase centralisé
    """

    def __init__(self, url: Optional[str] = None, key: Optional[str] = None):
        """
        Initialise le client Supabase

        Args:
            url: URL du projet Supabase
            key: Clé API Supabase
        """
        self.url = url or settings.supabase_url
        self.key = key or settings.supabase_key

        self.client: Optional[Client] = None

        logger.info(f"Initialisation SupabaseClient - URL: {self.url[:30]}...")

    def initialize(self):
        """Initialise la connexion"""
        try:
            if not self.url or not self.key:
                raise ValueError("SUPABASE_URL et SUPABASE_KEY requis")

            self.client = create_client(self.url, self.key)
            logger.info("Client Supabase initialisé")

        except Exception as e:
            logger.error(f"Erreur initialisation Supabase: {e}")
            raise

    # ========================================================================
    # AUTHENTIFICATION
    # ========================================================================

    def sign_up(self, email: str, password: str) -> Dict[str, Any]:
        """
        Inscription d'un utilisateur

        Args:
            email: Email
            password: Mot de passe

        Returns:
            Données utilisateur
        """
        try:
            response = self.client.auth.sign_up(
                {"email": email, "password": password}
            )

            logger.info(f"Utilisateur créé: {email}")
            return response

        except Exception as e:
            logger.error(f"Erreur sign_up: {e}")
            raise

    def sign_in(self, email: str, password: str) -> Dict[str, Any]:
        """
        Connexion d'un utilisateur

        Args:
            email: Email
            password: Mot de passe

        Returns:
            Session et token
        """
        try:
            response = self.client.auth.sign_in_with_password(
                {"email": email, "password": password}
            )

            logger.info(f"Utilisateur connecté: {email}")
            return response

        except Exception as e:
            logger.error(f"Erreur sign_in: {e}")
            raise

    def sign_out(self) -> None:
        """Déconnexion"""
        try:
            self.client.auth.sign_out()
            logger.info("Utilisateur déconnecté")

        except Exception as e:
            logger.error(f"Erreur sign_out: {e}")
            raise

    def get_current_user(self) -> Optional[Dict[str, Any]]:
        """Récupère l'utilisateur courant"""
        try:
            user = self.client.auth.get_user()
            return user

        except Exception as e:
            logger.error(f"Erreur get_current_user: {e}")
            return None

    # ========================================================================
    # PROFILS UTILISATEURS
    # ========================================================================

    def create_profile(self, profile: UserProfileCreate) -> UserProfile:
        """Crée un profil utilisateur"""
        try:
            data = {
                "id": str(profile.id),
                "full_name": profile.full_name,
                "law_firm": profile.law_firm,
                "role": profile.role.value,
            }

            response = self.client.table("profiles").insert(data).execute()

            logger.info(f"Profil créé: {profile.id}")
            return UserProfile(**response.data[0])

        except Exception as e:
            logger.error(f"Erreur create_profile: {e}")
            raise

    def get_profile(self, user_id: UUID) -> Optional[UserProfile]:
        """Récupère un profil"""
        try:
            response = (
                self.client.table("profiles")
                .select("*")
                .eq("id", str(user_id))
                .execute()
            )

            if response.data:
                return UserProfile(**response.data[0])
            return None

        except Exception as e:
            logger.error(f"Erreur get_profile: {e}")
            return None

    def update_profile(
        self, user_id: UUID, profile_update: UserProfileUpdate
    ) -> Optional[UserProfile]:
        """Met à jour un profil"""
        try:
            data = profile_update.model_dump(exclude_none=True)
            data["updated_at"] = datetime.utcnow().isoformat()

            response = (
                self.client.table("profiles")
                .update(data)
                .eq("id", str(user_id))
                .execute()
            )

            if response.data:
                logger.info(f"Profil mis à jour: {user_id}")
                return UserProfile(**response.data[0])
            return None

        except Exception as e:
            logger.error(f"Erreur update_profile: {e}")
            return None

    # ========================================================================
    # CONVERSATIONS
    # ========================================================================

    def create_conversation(
        self, conversation: ConversationCreate
    ) -> Conversation:
        """Crée une conversation"""
        try:
            data = {
                "user_id": str(conversation.user_id),
                "title": conversation.title,
            }

            response = self.client.table("conversations").insert(data).execute()

            logger.info(f"Conversation créée pour user {conversation.user_id}")
            return Conversation(**response.data[0])

        except Exception as e:
            logger.error(f"Erreur create_conversation: {e}")
            raise

    def get_conversation(self, conversation_id: UUID) -> Optional[Conversation]:
        """Récupère une conversation"""
        try:
            response = (
                self.client.table("conversations")
                .select("*")
                .eq("id", str(conversation_id))
                .execute()
            )

            if response.data:
                return Conversation(**response.data[0])
            return None

        except Exception as e:
            logger.error(f"Erreur get_conversation: {e}")
            return None

    def list_user_conversations(
        self, user_id: UUID, include_archived: bool = False
    ) -> List[ConversationSummary]:
        """Liste les conversations d'un utilisateur"""
        try:
            query = (
                self.client.table("conversations")
                .select("id, title, created_at")
                .eq("user_id", str(user_id))
                .order("updated_at", desc=True)
            )

            if not include_archived:
                query = query.eq("is_archived", False)

            response = query.execute()

            # Enrichir avec le nombre de messages
            summaries = []
            for conv in response.data:
                msg_count = self._count_messages(UUID(conv["id"]))
                last_msg = self._get_last_message(UUID(conv["id"]))

                summaries.append(
                    ConversationSummary(
                        id=conv["id"],
                        title=conv["title"],
                        message_count=msg_count,
                        last_message_at=last_msg.created_at if last_msg else None,
                        created_at=conv["created_at"],
                    )
                )

            return summaries

        except Exception as e:
            logger.error(f"Erreur list_user_conversations: {e}")
            return []

    def update_conversation(
        self, conversation_id: UUID, update: ConversationUpdate
    ) -> Optional[Conversation]:
        """Met à jour une conversation"""
        try:
            data = update.model_dump(exclude_none=True)
            data["updated_at"] = datetime.utcnow().isoformat()

            response = (
                self.client.table("conversations")
                .update(data)
                .eq("id", str(conversation_id))
                .execute()
            )

            if response.data:
                return Conversation(**response.data[0])
            return None

        except Exception as e:
            logger.error(f"Erreur update_conversation: {e}")
            return None

    def delete_conversation(self, conversation_id: UUID) -> bool:
        """Supprime une conversation (cascade sur les messages)"""
        try:
            self.client.table("conversations").delete().eq(
                "id", str(conversation_id)
            ).execute()

            logger.info(f"Conversation supprimée: {conversation_id}")
            return True

        except Exception as e:
            logger.error(f"Erreur delete_conversation: {e}")
            return False

    # ========================================================================
    # MESSAGES
    # ========================================================================

    def create_message(self, message: MessageCreate) -> Message:
        """Crée un message"""
        try:
            data = {
                "conversation_id": str(message.conversation_id),
                "user_id": str(message.user_id),
                "role": message.role.value,
                "content": message.content,
                "sources": message.sources,
            }

            response = self.client.table("messages").insert(data).execute()

            logger.debug(f"Message créé dans conversation {message.conversation_id}")
            return Message(**response.data[0])

        except Exception as e:
            logger.error(f"Erreur create_message: {e}")
            raise

    def get_conversation_messages(
        self, conversation_id: UUID, limit: int = 100
    ) -> List[Message]:
        """Récupère les messages d'une conversation"""
        try:
            response = (
                self.client.table("messages")
                .select("*")
                .eq("conversation_id", str(conversation_id))
                .order("created_at", desc=False)
                .limit(limit)
                .execute()
            )

            return [Message(**msg) for msg in response.data]

        except Exception as e:
            logger.error(f"Erreur get_conversation_messages: {e}")
            return []

    def _count_messages(self, conversation_id: UUID) -> int:
        """Compte les messages d'une conversation"""
        try:
            response = (
                self.client.table("messages")
                .select("id", count="exact")
                .eq("conversation_id", str(conversation_id))
                .execute()
            )

            return response.count or 0

        except Exception:
            return 0

    def _get_last_message(self, conversation_id: UUID) -> Optional[Message]:
        """Récupère le dernier message d'une conversation"""
        try:
            response = (
                self.client.table("messages")
                .select("*")
                .eq("conversation_id", str(conversation_id))
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )

            if response.data:
                return Message(**response.data[0])
            return None

        except Exception:
            return None

    # ========================================================================
    # DOCUMENTS
    # ========================================================================

    def create_document(self, document: DocumentCreate) -> Document:
        """Crée un document"""
        try:
            data = {
                "user_id": str(document.user_id),
                "filename": document.filename,
                "file_path": document.file_path,
                "file_size": document.file_size,
                "file_type": document.file_type,
                "category": document.category.value if document.category else None,
            }

            response = self.client.table("documents").insert(data).execute()

            logger.info(f"Document créé: {document.filename}")
            return Document(**response.data[0])

        except Exception as e:
            logger.error(f"Erreur create_document: {e}")
            raise

    def list_user_documents(self, user_id: UUID) -> List[Document]:
        """Liste les documents d'un utilisateur"""
        try:
            response = (
                self.client.table("documents")
                .select("*")
                .eq("user_id", str(user_id))
                .order("uploaded_at", desc=True)
                .execute()
            )

            return [Document(**doc) for doc in response.data]

        except Exception as e:
            logger.error(f"Erreur list_user_documents: {e}")
            return []

    def update_document(
        self, document_id: UUID, update: DocumentUpdate
    ) -> Optional[Document]:
        """Met à jour un document"""
        try:
            data = update.model_dump(exclude_none=True)
            if "category" in data and data["category"]:
                data["category"] = data["category"].value

            response = (
                self.client.table("documents")
                .update(data)
                .eq("id", str(document_id))
                .execute()
            )

            if response.data:
                return Document(**response.data[0])
            return None

        except Exception as e:
            logger.error(f"Erreur update_document: {e}")
            return None

    def delete_document(self, document_id: UUID) -> bool:
        """Supprime un document"""
        try:
            self.client.table("documents").delete().eq("id", str(document_id)).execute()

            logger.info(f"Document supprimé: {document_id}")
            return True

        except Exception as e:
            logger.error(f"Erreur delete_document: {e}")
            return False

    # ========================================================================
    # USAGE LOGS
    # ========================================================================

    def create_usage_log(self, log: UsageLogCreate) -> UsageLog:
        """Crée un log d'usage"""
        try:
            data = {
                "user_id": str(log.user_id),
                "action": log.action.value,
                "metadata": log.metadata,
            }

            response = self.client.table("usage_logs").insert(data).execute()

            return UsageLog(**response.data[0])

        except Exception as e:
            logger.error(f"Erreur create_usage_log: {e}")
            raise

    def get_user_statistics(self, user_id: UUID) -> UserStatistics:
        """Récupère les statistiques d'un utilisateur"""
        try:
            # Compter les conversations
            conv_response = (
                self.client.table("conversations")
                .select("id", count="exact")
                .eq("user_id", str(user_id))
                .execute()
            )

            # Compter les messages
            msg_response = (
                self.client.table("messages")
                .select("id", count="exact")
                .eq("user_id", str(user_id))
                .execute()
            )

            # Compter les documents
            doc_response = (
                self.client.table("documents")
                .select("id", count="exact")
                .eq("user_id", str(user_id))
                .execute()
            )

            # Compter les queries
            query_response = (
                self.client.table("usage_logs")
                .select("id", count="exact")
                .eq("user_id", str(user_id))
                .eq("action", ActionType.QUERY.value)
                .execute()
            )

            # Dernière activité
            last_log = (
                self.client.table("usage_logs")
                .select("created_at")
                .eq("user_id", str(user_id))
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )

            return UserStatistics(
                user_id=user_id,
                total_conversations=conv_response.count or 0,
                total_messages=msg_response.count or 0,
                total_documents=doc_response.count or 0,
                total_queries=query_response.count or 0,
                last_activity=(
                    last_log.data[0]["created_at"] if last_log.data else None
                ),
            )

        except Exception as e:
            logger.error(f"Erreur get_user_statistics: {e}")
            return UserStatistics(
                user_id=user_id,
                total_conversations=0,
                total_messages=0,
                total_documents=0,
                total_queries=0,
                last_activity=None,
            )

    # ========================================================================
    # RGPD - SUPPRESSION DONNÉES
    # ========================================================================

    def delete_all_user_data(self, user_id: UUID) -> bool:
        """
        Supprime toutes les données d'un utilisateur (RGPD)

        Args:
            user_id: ID utilisateur

        Returns:
            True si succès
        """
        try:
            # Supprimer les logs
            self.client.table("usage_logs").delete().eq(
                "user_id", str(user_id)
            ).execute()

            # Supprimer les documents
            self.client.table("documents").delete().eq(
                "user_id", str(user_id)
            ).execute()

            # Supprimer les conversations (cascade sur messages)
            self.client.table("conversations").delete().eq(
                "user_id", str(user_id)
            ).execute()

            # Supprimer le profil
            self.client.table("profiles").delete().eq("id", str(user_id)).execute()

            logger.info(f"Toutes les données supprimées pour user {user_id}")
            return True

        except Exception as e:
            logger.error(f"Erreur delete_all_user_data: {e}")
            return False


# Instance globale (singleton)
_supabase_client: Optional[SupabaseClient] = None


def get_supabase_client() -> SupabaseClient:
    """
    Récupère l'instance globale du client Supabase

    Returns:
        Instance initialisée de SupabaseClient
    """
    global _supabase_client

    if _supabase_client is None:
        _supabase_client = SupabaseClient()
        _supabase_client.initialize()

    return _supabase_client


__all__ = ["SupabaseClient", "get_supabase_client"]
