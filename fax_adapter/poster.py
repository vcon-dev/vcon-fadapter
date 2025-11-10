"""HTTP poster to send vCons to conserver endpoint."""

import logging
from typing import Dict, Optional
from vcon import Vcon


logger = logging.getLogger(__name__)


class HttpPoster:
    """Posts vCons to HTTP conserver endpoint."""
    
    def __init__(self, url: str, headers: Dict[str, str]):
        """Initialize HTTP poster.
        
        Args:
            url: Conserver endpoint URL
            headers: HTTP headers to include in requests
        """
        self.url = url
        self.headers = headers
    
    def post(self, vcon: Vcon) -> bool:
        """Post vCon to conserver endpoint.
        
        Args:
            vcon: Vcon object to post
            
        Returns:
            True if post was successful, False otherwise
        """
        try:
            logger.info(f"Posting vCon {vcon.uuid} to {self.url}")
            
            response = vcon.post_to_url(self.url, headers=self.headers)
            
            # Check if response indicates success
            # post_to_url may return different types, check status code if available
            if hasattr(response, 'status_code'):
                if response.status_code >= 200 and response.status_code < 300:
                    logger.info(
                        f"Successfully posted vCon {vcon.uuid} "
                        f"(status: {response.status_code})"
                    )
                    return True
                else:
                    logger.error(
                        f"Failed to post vCon {vcon.uuid} "
                        f"(status: {response.status_code})"
                    )
                    return False
            else:
                # If no status_code attribute, assume success if no exception
                logger.info(f"Posted vCon {vcon.uuid} to {self.url}")
                return True
                
        except Exception as e:
            logger.error(f"Error posting vCon {vcon.uuid} to {self.url}: {e}")
            return False

