"""
Configuration module for Tinder Profile Scraper.

This module handles the loading and validation of configuration parameters
from environment variables with smart defaults.
"""

import os
from pydantic import field_validator
from pydantic_settings import BaseSettings
from typing import Optional
from dotenv import load_dotenv
import pathlib

# Load environment variables from .env file
load_dotenv()

class TinderConfig(BaseSettings):
    """Configuration settings for the Tinder profile scraper."""
    
    # Tinder URL
    TARGET_URL: str = os.getenv("TARGET_URL", "https://tinder.com/app/recs")
    
    # Output directory for scraped profiles
    OUTPUT_DIR: str = os.getenv("OUTPUT_DIR", "./scraped_profiles")
    
    # Browser settings
    HEADLESS: bool = os.getenv("HEADLESS", "False").lower() == "true"
    USER_AGENT: str = os.getenv("USER_AGENT", "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1")
    DEVICE_NAME: str = os.getenv("DEVICE_NAME", "iPhone 14 Pro Max")
    CHROME_PROFILE_PATH: Optional[str] = os.getenv("CHROME_PROFILE_PATH", "/home/roman-slack/.config/google-chrome/Profile 4") # Default to Profile 4
    CHROME_EXECUTABLE_PATH: Optional[str] = os.getenv("CHROME_EXECUTABLE_PATH", "/usr/bin/google-chrome") 
    
    # Chrome Remote Debugging
    USE_REMOTE_CHROME: bool = os.getenv("USE_REMOTE_CHROME", "True").lower() == "true"
    REMOTE_DEBUGGING_PORT: int = int(os.getenv("REMOTE_DEBUGGING_PORT", "9222"))
    
    # Timeout values (in milliseconds)
    PAGE_LOAD_TIMEOUT: int = int(os.getenv("PAGE_LOAD_TIMEOUT", "30000"))
    NAVIGATION_TIMEOUT: int = int(os.getenv("NAVIGATION_TIMEOUT", "30000"))
    ELEMENT_TIMEOUT: int = int(os.getenv("ELEMENT_TIMEOUT", "10000"))
    
    # Session persistence
    SESSION_STORAGE_DIR: str = os.getenv("SESSION_STORAGE_DIR", "./browser_sessions")
    
    # Tinder specific selectors
    CAROUSEL_ITEM_SELECTOR: str = 'id=carousel-item-{}'
    PROFILE_NAME_AGE_SELECTOR: str = 'h1[class*="Typs(display-2-strong)"]'
    SHOW_MORE_SELECTOR: str = 'div[class*="Bdrs(30px)"] span:text("Show more")'
    VIEW_ALL_SELECTOR: str = 'div[class*="Px(16px)"]:text("View all 5")'
    INTERESTS_SELECTOR: str = 'div[class*="Gp(8px)"] div[class*="Bdrs(30px)"] span'
    PROFILE_SECTION_SELECTOR: str = 'div[class*="Mt(8px)"] div[class*="P(24px)"]'
    
    # Wait times (in milliseconds)
    WAIT_BETWEEN_ACTIONS: int = int(os.getenv("WAIT_BETWEEN_ACTIONS", "500"))
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: Optional[str] = os.getenv("LOG_FILE", "scraper.log")
    
    # Save raw HTML with profiles
    SAVE_HTML: bool = os.getenv("SAVE_HTML", "True").lower() == "true"
    
    @field_validator("OUTPUT_DIR")
    def create_output_dir(cls, v):
        """Create output directory if it doesn't exist."""
        path = pathlib.Path(v)
        path.mkdir(parents=True, exist_ok=True)
        return v
    
    @field_validator("SESSION_STORAGE_DIR")
    def create_session_dir(cls, v):
        """Create session storage directory if it doesn't exist."""
        path = pathlib.Path(v)
        path.mkdir(parents=True, exist_ok=True)
        return v
    
    class Config:
        """Pydantic config."""
        env_file = ".env"
        case_sensitive = True

# Create a global config instance
config = TinderConfig()