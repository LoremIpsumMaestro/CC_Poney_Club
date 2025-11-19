"""
Utilitaires de sécurité : hashing, JWT, validation
"""

from datetime import datetime, timedelta
from typing import Optional

import bcrypt
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config.settings import settings
from app.utils.logger import logger

# Context pour le hashing de mots de passe
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ============================================================================
# HASHING DE MOTS DE PASSE
# ============================================================================


def hash_password(password: str) -> str:
    """
    Hash un mot de passe avec bcrypt

    Args:
        password: Mot de passe en clair

    Returns:
        Hash du mot de passe
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Vérifie un mot de passe contre son hash

    Args:
        plain_password: Mot de passe en clair
        hashed_password: Hash à vérifier

    Returns:
        True si le mot de passe correspond
    """
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        logger.error(f"Erreur vérification password: {e}")
        return False


# ============================================================================
# JWT TOKENS
# ============================================================================


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Crée un JWT token

    Args:
        data: Données à encoder dans le token
        expires_delta: Durée de validité (optionnel)

    Returns:
        JWT token encodé
    """
    to_encode = data.copy()

    # Expiration
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.jwt_expiration_minutes)

    to_encode.update({"exp": expire})

    # Encoder le token
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.jwt_algorithm)

    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    """
    Décode et valide un JWT token

    Args:
        token: JWT token à décoder

    Returns:
        Payload du token ou None si invalide
    """
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
        return payload
    except JWTError as e:
        logger.warning(f"JWT invalide: {e}")
        return None


def validate_token(token: str) -> bool:
    """
    Vérifie si un token est valide

    Args:
        token: JWT token

    Returns:
        True si valide
    """
    return decode_access_token(token) is not None


# ============================================================================
# VALIDATION DE MOT DE PASSE
# ============================================================================


def validate_password_strength(password: str) -> tuple[bool, str]:
    """
    Vérifie la robustesse d'un mot de passe

    Args:
        password: Mot de passe à valider

    Returns:
        (is_valid, error_message)
    """
    if len(password) < settings.password_min_length:
        return False, f"Le mot de passe doit contenir au moins {settings.password_min_length} caractères"

    # Vérifications basiques
    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password)

    if not (has_upper and has_lower):
        return False, "Le mot de passe doit contenir des majuscules et minuscules"

    if not has_digit:
        return False, "Le mot de passe doit contenir au moins un chiffre"

    if not has_special:
        return (
            False,
            "Le mot de passe doit contenir au moins un caractère spécial (!@#$%^&*...)",
        )

    return True, ""


# ============================================================================
# SANITIZATION
# ============================================================================


def sanitize_input(text: str, max_length: int = 10000) -> str:
    """
    Nettoie un input utilisateur pour éviter les injections

    Args:
        text: Texte à nettoyer
        max_length: Longueur maximale

    Returns:
        Texte nettoyé
    """
    if not text:
        return ""

    # Tronquer si trop long
    text = text[:max_length]

    # Supprimer les caractères de contrôle dangereux
    # Garder les espaces, tabulations et retours à la ligne
    allowed_chars = set("\n\r\t")
    text = "".join(c for c in text if c.isprintable() or c in allowed_chars)

    # Supprimer les espaces multiples
    text = " ".join(text.split())

    return text.strip()


def sanitize_filename(filename: str) -> str:
    """
    Nettoie un nom de fichier

    Args:
        filename: Nom du fichier

    Returns:
        Nom nettoyé
    """
    # Caractères interdits dans les noms de fichiers
    forbidden_chars = '<>:"/\\|?*'

    for char in forbidden_chars:
        filename = filename.replace(char, "_")

    # Supprimer les espaces multiples
    filename = "_".join(filename.split())

    # Limiter la longueur
    max_length = 255
    if len(filename) > max_length:
        name, ext = filename.rsplit(".", 1) if "." in filename else (filename, "")
        name = name[: max_length - len(ext) - 1]
        filename = f"{name}.{ext}" if ext else name

    return filename


# ============================================================================
# VALIDATION D'EMAIL
# ============================================================================


def validate_email(email: str) -> bool:
    """
    Validation basique d'email

    Args:
        email: Email à valider

    Returns:
        True si valide
    """
    import re

    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))


# ============================================================================
# RATE LIMITING (simple)
# ============================================================================


class SimpleRateLimiter:
    """
    Rate limiter simple basé sur la mémoire
    Pour production, utiliser Redis
    """

    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: dict[str, list[datetime]] = {}

    def is_allowed(self, identifier: str) -> bool:
        """
        Vérifie si une requête est autorisée

        Args:
            identifier: Identifiant (user_id, IP, etc.)

        Returns:
            True si autorisé
        """
        now = datetime.utcnow()
        cutoff = now - timedelta(seconds=self.window_seconds)

        # Nettoyer les vieilles requêtes
        if identifier in self.requests:
            self.requests[identifier] = [
                req_time for req_time in self.requests[identifier] if req_time > cutoff
            ]
        else:
            self.requests[identifier] = []

        # Vérifier la limite
        if len(self.requests[identifier]) >= self.max_requests:
            return False

        # Ajouter la nouvelle requête
        self.requests[identifier].append(now)
        return True

    def reset(self, identifier: str) -> None:
        """Reset le compteur pour un identifier"""
        if identifier in self.requests:
            del self.requests[identifier]


# Instance globale des rate limiters
rate_limiter_minute = SimpleRateLimiter(
    max_requests=settings.rate_limit_per_minute, window_seconds=60
)
rate_limiter_hour = SimpleRateLimiter(
    max_requests=settings.rate_limit_per_hour, window_seconds=3600
)


__all__ = [
    "hash_password",
    "verify_password",
    "create_access_token",
    "decode_access_token",
    "validate_token",
    "validate_password_strength",
    "sanitize_input",
    "sanitize_filename",
    "validate_email",
    "SimpleRateLimiter",
    "rate_limiter_minute",
    "rate_limiter_hour",
]
