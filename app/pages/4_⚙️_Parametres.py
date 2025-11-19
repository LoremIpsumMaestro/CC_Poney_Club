"""
Page des paramètres utilisateur
Profil, statistiques, export de données, suppression de compte
"""

import streamlit as st
from uuid import UUID

from app.components.auth_guard import (
    require_authentication,
    get_current_user,
    get_current_user_profile,
    logout,
)
from app.components.sidebar import render_sidebar
from app.database.supabase_client import get_supabase_client
from app.database.models import UserProfileUpdate
from app.core.vector_store import get_vector_store
from app.utils.logger import logger
import asyncio

# Configuration
st.set_page_config(
    page_title="Paramètres - Coda2z",
    page_icon="⚙️",
    layout="wide",
)

# Authentification
if not require_authentication():
    st.stop()

# Sidebar
render_sidebar()

# User
user = get_current_user()
profile = get_current_user_profile()
user_id = user["id"] if user else None

if not user_id:
    st.error("Erreur: ID utilisateur introuvable")
    st.stop()

# Titre
st.title("⚙️ Paramètres")

# Tabs
tab_profile, tab_stats, tab_privacy, tab_advanced = st.tabs([
    "👤 Profil",
    "📊 Statistiques",
    "🔒 Confidentialité",
    "⚙️ Avancé",
])

with tab_profile:
    st.subheader("👤 Mon profil")

    if profile:
        with st.form("profile_form"):
            full_name = st.text_input(
                "Nom complet",
                value=profile.full_name,
            )

            law_firm = st.text_input(
                "Cabinet d'avocats",
                value=profile.law_firm or "",
            )

            st.caption(f"**Rôle** : {profile.role.capitalize()}")
            st.caption(f"**Compte créé le** : {profile.created_at.strftime('%d/%m/%Y')}")

            col1, col2 = st.columns(2)
            with col1:
                submit = st.form_submit_button("💾 Sauvegarder", use_container_width=True)
            with col2:
                cancel = st.form_submit_button("❌ Annuler", use_container_width=True)

            if submit:
                try:
                    client = get_supabase_client()

                    update = UserProfileUpdate(
                        full_name=full_name,
                        law_firm=law_firm if law_firm else None,
                    )

                    updated_profile = client.update_profile(UUID(user_id), update)

                    if updated_profile:
                        st.success("✅ Profil mis à jour !")
                        st.session_state.user_profile = updated_profile
                        st.rerun()
                    else:
                        st.error("Erreur lors de la mise à jour")

                except Exception as e:
                    st.error(f"Erreur: {e}")
                    logger.error(f"Erreur update profil: {e}")

            if cancel:
                st.rerun()

    else:
        st.warning("Profil non trouvé")

with tab_stats:
    st.subheader("📊 Vos statistiques d'utilisation")

    try:
        client = get_supabase_client()
        stats = client.get_user_statistics(UUID(user_id))

        col1, col2 = st.columns(2)

        with col1:
            st.metric(
                label="💬 Conversations",
                value=stats.total_conversations,
            )

            st.metric(
                label="💭 Messages envoyés",
                value=stats.total_messages,
            )

        with col2:
            st.metric(
                label="📄 Documents uploadés",
                value=stats.total_documents,
            )

            st.metric(
                label="🔍 Requêtes effectuées",
                value=stats.total_queries,
            )

        st.divider()

        # Dernière activité
        if stats.last_activity:
            st.info(f"🕐 **Dernière activité** : {stats.last_activity}")

    except Exception as e:
        st.error(f"Erreur chargement des statistiques: {e}")
        logger.error(f"Erreur stats: {e}")

    st.divider()

    st.subheader("📋 Mes conversations")

    try:
        conversations = client.list_user_conversations(UUID(user_id))

        if conversations:
            for conv in conversations:
                with st.expander(f"💬 {conv.title}"):
                    st.write(f"**Créée le** : {conv.created_at.strftime('%d/%m/%Y %H:%M')}")
                    st.write(f"**Messages** : {conv.message_count}")
                    if conv.last_message_at:
                        st.write(f"**Dernier message** : {conv.last_message_at.strftime('%d/%m/%Y %H:%M')}")
        else:
            st.info("Aucune conversation enregistrée")

    except Exception as e:
        st.error(f"Erreur: {e}")

