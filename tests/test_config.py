"""Tests for config.py module."""

import os
import pytest
from unittest.mock import patch, mock_open, MagicMock
from fax_adapter.config import Config


class TestConfig:
    """Test cases for Config class."""
    
    def test_config_required_variables_missing(self):
        """Test that missing required variables raise ValueError."""
        with patch.dict(os.environ, {}, clear=True):
            with patch("fax_adapter.config.load_dotenv", MagicMock()):
                with pytest.raises(ValueError, match="WATCH_DIRECTORY"):
                    Config()
    
    def test_config_watch_directory_missing(self):
        """Test that missing WATCH_DIRECTORY raises ValueError."""
        with patch.dict(os.environ, {"CONSERVER_URL": "http://test.com"}, clear=True):
            with patch("fax_adapter.config.load_dotenv", MagicMock()):
                with pytest.raises(ValueError, match="WATCH_DIRECTORY"):
                    Config()
    
    def test_config_conserver_url_missing(self):
        """Test that missing CONSERVER_URL raises ValueError."""
        with patch.dict(os.environ, {"WATCH_DIRECTORY": "/tmp"}, clear=True):
            with patch("fax_adapter.config.load_dotenv", MagicMock()):
                with pytest.raises(ValueError, match="CONSERVER_URL"):
                    Config()
    
    def test_config_minimal_required(self, env_vars):
        """Test config with minimal required variables."""
        with patch.dict(os.environ, env_vars, clear=True):
            config = Config()
            assert config.watch_directory == "/tmp/test_watch"
            assert config.conserver_url == "http://localhost:8000/api/vcon"
    
    def test_config_defaults(self, env_vars):
        """Test config default values."""
        minimal_vars = {
            "WATCH_DIRECTORY": "/tmp",
            "CONSERVER_URL": "http://test.com"
        }
        with patch.dict(os.environ, minimal_vars, clear=True):
            with patch("fax_adapter.config.load_dotenv", MagicMock()):
                config = Config()
                assert config.conserver_header_name == "x-conserver-api-token"
                assert config.delete_after_send is False
                assert config.process_existing is True
                assert config.state_file == ".fax_adapter_state.json"
                assert config.poll_interval == 1.0
                assert "jpg" in config.supported_formats
                assert config.ingress_lists == []
    
    def test_config_custom_values(self, env_vars):
        """Test config with custom values."""
        with patch.dict(os.environ, env_vars, clear=True):
            config = Config()
            assert config.conserver_api_token == "test-token"
            assert config.conserver_header_name == "x-api-token"
            assert config.delete_after_send is False
            assert config.process_existing is True
            assert config.state_file == ".test_state.json"
            assert config.poll_interval == 1.0
    
    def test_config_delete_after_send_true(self, env_vars):
        """Test DELETE_AFTER_SEND set to true."""
        env_vars["DELETE_AFTER_SEND"] = "true"
        with patch.dict(os.environ, env_vars, clear=True):
            config = Config()
            assert config.delete_after_send is True
    
    def test_config_delete_after_send_yes(self, env_vars):
        """Test DELETE_AFTER_SEND set to yes."""
        env_vars["DELETE_AFTER_SEND"] = "yes"
        with patch.dict(os.environ, env_vars, clear=True):
            config = Config()
            assert config.delete_after_send is True
    
    def test_config_delete_after_send_one(self, env_vars):
        """Test DELETE_AFTER_SEND set to 1."""
        env_vars["DELETE_AFTER_SEND"] = "1"
        with patch.dict(os.environ, env_vars, clear=True):
            config = Config()
            assert config.delete_after_send is True
    
    def test_config_process_existing_false(self, env_vars):
        """Test PROCESS_EXISTING set to false."""
        env_vars["PROCESS_EXISTING"] = "false"
        with patch.dict(os.environ, env_vars, clear=True):
            config = Config()
            assert config.process_existing is False
    
    def test_config_supported_formats(self, env_vars):
        """Test supported formats parsing."""
        env_vars["SUPPORTED_FORMATS"] = "jpg, png, gif"
        with patch.dict(os.environ, env_vars, clear=True):
            config = Config()
            assert "jpg" in config.supported_formats
            assert "png" in config.supported_formats
            assert "gif" in config.supported_formats
            assert all(isinstance(fmt, str) for fmt in config.supported_formats)
    
    def test_config_custom_filename_pattern(self, env_vars):
        """Test custom filename pattern."""
        custom_pattern = r"fax_(\d+)_(\d+)\.(\w+)"
        env_vars["FILENAME_PATTERN"] = custom_pattern
        with patch.dict(os.environ, env_vars, clear=True):
            config = Config()
            assert config.filename_pattern == custom_pattern
            regex = config.get_filename_regex()
            assert regex.pattern == custom_pattern
    
    def test_config_get_headers_no_token(self, env_vars):
        """Test get_headers without API token."""
        env_vars.pop("CONSERVER_API_TOKEN", None)
        with patch.dict(os.environ, env_vars, clear=True):
            config = Config()
            headers = config.get_headers()
            assert headers == {"Content-Type": "application/json"}
    
    def test_config_get_headers_with_token(self, env_vars):
        """Test get_headers with API token."""
        with patch.dict(os.environ, env_vars, clear=True):
            config = Config()
            headers = config.get_headers()
            assert headers["Content-Type"] == "application/json"
            assert headers["x-api-token"] == "test-token"
    
    def test_config_get_headers_custom_header_name(self, env_vars):
        """Test get_headers with custom header name."""
        env_vars["CONSERVER_HEADER_NAME"] = "x-custom-header"
        with patch.dict(os.environ, env_vars, clear=True):
            config = Config()
            headers = config.get_headers()
            assert "x-custom-header" in headers
            assert headers["x-custom-header"] == "test-token"
    
    def test_config_get_filename_regex(self, env_vars):
        """Test get_filename_regex returns compiled pattern."""
        with patch.dict(os.environ, env_vars, clear=True):
            config = Config()
            regex = config.get_filename_regex()
            assert hasattr(regex, "match")
            # Test it matches expected pattern
            match = regex.match("15085551212_15085551313.jpg")
            assert match is not None
            assert match.groups()[0] == "15085551212"
            assert match.groups()[1] == "15085551313"
    
    def test_config_custom_env_file(self, temp_dir, env_vars):
        """Test loading config from custom env file."""
        env_file = os.path.join(temp_dir, ".env")
        env_content = "\n".join([f"{k}={v}" for k, v in env_vars.items()])
        
        with open(env_file, "w") as f:
            f.write(env_content)
        
        with patch.dict(os.environ, {}, clear=True):
            config = Config(env_file=env_file)
            assert config.watch_directory == env_vars["WATCH_DIRECTORY"]
            assert config.conserver_url == env_vars["CONSERVER_URL"]
    
    def test_config_ingress_lists_empty(self, env_vars):
        """Test ingress_lists with empty value."""
        env_vars["INGRESS_LISTS"] = ""
        with patch.dict(os.environ, env_vars, clear=True):
            config = Config()
            assert config.ingress_lists == []
    
    def test_config_ingress_lists_single(self, env_vars):
        """Test ingress_lists with single value."""
        env_vars["INGRESS_LISTS"] = "fax_processing"
        with patch.dict(os.environ, env_vars, clear=True):
            config = Config()
            assert config.ingress_lists == ["fax_processing"]
    
    def test_config_ingress_lists_multiple(self, env_vars):
        """Test ingress_lists with multiple values."""
        env_vars["INGRESS_LISTS"] = "fax_processing,main_ingress,backup_queue"
        with patch.dict(os.environ, env_vars, clear=True):
            config = Config()
            assert config.ingress_lists == ["fax_processing", "main_ingress", "backup_queue"]
    
    def test_config_ingress_lists_with_spaces(self, env_vars):
        """Test ingress_lists with spaces around values."""
        env_vars["INGRESS_LISTS"] = " fax_processing , main_ingress , backup_queue "
        with patch.dict(os.environ, env_vars, clear=True):
            config = Config()
            assert config.ingress_lists == ["fax_processing", "main_ingress", "backup_queue"]
    
    def test_config_ingress_lists_not_set(self, env_vars):
        """Test ingress_lists when not set."""
        env_vars.pop("INGRESS_LISTS", None)
        with patch.dict(os.environ, env_vars, clear=True):
            with patch("fax_adapter.config.load_dotenv", MagicMock()):
                config = Config()
                assert config.ingress_lists == []

