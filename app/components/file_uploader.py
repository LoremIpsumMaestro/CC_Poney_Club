"""
Composant d'upload de fichiers réutilisable (OPTIMISÉ avec caching)
"""

import streamlit as st
import asyncio
from pathlib import Path
from uuid import uuid4

from app.core.document_processor import get_document_processor
from app.core.vector_store import get_vector_store
from app.database.supabase_client import get_supabase_client
from app.database.models import DocumentCreate, DocumentCategory
from app.utils.validators import validate_upload
from app.utils.security import sanitize_filename
from app.utils.logger import logger
from app.config.settings import settings


# OPTIMISATION : Cache pour liste documents
@st.cache_data(ttl=60)  # Cache 1 minute
def get_user_documents_cached(user_id: str):
    """
    Récupère les documents utilisateur avec cache (OPTIMISÉ)
    Réduit les appels DB redondants
    """
    client = get_supabase_client()
    return client.list_user_documents(user_id)


def render_file_uploader(
    user_id: str,
    label: str = "Choisissez un fichier",
    accept_multiple: bool = False,
    document_category: str = "autre",
    target: str = "user",  # "user" ou "knowledge_base"
):
    """
    Affiche un composant d'upload de fichiers

    Args:
        user_id: ID de l'utilisateur
        label: Label de l'uploader
        accept_multiple: Autoriser plusieurs fichiers
        document_category: Catégorie du document
        target: Destination (user ou knowledge_base)

    Returns:
        Liste des fichiers uploadés avec succès
    """
    # Types de fichiers acceptés
    accepted_types = ["pdf", "docx", "txt", "md", "xlsx", "csv", "json", "pptx"]

    uploaded_files = st.file_uploader(
        label,
        accept_multiple_files=accept_multiple,
        type=accepted_types,
        help=f"Formats supportés : {', '.join(accepted_types.upper())}. Taille max: {settings.max_upload_size_mb} MB",
    )

    uploaded_successfully = []

    if uploaded_files:
        # Normaliser en liste
        if not isinstance(uploaded_files, list):
            uploaded_files = [uploaded_files]

        for uploaded_file in uploaded_files:
            # Valider le fichier
            is_valid, error_msg = validate_upload(
                uploaded_file.name, uploaded_file.size
            )

            if not is_valid:
                st.error(f"❌ {uploaded_file.name}: {error_msg}")
                continue

            # Afficher les infos du fichier
            col1, col2 = st.columns([3, 1])
            with col1:
                st.info(f"📄 **{uploaded_file.name}** ({uploaded_file.size / 1024:.1f} KB)")
            with col2:
                if st.button(f"Uploader", key=f"upload_{uploaded_file.name}"):
                    success = asyncio.run(
                        process_file_upload(
                            user_id=user_id,
                            uploaded_file=uploaded_file,
                            category=document_category,
                            target=target,
                        )
                    )

                    if success:
                        st.success(f"✅ {uploaded_file.name} uploadé avec succès !")
                        uploaded_successfully.append(uploaded_file.name)
                    else:
                        st.error(f"❌ Erreur lors de l'upload de {uploaded_file.name}")

    return uploaded_successfully


async def process_file_upload(
    user_id: str,
    uploaded_file,
    category: str = "autre",
    target: str = "user",
) -> bool:
    """
    Traite l'upload d'un fichier

    Args:
        user_id: ID utilisateur
        uploaded_file: Fichier uploadé (UploadedFile Streamlit)
        category: Catégorie du document
        target: Destination (user ou knowledge_base)

    Returns:
        True si succès
    """
    try:
        # Nettoyer le nom de fichier
        safe_filename = sanitize_filename(uploaded_file.name)

        # Créer le chemin de destination
        upload_dir = settings.upload_dir / user_id
        upload_dir.mkdir(parents=True, exist_ok=True)

        file_path = upload_dir / safe_filename

        # Sauvegarder le fichier
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        logger.info(f"Fichier sauvegardé: {file_path}")

        # Traiter et indexer le document
        processor = get_document_processor()
        vector_store = await get_vector_store()

        # Parser et chunker
        with st.spinner(f"🔄 Traitement de {safe_filename}..."):
            chunks, metadatas = processor.process_file(
                file_path,
                metadata={
                    "user_id": user_id,
                    "category": category,
                    "uploaded_by": user_id,
                },
            )

        # Indexer dans le vector store
        with st.spinner(f"📊 Indexation de {safe_filename}..."):
            if target == "user":
                # Document privé utilisateur
                for chunk, metadata in zip(chunks, metadatas):
                    vector_store_id = await vector_store.add_user_document(
                        user_id=user_id,
                        document=chunk,
                        metadata=metadata,
                    )
            else:
                # Base de connaissances commune (admin uniquement)
                ids = await vector_store.add_to_knowledge_base(
                    documents=chunks,
                    metadatas=metadatas,
                )
                vector_store_id = ids[0] if ids else None

        # Sauvegarder les métadonnées dans Supabase
        client = get_supabase_client()

        doc_create = DocumentCreate(
            user_id=user_id,
            filename=safe_filename,
            file_path=str(file_path),
            file_size=uploaded_file.size,
            file_type=Path(safe_filename).suffix,
            category=DocumentCategory(category) if category in DocumentCategory.__members__.values() else None,
        )

        document = client.create_document(doc_create)

        # Mettre à jour avec le vector_store_id
        from app.database.models import DocumentUpdate

        client.update_document(
            document.id,
            DocumentUpdate(
                vector_store_id=vector_store_id,
                indexed_at=asyncio.get_event_loop().time(),
            ),
        )

        logger.info(
            f"Document indexé: {safe_filename} - {len(chunks)} chunks - ID: {vector_store_id}"
        )

        return True

    except Exception as e:
        logger.error(f"Erreur traitement upload: {e}")
        return False


