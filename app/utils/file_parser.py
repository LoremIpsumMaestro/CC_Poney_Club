"""
Parseurs pour différents formats de fichiers
"""

import json
from pathlib import Path
from typing import Optional

import pandas as pd
import pdfplumber
from docx import Document
from markdown import markdown
from openpyxl import load_workbook
from pptx import Presentation

from app.utils.logger import logger


# ============================================================================
# PARSEUR PDF
# ============================================================================


def parse_pdf(file_path: Path) -> str:
    """
    Extrait le texte d'un fichier PDF

    Args:
        file_path: Chemin du fichier PDF

    Returns:
        Texte extrait
    """
    try:
        text_parts = []

        with pdfplumber.open(file_path) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                text = page.extract_text()
                if text:
                    text_parts.append(f"--- Page {page_num} ---\n{text}")

        result = "\n\n".join(text_parts)
        logger.debug(f"PDF parsé: {file_path.name} - {len(result)} caractères")
        return result

    except Exception as e:
        logger.error(f"Erreur parsing PDF {file_path}: {e}")
        raise


# ============================================================================
# PARSEUR DOCX
# ============================================================================


def parse_docx(file_path: Path) -> str:
    """
    Extrait le texte d'un fichier DOCX

    Args:
        file_path: Chemin du fichier DOCX

    Returns:
        Texte extrait
    """
    try:
        doc = Document(file_path)

        text_parts = []

        # Extraire les paragraphes
        for para in doc.paragraphs:
            if para.text.strip():
                text_parts.append(para.text)

        # Extraire les tableaux
        for table in doc.tables:
            table_text = []
            for row in table.rows:
                row_text = [cell.text.strip() for cell in row.cells]
                table_text.append(" | ".join(row_text))

            if table_text:
                text_parts.append("\n--- Tableau ---\n" + "\n".join(table_text))

        result = "\n\n".join(text_parts)
        logger.debug(f"DOCX parsé: {file_path.name} - {len(result)} caractères")
        return result

    except Exception as e:
        logger.error(f"Erreur parsing DOCX {file_path}: {e}")
        raise


# ============================================================================
# PARSEUR TXT
# ============================================================================


def parse_txt(file_path: Path) -> str:
    """
    Lit un fichier texte

    Args:
        file_path: Chemin du fichier TXT

    Returns:
        Contenu du fichier
    """
    try:
        # Essayer plusieurs encodages
        encodings = ["utf-8", "latin-1", "cp1252"]

        for encoding in encodings:
            try:
                with open(file_path, "r", encoding=encoding) as f:
                    content = f.read()
                logger.debug(f"TXT parsé: {file_path.name} avec encoding {encoding}")
                return content
            except UnicodeDecodeError:
                continue

        # Si aucun encoding ne fonctionne
        logger.warning(f"Impossible de décoder {file_path.name}, utilisation de 'ignore'")
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()

    except Exception as e:
        logger.error(f"Erreur parsing TXT {file_path}: {e}")
        raise


# ============================================================================
# PARSEUR MARKDOWN
# ============================================================================


def parse_markdown(file_path: Path) -> str:
    """
    Lit un fichier Markdown (retourne le texte brut, pas HTML)

    Args:
        file_path: Chemin du fichier MD

    Returns:
        Contenu Markdown
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        logger.debug(f"Markdown parsé: {file_path.name}")
        return content

    except Exception as e:
        logger.error(f"Erreur parsing Markdown {file_path}: {e}")
        raise


# ============================================================================
# PARSEUR XLSX/CSV
# ============================================================================


def parse_xlsx(file_path: Path) -> str:
    """
    Extrait le contenu d'un fichier Excel

    Args:
        file_path: Chemin du fichier XLSX

    Returns:
        Texte formaté
    """
    try:
        df = pd.read_excel(file_path, sheet_name=None)  # Toutes les feuilles

        text_parts = []

        for sheet_name, sheet_df in df.items():
            text_parts.append(f"=== Feuille: {sheet_name} ===")

            # Convertir le DataFrame en texte lisible
            text_parts.append(sheet_df.to_string(index=False))

        result = "\n\n".join(text_parts)
        logger.debug(f"XLSX parsé: {file_path.name} - {len(result)} caractères")
        return result

    except Exception as e:
        logger.error(f"Erreur parsing XLSX {file_path}: {e}")
        raise


def parse_csv(file_path: Path) -> str:
    """
    Extrait le contenu d'un fichier CSV

    Args:
        file_path: Chemin du fichier CSV

    Returns:
        Texte formaté
    """
    try:
        # Essayer de détecter le séparateur
        with open(file_path, "r", encoding="utf-8") as f:
            first_line = f.readline()

        separator = "," if "," in first_line else ";"

        df = pd.read_csv(file_path, sep=separator)

        result = df.to_string(index=False)
        logger.debug(f"CSV parsé: {file_path.name} - {len(result)} caractères")
        return result

    except Exception as e:
        logger.error(f"Erreur parsing CSV {file_path}: {e}")
        raise


# ============================================================================
# PARSEUR JSON
# ============================================================================


def parse_json(file_path: Path) -> str:
    """
    Extrait le contenu d'un fichier JSON

    Args:
        file_path: Chemin du fichier JSON

    Returns:
        JSON formaté en texte lisible
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Formatter le JSON de manière lisible
        result = json.dumps(data, indent=2, ensure_ascii=False)

        logger.debug(f"JSON parsé: {file_path.name} - {len(result)} caractères")
        return result

    except Exception as e:
        logger.error(f"Erreur parsing JSON {file_path}: {e}")
        raise


