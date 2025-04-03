# FirstChat API Test Interface

A simple Streamlit interface for testing the FirstChat API.

## Features

- Upload images (automatically converted to base64)
- Enter user and match bio information
- Configure message generation parameters
- View API responses with generated messages

## Setup

1. Install requirements:

```bash
pip install -r requirements.txt
```

2. Make sure the FirstChat API is running:

```bash
cd /home/roman-slack/FirstChat_BackEnd/servers/rest_firstchat_api
python app.py
```

3. Run the Streamlit interface:

```bash
streamlit run streamlit_tester.py
```

4. Open your browser at http://localhost:8501

## Usage

1. Upload two images
2. Fill in the bios and parameters (or use the defaults)
3. Click "Send Request to API"
4. View the generated message and API response details

## Notes

- The API server must be running at http://localhost:8002
- You can modify the API URL in the sidebar if needed
- For production testing, ensure both services are accessible on the network