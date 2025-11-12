"""Tests for builder.py module."""

import os
import sys
import base64
import pytest
from unittest.mock import Mock, MagicMock, patch, mock_open
from fax_adapter.builder import VconBuilder, MIME_TYPES


class MockPILImage:
    """Context manager to mock PIL.Image for tests."""
    
    def __init__(self, size=(100, 200), raise_exception=False):
        self.size = size
        self.raise_exception = raise_exception
        self.original_pil = None
    
    def __enter__(self):
        if self.raise_exception:
            mock_pil = MagicMock()
            mock_pil.Image.open.side_effect = Exception("Not an image")
        else:
            mock_img = MagicMock()
            mock_img.size = self.size
            mock_image_context = MagicMock()
            mock_image_context.__enter__ = MagicMock(return_value=mock_img)
            mock_image_context.__exit__ = MagicMock(return_value=None)
            
            mock_image_class = MagicMock()
            mock_image_class.open = MagicMock(return_value=mock_image_context)
            mock_pil = MagicMock()
            mock_pil.Image = mock_image_class
        
        self.original_pil = sys.modules.get('PIL')
        sys.modules['PIL'] = mock_pil
        return self
    
    def __exit__(self, *args):
        if self.original_pil:
            sys.modules['PIL'] = self.original_pil
        elif 'PIL' in sys.modules:
            del sys.modules['PIL']


