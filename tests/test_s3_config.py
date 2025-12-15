"""Tests for S3 configuration."""

import os
import pytest
from fax_adapter.config import Config


class TestS3Config:
    """Test S3-specific configuration."""
    
    def test_default_source_type_filesystem(self, tmp_path, monkeypatch):
        """Test that default source type is filesystem."""
        # Set up minimal filesystem config
        monkeypatch.setenv("WATCH_DIRECTORY", str(tmp_path))
        monkeypatch.setenv("CONSERVER_URL", "http://localhost:8080")
        
        config = Config()
        assert config.source_type == "filesystem"
    
    def test_s3_source_type(self, monkeypatch):
        """Test S3 source type configuration."""
        monkeypatch.setenv("SOURCE_TYPE", "s3")
        monkeypatch.setenv("S3_BUCKET_NAME", "test-bucket")
        monkeypatch.setenv("CONSERVER_URL", "http://localhost:8080")
        
        config = Config()
        assert config.source_type == "s3"
        assert config.s3_bucket_name == "test-bucket"
    
    def test_invalid_source_type(self, monkeypatch):
        """Test that invalid source type raises error."""
        monkeypatch.setenv("SOURCE_TYPE", "invalid")
        monkeypatch.setenv("CONSERVER_URL", "http://localhost:8080")
        
        with pytest.raises(ValueError, match="SOURCE_TYPE must be"):
            Config()
    
    def test_s3_requires_bucket_name(self, monkeypatch):
        """Test that S3 source type requires bucket name."""
        monkeypatch.setenv("SOURCE_TYPE", "s3")
        monkeypatch.setenv("CONSERVER_URL", "http://localhost:8080")
        
        with pytest.raises(ValueError, match="S3_BUCKET_NAME is required"):
            Config()
    
    def test_filesystem_requires_watch_directory(self, monkeypatch):
        """Test that filesystem source type requires watch directory."""
        monkeypatch.setenv("SOURCE_TYPE", "filesystem")
        monkeypatch.setenv("CONSERVER_URL", "http://localhost:8080")
        
        with pytest.raises(ValueError, match="WATCH_DIRECTORY is required"):
            Config()
    
    def test_s3_optional_settings(self, monkeypatch):
        """Test S3 optional configuration settings."""
        monkeypatch.setenv("SOURCE_TYPE", "s3")
        monkeypatch.setenv("S3_BUCKET_NAME", "test-bucket")
        monkeypatch.setenv("S3_PREFIX", "faxes/incoming/")
        monkeypatch.setenv("S3_REGION", "us-west-2")
        monkeypatch.setenv("S3_POLL_INTERVAL", "60")
        monkeypatch.setenv("S3_DELETE_AFTER_SEND", "true")
        monkeypatch.setenv("CONSERVER_URL", "http://localhost:8080")
        
        config = Config()
        assert config.s3_prefix == "faxes/incoming/"
        assert config.s3_region == "us-west-2"
        assert config.s3_poll_interval == 60.0
        assert config.s3_delete_after_send is True
    
    def test_s3_prefix_defaults_to_empty(self, monkeypatch):
        """Test that S3 prefix defaults to empty string."""
        monkeypatch.setenv("SOURCE_TYPE", "s3")
        monkeypatch.setenv("S3_BUCKET_NAME", "test-bucket")
        monkeypatch.setenv("CONSERVER_URL", "http://localhost:8080")
        
        config = Config()
        assert config.s3_prefix == ""
    
    def test_aws_credentials_config(self, monkeypatch):
        """Test AWS credentials configuration."""
        monkeypatch.setenv("SOURCE_TYPE", "s3")
        monkeypatch.setenv("S3_BUCKET_NAME", "test-bucket")
        monkeypatch.setenv("AWS_ACCESS_KEY_ID", "AKIA123")
        monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "secret123")
        monkeypatch.setenv("AWS_SESSION_TOKEN", "token123")
        monkeypatch.setenv("CONSERVER_URL", "http://localhost:8080")
        
        config = Config()
        creds = config.get_aws_credentials()
        
        assert creds is not None
        assert creds["aws_access_key_id"] == "AKIA123"
        assert creds["aws_secret_access_key"] == "secret123"
        assert creds["aws_session_token"] == "token123"
    
    def test_aws_credentials_none_when_not_provided(self, monkeypatch):
        """Test that get_aws_credentials returns None when not configured."""
        monkeypatch.setenv("SOURCE_TYPE", "s3")
        monkeypatch.setenv("S3_BUCKET_NAME", "test-bucket")
        monkeypatch.setenv("CONSERVER_URL", "http://localhost:8080")
        
        config = Config()
        creds = config.get_aws_credentials()
        
        assert creds is None
    
    def test_s3_date_filter_slash_format(self, monkeypatch):
        """Test S3 date filter with slash format."""
        monkeypatch.setenv("SOURCE_TYPE", "s3")
        monkeypatch.setenv("S3_BUCKET_NAME", "test-bucket")
        monkeypatch.setenv("S3_DATE_FILTER", "2024/12/15")
        monkeypatch.setenv("CONSERVER_URL", "http://localhost:8080")
        
        config = Config()
        assert config.s3_date_filter == "2024/12/15"
    
    def test_s3_date_filter_dash_format(self, monkeypatch):
        """Test S3 date filter with dash format."""
        monkeypatch.setenv("SOURCE_TYPE", "s3")
        monkeypatch.setenv("S3_BUCKET_NAME", "test-bucket")
        monkeypatch.setenv("S3_DATE_FILTER", "2024-12-15")
        monkeypatch.setenv("CONSERVER_URL", "http://localhost:8080")
        
        config = Config()
        assert config.s3_date_filter == "2024-12-15"
    
    def test_s3_date_filter_compact_format(self, monkeypatch):
        """Test S3 date filter with compact format."""
        monkeypatch.setenv("SOURCE_TYPE", "s3")
        monkeypatch.setenv("S3_BUCKET_NAME", "test-bucket")
        monkeypatch.setenv("S3_DATE_FILTER", "20241215")
        monkeypatch.setenv("CONSERVER_URL", "http://localhost:8080")
        
        config = Config()
        assert config.s3_date_filter == "20241215"
    
    def test_s3_date_filter_invalid_format(self, monkeypatch):
        """Test that invalid date filter format raises error."""
        monkeypatch.setenv("SOURCE_TYPE", "s3")
        monkeypatch.setenv("S3_BUCKET_NAME", "test-bucket")
        monkeypatch.setenv("S3_DATE_FILTER", "invalid-date")
        monkeypatch.setenv("CONSERVER_URL", "http://localhost:8080")
        
        with pytest.raises(ValueError, match="S3_DATE_FILTER must be in format"):
            Config()
    
    def test_s3_date_range(self, monkeypatch):
        """Test S3 date range configuration."""
        monkeypatch.setenv("SOURCE_TYPE", "s3")
        monkeypatch.setenv("S3_BUCKET_NAME", "test-bucket")
        monkeypatch.setenv("S3_DATE_RANGE_START", "2024/12/01")
        monkeypatch.setenv("S3_DATE_RANGE_END", "2024/12/31")
        monkeypatch.setenv("CONSERVER_URL", "http://localhost:8080")
        
        config = Config()
        assert config.s3_date_range_start == "2024/12/01"
        assert config.s3_date_range_end == "2024/12/31"
    
    def test_s3_date_range_start_after_end(self, monkeypatch):
        """Test that start date after end date raises error."""
        monkeypatch.setenv("SOURCE_TYPE", "s3")
        monkeypatch.setenv("S3_BUCKET_NAME", "test-bucket")
        monkeypatch.setenv("S3_DATE_RANGE_START", "2024/12/31")
        monkeypatch.setenv("S3_DATE_RANGE_END", "2024/12/01")
        monkeypatch.setenv("CONSERVER_URL", "http://localhost:8080")
        
        with pytest.raises(ValueError, match="S3_DATE_RANGE_START must be before"):
            Config()
    
    def test_s3_date_range_same_day_allowed(self, monkeypatch):
        """Test that same start and end date is allowed."""
        monkeypatch.setenv("SOURCE_TYPE", "s3")
        monkeypatch.setenv("S3_BUCKET_NAME", "test-bucket")
        monkeypatch.setenv("S3_DATE_RANGE_START", "2024/12/15")
        monkeypatch.setenv("S3_DATE_RANGE_END", "2024/12/15")
        monkeypatch.setenv("CONSERVER_URL", "http://localhost:8080")
        
        config = Config()
        assert config.s3_date_range_start == "2024/12/15"
        assert config.s3_date_range_end == "2024/12/15"
    
    def test_s3_poll_interval_default(self, monkeypatch):
        """Test default S3 poll interval."""
        monkeypatch.setenv("SOURCE_TYPE", "s3")
        monkeypatch.setenv("S3_BUCKET_NAME", "test-bucket")
        monkeypatch.setenv("CONSERVER_URL", "http://localhost:8080")
        
        config = Config()
        assert config.s3_poll_interval == 30.0
    
    def test_s3_delete_after_send_default_false(self, monkeypatch):
        """Test that S3 delete after send defaults to false."""
        monkeypatch.setenv("SOURCE_TYPE", "s3")
        monkeypatch.setenv("S3_BUCKET_NAME", "test-bucket")
        monkeypatch.setenv("CONSERVER_URL", "http://localhost:8080")
        
        config = Config()
        assert config.s3_delete_after_send is False

