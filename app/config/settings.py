"""
Configuration centralisée de Coda2z
Utilise pydantic-settings pour la validation et le chargement depuis .env
"""

from pathlib import Path
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration principale de l'application"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = Field(default="Coda2z", description="Nom de l'application")
    app_version: str = Field(default="1.0.0", description="Version")
    environment: str = Field(default="development", description="Environnement")
    debug: bool = Field(default=True, description="Mode debug")

    # Server
    host: str = Field(default="0.0.0.0", description="Host du serveur")
    port: int = Field(default=8501, description="Port Streamlit")
    api_port: int = Field(default=8000, description="Port FastAPI")

    # Supabase
    supabase_url: str = Field(default="", description="URL du projet Supabase")
    supabase_key: str = Field(default="", description="Clé anonyme Supabase")
    supabase_service_role_key: str = Field(default="", description="Clé service role")

    # Database
    database_url: Optional[str] = Field(default=None, description="URL PostgreSQL")

    # LLM Configuration
    llm_model_name: str = Field(default="qwen2.5:14b", description="Nom du modèle LLM")
    llm_base_url: str = Field(default="http://localhost:11434", description="URL de l'API LLM")
    llm_api_key: str = Field(default="", description="Clé API LLM")
    llm_temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="Température")
    llm_max_tokens: int = Field(default=2048, ge=1, description="Tokens max par réponse")
    llm_context_window: int = Field(default=4096, description="Fenêtre de contexte")

    # Embeddings
    embeddings_model_name: str = Field(
        default="snowflake-arctic-embed2", description="Modèle embeddings"
    )
    embeddings_base_url: str = Field(
        default="http://localhost:11434", description="URL API embeddings"
    )
    embeddings_dimension: int = Field(default=768, description="Dimension des vecteurs")

    # Vector Store
    vector_store_type: str = Field(default="chromadb", description="Type de vector store")
    vector_store_path: Path = Field(
        default=Path("./vector_stores"), description="Chemin de stockage"
    )
    vector_store_persist: bool = Field(default=True, description="Persistance activée")

    # ChromaDB
    chroma_host: str = Field(default="localhost", description="Host ChromaDB")
    chroma_port: int = Field(default=8000, description="Port ChromaDB")
    chroma_tenant: str = Field(default="default_tenant", description="Tenant ChromaDB")
    chroma_database: str = Field(default="default_database", description="Database ChromaDB")

    # RAG Configuration
    rag_top_k: int = Field(default=5, ge=1, le=20, description="Nombre de résultats")
    rag_similarity_threshold: float = Field(
        default=0.7, ge=0.0, le=1.0, description="Seuil de similarité"
    )
    rag_chunk_size: int = Field(default=1000, ge=100, description="Taille des chunks")
    rag_chunk_overlap: int = Field(default=200, ge=0, description="Overlap des chunks")
    rag_enable_reranking: bool = Field(default=False, description="Activer le reranking")

    # Security
    secret_key: str = Field(
        default="change-this-secret-key-in-production",
        description="Clé secrète pour JWT",
    )
    jwt_algorithm: str = Field(default="HS256", description="Algorithme JWT")
    jwt_expiration_minutes: int = Field(
        default=10080, description="Expiration JWT (minutes)"
    )  # 7 jours
    password_min_length: int = Field(default=8, description="Longueur min password")

    # File Upload
    max_upload_size_mb: int = Field(default=50, description="Taille max upload (MB)")
    allowed_extensions: str = Field(
        default=".pdf,.docx,.txt,.md,.xlsx,.csv,.json,.pptx",
        description="Extensions autorisées",
    )
    upload_dir: Path = Field(default=Path("./data/user_uploads"), description="Répertoire upload")

    # Logging
    log_level: str = Field(default="INFO", description="Niveau de log")
    log_file_path: Path = Field(default=Path("./logs/coda2z.log"), description="Fichier de log")
    log_rotation: str = Field(default="100 MB", description="Rotation des logs")
    log_retention: str = Field(default="30 days", description="Rétention des logs")

    # Rate Limiting
    rate_limit_per_minute: int = Field(default=20, description="Requêtes/minute")
    rate_limit_per_hour: int = Field(default=100, description="Requêtes/heure")

    # GDPR
    data_retention_days: int = Field(default=90, description="Rétention des données (jours)")
    auto_delete_old_conversations: bool = Field(
        default=True, description="Suppression auto conversations"
    )

    # Monitoring
    enable_usage_tracking: bool = Field(default=True, description="Tracking d'usage activé")
    enable_error_reporting: bool = Field(default=False, description="Reporting erreurs")
    sentry_dsn: str = Field(default="", description="Sentry DSN")

    # Azure (optionnel)
    azure_storage_connection_string: str = Field(default="", description="Azure Storage")
    azure_storage_container: str = Field(default="", description="Container Azure")

    # Redis (optionnel)
    redis_url: str = Field(default="", description="URL Redis")
    redis_cache_ttl: int = Field(default=3600, description="TTL cache Redis")

    @field_validator("vector_store_path", "upload_dir", "log_file_path")
    @classmethod
    def create_dirs(cls, v: Path) -> Path:
        """Crée les répertoires s'ils n'existent pas"""
        if v.suffix:  # C'est un fichier
            v.parent.mkdir(parents=True, exist_ok=True)
        else:  # C'est un répertoire
            v.mkdir(parents=True, exist_ok=True)
        return v

    @field_validator("allowed_extensions")
    @classmethod
    def parse_extensions(cls, v: str) -> list[str]:
        """Parse les extensions autorisées"""
        return [ext.strip() for ext in v.split(",")]

    @property
    def is_production(self) -> bool:
        """Vérifie si on est en production"""
        return self.environment.lower() == "production"

    @property
    def knowledge_base_path(self) -> Path:
        """Chemin de la base de connaissances commune"""
        return self.vector_store_path / "knowledge_base"

    @property
    def user_histories_path(self) -> Path:
        """Chemin des historiques utilisateurs"""
        return self.vector_store_path / "user_histories"

    def get_user_collection_name(self, user_id: str, collection_type: str = "history") -> str:
        """
        Génère le nom de collection pour un utilisateur

        Args:
            user_id: ID de l'utilisateur
            collection_type: Type de collection (history | documents)

        Returns:
            Nom de la collection (ex: user_123abc_history)
        """
        return f"user_{user_id}_{collection_type}"


# Instance globale des settings (singleton)
settings = Settings()


# Validation au chargement
def validate_settings():
    """Valide les settings critiques au démarrage"""
    errors = []

    # Vérifier Supabase en production
    if settings.is_production:
        if not settings.supabase_url:
            errors.append("SUPABASE_URL requis en production")
        if not settings.supabase_key:
            errors.append("SUPABASE_KEY requis en production")
        if settings.secret_key == "change-this-secret-key-in-production":
            errors.append("SECRET_KEY doit être changé en production")

    # Vérifier les URLs LLM
    if not settings.llm_base_url:
        errors.append("LLM_BASE_URL requis")

    if errors:
        raise ValueError(f"Erreurs de configuration : {', '.join(errors)}")


# Exécuter la validation si le module est importé directement
if __name__ != "__main__":
    try:
        validate_settings()
    except ValueError as e:
        if settings.environment == "production":
            raise
        # En développement, on log juste un warning
        print(f"⚠️  Warning: {e}")
