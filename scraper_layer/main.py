#!/usr/bin/env python3
"""
Tinder Profile Scraper

A tool that extracts profile data from Tinder, 
including name, age, bio, interests, and images.

Usage:
    python main.py
"""

import asyncio
import sys
import os
import time
import re
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime
import argparse

from loguru import logger
from playwright.async_api import async_playwright

from config import config
from browser import (
    initialize_browser, navigate_to_tinder, interact_with_profile,
    extract_profile_data, close_browser
)
from data_processor import process_profile_data


# Configure logger
def setup_logger():
    """Set up the logger with appropriate configuration."""
    log_format = "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>"
    
    # Configure loguru
    logger.remove()  # Remove default handler
    
    # Add console handler
    logger.add(
        sys.stderr,
        format=log_format,
        level=config.LOG_LEVEL,
        colorize=True
    )
    
    # Add file handler if configured
    if config.LOG_FILE:
        log_dir = os.path.dirname(os.path.abspath(config.LOG_FILE))
        os.makedirs(log_dir, exist_ok=True)
        logger.add(
            config.LOG_FILE,
            format=log_format,
            level=config.LOG_LEVEL,
            rotation="10 MB",  # Rotate when file reaches 10MB
            retention="1 week"  # Keep logs for 1 week
        )


