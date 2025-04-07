"""
Browser interaction module for Tinder Profile Scraper.

This module provides utilities for browser automation using Playwright,
including session persistence, device emulation, and profile data extraction.
"""

import os
import asyncio
import re
import time
import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import urllib.request

from playwright.async_api import async_playwright, Browser, Page, BrowserContext, Playwright
from loguru import logger

from config import config


async def initialize_browser(playwright: Playwright) -> Tuple[Browser, BrowserContext, Page]:
    """
    Initialize browser with Playwright for Tinder scraping.
    
    Args:
        playwright: Playwright instance
    
    Returns:
        Tuple containing Browser, BrowserContext, and Page objects
    """
    # Launch browser with appropriate settings
    if config.CHROME_PROFILE_PATH:
        # Use existing Chrome profile if path is provided
        logger.info(f"Using Chrome profile from: {config.CHROME_PROFILE_PATH}")
        
        # Find Chrome executable path
        chrome_executable = config.CHROME_EXECUTABLE_PATH
        if not chrome_executable or not os.path.exists(chrome_executable):
            # Default to standard locations if not specified
            chrome_executable = "/usr/bin/google-chrome"  # Default on Ubuntu
            if not os.path.exists(chrome_executable):
                # Try alternative locations
                alternatives = [
                    "/usr/bin/google-chrome-stable",
                    "/usr/bin/chromium-browser",
                    "/usr/bin/chromium",
                    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",  # macOS
                    "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",  # Windows
                    "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe"  # Windows (32-bit)
                ]
                for alt in alternatives:
                    if os.path.exists(alt):
                        chrome_executable = alt
                        break
        
        if not chrome_executable or not os.path.exists(chrome_executable):
            raise FileNotFoundError("Could not find Chrome executable. Please specify it with CHROME_EXECUTABLE_PATH.")
            
        logger.info(f"Using Chrome executable: {chrome_executable}")
        
        # Launch browser with persistent context using the specific Chrome executable
        browser = await playwright.chromium.launch_persistent_context(
            user_data_dir=config.CHROME_PROFILE_PATH,
            executable_path=chrome_executable,
            headless=config.HEADLESS,
            args=[
                f'--user-data-dir={config.CHROME_PROFILE_PATH}',
                '--no-first-run',
                '--no-default-browser-check',
                '--disable-extensions-except=',
                '--disable-infobars',
                '--user-agent=' + config.USER_AGENT,
                # Mobile emulation
                '--enable-features=UseOzonePlatform',
                '--ozone-platform=headless',
                # Add more flags as needed
            ],
            ignore_default_args=['--enable-automation'],  # Don't show the automation notice
            viewport={"width": 430, "height": 932},
            device_scale_factor=3,
        )
        context = browser
    else:
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
                viewport={"width": 430, "height": 932},
                device_scale_factor=3,
                is_mobile=True,
            )
        else:
            logger.info("Creating new browser session")
            # Create context with mobile emulation
            context = await browser.new_context(
                user_agent=config.USER_AGENT,
                viewport={"width": 430, "height": 932},
                device_scale_factor=3,
                is_mobile=True,
            )
    
    # Configure timeouts
    context.set_default_navigation_timeout(config.NAVIGATION_TIMEOUT)
    context.set_default_timeout(config.ELEMENT_TIMEOUT)
    
    # Create a new page
    page = await context.new_page()
    
    # Enable mobile emulation if using chrome profile
    if config.CHROME_PROFILE_PATH:
        await page.evaluate("""
        () => {
            // Attempt to trigger mobile view if not already active
            const meta = document.createElement('meta');
            meta.name = 'viewport';
            meta.content = 'width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no';
            document.getElementsByTagName('head')[0].appendChild(meta);
        }
        """)
    
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


