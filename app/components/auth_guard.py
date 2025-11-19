"""
Composant de protection des pages avec authentification
"""

import streamlit as st
from typing import Optional
from uuid import UUID

from app.database.supabase_client import get_supabase_client
from app.database.models import UserProfile
from app.utils.logger import logger


def init_session_state():
    """Initialise les variables de session Streamlit"""
    if "user" not in st.session_state:
        st.session_state.user = None
    if "user_profile" not in st.session_state:
        st.session_state.user_profile = None
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "access_token" not in st.session_state:
        st.session_state.access_token = None


def check_authentication() -> bool:
    """
    Vérifie si l'utilisateur est authentifié

    Returns:
        True si authentifié
    """
    init_session_state()
    return st.session_state.authenticated


def get_current_user() -> Optional[dict]:
    """
    Récupère l'utilisateur courant

    Returns:
        Données utilisateur ou None
    """
    return st.session_state.user


def get_current_user_profile() -> Optional[UserProfile]:
    """
    Récupère le profil de l'utilisateur courant

    Returns:
        Profil utilisateur ou None
    """
    return st.session_state.user_profile


def login(email: str, password: str) -> tuple[bool, str]:
    """
    Connecte un utilisateur

    Args:
        email: Email de l'utilisateur
        password: Mot de passe

    Returns:
        (success, message)
    """
    try:
        client = get_supabase_client()

        # Authentification Supabase
        response = client.sign_in(email, password)

        if response and "user" in response:
            # Stocker les infos dans la session
            st.session_state.user = response["user"]
            st.session_state.authenticated = True

            if "session" in response and "access_token" in response["session"]:
                st.session_state.access_token = response["session"]["access_token"]

            # Récupérer le profil
            try:
                user_id = UUID(response["user"]["id"])
                profile = client.get_profile(user_id)
                st.session_state.user_profile = profile
            except Exception as e:
                logger.warning(f"Impossible de récupérer le profil: {e}")

            logger.info(f"Connexion réussie: {email}")
            return True, "Connexion réussie !"
        else:
            return False, "Email ou mot de passe incorrect"

    except Exception as e:
        logger.error(f"Erreur login: {e}")
        return False, f"Erreur de connexion: {str(e)}"


def logout():
    """Déconnecte l'utilisateur"""
    try:
        client = get_supabase_client()
        client.sign_out()
    except Exception as e:
        logger.error(f"Erreur logout: {e}")
    finally:
        # Nettoyer la session
        st.session_state.user = None
        st.session_state.user_profile = None
        st.session_state.authenticated = False
        st.session_state.access_token = None
        logger.info("Déconnexion réussie")


def require_authentication(admin_only: bool = False) -> bool:
    """
    Décore une page pour requérir l'authentification

    Args:
        admin_only: Si True, seuls les admins peuvent accéder

    Returns:
        True si l'utilisateur peut accéder à la page
    """
    init_session_state()

    if not check_authentication():
        st.warning("⚠️ Vous devez être connecté pour accéder à cette page.")

        # Afficher un formulaire de connexion minimal
        with st.form("login_form"):
            email = st.text_input("Email", key="login_email")
            password = st.text_input("Password", type="password", key="login_password")
            submit = st.form_submit_button("Se connecter")

            if submit:
                success, message = login(email, password)
                if success:
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)

        st.stop()
        return False

    # Vérifier si admin requis
    if admin_only:
        profile = get_current_user_profile()
        if not profile or profile.role != "admin":
            st.error("🚫 Accès réservé aux administrateurs")
            st.stop()
            return False

    return True


def show_login_page():
    """
    Affiche la page de connexion complète
    """
    st.title("🔐 Connexion à Coda2z")

    st.markdown("""
    Bienvenue sur **Coda2z**, votre assistant juridique intelligent.

    Connectez-vous pour accéder à vos conversations et documents.
    """)

    # Tabs pour Login / Register
    tab_login, tab_register = st.tabs(["Se connecter", "Créer un compte"])

    with tab_login:
        st.subheader("Connexion")

        with st.form("login_form_full"):
            email = st.text_input("Email professionnel", key="full_login_email")
            password = st.text_input("Mot de passe", type="password", key="full_login_password")
            remember_me = st.checkbox("Se souvenir de moi")

            col1, col2 = st.columns(2)
            with col1:
                submit = st.form_submit_button("Se connecter", use_container_width=True)
            with col2:
                forgot = st.form_submit_button("Mot de passe oublié ?", use_container_width=True)

            if submit:
                if not email or not password:
                    st.error("Veuillez remplir tous les champs")
                else:
                    success, message = login(email, password)
                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)

            if forgot:
                st.info("Contactez votre administrateur pour réinitialiser votre mot de passe.")

    with tab_register:
        st.subheader("Créer un compte")
        st.info("📧 Contactez votre administrateur pour obtenir un accès à Coda2z.")

        st.markdown("""
        Pour créer un compte :
        1. Contactez l'administrateur de votre cabinet
        2. Fournissez votre email professionnel
        3. Recevez vos identifiants par email sécurisé
        """)


def show_user_info():
    """
    Affiche les informations de l'utilisateur connecté dans la sidebar
    """
    if check_authentication():
        user = get_current_user()
        profile = get_current_user_profile()

        st.sidebar.divider()
        st.sidebar.subheader("👤 Profil")

        if profile:
            st.sidebar.write(f"**{profile.full_name}**")
            if profile.law_firm:
                st.sidebar.caption(f"📁 {profile.law_firm}")
            st.sidebar.caption(f"🔑 {profile.role.capitalize()}")
        elif user:
            st.sidebar.write(f"**{user.get('email', 'Utilisateur')}**")

        if st.sidebar.button("🚪 Se déconnecter", use_container_width=True):
            logout()
            st.rerun()


__all__ = [
    "init_session_state",
    "check_authentication",
    "get_current_user",
    "get_current_user_profile",
    "login",
    "logout",
    "require_authentication",
    "show_login_page",
    "show_user_info",
]
