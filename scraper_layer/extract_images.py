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
    # Fix the URL one more time before download to be safe
    url = url.replace('&amp;', '&')
    url = url.replace('&quot;', '')
    url = url.replace('&quot', '')
    
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
    
    # Dictionary to store labeled image URLs
    labeled_urls = {}
    clean_urls = []
    
    # First, look specifically for "Profile Photo 1" which is the main profile image
    first_image_pattern = r'aria-label="Profile Photo 1"[^>]*?background-image: url\(&quot;(https://images-ssl\.gotinder\.com/[^&]*)&'
    
    # Also try alternate pattern "Profile Image 1" as a fallback
    alt_first_image_pattern = r'aria-label="Profile Image 1"[^>]*?background-image: url\(&quot;(https://images-ssl\.gotinder\.com/[^&]*)&'
    
    # Try the first pattern
    first_image_match = re.search(first_image_pattern, html_content)
    
    # If not found, try the alternate pattern
    if not first_image_match:
        first_image_match = re.search(alt_first_image_pattern, html_content)
    
    # If we found the first image, add it first
    if first_image_match:
        first_url = first_image_match.group(1)
        # Fix the URL by manually replacing all HTML entities
        first_url = first_url.replace('&amp;', '&')
        first_url = first_url.replace('&quot;', '')
        first_url = first_url.replace('&quot', '')
        
        # Final sanity check to ensure URL is valid
        if first_url.endswith('\\') or first_url.endswith('"') or first_url.endswith("'"):
            first_url = first_url[:-1]
            
        # Make sure first URL is properly formatted with https://
        if first_url and 'https://images-ssl.gotinder.com/' in first_url:
            labeled_urls["Profile Photo 1"] = first_url
            clean_urls.append(first_url)
            logger.info(f"Found first profile image (Profile Photo 1): {first_url[:60]}...")
    else:
        # If we couldn't find the first profile photo, log an error and return empty
        logger.error("CRITICAL ERROR: Could not find Profile Photo 1. Stopping process.")
        return [], {}  # Return empty list and empty dict to signal failure
    
    # Look for other profile photos with specific labels (2, 3, etc.)
    for i in range(2, 10):  # Look for photos 2 through 9
        photo_pattern = rf'aria-label="Profile Photo {i}"[^>]*?background-image: url\(&quot;(https://images-ssl\.gotinder\.com/[^&]*)&'
        alt_photo_pattern = rf'aria-label="Profile Image {i}"[^>]*?background-image: url\(&quot;(https://images-ssl\.gotinder\.com/[^&]*)&'
        
        photo_match = re.search(photo_pattern, html_content)
        if not photo_match:
            photo_match = re.search(alt_photo_pattern, html_content)
            
        if photo_match:
            photo_url = photo_match.group(1)
            # Clean the URL
            photo_url = photo_url.replace('&amp;', '&')
            photo_url = photo_url.replace('&quot;', '')
            photo_url = photo_url.replace('&quot', '')
            
            # Final sanity check
            if photo_url.endswith('\\') or photo_url.endswith('"') or photo_url.endswith("'"):
                photo_url = photo_url[:-1]
                
            if photo_url and 'https://images-ssl.gotinder.com/' in photo_url and photo_url not in clean_urls:
                labeled_urls[f"Profile Photo {i}"] = photo_url
                clean_urls.append(photo_url)
                logger.info(f"Found profile image (Profile Photo {i}): {photo_url[:60]}...")
    
    # Now find any remaining URLs for completeness
    pattern = r'https://images-ssl\.gotinder\.com/[^"\')\s\\]+'
    
    # Find all matches in the HTML
    raw_image_urls = re.findall(pattern, html_content)
    
    # Process each URL to clean it
    for url in raw_image_urls:
        # Remove any trailing characters, quotes, etc.
        url = url.split('\\')[0]
        
        # Fix URL by manually replacing all HTML entities
        url = url.replace('&amp;', '&')
        url = url.replace('&quot;', '')
        url = url.replace('&quot', '')
        
        # Final sanity check to ensure URL is valid
        if url.endswith('\\') or url.endswith('"') or url.endswith("'"):
            url = url[:-1]
            
        # Only add if not already in the list and looks like a valid URL
        if url and url not in clean_urls and 'https://images-ssl.gotinder.com/' in url:
            clean_urls.append(url)
            # These are unlabeled photos
            if url not in labeled_urls.values():
                labeled_urls[f"Unlabeled Photo {len(labeled_urls) + 1}"] = url
    
    logger.info(f"Found {len(clean_urls)} unique image URLs in total")
    logger.info(f"Found {len(labeled_urls)} labeled image URLs")
    
    # Return both the clean URLs list and the labeled URLs dictionary
    return clean_urls, labeled_urls

