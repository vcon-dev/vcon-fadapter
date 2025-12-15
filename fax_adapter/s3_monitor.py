"""S3 bucket monitor to watch for new fax image files."""

import logging
import os
import re
import tempfile
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional, Set

try:
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError
except ImportError:
    boto3 = None
    ClientError = Exception
    NoCredentialsError = Exception


logger = logging.getLogger(__name__)


class S3Monitor:
    """Monitors S3 bucket for new fax image files."""
    
    # Date patterns to match in S3 keys
    DATE_PATTERNS = [
        re.compile(r"(\d{4})/(\d{2})/(\d{2})"),  # 2024/12/15
        re.compile(r"(\d{4})-(\d{2})-(\d{2})"),  # 2024-12-15
        re.compile(r"(\d{4})(\d{2})(\d{2})"),    # 20241215
    ]
    
    def __init__(
        self,
        bucket_name: str,
        prefix: str,
        supported_formats: List[str],
        callback: Callable[[str, str], None],  # callback(filepath, s3_key)
        region: Optional[str] = None,
        credentials: Optional[Dict[str, str]] = None,
        poll_interval: float = 30.0,
        date_filter: Optional[str] = None,
        date_range_start: Optional[str] = None,
        date_range_end: Optional[str] = None,
    ):
        """Initialize S3 monitor.
        
        Args:
            bucket_name: S3 bucket name
            prefix: S3 key prefix to filter objects
            supported_formats: List of supported file extensions
            callback: Function to call when a new image file is detected
            region: AWS region (optional)
            credentials: AWS credentials dict (optional, uses boto3 default chain if None)
            poll_interval: Seconds between polling S3
            date_filter: Exact date to filter (YYYY/MM/DD or variants)
            date_range_start: Start date for range filter
            date_range_end: End date for range filter
        """
        if boto3 is None:
            raise ImportError("boto3 is required for S3 monitoring. Install with: pip install boto3")
        
        self.bucket_name = bucket_name
        self.prefix = prefix
        self.supported_formats = set(ext.lower() for ext in supported_formats)
        self.callback = callback
        self.poll_interval = poll_interval
        
        # Date filtering
        self.date_filter = self._parse_date_filter(date_filter) if date_filter else None
        self.date_range_start = self._parse_date_filter(date_range_start) if date_range_start else None
        self.date_range_end = self._parse_date_filter(date_range_end) if date_range_end else None
        
        # Initialize S3 client
        session_kwargs = {}
        if region:
            session_kwargs["region_name"] = region
        if credentials:
            session_kwargs.update(credentials)
        
        try:
            self.s3_client = boto3.client("s3", **session_kwargs)
            # Test connection
            self.s3_client.head_bucket(Bucket=bucket_name)
        except NoCredentialsError:
            raise ValueError("AWS credentials not found. Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY or configure AWS credentials.")
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            if error_code == "404":
                raise ValueError(f"S3 bucket not found: {bucket_name}")
            elif error_code == "403":
                raise ValueError(f"Access denied to S3 bucket: {bucket_name}")
            else:
                raise ValueError(f"Error accessing S3 bucket {bucket_name}: {e}")
        
        # Tracking
        self.processed_keys: Set[str] = set()
        self.running = False
        self.poll_thread: Optional[threading.Thread] = None
        self.temp_dir = tempfile.mkdtemp(prefix="vcon_fadapter_")
        
        logger.info(f"Initialized S3 monitor for bucket: {bucket_name}, prefix: {prefix}")
    
    def start(self):
        """Start monitoring S3 bucket."""
        if self.running:
            logger.warning("S3 monitor already running")
            return
        
        self.running = True
        self.poll_thread = threading.Thread(target=self._poll_loop, daemon=True)
        self.poll_thread.start()
        logger.info("Started S3 monitoring")
    
    def stop(self):
        """Stop monitoring."""
        if not self.running:
            return
        
        logger.info("Stopping S3 monitor...")
        self.running = False
        if self.poll_thread:
            self.poll_thread.join(timeout=5.0)
        
        # Cleanup temp directory
        try:
            import shutil
            shutil.rmtree(self.temp_dir, ignore_errors=True)
        except Exception as e:
            logger.warning(f"Failed to clean up temp directory {self.temp_dir}: {e}")
        
        logger.info("S3 monitor stopped")
    
    def get_existing_files(self) -> List[str]:
        """Get list of existing image files in S3 bucket.
        
        Returns:
            List of S3 keys (not local file paths)
        """
        objects = self._list_objects()
        logger.info(f"Found {len(objects)} existing image files in S3")
        return [obj["Key"] for obj in objects]
    
    def _poll_loop(self):
        """Main polling loop."""
        logger.info(f"Starting S3 poll loop (interval: {self.poll_interval}s)")
        
        while self.running:
            try:
                objects = self._list_objects()
                
                for obj in objects:
                    if not self.running:
                        break
                    
                    key = obj["Key"]
                    etag = obj["ETag"].strip('"')
                    
                    # Create unique identifier with ETag
                    obj_id = f"{key}:{etag}"
                    
                    if obj_id not in self.processed_keys:
                        logger.info(f"New S3 object detected: {key}")
                        self._process_object(key)
                        self.processed_keys.add(obj_id)
                
            except Exception as e:
                logger.error(f"Error during S3 polling: {e}", exc_info=True)
            
            # Sleep with interrupt checking
            sleep_count = 0
            while sleep_count < self.poll_interval and self.running:
                time.sleep(1)
                sleep_count += 1
    
    def _list_objects(self) -> List[Dict]:
        """List objects in S3 bucket with filtering.
        
        Returns:
            List of object metadata dicts
        """
        objects = []
        
        try:
            paginator = self.s3_client.get_paginator("list_objects_v2")
            pages = paginator.paginate(Bucket=self.bucket_name, Prefix=self.prefix)
            
            for page in pages:
                for obj in page.get("Contents", []):
                    key = obj["Key"]
                    
                    # Skip if it's a directory marker
                    if key.endswith("/"):
                        continue
                    
                    # Check file extension
                    extension = Path(key).suffix.lstrip(".").lower()
                    if extension not in self.supported_formats:
                        continue
                    
                    # Check date filtering
                    if not self._matches_date_filter(key):
                        continue
                    
                    objects.append(obj)
        
        except ClientError as e:
            logger.error(f"Error listing S3 objects: {e}")
        
        return objects
    
    def _process_object(self, key: str):
        """Download and process an S3 object.
        
        Args:
            key: S3 object key
        """
        local_path = None
        try:
            # Download to temp file
            local_path = self._download_object(key)
            if local_path:
                # Call callback with both local path and S3 key
                self.callback(local_path, key)
        except Exception as e:
            logger.error(f"Error processing S3 object {key}: {e}", exc_info=True)
        finally:
            # Cleanup temp file
            if local_path:
                self._cleanup_temp_file(local_path)
    
    def _download_object(self, key: str) -> Optional[str]:
        """Download S3 object to temporary file.
        
        Args:
            key: S3 object key
            
        Returns:
            Local file path or None on error
        """
        try:
            # Create temp file with original extension
            extension = Path(key).suffix
            fd, temp_path = tempfile.mkstemp(suffix=extension, dir=self.temp_dir)
            os.close(fd)
            
            # Download file
            self.s3_client.download_file(self.bucket_name, key, temp_path)
            logger.debug(f"Downloaded {key} to {temp_path}")
            return temp_path
            
        except ClientError as e:
            logger.error(f"Error downloading S3 object {key}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error downloading {key}: {e}")
            return None
    
    def _cleanup_temp_file(self, filepath: str):
        """Clean up temporary downloaded file.
        
        Args:
            filepath: Local file path to delete
        """
        try:
            if os.path.exists(filepath):
                os.unlink(filepath)
                logger.debug(f"Cleaned up temp file: {filepath}")
        except Exception as e:
            logger.warning(f"Failed to clean up temp file {filepath}: {e}")
    
    def delete_s3_object(self, key: str) -> bool:
        """Delete an object from S3.
        
        Args:
            key: S3 object key
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=key)
            logger.info(f"Deleted S3 object: {key}")
            return True
        except ClientError as e:
            logger.error(f"Error deleting S3 object {key}: {e}")
            return False
    
    def _matches_date_filter(self, key: str) -> bool:
        """Check if S3 key matches date filter criteria.
        
        Args:
            key: S3 object key
            
        Returns:
            True if key matches filters or no filters set
        """
        # No filters means match everything
        if not self.date_filter and not self.date_range_start and not self.date_range_end:
            return True
        
        # Extract date from key
        key_date = self._extract_date_from_key(key)
        if not key_date:
            # No date found in key, include it if no filters
            return False
        
        # Check exact date filter
        if self.date_filter:
            return key_date.date() == self.date_filter.date()
        
        # Check date range
        key_date_only = key_date.date()
        if self.date_range_start and key_date_only < self.date_range_start.date():
            return False
        if self.date_range_end and key_date_only > self.date_range_end.date():
            return False
        
        return True
    
    def _extract_date_from_key(self, key: str) -> Optional[datetime]:
        """Extract date from S3 key using date patterns.
        
        Args:
            key: S3 object key
            
        Returns:
            datetime object or None if no date found
        """
        for pattern in self.DATE_PATTERNS:
            match = pattern.search(key)
            if match:
                try:
                    year, month, day = match.groups()
                    return datetime(int(year), int(month), int(day))
                except (ValueError, TypeError):
                    continue
        return None
    
    def _parse_date_filter(self, date_str: str) -> Optional[datetime]:
        """Parse date string to datetime object.
        
        Args:
            date_str: Date string in various formats
            
        Returns:
            datetime object or None
        """
        formats = ["%Y/%m/%d", "%Y-%m-%d", "%Y%m%d"]
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        return None

