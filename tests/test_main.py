"""Tests for main.py module."""

import os
import pytest
from unittest.mock import Mock, MagicMock, patch, call
from fax_adapter.config import Config
from main import FaxAdapter


class TestFaxAdapter:
    """Test cases for FaxAdapter class."""
    
    @pytest.fixture
    def mock_config(self, temp_dir, env_vars):
        """Create a mock config."""
        with patch.dict(os.environ, env_vars, clear=True):
            env_vars["WATCH_DIRECTORY"] = temp_dir
            os.makedirs(temp_dir, exist_ok=True)
            config = Config()
            return config
    
    @pytest.fixture
    def adapter(self, mock_config):
        """Create a FaxAdapter instance."""
        with patch("main.FilenameParser"), \
             patch("main.VconBuilder"), \
             patch("main.HttpPoster"), \
             patch("main.StateTracker"), \
             patch("main.FileSystemMonitor"):
            return FaxAdapter(mock_config)
    
    def test_init(self, mock_config):
        """Test adapter initialization."""
        with patch("main.FilenameParser") as mock_parser, \
             patch("main.VconBuilder") as mock_builder, \
             patch("main.HttpPoster") as mock_poster, \
             patch("main.StateTracker") as mock_tracker, \
             patch("main.FileSystemMonitor") as mock_monitor:
            
            adapter = FaxAdapter(mock_config)
            
            assert adapter.config == mock_config
            assert adapter.running is False
            mock_parser.assert_called_once()
            mock_builder.assert_called_once()
            mock_poster.assert_called_once()
            mock_tracker.assert_called_once()
            mock_monitor.assert_called_once()
    
    def test_process_file_already_processed(self, adapter, temp_file):
        """Test processing file that's already processed."""
        filepath = temp_file()
        adapter.tracker.is_processed.return_value = True
        
        adapter._process_file(filepath)
        
        adapter.parser.parse.assert_not_called()
        adapter.builder.build.assert_not_called()
    
    def test_process_file_parse_fails(self, adapter, temp_file):
        """Test processing file when parsing fails."""
        filepath = temp_file()
        adapter.tracker.is_processed.return_value = False
        adapter.parser.parse.return_value = None
        
        adapter._process_file(filepath)
        
        adapter.builder.build.assert_not_called()
        adapter.poster.post.assert_not_called()
    
    def test_process_file_build_fails(self, adapter, temp_file):
        """Test processing file when vCon build fails."""
        filepath = temp_file()
        adapter.tracker.is_processed.return_value = False
        adapter.parser.parse.return_value = ("123", "456", "jpg")
        adapter.builder.build.return_value = None
        
        adapter._process_file(filepath)
        
        adapter.poster.post.assert_not_called()
    
    def test_process_file_success(self, adapter, temp_file, mock_vcon):
        """Test successful file processing."""
        filepath = temp_file()
        adapter.tracker.is_processed.return_value = False
        adapter.parser.parse.return_value = ("123", "456", "jpg")
        adapter.builder.build.return_value = mock_vcon
        adapter.poster.post.return_value = True
        adapter.config.delete_after_send = False
        
        adapter._process_file(filepath)
        
        adapter.builder.build.assert_called_once_with(filepath, "123", "456", "jpg")
        adapter.poster.post.assert_called_once_with(mock_vcon)
        adapter.tracker.mark_processed.assert_called_once_with(
            filepath, mock_vcon.uuid, "success"
        )
    
    def test_process_file_post_fails(self, adapter, temp_file, mock_vcon):
        """Test processing file when HTTP post fails."""
        filepath = temp_file()
        adapter.tracker.is_processed.return_value = False
        adapter.parser.parse.return_value = ("123", "456", "jpg")
        adapter.builder.build.return_value = mock_vcon
        adapter.poster.post.return_value = False
        
        adapter._process_file(filepath)
        
        adapter.tracker.mark_processed.assert_called_once_with(
            filepath, mock_vcon.uuid, "failed"
        )
    
    def test_process_file_delete_after_send(self, adapter, temp_file, mock_vcon):
        """Test deleting file after successful send."""
        filepath = temp_file()
        adapter.tracker.is_processed.return_value = False
        adapter.parser.parse.return_value = ("123", "456", "jpg")
        adapter.builder.build.return_value = mock_vcon
        adapter.poster.post.return_value = True
        adapter.config.delete_after_send = True
        
        adapter._process_file(filepath)
        
        # File should be deleted
        assert not os.path.exists(filepath)
    
    def test_process_file_delete_error(self, adapter, temp_file, mock_vcon):
        """Test handling delete error."""
        filepath = temp_file()
        adapter.tracker.is_processed.return_value = False
        adapter.parser.parse.return_value = ("123", "456", "jpg")
        adapter.builder.build.return_value = mock_vcon
        adapter.poster.post.return_value = True
        adapter.config.delete_after_send = True
        
        # Make file unreadable to cause delete error
        os.chmod(filepath, 0o000)
        try:
            adapter._process_file(filepath)
            # Should not raise exception
        finally:
            if os.path.exists(filepath):
                os.chmod(filepath, 0o644)
                os.remove(filepath)
    
    def test_process_existing_files_disabled(self, adapter):
        """Test processing existing files when disabled."""
        adapter.config.process_existing = False
        adapter.process_existing_files()
        
        adapter.monitor.get_existing_files.assert_not_called()
    
    def test_process_existing_files_enabled(self, adapter):
        """Test processing existing files when enabled."""
        adapter.config.process_existing = True
        adapter.monitor.get_existing_files.return_value = [
            "/path/to/file1.jpg",
            "/path/to/file2.jpg"
        ]
        
        # Mock _process_file to track calls
        with patch.object(adapter, '_process_file') as mock_process:
            adapter.process_existing_files()
            
            assert mock_process.call_count == 2
            mock_process.assert_any_call("/path/to/file1.jpg")
            mock_process.assert_any_call("/path/to/file2.jpg")
    
    def test_start(self, adapter):
        """Test starting the adapter."""
        adapter.config.process_existing = True
        adapter.monitor.get_existing_files.return_value = []
        
        # Use a thread to stop the adapter after a short delay
        import threading
        def stop_adapter():
            import time
            time.sleep(0.1)
            adapter.running = False
        
        stop_thread = threading.Thread(target=stop_adapter, daemon=True)
        stop_thread.start()
        
        adapter.start()
        
        adapter.monitor.start.assert_called_once()
        assert adapter.running is False
    
    def test_stop(self, adapter):
        """Test stopping the adapter."""
        adapter.running = True
        adapter.stop()
        
        assert adapter.running is False
        adapter.monitor.stop.assert_called_once()
    
    def test_stop_not_running(self, adapter):
        """Test stopping when not running."""
        adapter.running = False
        adapter.stop()
        
        # Should not raise exception
        assert adapter.running is False