async def process_profile_directory(profile_dir):
    """Process a profile directory to extract and download images."""
    html_path = os.path.join(profile_dir, "profile.html")
    if not os.path.exists(html_path):
        logger.error(f"No HTML file found in {profile_dir}")
        return False
    
    # Read the HTML file
    with open(html_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    # Extract image URLs - now returns both clean_urls and labeled_urls
    image_urls, labeled_urls = extract_image_urls(html_content)
    
    # If we didn't find Profile Photo 1, stop the process
    if not image_urls or not labeled_urls:
        logger.error("Could not find Profile Photo 1. Stopping the image extraction process.")
        return False
    
    logger.info(f"Found {len(image_urls)} image URLs in HTML")
    
    # Save clean URLs to backup file
    backup_path = os.path.join(profile_dir, "image_urls_backup.txt")
    with open(backup_path, 'w', encoding='utf-8') as f:
        for url in image_urls:
            f.write(f"{url}\n")
    
    # Save labeled URLs to a separate file for reference
    labeled_backup_path = os.path.join(profile_dir, "labeled_image_urls.txt")
    with open(labeled_backup_path, 'w', encoding='utf-8') as f:
        for label, url in labeled_urls.items():
            f.write(f"{label}: {url}\n")
    
    # Download images with proper labeling
    download_tasks = []
    image_paths = {}  # Dictionary to map URLs to their local file paths
    
    # First, prepare all the labeled photos to be downloaded
    for label, url in labeled_urls.items():
        # Create a safe filename from the label
        safe_label = label.replace(" ", "_").lower()
        
        # Detect image format from URL
        if "webp" in url.lower():
            ext = "webp"
        elif "jpg" in url.lower() or "jpeg" in url.lower():
            ext = "jpg"
        elif "png" in url.lower():
            ext = "png"
        else:
            ext = "jpg"  # Default to jpg
        
        image_path = os.path.join(profile_dir, f"{safe_label}.{ext}")
        image_paths[url] = {"path": image_path, "label": label}
        download_tasks.append(download_image(url, image_path))
    
    # Then add any unlabeled images that might have been missed
    for i, url in enumerate(image_urls):
        if url not in image_paths:
            # Detect image format from URL
            if "webp" in url.lower():
                ext = "webp"
            elif "jpg" in url.lower() or "jpeg" in url.lower():
                ext = "jpg"
            elif "png" in url.lower():
                ext = "png"
            else:
                ext = "jpg"  # Default to jpg
            
            image_path = os.path.join(profile_dir, f"unlabeled_image_{i}.{ext}")
            image_paths[url] = {"path": image_path, "label": f"Unlabeled Image {i}"}
            download_tasks.append(download_image(url, image_path))
    
    # Download all images concurrently
    results = await asyncio.gather(*download_tasks)
    
    # Process download results
    successful_downloads = []
    for i, (url, result) in enumerate(zip(image_paths.keys(), results)):
        if result:
            successful_downloads.append({
                "url": url,
                "path": image_paths[url]["path"],
                "label": image_paths[url]["label"]
            })
    
    success_count = len(successful_downloads)
    logger.info(f"Downloaded {success_count} of {len(image_urls)} images")
    
    # Update profile_data.json with new image information
    json_path = os.path.join(profile_dir, "profile_data.json")
    if os.path.exists(json_path):
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                profile_data = json.load(f)
            
            # Update image information with labeled URLs
            profile_data["image_urls"] = image_urls
            profile_data["labeled_image_urls"] = labeled_urls
            profile_data["download_success_count"] = success_count
            
            # Add the successful downloads with labels
            profile_data["downloaded_images"] = [
                {
                    "label": download["label"],
                    "url": download["url"],
                    "local_path": download["path"]
                }
                for download in successful_downloads
            ]
            
            # Remove any screenshots from the root directory if they exist
            if "screenshot_paths" in profile_data:
                profile_data.pop("screenshot_paths", None)
            
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
        success = await process_profile_directory(path)
        if not success:
            logger.error("Failed to process profile directory. Exiting.")
            sys.exit(1)  # Exit with error code if Profile Photo 1 wasn't found
    elif os.path.isfile(path) and path.endswith(".html"):
        # Process a single HTML file
        dirname = os.path.dirname(path)
        with open(path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        image_urls, labeled_urls = extract_image_urls(html_content)
        
        # Check if we found the first profile photo
        if not image_urls or not labeled_urls:
            logger.error("CRITICAL ERROR: Could not find Profile Photo 1 in HTML. Exiting.")
            sys.exit(1)  # Exit with error code if Profile Photo 1 wasn't found
        
        logger.info(f"Found {len(image_urls)} image URLs in {path}")
        
        # Save URLs to backup file
        backup_path = os.path.join(dirname, "image_urls_from_script.txt")
        with open(backup_path, 'w', encoding='utf-8') as f:
            for url in image_urls:
                f.write(f"{url}\n")
        
        logger.info(f"Saved image URLs to {backup_path}")
        
        # Save labeled URLs to a separate file
        labeled_backup_path = os.path.join(dirname, "labeled_image_urls_from_script.txt")
        with open(labeled_backup_path, 'w', encoding='utf-8') as f:
            for label, url in labeled_urls.items():
                f.write(f"{label}: {url}\n")
        
        logger.info(f"Saved labeled image URLs to {labeled_backup_path}")
    else:
        logger.error(f"Invalid path: {path}")

if __name__ == "__main__":
    asyncio.run(main())