"""vCon builder to create vCons from fax image files."""

import base64
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Tuple
from vcon import Vcon
from vcon.party import Party


logger = logging.getLogger(__name__)

# MIME type mapping for image formats
MIME_TYPES = {
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
    "gif": "image/gif",
    "tiff": "image/tiff",
    "tif": "image/tiff",
    "bmp": "image/bmp",
    "webp": "image/webp",
}


class VconBuilder:
    """Builds vCon objects from fax image files."""
    
    def build(
        self,
        filepath: str,
        sender: str,
        receiver: str,
        extension: str
    ) -> Optional[Vcon]:
        """Build a vCon from an image file.
        
        Args:
            filepath: Path to the image file
            sender: Sender phone number
            receiver: Receiver phone number
            extension: File extension
            
        Returns:
            Vcon object or None if building fails
        """
        try:
            path = Path(filepath)
            
            if not path.exists():
                logger.error(f"File does not exist: {filepath}")
                return None
            
            # Get file metadata
            file_stat = path.stat()
            creation_time = datetime.fromtimestamp(
                file_stat.st_mtime, 
                tz=timezone.utc
            )
            file_size = file_stat.st_size
            
            # Read image file
            try:
                with open(path, 'rb') as f:
                    image_data = f.read()
            except Exception as e:
                logger.error(f"Error reading image file {filepath}: {e}")
                return None
            
            # Get image dimensions if possible
            try:
                from PIL import Image
                with Image.open(path) as img:
                    width, height = img.size
                    dimensions = f"{width}x{height}"
            except Exception as e:
                logger.debug(f"Could not get image dimensions: {e}")
                dimensions = None
            
            # Create vCon
            vcon = Vcon.build_new()
            
            # Set creation time from file modification time
            try:
                vcon.created_at = creation_time.isoformat()
            except AttributeError:
                # Some vcon versions have created_at as read-only
                logger.debug("Could not set created_at attribute (read-only in this vcon version)")
            
            # Add parties
            sender_party = Party(tel=sender)
            receiver_party = Party(tel=receiver)
            vcon.add_party(sender_party)
            vcon.add_party(receiver_party)
            
            # Encode image as base64
            image_base64 = base64.b64encode(image_data).decode('utf-8')
            
            # Get MIME type
            mime_type = MIME_TYPES.get(extension.lower(), "image/jpeg")
            
            # Add image as attachment
            # Try different parameter combinations for compatibility with various vcon library versions
            try:
                vcon.add_attachment(
                    type="fax_image",
                    body=image_base64,
                    encoding="base64",
                    filename=path.name,
                    mimetype=mime_type
                )
            except TypeError:
                try:
                    # Try without filename
                    vcon.add_attachment(
                        type="fax_image",
                        body=image_base64,
                        encoding="base64",
                        mimetype=mime_type
                    )
                except TypeError:
                    # Fall back to minimal parameters with type
                    vcon.add_attachment(
                        type="fax_image",
                        body=image_base64,
                        encoding="base64"
                    )
            
            # Add metadata tags
            vcon.add_tag("source", "fax_adapter")
            vcon.add_tag("original_filename", path.name)
            vcon.add_tag("file_size", str(file_size))
            if dimensions:
                vcon.add_tag("image_dimensions", dimensions)
            vcon.add_tag("sender", sender)
            vcon.add_tag("receiver", receiver)
            
            logger.info(
                f"Created vCon {vcon.uuid} from {filepath} "
                f"(sender: {sender}, receiver: {receiver})"
            )
            
            return vcon
            
        except Exception as e:
            logger.error(f"Error building vCon from {filepath}: {e}")
            return None