with tab_privacy:
    st.subheader("🔒 Confidentialité et données personnelles")

    st.info("""
    **Vos droits (RGPD)** :
    - ✅ Droit d'accès à vos données
    - ✅ Droit de rectification
    - ✅ Droit à l'effacement
    - ✅ Droit à la portabilité
    """)

    st.divider()

    # Export des données
    st.subheader("📥 Export de mes données")

    st.markdown("""
    Téléchargez une copie complète de toutes vos données :
    - Profil utilisateur
    - Conversations et messages
    - Documents uploadés
    - Logs d'activité
    """)

    if st.button("📦 Exporter mes données (JSON)", use_container_width=True):
        try:
            # TODO: Implémenter l'export complet
            st.info("🚧 Fonctionnalité d'export en développement")
            st.markdown("""
            En attendant, contactez support@coda2z.com pour obtenir
            une copie de vos données.
            """)
        except Exception as e:
            st.error(f"Erreur: {e}")

    st.divider()

    # Suppression de l'historique
    st.subheader("🗑️ Suppression de l'historique")

    st.warning("""
    ⚠️ **Action irréversible**

    Cette action supprimera :
    - Toutes vos conversations
    - Tout l'historique de messages
    - L'historique dans le vector store
    """)

    with st.form("delete_history_form"):
        confirm_text = st.text_input(
            "Tapez 'SUPPRIMER' pour confirmer",
            max_chars=20,
        )

        delete_history = st.form_submit_button("🗑️ Supprimer l'historique")

        if delete_history:
            if confirm_text == "SUPPRIMER":
                try:
                    # Supprimer de Supabase
                    # TODO: Implémenter suppression conversations

                    # Supprimer du vector store
                    async def delete_user_history():
                        vector_store = await get_vector_store()
                        return vector_store.delete_user_data(user_id)

                    result = asyncio.run(delete_user_history())

                    if result.get("history"):
                        st.success("✅ Historique supprimé avec succès")
                    else:
                        st.error("Erreur lors de la suppression")

                except Exception as e:
                    st.error(f"Erreur: {e}")
                    logger.error(f"Erreur suppression historique: {e}")
            else:
                st.error("❌ Confirmation incorrecte")

with tab_advanced:
    st.subheader("⚙️ Paramètres avancés")

    st.warning("🚧 Section en développement")

    st.markdown("""
    **Fonctionnalités prévues** :
    - 🎨 Thème de l'interface
    - 🔔 Notifications
    - 🌐 Langue de l'interface
    - 🔐 Sécurité avancée (2FA)
    - 📊 Préférences de recherche
    """)

    st.divider()

    # Suppression de compte
    st.subheader("❌ Suppression de compte")

    st.error("""
    ⚠️ **DANGER - Action définitivement irréversible**

    Cette action supprimera :
    - Votre profil utilisateur
    - Toutes vos conversations
    - Tous vos documents uploadés
    - Toutes vos données personnelles

    **Cette action ne peut PAS être annulée.**
    """)

    with st.form("delete_account_form"):
        st.write("Pour supprimer définitivement votre compte :")

        email_confirm = st.text_input("Confirmez votre email")
        delete_confirm = st.text_input("Tapez 'SUPPRIMER MON COMPTE'")

        delete_account = st.form_submit_button("❌ SUPPRIMER MON COMPTE DÉFINITIVEMENT")

        if delete_account:
            if user and email_confirm == user.get("email") and delete_confirm == "SUPPRIMER MON COMPTE":
                try:
                    # Supprimer toutes les données
                    client = get_supabase_client()

                    async def delete_all():
                        # Vector store
                        vector_store = await get_vector_store()
                        vector_store.delete_user_data(user_id)

                        # Database
                        client.delete_all_user_data(UUID(user_id))

                    asyncio.run(delete_all())

                    st.success("✅ Compte supprimé. Vous allez être déconnecté.")

                    # Déconnecter
                    logout()

                    # Rediriger
                    st.switch_page("main.py")

                except Exception as e:
                    st.error(f"Erreur: {e}")
                    logger.error(f"Erreur suppression compte: {e}")
            else:
                st.error("❌ Confirmations incorrectes")

# Footer
st.divider()
st.caption("""
🔒 **Sécurité** : Toutes vos modifications sont chiffrées et sécurisées.

📧 **Support** : Pour toute question, contactez support@coda2z.com

📖 **Documentation** : Consultez notre [documentation](https://docs.coda2z.com)
""")
