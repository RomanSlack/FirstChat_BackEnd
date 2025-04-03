"""
flask_first_chat.py

A practical "dating assist" product that generates a first chat message by processing:
- Two image files (analyzed via Google Cloud Vision for production-level image context)
- A user's bio (text)
- A match's bio (JSON string)

The Flask server exposes a web UI at "/" and an API endpoint at "/generate_message".

Usage (Web UI):
--------------
1. Run the script:
   python flask_first_chat.py
2. Open your browser at http://localhost:5000
3. Fill out the form with two images, your bio, and the match bio JSON, then click "Generate Message".

Usage (API via cURL):
----------------------
curl -X POST \
  -F "image1=@/path/to/image1.jpg" \
  -F "image2=@/path/to/image2.jpg" \
  -F "user_bio=I love hiking and coffee." \
  -F "match_bio_json={\"name\":\"Alice\",\"age\":28,\"bio\":\"Loves hiking and coffee.\"}" \
  http://localhost:5000/generate_message

Dependencies:
-------------
pip install flask openai Pillow google-cloud-vision

Ensure the environment variables are set:
  - GOOGLE_APPLICATION_CREDENTIALS (path to your Google Cloud service account JSON)
  - OPENAI_API_KEY (your OpenAI API key)

This product is built for practical use, prioritizing good results, low latency, and cost efficiency.
"""

import os
import json
from flask import Flask, request, jsonify, render_template_string, redirect, url_for
from PIL import Image
import openai
from openai import OpenAI  # New API client interface from OpenAI
from google.cloud import vision

app = Flask(__name__)

