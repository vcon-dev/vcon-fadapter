"""Pytest configuration and shared fixtures."""

import os
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
import pytest


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    temp_path = tempfile.mkdtemp()
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def temp_file(temp_dir):
    """Create a temporary file path."""
    def _create_file(content=b"test content", suffix=".jpg"):
        file_path = os.path.join(temp_dir, f"test_file{suffix}")
        with open(file_path, "wb") as f:
            f.write(content)
        return file_path
    return _create_file


@pytest.fixture
def sample_image_file(temp_dir):
    """Create a sample image file for testing."""
    # Create a minimal valid PNG file (1x1 pixel)
    png_data = (
        b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
        b'\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00'
        b'\x01\x00\x00\x05\x00\x01\r\n-\xdb\x00\x00\x00\x00IEND\xaeB`\x82'
    )
    file_path = os.path.join(temp_dir, "15085551212_15085551313.png")
    with open(file_path, "wb") as f:
        f.write(png_data)
    return file_path


@pytest.fixture
def env_vars():
    """Provide environment variables for testing."""
    return {
        "WATCH_DIRECTORY": "/tmp/test_watch",
        "CONSERVER_URL": "http://localhost:8000/api/vcon",
        "CONSERVER_API_TOKEN": "test-token",
        "CONSERVER_HEADER_NAME": "x-api-token",
        "FILENAME_PATTERN": r"(\d+)_(\d+)\.(jpg|jpeg|png|gif|tiff|tif|bmp|webp)",
        "SUPPORTED_FORMATS": "jpg,jpeg,png,gif",
        "DELETE_AFTER_SEND": "false",
        "PROCESS_EXISTING": "true",
        "STATE_FILE": ".test_state.json",
        "POLL_INTERVAL": "1.0",
    }


@pytest.fixture
def mock_vcon():
    """Create a mock vCon object."""
    vcon = MagicMock()
    vcon.uuid = "test-uuid-12345"
    vcon.created_at = "2024-01-01T00:00:00Z"
    vcon.add_party = MagicMock()
    vcon.add_attachment = MagicMock()
    vcon.add_tag = MagicMock()
    vcon.post_to_url = MagicMock()
    vcon.to_json = MagicMock(return_value='{"vcon": "1.0", "uuid": "test-uuid"}')
    return vcon


@pytest.fixture
def mock_response_success():
    """Create a mock successful HTTP response."""
    response = Mock()
    response.status_code = 200
    return response


@pytest.fixture
def mock_response_error():
    """Create a mock error HTTP response."""
    response = Mock()
    response.status_code = 500
    return response


@pytest.fixture
def state_file_path(temp_dir):
    """Create a path for a state file."""
    return os.path.join(temp_dir, "test_state.json")


@pytest.fixture
def sample_state_data():
    """Sample state data for testing."""
    return {
        "/path/to/file1.jpg": {
            "vcon_uuid": "uuid-1",
            "timestamp": "2024-01-01T00:00:00",
            "status": "success"
        },
        "/path/to/file2.jpg": {
            "vcon_uuid": "uuid-2",
            "timestamp": "2024-01-01T01:00:00",
            "status": "failed"
        }
    }

