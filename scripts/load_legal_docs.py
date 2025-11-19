"""
Script de chargement des documents juridiques dans la base de connaissances
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.document_processor import get_document_processor
from app.core.vector_store import get_vector_store
from app.utils.logger import logger


async def load_french_laws(directory: Path = None):
    """
    Charge les lois françaises dans la base de connaissances

    Args:
        directory: Répertoire contenant les lois (défaut: data/legal_documents/french_laws)
    """
    try:
        logger.info("🚀 Chargement des lois françaises...")

        # Répertoire par défaut
        if directory is None:
            directory = Path("data/legal_documents/french_laws")

        if not directory.exists():
            logger.error(f"❌ Répertoire introuvable: {directory}")
            logger.info("Créez le répertoire et ajoutez vos fichiers de lois")
            return False

        # Initialiser les composants
        processor = get_document_processor()
        vector_store = await get_vector_store()

        # Traiter tous les documents
        logger.info(f"📂 Traitement du répertoire: {directory}")

        # Patterns de fichiers à traiter
        patterns = ["*.md", "*.pdf", "*.txt"]
        all_files = []

        for pattern in patterns:
            all_files.extend(directory.glob(pattern))

        if not all_files:
            logger.warning(f"⚠️  Aucun fichier trouvé dans {directory}")
            return False

        logger.info(f"📄 {len(all_files)} fichiers trouvés")

        # Traiter chaque fichier
        total_chunks = 0

        for file_path in all_files:
            try:
                logger.info(f"Traitement: {file_path.name}...")

                # Parser et chunker
                chunks, metadatas = processor.process_legal_document(
                    file_path, document_type="code"
                )

                # Ajouter à la base de connaissances
                ids = await vector_store.add_to_knowledge_base(
                    documents=chunks, metadatas=metadatas
                )

                logger.info(
                    f"✅ {file_path.name}: {len(chunks)} chunks ajoutés"
                )
                total_chunks += len(chunks)

            except Exception as e:
                logger.error(f"❌ Erreur {file_path.name}: {e}")
                continue

        logger.info(f"\n🎉 Chargement terminé: {total_chunks} chunks totaux")

        # Afficher les stats
        stats = vector_store.get_collection_stats("french_laws")
        logger.info(f"📊 Base de connaissances: {stats['count']} documents")

        return True

    except Exception as e:
        logger.error(f"❌ Erreur load_french_laws: {e}")
        return False


async def main():
    """Point d'entrée"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Charge les documents juridiques dans Coda2z"
    )
    parser.add_argument(
        "--dir",
        type=str,
        default=None,
        help="Répertoire contenant les lois (défaut: data/legal_documents/french_laws)",
    )

    args = parser.parse_args()

    directory = Path(args.dir) if args.dir else None

    success = await load_french_laws(directory)

    if success:
        logger.info("\n✅ Prêt à être utilisé !")
    else:
        logger.error("\n❌ Échec du chargement")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
