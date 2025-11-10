"""Configuration management for fax adapter using .env file."""

import os
import re
from typing import Dict, List, Optional
from dotenv import load_dotenv


class Config:
    """Manages configuration from environment variables."""
    
    def __init__(self, env_file: Optional[str] = None):
        """Load configuration from .env file."""
        if env_file:
            load_dotenv(env_file)
        else:
            load_dotenv()
        
        # Required settings
        self.watch_directory = os.getenv("WATCH_DIRECTORY")
        if not self.watch_directory:
            raise ValueError("WATCH_DIRECTORY environment variable is required")
        
        self.conserver_url = os.getenv("CONSERVER_URL")
        if not self.conserver_url:
            raise ValueError("CONSERVER_URL environment variable is required")
        
        # Optional settings with defaults
        self.conserver_api_token = os.getenv("CONSERVER_API_TOKEN")
        self.conserver_header_name = os.getenv(
            "CONSERVER_HEADER_NAME", 
            "x-conserver-api-token"
        )
        
        # Filename pattern - configurable regex
        default_pattern = r"(\d+)_(\d+)\.(jpg|jpeg|png|gif|tiff|tif|bmp|webp)"
        self.filename_pattern = os.getenv("FILENAME_PATTERN", default_pattern)
        
        # Supported formats
        supported_formats_str = os.getenv(
            "SUPPORTED_FORMATS",
            "jpg,jpeg,png,gif,tiff,tif,bmp,webp"
        )
        self.supported_formats = [
            ext.strip().lower() 
            for ext in supported_formats_str.split(",")
        ]
        
        # File deletion
        delete_after_send_str = os.getenv("DELETE_AFTER_SEND", "false").lower()
        self.delete_after_send = delete_after_send_str in ("true", "1", "yes")
        
        # State tracking
        self.state_file = os.getenv("STATE_FILE", ".fax_adapter_state.json")
        
        # Polling interval
        self.poll_interval = float(os.getenv("POLL_INTERVAL", "1.0"))
        
        # Process existing files
        process_existing_str = os.getenv("PROCESS_EXISTING", "true").lower()
        self.process_existing = process_existing_str in ("true", "1", "yes")
    
    def get_headers(self) -> Dict[str, str]:
        """Get HTTP headers for conserver requests."""
        headers = {"Content-Type": "application/json"}
        if self.conserver_api_token:
            headers[self.conserver_header_name] = self.conserver_api_token
        return headers
    
    def get_filename_regex(self) -> re.Pattern:
        """Get compiled regex pattern for filename parsing."""
        return re.compile(self.filename_pattern, re.IGNORECASE)

