# FirstChat - Dating App First Message Generator

A complete system for generating personalized first messages for dating apps, composed of three main components:

## System Components

### 1. Profile Scraper (`/scraper_layer`)
- Extracts profile data from dating apps (currently Tinder)
- Saves profile details and images to structured folders
- Uses Playwright and Chrome for reliable profile extraction

### 2. API Server (`/servers/rest_firstchat_api`)
- FastAPI server that processes profile data and images
- Generates personalized first messages using OpenAI GPT models
- Provides a RESTful API for message generation

### 3. User Interface (`/user_inteface`)
- Flask web application with an intuitive UI
- Allows users to upload images and enter profile information
- Displays generated messages with detailed analytics

## Quick Start Guide

### Clone the Repository
```bash
git clone <repository-url>
cd FirstChat_BackEnd
```

### Setup and Run Each Component

#### 1. Profile Scraper
```bash
cd scraper_layer
pip install -r requirements.txt
playwright install chromium
./launch_chrome.sh  # In one terminal
./run_scraper       # In another terminal
```

#### 2. API Server
```bash
cd servers/rest_firstchat_api
pip install -r requirements.txt
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json
export OPENAI_API_KEY=your_openai_api_key
uvicorn app:app --host 0.0.0.0 --port 8002
```

#### 3. User Interface
```bash
cd user_inteface
pip install flask openai Pillow google-cloud-vision
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json
export OPENAI_API_KEY=your_openai_api_key
python app.py
```

## System Requirements

- Python 3.9+
- Google Cloud Vision API credentials
- OpenAI API key
- Chrome/Chromium for the scraper component

## Development Environment Setup

For a complete development environment, you can set up each component in sequence:

1. **Set up environment variables**:
   Create a `.env` file in each component directory with the required API keys.

2. **Install all dependencies**:
   ```bash
   cd scraper_layer && pip install -r requirements.txt
   cd ../servers/rest_firstchat_api && pip install -r requirements.txt
   cd ../user_inteface && pip install flask openai Pillow google-cloud-vision
   ```

3. **Initialize the database** (if using one in the future):
   Currently, the system does not use a persistent database, but stores extracted profiles in the filesystem.

## Configuration

Each component has its own configuration options:

- **Scraper**: Edit `scraper_layer/config.py` to adjust scraper behavior
- **API Server**: Configuration is primarily through environment variables 
- **User Interface**: Settings are defined in the Flask app (`user_inteface/app.py`)

## Documentation

For detailed documentation on each component, refer to the README.md files in their respective directories:

- [Scraper Documentation](scraper_layer/README.md)
- [API Server Documentation](servers/rest_firstchat_api/README.md)

## License

Proprietary - All rights reserved.