"""Tests for parser.py module."""

import re
import pytest
from fax_adapter.parser import FilenameParser


class TestFilenameParser:
    """Test cases for FilenameParser class."""
    
    @pytest.fixture
    def default_pattern(self):
        """Default filename pattern."""
        return re.compile(
            r"(\d+)_(\d+)\.(jpg|jpeg|png|gif|tiff|tif|bmp|webp)",
            re.IGNORECASE
        )
    
    @pytest.fixture
    def parser(self, default_pattern):
        """Create a parser with default pattern."""
        return FilenameParser(default_pattern)
    
    def test_parse_valid_filename(self, parser):
        """Test parsing a valid filename."""
        result = parser.parse("/path/to/15085551212_15085551313.jpg")
        assert result is not None
        sender, receiver, extension = result
        assert sender == "15085551212"
        assert receiver == "15085551313"
        assert extension == "jpg"
    
    def test_parse_valid_filename_png(self, parser):
        """Test parsing a PNG filename."""
        result = parser.parse("/path/to/1234567890_0987654321.png")
        assert result is not None
        sender, receiver, extension = result
        assert sender == "1234567890"
        assert receiver == "0987654321"
        assert extension == "png"
    
    def test_parse_case_insensitive(self, parser):
        """Test parsing is case insensitive."""
        result = parser.parse("/path/to/123_456.JPG")
        assert result is not None
        sender, receiver, extension = result
        assert extension.lower() == "jpg"
    
    def test_parse_invalid_filename(self, parser):
        """Test parsing an invalid filename."""
        result = parser.parse("/path/to/invalid_filename.txt")
        assert result is None
    
    def test_parse_missing_extension(self, parser):
        """Test parsing filename without extension."""
        result = parser.parse("/path/to/123_456")
        assert result is None
    
    def test_parse_wrong_format(self, parser):
        """Test parsing filename with wrong format."""
        result = parser.parse("/path/to/123-456.jpg")
        assert result is None
    
    def test_parse_custom_pattern(self):
        """Test parsing with custom pattern."""
        custom_pattern = re.compile(r"fax_(\d+)_(\d+)\.(\w+)")
        parser = FilenameParser(custom_pattern)
        result = parser.parse("/path/to/fax_123_456.jpg")
        assert result is not None
        sender, receiver, extension = result
        assert sender == "123"
        assert receiver == "456"
        assert extension == "jpg"
    
    def test_parse_pattern_without_extension_group(self):
        """Test parsing with pattern that doesn't capture extension."""
        pattern = re.compile(r"(\d+)_(\d+)")
        parser = FilenameParser(pattern)
        result = parser.parse("/path/to/123_456.jpg")
        # Should still work but extension will be empty
        assert result is not None
        sender, receiver, extension = result
        assert sender == "123"
        assert receiver == "456"
        assert extension == ""
    
    def test_parse_pattern_insufficient_groups(self):
        """Test parsing with pattern that has insufficient groups."""
        pattern = re.compile(r"(\d+)")
        parser = FilenameParser(pattern)
        result = parser.parse("/path/to/123.jpg")
        assert result is None
    
    def test_parse_full_path(self, parser):
        """Test parsing with full file path."""
        result = parser.parse("/var/fax/incoming/15085551212_15085551313.jpg")
        assert result is not None
        sender, receiver, extension = result
        assert sender == "15085551212"
        assert receiver == "15085551313"
    
    def test_parse_relative_path(self, parser):
        """Test parsing with relative path."""
        result = parser.parse("./fax/123_456.png")
        assert result is not None
        sender, receiver, extension = result
        assert sender == "123"
        assert receiver == "456"
    
    def test_parse_different_extensions(self, parser):
        """Test parsing different image extensions."""
        extensions = ["jpg", "jpeg", "png", "gif", "tiff", "tif", "bmp", "webp"]
        for ext in extensions:
            result = parser.parse(f"/path/to/123_456.{ext}")
            assert result is not None, f"Failed to parse .{ext} extension"
            assert result[2].lower() == ext.lower()

