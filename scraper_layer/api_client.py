"""
API Client for FirstChat REST API

This module handles the communication between the scraper and the API,
converting scraped profile data into the format expected by the message generator API.
"""

import os
import json
import base64
import random
import asyncio
import httpx
import time
from typing import Dict, Any, List, Optional
from pathlib import Path
from loguru import logger


async def encode_image_to_base64(image_path: str) -> Optional[str]:
    """
    Encode an image file to base64 string.
    
    Args:
        image_path: Path to the image file
        
    Returns:
        Base64 encoded string of the image or None if failed
    """
    try:
        with open(image_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode("utf-8")
            return f"data:image;base64,{encoded_string}"
    except Exception as e:
        logger.error(f"Error encoding image {image_path}: {str(e)}")
        return None


async def prepare_api_request(profile_data: Dict[str, Any], user_bio: str) -> Optional[Dict[str, Any]]:
    """
    Prepare request data for the FirstChat API from scraped profile data.
    
    Args:
        profile_data: Scraped profile data
        user_bio: Bio of the user requesting the first message
        
    Returns:
        Formatted request data ready to be sent to the API
    """
    try:
        # Extract basic profile information
        match_bio = {
            "name": profile_data.get("name", "Unknown"),
            "age": profile_data.get("age", 0),
            "bio": "",
            "interests": profile_data.get("interests", [])
        }
        
        # Combine profile sections to create a comprehensive bio
        bio_text = []
        for section_name, section_data in profile_data.get("profile_sections", {}).items():
            if isinstance(section_data, dict):
                section_text = f"{section_name}: " + ", ".join([f"{k}: {v}" for k, v in section_data.items()])
                bio_text.append(section_text)
            elif isinstance(section_data, str):
                bio_text.append(f"{section_name}: {section_data}")
        
        match_bio["bio"] = "\n".join(bio_text)
        
        # Get profile photo paths
        image_paths = profile_data.get("image_local_paths", [])
        successful_images = profile_data.get("successful_image_paths", [])
        
        # Use successful downloads if available, otherwise try with available paths
        available_images = successful_images if successful_images else image_paths
        
        if not available_images or len(available_images) < 1:
            logger.error("No images available to send to API")
            return None
            
        # Always use the first image (Profile Photo 1)
        image1_path = available_images[0]
        
        # Randomly select a second image from the remaining ones
        remaining_images = available_images[1:] if len(available_images) > 1 else [available_images[0]]
        image2_path = random.choice(remaining_images)
        
        # Encode images to base64
        image1_encoded = await encode_image_to_base64(image1_path)
        image2_encoded = await encode_image_to_base64(image2_path)
        
        if not image1_encoded or not image2_encoded:
            logger.error("Failed to encode one or both images")
            return None
            
        # Prepare the API request
        request_data = {
            "image1": image1_encoded,
            "image2": image2_encoded,
            "user_bio": user_bio,
            "match_bio": match_bio,
            "sentence_count": 2,
            "tone": "friendly",
            "creativity": 0.7
        }
        
        return request_data
        
    except Exception as e:
        logger.error(f"Error preparing API request: {str(e)}")
        return None


async def send_to_api(request_data: Dict[str, Any], api_url: str = "http://localhost:8002/generate_message") -> Optional[Dict[str, Any]]:
    """
    Send request to the FirstChat API.
    
    Args:
        request_data: Formatted request data
        api_url: URL of the FirstChat API
        
    Returns:
        API response or None if failed
    """
    try:
        logger.info(f"Sending request to API: {api_url}")
        start_time = time.time()
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                api_url,
                json=request_data,
                headers={"Content-Type": "application/json"}
            )
            
        elapsed_time = time.time() - start_time
        logger.info(f"API request completed in {elapsed_time:.2f} seconds")
        
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"API request failed with status code {response.status_code}: {response.text}")
            return None
            
    except Exception as e:
        logger.error(f"Error sending request to API: {str(e)}")
        return None
        

async def process_profile_for_firstchat(profile_folder: str, user_bio: str, api_url: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Process a profile folder to generate a first chat message.
    
    Args:
        profile_folder: Path to the profile folder containing profile_data.json
        user_bio: Bio of the user requesting the first message
        api_url: Optional URL of the FirstChat API (defaults to localhost)
        
    Returns:
        Generated message data or None if failed
    """
    try:
        profile_data_path = os.path.join(profile_folder, "profile_data.json")
        
        if not os.path.exists(profile_data_path):
            logger.error(f"Profile data not found at {profile_data_path}")
            return None
            
        with open(profile_data_path, 'r', encoding='utf-8') as f:
            profile_data = json.load(f)
            
        # Use provided API URL or default to localhost
        actual_api_url = api_url or "http://localhost:8002/generate_message"
        
        # Prepare the request data
        request_data = await prepare_api_request(profile_data, user_bio)
        if not request_data:
            return None
            
        # Send to API
        api_response = await send_to_api(request_data, actual_api_url)
        if not api_response:
            return None
            
        # Save the generated message to the profile folder
        result_path = os.path.join(profile_folder, "firstchat_message.json")
        with open(result_path, 'w', encoding='utf-8') as f:
            json.dump(api_response, f, indent=2)
            
        logger.info(f"Generated message saved to {result_path}")
        
        # Return the response for immediate use
        return api_response
        
    except Exception as e:
        logger.error(f"Error processing profile for FirstChat: {str(e)}")
        return None