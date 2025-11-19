"""
Système de logging centralisé avec Loguru
"""

import sys
from pathlib import Path
from typing import Optional

from loguru import logger

from app.config.settings import settings


def setup_logger(
    log_level: Optional[str] = None,
    log_file: Optional[Path] = None,
) -> None:
    """
    Configure le logger global de l'application

    Args:
        log_level: Niveau de log (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Chemin du fichier de log
    """
    # Valeurs par défaut depuis settings
    log_level = log_level or settings.log_level
    log_file = log_file or settings.log_file_path

    # Supprimer le handler par défaut
    logger.remove()

    # Format pour la console (coloré)
    console_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )

    # Format pour le fichier (sans couleur)
    file_format = (
        "{time:YYYY-MM-DD HH:mm:ss} | "
        "{level: <8} | "
        "{name}:{function}:{line} | "
        "{message}"
    )

    # Handler console
    logger.add(
        sys.stderr,
        format=console_format,
        level=log_level,
        colorize=True,
        backtrace=True,
        diagnose=settings.debug,
    )

    # Handler fichier avec rotation
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        logger.add(
            log_file,
            format=file_format,
            level=log_level,
            rotation=settings.log_rotation,
            retention=settings.log_retention,
            compression="zip",
            backtrace=True,
            diagnose=False,  # Ne pas exposer les détails en prod
            enqueue=True,  # Thread-safe
        )

    logger.info(f"Logger configuré - Niveau: {log_level} - Fichier: {log_file}")


def log_user_action(user_id: str, action: str, details: Optional[dict] = None) -> None:
    """
    Log une action utilisateur (pour audit)

    Args:
        user_id: ID de l'utilisateur
        action: Type d'action
        details: Détails supplémentaires
    """
    log_message = f"USER_ACTION | user={user_id} | action={action}"
    if details:
        log_message += f" | details={details}"

    logger.info(log_message)


def log_llm_request(user_id: str, query: str, response_time: float) -> None:
    """
    Log une requête LLM (sans le contenu sensible)

    Args:
        user_id: ID de l'utilisateur
        query: Requête (tronquée)
        response_time: Temps de réponse en secondes
    """
    # Tronquer la query pour éviter les logs trop longs
    query_preview = query[:100] + "..." if len(query) > 100 else query

    logger.info(
        f"LLM_REQUEST | user={user_id} | "
        f"query_length={len(query)} | "
        f"response_time={response_time:.2f}s | "
        f"preview={query_preview}"
    )


def log_document_upload(user_id: str, filename: str, file_size: int, success: bool) -> None:
    """
    Log un upload de document

    Args:
        user_id: ID de l'utilisateur
        filename: Nom du fichier
        file_size: Taille en bytes
        success: Upload réussi ou non
    """
    status = "SUCCESS" if success else "FAILED"
    logger.info(
        f"DOCUMENT_UPLOAD | user={user_id} | "
        f"filename={filename} | "
        f"size={file_size} bytes | "
        f"status={status}"
    )


def log_vector_store_operation(operation: str, collection: str, duration: float) -> None:
    """
    Log une opération sur le vector store

    Args:
        operation: Type d'opération (query, insert, delete)
        collection: Nom de la collection
        duration: Durée en secondes
    """
    logger.debug(
        f"VECTOR_STORE | operation={operation} | "
        f"collection={collection} | "
        f"duration={duration:.3f}s"
    )


def log_error_with_context(
    error: Exception,
    context: str,
    user_id: Optional[str] = None,
    extra: Optional[dict] = None,
) -> None:
    """
    Log une erreur avec contexte détaillé

    Args:
        error: Exception levée
        context: Contexte de l'erreur
        user_id: ID utilisateur si applicable
        extra: Données supplémentaires
    """
    error_message = f"ERROR | context={context} | error={type(error).__name__}: {str(error)}"

    if user_id:
        error_message += f" | user={user_id}"

    if extra:
        error_message += f" | extra={extra}"

    logger.error(error_message)
    logger.exception(error)  # Stack trace complète


# Initialiser le logger au chargement du module
setup_logger()

# Export du logger configuré
__all__ = [
    "logger",
    "setup_logger",
    "log_user_action",
    "log_llm_request",
    "log_document_upload",
    "log_vector_store_operation",
    "log_error_with_context",
]
