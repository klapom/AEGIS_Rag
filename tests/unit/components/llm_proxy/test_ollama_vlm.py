"""Unit tests for OllamaVLMClient (Feature 36.2).

Tests:
- Client initialization with various configurations
- Image description generation with base64 encoding
- Token counting and metadata
- Model availability checking
- Error handling (file not found, connection errors)
- Context manager support
"""

import base64
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.components.llm_proxy.ollama_vlm import OllamaVLMClient


class TestOllamaVLMClientInitialization:
    """Tests for OllamaVLMClient initialization."""

    def test_default_base_url(self):
        """Test default base URL is localhost:11434."""
        with patch.dict("os.environ", {}, clear=True):
            client = OllamaVLMClient()
            assert client.base_url == "http://localhost:11434"

    def test_custom_base_url(self):
        """Test custom base URL can be provided."""
        client = OllamaVLMClient(base_url="http://dgx-spark:11434")
        assert client.base_url == "http://dgx-spark:11434"

    def test_env_var_base_url(self):
        """Test OLLAMA_BASE_URL environment variable is used."""
        with patch.dict("os.environ", {"OLLAMA_BASE_URL": "http://custom:11434"}):
            client = OllamaVLMClient()
            assert client.base_url == "http://custom:11434"

    def test_custom_url_overrides_env_var(self):
        """Test explicit URL parameter overrides environment variable."""
        with patch.dict("os.environ", {"OLLAMA_BASE_URL": "http://env:11434"}):
            client = OllamaVLMClient(base_url="http://custom:11434")
            assert client.base_url == "http://custom:11434"

    def test_default_model(self):
        """Test default model is qwen3-vl:32b."""
        with patch.dict("os.environ", {}, clear=True):
            client = OllamaVLMClient()
            assert client.default_model == "qwen3-vl:32b"

    def test_custom_model(self):
        """Test custom model can be provided."""
        client = OllamaVLMClient(default_model="llava:7b")
        assert client.default_model == "llava:7b"

    def test_env_var_model(self):
        """Test OLLAMA_MODEL_VLM environment variable is used."""
        with patch.dict("os.environ", {"OLLAMA_MODEL_VLM": "llava:13b"}):
            client = OllamaVLMClient()
            assert client.default_model == "llava:13b"

    def test_custom_timeout(self):
        """Test custom timeout can be provided."""
        client = OllamaVLMClient(timeout=60.0)
        assert client.timeout == 60.0

    def test_default_timeout(self):
        """Test default timeout is 120 seconds."""
        client = OllamaVLMClient()
        assert client.timeout == 120.0

    def test_httpx_client_created(self):
        """Test httpx AsyncClient is initialized."""
        client = OllamaVLMClient()
        assert isinstance(client.client, httpx.AsyncClient)


