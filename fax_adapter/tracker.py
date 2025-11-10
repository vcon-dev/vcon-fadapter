"""State tracker to prevent reprocessing of files."""

import json
import logging
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime


logger = logging.getLogger(__name__)


class StateTracker:
    """Tracks processed files to avoid duplicates."""
    
    def __init__(self, state_file: str):
        """Initialize state tracker.
        
        Args:
            state_file: Path to JSON file storing state
        """
        self.state_file = Path(state_file)
        self.state: Dict[str, Dict] = {}
        self._load()
    
    def _load(self):
        """Load state from file."""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    self.state = json.load(f)
                logger.info(f"Loaded state for {len(self.state)} processed files")
            except Exception as e:
                logger.error(f"Error loading state file: {e}")
                self.state = {}
        else:
            self.state = {}
    
    def _save(self):
        """Save state to file."""
        try:
            with open(self.state_file, 'w') as f:
                json.dump(self.state, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving state file: {e}")
    
    def is_processed(self, filepath: str) -> bool:
        """Check if file has been processed.
        
        Args:
            filepath: Path to the file
            
        Returns:
            True if file has been processed
        """
        return filepath in self.state
    
    def mark_processed(
        self, 
        filepath: str, 
        vcon_uuid: str, 
        status: str = "success"
    ):
        """Mark file as processed.
        
        Args:
            filepath: Path to the file
            vcon_uuid: UUID of the created vCon
            status: Processing status (success, failed, etc.)
        """
        self.state[filepath] = {
            "vcon_uuid": vcon_uuid,
            "timestamp": datetime.utcnow().isoformat(),
            "status": status
        }
        self._save()
        logger.debug(f"Marked {filepath} as processed (status: {status})")
    
    def get_vcon_uuid(self, filepath: str) -> Optional[str]:
        """Get vCon UUID for a processed file.
        
        Args:
            filepath: Path to the file
            
        Returns:
            vCon UUID or None if not processed
        """
        entry = self.state.get(filepath)
        return entry.get("vcon_uuid") if entry else None

