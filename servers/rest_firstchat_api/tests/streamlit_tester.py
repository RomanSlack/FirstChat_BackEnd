"""
Streamlit test interface for the FirstChat API

This provides a simple web UI to test the FirstChat API by:
- Uploading images (converted to base64)
- Entering user and match bio information
- Setting message generation parameters
- Displaying the API response

Run with:
    streamlit run streamlit_tester.py
"""

import json
import base64
from io import BytesIO
import requests
import streamlit as st
from PIL import Image

# API configuration
API_BASE_URL = "http://localhost:8002"
GENERATE_MESSAGE_ENDPOINT = f"{API_BASE_URL}/generate_message"

# Page configuration
st.set_page_config(
    page_title="FirstChat API Tester",
    page_icon="💬",
    layout="wide"
)

# Function to convert uploaded image to base64
def image_to_base64(img):
    buffered = BytesIO()
    img.save(buffered, format="JPEG")
    return f"data:image/jpeg;base64,{base64.b64encode(buffered.getvalue()).decode('utf-8')}"

# App title and description
st.title("FirstChat API Tester")
st.markdown("""
This interface helps you test the FirstChat API by uploading images and configuring request parameters.
Results will show the generated first message and processing details.
""")

# Sidebar for API configuration
with st.sidebar:
    st.header("API Configuration")
    api_url = st.text_input("API URL", value=GENERATE_MESSAGE_ENDPOINT)
    
    st.header("Request Configuration")
    tone = st.selectbox(
        "Message Tone",
        options=["friendly", "witty", "flirty", "casual", "confident"],
        index=0
    )
    
    sentence_count = st.slider(
        "Sentence Count",
        min_value=1,
        max_value=5,
        value=2
    )
    
    creativity = st.slider(
        "Creativity Level",
        min_value=0.0,
        max_value=1.0,
        value=0.7,
        step=0.1
    )

# Main content layout with two columns
left_col, right_col = st.columns([1, 1])

# Left column for inputs
with left_col:
    st.header("Images")
    st.markdown("Upload two images to be analyzed")
    
    # Image uploads
    image1_file = st.file_uploader("Upload first image", type=["jpg", "jpeg", "png"])
    image2_file = st.file_uploader("Upload second image", type=["jpg", "jpeg", "png"])
    
    # Display uploaded images
    if image1_file and image2_file:
        image1 = Image.open(image1_file)
        image2 = Image.open(image2_file)
        
        img_col1, img_col2 = st.columns(2)
        with img_col1:
            st.image(image1, caption="Image 1", use_column_width=True)
        with img_col2:
            st.image(image2, caption="Image 2", use_column_width=True)
    
    # User bio input
    st.header("Your Bio")
    user_bio = st.text_area(
        "Enter your bio",
        value="Hey, I'm a 28-year-old photographer with a passion for travel and street food. I love exploring cities, capturing unique moments, and finding hidden gems. Looking for someone adventurous and laid-back.",
        height=100
    )
    
    # Match bio inputs
    st.header("Match Bio")
    match_name = st.text_input("Name", value="Emma")
    match_age = st.number_input("Age", min_value=18, max_value=99, value=26)
    match_bio = st.text_area(
        "Bio",
        value="Adventure seeker and coffee enthusiast. Love hiking, capturing sunsets, and finding cute cafes. Always up for trying something new!",
        height=100
    )
    match_interests = st.text_input(
        "Interests (comma separated)",
        value="hiking, photography, coffee, travel, nature"
    )

# Right column for request preview and results
with right_col:
    st.header("API Request")
    
    # Create request JSON
    if image1_file and image2_file:
        # Convert images to base64
        image1_base64 = image_to_base64(Image.open(image1_file))
        image2_base64 = image_to_base64(Image.open(image2_file))
        
        # Parse interests into a list
        interests_list = [i.strip() for i in match_interests.split(",") if i.strip()]
        
        # Create request payload
        request_payload = {
            "image1": image1_base64,
            "image2": image2_base64,
            "user_bio": user_bio,
            "match_bio": {
                "name": match_name,
                "age": match_age,
                "bio": match_bio,
                "interests": interests_list
            },
            "sentence_count": sentence_count,
            "tone": tone,
            "creativity": creativity
        }
        
        # Show the request JSON (without the full base64 strings for readability)
        display_request = request_payload.copy()
        display_request["image1"] = "[base64 image data...]"
        display_request["image2"] = "[base64 image data...]"
        
        st.code(json.dumps(display_request, indent=2), language="json")
        
        # Send request button
        if st.button("Send Request to API", type="primary"):
            with st.spinner("Sending request to FirstChat API..."):
                try:
                    # Make the API request
                    response = requests.post(
                        api_url,
                        json=request_payload,
                        headers={"Content-Type": "application/json"},
                        timeout=30
                    )
                    
                    # Display response
                    st.header("API Response")
                    
                    # Handle different response status codes
                    if response.status_code == 200:
                        response_data = response.json()
                        
                        # Show success response
                        st.success(f"Request successful! Status code: {response.status_code}")
                        
                        # Show generated message in a highlighted box
                        st.subheader("Generated Message")
                        st.info(response_data["data"]["generated_message"])
                        
                        # Show image tags
                        if "image_tags" in response_data["data"]:
                            st.subheader("Image Tags")
                            tags = response_data["data"]["image_tags"]
                            st.write(", ".join(tags))
                        
                        # Show token usage
                        if "token_usage" in response_data["data"]:
                            st.subheader("Token Usage")
                            token_usage = response_data["data"]["token_usage"]
                            st.text(f"Prompt tokens: {token_usage['prompt_tokens']}")
                            st.text(f"Completion tokens: {token_usage['completion_tokens']}")
                            st.text(f"Total tokens: {token_usage['total_tokens']}")
                        
                        # Show processing time
                        if "processing_time" in response_data:
                            st.text(f"Processing time: {response_data['processing_time']:.2f} seconds")
                        
                        # Show full JSON response in expandable section
                        with st.expander("View full JSON response"):
                            st.code(json.dumps(response_data, indent=2), language="json")
                    else:
                        # Show error response
                        st.error(f"Request failed with status code: {response.status_code}")
                        st.code(response.text)
                
                except Exception as e:
                    st.error(f"Error connecting to the API: {str(e)}")
                    st.warning("Make sure the API server is running at the specified URL.")
    else:
        st.warning("Please upload both images to create the API request.")
        
# Add information about how to run the API
st.markdown("---")
st.header("Running the API")
st.markdown("""
To use this test interface, make sure the FirstChat API is running:

```bash
cd /home/roman-slack/FirstChat_BackEnd/servers/rest_firstchat_api
python app.py
```

Then you can run this Streamlit interface:

```bash
streamlit run tests/streamlit_tester.py
```
""")

# Add the requirements for running this tester
st.sidebar.markdown("---")
st.sidebar.header("Requirements")
st.sidebar.code("pip install streamlit pillow requests")