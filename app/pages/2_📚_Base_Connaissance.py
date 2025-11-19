"""
Page de gestion de la base de connaissances commune (Admin uniquement)
Upload et gestion des lois françaises et documents juridiques communs
"""

import streamlit as st
import asyncio
from pathlib import Path

from app.components.auth_guard import require_authentication, get_current_user
from app.components.sidebar import render_sidebar
from app.components.file_uploader import render_file_uploader
from app.core.vector_store import get_vector_store
from app.utils.logger import logger

# Configuration
st.set_page_config(
    page_title="Base de Connaissance - Coda2z",
    page_icon="📚",
    layout="wide",
)

# Authentification ADMIN UNIQUEMENT
if not require_authentication(admin_only=True):
    st.stop()

# Sidebar
render_sidebar()

# User
user = get_current_user()
user_id = user["id"] if user else None

# Titre
st.title("📚 Base de Connaissance Commune")

st.warning("""
⚠️ **Page administrateur**

Cette page permet de gérer la base de connaissances commune accessible à tous les utilisateurs.

**Attention** : Les documents ajoutés ici seront visibles par tous.
""")

st.divider()

# Tabs
tab_upload, tab_stats, tab_manage = st.tabs(["📤 Upload", "📊 Statistiques", "⚙️ Gestion"])

with tab_upload:
    st.subheader("Uploader des documents à la base commune")

    st.info("""
    **Types de documents recommandés** :
    - Codes français (Code Civil, Code Pénal, etc.)
    - Lois et décrets
    - Jurisprudence de référence
    - Doctrine juridique officielle

    **Format recommandé** : Markdown (.md) pour une meilleure structuration
    """)

    # Type de document
    doc_type = st.selectbox(
        "Type de document",
        options=["code", "loi", "jurisprudence", "doctrine"],
        format_func=lambda x: x.capitalize(),
    )

    # Upload
    uploaded = render_file_uploader(
        user_id=user_id,
        label="Choisissez un ou plusieurs fichiers",
        accept_multiple=True,
        document_category=doc_type,
        target="knowledge_base",  # Important : base commune
    )

    if uploaded:
        st.success(f"✅ {len(uploaded)} document(s) ajouté(s) à la base de connaissances !")

        st.info("""
        Les documents sont maintenant accessibles à tous les utilisateurs
        lors de leurs recherches dans le chat.
        """)

with tab_stats:
    st.subheader("📊 Statistiques de la base de connaissances")

    try:
        # Récupérer les stats du vector store
        async def get_stats():
            vector_store = await get_vector_store()
            return vector_store.get_collection_stats("french_laws")

        stats = asyncio.run(get_stats())

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric(
                label="📄 Documents indexés",
                value=stats.get("count", 0),
            )

        with col2:
            st.metric(
                label="📚 Collection",
                value=stats.get("name", "N/A"),
            )

        with col3:
            st.metric(
                label="💾 Métadonnées",
                value=len(stats.get("metadata", {})),
            )

        st.divider()

        # Informations détaillées
        st.subheader("Informations détaillées")

        st.json(stats)

    except Exception as e:
        st.error(f"Erreur lors de la récupération des statistiques: {e}")
        logger.error(f"Erreur stats: {e}")

with tab_manage:
    st.subheader("⚙️ Gestion de la base de connaissances")

    st.warning("🚧 Fonctionnalités de gestion en développement")

    st.markdown("""
    **Fonctionnalités prévues** :
    - 🔍 Recherche dans la base
    - 📝 Édition des métadonnées
    - 🗑️ Suppression de documents
    - 🔄 Mise à jour automatique depuis Légifrance
    - 📊 Analyse de la qualité des embeddings
    - 🔐 Gestion des permissions
    """)

    # Placeholder pour futures fonctionnalités
    if st.button("🔄 Rafraîchir les statistiques"):
        st.rerun()

# Footer
st.divider()
st.caption("""
🔑 **Admin** : Vous avez les droits d'administration pour gérer la base commune.

📖 **Documentation** : Consultez la documentation pour en savoir plus sur la gestion de la base.

⚠️ **Responsabilité** : Assurez-vous que les documents ajoutés sont à jour et vérifiés.
""")
