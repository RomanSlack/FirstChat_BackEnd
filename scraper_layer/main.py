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
    extract_profile_data, close_browser, extract_images
)
from data_processor import process_profile_data


def setup_logger():
    """Set up the logger with appropriate configuration."""
    log_format = "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>"
    logger.remove()
    logger.add(
        sys.stderr,
        format=log_format,
        level=config.LOG_LEVEL,
        colorize=True
    )
    if config.LOG_FILE:
        log_dir = os.path.dirname(os.path.abspath(config.LOG_FILE))
        os.makedirs(log_dir, exist_ok=True)
        logger.add(
            config.LOG_FILE,
            format=log_format,
            level=config.LOG_LEVEL,
            rotation="10 MB",
            retention="1 week"
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
            browser, context, page = await initialize_browser(playwright)
            try:
                if not await navigate_to_tinder(page):
                    logger.error("Failed to navigate to Tinder. Exiting.")
                    return
                for i in range(profile_count):
                    logger.info(f"Processing profile {i + 1}/{profile_count}")
                    logger.info("Starting profile extraction with enhanced image navigation...")
                    image_urls = await extract_images(page)
                    if not image_urls:
                        logger.error("Failed to extract any images. Stopping.")
                        return
                    if not await interact_with_profile(page):
                        logger.error("Failed to interact with profile. Stopping.")
                        return
                    profile_data = await extract_profile_data(page)
                    if not profile_data.get("name"):
                        logger.error("Could not extract profile name. Stopping.")
                        return
                    if not any(key == "Profile Photo 1" for key in profile_data.get("labeled_image_urls", {}).keys()):
                        logger.error("CRITICAL ERROR: Profile Photo 1 not found in labeled URLs - aborting processing")
                        screenshot_path = os.path.join(config.OUTPUT_DIR, "missing_profile_photo_1.png")
                        await page.screenshot(path=screenshot_path)
                        logger.error(f"Screenshot saved to {screenshot_path}")
                        return
                    processed_data = await process_profile_data(profile_data)
                    logger.info("Processed data summary:")
                    logger.info(f"  Name: {processed_data['name']}")
                    logger.info(f"  Age: {processed_data.get('age', 'N/A')}")
                    logger.info(
                        f"  Images: {processed_data.get('download_success_count', 0)}/{len(processed_data.get('image_urls', []))}")
                    logger.info(f"  Interests: {len(processed_data.get('interests', []))}")
                    logger.info(f"  Saved to: {processed_data.get('folder_path', 'Unknown')}")
                    print("\n" + "=" * 50)
                    print(f"Profile {i + 1}/{profile_count} scraped successfully:")
                    print(f"Name: {processed_data['name']}")
                    print(f"Age: {processed_data.get('age', 'N/A')}")
                    print(
                        f"Images: {processed_data.get('download_success_count', 0)}/{len(processed_data.get('image_urls', []))}")
                    print(f"Interests: {', '.join(processed_data.get('interests', [])[:5])}")
                    print(f"Saved to: {processed_data.get('folder_path', 'Unknown')}")
                    print("=" * 50 + "\n")
                    profile_counter += 1
                    screenshot_path = os.path.join(config.OUTPUT_DIR, "tinder_screenshot.png")
                    if os.path.exists(screenshot_path):
                        try:
                            os.remove(screenshot_path)
                            logger.info(f"Removed screenshot file: {screenshot_path}")
                        except Exception as e:
                            logger.error(f"Error removing screenshot: {str(e)}")
                    logger.info("Profile extraction complete. Stopping as requested.")
                    break
            finally:
                await close_browser(browser, context, page)
        logger.info(f"Scraper execution completed in {(datetime.now() - start_time).total_seconds():.2f} seconds")
        logger.info(f"Successfully scraped {profile_counter} profiles")
    except Exception as e:
        logger.exception(f"Unexpected error in scraper: {str(e)}")


def parse_args():
    """Parse command line arguments."""
    import argparse
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
    args = parse_args()
    if args.headless:
        config.HEADLESS = True
    if args.chrome_profile:
        config.CHROME_PROFILE_PATH = args.chrome_profile
    if args.chrome_path:
        config.CHROME_EXECUTABLE_PATH = args.chrome_path
    setup_logger()
    asyncio.run(run_tinder_scraper(
        profile_count=1,
        capture_delay=0
    ))


def run_interactive():
    """Run the scraper in interactive mode with a simple menu."""
    setup_logger()
    print("\n=== Tinder Profile Scraper ===\n")
    print("This scraper will extract data from exactly ONE profile and then stop.\n")
    print("IMPORTANT: For best results, run the following steps:")
    print("1. Run: ./launch_chrome.sh")
    print("2. In the opened Chrome window, go to Tinder and log in if needed")
    print("3. Enable mobile emulation in Chrome DevTools (F12 -> Toggle device toolbar)")
    print("4. Select iPhone 12 Pro Max as the device")
    print("5. Navigate to a Tinder profile you want to scrape")
    print("6. In a new terminal, run this script again\n")
    try:
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
                headless = input("Run in headless mode? (y/N): ").lower() == 'y'
                config.HEADLESS = headless
                use_profile = input(
                    f"Use default Chrome profile ({config.CHROME_PROFILE_PATH})? (Y/n): ").lower() != 'n'
                if not use_profile:
                    chrome_profile = input("Enter Chrome profile path: ")
                    if chrome_profile:
                        config.CHROME_PROFILE_PATH = chrome_profile
        except:
            print("Could not check for running Chrome instances")
            config.USE_REMOTE_CHROME = False
        print("\nStarting scraper with the following settings:")
        if config.USE_REMOTE_CHROME:
            print(f"- Using remote Chrome on port {config.REMOTE_DEBUGGING_PORT}")
        else:
            print(f"- Headless mode: {'Yes' if config.HEADLESS else 'No'}")
            print(f"- Chrome profile: {config.CHROME_PROFILE_PATH}")
        print(f"- Output directory: {config.OUTPUT_DIR}")
        print("\nThe scraper will extract ONE profile only and then stop.")
        print("Press Ctrl+C to stop at any time\n")
        profile_count = 1
        delay = 0
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
        main()
    else:
        run_interactive()
