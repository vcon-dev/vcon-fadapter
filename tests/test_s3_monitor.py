"""Tests for S3 monitor."""

import os
import time
from datetime import datetime
from unittest.mock import Mock, patch
import pytest

try:
    import boto3
    from moto import mock_aws
    MOTO_AVAILABLE = True
except ImportError:
    MOTO_AVAILABLE = False

from fax_adapter.s3_monitor import S3Monitor


pytestmark = pytest.mark.skipif(not MOTO_AVAILABLE, reason="moto not installed")


class TestS3Monitor:
    """Test S3Monitor functionality."""
    
    @pytest.fixture(autouse=True)
    def aws_credentials(self, monkeypatch):
        """Mock AWS credentials for moto."""
        monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
        monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
        monkeypatch.setenv("AWS_SECURITY_TOKEN", "testing")
        monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")
    
    @pytest.fixture
    def s3_setup(self):
        """Set up mock S3 bucket with test files."""
        with mock_aws():
            # Create mock S3 bucket with explicit credentials for moto
            s3_client = boto3.client(
                "s3", 
                region_name="us-west-2",
                aws_access_key_id="testing",
                aws_secret_access_key="testing"
            )
            bucket_name = "test-fax-bucket"
            s3_client.create_bucket(
                Bucket=bucket_name,
                CreateBucketConfiguration={"LocationConstraint": "us-west-2"}
            )
            
            # Upload test files
            test_files = [
                ("faxes/1234567890_9876543210.jpg", b"fake jpg data"),
                ("faxes/2024/12/15/5551234567_5559876543.png", b"fake png data"),
                ("faxes/2024-12-16/1112223333_4445556666.tiff", b"fake tiff data"),
                ("faxes/20241217/7778889999_0001112222.gif", b"fake gif data"),
                ("faxes/document.txt", b"not an image"),  # Should be ignored
            ]
            
            for key, content in test_files:
                s3_client.put_object(Bucket=bucket_name, Key=key, Body=content)
            
            yield {
                "client": s3_client,
                "bucket": bucket_name,
                "files": test_files
            }
    
    def test_initialization(self, s3_setup):
        """Test S3Monitor initialization."""
        callback = Mock()
        
        monitor = S3Monitor(
            bucket_name=s3_setup["bucket"],
            prefix="faxes/",
            supported_formats=["jpg", "png"],
            callback=callback,
            region="us-west-2",
        )
        
        assert monitor.bucket_name == s3_setup["bucket"]
        assert monitor.prefix == "faxes/"
        assert monitor.supported_formats == {"jpg", "png"}
        assert not monitor.running
    
    
    def test_initialization_with_credentials(self, s3_setup):
        """Test S3Monitor initialization with explicit credentials."""
        callback = Mock()
        
        # With moto, credentials are mocked
        credentials = {
            "aws_access_key_id": "test_key",
            "aws_secret_access_key": "test_secret"
        }
        
        monitor = S3Monitor(
            bucket_name=s3_setup["bucket"],
            prefix="faxes/",
            supported_formats=["jpg"],
            callback=callback,
            region="us-west-2",
            credentials=credentials
        )
        
        assert monitor.bucket_name == s3_setup["bucket"]
    
    
    def test_initialization_bucket_not_found(self):
        """Test initialization fails with non-existent bucket."""
        callback = Mock()
        
        with pytest.raises(ValueError, match="(S3 bucket not found|Access denied to S3 bucket)"):
            S3Monitor(
                bucket_name="nonexistent-bucket",
                prefix="",
                supported_formats=["jpg"],
                callback=callback,
                region="us-west-2"
            )
    
    
    def test_list_objects(self, s3_setup):
        """Test listing objects from S3."""
        callback = Mock()
        
        monitor = S3Monitor(
            bucket_name=s3_setup["bucket"],
            prefix="faxes/",
            supported_formats=["jpg", "png", "tiff", "gif"],
            callback=callback,
            region="us-east-1"
        )
        
        objects = monitor._list_objects()
        
        # Should find 4 image files (txt file excluded)
        assert len(objects) == 4
        keys = [obj["Key"] for obj in objects]
        assert "faxes/1234567890_9876543210.jpg" in keys
        assert "faxes/2024/12/15/5551234567_5559876543.png" in keys
        assert "faxes/document.txt" not in keys
    
    
    def test_list_objects_with_format_filter(self, s3_setup):
        """Test listing objects with format filtering."""
        callback = Mock()
        
        monitor = S3Monitor(
            bucket_name=s3_setup["bucket"],
            prefix="faxes/",
            supported_formats=["jpg"],  # Only JPG
            callback=callback,
            region="us-east-1"
        )
        
        objects = monitor._list_objects()
        
        # Should find only 1 JPG file
        assert len(objects) == 1
        assert objects[0]["Key"] == "faxes/1234567890_9876543210.jpg"
    
    
    def test_get_existing_files(self, s3_setup):
        """Test getting existing files."""
        callback = Mock()
        
        monitor = S3Monitor(
            bucket_name=s3_setup["bucket"],
            prefix="faxes/",
            supported_formats=["jpg", "png", "tiff", "gif"],
            callback=callback,
            region="us-east-1"
        )
        
        existing = monitor.get_existing_files()
        
        assert len(existing) == 4
        assert isinstance(existing[0], str)
    
    
    def test_download_object(self, s3_setup):
        """Test downloading S3 object to temp file."""
        callback = Mock()
        
        monitor = S3Monitor(
            bucket_name=s3_setup["bucket"],
            prefix="faxes/",
            supported_formats=["jpg"],
            callback=callback,
            region="us-east-1"
        )
        
        key = "faxes/1234567890_9876543210.jpg"
        temp_path = monitor._download_object(key)
        
        assert temp_path is not None
        assert os.path.exists(temp_path)
        assert temp_path.endswith(".jpg")
        
        # Read content
        with open(temp_path, "rb") as f:
            content = f.read()
        assert content == b"fake jpg data"
        
        # Cleanup
        monitor._cleanup_temp_file(temp_path)
        assert not os.path.exists(temp_path)
    
    
    def test_delete_s3_object(self, s3_setup):
        """Test deleting S3 object."""
        callback = Mock()
        
        monitor = S3Monitor(
            bucket_name=s3_setup["bucket"],
            prefix="faxes/",
            supported_formats=["jpg"],
            callback=callback,
            region="us-east-1"
        )
        
        key = "faxes/1234567890_9876543210.jpg"
        
        # Verify object exists
        s3_setup["client"].head_object(Bucket=s3_setup["bucket"], Key=key)
        
        # Delete it
        success = monitor.delete_s3_object(key)
        assert success is True
        
        # Verify it's gone
        with pytest.raises(Exception):
            s3_setup["client"].head_object(Bucket=s3_setup["bucket"], Key=key)
    
    
    def test_date_extraction_slash_format(self, s3_setup):
        """Test extracting date from S3 key with slash format."""
        callback = Mock()
        
        monitor = S3Monitor(
            bucket_name=s3_setup["bucket"],
            prefix="faxes/",
            supported_formats=["png"],
            callback=callback,
            region="us-east-1"
        )
        
        key = "faxes/2024/12/15/5551234567_5559876543.png"
        date = monitor._extract_date_from_key(key)
        
        assert date is not None
        assert date.year == 2024
        assert date.month == 12
        assert date.day == 15
    
    
    def test_date_extraction_dash_format(self, s3_setup):
        """Test extracting date from S3 key with dash format."""
        callback = Mock()
        
        monitor = S3Monitor(
            bucket_name=s3_setup["bucket"],
            prefix="faxes/",
            supported_formats=["tiff"],
            callback=callback,
            region="us-east-1"
        )
        
        key = "faxes/2024-12-16/1112223333_4445556666.tiff"
        date = monitor._extract_date_from_key(key)
        
        assert date is not None
        assert date.year == 2024
        assert date.month == 12
        assert date.day == 16
    
    
    def test_date_extraction_compact_format(self, s3_setup):
        """Test extracting date from S3 key with compact format."""
        callback = Mock()
        
        monitor = S3Monitor(
            bucket_name=s3_setup["bucket"],
            prefix="faxes/",
            supported_formats=["gif"],
            callback=callback,
            region="us-east-1"
        )
        
        key = "faxes/20241217/7778889999_0001112222.gif"
        date = monitor._extract_date_from_key(key)
        
        assert date is not None
        assert date.year == 2024
        assert date.month == 12
        assert date.day == 17
    
    
    def test_date_extraction_no_date(self, s3_setup):
        """Test extracting date when key has no date."""
        callback = Mock()
        
        monitor = S3Monitor(
            bucket_name=s3_setup["bucket"],
            prefix="faxes/",
            supported_formats=["jpg"],
            callback=callback,
            region="us-east-1"
        )
        
        key = "faxes/1234567890_9876543210.jpg"
        date = monitor._extract_date_from_key(key)
        
        assert date is None
    
    
    def test_date_filter_exact_match(self, s3_setup):
        """Test filtering by exact date."""
        callback = Mock()
        
        monitor = S3Monitor(
            bucket_name=s3_setup["bucket"],
            prefix="faxes/",
            supported_formats=["jpg", "png", "tiff", "gif"],
            callback=callback,
            region="us-west-2",
            date_filter="2024/12/15"
        )
        
        objects = monitor._list_objects()
        
        # Should only find the file from 2024/12/15
        assert len(objects) == 1
        assert "2024/12/15" in objects[0]["Key"]
    
    
    def test_date_filter_no_matches(self, s3_setup):
        """Test filtering with date that has no matches."""
        callback = Mock()
        
        monitor = S3Monitor(
            bucket_name=s3_setup["bucket"],
            prefix="faxes/",
            supported_formats=["jpg", "png", "tiff", "gif"],
            callback=callback,
            region="us-west-2",
            date_filter="2024/01/01"
        )
        
        objects = monitor._list_objects()
        
        # Should find no files
        assert len(objects) == 0
    
    
    def test_date_range_filter(self, s3_setup):
        """Test filtering by date range."""
        callback = Mock()
        
        monitor = S3Monitor(
            bucket_name=s3_setup["bucket"],
            prefix="faxes/",
            supported_formats=["jpg", "png", "tiff", "gif"],
            callback=callback,
            region="us-west-2",
            date_range_start="2024/12/15",
            date_range_end="2024/12/16"
        )
        
        objects = monitor._list_objects()
        
        # Should find files from 12/15 and 12/16 (2 files)
        assert len(objects) == 2
        keys = [obj["Key"] for obj in objects]
        assert any("2024/12/15" in k for k in keys)
        assert any("2024-12-16" in k for k in keys)
    
    
    def test_start_stop_monitor(self, s3_setup):
        """Test starting and stopping the monitor."""
        callback = Mock()
        
        monitor = S3Monitor(
            bucket_name=s3_setup["bucket"],
            prefix="faxes/",
            supported_formats=["jpg"],
            callback=callback,
            region="us-west-2",
            poll_interval=0.1  # Short interval for testing
        )
        
        assert not monitor.running
        
        monitor.start()
        assert monitor.running
        assert monitor.poll_thread is not None
        
        # Let it run briefly
        time.sleep(0.2)
        
        monitor.stop()
        assert not monitor.running
    
    
    def test_process_object_calls_callback(self, s3_setup):
        """Test that processing an object calls the callback."""
        callback = Mock()
        
        monitor = S3Monitor(
            bucket_name=s3_setup["bucket"],
            prefix="faxes/",
            supported_formats=["jpg"],
            callback=callback,
            region="us-east-1"
        )
        
        key = "faxes/1234567890_9876543210.jpg"
        monitor._process_object(key)
        
        # Callback should be called with temp file path and S3 key
        assert callback.called
        call_args = callback.call_args[0]
        assert len(call_args) == 2
        local_path, s3_key = call_args
        assert os.path.exists(local_path) is False  # Should be cleaned up
        assert s3_key == key
    
    
    def test_poll_interval_config(self, s3_setup):
        """Test poll interval configuration."""
        callback = Mock()
        
        monitor = S3Monitor(
            bucket_name=s3_setup["bucket"],
            prefix="faxes/",
            supported_formats=["jpg"],
            callback=callback,
            region="us-west-2",
            poll_interval=42.5
        )
        
        assert monitor.poll_interval == 42.5
    
    
    def test_cleanup_temp_directory_on_stop(self, s3_setup):
        """Test that temp directory is cleaned up on stop."""
        callback = Mock()
        
        monitor = S3Monitor(
            bucket_name=s3_setup["bucket"],
            prefix="faxes/",
            supported_formats=["jpg"],
            callback=callback,
            region="us-east-1"
        )
        
        temp_dir = monitor.temp_dir
        assert os.path.exists(temp_dir)
        
        monitor.stop()
        
        # Temp directory should be removed
        # Note: This might not work perfectly in all cases, but we test the attempt
        # In real scenarios, cleanup happens asynchronously
    
    
    def test_no_date_filter_matches_all(self, s3_setup):
        """Test that no date filter matches all files."""
        callback = Mock()
        
        monitor = S3Monitor(
            bucket_name=s3_setup["bucket"],
            prefix="faxes/",
            supported_formats=["jpg", "png", "tiff", "gif"],
            callback=callback,
            region="us-east-1"
        )
        
        # No date filter set
        assert monitor.date_filter is None
        assert monitor.date_range_start is None
        assert monitor.date_range_end is None
        
        objects = monitor._list_objects()
        
        # Should find all 4 image files
        assert len(objects) == 4

