"""
Modèles de données pour Supabase
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


# ============================================================================
# ENUMS
# ============================================================================


class UserRole(str, Enum):
    """Rôles utilisateurs"""

    USER = "user"
    ADMIN = "admin"


class MessageRole(str, Enum):
    """Rôles des messages"""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class DocumentCategory(str, Enum):
    """Catégories de documents"""

    CONTRAT = "contrat"
    CONSULTATION = "consultation"
    JURISPRUDENCE = "jurisprudence"
    CODE = "code"
    LOI = "loi"
    DOCTRINE = "doctrine"
    AUTRE = "autre"


class ActionType(str, Enum):
    """Types d'actions pour les logs"""

    QUERY = "query"
    UPLOAD = "upload"
    DELETE = "delete"
    LOGIN = "login"
    LOGOUT = "logout"
    CREATE_CONVERSATION = "create_conversation"


# ============================================================================
# MODÈLES DE BASE
# ============================================================================


class UserProfile(BaseModel):
    """Profil utilisateur étendu"""

    id: UUID
    full_name: str = Field(..., min_length=1, max_length=200)
    law_firm: Optional[str] = Field(None, max_length=200)
    role: UserRole = UserRole.USER
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class Conversation(BaseModel):
    """Conversation entre user et assistant"""

    id: UUID
    user_id: UUID
    title: str = Field(default="Nouvelle conversation", max_length=200)
    created_at: datetime
    updated_at: datetime
    is_archived: bool = False

    class Config:
        from_attributes = True


class Message(BaseModel):
    """Message dans une conversation"""

    id: UUID
    conversation_id: UUID
    user_id: UUID
    role: MessageRole
    content: str = Field(..., min_length=1)
    sources: Optional[List[Dict[str, Any]]] = None
    created_at: datetime

    class Config:
        from_attributes = True


class Document(BaseModel):
    """Document uploadé par un utilisateur"""

    id: UUID
    user_id: UUID
    filename: str = Field(..., min_length=1, max_length=255)
    file_path: str
    file_size: int = Field(..., ge=0)
    file_type: str
    category: Optional[DocumentCategory] = None
    vector_store_id: Optional[str] = None
    uploaded_at: datetime
    indexed_at: Optional[datetime] = None

    @field_validator("file_size")
    @classmethod
    def validate_file_size(cls, v):
        """Valide la taille du fichier"""
        max_size = 50 * 1024 * 1024  # 50 MB
        if v > max_size:
            raise ValueError(f"Fichier trop volumineux (max {max_size} bytes)")
        return v

    class Config:
        from_attributes = True


class UsageLog(BaseModel):
    """Log d'utilisation"""

    id: UUID
    user_id: UUID
    action: ActionType
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# MODÈLES DE CRÉATION (sans ID/timestamps auto-générés)
# ============================================================================


class UserProfileCreate(BaseModel):
    """Création d'un profil utilisateur"""

    id: UUID  # Vient de Supabase Auth
    full_name: str = Field(..., min_length=1, max_length=200)
    law_firm: Optional[str] = Field(None, max_length=200)
    role: UserRole = UserRole.USER


class ConversationCreate(BaseModel):
    """Création d'une conversation"""

    user_id: UUID
    title: str = Field(default="Nouvelle conversation", max_length=200)


class MessageCreate(BaseModel):
    """Création d'un message"""

    conversation_id: UUID
    user_id: UUID
    role: MessageRole
    content: str = Field(..., min_length=1)
    sources: Optional[List[Dict[str, Any]]] = None


class DocumentCreate(BaseModel):
    """Création d'un document"""

    user_id: UUID
    filename: str = Field(..., min_length=1, max_length=255)
    file_path: str
    file_size: int = Field(..., ge=0)
    file_type: str
    category: Optional[DocumentCategory] = None


class UsageLogCreate(BaseModel):
    """Création d'un log d'usage"""

    user_id: UUID
    action: ActionType
    metadata: Optional[Dict[str, Any]] = None


# ============================================================================
# MODÈLES DE MISE À JOUR
# ============================================================================


class UserProfileUpdate(BaseModel):
    """Mise à jour d'un profil utilisateur"""

    full_name: Optional[str] = Field(None, min_length=1, max_length=200)
    law_firm: Optional[str] = Field(None, max_length=200)


class ConversationUpdate(BaseModel):
    """Mise à jour d'une conversation"""

    title: Optional[str] = Field(None, max_length=200)
    is_archived: Optional[bool] = None


class DocumentUpdate(BaseModel):
    """Mise à jour d'un document"""

    category: Optional[DocumentCategory] = None
    vector_store_id: Optional[str] = None
    indexed_at: Optional[datetime] = None


# ============================================================================
# MODÈLES DE RÉPONSE ENRICHIS
# ============================================================================


class ConversationWithMessages(Conversation):
    """Conversation avec ses messages"""

    messages: List[Message] = []


class ConversationSummary(BaseModel):
    """Résumé d'une conversation"""

    id: UUID
    title: str
    message_count: int
    last_message_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class UserStatistics(BaseModel):
    """Statistiques d'un utilisateur"""

    user_id: UUID
    total_conversations: int
    total_messages: int
    total_documents: int
    total_queries: int
    last_activity: Optional[datetime]


# ============================================================================
# MODÈLES D'AUTHENTIFICATION
# ============================================================================


class UserLogin(BaseModel):
    """Login utilisateur"""

    email: str = Field(..., pattern=r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
    password: str = Field(..., min_length=8)


class UserRegister(BaseModel):
    """Enregistrement utilisateur"""

    email: str = Field(..., pattern=r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
    password: str = Field(..., min_length=8)
    full_name: str = Field(..., min_length=1, max_length=200)
    law_firm: Optional[str] = Field(None, max_length=200)


class AuthToken(BaseModel):
    """Token d'authentification"""

    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user_id: UUID


__all__ = [
    # Enums
    "UserRole",
    "MessageRole",
    "DocumentCategory",
    "ActionType",
    # Modèles principaux
    "UserProfile",
    "Conversation",
    "Message",
    "Document",
    "UsageLog",
    # Création
    "UserProfileCreate",
    "ConversationCreate",
    "MessageCreate",
    "DocumentCreate",
    "UsageLogCreate",
    # Mise à jour
    "UserProfileUpdate",
    "ConversationUpdate",
    "DocumentUpdate",
    # Réponses enrichies
    "ConversationWithMessages",
    "ConversationSummary",
    "UserStatistics",
    # Auth
    "UserLogin",
    "UserRegister",
    "AuthToken",
]
