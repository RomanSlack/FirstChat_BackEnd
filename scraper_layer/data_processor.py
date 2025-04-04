"""
Data processing module for FirstChat Profile Scraper.

This module handles the processing of extracted profile data,
particularly image downloading and conversion to base64.
"""

import base64
import io
from typing import List, Dict, Any, Optional, Tuple
import asyncio
import httpx
from PIL import Image
from loguru import logger

from config import config


async def download_image(url: str, timeout: int = 30) -> Optional[bytes]:
    """
    Download image from URL asynchronously.
    
    Args:
        url: Image URL to download
        timeout: Timeout in seconds
        
    Returns:
        Image bytes or None if download failed
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=timeout, follow_redirects=True)
            response.raise_for_status()
            return response.content
    except Exception as e:
        logger.error(f"Failed to download image from {url}: {str(e)}")
        return None


async def image_to_base64(image_bytes: bytes, format: str = "JPEG") -> str:
    """
    Convert image bytes to base64 string with data URL format.
    
    Args:
        image_bytes: Raw image bytes
        format: Output image format (JPEG, PNG, etc.)
        
    Returns:
        Base64 encoded image with data URL prefix
    """
    try:
        # Open the image and convert to desired format
        image = Image.open(io.BytesIO(image_bytes))
        
        # Resize if too large (optional)
        max_dimension = 1200  # Reasonable size for API
        if max(image.size) > max_dimension:
            # Maintain aspect ratio
            if image.width > image.height:
                new_width = max_dimension
                new_height = int(max_dimension * image.height / image.width)
            else:
                new_height = max_dimension
                new_width = int(max_dimension * image.width / image.height)
            
            image = image.resize((new_width, new_height), Image.LANCZOS)
        
        # Convert image to bytes in specified format
        buffer = io.BytesIO()
        image.save(buffer, format=format)
        image_bytes = buffer.getvalue()
        
        # Convert to base64 and add data URL prefix
        encoded = base64.b64encode(image_bytes).decode('utf-8')
        mime_type = f"image/{format.lower()}"
        data_url = f"data:{mime_type};base64,{encoded}"
        
        return data_url
    except Exception as e:
        logger.error(f"Failed to convert image to base64: {str(e)}")
        # Return placeholder image if conversion fails
        return get_placeholder_image()


def get_placeholder_image() -> str:
    """
    Return a placeholder image as base64 for when image processing fails.
    
    Returns:
        Base64 encoded placeholder image
    """
    # 1x1 transparent pixel
    return "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="


async def process_profile_data(profile_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process raw profile data into the format needed for the API.
    
    Args:
        profile_data: Raw profile data extracted from browser
        
    Returns:
        Processed profile data ready for API
    """
    processed_data = {
        "match_bio": {
            "name": profile_data.get("name", "Unknown"),
            "bio": profile_data.get("bio", ""),
            "interests": profile_data.get("interests", [])
        }
    }
    
    # Add age if available
    if "age" in profile_data and profile_data["age"]:
        processed_data["match_bio"]["age"] = profile_data["age"]
    
    # Process images
    image_urls = profile_data.get("image_urls", [])
    base64_images = []
    
    # Download images concurrently
    download_tasks = [download_image(url) for url in image_urls[:config.IMAGE_COUNT]]
    image_bytes_list = await asyncio.gather(*download_tasks)
    
    # Process images to base64
    for img_bytes in image_bytes_list:
        if img_bytes:
            base64_image = await image_to_base64(img_bytes)
            base64_images.append(base64_image)
    
    # Ensure we have at least config.IMAGE_COUNT images (use placeholders if needed)
    while len(base64_images) < config.IMAGE_COUNT:
        logger.warning(f"Adding placeholder image. Only had {len(base64_images)} valid images")
        base64_images.append(get_placeholder_image())
    
    # Add the first two images to the processed data
    processed_data["image1"] = base64_images[0]
    if len(base64_images) > 1:
        processed_data["image2"] = base64_images[1]
    
    # Add user bio and message generation parameters
    processed_data["user_bio"] = config.USER_BIO
    processed_data["sentence_count"] = config.MESSAGE_SENTENCE_COUNT
    processed_data["tone"] = config.MESSAGE_TONE
    processed_data["creativity"] = config.MESSAGE_CREATIVITY
    
    return processed_data