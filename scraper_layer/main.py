#!/usr/bin/env python3
"""
FirstChat Profile Scraper

A production-grade script that extracts profile data from dating applications,
processes the information, and sends it to a local API endpoint for message generation.

Usage:
    python main.py
"""

import asyncio
import sys
import json
from typing import Dict, Any, List, Optional
import os
from datetime import datetime

from loguru import logger

from config import config
from browser import initialize_browser, navigate_to_profile, extract_profile_data, close_browser
from data_processor import process_profile_data
from api_client import send_to_api, format_api_response


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
        os.makedirs(os.path.dirname(os.path.abspath(config.LOG_FILE)), exist_ok=True)
        logger.add(
            config.LOG_FILE,
            format=log_format,
            level=config.LOG_LEVEL,
            rotation="10 MB",  # Rotate when file reaches 10MB
            retention="1 week"  # Keep logs for 1 week
        )


async def run_scraper() -> None:
    """Main function to execute the scraping process."""
    logger.info("Starting FirstChat Profile Scraper")
    logger.info(f"Target URL: {config.TARGET_URL}")
    logger.info(f"API Endpoint: {config.API_ENDPOINT}")
    
    start_time = datetime.now()
    
    try:
        # Initialize browser
        browser, context, page = await initialize_browser()
        
        try:
            # Navigate to profile
            if not await navigate_to_profile(page):
                logger.error("Failed to navigate to profile page. Exiting.")
                return
            
            # Extract profile data
            profile_data = await extract_profile_data(page)
            
            # Check if we have the minimum required data
            if not profile_data.get("name"):
                logger.error("Could not extract profile name. Exiting.")
                return
                
            if not profile_data.get("bio"):
                logger.warning("Bio is missing from profile data")
            
            if not profile_data.get("image_urls"):
                logger.error("No images found in profile. Exiting.")
                return
            
            # Process the profile data
            processed_data = await process_profile_data(profile_data)
            
            # Log summary of processed data
            logger.info(f"Processed data summary:")
            logger.info(f"  Name: {processed_data['match_bio']['name']}")
            logger.info(f"  Age: {processed_data['match_bio'].get('age', 'N/A')}")
            logger.info(f"  Bio length: {len(processed_data['match_bio']['bio'])} chars")
            logger.info(f"  Interests: {len(processed_data['match_bio']['interests'])}")
            logger.info(f"  Images: {2 if 'image2' in processed_data else 1}")
            
            # Skip API call and just save the data to file
            output_dir = "output"
            os.makedirs(output_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"{output_dir}/scraped_data_{timestamp}.json"
            
            # Display extracted data summary
            print("\n" + "=" * 50)
            print(f"Profile data scraped successfully:")
            print(f"Name: {processed_data['match_bio']['name']}")
            print(f"Age: {processed_data['match_bio'].get('age', 'N/A')}")
            print(f"Bio: {processed_data['match_bio']['bio'][:100]}...")
            print(f"Interests: {', '.join(processed_data['match_bio']['interests'][:5])}")
            print(f"Images: {2 if 'image2' in processed_data else 1}")
            print("=" * 50 + "\n")
            
            with open(output_file, 'w') as f:
                json.dump(processed_data, f, indent=2)
                
            logger.info(f"Scraped data saved to {output_file}")
            
            logger.info(f"Response saved to {output_file}")
            
        finally:
            # Close browser resources
            await close_browser(browser, context, page)
    
    except Exception as e:
        logger.exception(f"Unexpected error in scraper: {str(e)}")
    
    finally:
        # Log execution time
        execution_time = (datetime.now() - start_time).total_seconds()
        logger.info(f"Scraper execution completed in {execution_time:.2f} seconds")


def main():
    """Entry point for the scraper."""
    setup_logger()
    asyncio.run(run_scraper())


if __name__ == "__main__":
    main()