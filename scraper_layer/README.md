# FirstChat Profile Scraper

A production-grade Python application that extracts profile data from dating applications, processes the information, and sends it to the FirstChat API for message generation.

## Features

- **Browser Automation**: Uses Playwright for reliable web scraping
- **Session Persistence**: Maintains login sessions between runs
- **Image Processing**: Downloads and converts images to base64 format
- **Error Handling**: Comprehensive error handling and retry logic
- **Configuration**: Easily configurable via environment variables or .env file
- **Logging**: Detailed logging for monitoring and debugging

## Installation

1. Clone the repository and navigate to the scraper directory:

```bash
cd /home/roman-slack/FirstChat_BackEnd/scraper_layer
```

2. Install Python dependencies:

```bash
pip install -r requirements.txt
```

3. Install Playwright browsers:

```bash
playwright install
```

4. Create a configuration file by copying the example:

```bash
cp .env.example .env
```

5. Edit the `.env` file to customize your settings.

## Configuration

The scraper is highly configurable through environment variables or the `.env` file. Key configuration options include:

- `TARGET_URL`: The dating app URL to scrape profiles from
- `API_ENDPOINT`: The FirstChat API endpoint for message generation
- `USER_BIO`: Your profile bio that will be sent with the API request
- `HEADLESS`: Whether to run the browser in headless mode
- `*_SELECTOR`: CSS selectors for extracting profile data
- `MESSAGE_TONE`, `MESSAGE_SENTENCE_COUNT`, `MESSAGE_CREATIVITY`: Parameters for message generation

See `.env.example` for a complete list of configuration options.

## Usage

Run the scraper with:

```bash
python main.py
```

The scraper will:
1. Open a browser and navigate to the target dating app
2. Extract profile information (name, age, bio, images)
3. Download and convert profile images
4. Send the processed data to the FirstChat API
5. Display the generated message and save the result

## Output

The scraper will display the generated message in the console and save the complete API response to the `output` directory as a JSON file.

## CSS Selectors

The `.env.example` file contains default CSS selectors for extracting profile data:

```
PROFILE_NAME_SELECTOR=.profile-name
PROFILE_AGE_SELECTOR=.profile-age
PROFILE_BIO_SELECTOR=.profile-bio
PROFILE_INTERESTS_SELECTOR=.profile-interests .interest
PROFILE_IMAGES_SELECTOR=.profile-images img
```

These selectors must be customized for the specific dating app you're targeting.

## Error Handling

The scraper implements comprehensive error handling:

- Connection failures with automatic retries
- Image processing fallbacks with placeholder images
- Detailed logging for troubleshooting
- Graceful exit on critical errors

## Customization

For different dating apps, you may need to customize:

1. CSS selectors in your `.env` file
2. Login flow in `browser.py` if authentication is required
3. Image processing parameters in `data_processor.py`

## License

Proprietary - All rights reserved.

## Troubleshooting

- **Browser doesn't start**: Ensure Playwright is installed: `playwright install`
- **Can't find elements**: Adjust CSS selectors in your `.env` file
- **API connection fails**: Verify the API server is running at the configured endpoint
- **Authentication issues**: Check if the dating app requires login and modify accordingly