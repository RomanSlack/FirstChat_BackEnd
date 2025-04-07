"""
Browser interaction module for Tinder Profile Scraper.

This module provides utilities for browser automation using Playwright,
including connecting to existing Chrome instances, device emulation,
and profile data extraction.
"""

import os
import asyncio
import re
import time
import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

from playwright.async_api import async_playwright, Browser, Page, BrowserContext, Playwright
from loguru import logger

from config import config


async def initialize_browser(playwright: Playwright) -> Tuple[Browser, BrowserContext, Page]:
    """
    Initialize browser with Playwright for Tinder scraping.
    Either connects to an existing Chrome instance or launches a new one.
    
    Args:
        playwright: Playwright instance
    
    Returns:
        Tuple containing Browser, BrowserContext, and Page objects
    """
    try:
        if config.USE_REMOTE_CHROME:
            # Connect to an existing Chrome instance running with remote debugging
            # This expects Chrome to be started with:
            # google-chrome --remote-debugging-port=9222 --user-data-dir=/path/to/profile
            
            logger.info(f"Attempting to connect to existing Chrome instance on port {config.REMOTE_DEBUGGING_PORT}")
            
            try:
                # Connect to the browser
                browser = await playwright.chromium.connect_over_cdp(f"http://localhost:{config.REMOTE_DEBUGGING_PORT}")
                
                # Get all browser contexts
                contexts = browser.contexts
                if not contexts:
                    logger.warning("No contexts found in the connected browser. Creating a new one.")
                    context = await browser.new_context()
                else:
                    # Use the first context
                    context = contexts[0]
                    logger.info("Connected to existing browser context")
                
                # Get all pages or create a new one
                pages = context.pages
                if not pages:
                    logger.info("No pages found in the context. Creating a new one.")
                    page = await context.new_page()
                else:
                    # Use the first page
                    page = pages[0]
                    logger.info("Connected to existing page")
                
                logger.info("Successfully connected to Chrome with remote debugging")
                
                return browser, context, page
                
            except Exception as e:
                logger.error(f"Failed to connect to Chrome with remote debugging: {str(e)}")
                logger.info("Please run './launch_chrome.sh' first to start Chrome with remote debugging")
                logger.info("Falling back to launching a new browser instance")
                raise
        
        # If we're here, either USE_REMOTE_CHROME is False or connecting to remote Chrome failed
        
        logger.info("Launching a new browser instance")
        logger.info(f"Using Chrome profile: {config.CHROME_PROFILE_PATH}")
        
        # Launch a new browser instance with iPhone device emulation
        browser = await playwright.chromium.launch(
            headless=config.HEADLESS,
            executable_path=config.CHROME_EXECUTABLE_PATH,
        )
        
        # Create a new context with iPhone emulation
        iphone = playwright.devices['iPhone 12 Pro Max']
        context = await browser.new_context(**iphone)
        
        # Create a new page
        page = await context.new_page()
        
        logger.info("Successfully launched a new browser with mobile emulation")
        
        return browser, context, page
        
    except Exception as e:
        logger.error(f"Failed to initialize browser: {str(e)}")
        raise


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
        # Check if we're already on Tinder
        current_url = page.url
        if "tinder.com" in current_url:
            logger.info(f"Already on Tinder: {current_url}")
            # Wait for main content to load just in case
            await page.wait_for_load_state("networkidle")
        else:
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
        
        # Take a screenshot for debugging (optional)
        screenshot_path = os.path.join(config.OUTPUT_DIR, "tinder_screenshot.png")
        await page.screenshot(path=screenshot_path)
        logger.info(f"Saved screenshot to {screenshot_path}")
        
        logger.info("Successfully connected to Tinder")
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
        
        # Take a screenshot before interaction
        screenshot_path = os.path.join(config.OUTPUT_DIR, "before_interaction.png")
        await page.screenshot(path=screenshot_path)
        
        # Navigate to the third image using right taps
        # This navigates through images without swiping profiles
        
        # Tap right side of image to go to next image
        screen_width = await page.evaluate("window.innerWidth")
        screen_height = await page.evaluate("window.innerHeight")
        
        # Tap right side of image (80% of width, 30% of height) to navigate images
        # We tap twice to reach approximately the 3rd image
        x_position = int(screen_width * 0.8)
        y_position = int(screen_height * 0.3)
        
        logger.info(f"Navigating to 3rd image... (clicking at {x_position}, {y_position})")
        
        # First tap to 2nd image
        await page.mouse.click(x_position, y_position)
        await asyncio.sleep(config.WAIT_BETWEEN_ACTIONS / 1000)
        
        # Second tap to 3rd image
        await page.mouse.click(x_position, y_position)
        await asyncio.sleep(config.WAIT_BETWEEN_ACTIONS / 1000)
        
        # Take a screenshot after navigating to the 3rd image
        screenshot_path = os.path.join(config.OUTPUT_DIR, "after_image_navigation.png")
        await page.screenshot(path=screenshot_path)
        
        # Click "Show more" button
        try:
            logger.info("Looking for 'Show more' button...")
            
            # Try to find the show more button using the configured selector
            show_more_button = await page.query_selector(config.SHOW_MORE_SELECTOR)
            if show_more_button:
                await show_more_button.click()
                logger.info("Clicked 'Show more' button")
                await asyncio.sleep(config.WAIT_BETWEEN_ACTIONS / 1000)
            else:
                # Try alternative selector using text content
                logger.info("Trying alternative selector for 'Show more' button...")
                alt_buttons = await page.query_selector_all('div:has-text("Show more")')
                if alt_buttons:
                    for button in alt_buttons:
                        # Check if this looks like a button
                        class_name = await button.get_attribute('class')
                        if class_name and ('button' in class_name.lower() or 'btn' in class_name.lower() or 'Bd' in class_name):
                            await button.click()
                            logger.info("Clicked alternative 'Show more' button")
                            await asyncio.sleep(config.WAIT_BETWEEN_ACTIONS / 1000)
                            break
                else:
                    logger.warning("Could not find any 'Show more' button")
        except Exception as e:
            logger.warning(f"Could not find or click 'Show more' button: {str(e)}")
        
        # Take a screenshot after clicking show more
        screenshot_path = os.path.join(config.OUTPUT_DIR, "after_show_more.png")
        await page.screenshot(path=screenshot_path)
        
        # Click "View all 5" button if available
        try:
            logger.info("Looking for 'View all 5' button...")
            
            # Try the configured selector
            view_all_button = await page.query_selector(config.VIEW_ALL_SELECTOR)
            if view_all_button:
                await view_all_button.click()
                logger.info("Clicked 'View all 5' button")
                await asyncio.sleep(config.WAIT_BETWEEN_ACTIONS / 1000)
            else:
                # Try alternative selector
                logger.info("Trying alternative selector for 'View all 5' button...")
                alt_buttons = await page.query_selector_all('div:has-text("View all")')
                if alt_buttons:
                    for button in alt_buttons:
                        # Check if it has an SVG inside (arrow)
                        has_svg = await button.query_selector('svg')
                        if has_svg:
                            await button.click()
                            logger.info("Clicked alternative 'View all' button")
                            await asyncio.sleep(config.WAIT_BETWEEN_ACTIONS / 1000)
                            break
                else:
                    logger.warning("Could not find any 'View all' button")
        except Exception as e:
            logger.warning(f"Could not find or click 'View all 5' button: {str(e)}")
        
        # Allow everything to load
        await asyncio.sleep(1)
        
        # Take a final screenshot
        screenshot_path = os.path.join(config.OUTPUT_DIR, "after_interaction.png")
        await page.screenshot(path=screenshot_path)
        
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
        
        # Try alternative selector if the main one fails
        alt_selectors = [
            'h1', 
            'h1[class*="display"]',
            'div[class*="name"]',
            'div[class*="Name"]'
        ]
        
        for selector in alt_selectors:
            elements = await page.query_selector_all(selector)
            for element in elements:
                text = await element.text_content()
                if text:
                    # Look for a pattern like "Name, 25" or "Name 25"
                    match = re.search(r"([^\d,]+)(?:,?\s*)(\d+)", text)
                    if match:
                        name = match.group(1).strip()
                        age = int(match.group(2))
                        logger.info(f"Found name and age using alternative selector: {name}, {age}")
                        return name, age
        
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
        # First try to get background-image style from carousel items
        for i in range(9):  # Tinder shows up to 9 images
            carousel_selector = config.CAROUSEL_ITEM_SELECTOR.format(i)
            try:
                # First, look for the carousel item
                carousel_item = await page.query_selector(carousel_selector)
                if carousel_item:
                    logger.info(f"Found carousel item {i}")
                    
                    # Try to find the div with background-image style inside the carousel item
                    bg_div = await carousel_item.query_selector('div[class*="Bdrs(8px)"][class*="StretchedBox"]')
                    if bg_div:
                        # Get the style attribute
                        style = await bg_div.get_attribute('style')
                        if style and 'background-image' in style:
                            # Extract URL from background-image: url("URL")
                            url_match = re.search(r'background-image:\s*url\(["\']?(.*?)["\']?\)', style)
                            if url_match:
                                image_url = url_match.group(1)
                                # Remove the quotes that might be in the URL
                                image_url = image_url.replace('&quot;', '')
                                if image_url and not image_url.startswith('data:'):
                                    image_urls.append(image_url)
                                    logger.info(f"Extracted image URL from carousel item {i} background")
            except Exception as img_err:
                logger.warning(f"Error extracting image {i}: {str(img_err)}")
        
        # If we didn't get any images from background-image styles, try alternative methods
        if not image_urls:
            # Take a screenshot of the full page for analysis
            await page.screenshot(path=os.path.join(config.OUTPUT_DIR, "extract_images_debug.png"))
            logger.info("Saved debug screenshot for image extraction")
            
            # Try JavaScript to extract all background images
            try:
                bg_images = await page.evaluate("""
                () => {
                    const images = [];
                    // Get all elements with background-image
                    const elements = document.querySelectorAll('*');
                    elements.forEach(el => {
                        const style = window.getComputedStyle(el);
                        if (style.backgroundImage && style.backgroundImage !== 'none') {
                            let url = style.backgroundImage.slice(4, -1).replace(/["']/g, "");
                            if (url && !url.startsWith('data:') && url.includes('images-ssl.gotinder.com')) {
                                images.push(url);
                            }
                        }
                    });
                    return [...new Set(images)]; // Remove duplicates
                }
                """)
                
                if bg_images:
                    for url in bg_images:
                        if url not in image_urls:
                            image_urls.append(url)
                    logger.info(f"Extracted {len(image_urls)} background image URLs using JavaScript")
            except Exception as js_err:
                logger.warning(f"Error extracting images with JavaScript: {str(js_err)}")
            
            # Try to find any <img> tags as a fallback
            if not image_urls:
                selectors = [
                    '.keen-slider__slide img',
                    '.tappable-view img',
                    'div[class*="carousel"] img',
                    'img[src*="images-ssl"]',  # Tinder images often have this pattern
                    'img'  # Last resort - any image
                ]
                
                for selector in selectors:
                    img_elements = await page.query_selector_all(selector)
                    for img in img_elements:
                        src = await img.get_attribute('src')
                        if src and not src.startswith('data:') and src not in image_urls:
                            image_urls.append(src)
                    
                    if image_urls:
                        logger.info(f"Found {len(image_urls)} images using selector: {selector}")
                        break
        
        # Last resort: Try to extract from the raw HTML
        if not image_urls:
            html = await page.content()
            url_matches = re.findall(r'https://images-ssl\.gotinder\.com/[^"\')\s]+', html)
            for url in url_matches:
                # Clean up URL - sometimes there might be trailing characters
                url = url.split('\\')[0]  # Remove any backslash and everything after
                if url not in image_urls:
                    image_urls.append(url)
            logger.info(f"Extracted {len(image_urls)} image URLs from raw HTML")
            
        logger.info(f"Total extracted {len(image_urls)} image URLs")
        
        # Save the list of URLs to a file for debugging
        if image_urls:
            debug_file = os.path.join(config.OUTPUT_DIR, "image_urls.txt")
            with open(debug_file, 'w') as f:
                for url in image_urls:
                    f.write(f"{url}\n")
            logger.info(f"Saved image URLs to {debug_file}")
        
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
        
        # Try alternative selector if no interests found
        if not interests:
            alt_selectors = [
                'div[class*="Bdrs(30px)"] span',
                'div[class*="interest"] span',
                'div[class*="passions"] span',
                'div[class*="Interests"] span'
            ]
            
            for selector in alt_selectors:
                elements = await page.query_selector_all(selector)
                for element in elements:
                    text = await element.text_content()
                    if text and text.strip() not in interests:
                        interests.append(text.strip())
        
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
        if config.USE_REMOTE_CHROME:
            # Don't close the page if using remote Chrome - let the user keep control
            logger.info("Not closing browser since we're using remote debugging")
        else:
            # Save session if not using remote Chrome
            await save_session(context)
            await page.close()
            await context.close()
            await browser.close()
            logger.info("Browser resources closed")
    except Exception as e:
        logger.error(f"Error closing browser: {str(e)}")