class TestMainFunction:
    """Test cases for main() function."""
    
    def test_main_success(self, temp_dir, env_vars):
        """Test successful main execution."""
        env_vars["WATCH_DIRECTORY"] = temp_dir
        os.makedirs(temp_dir, exist_ok=True)
        
        with patch.dict(os.environ, env_vars, clear=True), \
             patch("fax_adapter.config.load_dotenv", MagicMock()), \
             patch("main.FaxAdapter") as mock_adapter_class, \
             patch("main.signal.signal"):
            mock_adapter = Mock()
            # Ensure start() is a no-op Mock that returns immediately
            mock_adapter.start = Mock()
            mock_adapter_class.return_value = mock_adapter
            
            from main import main
            
            # main() should complete immediately since start() is a Mock
            main()
            
            mock_adapter.start.assert_called_once()
    
    def test_main_config_error(self, env_vars):
        """Test main with configuration error."""
        env_vars.pop("WATCH_DIRECTORY", None)
        
        with patch.dict(os.environ, env_vars, clear=True), \
             patch("fax_adapter.config.load_dotenv", MagicMock()):
            from main import main
            
            with pytest.raises(SystemExit):
                main()
    
    def test_main_fatal_error(self, temp_dir, env_vars):
        """Test main with fatal error."""
        env_vars["WATCH_DIRECTORY"] = temp_dir
        os.makedirs(temp_dir, exist_ok=True)
        
        with patch.dict(os.environ, env_vars, clear=True), \
             patch("fax_adapter.config.load_dotenv", MagicMock()), \
             patch("main.FaxAdapter", side_effect=Exception("Fatal error")):
            from main import main
            
            with pytest.raises(SystemExit):
                main()
    
    def test_main_signal_handlers(self, temp_dir, env_vars):
        """Test signal handlers are set up."""
        env_vars["WATCH_DIRECTORY"] = temp_dir
        os.makedirs(temp_dir, exist_ok=True)
        
        with patch.dict(os.environ, env_vars, clear=True), \
             patch("fax_adapter.config.load_dotenv", MagicMock()), \
             patch("main.FaxAdapter") as mock_adapter_class, \
             patch("main.signal.signal") as mock_signal:
            mock_adapter = Mock()
            # Ensure start() is a no-op Mock that returns immediately
            mock_adapter.start = Mock()
            mock_adapter_class.return_value = mock_adapter
            
            from main import main
            
            # main() should complete immediately since start() is a Mock
            main()
            
            # Should set up signal handlers
            assert mock_signal.call_count == 2

