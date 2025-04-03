"""
Test suite for the FirstChat REST API.
"""

import os
import json
import base64
from typing import Dict, Any

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from app import app

# Create test client
client = TestClient(app)

# Sample image data (tiny 1x1 pixel transparent PNG as base64)
SAMPLE_IMAGE = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="

# Mock test data
TEST_REQUEST = {
    "image1": SAMPLE_IMAGE,
    "image2": SAMPLE_IMAGE,
    "user_bio": "Test user bio",
    "match_bio": {
        "name": "Test Match",
        "age": 25,
        "bio": "Test match bio",
        "interests": ["testing", "coding"]
    },
    "sentence_count": 2,
    "tone": "friendly",
    "creativity": 0.7
}

# Expected mock response from message generator
MOCK_RESPONSE = {
    "generated_message": "This is a test message. Hope you like it!",
    "image_tags": ["test", "mock"],
    "token_usage": {
        "prompt_tokens": 100,
        "completion_tokens": 20,
        "total_tokens": 120
    },
    "settings": {
        "sentence_count": 2,
        "tone": "friendly",
        "creativity": 0.7
    }
}

@pytest.fixture(autouse=True)
def mock_env_vars():
    """Mock environment variables for tests."""
    with patch.dict(os.environ, {
        "OPENAI_API_KEY": "test-key",
        "GOOGLE_APPLICATION_CREDENTIALS": "test-credentials.json"
    }):
        yield


def test_health_endpoint():
    """Test the health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data
    assert "timestamp" in data


@patch("app.generate_message_async")
async def test_generate_message_success(mock_generate):
    """Test successful message generation."""
    # Set up mock
    mock_generate.return_value = MOCK_RESPONSE
    
    # Make request
    response = client.post("/generate_message", json=TEST_REQUEST)
    
    # Check response
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "processing_time" in data
    assert data["data"] == MOCK_RESPONSE
    
    # Verify mock was called with correct parameters
    mock_generate.assert_called_once_with(
        image1_data=TEST_REQUEST["image1"],
        image2_data=TEST_REQUEST["image2"],
        user_bio=TEST_REQUEST["user_bio"],
        match_bio=TEST_REQUEST["match_bio"],
        sentence_count=TEST_REQUEST["sentence_count"],
        tone=TEST_REQUEST["tone"],
        creativity=TEST_REQUEST["creativity"]
    )


def test_invalid_request():
    """Test validation for invalid requests."""
    # Missing required fields
    invalid_request = {
        "image1": SAMPLE_IMAGE,
        # image2 is missing
        "user_bio": "Test bio"
        # match_bio is missing
    }
    
    response = client.post("/generate_message", json=invalid_request)
    assert response.status_code == 422  # Validation error
    
    # Invalid tone
    invalid_tone_request = TEST_REQUEST.copy()
    invalid_tone_request["tone"] = "invalid_tone"
    
    response = client.post("/generate_message", json=invalid_tone_request)
    assert response.status_code == 422  # Validation error
    
    # Invalid sentence count
    invalid_count_request = TEST_REQUEST.copy()
    invalid_count_request["sentence_count"] = 10  # Out of range
    
    response = client.post("/generate_message", json=invalid_count_request)
    assert response.status_code == 422  # Validation error


@patch("app.generate_message_async")
async def test_generate_message_error(mock_generate):
    """Test error handling during message generation."""
    # Set up mock to raise an exception
    mock_generate.side_effect = Exception("Test error")
    
    # Make request
    response = client.post("/generate_message", json=TEST_REQUEST)
    
    # Check response
    assert response.status_code == 500
    data = response.json()
    assert "detail" in data
    assert "error" in data["detail"].lower()