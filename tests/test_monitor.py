"""Tests for monitor.py module."""

import os
import time
import pytest
from unittest.mock import Mock, MagicMock, patch
from fax_adapter.monitor import FileSystemMonitor, FaxImageHandler


class TestFaxImageHandler:
    """Test cases for FaxImageHandler class."""
    
    def test_init(self):
        """Test handler initialization."""
        callback = Mock()
        handler = FaxImageHandler(["jpg", "png"], callback)
        
        assert "jpg" in handler.supported_formats
        assert "png" in handler.supported_formats
        assert handler.callback == callback
    
    def test_on_created_image_file(self):
        """Test handling created image file."""
        callback = Mock()
        handler = FaxImageHandler(["jpg", "png"], callback)
        
        event = Mock()
        event.is_directory = False
        event.src_path = "/path/to/test.jpg"
        
        with patch("fax_adapter.monitor.Path") as mock_path:
            mock_path.return_value.suffix = ".jpg"
            with patch("fax_adapter.monitor.time.sleep"):
                handler.on_created(event)
                callback.assert_called_once_with("/path/to/test.jpg")
    
    def test_on_created_directory(self):
        """Test ignoring directory creation."""
        callback = Mock()
        handler = FaxImageHandler(["jpg"], callback)
        
        event = Mock()
        event.is_directory = True
        
        handler.on_created(event)
        callback.assert_not_called()
    
    def test_on_created_unsupported_format(self):
        """Test ignoring unsupported file format."""
        callback = Mock()
        handler = FaxImageHandler(["jpg", "png"], callback)
        
        event = Mock()
        event.is_directory = False
        event.src_path = "/path/to/test.txt"
        
        with patch("fax_adapter.monitor.Path") as mock_path:
            mock_path.return_value.suffix = ".txt"
            handler.on_created(event)
            callback.assert_not_called()
    
    def test_on_created_case_insensitive(self):
        """Test case insensitive format matching."""
        callback = Mock()
        handler = FaxImageHandler(["jpg"], callback)
        
        event = Mock()
        event.is_directory = False
        event.src_path = "/path/to/test.JPG"
        
        with patch("fax_adapter.monitor.Path") as mock_path:
            mock_path.return_value.suffix = ".JPG"
            with patch("fax_adapter.monitor.time.sleep"):
                handler.on_created(event)
                callback.assert_called_once()


class TestFileSystemMonitor:
    """Test cases for FileSystemMonitor class."""
    
    def test_init_directory_not_exists(self, temp_dir):
        """Test initialization with non-existent directory."""
        nonexistent_dir = os.path.join(temp_dir, "nonexistent")
        callback = Mock()
        
        with pytest.raises(ValueError, match="does not exist"):
            FileSystemMonitor(nonexistent_dir, ["jpg"], callback)
    
    def test_init_directory_exists(self, temp_dir):
        """Test initialization with existing directory."""
        callback = Mock()
        monitor = FileSystemMonitor(temp_dir, ["jpg", "png"], callback)
        
        assert str(monitor.watch_directory) == temp_dir
        assert monitor.supported_formats == ["jpg", "png"]
        assert monitor.callback == callback
        assert monitor.observer is None
    
    def test_start(self, temp_dir):
        """Test starting the monitor."""
        callback = Mock()
        monitor = FileSystemMonitor(temp_dir, ["jpg"], callback)
        
        with patch("fax_adapter.monitor.Observer") as mock_observer_class:
            mock_observer = Mock()
            mock_observer_class.return_value = mock_observer
            
            monitor.start()
            
            assert monitor.observer is not None
            mock_observer.schedule.assert_called_once()
            mock_observer.start.assert_called_once()
    
    def test_stop(self, temp_dir):
        """Test stopping the monitor."""
        callback = Mock()
        monitor = FileSystemMonitor(temp_dir, ["jpg"], callback)
        
        mock_observer = Mock()
        monitor.observer = mock_observer
        
        monitor.stop()
        
        mock_observer.stop.assert_called_once()
        mock_observer.join.assert_called_once()
    
    def test_stop_no_observer(self, temp_dir):
        """Test stopping when observer is None."""
        callback = Mock()
        monitor = FileSystemMonitor(temp_dir, ["jpg"], callback)
        monitor.observer = None
        
        # Should not raise exception
        monitor.stop()
    
    def test_get_existing_files(self, temp_dir):
        """Test getting existing files."""
        # Create some test files
        jpg_file = os.path.join(temp_dir, "test1.jpg")
        png_file = os.path.join(temp_dir, "test2.png")
        txt_file = os.path.join(temp_dir, "test3.txt")
        
        with open(jpg_file, "w") as f:
            f.write("test")
        with open(png_file, "w") as f:
            f.write("test")
        with open(txt_file, "w") as f:
            f.write("test")
        
        callback = Mock()
        monitor = FileSystemMonitor(temp_dir, ["jpg", "png"], callback)
        
        existing_files = monitor.get_existing_files()
        
        assert len(existing_files) == 2
        assert any("test1.jpg" in f for f in existing_files)
        assert any("test2.png" in f for f in existing_files)
        assert not any("test3.txt" in f for f in existing_files)
    
    def test_get_existing_files_case_insensitive(self, temp_dir):
        """Test getting existing files with case insensitive matching."""
        jpg_file = os.path.join(temp_dir, "test.JPG")
        with open(jpg_file, "w") as f:
            f.write("test")
        
        callback = Mock()
        monitor = FileSystemMonitor(temp_dir, ["jpg"], callback)
        
        existing_files = monitor.get_existing_files()
        assert len(existing_files) == 1
    
    def test_get_existing_files_empty_directory(self, temp_dir):
        """Test getting existing files from empty directory."""
        callback = Mock()
        monitor = FileSystemMonitor(temp_dir, ["jpg"], callback)
        
        existing_files = monitor.get_existing_files()
        assert existing_files == []
    
    def test_get_existing_files_error_handling(self, temp_dir):
        """Test error handling when scanning directory."""
        callback = Mock()
        monitor = FileSystemMonitor(temp_dir, ["jpg"], callback)
        
        # Make directory unreadable to cause error
        os.chmod(temp_dir, 0o000)
        try:
            existing_files = monitor.get_existing_files()
            # Should return empty list on error
            assert existing_files == []
        finally:
            os.chmod(temp_dir, 0o755)
    
    def test_get_existing_files_subdirectories_ignored(self, temp_dir):
        """Test that subdirectories are ignored."""
        subdir = os.path.join(temp_dir, "subdir")
        os.makedirs(subdir)
        file_in_subdir = os.path.join(subdir, "test.jpg")
        with open(file_in_subdir, "w") as f:
            f.write("test")
        
        callback = Mock()
        monitor = FileSystemMonitor(temp_dir, ["jpg"], callback)
        
        existing_files = monitor.get_existing_files()
        # Should not include files in subdirectories
        assert len(existing_files) == 0

