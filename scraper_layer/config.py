"""
Configuration module for FirstChat Profile Scraper.

This module handles the loading and validation of configuration parameters
from environment variables with smart defaults.
"""

import os
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings
from typing import Optional, List
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class ScraperConfig(BaseSettings):
    """Configuration settings for the profile scraper."""
    
    # Target dating app URL
    TARGET_URL: str = os.getenv("TARGET_URL", "http://localhost:3000")
    
    # API endpoint for message generation
    API_ENDPOINT: str = os.getenv("API_ENDPOINT", "http://localhost:8002/generate_message")
    
    # User profile information (the person running the script)
    USER_BIO: str = os.getenv("USER_BIO", "I'm a 28-year-old software engineer who loves hiking, photography, and trying new restaurants. I travel whenever I can and am looking for someone with similar interests.")
    
    # Number of images to process
    IMAGE_COUNT: int = int(os.getenv("IMAGE_COUNT", "2"))
    
    # Browser settings
    HEADLESS: bool = os.getenv("HEADLESS", "True").lower() == "true"
    USER_AGENT: str = os.getenv("USER_AGENT", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    
    # Timeout values (in milliseconds)
    PAGE_LOAD_TIMEOUT: int = int(os.getenv("PAGE_LOAD_TIMEOUT", "30000"))
    NAVIGATION_TIMEOUT: int = int(os.getenv("NAVIGATION_TIMEOUT", "30000"))
    ELEMENT_TIMEOUT: int = int(os.getenv("ELEMENT_TIMEOUT", "10000"))
    
    # Session persistence
    SESSION_STORAGE_DIR: str = os.getenv("SESSION_STORAGE_DIR", "./browser_sessions")
    
    # Profile selectors (these would be specific to the dating app being scraped)
    PROFILE_NAME_SELECTOR: str = os.getenv("PROFILE_NAME_SELECTOR", ".profile-name")
    PROFILE_AGE_SELECTOR: str = os.getenv("PROFILE_AGE_SELECTOR", ".profile-age")
    PROFILE_BIO_SELECTOR: str = os.getenv("PROFILE_BIO_SELECTOR", ".profile-bio")
    PROFILE_INTERESTS_SELECTOR: str = os.getenv("PROFILE_INTERESTS_SELECTOR", ".profile-interests .interest")
    PROFILE_IMAGES_SELECTOR: str = os.getenv("PROFILE_IMAGES_SELECTOR", ".profile-images img")
    
    # API request settings
    MESSAGE_SENTENCE_COUNT: int = int(os.getenv("MESSAGE_SENTENCE_COUNT", "2"))
    MESSAGE_TONE: str = os.getenv("MESSAGE_TONE", "friendly")
    MESSAGE_CREATIVITY: float = float(os.getenv("MESSAGE_CREATIVITY", "0.7"))
    
    # Network settings
    MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "3"))
    RETRY_DELAY: int = int(os.getenv("RETRY_DELAY", "1000"))  # in milliseconds
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: Optional[str] = os.getenv("LOG_FILE", "scraper.log")
    
    @field_validator("MESSAGE_TONE")
    def validate_tone(cls, v):
        """Validate that the message tone is from the allowed list."""
        allowed_tones = ["friendly", "witty", "flirty", "casual", "confident"]
        if v.lower() not in allowed_tones:
            raise ValueError(f"Message tone must be one of: {', '.join(allowed_tones)}")
        return v.lower()
    
    @field_validator("MESSAGE_CREATIVITY")
    def validate_creativity(cls, v):
        """Validate that creativity is within the allowed range."""
        if not 0.0 <= v <= 1.0:
            raise ValueError("Creativity must be between 0.0 and 1.0")
        return v
    
    @field_validator("IMAGE_COUNT")
    def validate_image_count(cls, v):
        """Validate that image count is reasonable."""
        if v < 1:
            raise ValueError("Must process at least 1 image")
        if v > 10:
            raise ValueError("Cannot process more than 10 images")
        return v
    
    class Config:
        """Pydantic config."""
        env_file = ".env"
        case_sensitive = True

# Create a global config instance
config = ScraperConfig()