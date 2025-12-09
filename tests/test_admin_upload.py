"""Unit tests for Sprint 35 Feature 35.10: File Upload Endpoint.

Tests the /admin/indexing/upload endpoint that handles multipart file uploads
for subsequent indexing via the LangGraph pipeline.
"""

import shutil
from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)


@pytest.fixture
def upload_dir(tmp_path):
    """Fixture to provide a temporary upload directory."""
    upload_path = tmp_path / "uploads"
    upload_path.mkdir(parents=True, exist_ok=True)
    yield upload_path
    # Cleanup after test
    if upload_path.exists():
        shutil.rmtree(upload_path)


@pytest.fixture
def mock_uuid():
    """Fixture to mock uuid.uuid4 for predictable upload directories."""
    with patch("uuid.uuid4") as mock:
        mock.return_value = MagicMock(hex="test-session-12345")
        mock.return_value.__str__ = lambda x: "test-session-12345"
        yield mock


class TestFileUploadEndpoint:
    """Tests for /admin/indexing/upload endpoint."""

    def test_upload_single_pdf_file(self, upload_dir, mock_uuid):
        """Test uploading a single PDF file."""
        # Create test file
        test_content = b"PDF content here"
        test_file = BytesIO(test_content)
        test_file.name = "test-document.pdf"

        # Patch Path to use our temp directory
        with patch("src.api.v1.admin.Path") as mock_path:
            mock_upload_dir = upload_dir / "test-session-12345"
            mock_upload_dir.mkdir(parents=True, exist_ok=True)
            mock_path.return_value = mock_upload_dir
            mock_path.side_effect = lambda p: Path(p) if p != "data/uploads" else upload_dir

            # Upload file
            response = client.post(
                "/api/v1/admin/indexing/upload",
                files={"files": ("test-document.pdf", test_file, "application/pdf")},
            )

            assert response.status_code == 200
            data = response.json()

            # Verify response structure
            assert "upload_dir" in data
            assert "files" in data
            assert "total_size_bytes" in data
            assert len(data["files"]) == 1

            # Verify file info
            file_info = data["files"][0]
            assert file_info["filename"] == "test-document.pdf"
            assert file_info["file_size_bytes"] == len(test_content)
            assert file_info["file_extension"] == "pdf"
            assert "file_path" in file_info

    def test_upload_multiple_files(self, upload_dir, mock_uuid):
        """Test uploading multiple files at once."""
        # Create test files
        files = [
            ("document1.pdf", b"PDF content 1", "application/pdf"),
            ("document2.docx", b"DOCX content 2", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
            ("notes.txt", b"Text content 3", "text/plain"),
        ]

        with patch("src.api.v1.admin.Path") as mock_path:
            mock_upload_dir = upload_dir / "test-session-12345"
            mock_upload_dir.mkdir(parents=True, exist_ok=True)
            mock_path.return_value = mock_upload_dir
            mock_path.side_effect = lambda p: Path(p) if p != "data/uploads" else upload_dir

            # Upload files
            response = client.post(
                "/api/v1/admin/indexing/upload",
                files=[
                    ("files", (filename, BytesIO(content), mime_type))
                    for filename, content, mime_type in files
                ],
            )

            assert response.status_code == 200
            data = response.json()

            # Verify all files uploaded
            assert len(data["files"]) == 3
            assert data["total_size_bytes"] == sum(len(content) for _, content, _ in files)

            # Verify file extensions
            extensions = {f["file_extension"] for f in data["files"]}
            assert extensions == {"pdf", "docx", "txt"}

    def test_upload_no_files_error(self):
        """Test that uploading with no files returns 400 error."""
        response = client.post("/api/v1/admin/indexing/upload")

        assert response.status_code == 422  # FastAPI validation error for missing required field

    def test_upload_file_too_large_error(self, upload_dir, mock_uuid):
        """Test that files exceeding size limit return 400 error."""
        # Create file larger than 100MB
        large_content = b"x" * (101 * 1024 * 1024)  # 101MB
        large_file = BytesIO(large_content)
        large_file.name = "huge-document.pdf"

        with patch("src.api.v1.admin.Path") as mock_path:
            mock_upload_dir = upload_dir / "test-session-12345"
            mock_upload_dir.mkdir(parents=True, exist_ok=True)
            mock_path.return_value = mock_upload_dir
            mock_path.side_effect = lambda p: Path(p) if p != "data/uploads" else upload_dir

            response = client.post(
                "/api/v1/admin/indexing/upload",
                files={"files": ("huge-document.pdf", large_file, "application/pdf")},
            )

            assert response.status_code == 400
            assert "exceeds maximum size" in response.json()["detail"]

    def test_upload_creates_unique_session_directory(self, upload_dir):
        """Test that each upload creates a unique session directory."""
        test_file = BytesIO(b"test content")
        test_file.name = "test.pdf"

        # First upload
        with patch("uuid.uuid4") as mock_uuid1, patch("src.api.v1.admin.Path") as mock_path1:
            mock_uuid1.return_value = MagicMock(hex="session-1")
            mock_uuid1.return_value.__str__ = lambda x: "session-1"

            mock_upload_dir1 = upload_dir / "session-1"
            mock_upload_dir1.mkdir(parents=True, exist_ok=True)
            mock_path1.return_value = mock_upload_dir1
            mock_path1.side_effect = lambda p: Path(p) if p != "data/uploads" else upload_dir

            response1 = client.post(
                "/api/v1/admin/indexing/upload",
                files={"files": ("test1.pdf", BytesIO(b"content1"), "application/pdf")},
            )

            assert response1.status_code == 200
            session1_dir = response1.json()["upload_dir"]

        # Second upload
        with patch("uuid.uuid4") as mock_uuid2, patch("src.api.v1.admin.Path") as mock_path2:
            mock_uuid2.return_value = MagicMock(hex="session-2")
            mock_uuid2.return_value.__str__ = lambda x: "session-2"

            mock_upload_dir2 = upload_dir / "session-2"
            mock_upload_dir2.mkdir(parents=True, exist_ok=True)
            mock_path2.return_value = mock_upload_dir2
            mock_path2.side_effect = lambda p: Path(p) if p != "data/uploads" else upload_dir

            response2 = client.post(
                "/api/v1/admin/indexing/upload",
                files={"files": ("test2.pdf", BytesIO(b"content2"), "application/pdf")},
            )

            assert response2.status_code == 200
            session2_dir = response2.json()["upload_dir"]

        # Verify unique directories
        assert session1_dir != session2_dir
        assert "session-1" in session1_dir
        assert "session-2" in session2_dir

    def test_upload_supported_file_formats(self, upload_dir, mock_uuid):
        """Test uploading various supported file formats."""
        supported_formats = [
            ("document.pdf", b"PDF", "application/pdf"),
            ("document.docx", b"DOCX", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
            ("slides.pptx", b"PPTX", "application/vnd.openxmlformats-officedocument.presentationml.presentation"),
            ("notes.txt", b"TXT", "text/plain"),
            ("readme.md", b"MD", "text/markdown"),
            ("page.html", b"HTML", "text/html"),
        ]

        with patch("src.api.v1.admin.Path") as mock_path:
            mock_upload_dir = upload_dir / "test-session-12345"
            mock_upload_dir.mkdir(parents=True, exist_ok=True)
            mock_path.return_value = mock_upload_dir
            mock_path.side_effect = lambda p: Path(p) if p != "data/uploads" else upload_dir

            for filename, content, mime_type in supported_formats:
                response = client.post(
                    "/api/v1/admin/indexing/upload",
                    files={"files": (filename, BytesIO(content), mime_type)},
                )

                assert response.status_code == 200, f"Failed to upload {filename}"
                data = response.json()
                assert len(data["files"]) == 1
                assert data["files"][0]["filename"] == filename

    def test_upload_file_path_contains_session_id(self, upload_dir, mock_uuid):
        """Test that uploaded file paths include the session ID."""
        test_file = BytesIO(b"content")
        test_file.name = "test.pdf"

        with patch("src.api.v1.admin.Path") as mock_path:
            mock_upload_dir = upload_dir / "test-session-12345"
            mock_upload_dir.mkdir(parents=True, exist_ok=True)
            mock_path.return_value = mock_upload_dir
            mock_path.side_effect = lambda p: Path(p) if p != "data/uploads" else upload_dir

            response = client.post(
                "/api/v1/admin/indexing/upload",
                files={"files": ("test.pdf", test_file, "application/pdf")},
            )

            assert response.status_code == 200
            data = response.json()

            file_path = data["files"][0]["file_path"]
            assert "test-session-12345" in file_path
            assert "test.pdf" in file_path

    def test_upload_preserves_original_filenames(self, upload_dir, mock_uuid):
        """Test that original filenames are preserved."""
        filenames = [
            "Document With Spaces.pdf",
            "file-with-dashes.docx",
            "file_with_underscores.txt",
            "CamelCaseFile.md",
        ]

        with patch("src.api.v1.admin.Path") as mock_path:
            mock_upload_dir = upload_dir / "test-session-12345"
            mock_upload_dir.mkdir(parents=True, exist_ok=True)
            mock_path.return_value = mock_upload_dir
            mock_path.side_effect = lambda p: Path(p) if p != "data/uploads" else upload_dir

            response = client.post(
                "/api/v1/admin/indexing/upload",
                files=[
                    ("files", (filename, BytesIO(b"content"), "application/pdf"))
                    for filename in filenames
                ],
            )

            assert response.status_code == 200
            data = response.json()

            uploaded_filenames = {f["filename"] for f in data["files"]}
            assert uploaded_filenames == set(filenames)

    def test_upload_calculates_correct_total_size(self, upload_dir, mock_uuid):
        """Test that total_size_bytes is calculated correctly."""
        files = [
            ("file1.pdf", b"a" * 1000),
            ("file2.docx", b"b" * 2000),
            ("file3.txt", b"c" * 500),
        ]

        with patch("src.api.v1.admin.Path") as mock_path:
            mock_upload_dir = upload_dir / "test-session-12345"
            mock_upload_dir.mkdir(parents=True, exist_ok=True)
            mock_path.return_value = mock_upload_dir
            mock_path.side_effect = lambda p: Path(p) if p != "data/uploads" else upload_dir

            response = client.post(
                "/api/v1/admin/indexing/upload",
                files=[
                    ("files", (filename, BytesIO(content), "application/pdf"))
                    for filename, content in files
                ],
            )

            assert response.status_code == 200
            data = response.json()

            expected_total = 1000 + 2000 + 500
            assert data["total_size_bytes"] == expected_total

    def test_upload_empty_file(self, upload_dir, mock_uuid):
        """Test uploading an empty file (0 bytes)."""
        empty_file = BytesIO(b"")
        empty_file.name = "empty.txt"

        with patch("src.api.v1.admin.Path") as mock_path:
            mock_upload_dir = upload_dir / "test-session-12345"
            mock_upload_dir.mkdir(parents=True, exist_ok=True)
            mock_path.return_value = mock_upload_dir
            mock_path.side_effect = lambda p: Path(p) if p != "data/uploads" else upload_dir

            response = client.post(
                "/api/v1/admin/indexing/upload",
                files={"files": ("empty.txt", empty_file, "text/plain")},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["files"][0]["file_size_bytes"] == 0


@pytest.mark.integration
class TestFileUploadIntegration:
    """Integration tests for file upload with indexing pipeline."""

    def test_upload_then_index_workflow(self, upload_dir, mock_uuid):
        """Test complete workflow: upload files → start indexing."""
        # Step 1: Upload files
        with patch("src.api.v1.admin.Path") as mock_path:
            mock_upload_dir = upload_dir / "test-session-12345"
            mock_upload_dir.mkdir(parents=True, exist_ok=True)
            mock_path.return_value = mock_upload_dir
            mock_path.side_effect = lambda p: Path(p) if p != "data/uploads" else upload_dir

            upload_response = client.post(
                "/api/v1/admin/indexing/upload",
                files={"files": ("test.pdf", BytesIO(b"content"), "application/pdf")},
            )

            assert upload_response.status_code == 200
            upload_data = upload_response.json()
            file_paths = [f["file_path"] for f in upload_data["files"]]

        # Step 2: Verify file paths can be used with /indexing/add endpoint
        # (This would be tested in E2E tests with actual indexing)
        assert len(file_paths) == 1
        assert Path(file_paths[0]).name == "test.pdf"
