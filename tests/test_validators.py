"""
Tests pour les validateurs
"""

import pytest
from app.utils.validators import (
    validate_file_extension,
    validate_file_size,
    validate_upload,
    validate_query,
    validate_user_id,
    validate_conversation_title,
    validate_document_category,
    validate_metadata,
    validate_chunk_params,
    ValidationError,
    ensure_valid,
)


@pytest.mark.unit
class TestFileValidation:
    """Tests de validation de fichiers"""

    def test_validate_file_extension_valid(self):
        """Test extension valide"""
        is_valid, error = validate_file_extension("document.pdf")
        assert is_valid is True
        assert error == ""

    def test_validate_file_extension_invalid(self):
        """Test extension invalide"""
        is_valid, error = validate_file_extension("document.exe")
        assert is_valid is False
        assert "non autorisée" in error.lower()

    def test_validate_file_extension_no_extension(self):
        """Test fichier sans extension"""
        is_valid, error = validate_file_extension("document")
        assert is_valid is False
        assert "extension" in error.lower()

    def test_validate_file_size_valid(self):
        """Test taille valide"""
        is_valid, error = validate_file_size(1024 * 1024)  # 1 MB
        assert is_valid is True
        assert error == ""

    def test_validate_file_size_too_large(self):
        """Test fichier trop volumineux"""
        is_valid, error = validate_file_size(100 * 1024 * 1024)  # 100 MB
        assert is_valid is False
        assert "trop volumineux" in error.lower()

    def test_validate_file_size_zero(self):
        """Test fichier vide"""
        is_valid, error = validate_file_size(0)
        assert is_valid is False
        assert "vide" in error.lower()

    def test_validate_upload_valid(self):
        """Test upload valide"""
        is_valid, error = validate_upload("document.pdf", 1024 * 1024)
        assert is_valid is True

    def test_validate_upload_invalid_extension(self):
        """Test upload avec extension invalide"""
        is_valid, error = validate_upload("malware.exe", 1024)
        assert is_valid is False


@pytest.mark.unit
class TestQueryValidation:
    """Tests de validation de requêtes"""

    def test_validate_query_valid(self):
        """Test requête valide"""
        is_valid, error = validate_query("Qu'est-ce que l'article 1240 ?")
        assert is_valid is True

    def test_validate_query_too_short(self):
        """Test requête trop courte"""
        is_valid, error = validate_query("ab")
        assert is_valid is False
        assert "trop courte" in error.lower()

    def test_validate_query_empty(self):
        """Test requête vide"""
        is_valid, error = validate_query("")
        assert is_valid is False
        assert "vide" in error.lower()

    def test_validate_query_too_long(self):
        """Test requête trop longue"""
        long_query = "a" * 6000
        is_valid, error = validate_query(long_query)
        assert is_valid is False
        assert "trop longue" in error.lower()


@pytest.mark.unit
class TestUserIDValidation:
    """Tests de validation d'UUID"""

    def test_validate_user_id_valid(self):
        """Test UUID valide"""
        is_valid, error = validate_user_id("550e8400-e29b-41d4-a716-446655440000")
        assert is_valid is True

    def test_validate_user_id_invalid_format(self):
        """Test UUID invalide"""
        is_valid, error = validate_user_id("not-a-uuid")
        assert is_valid is False
        assert "invalide" in error.lower()

    def test_validate_user_id_empty(self):
        """Test UUID vide"""
        is_valid, error = validate_user_id("")
        assert is_valid is False


@pytest.mark.unit
class TestConversationValidation:
    """Tests de validation de conversations"""

    def test_validate_conversation_title_valid(self):
        """Test titre valide"""
        is_valid, error = validate_conversation_title("Ma conversation juridique")
        assert is_valid is True

    def test_validate_conversation_title_empty(self):
        """Test titre vide"""
        is_valid, error = validate_conversation_title("")
        assert is_valid is False

    def test_validate_conversation_title_too_long(self):
        """Test titre trop long"""
        long_title = "a" * 250
        is_valid, error = validate_conversation_title(long_title)
        assert is_valid is False


@pytest.mark.unit
class TestDocumentCategoryValidation:
    """Tests de validation de catégories"""

    def test_validate_document_category_valid(self):
        """Test catégorie valide"""
        is_valid, error = validate_document_category("contrat")
        assert is_valid is True

    def test_validate_document_category_invalid(self):
        """Test catégorie invalide"""
        is_valid, error = validate_document_category("invalid_category")
        assert is_valid is False


@pytest.mark.unit
class TestMetadataValidation:
    """Tests de validation de métadonnées"""

    def test_validate_metadata_valid(self):
        """Test métadonnées valides"""
        metadata = {"source": "Code Civil", "article": "Art. 1240"}
        is_valid, error = validate_metadata(metadata)
        assert is_valid is True

    def test_validate_metadata_not_dict(self):
        """Test métadonnées non-dictionnaire"""
        is_valid, error = validate_metadata("not a dict")
        assert is_valid is False

    def test_validate_metadata_too_large(self):
        """Test métadonnées trop volumineuses"""
        large_metadata = {"data": "x" * 20000}
        is_valid, error = validate_metadata(large_metadata)
        assert is_valid is False


@pytest.mark.unit
class TestChunkParamsValidation:
    """Tests de validation des paramètres de chunking"""

    def test_validate_chunk_params_valid(self):
        """Test paramètres valides"""
        is_valid, error = validate_chunk_params(chunk_size=1000, chunk_overlap=200)
        assert is_valid is True

    def test_validate_chunk_params_size_too_small(self):
        """Test chunk_size trop petit"""
        is_valid, error = validate_chunk_params(chunk_size=50, chunk_overlap=10)
        assert is_valid is False

    def test_validate_chunk_params_overlap_negative(self):
        """Test overlap négatif"""
        is_valid, error = validate_chunk_params(chunk_size=1000, chunk_overlap=-10)
        assert is_valid is False

    def test_validate_chunk_params_overlap_too_large(self):
        """Test overlap >= chunk_size"""
        is_valid, error = validate_chunk_params(chunk_size=1000, chunk_overlap=1500)
        assert is_valid is False


@pytest.mark.unit
class TestEnsureValid:
    """Tests de la fonction ensure_valid"""

    def test_ensure_valid_success(self):
        """Test validation réussie"""
        try:
            ensure_valid((True, ""))
        except ValidationError:
            pytest.fail("ValidationError levée à tort")

    def test_ensure_valid_failure(self):
        """Test validation échouée"""
        with pytest.raises(ValidationError):
            ensure_valid((False, "Erreur de validation"))
