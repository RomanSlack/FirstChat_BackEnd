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
import sys
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
            logger.info(f"Attempting to connect to existing Chrome instance on port {config.REMOTE_DEBUGGING_PORT}")
            try:
                browser = await playwright.chromium.connect_over_cdp(f"http://localhost:{config.REMOTE_DEBUGGING_PORT}")
                contexts = browser.contexts
                if not contexts:
                    logger.warning("No contexts found in the connected browser. Creating a new one.")
                    context = await browser.new_context()
                else:
                    context = contexts[0]
                    logger.info("Connected to existing browser context")
                pages = context.pages
                if not pages:
                    logger.info("No pages found in the context. Creating a new one.")
                    page = await context.new_page()
                else:
                    page = pages[0]
                    logger.info("Connected to existing page")
                logger.info("Successfully connected to Chrome with remote debugging")
                return browser, context, page
            except Exception as e:
                logger.error(f"Failed to connect to Chrome with remote debugging: {str(e)}")
                logger.info("Please run './launch_chrome.sh' first to start Chrome with remote debugging")
                logger.info("Falling back to launching a new browser instance")
                raise
        logger.info("Launching a new browser instance")
        logger.info(f"Using Chrome profile: {config.CHROME_PROFILE_PATH}")
        browser = await playwright.chromium.launch(
            headless=config.HEADLESS,
            executable_path=config.CHROME_EXECUTABLE_PATH,
        )
        iphone = playwright.devices['iPhone 12 Pro Max']
        context = await browser.new_context(**iphone)
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
    Immediately checks for Profile Photo 1 and exits if not found.

    Args:
        page: Playwright page object

    Returns:
        bool: True if navigation and Profile Photo 1 check were successful, False otherwise
    """
    try:
        current_url = page.url
        if "tinder.com" in current_url:
            logger.info(f"Already on Tinder: {current_url}")
            await page.wait_for_load_state("networkidle")
        else:
            target_url = config.TARGET_URL
            if "?" in target_url:
                target_url += "&go-mobile=1"
            else:
                target_url += "?go-mobile=1"
            logger.info(f"Navigating to {target_url}")
            await page.goto(target_url, timeout=config.PAGE_LOAD_TIMEOUT)
            await page.wait_for_load_state("networkidle")
        if await page.is_visible('text="Log in"'):
            logger.warning("Login required - please use a Chrome profile that's already logged in to Tinder")
            return False
        logger.info("Successfully connected to Tinder")
        return True
    except Exception as e:
        logger.error(f"Failed to navigate to Tinder: {str(e)}")
        return False


async def interact_with_profile(page: Page) -> bool:
    """
    Interact with a Tinder profile to expand details.
    Image navigation is handled separately in extract_images.

    This updated version attempts to locate the "Show more" button.
    If not found on the current (target) slide, it iterates over all slides
    (by tapping left/right based on stored indices) until the button is found.
    If it still isn’t found, it logs a warning and continues.

    Args:
        page: Playwright page object

    Returns:
        bool: True if interaction (or fallback) was successful, False otherwise.
    """
    try:
        await asyncio.sleep(1)
        if not hasattr(page, "profile_data"):
            page.profile_data = {}

        # First, try the standard selector on the current slide.
        logger.info("Looking for 'Show more' button on current slide...")
        show_more_button = await page.query_selector(config.SHOW_MORE_SELECTOR)
        if show_more_button:
            await show_more_button.click()
            logger.info("Clicked 'Show more' button on current slide.")
            await asyncio.sleep(config.WAIT_BETWEEN_ACTIONS / 1000)
            return True

        # If not found, attempt to search other slides.
        logger.info("No 'Show more' button on current slide. Searching other slides...")

        # Get tap positions.
        const_screen_width = await page.evaluate("window.innerWidth")
        const_screen_height = await page.evaluate("window.innerHeight")
        right_tap_x = int(const_screen_width * 0.8)  # tap on right 80% of screen width
        left_tap_x = int(const_screen_width * 0.2)  # tap on left 20% of screen width
        tap_y = int(const_screen_height * 0.5)  # vertically centered

        # Retrieve total slides and target slide from profile_data, or compute them.
        total_slides = page.profile_data.get("total_slides")
        target_slide = page.profile_data.get("target_slide", 2)  # default to slide index 2 (3rd slide)
        if total_slides is None:
            total_slides = await page.evaluate('''() => {
                const container = document.querySelector('div[data-keyboard-gamepad="true"][aria-hidden="false"]');
                return container ? container.querySelectorAll('.keen-slider__slide').length : 0;
            }''')
            page.profile_data["total_slides"] = total_slides

        # Get current slide index (assumes the visible slide has aria-hidden="false")
        current_index = await page.evaluate('''() => {
            const container = document.querySelector('div[data-keyboard-gamepad="true"][aria-hidden="false"]');
            if (!container) return -1;
            const slides = container.querySelectorAll('.keen-slider__slide');
            for (let i = 0; i < slides.length; i++) {
                if (slides[i].getAttribute("aria-hidden") === "false") {
                    return i;
                }
            }
            return -1;
        }''')
        if current_index == -1:
            current_index = target_slide  # fallback

        original_index = current_index
        # Order indices by closeness to the target slide.
        indices = list(range(total_slides))
        indices.sort(key=lambda i: abs(i - target_slide))

        found = False
        for idx in indices:
            if idx == current_index:
                # Check current slide.
                button = await page.query_selector(config.SHOW_MORE_SELECTOR)
                if button:
                    await button.click()
                    logger.info(f"Found 'Show more' button on slide {idx}.")
                    found = True
                    break
                continue
            # Determine number of taps required.
            diff = idx - current_index
            if diff > 0:
                for _ in range(diff):
                    await page.mouse.click(right_tap_x, tap_y)
                    await asyncio.sleep(1.0)
            elif diff < 0:
                for _ in range(-diff):
                    await page.mouse.click(left_tap_x, tap_y)
                    await asyncio.sleep(1.0)
            current_index = idx
            button = await page.query_selector(config.SHOW_MORE_SELECTOR)
            if button:
                await button.click()
                logger.info(f"Found 'Show more' button on slide {idx}.")
                found = True
                break

        # Return to original slide.
        diff = original_index - current_index
        if diff > 0:
            for _ in range(diff):
                await page.mouse.click(right_tap_x, tap_y)
                await asyncio.sleep(1.0)
        elif diff < 0:
            for _ in range(-diff):
                await page.mouse.click(left_tap_x, tap_y)
                await asyncio.sleep(1.0)

        if not found:
            logger.warning("Could not find 'Show more' button on any slide; proceeding with unknown details.")
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
                match = re.search(r"([^\d]+)\s*(\d+)", name_age_text)
                if match:
                    name = match.group(1).strip()
                    age = int(match.group(2))
                    return name, age
                else:
                    return name_age_text.strip(), None
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
    Extract image URLs from Tinder carousel using DOM navigation and simulated taps.

    Steps:
      1. Locate the carousel container and read the total number of images from the first slide's aria-label.
      2. Extract the first image URL from slide index 0.
      3. For each subsequent image, simulate a tap on the right side of the screen to load the next image,
         wait for the slide transition, then extract its URL by slide index.
      4. After collecting all image URLs, simulate left taps to return to the 3rd image (or remain if fewer than 3).

    Returns:
      List of image URLs.
    """
    try:
        logger.info("Starting enhanced image extraction using simulated taps...")

        if not hasattr(page, "profile_data"):
            page.profile_data = {}

        labeled_urls = {}
        clean_urls = []

        # Step 1: Find the carousel container and total image count.
        carousel_info = await page.evaluate('''() => {
            // Select the carousel container with data-keyboard-gamepad="true" and aria-hidden="false"
            const container = document.querySelector('div[data-keyboard-gamepad="true"][aria-hidden="false"]');
            if (container) {
                // Extract the first slide to get the total image count from its aria-label
                const firstSlide = container.querySelector('.keen-slider__slide');
                if (firstSlide) {
                    const ariaLabel = firstSlide.getAttribute('aria-label') || "";
                    const match = ariaLabel.match(/(\\d+)\\s*of\\s*(\\d+)/i);
                    let totalImages = 0;
                    if (match && match.length >= 3) {
                        totalImages = parseInt(match[2]);
                    }
                    return { found: true, totalImages: totalImages };
                }
            }
            return { found: false };
        }''')

        if not carousel_info or not carousel_info.get("found"):
            logger.error("Failed to locate image carousel container")
            return []

        total_images = carousel_info.get("totalImages", 0)
        logger.info(f"Found image carousel with total images: {total_images}")
        if total_images < 1:
            logger.error("No images found in carousel")
            return []

        # Helper function: get the image URL from a slide by index.
        async def get_image_by_index(index):
            return await page.evaluate('(index) => { '
                'const container = document.querySelector(\'div[data-keyboard-gamepad="true"][aria-hidden="false"]\');'
                'if (!container) return null;'
                'const slides = container.querySelectorAll(\'.keen-slider__slide\');'
                'if (index < slides.length) {'
                '  const slide = slides[index];'
                '  let imgDiv = slide.querySelector(\'div[style*="background-image"]\') || '
                '               slide.querySelector(\'div[role="img"]\') || '
                '               slide.querySelector(\'div[aria-label*="Profile Photo"]\');'
                '  if (!imgDiv) return null;'
                '  const style = imgDiv.getAttribute("style") || "";'
                '  const urlMatch = style.match(/url\\(["\\\']?(.*?)["\\\']?\\)/);'
                '  return urlMatch ? urlMatch[1] : null;'
                '}'
                'return null;'
                '}', index)

        # Step 2: Extract the first image (slide index 0).
        first_url = await get_image_by_index(0)
        if not first_url:
            logger.error("Failed to extract the first image URL")
            return []
        first_url = first_url.replace('&amp;', '&')
        labeled_urls["Profile Photo 1"] = first_url
        clean_urls.append(first_url)
        logger.info(f"Extracted Profile Photo 1: {first_url[:60]}...")

        # Calculate tap positions.
        screen_width = await page.evaluate("window.innerWidth")
        screen_height = await page.evaluate("window.innerHeight")
        right_tap_x = int(screen_width * 0.8)   # tap on right 80% of screen width
        left_tap_x = int(screen_width * 0.2)    # tap on left 20% of screen width
        tap_y = int(screen_height * 0.5)        # vertically centered

        # Step 3: For each subsequent image, tap right and extract its URL by slide index.
        for i in range(1, total_images):
            logger.info(f"Tapping to load image {i+1} of {total_images}...")
            await page.mouse.click(right_tap_x, tap_y)
            await asyncio.sleep(1.0)  # increased delay to ensure slide transition
            img_url = await get_image_by_index(i)
            if not img_url:
                logger.warning(f"Could not extract image URL for image {i+1}")
                continue
            img_url = img_url.replace('&amp;', '&')
            label = f"Profile Photo {i+1}"
            labeled_urls[label] = img_url
            if img_url not in clean_urls:
                clean_urls.append(img_url)
            logger.info(f"Extracted {label}: {img_url[:60]}...")

        # Step 4: Navigate back to the third image (if there are at least 3).
        target_image = 3 if total_images >= 3 else total_images
        current_image = total_images  # assume the last loaded slide is current
        left_taps_needed = current_image - target_image
        logger.info(f"Navigating back to image {target_image} by tapping left {left_taps_needed} times...")
        for _ in range(left_taps_needed):
            await page.mouse.click(left_tap_x, tap_y)
            await asyncio.sleep(1.0)

        logger.info(f"Completed image extraction. Found {len(clean_urls)} images.")
        page.profile_data["image_urls"] = clean_urls
        page.profile_data["labeled_image_urls"] = labeled_urls
        return clean_urls

    except Exception as e:
        logger.error(f"Error extracting images: {str(e)}")
        return []



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
        section_elements = await page.query_selector_all(config.PROFILE_SECTION_SELECTOR)
        for section in section_elements:
            title_elem = await section.query_selector('div[class*="Mstart(8px)"][class*="C($c-ds-text-secondary)"]')
            section_title = "Unknown"
            if title_elem:
                title_text = await title_elem.text_content()
                if title_text:
                    section_title = title_text.strip()
            content_items = {}
            subtitle_elems = await section.query_selector_all('h3[class*="C($c-ds-text-secondary)"]')
            for subtitle_elem in subtitle_elems:
                subtitle = await subtitle_elem.text_content()
                if subtitle:
                    subtitle = subtitle.strip()
                    content_elem = await subtitle_elem.evaluate_handle('el => el.nextElementSibling')
                    if content_elem:
                        content_text = await content_elem.text_content()
                        if content_text:
                            content_items[subtitle] = content_text.strip()
            if content_items:
                sections_data[section_title] = content_items
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
        name, age = await extract_name_and_age(page)
        profile_data["name"] = name
        if age:
            profile_data["age"] = age
        image_urls = await extract_images(page)
        profile_data["image_urls"] = image_urls
        section_data = await extract_profile_sections(page)
        profile_data["profile_sections"] = section_data
        if "Interests" in section_data and isinstance(section_data["Interests"], list):
            profile_data["interests"] = section_data["Interests"]
        else:
            interests = await extract_interests(page)
            if interests:
                profile_data["interests"] = interests
        if config.SAVE_HTML:
            profile_data["html"] = await page.content()
        if hasattr(page, "profile_data"):
            for key, value in page.profile_data.items():
                profile_data[key] = value
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
            logger.info("Not closing browser since we're using remote debugging")
        else:
            await save_session(context)
            await page.close()
            await context.close()
            await browser.close()
            logger.info("Browser resources closed")
    except Exception as e:
        logger.error(f"Error closing browser: {str(e)}")
