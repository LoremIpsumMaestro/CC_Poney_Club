"""
Page de chat principal
Permet de poser des questions juridiques et obtenir des réponses de l'IA
"""

import streamlit as st
from app.components.auth_guard import require_authentication, get_current_user
from app.components.sidebar import render_sidebar
from app.components.chat_interface import render_chat_interface

# Configuration de la page
st.set_page_config(
    page_title="Chat - Coda2z",
    page_icon="💬",
    layout="wide",
)

# Vérifier l'authentification
if not require_authentication():
    st.stop()

# Afficher la sidebar
render_sidebar()

# Récupérer l'utilisateur courant
user = get_current_user()
user_id = user["id"] if user else None

if not user_id:
    st.error("Erreur: Impossible de récupérer l'ID utilisateur")
    st.stop()

# Afficher l'interface de chat
render_chat_interface(user_id)

# Footer
st.divider()
st.caption("""
💡 **Astuce** : Soyez spécifique dans vos questions pour obtenir de meilleures réponses.

🔒 **Confidentialité** : Vos conversations sont privées et chiffrées.
""")
