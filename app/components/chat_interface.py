"""
Composant interface de chat réutilisable (OPTIMISÉ avec caching Streamlit)
"""

import streamlit as st
import asyncio
from datetime import datetime
from typing import Optional
from uuid import uuid4

from app.core.rag_pipeline import get_rag_pipeline
from app.database.supabase_client import get_supabase_client
from app.database.models import (
    ConversationCreate,
    MessageCreate,
    MessageRole,
)
from app.utils.logger import logger


# OPTIMISATION : Singleton RAG Pipeline avec cache Streamlit
@st.cache_resource
def get_cached_rag_pipeline():
    """
    Pipeline RAG singleton avec cache Streamlit (OPTIMISÉ)
    Évite de recréer le pipeline à chaque interaction
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    pipeline = loop.run_until_complete(get_rag_pipeline())
    logger.info("Pipeline RAG chargé et caché")
    return pipeline


# OPTIMISATION : Singleton Supabase Client avec cache
@st.cache_resource
def get_cached_supabase_client():
    """
    Client Supabase singleton avec cache (OPTIMISÉ)
    Réutilise la même connexion au lieu de la recréer
    """
    client = get_supabase_client()
    logger.info("Client Supabase chargé et caché")
    return client


def init_chat_session():
    """Initialise les variables de session pour le chat"""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "current_conversation_id" not in st.session_state:
        st.session_state.current_conversation_id = None
    if "rag_pipeline" not in st.session_state:
        st.session_state.rag_pipeline = None


async def get_or_create_rag_pipeline():
    """Récupère ou crée le pipeline RAG (OPTIMISÉ - utilise le cache)"""
    # OPTIMISATION : Utiliser la version cachée au lieu de session_state
    return get_cached_rag_pipeline()


def create_new_conversation(user_id: str, title: str = "Nouvelle conversation"):
    """
    Crée une nouvelle conversation

    Args:
        user_id: ID de l'utilisateur
        title: Titre de la conversation

    Returns:
        ID de la conversation créée
    """
    try:
        client = get_cached_supabase_client()  # OPTIMISÉ

        conv_create = ConversationCreate(user_id=user_id, title=title)
        conversation = client.create_conversation(conv_create)

        logger.info(f"Conversation créée: {conversation.id}")
        return str(conversation.id)

    except Exception as e:
        logger.error(f"Erreur création conversation: {e}")
        return None


def save_message_to_db(
    user_id: str,
    conversation_id: str,
    role: str,
    content: str,
    sources: Optional[list] = None,
):
    """
    Sauvegarde un message dans la base de données

    Args:
        user_id: ID utilisateur
        conversation_id: ID conversation
        role: Rôle du message (user/assistant)
        content: Contenu du message
        sources: Sources utilisées
    """
    try:
        client = get_cached_supabase_client()  # OPTIMISÉ

        message_create = MessageCreate(
            conversation_id=conversation_id,
            user_id=user_id,
            role=MessageRole(role),
            content=content,
            sources=sources,
        )

        client.create_message(message_create)
        logger.debug(f"Message sauvegardé dans conversation {conversation_id}")

    except Exception as e:
        logger.error(f"Erreur sauvegarde message: {e}")


def render_message(role: str, content: str, sources: Optional[list] = None):
    """
    Affiche un message de chat

    Args:
        role: Rôle (user/assistant)
        content: Contenu du message
        sources: Sources (pour l'assistant)
    """
    avatar = "👤" if role == "user" else "🤖"

    with st.chat_message(role, avatar=avatar):
        st.markdown(content)

        # Afficher les sources si disponibles
        if sources and role == "assistant":
            with st.expander("📚 Sources utilisées"):
                for i, source in enumerate(sources, 1):
                    source_type = source.get("type", "unknown")

                    if source_type == "law":
                        st.markdown(f"""
                        **{i}. {source.get('name', 'Source')}**
                        - Article: {source.get('article', 'N/A')}
                        - Pertinence: {source.get('relevance_score', 0):.0%}
                        - Extrait: _{source.get('excerpt', '')}_
                        """)
                    else:
                        st.markdown(f"""
                        **{i}. {source.get('name', 'Document')}**
                        - Type: {source.get('category', 'N/A')}
                        - Pertinence: {source.get('relevance_score', 0):.0%}
                        - Extrait: _{source.get('excerpt', '')}_
                        """)


async def process_user_query(user_id: str, query: str, conversation_id: Optional[str] = None):
    """
    Traite une requête utilisateur

    Args:
        user_id: ID utilisateur
        query: Question de l'utilisateur
        conversation_id: ID de la conversation

    Returns:
        Réponse de l'assistant
    """
    try:
        # Créer une conversation si nécessaire
        if not conversation_id:
            conversation_id = create_new_conversation(user_id, title=query[:50])
            st.session_state.current_conversation_id = conversation_id

        # Sauvegarder la question
        save_message_to_db(user_id, conversation_id, "user", query)

        # Récupérer le pipeline RAG
        rag_pipeline = await get_or_create_rag_pipeline()

        # Traiter la requête
        with st.spinner("🔍 Recherche dans la base de connaissances..."):
            result = await rag_pipeline.process_query(
                query=query,
                user_id=user_id,
                conversation_id=conversation_id,
                history=st.session_state.messages,
            )

        # Vérifier s'il y a une erreur
        if "error" in result:
            response = result.get("response", "Une erreur est survenue.")
            sources = []
        else:
            response = result.get("response", "")
            sources = result.get("sources", [])

        # Sauvegarder la réponse
        save_message_to_db(user_id, conversation_id, "assistant", response, sources)

        # Sauvegarder dans l'historique du pipeline RAG (pour le contexte)
        await rag_pipeline.save_to_history(user_id, conversation_id, query, response)

        return {"role": "assistant", "content": response, "sources": sources}

    except Exception as e:
        logger.error(f"Erreur traitement requête: {e}")
        error_response = f"Désolé, une erreur est survenue: {str(e)}"
        return {"role": "assistant", "content": error_response, "sources": []}


def render_chat_interface(user_id: str):
    """
    Affiche l'interface de chat complète

    Args:
        user_id: ID de l'utilisateur
    """
    init_chat_session()

    # Titre
    st.title("💬 Chat Juridique")

    # Sidebar pour les conversations
    with st.sidebar:
        st.subheader("💭 Conversations")

        # Bouton nouvelle conversation
        if st.button("➕ Nouvelle conversation", use_container_width=True):
            st.session_state.messages = []
            st.session_state.current_conversation_id = None
            st.rerun()

        # Liste des conversations (à implémenter)
        st.caption("📋 Historique des conversations disponible dans Paramètres")

    # Afficher l'historique des messages
    for message in st.session_state.messages:
        render_message(
            role=message["role"],
            content=message["content"],
            sources=message.get("sources"),
        )

    # Input utilisateur
    if prompt := st.chat_input("Posez votre question juridique..."):
        # Afficher la question
        st.session_state.messages.append({"role": "user", "content": prompt})
        render_message("user", prompt)

        # Traiter la requête
        response = asyncio.run(
            process_user_query(
                user_id=user_id,
                query=prompt,
                conversation_id=st.session_state.current_conversation_id,
            )
        )

        # Afficher la réponse
        st.session_state.messages.append(response)
        render_message(
            role=response["role"],
            content=response["content"],
            sources=response.get("sources"),
        )

    # Bouton pour effacer l'historique
    if st.session_state.messages:
        col1, col2, col3 = st.columns([2, 1, 1])
        with col3:
            if st.button("🗑️ Effacer l'historique"):
                if st.session_state.current_conversation_id:
                    # Demander confirmation
                    st.warning("Êtes-vous sûr ? Cette action est irréversible.")
                    col_yes, col_no = st.columns(2)
                    with col_yes:
                        if st.button("Oui, effacer"):
                            st.session_state.messages = []
                            st.session_state.current_conversation_id = None
                            st.rerun()
                    with col_no:
                        if st.button("Annuler"):
                            st.rerun()


__all__ = [
    "init_chat_session",
    "render_chat_interface",
    "render_message",
    "process_user_query",
]