async def navigate_to_tinder(page: Page) -> bool:
    """
    Navigate to Tinder recommendations page.
    
    Args:
        page: Playwright page object
        
    Returns:
        bool: True if navigation was successful, False otherwise
    """
    try:
        # Add a parameter to try to force mobile view
        target_url = config.TARGET_URL
        if "?" in target_url:
            target_url += "&go-mobile=1"
        else:
            target_url += "?go-mobile=1"
            
        logger.info(f"Navigating to {target_url}")
        await page.goto(target_url, timeout=config.PAGE_LOAD_TIMEOUT)
        
        # Wait for main content to load
        await page.wait_for_load_state("networkidle")
        
        # Check if we need to log in
        if await page.is_visible('text="Log in"'):
            logger.warning("Login required - please use a Chrome profile that's already logged in to Tinder")
            return False
            
        # Try to emulate an iPhone
        try:
            # Enable Chrome DevTools Protocol and use it to enable device emulation
            client = await page.context.new_cdp_session(page)
            
            # iPhone 14 Pro Max configuration
            await client.send('Emulation.setDeviceMetricsOverride', {
                'mobile': True,
                'width': 430,
                'height': 932,
                'deviceScaleFactor': 3,
                'screenOrientation': {'type': 'portraitPrimary', 'angle': 0}
            })
            
            # Set user agent to iPhone
            await client.send('Network.setUserAgentOverride', {
                'userAgent': config.USER_AGENT
            })
            
            logger.info("Enabled device emulation via CDP")
        except Exception as e:
            logger.warning(f"Could not use CDP for device emulation: {str(e)}")
            
            # Fallback to JavaScript approach
            await page.evaluate("""
            () => {
                // Force mobile view if not already
                if (typeof navigator.userAgent !== 'undefined') {
                    // Create and add mobile viewport meta tag
                    const meta = document.createElement('meta');
                    meta.name = 'viewport';
                    meta.content = 'width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no';
                    document.head.appendChild(meta);
                    
                    // Add mobile class if needed
                    document.documentElement.classList.add('mobile');
                    
                    // Try to modify navigator.userAgent (may not work in all browsers)
                    try {
                        Object.defineProperty(navigator, 'userAgent', {
                            get: function() { 
                                return 'Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1'; 
                            }
                        });
                    } catch (e) {
                        console.error('Failed to override userAgent', e);
                    }
                }
            }
            """)
        
        # Take a screenshot for debugging (optional)
        if not config.HEADLESS:
            screenshot_path = os.path.join(config.OUTPUT_DIR, "tinder_screenshot.png")
            await page.screenshot(path=screenshot_path)
            logger.info(f"Saved screenshot to {screenshot_path}")
        
        logger.info("Successfully navigated to Tinder")
        return True
        
    except Exception as e:
        logger.error(f"Failed to navigate to Tinder: {str(e)}")
        return False


async def interact_with_profile(page: Page) -> bool:
    """
    Interact with a Tinder profile using the required sequence.
    
    Args:
        page: Playwright page object
        
    Returns:
        bool: True if interaction was successful, False otherwise
    """
    try:
        # Wait for profile to load
        await asyncio.sleep(1)
        
        # Navigate to the third image using right taps
        # This navigates through images without swiping profiles
        
        # Tap right side of image to go to next image
        screen_width = 430  # From our mobile emulation
        screen_height = 932  # From our mobile emulation
        
        # Tap right side of image (80% of width, 30% of height) to navigate images
        # We tap twice to reach approximately the 3rd image
        x_position = int(screen_width * 0.8)
        y_position = int(screen_height * 0.3)
        
        logger.info("Navigating to 3rd image...")
        
        # First tap to 2nd image
        await page.mouse.click(x_position, y_position)
        await asyncio.sleep(config.WAIT_BETWEEN_ACTIONS / 1000)
        
        # Second tap to 3rd image
        await page.mouse.click(x_position, y_position)
        await asyncio.sleep(config.WAIT_BETWEEN_ACTIONS / 1000)
        
        # Click "Show more" button
        try:
            logger.info("Looking for 'Show more' button...")
            show_more_button = await page.wait_for_selector(config.SHOW_MORE_SELECTOR, timeout=5000)
            if show_more_button:
                await show_more_button.click()
                logger.info("Clicked 'Show more' button")
                await asyncio.sleep(config.WAIT_BETWEEN_ACTIONS / 1000)
        except Exception as e:
            logger.warning(f"Could not find or click 'Show more' button: {str(e)}")
        
        # Click "View all 5" button if available
        try:
            logger.info("Looking for 'View all 5' button...")
            view_all_button = await page.wait_for_selector(config.VIEW_ALL_SELECTOR, timeout=5000)
            if view_all_button:
                await view_all_button.click()
                logger.info("Clicked 'View all 5' button")
                await asyncio.sleep(config.WAIT_BETWEEN_ACTIONS / 1000)
        except Exception as e:
            logger.warning(f"Could not find or click 'View all 5' button: {str(e)}")
        
        # Allow everything to load
        await asyncio.sleep(1)
        
        return True
        
    except Exception as e:
        logger.error(f"Error during profile interaction: {str(e)}")
        return False


async def extract_name_and_age(page: Page) -> Tuple[Optional[str], Optional[int]]:
    """
    Extract name and age from Tinder profile.
    
    Args:
        page: Playwright page object
        
    Returns:
        Tuple containing name (str) and age (int)
    """
    try:
        name_age_element = await page.query_selector(config.PROFILE_NAME_AGE_SELECTOR)
        if name_age_element:
            name_age_text = await name_age_element.text_content()
            if name_age_text:
                # Parse name and age based on Tinder's format
                # Expected format is something like "Jane 19"
                match = re.search(r"([^\d]+)\s*(\d+)", name_age_text)
                if match:
                    name = match.group(1).strip()
                    age = int(match.group(2))
                    return name, age
                else:
                    # If regex doesn't match, just return the text as name
                    return name_age_text.strip(), None
        
        return None, None
    
    except Exception as e:
        logger.error(f"Error extracting name and age: {str(e)}")
        return None, None


