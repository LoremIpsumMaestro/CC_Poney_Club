"""
Composant sidebar réutilisable pour toutes les pages
"""

import streamlit as st
from app.components.auth_guard import check_authentication, show_user_info


def render_sidebar():
    """
    Affiche la sidebar avec navigation et infos utilisateur
    """
    with st.sidebar:
        # Logo et titre
        st.title("⚖️ Coda2z")
        st.caption("Assistant Juridique IA")

        st.divider()

        # Navigation principale
        st.subheader("📚 Navigation")

        # Si authentifié, afficher toutes les pages
        if check_authentication():
            pages = {
                "💬 Chat": "pages/1_💬_Chat.py",
                "📄 Mes Documents": "pages/3_📄_Mes_Documents.py",
                "⚙️ Paramètres": "pages/4_⚙️_Parametres.py",
            }

            # Page admin (si admin)
            from app.components.auth_guard import get_current_user_profile

            profile = get_current_user_profile()
            if profile and profile.role == "admin":
                pages["📚 Base de Connaissance"] = "pages/2_📚_Base_Connaissance.py"

            for label, page in pages.items():
                st.page_link(page, label=label)

        else:
            st.info("Connectez-vous pour accéder aux fonctionnalités")

        # Infos utilisateur
        show_user_info()

        # Footer
        st.divider()
        st.caption("🇫🇷 Coda2z V1.0")
        st.caption("© 2024 - Confidentiel")


__all__ = ["render_sidebar"]