class TestVconBuilder:
    """Test cases for VconBuilder class."""
    
    @pytest.fixture
    def builder(self):
        """Create a VconBuilder instance."""
        return VconBuilder()
    
    @pytest.fixture
    def sample_image_data(self):
        """Sample image data."""
        return b"fake image data"
    
    def test_build_file_not_exists(self, builder, temp_dir):
        """Test building vCon from non-existent file."""
        filepath = os.path.join(temp_dir, "nonexistent.jpg")
        result = builder.build(filepath, "123", "456", "jpg")
        assert result is None
    
    def test_build_success(self, builder, sample_image_file, mock_vcon):
        """Test successful vCon building."""
        with patch("fax_adapter.builder.Vcon") as mock_vcon_class:
            mock_vcon_class.build_new.return_value = mock_vcon
            with MockPILImage():
                result = builder.build(
                    sample_image_file,
                    "15085551212",
                    "15085551313",
                    "png"
                )
                
                assert result is not None
                assert result == mock_vcon
                mock_vcon.add_party.assert_called()
                assert mock_vcon.add_party.call_count == 2
                mock_vcon.add_attachment.assert_called_once()
                mock_vcon.add_tag.assert_called()
    
    def test_build_without_image_dimensions(self, builder, temp_file, mock_vcon):
        """Test building vCon when image dimensions can't be read."""
        filepath = temp_file(content=b"not an image", suffix=".jpg")
        
        with patch("fax_adapter.builder.Vcon") as mock_vcon_class:
            mock_vcon_class.build_new.return_value = mock_vcon
            with MockPILImage(raise_exception=True):
                result = builder.build(filepath, "123", "456", "jpg")
                
                assert result is not None
                # Should still create vCon even without dimensions
                mock_vcon.add_tag.assert_called()
    
    def test_build_file_read_error(self, builder, temp_dir):
        """Test building vCon when file can't be read."""
        filepath = os.path.join(temp_dir, "unreadable.jpg")
        # Create file but make it unreadable
        with open(filepath, "w") as f:
            f.write("test")
        os.chmod(filepath, 0o000)
        
        try:
            result = builder.build(filepath, "123", "456", "jpg")
            assert result is None
        finally:
            os.chmod(filepath, 0o644)
            os.remove(filepath)
    
    def test_build_adds_parties(self, builder, sample_image_file, mock_vcon):
        """Test that parties are added correctly."""
        with patch("fax_adapter.builder.Vcon") as mock_vcon_class:
            mock_vcon_class.build_new.return_value = mock_vcon
            with MockPILImage():
                builder.build(sample_image_file, "sender123", "receiver456", "png")
                
                # Check that add_party was called with correct arguments
                calls = mock_vcon.add_party.call_args_list
                assert len(calls) == 2
                # First call should be sender
                sender_party = calls[0][0][0]
                assert hasattr(sender_party, "tel")
                # Second call should be receiver
                receiver_party = calls[1][0][0]
                assert hasattr(receiver_party, "tel")
    
    def test_build_attachment_encoding(self, builder, sample_image_file, mock_vcon):
        """Test that attachment is base64 encoded."""
        with patch("fax_adapter.builder.Vcon") as mock_vcon_class:
            mock_vcon_class.build_new.return_value = mock_vcon
            with MockPILImage():
                builder.build(sample_image_file, "123", "456", "png")
                
                # Check attachment was added with base64 encoding
                call_args = mock_vcon.add_attachment.call_args
                assert call_args is not None
                kwargs = call_args[1]
                assert kwargs["encoding"] == "base64"
                assert kwargs["type"] == "fax_image"
                # Verify body is base64 encoded
                body = kwargs["body"]
                # Should be able to decode it
                decoded = base64.b64decode(body)
                assert isinstance(decoded, bytes)
    
    def test_build_mime_type_mapping(self, builder, temp_file, mock_vcon):
        """Test MIME type mapping for different extensions."""
        for ext, expected_mime in MIME_TYPES.items():
            filepath = temp_file(suffix=f".{ext}")
            with patch("fax_adapter.builder.Vcon") as mock_vcon_class:
                mock_vcon_class.build_new.return_value = mock_vcon
                # Ensure vcon_dict exists with attachments list
                mock_vcon.vcon_dict = {"attachments": []}
                # Make add_attachment actually append to the list
                def add_attachment_side_effect(*args, **kwargs):
                    attachment = {"type": kwargs.get("type", args[0] if args else ""),
                                 "body": kwargs.get("body", args[1] if len(args) > 1 else ""),
                                 "encoding": kwargs.get("encoding", args[2] if len(args) > 2 else "none")}
                    mock_vcon.vcon_dict["attachments"].append(attachment)
                mock_vcon.add_attachment.side_effect = add_attachment_side_effect
                with MockPILImage():
                    builder.build(filepath, "123", "456", ext)
                    
                    # Check that mimetype was added to the attachment dictionary
                    assert len(mock_vcon.vcon_dict["attachments"]) > 0
                    attachment = mock_vcon.vcon_dict["attachments"][-1]
                    assert attachment["mimetype"] == expected_mime
    
    def test_build_default_mime_type(self, builder, temp_file, mock_vcon):
        """Test default MIME type for unknown extension."""
        filepath = temp_file(suffix=".unknown")
        with patch("fax_adapter.builder.Vcon") as mock_vcon_class:
            mock_vcon_class.build_new.return_value = mock_vcon
            # Ensure vcon_dict exists with attachments list
            mock_vcon.vcon_dict = {"attachments": []}
            # Make add_attachment actually append to the list
            def add_attachment_side_effect(*args, **kwargs):
                attachment = {"type": kwargs.get("type", args[0] if args else ""),
                             "body": kwargs.get("body", args[1] if len(args) > 1 else ""),
                             "encoding": kwargs.get("encoding", args[2] if len(args) > 2 else "none")}
                mock_vcon.vcon_dict["attachments"].append(attachment)
            mock_vcon.add_attachment.side_effect = add_attachment_side_effect
            with MockPILImage():
                builder.build(filepath, "123", "456", "unknown")
                
                # Check that mimetype was added to the attachment dictionary
                assert len(mock_vcon.vcon_dict["attachments"]) > 0
                attachment = mock_vcon.vcon_dict["attachments"][-1]
                assert attachment["mimetype"] == "image/jpeg"  # Default
    
    def test_build_adds_tags(self, builder, sample_image_file, mock_vcon):
        """Test that metadata tags are added."""
        with patch("fax_adapter.builder.Vcon") as mock_vcon_class:
            mock_vcon_class.build_new.return_value = mock_vcon
            with MockPILImage():
                builder.build(sample_image_file, "sender123", "receiver456", "png")
                
                # Check that tags were added
                tag_calls = mock_vcon.add_tag.call_args_list
                tag_dict = {call[0][0]: call[0][1] for call in tag_calls}
                
                assert tag_dict["source"] == "fax_adapter"
                assert "original_filename" in tag_dict
                assert "file_size" in tag_dict
                assert tag_dict["sender"] == "sender123"
                assert tag_dict["receiver"] == "receiver456"
    
    def test_build_sets_created_at(self, builder, sample_image_file, mock_vcon):
        """Test that created_at is set from file modification time."""
        import time
        with patch("fax_adapter.builder.Vcon") as mock_vcon_class:
            mock_vcon_class.build_new.return_value = mock_vcon
            with MockPILImage():
                builder.build(sample_image_file, "123", "456", "png")
                
                # Check that created_at was set
                assert mock_vcon.created_at is not None
                # Should be an ISO format string
                assert "T" in mock_vcon.created_at or "Z" in mock_vcon.created_at
    
    def test_build_exception_handling(self, builder, temp_file, mock_vcon):
        """Test exception handling during build."""
        filepath = temp_file()
        with patch("fax_adapter.builder.Vcon") as mock_vcon_class:
            mock_vcon_class.build_new.side_effect = Exception("Build error")
            
            result = builder.build(filepath, "123", "456", "jpg")
            assert result is None

