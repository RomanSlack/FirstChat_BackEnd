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
import base64
from flask import Flask, request, jsonify, render_template_string, redirect, url_for
from PIL import Image
import io
import openai
from openai import OpenAI  # New API client interface from OpenAI
from google.cloud import vision

app = Flask(__name__)

# HTML template for the home page with improved UI/UX
INDEX_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Dating Assist - First Message Generator</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600&display=swap" rel="stylesheet">
    <style>
      body { 
        font-family: 'Poppins', sans-serif;
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        margin: 0;
        padding: 20px;
        min-height: 100vh;
      }
      .container {
        max-width: 800px;
        margin: 20px auto;
        background: white;
        padding: 30px;
        border-radius: 16px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.1);
      }
      h2 {
        color: #4a6ee0;
        text-align: center;
        margin-bottom: 30px;
      }
      .form-group {
        margin-bottom: 25px;
      }
      label {
        display: block;
        margin-bottom: 8px;
        font-weight: 500;
        color: #333;
      }
      textarea, input[type="text"], select {
        width: 100%;
        padding: 12px;
        border: 1px solid #ddd;
        border-radius: 8px;
        font-family: inherit;
        transition: border 0.3s;
        box-sizing: border-box;
      }
      textarea:focus, input[type="text"]:focus, select:focus {
        border-color: #4a6ee0;
        outline: none;
      }
      .drop-area {
        padding: 40px 20px;
        border: 2px dashed #cbd5e0;
        border-radius: 8px;
        text-align: center;
        cursor: pointer;
        transition: all 0.3s;
        margin-bottom: 10px;
        background: #f9fafc;
      }
      .drop-area:hover, .drop-area.highlight {
        border-color: #4a6ee0;
        background: #f0f5ff;
      }
      .drop-area p {
        margin: 0;
        color: #718096;
      }
      .image-preview {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
        gap: 10px;
        margin-top: 15px;
      }
      .image-preview .preview-item {
        position: relative;
        height: 150px;
        border-radius: 8px;
        overflow: hidden;
      }
      .image-preview img {
        width: 100%;
        height: 100%;
        object-fit: cover;
      }
      .image-preview .remove-btn {
        position: absolute;
        top: 5px;
        right: 5px;
        background: rgba(255,255,255,0.8);
        border: none;
        width: 25px;
        height: 25px;
        border-radius: 50%;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: bold;
        color: #f56565;
      }
      .form-row {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 15px;
      }
      .match-bio-form {
        background: #f9fafc;
        padding: 20px;
        border-radius: 8px;
        border: 1px solid #e2e8f0;
        margin-top: 10px;
      }
      .json-preview {
        background: #2d3748;
        color: #e2e8f0;
        padding: 15px;
        border-radius: 8px;
        font-family: monospace;
        white-space: pre-wrap;
        margin-top: 15px;
        font-size: 14px;
        height: 100px;
        overflow-y: auto;
      }
      .btn {
        padding: 12px 25px;
        background-color: #4a6ee0;
        color: white;
        border: none;
        border-radius: 8px;
        cursor: pointer;
        font-size: 16px;
        font-weight: 500;
        transition: all 0.3s;
        width: 100%;
      }
      .btn:hover {
        background-color: #3758ca;
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(0,0,0,0.1);
      }
      .btn:active {
        transform: translateY(0);
      }
      .btn-secondary {
        background-color: #718096;
      }
      .btn-secondary:hover {
        background-color: #4a5568;
      }
      .error {
        color: #e53e3e;
        margin-top: 5px;
        font-size: 14px;
      }
      @media (max-width: 768px) {
        .form-row {
          grid-template-columns: 1fr;
        }
      }
      .tabs {
        display: flex;
        margin-bottom: 20px;
        border-bottom: 1px solid #e2e8f0;
      }
      .tab {
        padding: 10px 20px;
        cursor: pointer;
        border-bottom: 2px solid transparent;
        margin-right: 10px;
      }
      .tab.active {
        border-bottom-color: #4a6ee0;
        color: #4a6ee0;
        font-weight: 500;
      }
    </style>
