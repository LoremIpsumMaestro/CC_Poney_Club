"""
Validateurs pour les inputs utilisateurs
"""

from pathlib import Path
from typing import Optional

from app.config.settings import settings
from app.utils.logger import logger


# ============================================================================
# VALIDATION DE FICHIERS
# ============================================================================


def validate_file_extension(filename: str) -> tuple[bool, str]:
    """
    Vérifie si l'extension du fichier est autorisée

    Args:
        filename: Nom du fichier

    Returns:
        (is_valid, error_message)
    """
    file_ext = Path(filename).suffix.lower()

    if not file_ext:
        return False, "Le fichier n'a pas d'extension"

    allowed = settings.allowed_extensions
    if file_ext not in allowed:
        return False, f"Extension non autorisée. Extensions acceptées : {', '.join(allowed)}"

    return True, ""


def validate_file_size(file_size_bytes: int) -> tuple[bool, str]:
    """
    Vérifie la taille du fichier

    Args:
        file_size_bytes: Taille en bytes

    Returns:
        (is_valid, error_message)
    """
    max_size_bytes = settings.max_upload_size_mb * 1024 * 1024

    if file_size_bytes > max_size_bytes:
        max_size_mb = settings.max_upload_size_mb
        actual_size_mb = file_size_bytes / (1024 * 1024)
        return (
            False,
            f"Fichier trop volumineux ({actual_size_mb:.1f} MB). Taille max : {max_size_mb} MB",
        )

    if file_size_bytes == 0:
        return False, "Le fichier est vide"

    return True, ""


def validate_upload(filename: str, file_size_bytes: int) -> tuple[bool, str]:
    """
    Validation complète d'un fichier uploadé

    Args:
        filename: Nom du fichier
        file_size_bytes: Taille en bytes

    Returns:
        (is_valid, error_message)
    """
    # Vérifier l'extension
    valid_ext, error_ext = validate_file_extension(filename)
    if not valid_ext:
        return False, error_ext

    # Vérifier la taille
    valid_size, error_size = validate_file_size(file_size_bytes)
    if not valid_size:
        return False, error_size

    return True, ""


# ============================================================================
# VALIDATION DE REQUÊTES
# ============================================================================


def validate_query(query: str, min_length: int = 3, max_length: int = 5000) -> tuple[bool, str]:
    """
    Valide une requête utilisateur

    Args:
        query: Texte de la requête
        min_length: Longueur minimale
        max_length: Longueur maximale

    Returns:
        (is_valid, error_message)
    """
    if not query or not query.strip():
        return False, "La requête ne peut pas être vide"

    query_length = len(query.strip())

    if query_length < min_length:
        return False, f"La requête est trop courte (minimum {min_length} caractères)"

    if query_length > max_length:
        return False, f"La requête est trop longue (maximum {max_length} caractères)"

    return True, ""


def validate_user_id(user_id: str) -> tuple[bool, str]:
    """
    Valide un UUID utilisateur

    Args:
        user_id: ID utilisateur

    Returns:
        (is_valid, error_message)
    """
    import re

    uuid_pattern = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"

    if not user_id:
        return False, "User ID manquant"

    if not re.match(uuid_pattern, user_id.lower()):
        return False, "User ID invalide (format UUID attendu)"

    return True, ""


# ============================================================================
# VALIDATION DE CONVERSATION
# ============================================================================


def validate_conversation_title(title: str) -> tuple[bool, str]:
    """
    Valide un titre de conversation

    Args:
        title: Titre

    Returns:
        (is_valid, error_message)
    """
    if not title or not title.strip():
        return False, "Le titre ne peut pas être vide"

    if len(title) > 200:
        return False, "Le titre est trop long (maximum 200 caractères)"

    return True, ""


# ============================================================================
# VALIDATION DE DOCUMENT
# ============================================================================


def validate_document_category(category: str) -> tuple[bool, str]:
    """
    Valide une catégorie de document

    Args:
        category: Catégorie

    Returns:
        (is_valid, error_message)
    """
    valid_categories = [
        "contrat",
        "consultation",
        "jurisprudence",
        "code",
        "loi",
        "doctrine",
        "autre",
    ]

    if category not in valid_categories:
        return False, f"Catégorie invalide. Catégories valides : {', '.join(valid_categories)}"

    return True, ""


# ============================================================================
# VALIDATION DE METADATA
# ============================================================================


def validate_metadata(metadata: dict) -> tuple[bool, str]:
    """
    Valide un dictionnaire de métadonnées

    Args:
        metadata: Métadonnées à valider

    Returns:
        (is_valid, error_message)
    """
    if not isinstance(metadata, dict):
        return False, "Les métadonnées doivent être un dictionnaire"

    # Vérifier la taille
    import json

    try:
        metadata_json = json.dumps(metadata)
        if len(metadata_json) > 10000:  # 10KB max
            return False, "Les métadonnées sont trop volumineuses"
    except Exception as e:
        return False, f"Métadonnées non sérialisables : {e}"

    return True, ""


# ============================================================================
# VALIDATION DE CHUNKS
# ============================================================================


def validate_chunk_params(chunk_size: int, chunk_overlap: int) -> tuple[bool, str]:
    """
    Valide les paramètres de chunking

    Args:
        chunk_size: Taille des chunks
        chunk_overlap: Overlap entre chunks

    Returns:
        (is_valid, error_message)
    """
    if chunk_size < 100:
        return False, "chunk_size trop petit (minimum 100)"

    if chunk_size > 5000:
        return False, "chunk_size trop grand (maximum 5000)"

    if chunk_overlap < 0:
        return False, "chunk_overlap ne peut pas être négatif"

    if chunk_overlap >= chunk_size:
        return False, "chunk_overlap doit être inférieur à chunk_size"

    return True, ""


# ============================================================================
# VALIDATION GLOBALE
# ============================================================================


class ValidationError(Exception):
    """Exception levée lors d'une erreur de validation"""

    pass


def ensure_valid(validation_result: tuple[bool, str]) -> None:
    """
    Lève une exception si la validation échoue

    Args:
        validation_result: Tuple (is_valid, error_message)

    Raises:
        ValidationError: Si la validation échoue
    """
    is_valid, error_message = validation_result
    if not is_valid:
        raise ValidationError(error_message)


__all__ = [
    "validate_file_extension",
    "validate_file_size",
    "validate_upload",
    "validate_query",
    "validate_user_id",
    "validate_conversation_title",
    "validate_document_category",
    "validate_metadata",
    "validate_chunk_params",
    "ValidationError",
    "ensure_valid",
]