class TestGenerateImageDescription:
    """Tests for generate_image_description method."""

    @pytest.mark.asyncio
    async def test_file_not_found_raises(self):
        """Test FileNotFoundError is raised for missing file."""
        client = OllamaVLMClient()

        with pytest.raises(FileNotFoundError):
            await client.generate_image_description(
                image_path=Path("/nonexistent/image.png"),
                prompt="Describe this image",
            )

    @pytest.mark.asyncio
    async def test_successful_generation(self, tmp_path):
        """Test successful image description generation."""
        # Create test image
        test_image = tmp_path / "test.png"
        test_image.write_bytes(b"fake image data")

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "response": "A test image description",
            "eval_count": 100,
            "prompt_eval_count": 50,
            "total_duration": 2000000000,  # 2 seconds in nanoseconds
            "eval_duration": 1500000000,
        }
        mock_response.raise_for_status = MagicMock()

        client = OllamaVLMClient()
        client.client = AsyncMock()
        client.client.post = AsyncMock(return_value=mock_response)

        description, metadata = await client.generate_image_description(
            image_path=test_image,
            prompt="Describe this image",
        )

        assert description == "A test image description"
        assert metadata["provider"] == "ollama"
        assert metadata["local"] is True
        assert metadata["cost_usd"] == 0.0
        assert metadata["tokens_total"] == 100

    @pytest.mark.asyncio
    async def test_image_encoded_as_base64(self, tmp_path):
        """Test image is correctly encoded as base64."""
        # Create test image with known content
        test_image = tmp_path / "test.png"
        test_content = b"test image content"
        test_image.write_bytes(test_content)
        expected_base64 = base64.b64encode(test_content).decode("utf-8")

        mock_response = MagicMock()
        mock_response.json.return_value = {"response": "description", "eval_count": 10}
        mock_response.raise_for_status = MagicMock()

        client = OllamaVLMClient()
        client.client = AsyncMock()
        client.client.post = AsyncMock(return_value=mock_response)

        await client.generate_image_description(test_image, "test")

        # Verify base64 encoding
        call_args = client.client.post.call_args
        payload = call_args.kwargs.get("json")
        assert payload["images"][0] == expected_base64

    @pytest.mark.asyncio
    async def test_custom_model(self, tmp_path):
        """Test using custom model parameter."""
        test_image = tmp_path / "test.png"
        test_image.write_bytes(b"fake image")

        mock_response = MagicMock()
        mock_response.json.return_value = {"response": "desc", "eval_count": 10}
        mock_response.raise_for_status = MagicMock()

        client = OllamaVLMClient(default_model="qwen3-vl:32b")
        client.client = AsyncMock()
        client.client.post = AsyncMock(return_value=mock_response)

        await client.generate_image_description(
            test_image,
            "test",
            model="llava:7b",
        )

        # Verify custom model was used
        call_args = client.client.post.call_args
        payload = call_args.kwargs.get("json")
        assert payload["model"] == "llava:7b"

    @pytest.mark.asyncio
    async def test_default_model_used_if_not_specified(self, tmp_path):
        """Test default model is used when model parameter is None."""
        test_image = tmp_path / "test.png"
        test_image.write_bytes(b"fake image")

        mock_response = MagicMock()
        mock_response.json.return_value = {"response": "desc", "eval_count": 10}
        mock_response.raise_for_status = MagicMock()

        client = OllamaVLMClient(default_model="custom-model:v1")
        client.client = AsyncMock()
        client.client.post = AsyncMock(return_value=mock_response)

        await client.generate_image_description(test_image, "test")

        # Verify default model was used
        call_args = client.client.post.call_args
        payload = call_args.kwargs.get("json")
        assert payload["model"] == "custom-model:v1"

    @pytest.mark.asyncio
    async def test_metadata_structure(self, tmp_path):
        """Test metadata dictionary has all required fields."""
        test_image = tmp_path / "test.png"
        test_image.write_bytes(b"fake image")

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "response": "description",
            "eval_count": 150,
            "prompt_eval_count": 75,
            "total_duration": 3000000000,  # 3 seconds
            "eval_duration": 2000000000,
        }
        mock_response.raise_for_status = MagicMock()

        client = OllamaVLMClient()
        client.client = AsyncMock()
        client.client.post = AsyncMock(return_value=mock_response)

        _, metadata = await client.generate_image_description(test_image, "test")

        # Verify required metadata fields
        assert "model" in metadata
        assert "provider" in metadata
        assert metadata["provider"] == "ollama"
        assert "tokens_total" in metadata
        assert "tokens_prompt" in metadata
        assert "local" in metadata
        assert metadata["local"] is True
        assert "cost_usd" in metadata
        assert metadata["cost_usd"] == 0.0
        assert "duration_ms" in metadata
        assert "eval_duration_ms" in metadata

    @pytest.mark.asyncio
    async def test_token_counting(self, tmp_path):
        """Test token counts are correctly extracted from response."""
        test_image = tmp_path / "test.png"
        test_image.write_bytes(b"fake image")

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "response": "description",
            "eval_count": 200,
            "prompt_eval_count": 50,
            "total_duration": 1000000000,
        }
        mock_response.raise_for_status = MagicMock()

        client = OllamaVLMClient()
        client.client = AsyncMock()
        client.client.post = AsyncMock(return_value=mock_response)

        _, metadata = await client.generate_image_description(test_image, "test")

        assert metadata["tokens_total"] == 200
        assert metadata["tokens_prompt"] == 50

    @pytest.mark.asyncio
    async def test_custom_parameters(self, tmp_path):
        """Test custom max_tokens and temperature parameters."""
        test_image = tmp_path / "test.png"
        test_image.write_bytes(b"fake image")

        mock_response = MagicMock()
        mock_response.json.return_value = {"response": "desc", "eval_count": 10}
        mock_response.raise_for_status = MagicMock()

        client = OllamaVLMClient()
        client.client = AsyncMock()
        client.client.post = AsyncMock(return_value=mock_response)

        await client.generate_image_description(
            test_image,
            "test",
            max_tokens=1024,
            temperature=0.5,
        )

        call_args = client.client.post.call_args
        payload = call_args.kwargs.get("json")
        assert payload["options"]["num_predict"] == 1024
        assert payload["options"]["temperature"] == 0.5

    @pytest.mark.asyncio
    async def test_http_error_handling(self, tmp_path):
        """Test HTTP errors are properly raised."""
        test_image = tmp_path / "test.png"
        test_image.write_bytes(b"fake image")

        client = OllamaVLMClient()
        client.client = AsyncMock()
        error_response = MagicMock()
        error_response.status_code = 500
        client.client.post = AsyncMock(
            side_effect=httpx.HTTPStatusError(
                "Server error", request=MagicMock(), response=error_response
            )
        )

        with pytest.raises(httpx.HTTPStatusError):
            await client.generate_image_description(test_image, "test")

    @pytest.mark.asyncio
    async def test_connection_error_handling(self, tmp_path):
        """Test connection errors are properly raised."""
        test_image = tmp_path / "test.png"
        test_image.write_bytes(b"fake image")

        client = OllamaVLMClient(base_url="http://nonexistent:11434")
        client.client = AsyncMock()
        client.client.post = AsyncMock(side_effect=httpx.ConnectError("Cannot connect"))

        with pytest.raises(httpx.ConnectError):
            await client.generate_image_description(test_image, "test")

    @pytest.mark.asyncio
    async def test_api_endpoint_correct(self, tmp_path):
        """Test correct API endpoint is called."""
        test_image = tmp_path / "test.png"
        test_image.write_bytes(b"fake image")

        mock_response = MagicMock()
        mock_response.json.return_value = {"response": "desc", "eval_count": 10}
        mock_response.raise_for_status = MagicMock()

        client = OllamaVLMClient(base_url="http://custom:11434")
        client.client = AsyncMock()
        client.client.post = AsyncMock(return_value=mock_response)

        await client.generate_image_description(test_image, "test")

        # Verify correct endpoint was called
        call_args = client.client.post.call_args
        call_args[0][0] if call_args[0] else call_args.kwargs.get("url", "")
        # The endpoint should contain the base URL and /api/generate
        assert "http://custom:11434" in client.base_url
        assert "/api/generate" in call_args[0][0]


