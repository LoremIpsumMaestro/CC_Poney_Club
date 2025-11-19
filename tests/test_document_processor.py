"""
Tests pour le document processor
"""

import pytest
from pathlib import Path
from app.core.document_processor import DocumentProcessor


@pytest.mark.unit
class TestDocumentProcessor:
    """Tests du traitement de documents"""

    @pytest.fixture
    def processor(self):
        """Instance du processeur"""
        return DocumentProcessor(chunk_size=500, chunk_overlap=100)

    def test_initialization(self, processor):
        """Test initialisation"""
        assert processor.chunk_size == 500
        assert processor.chunk_overlap == 100
        assert processor.text_splitter is not None

    def test_chunk_text(self, processor, sample_legal_text):
        """Test découpage de texte"""
        chunks, metadatas = processor.chunk_text(
            sample_legal_text, metadata={"source": "test"}
        )

        assert len(chunks) > 0
        assert len(chunks) == len(metadatas)
        assert all(isinstance(chunk, str) for chunk in chunks)
        assert all(metadata["source"] == "test" for metadata in metadatas)
        assert all("chunk_index" in metadata for metadata in metadatas)

    def test_chunk_text_with_metadata(self, processor, sample_legal_text):
        """Test chunking avec métadonnées"""
        base_metadata = {"source": "Code Civil", "year": 2024}
        chunks, metadatas = processor.chunk_text(sample_legal_text, metadata=base_metadata)

        for metadata in metadatas:
            assert metadata["source"] == "Code Civil"
            assert metadata["year"] == 2024
            assert "chunk_index" in metadata
            assert "chunk_size" in metadata
            assert "total_chunks" in metadata

    def test_clean_text(self, processor):
        """Test nettoyage de texte"""
        dirty_text = "Texte   avec    espaces\n\n\nmultiples\n\n\nligne"
        clean = processor._clean_text(dirty_text)

        assert "  " not in clean  # Pas d'espaces multiples
        assert "\n\n\n" not in clean  # Pas de lignes vides multiples
        assert clean.startswith("Texte")

    def test_extract_legal_metadata(self, processor, sample_legal_text):
        """Test extraction de métadonnées juridiques"""
        metadata = processor.extract_legal_metadata(sample_legal_text)

        assert "articles" in metadata or len(metadata) > 0
        # Le texte contient "Code Civil"
        if "code_type" in metadata:
            assert "civil" in metadata["code_type"].lower()

    def test_merge_small_chunks(self, processor):
        """Test fusion de petits chunks"""
        small_chunks = ["Court", "Petit", "Chunk assez long pour ne pas être fusionné"]
        metadatas = [{"index": i} for i in range(3)]

        merged_chunks, merged_metadatas = processor.merge_small_chunks(
            small_chunks, metadatas, min_size=20
        )

        # Les 2 premiers devraient être fusionnés
        assert len(merged_chunks) < len(small_chunks)

    def test_chunk_text_empty_string(self, processor):
        """Test chunking avec string vide"""
        chunks, metadatas = processor.chunk_text("")

        assert len(chunks) == 0
        assert len(metadatas) == 0

    def test_chunk_size_respected(self, processor):
        """Test que la taille des chunks est respectée"""
        long_text = "Texte juridique. " * 200
        chunks, _ = processor.chunk_text(long_text)

        for chunk in chunks:
            # Tous les chunks (sauf peut-être le dernier) doivent être <= chunk_size
            assert len(chunk) <= processor.chunk_size + 100  # Marge de tolérance


@pytest.mark.unit
class TestDocumentProcessorWithFiles:
    """Tests avec des fichiers réels"""

    @pytest.fixture
    def processor(self):
        """Instance du processeur"""
        return DocumentProcessor()

    def test_process_txt_file(self, processor, temp_txt_file):
        """Test traitement d'un fichier TXT"""
        chunks, metadatas = processor.process_file(temp_txt_file)

        assert len(chunks) > 0
        assert all(metadata["filename"] == temp_txt_file.name for metadata in metadatas)
        assert all(metadata["file_type"] == ".txt" for metadata in metadatas)

    def test_process_file_with_custom_metadata(self, processor, temp_txt_file):
        """Test traitement avec métadonnées personnalisées"""
        custom_metadata = {"author": "Test Author", "category": "contrat"}
        chunks, metadatas = processor.process_file(temp_txt_file, metadata=custom_metadata)

        for metadata in metadatas:
            assert metadata["author"] == "Test Author"
            assert metadata["category"] == "contrat"
            assert metadata["filename"] == temp_txt_file.name

    def test_process_legal_document(self, processor, temp_txt_file):
        """Test traitement d'un document juridique"""
        chunks, metadatas = processor.process_legal_document(
            temp_txt_file, document_type="code"
        )

        assert len(chunks) > 0
        assert all(metadata["document_type"] == "code" for metadata in metadatas)

    def test_process_nonexistent_file(self, processor):
        """Test traitement d'un fichier inexistant"""
        with pytest.raises(FileNotFoundError):
            processor.process_file(Path("/nonexistent/file.txt"))


@pytest.mark.unit
class TestBatchProcessing:
    """Tests du traitement batch"""

    @pytest.fixture
    def processor(self):
        """Instance du processeur"""
        return DocumentProcessor()

    def test_batch_process_directory(self, processor, tmp_path):
        """Test traitement d'un répertoire"""
        # Créer plusieurs fichiers de test
        for i in range(3):
            (tmp_path / f"doc{i}.txt").write_text(f"Contenu du document {i}")

        all_chunks, all_metadatas = processor.batch_process_directory(
            tmp_path, document_type="loi", file_pattern="*.txt"
        )

        assert len(all_chunks) >= 3  # Au moins 1 chunk par fichier
        assert len(all_chunks) == len(all_metadatas)
        assert all(m["document_type"] == "loi" for m in all_metadatas)

    def test_batch_process_empty_directory(self, processor, tmp_path):
        """Test traitement d'un répertoire vide"""
        all_chunks, all_metadatas = processor.batch_process_directory(tmp_path)

        assert len(all_chunks) == 0
        assert len(all_metadatas) == 0
