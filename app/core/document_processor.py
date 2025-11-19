"""
Traitement et chunking de documents pour l'indexation
"""

import re
from pathlib import Path
from typing import Any, Dict, List, Tuple

from langchain.text_splitter import RecursiveCharacterTextSplitter

from app.config.settings import settings
from app.utils.file_parser import parse_file
from app.utils.logger import logger


class DocumentProcessor:
    """
    Traite et découpe les documents pour l'indexation
    """

    def __init__(
        self, chunk_size: int = None, chunk_overlap: int = None, separators: List[str] = None
    ):
        """
        Initialise le processeur de documents

        Args:
            chunk_size: Taille des chunks
            chunk_overlap: Overlap entre chunks
            separators: Séparateurs personnalisés
        """
        self.chunk_size = chunk_size or settings.rag_chunk_size
        self.chunk_overlap = chunk_overlap or settings.rag_chunk_overlap

        # Séparateurs optimisés pour documents juridiques
        self.separators = separators or [
            "\n\n\n",  # Sections majeures
            "\n\n",  # Paragraphes
            "\n",  # Lignes
            ". ",  # Phrases
            ", ",  # Clauses
            " ",  # Mots
            "",  # Caractères
        ]

        # Initialiser le text splitter
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            separators=self.separators,
            length_function=len,
        )

        logger.info(
            f"DocumentProcessor initialisé - "
            f"ChunkSize: {self.chunk_size}, Overlap: {self.chunk_overlap}"
        )

    def process_file(
        self, file_path: Path, metadata: Optional[Dict[str, Any]] = None
    ) -> Tuple[List[str], List[Dict[str, Any]]]:
        """
        Traite un fichier : parsing + chunking

        Args:
            file_path: Chemin du fichier
            metadata: Métadonnées de base

        Returns:
            (chunks, metadatas)
        """
        try:
            # Parser le fichier
            logger.info(f"Traitement fichier: {file_path.name}")
            text = parse_file(file_path)

            # Nettoyer le texte
            text = self._clean_text(text)

            # Métadonnées de base
            base_metadata = metadata or {}
            base_metadata.update(
                {
                    "filename": file_path.name,
                    "file_type": file_path.suffix.lower(),
                }
            )

            # Chunker
            chunks, metadatas = self.chunk_text(text, base_metadata)

            logger.info(
                f"Fichier traité: {file_path.name} -> {len(chunks)} chunks "
                f"({len(text)} chars)"
            )

            return chunks, metadatas

        except Exception as e:
            logger.error(f"Erreur traitement fichier {file_path}: {e}")
            raise

    def chunk_text(
        self, text: str, metadata: Optional[Dict[str, Any]] = None
    ) -> Tuple[List[str], List[Dict[str, Any]]]:
        """
        Découpe un texte en chunks

        Args:
            text: Texte à découper
            metadata: Métadonnées de base

        Returns:
            (chunks, metadatas)
        """
        try:
            # Découper avec LangChain
            chunks = self.text_splitter.split_text(text)

            # Créer les métadonnées pour chaque chunk
            metadatas = []
            base_metadata = metadata or {}

            for i, chunk in enumerate(chunks):
                chunk_metadata = base_metadata.copy()
                chunk_metadata.update(
                    {
                        "chunk_index": i,
                        "chunk_size": len(chunk),
                        "total_chunks": len(chunks),
                    }
                )
                metadatas.append(chunk_metadata)

            logger.debug(f"Texte découpé en {len(chunks)} chunks")

            return chunks, metadatas

        except Exception as e:
            logger.error(f"Erreur chunking: {e}")
            raise

    def _clean_text(self, text: str) -> str:
        """
        Nettoie un texte (espaces multiples, caractères spéciaux, etc.)

        Args:
            text: Texte brut

        Returns:
            Texte nettoyé
        """
        # Supprimer les espaces multiples
        text = re.sub(r"\s+", " ", text)

        # Supprimer les lignes vides multiples
        text = re.sub(r"\n{3,}", "\n\n", text)

        # Supprimer les espaces en début/fin
        text = text.strip()

        return text

    def extract_legal_metadata(self, text: str) -> Dict[str, Any]:
        """
        Extrait des métadonnées juridiques depuis le texte

        Args:
            text: Texte du document

        Returns:
            Métadonnées extraites
        """
        metadata = {}

        # Détecter les articles de loi
        article_pattern = r"(?:Article|Art\.)\s+(\d+(?:-\d+)?)"
        articles = re.findall(article_pattern, text)
        if articles:
            metadata["articles"] = list(set(articles))

        # Détecter le type de code
        code_patterns = {
            "code_civil": r"Code civil",
            "code_penal": r"Code pénal",
            "code_commerce": r"Code de commerce",
            "code_travail": r"Code du travail",
            "code_procedure_civile": r"Code de procédure civile",
        }

        for code_type, pattern in code_patterns.items():
            if re.search(pattern, text, re.IGNORECASE):
                metadata["code_type"] = code_type
                break

        # Détecter les dates
        date_pattern = r"\b(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})\b"
        dates = re.findall(date_pattern, text)
        if dates:
            metadata["dates_mentioned"] = dates[:5]  # Garder les 5 premières

        return metadata

    def process_legal_document(
        self, file_path: Path, document_type: str = "unknown"
    ) -> Tuple[List[str], List[Dict[str, Any]]]:
        """
        Traite un document juridique avec extraction de métadonnées

        Args:
            file_path: Chemin du fichier
            document_type: Type de document (code, loi, jurisprudence, etc.)

        Returns:
            (chunks, metadatas)
        """
        try:
            # Parser
            text = parse_file(file_path)
            text = self._clean_text(text)

            # Extraire métadonnées juridiques
            legal_metadata = self.extract_legal_metadata(text)

            # Métadonnées de base
            base_metadata = {
                "filename": file_path.name,
                "file_type": file_path.suffix.lower(),
                "document_type": document_type,
                **legal_metadata,
            }

            # Chunker
            chunks, metadatas = self.chunk_text(text, base_metadata)

            logger.info(
                f"Document juridique traité: {file_path.name} - "
                f"Type: {document_type} - {len(chunks)} chunks"
            )

            return chunks, metadatas

        except Exception as e:
            logger.error(f"Erreur traitement document juridique {file_path}: {e}")
            raise

    def batch_process_directory(
        self, directory: Path, document_type: str = "unknown", file_pattern: str = "*.*"
    ) -> Tuple[List[str], List[Dict[str, Any]]]:
        """
        Traite tous les fichiers d'un répertoire

        Args:
            directory: Répertoire à traiter
            document_type: Type de documents
            file_pattern: Pattern de fichiers (ex: "*.pdf")

        Returns:
            (all_chunks, all_metadatas)
        """
        all_chunks = []
        all_metadatas = []

        files = list(directory.glob(file_pattern))
        logger.info(f"Traitement batch: {len(files)} fichiers dans {directory}")

        for file_path in files:
            try:
                chunks, metadatas = self.process_legal_document(file_path, document_type)
                all_chunks.extend(chunks)
                all_metadatas.extend(metadatas)

            except Exception as e:
                logger.error(f"Erreur fichier {file_path.name}: {e}")
                continue

        logger.info(
            f"Batch terminé: {len(files)} fichiers -> {len(all_chunks)} chunks totaux"
        )

        return all_chunks, all_metadatas

    def merge_small_chunks(
        self, chunks: List[str], metadatas: List[Dict[str, Any]], min_size: int = 200
    ) -> Tuple[List[str], List[Dict[str, Any]]]:
        """
        Fusionne les chunks trop petits

        Args:
            chunks: Liste de chunks
            metadatas: Liste de métadonnées
            min_size: Taille minimale d'un chunk

        Returns:
            (merged_chunks, merged_metadatas)
        """
        merged_chunks = []
        merged_metadatas = []

        current_chunk = ""
        current_metadata = None

        for i, chunk in enumerate(chunks):
            if len(chunk) < min_size and i < len(chunks) - 1:
                # Chunk trop petit, on accumule
                current_chunk += " " + chunk if current_chunk else chunk
                if current_metadata is None:
                    current_metadata = metadatas[i].copy()
            else:
                # Chunk suffisamment grand ou dernier chunk
                if current_chunk:
                    current_chunk += " " + chunk
                else:
                    current_chunk = chunk

                merged_chunks.append(current_chunk)

                # Métadonnées du premier chunk de la fusion
                merged_metadatas.append(current_metadata or metadatas[i])

                # Reset
                current_chunk = ""
                current_metadata = None

        logger.debug(
            f"Fusion chunks: {len(chunks)} -> {len(merged_chunks)} "
            f"(seuil: {min_size} chars)"
        )

        return merged_chunks, merged_metadatas


# Instance globale
_document_processor: Optional[DocumentProcessor] = None


def get_document_processor() -> DocumentProcessor:
    """
    Récupère l'instance globale du processeur de documents

    Returns:
        Instance de DocumentProcessor
    """
    global _document_processor

    if _document_processor is None:
        _document_processor = DocumentProcessor()

    return _document_processor


__all__ = ["DocumentProcessor", "get_document_processor"]