async def run_tinder_scraper(profile_count: int = 1, capture_delay: float = 0.5) -> None:
    """
    Main function to execute the Tinder scraping process.
    
    Args:
        profile_count: Number of profiles to scrape
        capture_delay: Delay in seconds between capturing profiles
    """
    logger.info("Starting Tinder Profile Scraper")
    logger.info(f"Target URL: {config.TARGET_URL}")
    logger.info(f"Output directory: {config.OUTPUT_DIR}")
    logger.info(f"Profiles to scrape: {profile_count}")
    
    profile_counter = 0
    start_time = datetime.now()
    
    try:
        async with async_playwright() as playwright:
            # Initialize browser
            browser, context, page = await initialize_browser(playwright)
            
            try:
                # Navigate to Tinder
                if not await navigate_to_tinder(page):
                    logger.error("Failed to navigate to Tinder. Exiting.")
                    return
                
                # Process profiles
                for i in range(profile_count):
                    logger.info(f"Processing profile {i+1}/{profile_count}")
                    
                    # First, check for Profile Photo 1 BEFORE any interactions
                    html = await page.content()
                    
                    # Use exact pattern from the reference file, but capture the FULL URL
                    # This pattern captures everything between url(&quot; and &quot;) to get the complete URL with signature
                    profile_photo_pattern = r'aria-label="Profile Photo 1"[^>]*?url\(&quot;(https://images-ssl\.gotinder\.com/[^&"]+(?:&amp;[^&"]+)*)&quot;\)'
                    
                    # Alternative patterns if the exact one fails
                    alt_patterns = [
                        # Try to get the complete URL including signature
                        r'Profile Photo 1"[^>]*?url\(&quot;(https://images-ssl\.gotinder\.com/[^"]+)&quot;',
                        
                        # Another version capturing the full URL
                        r'aria-label="Profile Photo 1"[^>]*?background-image: url\(&quot;(https://images-ssl\.gotinder\.com/[^)]+)',
                        
                        # Even more aggressive pattern
                        r'Profile Photo 1.*?url\(&quot;(https://images-ssl\.gotinder\.com/[^)]+)',
                        
                        # Last resort - just try to find any URL after Profile Photo 1
                        r'Profile Photo 1.*?(https://images-ssl\.gotinder\.com/[^"\'<>\s]+)',
                    ]
                    
                    # Try the exact pattern first
                    match = re.search(profile_photo_pattern, html)
                    
                    # If not found, try alternatives
                    if not match:
                        for pattern in alt_patterns:
                            match = re.search(pattern, html)
                            if match:
                                break
                    
                    # If STILL not found, stop everything
                    if not match:
                        logger.error("CRITICAL ERROR: Profile Photo 1 not found on initial check. Stopping immediately.")
                        # Save HTML for debugging
                        debug_path = os.path.join(config.OUTPUT_DIR, "debug_html_main.txt")
                        with open(debug_path, 'w', encoding='utf-8') as f:
                            f.write(html[:10000])  # First 10K chars to avoid huge files
                        logger.error(f"Saved debug HTML to {debug_path}")
                        return
                    
                    # If we found it, store the URL for later use
                    first_photo_url = match.group(1)
                    
                    # Clean up HTML entities in the URL
                    first_photo_url = first_photo_url.replace('&amp;', '&')
                    first_photo_url = first_photo_url.replace('&quot;', '')
                    first_photo_url = first_photo_url.replace('&quot', '')
                    
                    # Check if the URL has a signature
                    if "Signature=" not in first_photo_url:
                        logger.warning("Profile Photo 1 URL doesn't contain a signature. This might cause issues.")
                        
                    logger.info(f"FOUND PROFILE PHOTO 1: {first_photo_url[:60]}...")
                    
                    # Interact with the profile (click sequence)
                    if not await interact_with_profile(page):
                        logger.error("Failed to interact with profile. Stopping.")
                        return
                    
                    # Extract profile data and manually inject the first photo URL
                    profile_data = await extract_profile_data(page)
                    
                    # Make sure the Profile Photo 1 URL is in the data
                    if not profile_data.get("image_urls"):
                        profile_data["image_urls"] = []
                        
                    if first_photo_url not in profile_data["image_urls"]:
                        profile_data["image_urls"].insert(0, first_photo_url)
                        
                    # Add labeled image URLs if not present
                    if not profile_data.get("labeled_image_urls"):
                        profile_data["labeled_image_urls"] = {}
                        
                    profile_data["labeled_image_urls"]["Profile Photo 1"] = first_photo_url
                    
                    # Check if we have the minimum required data
                    if not profile_data.get("name"):
                        logger.error("Could not extract profile name. Stopping.")
                        return
                    
                    # Process the profile data (download images, save JSON)
                    processed_data = await process_profile_data(profile_data)
                    
                    # Log summary of processed data
                    logger.info(f"Processed data summary:")
                    logger.info(f"  Name: {processed_data['name']}")
                    logger.info(f"  Age: {processed_data.get('age', 'N/A')}")
                    logger.info(f"  Images: {processed_data.get('download_success_count', 0)}/{len(processed_data.get('image_urls', []))}")
                    logger.info(f"  Interests: {len(processed_data.get('interests', []))}")
                    logger.info(f"  Saved to: {processed_data.get('folder_path', 'Unknown')}")
                    
                    # Display real-time feedback
                    print("\n" + "=" * 50)
                    print(f"Profile {i+1}/{profile_count} scraped successfully:")
                    print(f"Name: {processed_data['name']}")
                    print(f"Age: {processed_data.get('age', 'N/A')}")
                    print(f"Images: {processed_data.get('download_success_count', 0)}/{len(processed_data.get('image_urls', []))}")
                    print(f"Interests: {', '.join(processed_data.get('interests', [])[:5])}")
                    print(f"Saved to: {processed_data.get('folder_path', 'Unknown')}")
                    print("=" * 50 + "\n")
                    
                    profile_counter += 1
                    
                    # Remove screenshot files if they exist
                    screenshot_path = os.path.join(config.OUTPUT_DIR, "tinder_screenshot.png")
                    if os.path.exists(screenshot_path):
                        try:
                            os.remove(screenshot_path)
                            logger.info(f"Removed screenshot file: {screenshot_path}")
                        except Exception as e:
                            logger.error(f"Error removing screenshot: {str(e)}")
                    
                    # Just stop here after extracting data from one profile
                    # No clicking on Pass or moving to next profile
                    logger.info("Profile extraction complete. Stopping as requested.")
                    # Break out of the for loop after the first profile
                    break
                    
            finally:
                # Close browser resources
                await close_browser(browser, context, page)
        
    except Exception as e:
        logger.exception(f"Unexpected error in scraper: {str(e)}")
    
    finally:
        # Log execution time and summary
        execution_time = (datetime.now() - start_time).total_seconds()
        logger.info(f"Scraper execution completed in {execution_time:.2f} seconds")
        logger.info(f"Successfully scraped {profile_counter} profiles")


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Tinder Profile Scraper")
    parser.add_argument(
        "--headless", 
        action="store_true", 
        help="Run in headless mode (no browser UI)"
    )
    parser.add_argument(
        "--chrome-profile", 
        type=str, 
        help="Path to Chrome profile directory"
    )
    parser.add_argument(
        "--chrome-path", 
        type=str, 
        help="Path to Chrome executable"
    )
    return parser.parse_args()


