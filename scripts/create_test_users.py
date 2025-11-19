"""
Script de création d'utilisateurs de test
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database.models import UserProfileCreate, UserRole
from app.database.supabase_client import get_supabase_client
from app.utils.logger import logger


async def create_test_users():
    """Crée des utilisateurs de test"""
    try:
        logger.info("🚀 Création d'utilisateurs de test...")

        client = get_supabase_client()

        # Utilisateur admin
        admin_email = "admin@coda2z.com"
        admin_password = "Admin123!@#"

        try:
            logger.info(f"Création admin: {admin_email}")
            auth_response = client.sign_up(admin_email, admin_password)

            if auth_response.user:
                # Créer le profil
                profile = UserProfileCreate(
                    id=auth_response.user.id,
                    full_name="Admin Coda2z",
                    law_firm="Coda2z SAS",
                    role=UserRole.ADMIN,
                )
                client.create_profile(profile)
                logger.info(f"✅ Admin créé: {admin_email}")

        except Exception as e:
            logger.warning(f"⚠️  Admin existe déjà ou erreur: {e}")

        # Utilisateur test
        user_email = "user@coda2z.com"
        user_password = "User123!@#"

        try:
            logger.info(f"Création user: {user_email}")
            auth_response = client.sign_up(user_email, user_password)

            if auth_response.user:
                profile = UserProfileCreate(
                    id=auth_response.user.id,
                    full_name="Jean Dupont",
                    law_firm="Cabinet Dupont & Associés",
                    role=UserRole.USER,
                )
                client.create_profile(profile)
                logger.info(f"✅ User créé: {user_email}")

        except Exception as e:
            logger.warning(f"⚠️  User existe déjà ou erreur: {e}")

        logger.info("\n📋 UTILISATEURS DE TEST:")
        logger.info("=" * 60)
        logger.info(f"Admin: {admin_email} / {admin_password}")
        logger.info(f"User:  {user_email} / {user_password}")
        logger.info("=" * 60)
        logger.info("\n⚠️  CHANGEZ CES MOTS DE PASSE EN PRODUCTION !")

        return True

    except Exception as e:
        logger.error(f"❌ Erreur: {e}")
        return False


if __name__ == "__main__":
    asyncio.run(create_test_users())
