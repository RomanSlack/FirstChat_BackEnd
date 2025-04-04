"""
Tests for the data processor module.
"""

import pytest
import asyncio
import base64
from unittest.mock import patch, MagicMock
import httpx
import io
from PIL import Image

from data_processor import (
    download_image,
    image_to_base64,
    get_placeholder_image,
    process_profile_data
)


@pytest.mark.asyncio
async def test_download_image_success():
    """Test successful image download."""
    # Create a simple test image
    img = Image.new('RGB', (100, 100), color='red')
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='JPEG')
    img_bytes = img_bytes.getvalue()
    
    # Mock httpx response
    mock_response = httpx.Response(200, content=img_bytes)
    
    # Patch httpx.AsyncClient.get
    with patch('httpx.AsyncClient.get', return_value=mock_response):
        result = await download_image('http://example.com/image.jpg')
        
    # Verify result
    assert result == img_bytes


@pytest.mark.asyncio
async def test_download_image_failure():
    """Test image download failure."""
    # Patch httpx.AsyncClient.get to raise an exception
    with patch('httpx.AsyncClient.get', side_effect=httpx.RequestError('Connection error')):
        result = await download_image('http://example.com/image.jpg')
        
    # Verify result is None for failure
    assert result is None


@pytest.mark.asyncio
async def test_image_to_base64():
    """Test image to base64 conversion."""
    # Create a simple test image
    img = Image.new('RGB', (100, 100), color='red')
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='JPEG')
    img_bytes = img_bytes.getvalue()
    
    # Convert to base64
    result = await image_to_base64(img_bytes)
    
    # Verify result starts with data URL prefix
    assert result.startswith('data:image/jpeg;base64,')
    
    # Verify the decoded image matches
    encoded_part = result.split(',')[1]
    decoded = base64.b64decode(encoded_part)
    assert len(decoded) > 0


def test_get_placeholder_image():
    """Test placeholder image generation."""
    placeholder = get_placeholder_image()
    
    # Verify it's a valid data URL
    assert placeholder.startswith('data:image/png;base64,')


@pytest.mark.asyncio
async def test_process_profile_data():
    """Test profile data processing."""
    # Sample profile data
    profile_data = {
        "name": "Test User",
        "age": 25,
        "bio": "This is a test bio",
        "interests": ["hiking", "photography"],
        "image_urls": ["http://example.com/image1.jpg", "http://example.com/image2.jpg"]
    }
    
    # Create a simple test image
    img = Image.new('RGB', (100, 100), color='red')
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='JPEG')
    img_bytes = img_bytes.getvalue()
    
    # Mock image download
    with patch('data_processor.download_image', return_value=img_bytes):
        # Mock base64 conversion to return a simple string for testing
        with patch('data_processor.image_to_base64', return_value="data:image/jpeg;base64,test"):
            result = await process_profile_data(profile_data)
    
    # Verify the processed data
    assert result["match_bio"]["name"] == "Test User"
    assert result["match_bio"]["age"] == 25
    assert result["match_bio"]["bio"] == "This is a test bio"
    assert "hiking" in result["match_bio"]["interests"]
    assert result["image1"] == "data:image/jpeg;base64,test"
    assert result["image2"] == "data:image/jpeg;base64,test"
    assert "user_bio" in result
    assert "sentence_count" in result
    assert "tone" in result
    assert "creativity" in result