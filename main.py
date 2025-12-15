#!/usr/bin/env python3
"""Main entry point for fax image vCon adapter."""

import sys
import signal
import logging
from pathlib import Path
from fax_adapter.config import Config
from fax_adapter.parser import FilenameParser
from fax_adapter.builder import VconBuilder
from fax_adapter.poster import HttpPoster
from fax_adapter.tracker import StateTracker
from fax_adapter.monitor import FileSystemMonitor
from fax_adapter.s3_monitor import S3Monitor


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class FaxAdapter:
    """Main adapter class that orchestrates all components."""
    
    def __init__(self, config: Config):
        """Initialize adapter with configuration."""
        self.config = config
        
        # Initialize components
        self.parser = FilenameParser(config.get_filename_regex())
        self.builder = VconBuilder()
        self.poster = HttpPoster(
            config.conserver_url, 
            config.get_headers(), 
            config.ingress_lists
        )
        self.tracker = StateTracker(config.state_file)
        
        # Initialize appropriate monitor based on source type
        if config.source_type == "filesystem":
            self.monitor = FileSystemMonitor(
                config.watch_directory,
                config.supported_formats,
                self._process_file
            )
        elif config.source_type == "s3":
            self.monitor = S3Monitor(
                config.s3_bucket_name,
                config.s3_prefix,
                config.supported_formats,
                self._process_file_s3,
                region=config.s3_region,
                credentials=config.get_aws_credentials(),
                poll_interval=config.s3_poll_interval,
                date_filter=config.s3_date_filter,
                date_range_start=config.s3_date_range_start,
                date_range_end=config.s3_date_range_end,
            )
        else:
            raise ValueError(f"Invalid source type: {config.source_type}")
        
        self.running = False
    
    def _process_file(self, filepath: str):
        """Process a single image file from filesystem.
        
        Args:
            filepath: Path to the image file
        """
        # Check if already processed
        if self.tracker.is_processed(filepath):
            logger.debug(f"Skipping already processed file: {filepath}")
            return
        
        # Parse filename
        parsed = self.parser.parse(filepath)
        if not parsed:
            logger.warning(f"Could not parse filename: {filepath}")
            return
        
        sender, receiver, extension = parsed
        
        # Build vCon
        vcon = self.builder.build(filepath, sender, receiver, extension)
        if not vcon:
            logger.error(f"Failed to build vCon from: {filepath}")
            return
        
        # Post to conserver
        success = self.poster.post(vcon)
        
        if success:
            # Mark as processed
            self.tracker.mark_processed(filepath, vcon.uuid, "success")
            
            # Delete file if configured
            if self.config.delete_after_send:
                try:
                    Path(filepath).unlink()
                    logger.info(f"Deleted file after successful post: {filepath}")
                except Exception as e:
                    logger.warning(f"Failed to delete file {filepath}: {e}")
        else:
            # Mark as failed but don't delete
            self.tracker.mark_processed(filepath, vcon.uuid, "failed")
            logger.error(f"Failed to post vCon for: {filepath}")
    
    def _process_file_s3(self, filepath: str, s3_key: str):
        """Process a single image file from S3.
        
        Args:
            filepath: Local path to downloaded temp file
            s3_key: S3 object key
        """
        # Check if already processed
        if self.tracker.is_processed(filepath, s3_key=s3_key):
            logger.debug(f"Skipping already processed S3 object: {s3_key}")
            return
        
        # Parse filename from S3 key
        parsed = self.parser.parse(s3_key)
        if not parsed:
            logger.warning(f"Could not parse S3 key: {s3_key}")
            return
        
        sender, receiver, extension = parsed
        
        # Build vCon from local temp file
        vcon = self.builder.build(filepath, sender, receiver, extension)
        if not vcon:
            logger.error(f"Failed to build vCon from S3 object: {s3_key}")
            return
        
        # Post to conserver
        success = self.poster.post(vcon)
        
        if success:
            # Mark as processed
            self.tracker.mark_processed(filepath, vcon.uuid, "success", s3_key=s3_key)
            
            # Delete S3 object if configured
            if self.config.s3_delete_after_send:
                if isinstance(self.monitor, S3Monitor):
                    self.monitor.delete_s3_object(s3_key)
        else:
            # Mark as failed but don't delete
            self.tracker.mark_processed(filepath, vcon.uuid, "failed", s3_key=s3_key)
            logger.error(f"Failed to post vCon for S3 object: {s3_key}")
    
    def process_existing_files(self):
        """Process existing files in the watch directory or S3 bucket."""
        if not self.config.process_existing:
            logger.info("Skipping existing files (PROCESS_EXISTING=false)")
            return
        
        logger.info("Processing existing files...")
        existing_files = self.monitor.get_existing_files()
        
        if self.config.source_type == "filesystem":
            for filepath in existing_files:
                self._process_file(filepath)
        elif self.config.source_type == "s3":
            # For S3, existing_files contains S3 keys
            for s3_key in existing_files:
                if isinstance(self.monitor, S3Monitor):
                    self.monitor._process_object(s3_key)
        
        logger.info(f"Finished processing {len(existing_files)} existing files")
    
    def start(self):
        """Start the adapter."""
        logger.info("Starting fax image vCon adapter...")
        
        # Process existing files first
        self.process_existing_files()
        
        # Start monitoring for new files
        self.monitor.start()
        self.running = True
        
        logger.info("Adapter is running. Press Ctrl+C to stop.")
        
        # Keep running until interrupted
        try:
            while self.running:
                import time
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
        finally:
            self.stop()
    
    def stop(self):
        """Stop the adapter."""
        if self.running:
            logger.info("Stopping adapter...")
            self.running = False
            self.monitor.stop()
            logger.info("Adapter stopped")


def main():
    """Main entry point."""
    try:
        # Load configuration
        config = Config()
        
        # Create adapter
        adapter = FaxAdapter(config)
        
        # Set up signal handlers for graceful shutdown
        def signal_handler(sig, frame):
            logger.info("Received shutdown signal")
            adapter.stop()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Start adapter
        adapter.start()
        
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()



