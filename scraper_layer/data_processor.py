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


async def download_image(url: str, save_path: str, timeout: int = 30, max_retries: int = 3) -> bool:
    """
    Download image from URL asynchronously and save to specified path.
    
    Args:
        url: Image URL to download
        save_path: Path to save the image to
        timeout: Timeout in seconds
        max_retries: Maximum number of retry attempts
        
    Returns:
        True if download succeeded, False otherwise
    """
    # Clean the URL - remove quotes and other artifacts
    url = url.replace('&quot;', '').replace('"', '').replace("'", "")
    
    # Make sure it's a valid URL
    if not url.startswith('https://'):
        logger.error(f"Invalid URL format: {url}")
        return False
    
    # For Tinder images that include authentication tokens, we'll skip trying to download them
    # as they require a valid session. Instead, we'll save the URL for reference.
    if 'images-ssl.gotinder.com' in url and ('Policy=' in url or 'Signature=' in url):
        logger.warning(f"Tinder image URL requires authentication, can't download directly: {url}")
        
        # Write the URL to the save path as a reference
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        with open(f"{save_path}.url", 'w') as f:
            f.write(url)
            
        # Since we can't download the file, we'll treat this as a failure for the download operation
        return False
    
    # For all other URLs, attempt normal download
    for attempt in range(max_retries):
        try:
            # Set up custom headers to avoid being blocked
            headers = {
                'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1',
                'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Referer': 'https://tinder.com/',
                'Sec-Fetch-Dest': 'image',
                'Sec-Fetch-Mode': 'no-cors',
                'Sec-Fetch-Site': 'cross-site',
            }
            
            logger.info(f"Downloading image from {url} (attempt {attempt+1}/{max_retries})")
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url, 
                    timeout=timeout, 
                    follow_redirects=True,
                    headers=headers
                )
                response.raise_for_status()
                
                # Check if the response is an image
                content_type = response.headers.get('content-type', '')
                if not content_type.startswith('image/'):
                    logger.warning(f"URL didn't return an image: {url} (Content-Type: {content_type})")
                    
                    # Check if it's just a small response (likely an error page)
                    if len(response.content) < 1000:
                        logger.warning(f"Small response received ({len(response.content)} bytes), retrying...")
                        if attempt < max_retries - 1:
                            await asyncio.sleep(1)  # Wait before retrying
                            continue
                        else:
                            return False
                
                # Create directory if it doesn't exist
                os.makedirs(os.path.dirname(save_path), exist_ok=True)
                
                # Save the image to file
                with open(save_path, 'wb') as f:
                    f.write(response.content)
                    
                logger.info(f"Downloaded image to {save_path} ({len(response.content)} bytes)")
                return True
                
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error downloading image: {e.response.status_code} - {url}")
            if e.response.status_code == 403:
                # Save the URL that requires authentication
                os.makedirs(os.path.dirname(save_path), exist_ok=True)
                with open(f"{save_path}.url", 'w') as f:
                    f.write(url)
                logger.warning(f"Access forbidden, URL requires authentication. Saved URL to {save_path}.url")
                return False
            
            # Retry for server errors (5xx)
            if 500 <= e.response.status_code < 600 and attempt < max_retries - 1:
                logger.warning(f"Server error, retrying in 1 second...")
                await asyncio.sleep(1)  # Wait before retrying
                continue
            return False
                
        except Exception as e:
            logger.error(f"Failed to download image from {url} to {save_path}: {str(e)}")
            if attempt < max_retries - 1:
                logger.warning(f"Retrying in 1 second...")
                await asyncio.sleep(1)  # Wait before retrying
            else:
                return False
    
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
        # Use a default name if none is available
        profile_data["name"] = "Unknown"
    
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
    
    # Also check if we have backup image URLs
    backup_urls = profile_data.get("image_urls_backup", [])
    if backup_urls:
        # Combine with main image URLs, eliminating duplicates
        for url in backup_urls:
            if url not in image_urls:
                image_urls.append(url)
        logger.info(f"Added {len(backup_urls)} backup image URLs, total is now {len(image_urls)}")
    
    image_local_paths = []
    successful_downloads = []
    
    logger.info(f"Processing {len(image_urls)} images")
    
    # Create a backup of the image URLs
    with open(os.path.join(profile_dir, "image_urls_backup.txt"), 'w', encoding='utf-8') as f:
        for url in image_urls:
            f.write(f"{url}\n")
            
    # Move screenshots to the profile directory
    screenshot_paths = profile_data.get("screenshot_paths", [])
    if screenshot_paths:
        logger.info(f"Moving {len(screenshot_paths)} screenshots to profile directory")
        for i, screenshot_path in enumerate(screenshot_paths):
            if os.path.exists(screenshot_path):
                filename = os.path.basename(screenshot_path)
                destination = os.path.join(profile_dir, filename)
                try:
                    import shutil
                    shutil.copy2(screenshot_path, destination)
                    logger.info(f"Copied screenshot to {destination}")
                except Exception as e:
                    logger.error(f"Error copying screenshot: {str(e)}")
    
    # Download images concurrently (but not too many at once to avoid rate limits)
    download_tasks = []
    batch_size = 3  # Download 3 images at a time
    
    for i, url in enumerate(image_urls):
        # Detect image format from URL (or default to jpg)
        if "webp" in url.lower():
            ext = "webp"
        elif "jpg" in url.lower() or "jpeg" in url.lower():
            ext = "jpg"
        elif "png" in url.lower():
            ext = "png"
        elif "gif" in url.lower():
            ext = "gif"
        else:
            ext = "jpg"  # Default to jpg
            
        image_filename = f"image_{i}.{ext}"
        image_path = os.path.join(profile_dir, image_filename)
        image_local_paths.append(image_path)
        
        download_tasks.append(download_image(url, image_path))
        
        # Process in batches to avoid overwhelming the server
        if len(download_tasks) >= batch_size or i == len(image_urls) - 1:
            # Store the starting index for this batch
            batch_start_index = i - len(download_tasks) + 1
            
            # Wait for all downloads in this batch to complete
            batch_results = await asyncio.gather(*download_tasks)
            
            # Process results
            for j, result in enumerate(batch_results):
                if result:
                    # Calculate the correct index in the full image_local_paths list
                    successful_index = batch_start_index + j
                    if 0 <= successful_index < len(image_local_paths):
                        successful_downloads.append(image_local_paths[successful_index])
                        logger.info(f"Successfully downloaded image {successful_index}")
            
            # Reset for next batch
            download_tasks = []
            # Small delay between batches
            await asyncio.sleep(0.5)
    
    # Update the processing results
    processed_data["image_local_paths"] = image_local_paths
    processed_data["successful_image_paths"] = successful_downloads
    processed_data["download_success_count"] = len(successful_downloads)
    
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
    
    # Create a summary file for quick reference
    summary_path = os.path.join(profile_dir, "summary.txt")
    with open(summary_path, 'w', encoding='utf-8') as f:
        f.write(f"Name: {profile_data.get('name', 'Unknown')}\n")
        f.write(f"Age: {profile_data.get('age', 'Unknown')}\n")
        f.write(f"Images: {processed_data['download_success_count']} of {len(image_urls)} downloaded\n")
        f.write(f"Interests: {', '.join(profile_data.get('interests', []))}\n\n")
        
        # Add sections data
        f.write("Profile Sections:\n")
        for section_name, section_data in profile_data.get("profile_sections", {}).items():
            f.write(f"\n{section_name}:\n")
            if isinstance(section_data, dict):
                for key, value in section_data.items():
                    f.write(f"  {key}: {value}\n")
            elif isinstance(section_data, list):
                for item in section_data:
                    f.write(f"  - {item}\n")
            else:
                f.write(f"  {section_data}\n")
    
    logger.info(f"Saved profile data to {json_path}")
    logger.info(f"Created summary at {summary_path}")
    logger.info(f"Downloaded {processed_data['download_success_count']} of {len(image_urls)} images")
    
    return processed_data