"""
Point d'entrée principal de l'application Coda2z
Page d'accueil et de connexion
"""

import streamlit as st
from app.components.auth_guard import (
    init_session_state,
    check_authentication,
    show_login_page,
)
from app.components.sidebar import render_sidebar
from app.config.settings import settings

# Configuration de la page
st.set_page_config(
    page_title="Coda2z - Assistant Juridique IA",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "Get Help": "https://docs.coda2z.com",
        "Report a bug": "https://github.com/votre-org/coda2z/issues",
        "About": "Coda2z V1.0 - Assistant juridique intelligent pour avocats français",
    },
)

# CSS personnalisé
st.markdown(
    """
    <style>
    /* Style général */
    .main {
        padding: 2rem;
    }

    /* Style des titres */
    h1 {
        color: #1f2937;
        font-weight: 700;
    }

    h2 {
        color: #374151;
        font-weight: 600;
    }

    /* Style des cards */
    .feature-card {
        background: white;
        padding: 1.5rem;
        border-radius: 0.5rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        margin-bottom: 1rem;
    }

    /* Style des boutons */
    .stButton > button {
        width: 100%;
        border-radius: 0.375rem;
        font-weight: 500;
    }

    /* Style des inputs */
    .stTextInput > div > div > input {
        border-radius: 0.375rem;
    }

    /* Style de la sidebar */
    [data-testid="stSidebar"] {
        background-color: #f9fafb;
    }

    /* Messages d'info */
    .stAlert {
        border-radius: 0.375rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Initialiser la session
init_session_state()

# Afficher la sidebar
render_sidebar()

# Contenu principal
def main():
    """Fonction principale"""

    # Si déjà authentifié, afficher la page d'accueil
    if check_authentication():
        show_home_page()
    else:
        # Sinon, afficher la page de connexion
        show_login_page()


def show_home_page():
    """Affiche la page d'accueil pour les utilisateurs connectés"""

    from app.components.auth_guard import get_current_user_profile

    profile = get_current_user_profile()

    # Header
    st.title("⚖️ Bienvenue sur Coda2z")

    if profile:
        st.subheader(f"Bonjour {profile.full_name} 👋")
    else:
        st.subheader("Bonjour 👋")

    st.markdown("---")

    # Présentation
    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("""
        ### 🤖 Votre assistant juridique intelligent

        Coda2z vous aide dans vos recherches juridiques et l'analyse de documents
        grâce à l'intelligence artificielle.

        #### ✨ Fonctionnalités principales

        💬 **Chat Intelligent**
        - Posez vos questions juridiques en langage naturel
        - Obtenez des réponses contextualisées avec citations des sources
        - Historique de vos conversations sauvegardé

        📄 **Gestion de Documents**
        - Uploadez vos documents privés (contrats, consultations, etc.)
        - Indexation automatique pour recherche instantanée
        - Isolation stricte de vos données

        🔍 **Recherche Juridique**
        - Accès à la base de lois françaises
        - Recherche sémantique avancée
        - Sources officielles et à jour
        """)

        # Bouton d'action principal
        if st.button("💬 Commencer une conversation", type="primary", use_container_width=True):
            st.switch_page("pages/1_💬_Chat.py")

    with col2:
        # Statistiques rapides
        st.info("""
        **📊 Statistiques**

        Base de connaissances :
        - 10 codes français
        - ~2.6 GB de données juridiques
        - Mise à jour régulière

        Votre utilisation :
        - Voir vos statistiques dans **Paramètres**
        """)

        # Liens rapides
        st.success("""
        **🔗 Liens rapides**

        - [Légifrance](https://www.legifrance.gouv.fr/)
        - [Documentation](https://docs.coda2z.com)
        - [Support](mailto:support@coda2z.com)
        """)

    st.markdown("---")

    # Fonctionnalités détaillées
    st.subheader("🎯 Comment utiliser Coda2z")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("""
        #### 1️⃣ Posez vos questions

        Utilisez le **Chat** pour poser vos questions juridiques :
        - "Qu'est-ce que l'article 1240 du code civil ?"
        - "Comment rédiger une clause de non-concurrence ?"
        - "Quelles sont les sanctions en cas de diffamation ?"

        L'IA recherchera automatiquement dans la base de lois
        et vos documents privés pour vous fournir une réponse
        complète et sourcée.
        """)

    with col2:
        st.markdown("""
        #### 2️⃣ Uploadez vos documents

        Dans **Mes Documents**, importez vos fichiers :
        - Contrats clients
        - Consultations juridiques
        - Notes de recherche
        - Jurisprudence

        Formats supportés : PDF, DOCX, TXT, MD, XLSX, CSV

        Vos documents restent **strictement privés** et isolés.
        """)

    with col3:
        st.markdown("""
        #### 3️⃣ Gérez votre compte

        Dans **Paramètres** :
        - Consultez vos statistiques d'usage
        - Gérez vos conversations
        - Exportez vos données (RGPD)
        - Supprimez votre historique

        Toutes vos données sont **chiffrées** et **sécurisées**.
        """)

    st.markdown("---")

    # Avertissements légaux
    st.warning("""
    ⚠️ **Important**

    Coda2z est un outil d'assistance à la recherche juridique.
    Il **ne remplace pas** l'analyse d'un avocat qualifié et ne peut être utilisé
    comme unique source pour des décisions juridiques importantes.

    Les réponses fournies sont basées sur les données disponibles dans la base
    de connaissances et peuvent nécessiter une vérification complémentaire.
    """)

    # Footer
    st.caption(f"""
    🔒 **Confidentialité** : Vos données sont hébergées en France et respectent le RGPD.
    Aucune conversation n'est partagée avec des tiers.

    Version : {settings.app_version} | Environnement : {settings.environment}
    """)


if __name__ == "__main__":
    main()