def render_document_list(user_id: str, show_delete: bool = True):
    """
    Affiche la liste des documents d'un utilisateur (OPTIMISÉ avec cache)

    Args:
        user_id: ID utilisateur
        show_delete: Afficher le bouton de suppression
    """
    try:
        # OPTIMISATION : Utiliser la version cachée
        documents = get_user_documents_cached(user_id)

        if not documents:
            st.info("📭 Aucun document uploadé pour le moment")
            return

        st.subheader(f"📄 Mes documents ({len(documents)})")

        for doc in documents:
            with st.expander(f"📎 {doc.filename}"):
                col1, col2 = st.columns([3, 1])

                with col1:
                    st.write(f"**Type:** {doc.file_type}")
                    st.write(f"**Taille:** {doc.file_size / 1024:.1f} KB")
                    st.write(f"**Catégorie:** {doc.category or 'Non spécifiée'}")
                    st.write(f"**Upload:** {doc.uploaded_at.strftime('%d/%m/%Y %H:%M')}")
                    if doc.indexed_at:
                        st.success("✅ Indexé et recherchable")
                    else:
                        st.warning("⏳ En cours d'indexation...")

                with col2:
                    if show_delete:
                        if st.button("🗑️ Supprimer", key=f"delete_{doc.id}"):
                            # Confirmation
                            st.warning("Êtes-vous sûr ?")
                            if st.button("Confirmer", key=f"confirm_{doc.id}"):
                                success = asyncio.run(delete_document(user_id, str(doc.id)))
                                if success:
                                    st.success("✅ Document complètement supprimé")
                                    st.rerun()
                                else:
                                    st.error("❌ Erreur lors de la suppression")

    except Exception as e:
        st.error(f"Erreur chargement des documents: {e}")
        logger.error(f"Erreur list documents: {e}")


async def delete_document(user_id: str, document_id: str) -> bool:
    """
    Supprime un document complètement (DB + vector store + fichier physique)

    Args:
        user_id: ID utilisateur
        document_id: ID du document

    Returns:
        True si succès
    """
    try:
        client = get_supabase_client()

        # 1. Récupérer les infos du document avant suppression
        response = (
            client.client.table("documents")
            .select("*")
            .eq("id", document_id)
            .eq("user_id", user_id)  # Sécurité : vérifier que c'est bien son document
            .execute()
        )

        if not response.data or len(response.data) == 0:
            logger.warning(f"Document non trouvé ou accès refusé: {document_id}")
            return False

        document = response.data[0]
        file_path = document.get("file_path")
        vector_store_id = document.get("vector_store_id")
        filename = document.get("filename")

        # 2. Supprimer du vector store
        if vector_store_id:
            try:
                vector_store = await get_vector_store()

                # Supprimer de la collection user_documents
                user_docs_collection = settings.get_user_collection_name(user_id, "documents")
                vector_store.delete_documents(
                    collection_name=user_docs_collection,
                    where={"filename": filename},  # Supprimer tous les chunks de ce fichier
                )
                logger.info(f"Document supprimé du vector store: {vector_store_id}")
            except Exception as e:
                logger.error(f"Erreur suppression vector store: {e}")
                # Continuer quand même

        # 3. Supprimer le fichier physique
        if file_path:
            try:
                file_path_obj = Path(file_path)
                if file_path_obj.exists():
                    file_path_obj.unlink()
                    logger.info(f"Fichier physique supprimé: {file_path}")
            except Exception as e:
                logger.error(f"Erreur suppression fichier physique: {e}")
                # Continuer quand même

        # 4. Supprimer de la base de données
        success = client.delete_document(document_id)

        if success:
            logger.info(f"Document complètement supprimé: {document_id}")

        return success

    except Exception as e:
        logger.error(f"Erreur suppression document: {e}")
        return False


__all__ = [
    "render_file_uploader",
    "process_file_upload",
    "render_document_list",
    "delete_document",
]
