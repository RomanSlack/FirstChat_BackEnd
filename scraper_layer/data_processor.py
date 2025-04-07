"""
Data processing module for Tinder Profile Scraper.

This module handles the processing of extracted profile data,
particularly downloading and saving images and JSON data.
"""

import os
import sys
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
    url = url.replace('&quot;', '').replace('\"', '').replace("'", "")
    if not url.startswith('https://'):
        logger.error(f"Invalid URL format: {url}")
        return False
    if 'images-ssl.gotinder.com' in url and ('Policy=' in url or 'Signature=' in url):
        logger.warning(f"Tinder image URL requires authentication, can't download directly: {url}")
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        with open(f"{save_path}.url", 'w') as f:
            f.write(url)
        return False
    for attempt in range(max_retries):
        try:
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
                content_type = response.headers.get('content-type', '')
                if not content_type.startswith('image/'):
                    logger.warning(f"URL didn't return an image: {url} (Content-Type: {content_type})")
                    if len(response.content) < 1000:
                        logger.warning(f"Small response received ({len(response.content)} bytes), retrying...")
                        if attempt < max_retries - 1:
                            await asyncio.sleep(1)
                            continue
                        else:
                            return False
                os.makedirs(os.path.dirname(save_path), exist_ok=True)
                with open(save_path, 'wb') as f:
                    f.write(response.content)
                logger.info(f"Downloaded image to {save_path} ({len(response.content)} bytes)")
                return True
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error downloading image: {e.response.status_code} - {url}")
            if e.response.status_code == 403:
                os.makedirs(os.path.dirname(save_path), exist_ok=True)
                with open(f"{save_path}.url", 'w') as f:
                    f.write(url)
                logger.warning(f"Access forbidden, URL requires authentication. Saved URL to {save_path}.url")
                return False
            if 500 <= e.response.status_code < 600 and attempt < max_retries - 1:
                logger.warning("Server error, retrying in 1 second...")
                await asyncio.sleep(1)
                continue
            return False
        except Exception as e:
            logger.error(f"Failed to download image from {url} to {save_path}: {str(e)}")
            if attempt < max_retries - 1:
                logger.warning("Retrying in 1 second...")
                await asyncio.sleep(1)
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
        profile_data["name"] = "Unknown"
    name = profile_data["name"]
    safe_name = re.sub(r'[\\/*?:"<>|]', "", name)
    timestamp = int(time.time())
    folder_name = f"{safe_name}_{timestamp}"
    profile_dir = os.path.join(config.OUTPUT_DIR, folder_name)
    os.makedirs(profile_dir, exist_ok=True)
    processed_data = profile_data.copy()
    processed_data["folder_path"] = profile_dir
    image_urls = profile_data.get("image_urls", [])
    labeled_image_urls = profile_data.get("labeled_image_urls", {})
    if not labeled_image_urls.get("Profile Photo 1"):
        logger.error("CRITICAL ERROR: Profile Photo 1 not found in data. Stopping processing.")
        profile_data["error"] = "Missing Profile Photo 1"
        json_path = os.path.join(profile_dir, "profile_data.json")
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(profile_data, f, indent=2, ensure_ascii=False)
        logger.error("Exiting immediately as Profile Photo 1 is required")
        sys.exit(1)
        return profile_data
    backup_urls = profile_data.get("image_urls_backup", [])
    if backup_urls:
        for url in backup_urls:
            if url not in image_urls:
                image_urls.append(url)
        logger.info(f"Added {len(backup_urls)} backup image URLs, total is now {len(image_urls)}")
    labeled_backup_path = os.path.join(profile_dir, "labeled_image_urls.txt")
    with open(labeled_backup_path, 'w', encoding='utf-8') as f:
        for label, url in labeled_image_urls.items():
            f.write(f"{label}: {url}\n")
    with open(os.path.join(profile_dir, "image_urls_backup.txt"), 'w', encoding='utf-8') as f:
        for url in image_urls:
            f.write(f"{url}\n")
    image_local_paths = []
    successful_downloads = []
    downloaded_images_info = []
    logger.info(f"Processing {len(image_urls)} images including {len(labeled_image_urls)} labeled images")
    download_tasks = []
    image_info = []
    batch_size = 3
    for label, url in labeled_image_urls.items():
        safe_label = label.replace(" ", "_").lower()
        if not url or 'https://images-ssl.gotinder.com/' not in url:
            logger.warning(f"Skipping invalid URL for {label}: {url}")
            continue
        if label == "Profile Photo 1":
            logger.info(f"Processing Profile Photo 1 URL: {url[:100]}...")
            if "Signature=" not in url:
                logger.warning("Profile Photo 1 URL doesn't contain a signature!")
        if "webp" in url.lower():
            ext = "webp"
        elif "jpg" in url.lower() or "jpeg" in url.lower():
            ext = "jpg"
        elif "png" in url.lower():
            ext = "png"
        elif "gif" in url.lower():
            ext = "gif"
        else:
            ext = "jpg"
        image_filename = f"{safe_label}.{ext}"
        image_path = os.path.join(profile_dir, image_filename)
        image_local_paths.append(image_path)
        image_info.append({
            "url": url,
            "path": image_path,
            "label": label
        })
        download_tasks.append(download_image(url, image_path))
        if len(download_tasks) >= batch_size or label == list(labeled_image_urls.keys())[-1]:
            batch_results = await asyncio.gather(*download_tasks)
            for j, result in enumerate(batch_results):
                if result and j < len(image_info):
                    successful_downloads.append(image_info[j]["path"])
                    downloaded_images_info.append(image_info[j])
                    logger.info(f"Successfully downloaded image: {image_info[j]['label']}")
            download_tasks = []
            image_info = []
            await asyncio.sleep(0.5)
    unlabeled_count = 0
    for i, url in enumerate(image_urls):
        if url in labeled_image_urls.values():
            continue
        if "webp" in url.lower():
            ext = "webp"
        elif "jpg" in url.lower() or "jpeg" in url.lower():
            ext = "jpg"
        elif "png" in url.lower():
            ext = "png"
        elif "gif" in url.lower():
            ext = "gif"
        else:
            ext = "jpg"
        unlabeled_count += 1
        image_filename = f"unlabeled_image_{unlabeled_count}.{ext}"
        image_path = os.path.join(profile_dir, image_filename)
        image_local_paths.append(image_path)
        image_info.append({
            "url": url,
            "path": image_path,
            "label": f"Unlabeled Image {unlabeled_count}"
        })
        download_tasks.append(download_image(url, image_path))
        if len(download_tasks) >= batch_size or i == len(image_urls) - 1:
            batch_results = await asyncio.gather(*download_tasks)
            for j, result in enumerate(batch_results):
                if result and j < len(image_info):
                    successful_downloads.append(image_info[j]["path"])
                    downloaded_images_info.append(image_info[j])
                    logger.info(f"Successfully downloaded image: {image_info[j]['label']}")
            download_tasks = []
            image_info = []
            await asyncio.sleep(0.5)
    processed_data["image_local_paths"] = image_local_paths
    processed_data["successful_image_paths"] = successful_downloads
    processed_data["download_success_count"] = len(successful_downloads)
    processed_data["downloaded_images"] = downloaded_images_info
    if labeled_image_urls:
        processed_data["labeled_image_urls"] = labeled_image_urls
    json_path = os.path.join(profile_dir, "profile_data.json")
    json_data = processed_data.copy()
    if "html" in json_data:
        html_path = os.path.join(profile_dir, "profile.html")
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(json_data["html"])
        json_data.pop("html")
    if "screenshot_paths" in json_data:
        json_data.pop("screenshot_paths")
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, indent=2, ensure_ascii=False)
    summary_path = os.path.join(profile_dir, "summary.txt")
    with open(summary_path, 'w', encoding='utf-8') as f:
        f.write(f"Name: {profile_data.get('name', 'Unknown')}\n")
        f.write(f"Age: {profile_data.get('age', 'Unknown')}\n")
        f.write(f"Images: {processed_data['download_success_count']} of {len(image_urls)} downloaded\n")
        f.write("\nLabeled Images:\n")
        for label, url in labeled_image_urls.items():
            f.write(f"  {label}\n")
        f.write(f"\nInterests: {', '.join(profile_data.get('interests', []))}\n\n")
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
    if "Profile Photo 1" in labeled_image_urls:
        first_photo_url = labeled_image_urls["Profile Photo 1"]
        logger.info(f"Successfully extracted Profile Photo 1: {first_photo_url[:60]}...")
    return processed_data
