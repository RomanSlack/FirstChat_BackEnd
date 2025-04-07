#!/usr/bin/env python3
"""
Simple script to extract Tinder image URLs from HTML.
This can be run directly on an HTML file to extract all image URLs.
"""

import re
import os
import sys
import json
from pathlib import Path
import asyncio
import httpx
from loguru import logger

# Configure logger
logger.remove()
logger.add(sys.stderr, level="INFO")

async def download_image(url, save_path, timeout=30, max_retries=3):
    """Download image from URL and save to path."""
    for attempt in range(max_retries):
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko)',
                'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
                'Referer': 'https://tinder.com/',
            }
            
            logger.info(f"Downloading image from {url} (attempt {attempt+1}/{max_retries})")
            
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=timeout, follow_redirects=True, headers=headers)
                response.raise_for_status()
                
                # Create directory if needed
                os.makedirs(os.path.dirname(save_path), exist_ok=True)
                
                # Save the image
                with open(save_path, 'wb') as f:
                    f.write(response.content)
                
                logger.info(f"Successfully downloaded to {save_path} ({len(response.content)} bytes)")
                return True
                
        except Exception as e:
            logger.error(f"Error downloading image: {str(e)}")
            if attempt < max_retries - 1:
                await asyncio.sleep(1)
            else:
                return False
    
    return False

def extract_image_urls(html_content):
    """Extract all Tinder image URLs from HTML content."""
    import html
    
    # We want to extract all image URLs from all slides
    # This pattern will match URLs from images-ssl.gotinder.com
    pattern = r'https://images-ssl\.gotinder\.com/[^"\')\s\\]+'
    
    # Find all matches in the HTML
    image_urls = re.findall(pattern, html_content)
    
    # Clean up URLs and remove duplicates
    clean_urls = []
    for url in image_urls:
        # Remove any trailing characters, quotes, etc.
        url = url.split('\\')[0].replace('"', '').replace("'", "")
        
        # Decode HTML entities like &amp; to &
        url = html.unescape(url)
        
        # Only add if not already in the list
        if url and url not in clean_urls:
            clean_urls.append(url)
    
    logger.info(f"Found {len(clean_urls)} unique image URLs")
    return clean_urls

async def process_profile_directory(profile_dir):
    """Process a profile directory to extract and download images."""
    html_path = os.path.join(profile_dir, "profile.html")
    if not os.path.exists(html_path):
        logger.error(f"No HTML file found in {profile_dir}")
        return False
    
    # Read the HTML file
    with open(html_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    # Extract image URLs
    image_urls = extract_image_urls(html_content)
    logger.info(f"Found {len(image_urls)} image URLs in HTML")
    
    # Save URLs to backup file
    backup_path = os.path.join(profile_dir, "image_urls_backup.txt")
    with open(backup_path, 'w', encoding='utf-8') as f:
        for url in image_urls:
            f.write(f"{url}\n")
    
    # Download images
    download_tasks = []
    successful_downloads = []
    
    for i, url in enumerate(image_urls):
        # Detect image format from URL
        if "webp" in url.lower():
            ext = "webp"
        elif "jpg" in url.lower() or "jpeg" in url.lower():
            ext = "jpg"
        elif "png" in url.lower():
            ext = "png"
        else:
            ext = "jpg"  # Default to jpg
        
        image_path = os.path.join(profile_dir, f"image_{i}.{ext}")
        download_tasks.append(download_image(url, image_path))
    
    # Download all images concurrently
    results = await asyncio.gather(*download_tasks)
    
    # Count successful downloads
    success_count = sum(1 for r in results if r)
    logger.info(f"Downloaded {success_count} of {len(image_urls)} images")
    
    # Update profile_data.json with new image information
    json_path = os.path.join(profile_dir, "profile_data.json")
    if os.path.exists(json_path):
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                profile_data = json.load(f)
            
            # Update image information
            profile_data["image_urls"] = image_urls
            profile_data["download_success_count"] = success_count
            
            # Save updated JSON
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(profile_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Updated profile data in {json_path}")
        except Exception as e:
            logger.error(f"Error updating profile data: {str(e)}")
    
    return True

async def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        logger.error("Usage: python extract_images.py <profile_directory_or_html_file>")
        return
    
    path = sys.argv[1]
    
    if os.path.isdir(path):
        # Process a profile directory
        await process_profile_directory(path)
    elif os.path.isfile(path) and path.endswith(".html"):
        # Process a single HTML file
        dirname = os.path.dirname(path)
        with open(path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        image_urls = extract_image_urls(html_content)
        logger.info(f"Found {len(image_urls)} image URLs in {path}")
        
        # Save URLs to backup file
        backup_path = os.path.join(dirname, "image_urls_from_script.txt")
        with open(backup_path, 'w', encoding='utf-8') as f:
            for url in image_urls:
                f.write(f"{url}\n")
        
        logger.info(f"Saved image URLs to {backup_path}")
    else:
        logger.error(f"Invalid path: {path}")

if __name__ == "__main__":
    asyncio.run(main())