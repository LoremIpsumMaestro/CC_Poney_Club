"""
Page de gestion des documents privés de l'utilisateur
Upload, consultation et suppression de documents
"""

import streamlit as st
from app.components.auth_guard import require_authentication, get_current_user
from app.components.sidebar import render_sidebar
from app.components.file_uploader import render_file_uploader, render_document_list

# Configuration
st.set_page_config(
    page_title="Mes Documents - Coda2z",
    page_icon="📄",
    layout="wide",
)

# Authentification
if not require_authentication():
    st.stop()

# Sidebar
render_sidebar()

# User
user = get_current_user()
user_id = user["id"] if user else None

if not user_id:
    st.error("Erreur: ID utilisateur introuvable")
    st.stop()

# Titre
st.title("📄 Mes Documents")

st.markdown("""
Uploadez vos documents juridiques personnels pour les rendre recherchables dans le chat.

Vos documents restent **strictement privés** et ne sont accessibles que par vous.
""")

st.divider()

# Tabs
tab_upload, tab_list = st.tabs(["📤 Upload", "📋 Mes documents"])

with tab_upload:
    st.subheader("Uploader un nouveau document")

    st.info("""
    **Formats supportés** : PDF, DOCX, TXT, MD, XLSX, CSV, JSON, PPTX

    **Taille maximale** : 50 MB par fichier

    **Catégories** :
    - Contrat
    - Consultation
    - Jurisprudence
    - Doctrine
    - Autre
    """)

    # Sélection de catégorie
    category = st.selectbox(
        "Catégorie du document",
        options=["contrat", "consultation", "jurisprudence", "doctrine", "autre"],
        format_func=lambda x: x.capitalize(),
    )

    # Composant d'upload
    uploaded = render_file_uploader(
        user_id=user_id,
        label="Choisissez un ou plusieurs fichiers",
        accept_multiple=True,
        document_category=category,
        target="user",
    )

    if uploaded:
        st.success(f"✅ {len(uploaded)} document(s) uploadé(s) avec succès !")

        st.info("""
        **Prochaines étapes** :
        1. Vos documents sont en cours d'indexation
        2. Ils seront automatiquement recherchables dans le chat
        3. Vous pouvez continuer à uploader d'autres documents
        """)

with tab_list:
    st.subheader("📋 Mes documents uploadés")

    # Afficher la liste des documents
    render_document_list(user_id=user_id, show_delete=True)

# Footer
st.divider()
st.caption("""
🔒 **Sécurité** : Tous vos documents sont chiffrés et isolés des autres utilisateurs.

💾 **Stockage** : Les documents sont hébergés en France et conformes au RGPD.

🗑️ **Suppression** : Vous pouvez supprimer vos documents à tout moment.
""")
