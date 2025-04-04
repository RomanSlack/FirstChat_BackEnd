"""
Browser interaction module for FirstChat Profile Scraper.

This module provides utilities for browser automation using Playwright,
including session persistence and profile data extraction.
"""

import os
import asyncio
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

from playwright.async_api import async_playwright, Browser, Page, BrowserContext
from loguru import logger

from config import config


async def initialize_browser() -> Tuple[Browser, BrowserContext, Page]:
    """
    Initialize browser with Playwright.
    
    Returns:
        Tuple containing Browser, BrowserContext, and Page objects
    """
    playwright = await async_playwright().start()
    
    # Create session storage directory if it doesn't exist
    os.makedirs(config.SESSION_STORAGE_DIR, exist_ok=True)
    session_path = Path(config.SESSION_STORAGE_DIR) / "dating_app_session"
    
    # Launch browser with appropriate settings
    browser = await playwright.chromium.launch(headless=config.HEADLESS)
    
    # Create a persistent context if session storage exists
    if session_path.exists():
        logger.info("Loading existing browser session")
        context = await browser.new_context(
            user_agent=config.USER_AGENT,
            storage_state=str(session_path),
        )
    else:
        logger.info("Creating new browser session")
        context = await browser.new_context(
            user_agent=config.USER_AGENT,
        )
    
    # Configure timeouts
    context.set_default_navigation_timeout(config.NAVIGATION_TIMEOUT)
    context.set_default_timeout(config.ELEMENT_TIMEOUT)
    
    # Create a new page
    page = await context.new_page()
    
    return browser, context, page


async def save_session(context: BrowserContext) -> None:
    """
    Save the browser session for future use.
    
    Args:
        context: Playwright browser context
    """
    session_path = Path(config.SESSION_STORAGE_DIR) / "dating_app_session"
    await context.storage_state(path=str(session_path))
    logger.info(f"Session saved to {session_path}")


async def navigate_to_profile(page: Page) -> bool:
    """
    Navigate to the dating app profile page.
    
    Args:
        page: Playwright page object
        
    Returns:
        bool: True if navigation was successful, False otherwise
    """
    try:
        logger.info(f"Navigating to {config.TARGET_URL}")
        await page.goto(config.TARGET_URL, timeout=config.PAGE_LOAD_TIMEOUT)
        
        # Wait for main content to load - modify selector based on actual app
        await page.wait_for_selector("body", state="visible")
        
        # Check if we need to log in - this would be app-specific
        if await page.is_visible(".login-form"):
            logger.warning("Login required - please handle authentication")
            return False
            
        logger.info("Successfully navigated to profile page")
        return True
        
    except Exception as e:
        logger.error(f"Failed to navigate to profile: {str(e)}")
        return False


async def extract_profile_data(page: Page) -> Dict[str, Any]:
    """
    Extract profile data from the current page.
    
    Args:
        page: Playwright page object
        
    Returns:
        Dictionary containing profile information
    """
    profile_data = {}
    
    try:
        # Extract name and age
        name_age_element = await page.query_selector(config.PROFILE_NAME_SELECTOR)
        if name_age_element:
            name_age_text = await name_age_element.text_content()
            if name_age_text:
                # Parse name and age - pattern like "Name, 25"
                match = re.search(r"([^,]+),?\s*(\d+)", name_age_text)
                if match:
                    profile_data["name"] = match.group(1).strip()
                    profile_data["age"] = int(match.group(2))
                else:
                    profile_data["name"] = name_age_text.strip()
        
        # Extract bio
        bio_element = await page.query_selector(config.PROFILE_BIO_SELECTOR)
        if bio_element:
            bio_text = await bio_element.text_content()
            if bio_text:
                profile_data["bio"] = bio_text.strip()
        
        # Extract interests
        interests = []
        interest_elements = await page.query_selector_all(config.PROFILE_INTERESTS_SELECTOR)
        for element in interest_elements:
            interest_text = await element.text_content()
            if interest_text:
                interests.append(interest_text.strip())
        profile_data["interests"] = interests
        
        # Extract image URLs
        image_urls = []
        image_elements = await page.query_selector_all(config.PROFILE_IMAGES_SELECTOR)
        for element in image_elements:
            src = await element.get_attribute("src")
            if src and not src.startswith("data:"):  # Avoid placeholder images
                # Handle relative URLs
                if src.startswith("/"):
                    parsed_url = config.TARGET_URL.rstrip("/") + src
                else:
                    parsed_url = src
                image_urls.append(parsed_url)
        
        profile_data["image_urls"] = image_urls[:config.IMAGE_COUNT]
        
        logger.info(f"Extracted profile data: Name: {profile_data.get('name', 'N/A')}, "
                   f"Age: {profile_data.get('age', 'N/A')}, "
                   f"Images: {len(profile_data.get('image_urls', []))}")
        
        return profile_data
        
    except Exception as e:
        logger.error(f"Error extracting profile data: {str(e)}")
        return profile_data


async def close_browser(browser: Browser, context: BrowserContext, page: Page) -> None:
    """
    Properly close all browser resources.
    
    Args:
        browser: Playwright browser object
        context: Playwright browser context
        page: Playwright page object
    """
    try:
        await save_session(context)
        await page.close()
        await context.close()
        await browser.close()
        logger.info("Browser resources closed")
    except Exception as e:
        logger.error(f"Error closing browser: {str(e)}")