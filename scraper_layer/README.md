# Tinder Profile Scraper

A tool that extracts profile data from ONE Tinder profile, including name, age, interests, and images. The scraper saves all data to an organized folder and then stops without interacting with like/dislike buttons.

## Features

- **Profile Data Extraction**: Name, age, interests, and other profile details
- **Image Download**: Saves all carousel images (up to 5)
- **Non-Intrusive**: Doesn't like or dislike profiles
- **Smart Navigation**: Implements the specific click sequence required for Tinder
- **Remote Chrome Support**: Can connect to a running Chrome instance
- **Chrome Profile Support**: Uses your existing Chrome profile with Tinder login
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

### Recommended Method (Two-step process)

1. First, launch Chrome with remote debugging enabled:

```bash
./launch_chrome.sh
```

2. In the Chrome window that opens:
   - Navigate to Tinder and login if needed
   - Open DevTools (F12)
   - Enable mobile emulation (Click "Toggle device toolbar" icon)
   - Select "iPhone 12 Pro Max" from the device dropdown
   - Navigate to the Tinder profile you want to scrape
   - Make sure you can see the profile info

3. In a new terminal window, run the scraper:

```bash
./run_scraper
```

4. Select "Yes" when asked if you want to connect to the running Chrome instance

### Alternative Method (Direct Connection)

If you prefer, you can run the scraper directly:

```bash
./run_scraper
```

And then follow the prompts to configure the scraper options.

## Output

For each profile, the scraper creates a directory with:

1. `profile_data.json`: Contains all extracted profile data
2. `profile.html`: Raw HTML of the profile (if enabled in config)
3. `image_0.jpg`, `image_1.jpg`, etc.: All downloaded profile images
4. Several screenshots of the extraction process for debugging

Example output structure:
```
scraped_profiles/
└── Jane_1649213001/
    ├── profile_data.json
    ├── profile.html
    ├── image_0.jpg
    ├── image_1.jpg
    └── image_2.jpg
```

## Troubleshooting

- **Login Required**: Make sure to run with a Chrome profile that's already logged in to Tinder
- **Elements Not Found**: If buttons or profile sections can't be found, try using the recommended method with remote debugging
- **Images Not Downloading**: Check the screenshots in the output directory to see if the profile is visible
- **Remote Debugging Not Working**: Make sure Chrome is running with remote debugging on port 9222 (use the launch_chrome.sh script)

## License

Proprietary - All rights reserved.