</head>
<body>
    <div class="container">
      <h2>Dating Assist - First Message Generator</h2>
      <form id="messageForm" action="{{ url_for('generate_message') }}" method="POST" enctype="multipart/form-data">
          <div class="form-group">
              <label>Upload Images (select or drag multiple images)</label>
              <div id="dropArea" class="drop-area">
                  <p>Drag & drop images here or click to select files</p>
                  <p style="margin-top: 10px; font-size: 14px; color: #4a6ee0;">Select at least 2 images</p>
                  <input type="file" id="imageInput" name="images[]" multiple accept="image/*" style="display:none">
              </div>
              <div id="imagePreview" class="image-preview"></div>
              <div id="imageError" class="error"></div>
              <input type="hidden" id="image1" name="image1">
              <input type="hidden" id="image2" name="image2">
          </div>
          
          <div class="form-group">
              <label for="user_bio">Your Bio:</label>
              <textarea name="user_bio" id="user_bio" rows="3" placeholder="Enter your bio..." required>Hi, I'm a 22-year-old guy who loves hiking, photography, and trying new coffee shops. I work in tech and enjoy weekend adventures. Looking for someone to share good conversations and outdoor activities.</textarea>
          </div>
          
          <div class="form-group">
              <label for="match_bio_section">Match Bio:</label>
              <div class="tabs">
                <div class="tab active" data-tab="form">Form Input</div>
                <div class="tab" data-tab="json">JSON Input</div>
              </div>
              <p style="margin: 5px 0; font-size: 12px; color: #666;">Default values are pre-filled for quick testing. You can modify them or proceed directly to uploading images.</p>
              
              <div id="match-bio-form" class="match-bio-form">
                <div class="form-row">
                  <div class="form-group">
                    <label for="match_name">Name:</label>
                    <input type="text" id="match_name" placeholder="Name" value="Emma">
                  </div>
                  <div class="form-group">
                    <label for="match_age">Age:</label>
                    <input type="text" id="match_age" placeholder="Age" value="21">
                  </div>
                </div>
                <div class="form-group">
                  <label for="match_bio">Bio:</label>
                  <textarea id="match_bio" rows="3" placeholder="Enter match's bio...">Hey there! I'm a 21-year-old student majoring in environmental science. Love exploring nature trails, capturing sunsets, and finding hidden coffee gems. Always up for a good book recommendation or a spontaneous adventure!</textarea>
                </div>
                <div class="form-group">
                  <label for="match_interests">Interests (comma separated):</label>
                  <input type="text" id="match_interests" placeholder="travelling, coffee, hiking" value="hiking, photography, coffee, reading, nature, travel">
                </div>
              </div>
              
              <div id="json-input" style="display:none;">
                <textarea name="match_bio_json" id="match_bio_json" rows="5" placeholder='{"name": "Alice", "age": 28, "bio": "Loves hiking and coffee.", "interests": ["travelling", "coffee", "hiking"]}'></textarea>
              </div>
              
              <div class="json-preview" id="json-preview"></div>
          </div>
          
          <button type="submit" class="btn">Generate Message</button>
      </form>
    </div>
    
    <script>
      document.addEventListener('DOMContentLoaded', function() {
        // Drop area functionality
        const dropArea = document.getElementById('dropArea');
        const imageInput = document.getElementById('imageInput');
        const imagePreview = document.getElementById('imagePreview');
        const imageError = document.getElementById('imageError');
        const image1Input = document.getElementById('image1');
        const image2Input = document.getElementById('image2');
        const form = document.getElementById('messageForm');
        const matchBioJson = document.getElementById('match_bio_json');
        
        // Auto-fill match bio JSON on load
        updateJsonFromForm();
        
        // Prevent default drag behaviors
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
          dropArea.addEventListener(eventName, preventDefaults, false);
          document.body.addEventListener(eventName, preventDefaults, false);
        });
        
        // Highlight drop area when dragging over it
        ['dragenter', 'dragover'].forEach(eventName => {
          dropArea.addEventListener(eventName, highlight, false);
        });
        
        ['dragleave', 'drop'].forEach(eventName => {
          dropArea.addEventListener(eventName, unhighlight, false);
        });
        
        // Handle dropped files
        dropArea.addEventListener('drop', handleDrop, false);
        
        // Handle click to select files
        dropArea.addEventListener('click', (e) => {
          e.preventDefault();
          e.stopPropagation();
          imageInput.click();
        });
        
        // Handle selected files
        imageInput.addEventListener('change', (e) => {
          e.preventDefault();
          if (imageInput.files && imageInput.files.length > 0) {
            handleFiles(imageInput.files);
          }
        });
        
        // Display initial status message for images
        updateHiddenInputs();
        
        // Match bio form and JSON generation
        const matchNameInput = document.getElementById('match_name');
        const matchAgeInput = document.getElementById('match_age');
        const matchBioInput = document.getElementById('match_bio');
        const matchInterestsInput = document.getElementById('match_interests');
        const matchBioJson = document.getElementById('match_bio_json');
        const jsonPreview = document.getElementById('json-preview');
        
        // Update JSON when form fields change
        [matchNameInput, matchAgeInput, matchBioInput, matchInterestsInput].forEach(input => {
          input.addEventListener('input', updateJsonFromForm);
        });
        
        // Update form when JSON changes
        matchBioJson.addEventListener('input', updateFormFromJson);
        
        // Initial JSON update
        updateJsonFromForm();
        
        // Tab switching
        const tabs = document.querySelectorAll('.tab');
        const matchBioForm = document.getElementById('match-bio-form');
        const jsonInput = document.getElementById('json-input');
        
        tabs.forEach(tab => {
          tab.addEventListener('click', () => {
            tabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            
            if (tab.dataset.tab === 'form') {
              matchBioForm.style.display = 'block';
              jsonInput.style.display = 'none';
            } else {
              matchBioForm.style.display = 'none';
              jsonInput.style.display = 'block';
            }
          });
        });
        
        // Form validation before submit
        form.addEventListener('submit', function(event) {
          // Ensure we have at least 2 images
          const imageInputs = [image1Input, image2Input];
          if (!imageInputs[0].value || !imageInputs[1].value) {
            event.preventDefault();
            imageError.textContent = 'Please upload at least 2 images';
            return false;
          }
          
          // Ensure match bio JSON is valid
          try {
            JSON.parse(matchBioJson.value);
          } catch (e) {
            event.preventDefault();
            alert('Invalid JSON format for match bio');
            return false;
          }
          
          return true;
        });
        
        // Helper functions
        function preventDefaults(e) {
          e.preventDefault();
          e.stopPropagation();
        }
        
        function highlight() {
          dropArea.classList.add('highlight');
        }
        
        function unhighlight() {
          dropArea.classList.remove('highlight');
        }
        
        function handleDrop(e) {
          console.log('File dropped');
          const dt = e.dataTransfer;
          const files = dt.files;
          if (files && files.length > 0) {
            console.log(`Dropped ${files.length} files`);
            handleFiles(files);
          } else {
            console.log('No files found in drop event');
          }
        }
        
        function handleFiles(files) {
          files = [...files];
          files = files.filter(file => file.type.startsWith('image/'));
          
          if (files.length === 0) {
            imageError.textContent = 'Please select image files only';
            return;
          }
          
          imageError.textContent = '';
          
          // Keep track of file count to limit to 10
          const fileCount = imagePreview.querySelectorAll('.preview-item').length;
          const remainingSlots = 10 - fileCount;
          const filesToProcess = files.slice(0, remainingSlots);
          
          filesToProcess.forEach((file) => {
            const reader = new FileReader();
            
            reader.onload = function(e) {
              const div = document.createElement('div');
              div.className = 'preview-item';
              
              const img = document.createElement('img');
              img.src = e.target.result;
              
              const removeBtn = document.createElement('button');
              removeBtn.className = 'remove-btn';
              removeBtn.innerHTML = '×';
              removeBtn.onclick = function(event) {
                event.preventDefault();
                event.stopPropagation();
                div.remove();
                updateHiddenInputs();
              };
              
              div.appendChild(img);
              div.appendChild(removeBtn);
              div.dataset.base64 = e.target.result;
              
              imagePreview.appendChild(div);
              updateHiddenInputs();
            };
            
            reader.readAsDataURL(file);
          });
          
          // Clear the file input so the same files can be added again if needed
          imageInput.value = '';
        }
        
        function updateHiddenInputs() {
          const previews = imagePreview.querySelectorAll('.preview-item');
          
          // Reset inputs
          image1Input.value = '';
          image2Input.value = '';
          
          // Set values for first two images
          if (previews.length > 0) {
            image1Input.value = previews[0].dataset.base64;
          }
          
          if (previews.length > 1) {
            image2Input.value = previews[1].dataset.base64;
          }
          
          // Update the validation visual feedback
          if (previews.length >= 2) {
            imageError.textContent = '';
            imageError.style.color = '#4CAF50';
            imageError.innerHTML = '✓ Images selected';
          } else {
            imageError.style.color = '#e53e3e';
            imageError.textContent = `Please select at least 2 images (${previews.length}/2 selected)`;
          }
        }
        
        function updateJsonFromForm() {
          const json = {
            name: matchNameInput.value || '',
            age: matchAgeInput.value ? parseInt(matchAgeInput.value) : '',
            bio: matchBioInput.value || '',
            interests: matchInterestsInput.value ? 
              matchInterestsInput.value.split(',').map(i => i.trim()).filter(i => i) : 
              []
          };
          
          matchBioJson.value = JSON.stringify(json, null, 2);
          jsonPreview.textContent = JSON.stringify(json, null, 2);
        }
        
        function updateFormFromJson() {
          try {
            const json = JSON.parse(matchBioJson.value);
            
            matchNameInput.value = json.name || '';
            matchAgeInput.value = json.age || '';
            matchBioInput.value = json.bio || '';
            
            if (Array.isArray(json.interests)) {
              matchInterestsInput.value = json.interests.join(', ');
            }
            
            jsonPreview.textContent = matchBioJson.value;
          } catch (e) {
            jsonPreview.textContent = 'Invalid JSON';
          }
        }
      });
    </script>
