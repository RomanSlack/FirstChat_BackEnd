# Tinder Profile Scraper

A tool that extracts profile data from ONE Tinder profile, including name, age, interests, and images. The scraper saves all data to an organized folder and then stops without interacting with like/dislike buttons.

## Features

- **Profile Data Extraction**: Name, age, interests, and other profile details
- **Image Download**: Saves all carousel images (up to 5)
- **Non-Intrusive**: Doesn't like or dislike profiles
- **Smart Navigation**: Implements the specific click sequence required for Tinder
- **Session Persistence**: Maintains login sessions between runs
- **User-Friendly**: Interactive mode with real-time display
- **Chrome Profile Support**: Can use an existing Chrome profile for authentication
- **Organized Output**: Creates a folder named after the profile with all extracted data

## Installation

1. Navigate to the scraper directory:

```bash
cd /home/roman-slack/FirstChat_BackEnd/scraper_layer
```

2. Install Python dependencies:

```bash
pip install -r requirements.txt
```

3. Install Playwright browsers:

```bash
playwright install chromium
```

## Usage

### Interactive Mode

Simply run the script with no arguments to enter interactive mode:

```bash
python main.py
```

The script will prompt you for:
- Number of profiles to scrape
- Delay between profiles
- Headless mode (yes/no)
- Whether to use an existing Chrome profile

### Command Line Arguments

You can also run the script with command line arguments:

```bash
python main.py --chrome-profile "/path/to/chrome/profile" --chrome-path "/path/to/chrome"
```

Available options:
- `--headless`: Run in headless mode (no browser UI)
- `--chrome-profile`: Path to Chrome profile directory
- `--chrome-path`: Path to Chrome executable

### Chrome Profile

To use your existing Tinder login, you need to provide the path to your Chrome profile where you're already logged in to Tinder. This is typically found at:

- Windows: `C:\Users\username\AppData\Local\Google\Chrome\User Data\Default`
- macOS: `/Users/username/Library/Application Support/Google/Chrome/Default`
- Linux: `/home/username/.config/google-chrome/Default`

## Output

For each profile, the scraper creates a directory with:

1. `profile_data.json`: Contains all extracted profile data
2. `profile.html`: Raw HTML of the profile (if enabled in config)
3. `image_0.jpg`, `image_1.jpg`, etc.: All downloaded profile images

Example output structure:
```
scraped_profiles/
├── Jane_1649213001/
│   ├── profile_data.json
│   ├── profile.html
│   ├── image_0.jpg
│   ├── image_1.jpg
│   └── image_2.jpg
└── John_1649213042/
    ├── profile_data.json
    ├── profile.html
    ├── image_0.jpg
    └── image_1.jpg
```

## Configuration

The scraper can be configured through environment variables or a `.env` file. Key configuration options:

- `TARGET_URL`: The Tinder URL to scrape (default: "https://tinder.com/app/recs")
- `OUTPUT_DIR`: Directory to save profile data (default: "./scraped_profiles")
- `HEADLESS`: Whether to run the browser in headless mode
- `DEVICE_NAME`: Mobile device to emulate (default: "iPhone 14 Pro Max")
- `SAVE_HTML`: Whether to save raw HTML with profiles

## Troubleshooting

- **Login Required**: Use the `--chrome-profile` option with your existing Chrome profile
- **Selectors Not Working**: Tinder may have updated their UI; check the latest HTML reference
- **Images Not Downloading**: Check network connectivity and URL formats
- **Browser Not Starting**: Ensure Playwright is installed correctly
- **Navigation Issues**: Try adjusting the delay between actions in config

## License

Proprietary - All rights reserved.