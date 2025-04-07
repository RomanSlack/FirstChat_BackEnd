# FirstChat Backend System

A complete backend solution for a dating app first message generator with three main components:
1. Profile Data Scraper (scraper_layer)
2. API Server (servers/rest_firstchat_api)
3. User Interface (user_interface)

## System Overview

The FirstChat system works as follows:
1. The **Profile Scraper** extracts profile data from dating apps (Tinder)
2. The **API Server** processes requests with profile data and images to generate personalized first messages
3. The **User Interface** provides a web interface for users to input profile data and receive generated messages

## 1. Profile Scraper

The scraper extracts profile data from ONE Tinder profile at a time, including name, age, interests, and images.

### Installation

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

### Running the Scraper

#### Method 1: Two-step process (Recommended)

1. Launch Chrome with remote debugging enabled:
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

#### Method 2: Interactive Mode

Run the scraper directly and follow the prompts:
```bash
./run_scraper
```

### Scraper Output

For each profile, the scraper creates a directory in `./scraped_profiles/` with:
- `profile_data.json`: All extracted profile data in structured format
- `profile.html`: Raw HTML of the profile (if enabled in config)
- `image_0.jpg`, `image_1.jpg`, etc.: All downloaded profile images
- Screenshots from the extraction process for debugging

## 2. REST API Server

A FastAPI server that generates personalized first messages based on profile data and images.

### Installation

1. Navigate to the API server directory:
```bash
cd /home/roman-slack/FirstChat_BackEnd/servers/rest_firstchat_api
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up required environment variables:
```bash
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/your/google-cloud-credentials.json
export OPENAI_API_KEY=your_openai_api_key
```

### Running the API Server

```bash
uvicorn app:app --host 0.0.0.0 --port 8002
```

The API documentation will be available at http://localhost:8002/docs

### API Endpoints

- `GET /health`: Health check endpoint
- `POST /generate_message`: Generate a first message based on profile information and images

## 3. User Interface

A Flask web application that provides a user-friendly interface for generating first messages.

### Installation

1. Navigate to the user interface directory:
```bash
cd /home/roman-slack/FirstChat_BackEnd/user_inteface
```

2. Install dependencies:
```bash
pip install flask openai Pillow google-cloud-vision
```

3. Set up the same environment variables as for the API server:
```bash
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/your/google-cloud-credentials.json
export OPENAI_API_KEY=your_openai_api_key
```

### Running the User Interface

```bash
python app.py
```

The web interface will be available at http://localhost:5000

## End-to-End Workflow

1. Use the scraper to extract profile data from a dating app
2. Take the profile data and images from the scraper output
3. Either:
   - Use the web interface to generate a message
   - Make a direct API call to the REST server

## Troubleshooting

### Scraper Issues
- **Login Required**: Make sure to run with a Chrome profile that's already logged in to Tinder
- **Elements Not Found**: Use the recommended method with remote debugging
- **Images Not Downloading**: Check the screenshots in the output directory
- **Remote Debugging Not Working**: Make sure Chrome is running with remote debugging on port 9222

### API Server Issues
- **Missing Environment Variables**: Ensure GOOGLE_APPLICATION_CREDENTIALS and OPENAI_API_KEY are set
- **Permission Errors**: Check Google Cloud service account permissions for Vision API
- **Connection Issues**: If running in a Docker container, check network connectivity

### UI Issues
- **Image Upload Errors**: Ensure images are in supported formats (JPG, PNG)
- **Form Validation Errors**: Ensure all required fields are filled in
- **API Connection Errors**: If using remote API, check connectivity and CORS settings

## License

Open Source