</body>
</html>
"""

# HTML template for the result page with improved styling.
RESULT_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Generated Message</title>
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600&display=swap" rel="stylesheet">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
      body { 
        font-family: 'Poppins', sans-serif;
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        margin: 0;
        padding: 20px;
        min-height: 100vh;
        display: flex;
        align-items: center;
        justify-content: center;
      }
      .container { 
        max-width: 800px;
        width: 100%;
        background: white;
        padding: 30px;
        border-radius: 16px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.1);
      }
      h2 {
        color: #4a6ee0;
        text-align: center;
        margin-bottom: 30px;
      }
      .message {
        font-size: 1.1em;
        margin: 25px 0;
        padding: 25px;
        background: #f0f5ff;
        border-left: 4px solid #4a6ee0;
        border-radius: 8px;
        line-height: 1.6;
      }
      .btn {
        display: inline-block;
        padding: 12px 25px;
        background-color: #4a6ee0;
        color: white;
        border: none;
        border-radius: 8px;
        cursor: pointer;
        font-size: 16px;
        font-weight: 500;
        text-decoration: none;
        transition: all 0.3s;
        text-align: center;
      }
      .btn:hover {
        background-color: #3758ca;
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(0,0,0,0.1);
      }
      .image-preview {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
        gap: 15px;
        margin: 20px 0;
      }
      .image-preview img {
        width: 100%;
        height: 150px;
        object-fit: cover;
        border-radius: 8px;
        box-shadow: 0 3px 10px rgba(0,0,0,0.1);
      }
      .section {
        margin-bottom: 20px;
      }
      .section-title {
        font-weight: 600;
        color: #4a5568;
        margin-bottom: 10px;
      }
      .bio {
        background: #f9fafc;
        padding: 15px;
        border-radius: 8px;
        border: 1px solid #e2e8f0;
      }
    </style>
</head>
<body>
    <div class="container">
        <h2>Your Generated Message</h2>
        
        {% if image1_data and image2_data %}
        <div class="section">
            <div class="section-title">Images Used</div>
            <div class="image-preview">
                <img src="{{ image1_data }}" alt="Image 1">
                <img src="{{ image2_data }}" alt="Image 2">
            </div>
        </div>
        {% endif %}
        
        <div class="section">
            <div class="section-title">Your Bio</div>
            <div class="bio">{{ user_bio }}</div>
        </div>
        
        <div class="section">
            <div class="section-title">Match Bio</div>
            <div class="bio">{{ match_bio_formatted }}</div>
        </div>
        
        <div class="section">
            <div class="section-title">Generated Message</div>
            <div class="message">{{ generated_message }}</div>
        </div>
        
        <div style="text-align: center; margin-top: 30px;">
            <a href="{{ url_for('index') }}" class="btn">Generate Another Message</a>
        </div>
    </div>
</body>
</html>
"""

