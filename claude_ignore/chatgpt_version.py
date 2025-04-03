"""
flask_first_chat.py

A practical "dating assist" product that generates a first chat message by processing:
- Two image files (for minimal image analysis)
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
pip install flask openai Pillow

Ensure the environment variable OPENAI_API_KEY is set. For example:
  export OPENAI_API_KEY="your_openai_api_key_here"

This product is built for practical use, prioritizing good results, low latency, and cost efficiency.
"""

import os
import json
from flask import Flask, request, jsonify, render_template_string, redirect, url_for
from PIL import Image
import openai
from openai import OpenAI  # New style: use OpenAI client from the OpenAI package

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
    Minimal image analysis using Pillow.
    This function loads the image and returns a dummy tag list.
    For production, integrate a lightweight pre-trained model.
    """
    try:
        img = Image.open(image_file)
        width, height = img.size
        tag = "landscape" if width > height else "portrait"
        return [tag]
    except Exception as e:
        print("Error processing image:", e)
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

    # Perform minimal image analysis on both images.
    tags1 = analyze_image(image1)
    # Reset the pointer if needed.
    image1.seek(0)
    tags2 = analyze_image(image2)
    tags = list(set(tags1 + tags2))
    tags_str = ", ".join(tags)

    # Construct a concise prompt for the OpenAI API.
    prompt = (
        f"User Bio: {user_bio}\n"
        f"Match Bio: {match_bio.get('bio', '')}\n"
        f"Image tags: {tags_str}\n"
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
            model="gpt-3.5-turbo",  # You may change to another model if desired.
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
    # Run the Flask server on port 5000.
    app.run(host="0.0.0.0", port=5000, debug=True)
