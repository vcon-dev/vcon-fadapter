"""Integration tests for S3 functionality."""

import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
import pytest

try:
    import boto3
    from moto import mock_aws
    from PIL import Image
    MOTO_AVAILABLE = True
except ImportError:
    MOTO_AVAILABLE = False

from fax_adapter.config import Config
from fax_adapter.s3_monitor import S3Monitor
from fax_adapter.tracker import StateTracker
from fax_adapter.parser import FilenameParser
from fax_adapter.builder import VconBuilder


pytestmark = pytest.mark.skipif(not MOTO_AVAILABLE, reason="moto not installed")


class TestS3Integration:
    """Integration tests for S3 functionality."""
    
    @pytest.fixture(autouse=True)
    def aws_credentials(self, monkeypatch):
        """Mock AWS credentials for moto."""
        monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
        monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
        monkeypatch.setenv("AWS_SECURITY_TOKEN", "testing")
        monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")
    
    @pytest.fixture
    def test_image(self, tmp_path):
        """Create a test image file."""
        img_path = tmp_path / "test_image.jpg"
        img = Image.new("RGB", (100, 100), color="red")
        img.save(img_path)
        return img_path
    
    @pytest.fixture
    def s3_integration_setup(self, test_image):
        """Set up S3 bucket with test images."""
        with mock_aws():
            # Create mock S3 bucket with explicit credentials for moto
            s3_client = boto3.client(
                "s3", 
                region_name="us-west-2",
                aws_access_key_id="testing",
                aws_secret_access_key="testing"
            )
            bucket_name = "integration-test-bucket"
            s3_client.create_bucket(
                Bucket=bucket_name,
                CreateBucketConfiguration={"LocationConstraint": "us-west-2"}
            )
            
            # Upload test images with proper filenames
            test_files = [
                "faxes/1234567890_9876543210.jpg",
                "faxes/2024/12/15/5551234567_5559876543.jpg",
                "faxes/2024/12/16/7778889999_0001112222.jpg",
            ]
            
            with open(test_image, "rb") as f:
                image_data = f.read()
            
            for key in test_files:
                s3_client.put_object(Bucket=bucket_name, Key=key, Body=image_data)
            
            yield {
                "client": s3_client,
                "bucket": bucket_name,
                "files": test_files,
                "image_data": image_data
            }
    
    
    def test_config_s3_integration(self, s3_integration_setup, monkeypatch):
        """Test S3 configuration integration."""
        monkeypatch.setenv("SOURCE_TYPE", "s3")
        monkeypatch.setenv("S3_BUCKET_NAME", s3_integration_setup["bucket"])
        monkeypatch.setenv("S3_PREFIX", "faxes/")
        monkeypatch.setenv("S3_REGION", "us-west-2")
        monkeypatch.setenv("CONSERVER_URL", "http://localhost:8080")
        
        config = Config()
        
        assert config.source_type == "s3"
        assert config.s3_bucket_name == s3_integration_setup["bucket"]
        assert config.s3_prefix == "faxes/"
        assert config.s3_region == "us-west-2"
    
    
    def test_s3_monitor_with_parser(self, s3_integration_setup):
        """Test S3Monitor integration with FilenameParser."""
        callback = Mock()
        
        monitor = S3Monitor(
            bucket_name=s3_integration_setup["bucket"],
            prefix="faxes/",
            supported_formats=["jpg"],
            callback=callback,
            region="us-west-2"
        )
        
        # Get existing files
        existing_files = monitor.get_existing_files()
        assert len(existing_files) == 3
        
        # Test parsing filenames from S3 keys
        import re
        parser = FilenameParser(re.compile(r"(\d+)_(\d+)\.(jpg|jpeg|png)", re.IGNORECASE))
        for key in existing_files:
            parsed = parser.parse(key)
            assert parsed is not None
            sender, receiver, ext = parsed
            assert sender.isdigit()
            assert receiver.isdigit()
            assert ext == "jpg"
    
    
    def test_s3_monitor_with_tracker(self, s3_integration_setup, tmp_path):
        """Test S3Monitor integration with StateTracker."""
        state_file = tmp_path / "test_state.json"
        tracker = StateTracker(str(state_file))
        
        callback = Mock()
        
        monitor = S3Monitor(
            bucket_name=s3_integration_setup["bucket"],
            prefix="faxes/",
            supported_formats=["jpg"],
            callback=callback,
            region="us-west-2"
        )
        
        # Get existing files
        existing_files = monitor.get_existing_files()
        
        # Mark first file as processed
        test_key = existing_files[0]
        tracker.mark_processed(test_key, "test-uuid", "success", s3_key=test_key)
        
        # Check if processed
        assert tracker.is_processed(test_key, s3_key=test_key)
        assert tracker.get_vcon_uuid(test_key, s3_key=test_key) == "test-uuid"
    
    
    def test_s3_download_and_build_vcon(self, s3_integration_setup):
        """Test downloading S3 object and building vCon."""
        monitor = S3Monitor(
            bucket_name=s3_integration_setup["bucket"],
            prefix="faxes/",
            supported_formats=["jpg"],
            callback=Mock(),
            region="us-west-2"
        )
        
        # Download a file
        key = "faxes/1234567890_9876543210.jpg"
        local_path = monitor._download_object(key)
        
        assert local_path is not None
        assert os.path.exists(local_path)
        
        # Build vCon from downloaded file
        builder = VconBuilder()
        vcon = builder.build(local_path, "1234567890", "9876543210", "jpg")
        
        assert vcon is not None
        assert len(vcon.parties) == 2
        assert vcon.parties[0].tel == "1234567890"
        assert vcon.parties[1].tel == "9876543210"
        
        # Cleanup
        monitor._cleanup_temp_file(local_path)
    
    
    def test_s3_date_filtering_integration(self, s3_integration_setup):
        """Test date filtering with S3Monitor."""
        callback = Mock()
        
        # Filter for specific date
        monitor = S3Monitor(
            bucket_name=s3_integration_setup["bucket"],
            prefix="faxes/",
            supported_formats=["jpg"],
            callback=callback,
            region="us-west-2",
            date_filter="2024/12/15"
        )
        
        existing_files = monitor.get_existing_files()
        
        # Should only get files from 2024/12/15
        assert len(existing_files) == 1
        assert "2024/12/15" in existing_files[0]
    
    
    def test_s3_date_range_filtering_integration(self, s3_integration_setup):
        """Test date range filtering with S3Monitor."""
        callback = Mock()
        
        # Filter for date range
        monitor = S3Monitor(
            bucket_name=s3_integration_setup["bucket"],
            prefix="faxes/",
            supported_formats=["jpg"],
            callback=callback,
            region="us-west-2",
            date_range_start="2024/12/15",
            date_range_end="2024/12/16"
        )
        
        existing_files = monitor.get_existing_files()
        
        # Should get files from both dates
        assert len(existing_files) == 2
    
    
    def test_s3_delete_after_processing(self, s3_integration_setup):
        """Test deleting S3 object after successful processing."""
        callback = Mock()
        
        monitor = S3Monitor(
            bucket_name=s3_integration_setup["bucket"],
            prefix="faxes/",
            supported_formats=["jpg"],
            callback=callback,
            region="us-west-2"
        )
        
        key = "faxes/1234567890_9876543210.jpg"
        
        # Verify object exists
        s3_integration_setup["client"].head_object(
            Bucket=s3_integration_setup["bucket"], 
            Key=key
        )
        
        # Delete it
        success = monitor.delete_s3_object(key)
        assert success is True
        
        # Verify it's deleted
        with pytest.raises(Exception):
            s3_integration_setup["client"].head_object(
                Bucket=s3_integration_setup["bucket"], 
                Key=key
            )
    
    
    def test_s3_etag_tracking(self, s3_integration_setup, tmp_path):
        """Test ETag-based tracking for S3 objects."""
        state_file = tmp_path / "test_state.json"
        tracker = StateTracker(str(state_file))
        
        key = "faxes/1234567890_9876543210.jpg"
        etag1 = "abc123"
        etag2 = "def456"
        
        # Mark as processed with ETag
        tracker.mark_processed(key, "uuid1", "success", s3_key=key, etag=etag1)
        
        # Should be processed with matching ETag
        assert tracker.is_s3_object_processed(key, etag1) is True
        
        # Should not be processed with different ETag (file was updated)
        assert tracker.is_s3_object_processed(key, etag2) is False
    
    
    def test_full_workflow_s3_to_vcon(self, s3_integration_setup, tmp_path, monkeypatch):
        """Test complete workflow from S3 to vCon creation."""
        # Set up state tracker
        state_file = tmp_path / "workflow_state.json"
        tracker = StateTracker(str(state_file))
        
        # Set up parser and builder
        import re
        parser = FilenameParser(re.compile(r"(\d+)_(\d+)\.(jpg|jpeg|png)", re.IGNORECASE))
        builder = VconBuilder()
        
        processed_files = []
        
        def process_callback(filepath, s3_key):
            """Callback that processes file through full workflow."""
            # Check if already processed
            if tracker.is_processed(filepath, s3_key=s3_key):
                return
            
            # Parse filename
            parsed = parser.parse(s3_key)
            if not parsed:
                return
            
            sender, receiver, ext = parsed
            
            # Build vCon
            vcon = builder.build(filepath, sender, receiver, ext)
            if not vcon:
                return
            
            # Mark as processed
            tracker.mark_processed(filepath, vcon.uuid, "success", s3_key=s3_key)
            processed_files.append(s3_key)
        
        # Create monitor
        monitor = S3Monitor(
            bucket_name=s3_integration_setup["bucket"],
            prefix="faxes/",
            supported_formats=["jpg"],
            callback=process_callback,
            region="us-west-2"
        )
        
        # Process existing files
        existing_files = monitor.get_existing_files()
        for key in existing_files:
            monitor._process_object(key)
        
        # Verify all files were processed
        assert len(processed_files) == 3
        
        # Verify state was saved
        for key in existing_files:
            assert tracker.is_processed(key, s3_key=key)
    
    
    def test_s3_monitor_error_handling(self, s3_integration_setup):
        """Test S3Monitor error handling."""
        
        def failing_callback(filepath, s3_key):
            """Callback that always fails."""
            raise Exception("Simulated processing error")
        
        monitor = S3Monitor(
            bucket_name=s3_integration_setup["bucket"],
            prefix="faxes/",
            supported_formats=["jpg"],
            callback=failing_callback,
            region="us-west-2"
        )
        
        key = "faxes/1234567890_9876543210.jpg"
        
        # Should handle error gracefully
        monitor._process_object(key)  # Should not raise
        
        # Object should still exist in S3 (not deleted)
        s3_integration_setup["client"].head_object(
            Bucket=s3_integration_setup["bucket"], 
            Key=key
        )
    
    
    def test_s3_prefix_filtering(self, s3_integration_setup):
        """Test that S3 prefix correctly filters objects."""
        # Create objects outside the prefix
        s3_integration_setup["client"].put_object(
            Bucket=s3_integration_setup["bucket"],
            Key="other/1234567890_9876543210.jpg",
            Body=s3_integration_setup["image_data"]
        )
        
        callback = Mock()
        
        monitor = S3Monitor(
            bucket_name=s3_integration_setup["bucket"],
            prefix="faxes/",  # Only look in faxes/
            supported_formats=["jpg"],
            callback=callback,
            region="us-west-2"
        )
        
        existing_files = monitor.get_existing_files()
        
        # Should only find files under faxes/ prefix
        assert len(existing_files) == 3
        assert all(key.startswith("faxes/") for key in existing_files)
    
    
    def test_s3_unsupported_format_ignored(self, s3_integration_setup):
        """Test that unsupported file formats are ignored."""
        # Add a file with unsupported format
        s3_integration_setup["client"].put_object(
            Bucket=s3_integration_setup["bucket"],
            Key="faxes/document.pdf",
            Body=b"fake pdf"
        )
        
        callback = Mock()
        
        monitor = S3Monitor(
            bucket_name=s3_integration_setup["bucket"],
            prefix="faxes/",
            supported_formats=["jpg"],  # Only JPG
            callback=callback,
            region="us-west-2"
        )
        
        existing_files = monitor.get_existing_files()
        
        # Should not include PDF file
        assert all(key.endswith(".jpg") for key in existing_files)
        assert not any(key.endswith(".pdf") for key in existing_files)