def main():
    """Entry point for the scraper."""
    # Parse command line arguments
    args = parse_args()
    
    # Override config with command line arguments
    if args.headless:
        config.HEADLESS = True
    if args.chrome_profile:
        config.CHROME_PROFILE_PATH = args.chrome_profile
    if args.chrome_path:
        config.CHROME_EXECUTABLE_PATH = args.chrome_path
    
    # Set up logger
    setup_logger()
    
    # Run the scraper with fixed count=1
    asyncio.run(run_tinder_scraper(
        profile_count=1,
        capture_delay=0
    ))


def run_interactive():
    """Run the scraper in interactive mode with a simple menu."""
    setup_logger()
    
    print("\n=== Tinder Profile Scraper ===\n")
    print("This scraper will extract data from exactly ONE profile and then stop.")
    print()
    print("IMPORTANT: For best results, run the following steps:")
    print("1. Run: ./launch_chrome.sh")
    print("2. In the opened Chrome window, go to Tinder and log in if needed")
    print("3. Enable mobile emulation in Chrome DevTools (F12 -> Toggle device toolbar)")
    print("4. Select iPhone 12 Pro Max as the device")
    print("5. Navigate to a Tinder profile you want to scrape")
    print("6. In a new terminal, run this script again")
    print()
    
    try:
        # Always use profile_count=1
        profile_count = 1
        delay = 0 # Not used since we're only scraping one profile
        
        # Check if Chrome is running with remote debugging
        import socket
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(('localhost', config.REMOTE_DEBUGGING_PORT))
            sock.close()
            
            if result == 0:
                print(f"Found Chrome running with remote debugging on port {config.REMOTE_DEBUGGING_PORT}")
                use_remote_chrome = input("Connect to this Chrome instance? (Y/n): ").lower() != 'n'
                config.USE_REMOTE_CHROME = use_remote_chrome
            else:
                print(f"No Chrome instance found on port {config.REMOTE_DEBUGGING_PORT}")
                print("You can start Chrome with remote debugging using: ./launch_chrome.sh")
                use_remote_chrome = False
                config.USE_REMOTE_CHROME = use_remote_chrome
                
                # If not using remote Chrome, ask about headless mode
                headless = input("Run in headless mode? (y/N): ").lower() == 'y'
                config.HEADLESS = headless
                
                # Ask about Chrome profile
                use_profile = input(f"Use default Chrome profile ({config.CHROME_PROFILE_PATH})? (Y/n): ").lower() != 'n'
                if not use_profile:
                    chrome_profile = input("Enter Chrome profile path: ")
                    if chrome_profile:
                        config.CHROME_PROFILE_PATH = chrome_profile
        except:
            print("Could not check for running Chrome instances")
            config.USE_REMOTE_CHROME = False
        
        # Print settings
        print("\nStarting scraper with the following settings:")
        if config.USE_REMOTE_CHROME:
            print(f"- Using remote Chrome on port {config.REMOTE_DEBUGGING_PORT}")
        else:
            print(f"- Headless mode: {'Yes' if config.HEADLESS else 'No'}")
            print(f"- Chrome profile: {config.CHROME_PROFILE_PATH}")
        print(f"- Output directory: {config.OUTPUT_DIR}")
        print("\nThe scraper will extract ONE profile only and then stop.")
        print("Press Ctrl+C to stop at any time\n")
        
        # Run the scraper
        asyncio.run(run_tinder_scraper(
            profile_count=profile_count,
            capture_delay=delay
        ))
        
    except KeyboardInterrupt:
        print("\nScraper stopped by user")
    except ValueError:
        print("\nInvalid input. Please enter numeric values where required.")
    except Exception as e:
        print(f"\nError: {str(e)}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Run with command line arguments
        main()
    else:
        # Run interactive mode
        run_interactive()