# HTML template for the home page (form for uploading images and bios)
INDEX_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Dating Assist - First Message Generator</title>
    <style>
      body { font-family: Arial, sans-serif; background-color: #f2f2f2; margin: 0; padding: 20px; }
      .container { max-width: 600px; margin: auto; background: white; padding: 20px; border-radius: 8px; }
      label { display: block; margin-top: 10px; }
      input[type="file"], textarea, input[type="text"] { width: 100%; padding: 8px; margin-top: 5px; }
      input[type="submit"] { margin-top: 15px; padding: 10px 20px; background-color: #4CAF50; color: white; border: none; border-radius: 4px; cursor: pointer; }
      input[type="submit"]:hover { background-color: #45a049; }
    </style>
</head>
<body>
    <div class="container">
      <h2>Dating Assist - First Message Generator</h2>
      <form action="{{ url_for('generate_message') }}" method="POST" enctype="multipart/form-data">
          <label for="image1">Image 1:</label>
          <input type="file" name="image1" id="image1" accept="image/*" required>
          
          <label for="image2">Image 2:</label>
          <input type="file" name="image2" id="image2" accept="image/*" required>
          
          <label for="user_bio">Your Bio:</label>
          <textarea name="user_bio" id="user_bio" rows="3" placeholder="Enter your bio..." required></textarea>
          
          <label for="match_bio_json">Match Bio (JSON):</label>
          <textarea name="match_bio_json" id="match_bio_json" rows="3" placeholder='e.g. {"name": "Alice", "age": 28, "bio": "Loves hiking and coffee."}' required></textarea>
          
          <input type="submit" value="Generate Message">
      </form>
    </div>
</body>
</html>
"""

# HTML template for the result page.
RESULT_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Generated Message</title>
    <style>
      body { font-family: Arial, sans-serif; background-color: #f2f2f2; margin: 0; padding: 20px; }
      .container { max-width: 600px; margin: auto; background: white; padding: 20px; border-radius: 8px; }
      .message { font-size: 1.2em; margin-top: 20px; padding: 15px; background: #e7f3fe; border: 1px solid #b3d7ff; border-radius: 4px; }
      a { text-decoration: none; color: #007BFF; }
    </style>
</head>
<body>
    <div class="container">
      <h2>Your Generated Message</h2>
      <div class="message">{{ generated_message }}</div>
      <p><a href="{{ url_for('index') }}">Generate Another Message</a></p>
    </div>
</body>
</html>
"""

def analyze_image(image_file):
    """
    Production-level image analysis using Google Cloud Vision API.
    Reads the image file and returns descriptive text based on detected labels and landmarks.
    """
    try:
        # Initialize the Vision API client.
        client = vision.ImageAnnotatorClient()
        content = image_file.read()
        image = vision.Image(content=content)

        # Perform label detection.
        label_response = client.label_detection(image=image)
        labels = label_response.label_annotations
        label_descriptions = [label.description for label in labels[:3]]  # top 3 labels

        # Perform landmark detection.
        landmark_response = client.landmark_detection(image=image)
        landmarks = landmark_response.landmark_annotations
        landmark_descriptions = [landmark.description for landmark in landmarks] if landmarks else []

        # Optionally, perform web detection for additional context.
        web_response = client.web_detection(image=image)
        web_detection = web_response.web_detection
        web_entities = web_detection.web_entities
        web_descriptions = [entity.description for entity in web_entities if entity.description] if web_entities else []

        # Merge all descriptive texts, remove duplicates.
        descriptions = list(set(label_descriptions + landmark_descriptions + web_descriptions))
        # For brevity, return the top 3 descriptions.
        return descriptions[:3]
    except Exception as e:
        print("Error analyzing image with Google Cloud Vision:", e)
        return ["unknown"]

@app.route("/", methods=["GET"])
def index():
    return render_template_string(INDEX_HTML)

@app.route("/generate_message", methods=["POST"])
def generate_message():
    # Check that both image files are provided.
    if 'image1' not in request.files or 'image2' not in request.files:
        return jsonify({"status": "error", "error": "Missing one or both image files."}), 400

    image1 = request.files['image1']
    image2 = request.files['image2']

    # Get the user_bio and match_bio_json from the form data.
    user_bio = request.form.get("user_bio")
    match_bio_json = request.form.get("match_bio_json")
    if not user_bio or not match_bio_json:
        return jsonify({"status": "error", "error": "Missing user_bio or match_bio_json."}), 400

    try:
        match_bio = json.loads(match_bio_json)
    except Exception as e:
        return jsonify({"status": "error", "error": "Invalid match_bio_json format."}), 400

    # Analyze each image using Google Cloud Vision.
    tags1 = analyze_image(image1)
    # Reset pointer if needed.
    image1.seek(0)
    tags2 = analyze_image(image2)
    # Merge and deduplicate descriptions.
    image_descriptions = list(set(tags1 + tags2))
    image_context = ", ".join(image_descriptions)

    # Construct a concise prompt for the OpenAI API.
    prompt = (
        f"User Bio: {user_bio}\n"
        f"Match Bio: {match_bio.get('bio', '')}\n"
        f"Image context: {image_context}\n"
        "Generate a short, friendly first message that references these details."
    )

    # Ensure the OpenAI API key is set.
    openai_api_key = os.environ.get("OPENAI_API_KEY")
    if not openai_api_key:
        return jsonify({"status": "error", "error": "OPENAI_API_KEY not set in environment."}), 500

    # Initialize the OpenAI client using the new API interface.
    client = OpenAI(api_key=openai_api_key)

    try:
        # Use the new chat completions API call.
        completion = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a friendly chat message generator."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=60,
            temperature=0.7,
        )
        generated_message = completion.choices[0].message.content.strip()
    except Exception as e:
        return jsonify({"status": "error", "error": f"OpenAI API error: {e}"}), 500

    # Return JSON if the client accepts JSON; otherwise, render the result page.
    if "application/json" in request.headers.get("Accept", ""):
        return jsonify({"status": "success", "data": {"generated_message": generated_message}})
    else:
        return render_template_string(RESULT_HTML, generated_message=generated_message)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