async def extract_images(page: Page) -> List[str]:
    """
    Extract image URLs from Tinder carousel.
    
    Args:
        page: Playwright page object
        
    Returns:
        List of image URLs
    """
    image_urls = []
    
    try:
        # Try to extract images from carousel items (0-4)
        for i in range(5):  # Tinder typically shows up to 5 images
            carousel_selector = config.CAROUSEL_ITEM_SELECTOR.format(i)
            try:
                carousel_item = await page.query_selector(carousel_selector)
                if carousel_item:
                    # Try to find image within the carousel item
                    img_element = await carousel_item.query_selector('img')
                    if img_element:
                        src = await img_element.get_attribute('src')
                        if src and not src.startswith('data:'):  # Avoid data URIs
                            image_urls.append(src)
            except Exception as img_err:
                logger.warning(f"Error extracting image {i}: {str(img_err)}")
        
        # If we didn't find any images, try with a more general selector
        if not image_urls:
            img_elements = await page.query_selector_all('.keen-slider__slide img')
            for img in img_elements:
                src = await img.get_attribute('src')
                if src and not src.startswith('data:'):
                    image_urls.append(src)
        
        logger.info(f"Extracted {len(image_urls)} image URLs")
        return image_urls
        
    except Exception as e:
        logger.error(f"Error extracting images: {str(e)}")
        return image_urls


async def extract_interests(page: Page) -> List[str]:
    """
    Extract interests from Tinder profile.
    
    Args:
        page: Playwright page object
        
    Returns:
        List of interests
    """
    interests = []
    
    try:
        interest_elements = await page.query_selector_all(config.INTERESTS_SELECTOR)
        for element in interest_elements:
            interest_text = await element.text_content()
            if interest_text:
                interests.append(interest_text.strip())
        
        logger.info(f"Extracted {len(interests)} interests")
        return interests
        
    except Exception as e:
        logger.error(f"Error extracting interests: {str(e)}")
        return interests


async def extract_profile_sections(page: Page) -> Dict[str, Any]:
    """
    Extract all profile sections from Tinder "Show more" area.
    
    Args:
        page: Playwright page object
        
    Returns:
        Dictionary containing profile section information
    """
    sections_data = {}
    
    try:
        # Get all section containers
        section_elements = await page.query_selector_all(config.PROFILE_SECTION_SELECTOR)
        
        for section in section_elements:
            # Get section title if available
            title_elem = await section.query_selector('div[class*="Mstart(8px)"][class*="C($c-ds-text-secondary)"]')
            section_title = "Unknown"
            if title_elem:
                title_text = await title_elem.text_content()
                if title_text:
                    section_title = title_text.strip()
            
            # Get all content divs in this section
            content_items = {}
            
            # Look for subtitle and content pairs
            subtitle_elems = await section.query_selector_all('h3[class*="C($c-ds-text-secondary)"]')
            for subtitle_elem in subtitle_elems:
                subtitle = await subtitle_elem.text_content()
                if subtitle:
                    subtitle = subtitle.strip()
                    
                    # Find the next div with content
                    content_elem = await subtitle_elem.evaluate_handle('el => el.nextElementSibling')
                    if content_elem:
                        content_text = await content_elem.text_content()
                        if content_text:
                            content_items[subtitle] = content_text.strip()
            
            # If we have content items, add them to the section
            if content_items:
                sections_data[section_title] = content_items
                
            # Special case for interests section which has a different structure
            if section_title == "Interests" and not content_items:
                interests = await extract_interests(page)
                if interests:
                    sections_data["Interests"] = interests
        
        logger.info(f"Extracted {len(sections_data)} profile sections")
        return sections_data
        
    except Exception as e:
        logger.error(f"Error extracting profile sections: {str(e)}")
        return sections_data


async def extract_profile_data(page: Page) -> Dict[str, Any]:
    """
    Extract all profile data from Tinder.
    
    Args:
        page: Playwright page object
        
    Returns:
        Dictionary containing profile information
    """
    profile_data = {}
    
    try:
        # Extract name and age
        name, age = await extract_name_and_age(page)
        profile_data["name"] = name
        if age:
            profile_data["age"] = age
        
        # Extract images
        image_urls = await extract_images(page)
        profile_data["image_urls"] = image_urls
        
        # Extract profile sections (including interests)
        section_data = await extract_profile_sections(page)
        profile_data["profile_sections"] = section_data
        
        # Extract interests from dedicated section if available
        if "Interests" in section_data and isinstance(section_data["Interests"], list):
            profile_data["interests"] = section_data["Interests"]
        else:
            interests = await extract_interests(page)
            if interests:
                profile_data["interests"] = interests
        
        # Save raw HTML for debugging if enabled
        if config.SAVE_HTML:
            profile_data["html"] = await page.content()
        
        logger.info(f"Extracted profile data for {name or 'Unknown'}")
        return profile_data
        
    except Exception as e:
        logger.error(f"Error extracting complete profile data: {str(e)}")
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
        if not config.CHROME_PROFILE_PATH:  # Only save session if not using Chrome profile
            await save_session(context)
        await page.close()
        await context.close()
        if not config.CHROME_PROFILE_PATH:  # Only close browser if not using Chrome profile
            await browser.close()
        logger.info("Browser resources closed")
    except Exception as e:
        logger.error(f"Error closing browser: {str(e)}")