# ============================================================================
# PARSEUR PPTX
# ============================================================================


def parse_pptx(file_path: Path) -> str:
    """
    Extrait le texte d'un fichier PowerPoint

    Args:
        file_path: Chemin du fichier PPTX

    Returns:
        Texte extrait
    """
    try:
        prs = Presentation(file_path)

        text_parts = []

        for slide_num, slide in enumerate(prs.slides, 1):
            slide_text = [f"--- Slide {slide_num} ---"]

            for shape in slide.shapes:
                if hasattr(shape, "text") and shape.text.strip():
                    slide_text.append(shape.text)

            if len(slide_text) > 1:  # Plus que juste le titre
                text_parts.append("\n".join(slide_text))

        result = "\n\n".join(text_parts)
        logger.debug(f"PPTX parsé: {file_path.name} - {len(result)} caractères")
        return result

    except Exception as e:
        logger.error(f"Erreur parsing PPTX {file_path}: {e}")
        raise


# ============================================================================
# PARSEUR UNIVERSEL
# ============================================================================


def parse_file(file_path: Path) -> str:
    """
    Parse automatiquement un fichier selon son extension

    Args:
        file_path: Chemin du fichier

    Returns:
        Texte extrait

    Raises:
        ValueError: Si le format n'est pas supporté
    """
    if not file_path.exists():
        raise FileNotFoundError(f"Fichier introuvable : {file_path}")

    extension = file_path.suffix.lower()

    parsers = {
        ".pdf": parse_pdf,
        ".docx": parse_docx,
        ".txt": parse_txt,
        ".md": parse_markdown,
        ".xlsx": parse_xlsx,
        ".xls": parse_xlsx,
        ".csv": parse_csv,
        ".json": parse_json,
        ".pptx": parse_pptx,
    }

    parser = parsers.get(extension)

    if parser is None:
        raise ValueError(
            f"Format de fichier non supporté : {extension}. "
            f"Formats supportés : {', '.join(parsers.keys())}"
        )

    logger.info(f"Parsing fichier : {file_path.name} ({extension})")
    return parser(file_path)


# ============================================================================
# UTILITAIRES
# ============================================================================


def get_file_info(file_path: Path) -> dict:
    """
    Récupère les informations sur un fichier

    Args:
        file_path: Chemin du fichier

    Returns:
        Dictionnaire avec les infos
    """
    stat = file_path.stat()

    return {
        "filename": file_path.name,
        "extension": file_path.suffix.lower(),
        "size_bytes": stat.st_size,
        "size_mb": round(stat.st_size / (1024 * 1024), 2),
        "created": stat.st_ctime,
        "modified": stat.st_mtime,
    }


def extract_text_preview(text: str, max_length: int = 500) -> str:
    """
    Extrait un aperçu d'un texte

    Args:
        text: Texte complet
        max_length: Longueur max de l'aperçu

    Returns:
        Aperçu du texte
    """
    if len(text) <= max_length:
        return text

    return text[:max_length] + "..."


__all__ = [
    "parse_pdf",
    "parse_docx",
    "parse_txt",
    "parse_markdown",
    "parse_xlsx",
    "parse_csv",
    "parse_json",
    "parse_pptx",
    "parse_file",
    "get_file_info",
    "extract_text_preview",
]
