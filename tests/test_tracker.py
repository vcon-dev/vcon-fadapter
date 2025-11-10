"""Tests for tracker.py module."""

import os
import json
import pytest
from fax_adapter.tracker import StateTracker


class TestStateTracker:
    """Test cases for StateTracker class."""
    
    def test_init_new_state_file(self, state_file_path):
        """Test initializing with new state file."""
        tracker = StateTracker(state_file_path)
        assert tracker.state == {}
        assert not os.path.exists(state_file_path)
    
    def test_init_existing_state_file(self, state_file_path, sample_state_data):
        """Test initializing with existing state file."""
        with open(state_file_path, "w") as f:
            json.dump(sample_state_data, f)
        
        tracker = StateTracker(state_file_path)
        assert len(tracker.state) == 2
        assert "/path/to/file1.jpg" in tracker.state
    
    def test_init_corrupted_state_file(self, state_file_path):
        """Test initializing with corrupted state file."""
        with open(state_file_path, "w") as f:
            f.write("invalid json content")
        
        tracker = StateTracker(state_file_path)
        # Should handle error gracefully and use empty state
        assert tracker.state == {}
    
    def test_is_processed_false(self, state_file_path):
        """Test is_processed returns False for unprocessed file."""
        tracker = StateTracker(state_file_path)
        assert tracker.is_processed("/path/to/new_file.jpg") is False
    
    def test_is_processed_true(self, state_file_path, sample_state_data):
        """Test is_processed returns True for processed file."""
        with open(state_file_path, "w") as f:
            json.dump(sample_state_data, f)
        
        tracker = StateTracker(state_file_path)
        assert tracker.is_processed("/path/to/file1.jpg") is True
    
    def test_mark_processed(self, state_file_path):
        """Test marking a file as processed."""
        tracker = StateTracker(state_file_path)
        tracker.mark_processed("/path/to/file.jpg", "uuid-123", "success")
        
        assert tracker.is_processed("/path/to/file.jpg") is True
        assert tracker.state["/path/to/file.jpg"]["vcon_uuid"] == "uuid-123"
        assert tracker.state["/path/to/file.jpg"]["status"] == "success"
        assert "timestamp" in tracker.state["/path/to/file.jpg"]
    
    def test_mark_processed_saves_to_file(self, state_file_path):
        """Test that marking processed saves to file."""
        tracker = StateTracker(state_file_path)
        tracker.mark_processed("/path/to/file.jpg", "uuid-123", "success")
        
        assert os.path.exists(state_file_path)
        with open(state_file_path, "r") as f:
            saved_state = json.load(f)
        assert "/path/to/file.jpg" in saved_state
    
    def test_mark_processed_multiple_files(self, state_file_path):
        """Test marking multiple files as processed."""
        tracker = StateTracker(state_file_path)
        tracker.mark_processed("/path/to/file1.jpg", "uuid-1", "success")
        tracker.mark_processed("/path/to/file2.jpg", "uuid-2", "success")
        tracker.mark_processed("/path/to/file3.jpg", "uuid-3", "failed")
        
        assert len(tracker.state) == 3
        assert tracker.is_processed("/path/to/file1.jpg")
        assert tracker.is_processed("/path/to/file2.jpg")
        assert tracker.is_processed("/path/to/file3.jpg")
    
    def test_mark_processed_different_statuses(self, state_file_path):
        """Test marking files with different statuses."""
        tracker = StateTracker(state_file_path)
        tracker.mark_processed("/path/to/file1.jpg", "uuid-1", "success")
        tracker.mark_processed("/path/to/file2.jpg", "uuid-2", "failed")
        tracker.mark_processed("/path/to/file3.jpg", "uuid-3", "pending")
        
        assert tracker.state["/path/to/file1.jpg"]["status"] == "success"
        assert tracker.state["/path/to/file2.jpg"]["status"] == "failed"
        assert tracker.state["/path/to/file3.jpg"]["status"] == "pending"
    
    def test_get_vcon_uuid_exists(self, state_file_path, sample_state_data):
        """Test getting vCon UUID for processed file."""
        with open(state_file_path, "w") as f:
            json.dump(sample_state_data, f)
        
        tracker = StateTracker(state_file_path)
        uuid = tracker.get_vcon_uuid("/path/to/file1.jpg")
        assert uuid == "uuid-1"
    
    def test_get_vcon_uuid_not_exists(self, state_file_path):
        """Test getting vCon UUID for unprocessed file."""
        tracker = StateTracker(state_file_path)
        uuid = tracker.get_vcon_uuid("/path/to/nonexistent.jpg")
        assert uuid is None
    
    def test_state_persistence(self, state_file_path):
        """Test that state persists across instances."""
        tracker1 = StateTracker(state_file_path)
        tracker1.mark_processed("/path/to/file.jpg", "uuid-123", "success")
        
        tracker2 = StateTracker(state_file_path)
        assert tracker2.is_processed("/path/to/file.jpg")
        assert tracker2.get_vcon_uuid("/path/to/file.jpg") == "uuid-123"
    
    def test_mark_processed_overwrites_existing(self, state_file_path):
        """Test that marking processed again overwrites existing entry."""
        tracker = StateTracker(state_file_path)
        tracker.mark_processed("/path/to/file.jpg", "uuid-1", "success")
        tracker.mark_processed("/path/to/file.jpg", "uuid-2", "failed")
        
        assert len(tracker.state) == 1
        assert tracker.get_vcon_uuid("/path/to/file.jpg") == "uuid-2"
        assert tracker.state["/path/to/file.jpg"]["status"] == "failed"
    
    def test_save_error_handling(self, state_file_path):
        """Test error handling when save fails."""
        tracker = StateTracker(state_file_path)
        # Create a directory with the same name to cause write error
        os.makedirs(state_file_path, exist_ok=True)
        
        # Should not raise exception
        tracker.mark_processed("/path/to/file.jpg", "uuid-123", "success")
        # State should still be updated in memory
        assert tracker.is_processed("/path/to/file.jpg")
        
        # Cleanup
        os.rmdir(state_file_path)

