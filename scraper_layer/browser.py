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
    Immediately checks for Profile Photo 1 and exits if not found.
    
    Args:
        page: Playwright page object
        
    Returns:
        bool: True if navigation and Profile Photo 1 check were successful, False otherwise
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
        
        # We no longer check for Profile Photo 1 here - it's now done in main.py
        # This prevents duplicate checks and ensures it happens at exactly the right time
        
        logger.info("Successfully connected to Tinder")
        return True
        
    except Exception as e:
        logger.error(f"Failed to navigate to Tinder: {str(e)}")
        return False


async def interact_with_profile(page: Page) -> bool:
    """
    Interact with a Tinder profile to expand details.
    Image navigation is now handled separately in extract_images function.
    
    Args:
        page: Playwright page object
        
    Returns:
        bool: True if interaction was successful, False otherwise
    """
    try:
        # Wait for profile to load
        await asyncio.sleep(1)
        
        # Initialize profile_data if needed
        if not hasattr(page, "profile_data"):
            page.profile_data = {}
        
        # We're now assuming we're already positioned at the right image
        # from the extract_images function, so skip navigation
        
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
        
        # Click "View all 5" button if available
        try:
            logger.info("Looking for 'View all' button...")
            
            # Try the configured selector
            view_all_button = await page.query_selector(config.VIEW_ALL_SELECTOR)
            if view_all_button:
                await view_all_button.click()
                logger.info("Clicked 'View all' button")
                await asyncio.sleep(config.WAIT_BETWEEN_ACTIONS / 1000)
            else:
                # Try alternative selector
                logger.info("Trying alternative selector for 'View all' button...")
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
            logger.warning(f"Could not find or click 'View all' button: {str(e)}")
        
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
    Extract image URLs from Tinder carousel using DOM navigation.
    
    Args:
        page: Playwright page object
        
    Returns:
        List of image URLs
    """
    try:
        logger.info("Starting enhanced image extraction using DOM navigation...")
        
        # Initialize profile_data if needed
        if not hasattr(page, "profile_data"):
            page.profile_data = {}
            
        # Initialize collections for URLs
        labeled_urls = {}
        clean_urls = []
        
        # Step 1: Find the keen-slider container with the images
        logger.info("Locating the image carousel container...")
        
        # Look for the container with aria-live="polite" and keen-slider class
        carousel_container = await page.evaluate('''() => {
            // Find keen-slider container
            const container = document.querySelector('.keen-slider[aria-live="polite"]');
            if (!container) return null;
            
            // Get total number of images from the first slide
            const firstSlide = container.querySelector('.keen-slider__slide[aria-hidden="false"]');
            if (!firstSlide) return null;
            
            const ariaLabel = firstSlide.getAttribute('aria-label');
            const totalImagesMatch = ariaLabel ? ariaLabel.match(/(\\d+)$/) : null;
            const totalImages = totalImagesMatch ? parseInt(totalImagesMatch[1]) : 0;
            
            return {
                found: true,
                totalImages: totalImages
            };
        }''')
        
        if not carousel_container or not carousel_container.get('found'):
            logger.error("Failed to locate image carousel container")
            return []
            
        total_images = carousel_container.get('totalImages', 0)
        logger.info(f"Found image carousel with {total_images} total images")
        
        if total_images < 1:
            logger.error("No images found in carousel")
            return []
            
        # Step 2: Extract the first image
        logger.info("Extracting the first image URL...")
        
        # First, let's log the HTML structure around the image to debug
        html_debug = await page.evaluate('''() => {
            const slide = document.querySelector('.keen-slider__slide[aria-hidden="false"]');
            if (!slide) return "No visible slide found";
            
            return {
                slideHTML: slide.outerHTML.substring(0, 500),
                hasImgDiv: !!slide.querySelector('div[style*="background-image"]'),
                hasImgDivAlt: !!slide.querySelector('div[role="img"]'),
                allNestedDivs: slide.querySelectorAll('div').length,
                slideLabel: slide.getAttribute('aria-label')
            };
        }''')
        
        logger.info(f"HTML Debug Info: {html_debug}")
        
        # Now try to extract the image with multiple approaches
        first_image_data = await page.evaluate('''() => {
            // Find the currently visible slide
            const slide = document.querySelector('.keen-slider__slide[aria-hidden="false"]');
            if (!slide) return { error: "No visible slide found" };
            
            // Get the aria-label for numbering
            const slideLabel = slide.getAttribute('aria-label');
            
            // Try multiple approaches to find the image div
            let imgDiv = null;
            let approachUsed = "";
            
            // Approach 1: Find div with background-image in style
            imgDiv = slide.querySelector('div[style*="background-image"]');
            if (imgDiv) approachUsed = "background-image-style";
            
            // Approach 2: Find div with role="img"
            if (!imgDiv) {
                imgDiv = slide.querySelector('div[role="img"]');
                if (imgDiv) approachUsed = "role-img";
            }
            
            // Approach 3: Find div with aria-label containing "Profile Photo"
            if (!imgDiv) {
                imgDiv = slide.querySelector('div[aria-label*="Profile Photo"]');
                if (imgDiv) approachUsed = "aria-label-profile-photo";
            }
            
            // Approach 4: Just take the first div with a style attribute
            if (!imgDiv) {
                const allDivs = slide.querySelectorAll('div[style]');
                if (allDivs.length > 0) {
                    imgDiv = allDivs[0];
                    approachUsed = "first-styled-div";
                }
            }
            
            if (!imgDiv) {
                return { 
                    error: "No image div found",
                    slideLabel: slideLabel,
                    slideHTML: slide.outerHTML.substring(0, 300)
                };
            }
            
            // Extract the URL from the style
            const style = imgDiv.getAttribute('style');
            
            // Try multiple patterns to extract the URL
            let urlMatch = null;
            let patternUsed = "";
            
            // Pattern 1: Standard URL extraction
            urlMatch = style ? style.match(/url\\(&quot;(.*?)&quot;\\)/) : null;
            if (urlMatch) patternUsed = "standard-quot";
            
            // Pattern 2: URL with single quotes
            if (!urlMatch) {
                urlMatch = style ? style.match(/url\\('(.*?)'\\)/) : null;
                if (urlMatch) patternUsed = "single-quotes";
            }
            
            // Pattern 3: URL with double quotes
            if (!urlMatch) {
                urlMatch = style ? style.match(/url\\("(.*?)"\\)/) : null;
                if (urlMatch) patternUsed = "double-quotes";
            }
            
            // Pattern 4: URL without quotes
            if (!urlMatch) {
                urlMatch = style ? style.match(/url\\((.*?)\\)/) : null;
                if (urlMatch) patternUsed = "no-quotes";
            }
            
            if (!urlMatch) {
                return { 
                    error: "No URL found in style",
                    style: style,
                    approachUsed: approachUsed
                };
            }
            
            // Get the label for this image
            const imgLabel = imgDiv.getAttribute('aria-label') || ('Profile Image ' + (slideLabel ? slideLabel.split(' ')[0] : '1'));
            
            return {
                label: imgLabel,
                url: urlMatch[1],
                approachUsed: approachUsed,
                patternUsed: patternUsed,
                style: style.substring(0, 100) // Include part of the style for debugging
            };
        }''')
        
        if not first_image_data:
            logger.error("Failed to extract the first image URL - null result")
            # Get raw HTML for debugging
            html = await page.content()
            debug_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "debug_html_raw.txt")
            with open(debug_path, 'w', encoding='utf-8') as f:
                f.write(html[:20000])  # Save first 20K chars
            logger.error(f"Saved raw HTML to {debug_path}")
            return []
            
        # Check for error in the result
        if 'error' in first_image_data:
            logger.error(f"Failed to extract the first image URL - {first_image_data.get('error')}")
            logger.error(f"Debug data: {first_image_data}")
            # Take a screenshot for debugging
            await page.screenshot(path="debug_screenshot.png")
            logger.error("Saved debug screenshot to debug_screenshot.png")
            return []
            
        # Clean and add the first image URL
        first_url = first_image_data.get('url', '')
        first_label = first_image_data.get('label', 'Profile Photo 1')
        
        # Log additional debug info
        logger.info(f"First image extraction approach: {first_image_data.get('approachUsed')}")
        logger.info(f"URL pattern used: {first_image_data.get('patternUsed')}")
        if 'style' in first_image_data:
            logger.info(f"Style attribute preview: {first_image_data.get('style')}")
        
        # Clean up the URL entities
        first_url = first_url.replace('&amp;', '&')
        
        if first_url and 'https://images-ssl.gotinder.com/' in first_url:
            labeled_urls[first_label] = first_url
            clean_urls.append(first_url)
            logger.info(f"Successfully extracted {first_label}: {first_url[:60]}...")
        else:
            logger.error(f"Failed to extract valid URL for {first_label} - URL: {first_url}")
            # Try one more fallback - take a screenshot and see if we can extract the URL some other way
            await page.screenshot(path="first_image_screenshot.png")
            logger.error("First image extraction failed - saved screenshot for debugging")
            
            # Get raw HTML for debugging
            html = await page.content()
            with open("debug_html.txt", 'w', encoding='utf-8') as f:
                f.write(html[:20000])
            logger.error("Saved HTML for debugging")
            return []
            
        # Step 3: Tap through and extract each image
        logger.info(f"Extracting remaining {total_images - 1} images...")
        
        # Calculate tap positions - right side for forward, left side for backward
        screen_width = await page.evaluate("window.innerWidth")
        screen_height = await page.evaluate("window.innerHeight")
        
        right_tap_x = int(screen_width * 0.8)  # 80% from left
        left_tap_x = int(screen_width * 0.2)   # 20% from left
        tap_y = int(screen_height * 0.3)       # 30% from top
        
        # Try a more direct approach for carousel navigation
        # Instead of tapping, we'll use JavaScript to directly find and extract each image
        
        # Get all the slides first
        all_slides = await page.evaluate('''() => {
            const slides = document.querySelectorAll('.keen-slider__slide');
            const results = [];
            
            slides.forEach(slide => {
                results.push({
                    id: slide.id,
                    label: slide.getAttribute('aria-label'),
                    hidden: slide.getAttribute('aria-hidden') === 'true'
                });
            });
            
            return results;
        }''')
        
        logger.info(f"Found {len(all_slides)} slides in carousel: {all_slides}")
        
        # Process each slide directly without tapping
        for i in range(2, total_images + 1):
            logger.info(f"Processing image #{i} of {total_images}...")
            
            # We'll extract each image directly by finding the matching slide instead of trying to navigate
            slide_id = None
            
            # Find the slide ID that corresponds to this image number
            for slide in all_slides:
                if slide.get('label') and f"{i} of " in slide.get('label'):
                    slide_id = slide.get('id')
                    break
                    
            if not slide_id:
                logger.warning(f"Could not find slide ID for image #{i}")
                continue
                
            logger.info(f"Found slide ID '{slide_id}' for image #{i}")
            
            # Now extract image data directly from this slide using its ID
            image_data = await page.evaluate('''(slideId) => {
                // Find the slide by ID
                const slide = document.getElementById(slideId);
                if (!slide) {
                    return { error: "Slide not found by ID" };
                }
                
                // Find image div within this slide
                const imgDiv = slide.querySelector('div[style*="background-image"]') || 
                               slide.querySelector('div[role="img"]') ||
                               slide.querySelector('div[aria-label*="Profile Photo"]');
                               
                if (!imgDiv) {
                    return { 
                        error: "No image div found in slide",
                        slideId: slideId
                    };
                }
                
                // Extract URL from style
                const style = imgDiv.getAttribute('style');
                let urlMatch = null;
                let patternUsed = "";
                
                // Try multiple patterns
                urlMatch = style ? style.match(/url\\("(.*?)"\\)/) : null;
                if (urlMatch) patternUsed = "double-quotes";
                
                if (!urlMatch) {
                    urlMatch = style ? style.match(/url\\('(.*?)'\\)/) : null;
                    if (urlMatch) patternUsed = "single-quotes";
                }
                
                if (!urlMatch) {
                    urlMatch = style ? style.match(/url\\(&quot;(.*?)&quot;\\)/) : null;
                    if (urlMatch) patternUsed = "html-quotes";
                }
                
                if (!urlMatch) {
                    urlMatch = style ? style.match(/url\\((.*?)\\)/) : null;
                    if (urlMatch) patternUsed = "no-quotes";
                }
                
                if (!urlMatch) {
                    return { 
                        error: "No URL found in style", 
                        style: style ? style.substring(0, 100) : null 
                    };
                }
                
                // Get label
                const imgLabel = imgDiv.getAttribute('aria-label') || ('Profile Photo ' + (slide.getAttribute('aria-label') || '').split(' ')[0]);
                
                return {
                    label: imgLabel,
                    url: urlMatch[1],
                    patternUsed: patternUsed
                };
                // Pattern 4: URL without quotes
                if (!urlMatch) {
                    urlMatch = style ? style.match(/url\\((.*?)\\)/) : null;
                    if (urlMatch) patternUsed = "no-quotes";
                }
                
                if (!urlMatch) {
                    return { 
                        error: "No URL found in style",
                        style: style ? style.substring(0, 100) : null,
                        approachUsed: approachUsed
                    };
                }
                
                // Get the label for this image
                const imgLabel = imgDiv.getAttribute('aria-label') || ('Profile Photo ' + imageNumber);
                
                return {
                    label: imgLabel,
                    url: urlMatch[1],
                    approachUsed: approachUsed,
                    patternUsed: patternUsed
                };
            }''', i)
            
            if not image_data:
                logger.warning(f"Failed to extract image #{i} - null result")
                continue
                
            # Check for error in the result
            if 'error' in image_data:
                logger.warning(f"Failed to extract image #{i} - {image_data.get('error')}")
                logger.warning(f"Debug data: {image_data}")
                continue
                
            # Log approach used
            logger.info(f"Image #{i} extraction approach: {image_data.get('approachUsed', 'unknown')}")
            logger.info(f"URL pattern used: {image_data.get('patternUsed', 'unknown')}")
                
            # Clean and add the image URL
            img_url = image_data.get('url', '')
            img_label = image_data.get('label', f'Profile Photo {i}')
            
            # Clean up the URL entities
            img_url = img_url.replace('&amp;', '&')
            
            if img_url and 'https://images-ssl.gotinder.com/' in img_url and img_url not in clean_urls:
                labeled_urls[img_label] = img_url
                clean_urls.append(img_url)
                logger.info(f"Successfully extracted {img_label}: {img_url[:60]}...")
        
        # Step 4: Return to the 3rd image (or the last image if there are fewer than 3)
        target_image = min(3, total_images)
        current_image = total_images
        
        # Calculate how many left taps needed to go from last image to 3rd
        left_taps_needed = current_image - target_image
        
        logger.info(f"Navigating back to image #{target_image} from image #{current_image}...")
        
        # Tap left as needed
        for _ in range(left_taps_needed):
            await page.mouse.click(left_tap_x, tap_y)
            await asyncio.sleep(0.3)
        
        logger.info(f"Completed image extraction. Found {len(clean_urls)} images with {len(labeled_urls)} labels.")
        
        # Check if we found the critical first image - if not, this is a terminal failure
        profile_photo_1_exists = any(key == "Profile Photo 1" for key in labeled_urls.keys())
        
        if not profile_photo_1_exists or len(clean_urls) < 1:
            logger.error("CRITICAL ERROR: Could not find Profile Photo 1 or no images extracted.")
            logger.error("No fallback attempted - exiting immediately as requested.")
            
            # Take a debug screenshot
            debug_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "failed_extraction.png")
            await page.screenshot(path=debug_path)
            logger.error(f"Saved debug screenshot to {debug_path}")
            
            return []
        
        # Store the results in the page object
        page.profile_data["image_urls"] = clean_urls
        page.profile_data["image_urls_backup"] = clean_urls  # For compatibility
        page.profile_data["labeled_image_urls"] = labeled_urls
        
        # Don't auto-label as Profile Photo 1 - if it's not properly labeled, we should exit
        # This was already checked above
        
        # Return the clean URLs
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
        
        # Add any screenshot paths and other debug info we've collected
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