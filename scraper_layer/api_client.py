"""
API client module for FirstChat Profile Scraper.

This module handles communication with the FirstChat API,
sending profile data and retrieving generated messages.
"""

import json
import asyncio
import httpx
from typing import Dict, Any, Optional, Union
from loguru import logger

from config import config


async def send_to_api(profile_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Send processed profile data to the FirstChat API.
    
    Args:
        profile_data: Processed profile data ready for API
        
    Returns:
        API response as dictionary
    """
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    # Initialize with empty response
    api_response = {"status": "error", "error": "Unknown error"}
    
    # Implement retry logic
    for attempt in range(1, config.MAX_RETRIES + 1):
        try:
            logger.info(f"Sending data to API (attempt {attempt}/{config.MAX_RETRIES})")
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    config.API_ENDPOINT,
                    json=profile_data,
                    headers=headers,
                    timeout=30  # 30 seconds timeout
                )
                
                # Parse response
                response_data = response.json()
                
                # Check if successful
                if response.status_code == 200 and response_data.get("status") == "success":
                    logger.info("Successfully received API response")
                    return response_data
                else:
                    error_detail = response_data.get("detail", response_data.get("error", "Unknown error"))
                    logger.error(f"API error: {error_detail} (Status: {response.status_code})")
                    api_response = {"status": "error", "error": error_detail}
            
        except httpx.TimeoutException:
            logger.warning(f"API request timed out (attempt {attempt}/{config.MAX_RETRIES})")
            api_response = {"status": "error", "error": "API request timed out"}
            
        except httpx.RequestError as e:
            logger.error(f"Request error: {str(e)} (attempt {attempt}/{config.MAX_RETRIES})")
            api_response = {"status": "error", "error": f"Request error: {str(e)}"}
            
        except Exception as e:
            logger.exception(f"Unexpected error sending to API: {str(e)} (attempt {attempt}/{config.MAX_RETRIES})")
            api_response = {"status": "error", "error": f"Unexpected error: {str(e)}"}
        
        # If not the last attempt, wait before retrying
        if attempt < config.MAX_RETRIES:
            retry_delay_seconds = config.RETRY_DELAY / 1000
            logger.info(f"Retrying in {retry_delay_seconds} seconds...")
            await asyncio.sleep(retry_delay_seconds)
    
    # If we get here, all attempts failed
    logger.error(f"Failed to send data to API after {config.MAX_RETRIES} attempts")
    return api_response


def format_api_response(response: Dict[str, Any]) -> str:
    """
    Format API response for display.
    
    Args:
        response: API response dictionary
        
    Returns:
        Formatted string for display
    """
    if response.get("status") == "success":
        data = response.get("data", {})
        message = data.get("generated_message", "No message generated")
        
        # Format token usage
        token_usage = data.get("token_usage", {})
        prompt_tokens = token_usage.get("prompt_tokens", 0)
        completion_tokens = token_usage.get("completion_tokens", 0)
        total_tokens = token_usage.get("total_tokens", 0)
        
        # Format processing time
        processing_time = response.get("processing_time", 0)
        
        # Format image tags
        image_tags = data.get("image_tags", [])
        tags_str = ", ".join(image_tags) if image_tags else "None"
        
        formatted = f"""
----- GENERATED MESSAGE -----
{message}

----- DETAILS -----
Image tags: {tags_str}
Processing time: {processing_time:.2f} seconds
Token usage: {prompt_tokens} prompt + {completion_tokens} completion = {total_tokens} total
"""
        return formatted.strip()
    else:
        error = response.get("error", "Unknown error")
        return f"Error: {error}"