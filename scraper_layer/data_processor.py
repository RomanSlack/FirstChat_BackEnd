"""
Data processing module for Tinder Profile Scraper.

This module handles the processing of extracted profile data,
particularly downloading and saving images and JSON data.
"""

import os
import json
import asyncio
import httpx
from pathlib import Path
from typing import List, Dict, Any, Optional
from loguru import logger
import re
import time

from config import config


async def download_image(url: str, save_path: str, timeout: int = 30) -> bool:
    """
    Download image from URL asynchronously and save to specified path.
    
    Args:
        url: Image URL to download
        save_path: Path to save the image to
        timeout: Timeout in seconds
        
    Returns:
        True if download succeeded, False otherwise
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=timeout, follow_redirects=True)
            response.raise_for_status()
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            
            # Save the image to file
            with open(save_path, 'wb') as f:
                f.write(response.content)
                
            logger.info(f"Downloaded image to {save_path}")
            return True
            
    except Exception as e:
        logger.error(f"Failed to download image from {url} to {save_path}: {str(e)}")
        return False


async def process_profile_data(profile_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process and save profile data to disk.
    
    Args:
        profile_data: Raw profile data extracted from browser
        
    Returns:
        Processed profile data with local file paths
    """
    if not profile_data.get("name"):
        logger.error("Profile data is missing a name, cannot process")
        return profile_data
    
    # Clean the name to use as directory name (remove special chars)
    name = profile_data["name"]
    safe_name = re.sub(r'[\\/*?:"<>|]', "", name)
    timestamp = int(time.time())
    folder_name = f"{safe_name}_{timestamp}"
    
    # Create profile directory
    profile_dir = os.path.join(config.OUTPUT_DIR, folder_name)
    os.makedirs(profile_dir, exist_ok=True)
    
    # Add local paths to profile data
    processed_data = profile_data.copy()
    processed_data["folder_path"] = profile_dir
    
    # Process and download images
    image_urls = profile_data.get("image_urls", [])
    image_local_paths = []
    
    # Download images concurrently
    download_tasks = []
    for i, url in enumerate(image_urls):
        ext = url.split('?')[0].split('.')[-1] if '.' in url else 'jpg'
        if ext not in ['jpg', 'jpeg', 'png', 'gif', 'webp']:
            ext = 'jpg'  # Default to jpg if extension seems invalid
            
        image_filename = f"image_{i}.{ext}"
        image_path = os.path.join(profile_dir, image_filename)
        image_local_paths.append(image_path)
        
        download_tasks.append(download_image(url, image_path))
    
    # Wait for all image downloads to complete
    download_results = await asyncio.gather(*download_tasks)
    
    # Update the processing results
    processed_data["image_local_paths"] = image_local_paths
    processed_data["download_success_count"] = sum(1 for result in download_results if result)
    
    # Save profile data to JSON
    json_path = os.path.join(profile_dir, "profile_data.json")
    
    # Create a clean version of the data for JSON (removing HTML)
    json_data = processed_data.copy()
    if "html" in json_data:
        # Save HTML to a separate file
        html_path = os.path.join(profile_dir, "profile.html")
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(json_data["html"])
        json_data.pop("html")
    
    # Save the JSON
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Saved profile data to {json_path}")
    logger.info(f"Downloaded {processed_data['download_success_count']} of {len(image_urls)} images")
    
    return processed_data