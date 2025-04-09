# FirstChat Web UI

A minimalistic web interface for the FirstChat system that presents a sleek blue and white design for browsing scraped profiles and generating first messages.

## Features

- View all scraped profiles in an intuitive grid layout
- Examine detailed profile information for each match
- Select specific profile photos to use for message generation
- Customize message settings:
  - Message tone (friendly, witty, flirty, casual, confident)
  - Message length (1-5 sentences)
  - Creativity level (0.1-1.0)
- Generate personalized first messages using the FirstChat API
- View the image analysis and generated messages in an easy-to-read format
- Copy messages to clipboard with one click

## Requirements

- Python 3.6+
- Flask
- Requests

## Setup

The dependencies will be automatically installed when running the UI for the first time.

## Usage

1. Make sure the FirstChat API server is running:
   ```bash
   cd /path/to/FirstChat_BackEnd/servers/rest_firstchat_api
   uvicorn app:app --host 0.0.0.0 --port 8002
   ```

2. Run the UI server:
   ```bash
   cd /path/to/FirstChat_BackEnd/user_inteface
   ./run_ui.sh
   ```

3. Open your browser and navigate to:
   ```
   http://localhost:5001
   ```

## Workflow

1. **Profiles Tab**:
   - Browse all scraped profiles
   - View detailed profile information
   - Select images to use for message generation

2. **Generate Tab**:
   - Customize your bio
   - Set message tone, length, and creativity
   - Randomize or select specific profile images
   - Generate a personalized message

3. **Results Tab**:
   - View the generated message
   - See image analysis tags that were identified
   - Check token usage and other statistics
   - Copy message to clipboard

## Configuration

You can modify the following parameters in `firstchat_ui.py`:

- `SCRAPED_PROFILES_FOLDER`: Path to the scraped profiles directory
- `API_URL`: URL for the FirstChat API
- `DEFAULT_USER_BIO`: Default bio to use when generating messages

## Screenshots

The UI features a clean, modern interface with a blue and white color scheme, focusing on presenting profile information and generated messages in an easy-to-read format.