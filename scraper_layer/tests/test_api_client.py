"""
Tests for the API client module.
"""

import pytest
import asyncio
from unittest.mock import patch, MagicMock
import httpx
import json

from api_client import send_to_api, format_api_response


@pytest.mark.asyncio
async def test_send_to_api_success():
    """Test successful API request."""
    # Sample profile data
    profile_data = {
        "image1": "data:image/jpeg;base64,test",
        "image2": "data:image/jpeg;base64,test",
        "user_bio": "Test user bio",
        "match_bio": {
            "name": "Test User",
            "age": 25,
            "bio": "Test bio",
            "interests": ["hiking", "photography"]
        },
        "sentence_count": 2,
        "tone": "friendly",
        "creativity": 0.7
    }
    
    # Expected API response
    api_response = {
        "status": "success",
        "data": {
            "generated_message": "Test message",
            "image_tags": ["test", "photo"],
            "token_usage": {
                "prompt_tokens": 100,
                "completion_tokens": 20,
                "total_tokens": 120
            }
        },
        "processing_time": 1.5
    }
    
    # Mock httpx response
    mock_response = httpx.Response(
        200, 
        json=api_response
    )
    
    # Patch httpx.AsyncClient.post
    with patch('httpx.AsyncClient.post', return_value=mock_response):
        result = await send_to_api(profile_data)
        
    # Verify result
    assert result["status"] == "success"
    assert result["data"]["generated_message"] == "Test message"


@pytest.mark.asyncio
async def test_send_to_api_failure():
    """Test API request failure."""
    # Sample profile data
    profile_data = {
        "image1": "data:image/jpeg;base64,test",
        "image2": "data:image/jpeg;base64,test",
        "user_bio": "Test user bio",
        "match_bio": {
            "name": "Test User",
            "age": 25,
            "bio": "Test bio",
            "interests": ["hiking", "photography"]
        },
        "sentence_count": 2,
        "tone": "friendly",
        "creativity": 0.7
    }
    
    # Mock httpx.TimeoutException
    with patch('httpx.AsyncClient.post', side_effect=httpx.TimeoutException("Timeout")):
        result = await send_to_api(profile_data)
        
    # Verify result contains error
    assert result["status"] == "error"
    assert "timeout" in result["error"].lower()


def test_format_api_response_success():
    """Test formatting successful API response."""
    # Sample API response
    api_response = {
        "status": "success",
        "data": {
            "generated_message": "Test message",
            "image_tags": ["test", "photo"],
            "token_usage": {
                "prompt_tokens": 100,
                "completion_tokens": 20,
                "total_tokens": 120
            }
        },
        "processing_time": 1.5
    }
    
    formatted = format_api_response(api_response)
    
    # Verify formatted contains the expected elements
    assert "Test message" in formatted
    assert "test, photo" in formatted
    assert "1.50 seconds" in formatted
    assert "100 prompt + 20 completion = 120 total" in formatted


def test_format_api_response_error():
    """Test formatting API error response."""
    # Sample error response
    error_response = {
        "status": "error",
        "error": "API connection failed"
    }
    
    formatted = format_api_response(error_response)
    
    # Verify formatted contains the error message
    assert "Error: API connection failed" in formatted