def analyze_image(image_data):
    """
    Production-level image analysis using Google Cloud Vision API.
    Accepts base64 image data or file object and returns descriptive text.
    """
    try:
        # Initialize the Vision API client.
        client = vision.ImageAnnotatorClient()
        
        # Handle either file object or base64 data
        if isinstance(image_data, str) and image_data.startswith('data:image'):
            # Extract the base64 part
            content = base64.b64decode(image_data.split(',')[1])
        else:
            # It's a file object
            content = image_data.read()
            
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
    # Extract images from form data
    image1_data = request.form.get('image1')
    image2_data = request.form.get('image2')
    
    # Log for debugging
    print(f"Image1 data received: {bool(image1_data)}, length: {len(image1_data) if image1_data else 0}")
    print(f"Image2 data received: {bool(image2_data)}, length: {len(image2_data) if image2_data else 0}")
    
    # Check that both images are provided
    if not image1_data or not image2_data:
        if 'image1' not in request.files or 'image2' not in request.files:
            return jsonify({"status": "error", "error": "Missing one or both image files."}), 400
        
        # If not using base64, fall back to files
        image1 = request.files['image1']
        image2 = request.files['image2']
    else:
        # Using base64 data
        image1 = image1_data
        image2 = image2_data

    # Get the user_bio and match_bio_json from the form data.
    user_bio = request.form.get("user_bio")
    match_bio_json = request.form.get("match_bio_json")
    if not user_bio or not match_bio_json:
        return jsonify({"status": "error", "error": "Missing user_bio or match_bio_json."}), 400

    try:
        match_bio = json.loads(match_bio_json)
    except Exception as e:
        return jsonify({"status": "error", "error": "Invalid match_bio_json format."}), 400

    # Analyze each image using Google Cloud Vision
    tags1 = analyze_image(image1)
    
    # Reset pointer if using file objects
    if isinstance(image1, bytes) or hasattr(image1, 'read'):
        if hasattr(image1, 'seek'):
            image1.seek(0)
            
    tags2 = analyze_image(image2)
    
    # Merge and deduplicate descriptions
    image_descriptions = list(set(tags1 + tags2))
    image_context = ", ".join(image_descriptions)

    # Format the match bio for display
    match_bio_formatted = ""
    if "name" in match_bio:
        match_bio_formatted += f"Name: {match_bio['name']}<br>"
    if "age" in match_bio:
        match_bio_formatted += f"Age: {match_bio['age']}<br>"
    if "bio" in match_bio:
        match_bio_formatted += f"Bio: {match_bio['bio']}<br>"
    if "interests" in match_bio and match_bio["interests"]:
        match_bio_formatted += f"Interests: {', '.join(match_bio['interests'])}"

    # Construct a concise prompt for the OpenAI API.
    prompt = (
        f"User Bio: {user_bio}\n"
        f"Match Bio: {match_bio.get('bio', '')}\n"
        f"Match Name: {match_bio.get('name', '')}\n"
        f"Match Age: {match_bio.get('age', '')}\n"
        f"Match Interests: {', '.join(match_bio.get('interests', []))}\n"
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
        return render_template_string(
            RESULT_HTML, 
            generated_message=generated_message,
            user_bio=user_bio,
            match_bio_formatted=match_bio_formatted,
            image1_data=image1_data if isinstance(image1_data, str) else None,
            image2_data=image2_data if isinstance(image2_data, str) else None
        )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)