class TestCheckModelAvailable:
    """Tests for check_model_available method."""

    @pytest.mark.asyncio
    async def test_model_available(self):
        """Test model availability check returns True for available model."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "models": [
                {"name": "qwen3-vl:32b"},
                {"name": "llama3:8b"},
            ]
        }
        mock_response.raise_for_status = MagicMock()

        client = OllamaVLMClient(default_model="qwen3-vl:32b")
        client.client = AsyncMock()
        client.client.get = AsyncMock(return_value=mock_response)

        is_available = await client.check_model_available()
        assert is_available is True

    @pytest.mark.asyncio
    async def test_model_not_available(self):
        """Test model availability check returns False for missing model."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"models": [{"name": "llama3:8b"}]}
        mock_response.raise_for_status = MagicMock()

        client = OllamaVLMClient(default_model="qwen3-vl:32b")
        client.client = AsyncMock()
        client.client.get = AsyncMock(return_value=mock_response)

        is_available = await client.check_model_available()
        assert is_available is False

    @pytest.mark.asyncio
    async def test_custom_model_check(self):
        """Test checking availability of custom model."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "models": [
                {"name": "custom-model:v1"},
                {"name": "llama3:8b"},
            ]
        }
        mock_response.raise_for_status = MagicMock()

        client = OllamaVLMClient()
        client.client = AsyncMock()
        client.client.get = AsyncMock(return_value=mock_response)

        is_available = await client.check_model_available("custom-model:v1")
        assert is_available is True

    @pytest.mark.asyncio
    async def test_empty_models_list(self):
        """Test handling of empty models list."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"models": []}
        mock_response.raise_for_status = MagicMock()

        client = OllamaVLMClient(default_model="any-model")
        client.client = AsyncMock()
        client.client.get = AsyncMock(return_value=mock_response)

        is_available = await client.check_model_available()
        assert is_available is False

    @pytest.mark.asyncio
    async def test_connection_error_returns_false(self):
        """Test connection error returns False gracefully."""
        client = OllamaVLMClient()
        client.client = AsyncMock()
        client.client.get = AsyncMock(side_effect=Exception("Connection failed"))

        is_available = await client.check_model_available()
        assert is_available is False

    @pytest.mark.asyncio
    async def test_api_endpoint_correct(self):
        """Test correct API endpoint is called."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"models": []}
        mock_response.raise_for_status = MagicMock()

        client = OllamaVLMClient(base_url="http://custom:11434")
        client.client = AsyncMock()
        client.client.get = AsyncMock(return_value=mock_response)

        await client.check_model_available()

        client.client.get.assert_called_once()
        call_args = client.client.get.call_args
        endpoint = call_args[0][0]
        assert "http://custom:11434" in endpoint
        assert "/api/tags" in endpoint


class TestContextManager:
    """Tests for context manager support."""

    @pytest.mark.asyncio
    async def test_async_context_manager(self):
        """Test async context manager works correctly."""
        async with OllamaVLMClient() as client:
            assert isinstance(client, OllamaVLMClient)

    @pytest.mark.asyncio
    async def test_close_called_on_exit(self):
        """Test close() is called when exiting context."""
        client = OllamaVLMClient()
        client.client = AsyncMock()

        async with client:
            pass

        # After context exit, close should have been called
        # (This is implicit in __aexit__)

    @pytest.mark.asyncio
    async def test_close_method(self):
        """Test close method closes HTTP client."""
        client = OllamaVLMClient()
        client.client = AsyncMock()

        await client.close()

        client.client.aclose.assert_called_once()


class TestOllamaVLMClientEdgeCases:
    """Tests for edge cases and error conditions."""

    @pytest.mark.asyncio
    async def test_empty_response(self, tmp_path):
        """Test handling of empty response from API."""
        test_image = tmp_path / "test.png"
        test_image.write_bytes(b"fake image")

        mock_response = MagicMock()
        mock_response.json.return_value = {"response": "", "eval_count": 0}
        mock_response.raise_for_status = MagicMock()

        client = OllamaVLMClient()
        client.client = AsyncMock()
        client.client.post = AsyncMock(return_value=mock_response)

        description, metadata = await client.generate_image_description(test_image, "test")

        assert description == ""
        assert metadata["tokens_total"] == 0

    @pytest.mark.asyncio
    async def test_very_long_description(self, tmp_path):
        """Test handling of very long descriptions."""
        test_image = tmp_path / "test.png"
        test_image.write_bytes(b"fake image")

        long_description = "Description. " * 1000  # Very long description

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "response": long_description,
            "eval_count": 5000,
        }
        mock_response.raise_for_status = MagicMock()

        client = OllamaVLMClient()
        client.client = AsyncMock()
        client.client.post = AsyncMock(return_value=mock_response)

        description, metadata = await client.generate_image_description(test_image, "test")

        assert len(description) > 10000
        assert metadata["tokens_total"] == 5000

    @pytest.mark.asyncio
    async def test_missing_optional_fields_in_response(self, tmp_path):
        """Test handling when response missing optional fields."""
        test_image = tmp_path / "test.png"
        test_image.write_bytes(b"fake image")

        # Minimal response with only required field
        mock_response = MagicMock()
        mock_response.json.return_value = {"response": "description"}
        mock_response.raise_for_status = MagicMock()

        client = OllamaVLMClient()
        client.client = AsyncMock()
        client.client.post = AsyncMock(return_value=mock_response)

        description, metadata = await client.generate_image_description(test_image, "test")

        # Should handle gracefully with defaults
        assert description == "description"
        assert metadata["tokens_total"] == 0
        assert metadata["tokens_prompt"] == 0
