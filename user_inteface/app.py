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
      .slider-container {
        margin-top: 15px;
      }
      .slider {
        -webkit-appearance: none;
        width: 100%;
        height: 8px;
        background: #d3d3d3;
        outline: none;
        opacity: 0.7;
        -webkit-transition: .2s;
        transition: opacity .2s;
        border-radius: 5px;
      }
      .slider:hover {
        opacity: 1;
      }
      .slider::-webkit-slider-thumb {
        -webkit-appearance: none;
        appearance: none;
        width: 20px;
        height: 20px;
        background: #4a6ee0;
        cursor: pointer;
        border-radius: 50%;
      }
      .slider::-moz-range-thumb {
        width: 20px;
        height: 20px;
        background: #4a6ee0;
        cursor: pointer;
        border-radius: 50%;
      }
      .slider-value {
        text-align: center;
        font-weight: 500;
        margin-top: 8px;
        color: #4a6ee0;
      }
      .tone-selector {
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
        margin-top: 10px;
      }
      .tone-option {
        flex: 1 0 auto;
        padding: 8px 15px;
        background: #f0f5ff;
        border: 1px solid #d1ddfb;
        border-radius: 20px;
        text-align: center;
        cursor: pointer;
        transition: all 0.2s;
        font-size: 14px;
        min-width: 80px;
      }
      .tone-option:hover {
        background: #e1eaff;
        border-color: #4a6ee0;
      }
      .tone-option.selected {
        background: #4a6ee0;
        color: white;
        border-color: #3758ca;
      }
      .creativity-container {
        display: flex;
        align-items: center;
        gap: 15px;
      }
      .creativity-container .slider-container {
        flex: 1;
      }
      .creativity-labels {
        display: flex;
        justify-content: space-between;
        margin-top: 5px;
        font-size: 12px;
        color: #718096;
      }
      .loading-overlay {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0,0,0,0.5);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 1000;
        display: none;
      }
      .loading-content {
        background: white;
        padding: 30px;
        border-radius: 10px;
        text-align: center;
        box-shadow: 0 5px 15px rgba(0,0,0,0.2);
      }
      .spinner {
        border: 5px solid #f3f3f3;
        border-top: 5px solid #4a6ee0;
        border-radius: 50%;
        width: 50px;
        height: 50px;
        animation: spin 1s linear infinite;
        margin: 0 auto 20px;
      }
      @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
      }
      .tag-preview {
        background: #f9fafc;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 10px;
        margin-top: 10px;
        font-size: 14px;
      }
      .tag-item {
        display: inline-block;
        background: #e1eaff;
        color: #3758ca;
        padding: 3px 8px;
        border-radius: 12px;
        margin: 2px;
        font-size: 12px;
      }
      .tag-header {
        font-weight: 500;
        margin-bottom: 5px;
        color: #4a5568;
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
              <label>Upload Images (drag & drop or click to select)</label>
              <div id="dropArea" class="drop-area">
                  <p>Drag & drop images here or click to select files</p>
                  <p style="margin-top: 10px; font-size: 14px; color: #4a6ee0;">Select at least 2 images</p>
                  <input type="file" id="imageInput" multiple accept="image/*" style="display:none">
              </div>
              <div id="imagePreview" class="image-preview"></div>
              <div id="imageError" class="error"></div>
              <div id="tagPreview" class="tag-preview" style="display: none;">
                  <div class="tag-header">Detected tags:</div>
                  <div id="tagContent"></div>
              </div>
              <!-- Hidden inputs to send base64 image data -->
              <input type="hidden" id="image1" name="image1">
              <input type="hidden" id="image2" name="image2">
          </div>
          
          <div class="form-group">
              <label for="user_bio">Your Bio:</label>
              <textarea name="user_bio" id="user_bio" rows="3" placeholder="Enter your bio..." required>
Hey, I’m a 25-year-old architect with a passion for design, travel, and street food. I spend my weekends exploring cities, sketching buildings, and hanging out with my rescue dog, Milo. Looking for someone curious, creative, and down for spontaneous adventures or laid-back park days with the pup.</textarea>
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
          
          <div class="form-group">
              <label for="sentence_count">Message Length:</label>
              <div class="slider-container">
                  <input type="range" min="1" max="5" value="2" class="slider" id="sentence_count" name="sentence_count">
                  <div class="slider-value" id="sentence_value">2 sentences</div>
              </div>
          </div>
          
          <div class="form-group">
              <label for="tone">Message Tone:</label>
              <div class="tone-selector" id="toneSelector">
                  <div class="tone-option selected" data-tone="friendly">Friendly</div>
                  <div class="tone-option" data-tone="witty">Witty</div>
                  <div class="tone-option" data-tone="flirty">Flirty</div>
                  <div class="tone-option" data-tone="casual">Casual</div>
                  <div class="tone-option" data-tone="confident">Confident</div>
                  <div class="tone-option" data-tone="unhinged">Unhinged</div>
              </div>
              <input type="hidden" id="tone" name="tone" value="friendly">
          </div>
          
          <div class="form-group">
              <label for="creativity">Creativity Level:</label>
              <div class="creativity-container">
                  <div class="slider-container">
                      <input type="range" min="0" max="10" value="7" class="slider" id="creativity" name="creativity">
                      <div class="creativity-labels">
                          <span>Conservative</span>
                          <span>Balanced</span>
                          <span>Creative</span>
                      </div>
                  </div>
                  <div class="slider-value" id="creativity_value">0.7</div>
              </div>
          </div>
          
          <button type="submit" class="btn">Generate Message</button>
      </form>
    </div>
    
    <script>
      document.addEventListener('DOMContentLoaded', function() {
        // Sentence slider functionality
        const sentenceSlider = document.getElementById('sentence_count');
        const sentenceValue = document.getElementById('sentence_value');
        const creativitySlider = document.getElementById('creativity');
        const creativityValue = document.getElementById('creativity_value');
        const loadingOverlay = document.getElementById('loadingOverlay');
        const loadingMessage = document.getElementById('loadingMessage');
        const tagPreview = document.getElementById('tagPreview');
        const tagContent = document.getElementById('tagContent');
        const toneSelector = document.getElementById('toneSelector');
        const toneInput = document.getElementById('tone');
        
        // Tone selector functionality
        if (toneSelector) {
          const toneOptions = toneSelector.querySelectorAll('.tone-option');
          toneOptions.forEach(option => {
            option.addEventListener('click', function() {
              toneOptions.forEach(o => o.classList.remove('selected'));
              this.classList.add('selected');
              toneInput.value = this.dataset.tone;
            });
          });
        }
        
        // Creativity slider functionality
        if (creativitySlider) {
          creativitySlider.oninput = function() {
            const value = parseInt(this.value) / 10;
            creativityValue.textContent = value.toFixed(1);
          };
        }
        
        // Sentence slider functionality
        sentenceSlider.oninput = function() {
          sentenceValue.textContent = this.value + (this.value === '1' ? ' sentence' : ' sentences');
        }
        const dropArea = document.getElementById('dropArea');
        const imageInput = document.getElementById('imageInput');
        const imagePreview = document.getElementById('imagePreview');
        const imageError = document.getElementById('imageError');
        const image1Input = document.getElementById('image1');
        const image2Input = document.getElementById('image2');
        const form = document.getElementById('messageForm');
        
        // Match bio fields and JSON preview
        const matchNameInput = document.getElementById('match_name');
        const matchAgeInput = document.getElementById('match_age');
        const matchBioInput = document.getElementById('match_bio');
        const matchInterestsInput = document.getElementById('match_interests');
        const matchBioJson = document.getElementById('match_bio_json');
        const jsonPreview = document.getElementById('json-preview');
        
        // Prevent default drag behaviors
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
          dropArea.addEventListener(eventName, preventDefaults, false);
          document.body.addEventListener(eventName, preventDefaults, false);
        });
        
        // Highlight drop area when dragging over it
        ['dragenter', 'dragover'].forEach(eventName => {
          dropArea.addEventListener(eventName, () => dropArea.classList.add('highlight'), false);
        });
        
        ['dragleave', 'drop'].forEach(eventName => {
          dropArea.addEventListener(eventName, () => dropArea.classList.remove('highlight'), false);
        });
        
        // Handle dropped files
        dropArea.addEventListener('drop', handleDrop, false);
        
        // Handle dropped files function
        function handleDrop(e) {
          if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
            handleFiles(e.dataTransfer.files);
          }
        }
        
        // Handle click to open file dialog
        dropArea.addEventListener('click', (e) => {
          e.preventDefault();
          imageInput.click();
        });
        
        // Handle file input change event
        imageInput.addEventListener('change', (e) => {
          if (imageInput.files && imageInput.files.length > 0) {
            handleFiles(imageInput.files);
          }
        });
        
        // Process dropped or selected files
        function handleFiles(files) {
          files = Array.from(files).filter(file => file.type.startsWith('image/'));
          if (files.length === 0) {
            imageError.textContent = 'Please select image files only';
            return;
          }
          imageError.textContent = '';
          const currentCount = imagePreview.querySelectorAll('.preview-item').length;
          const remainingSlots = 10 - currentCount;
          const filesToProcess = files.slice(0, remainingSlots);
          
          filesToProcess.forEach(file => {
            const reader = new FileReader();
            reader.onload = (e) => {
              const div = document.createElement('div');
              div.className = 'preview-item';
              const img = document.createElement('img');
              img.src = e.target.result;
              const removeBtn = document.createElement('button');
              removeBtn.className = 'remove-btn';
              removeBtn.innerHTML = '×';
              removeBtn.onclick = (event) => {
                event.preventDefault();
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
          imageInput.value = '';
        }
        
        // Update hidden inputs with base64 data for the first two images
        function updateHiddenInputs() {
          const previews = imagePreview.querySelectorAll('.preview-item');
          image1Input.value = previews.length > 0 ? previews[0].dataset.base64 : '';
          image2Input.value = previews.length > 1 ? previews[1].dataset.base64 : '';
          
          if (previews.length >= 2) {
            imageError.style.color = '#4CAF50';
            imageError.textContent = '✓ Images selected';
          } else {
            imageError.style.color = '#e53e3e';
            imageError.textContent = `Please select at least 2 images (${previews.length}/2 selected)`;
          }
        }
        
        // Update JSON preview from match bio form
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
        
        // Update form from JSON input (if edited manually)
        function updateFormFromJson() {
          try {
            const json = JSON.parse(matchBioJson.value);
            matchNameInput.value = json.name || '';
            matchAgeInput.value = json.age || '';
            matchBioInput.value = json.bio || '';
            matchInterestsInput.value = Array.isArray(json.interests) ? json.interests.join(', ') : '';
            jsonPreview.textContent = matchBioJson.value;
          } catch (e) {
            jsonPreview.textContent = 'Invalid JSON';
          }
        }
        
        // Attach input listeners for match bio fields
        [matchNameInput, matchAgeInput, matchBioInput, matchInterestsInput].forEach(input => {
          input.addEventListener('input', updateJsonFromForm);
        });
        matchBioJson.addEventListener('input', updateFormFromJson);
        updateJsonFromForm();
        
        // Show mock image tag analysis for immediate feedback
        function showMockTagAnalysis(file) {
          // Simple client-side tag mockup to enhance UX while real processing happens on server
          const mockTags = ['person', 'nature', 'outdoors', 'portrait', 'travel', 'photography', 'smile', 'landscape'];
          const randomTags = [];
          // Select 2-3 random tags
          for (let i = 0; i < Math.floor(Math.random() * 2) + 2; i++) {
            const tag = mockTags[Math.floor(Math.random() * mockTags.length)];
            if (!randomTags.includes(tag)) randomTags.push(tag);
          }
          
          // Display the mock tags
          tagContent.innerHTML = '';
          randomTags.forEach(tag => {
            const tagElement = document.createElement('span');
            tagElement.className = 'tag-item';
            tagElement.textContent = tag;
            tagContent.appendChild(tagElement);
          });
          
          tagPreview.style.display = 'block';
        }
        
        // Update the handleFiles function to show mock tags
        const originalHandleFiles = handleFiles;
        handleFiles = function(files) {
          originalHandleFiles(files);
          if (files.length > 0) {
            showMockTagAnalysis(files[0]);
          }
        };
        
        // Form validation on submit
        form.addEventListener('submit', function(event) {
          if (!image1Input.value || !image2Input.value) {
            event.preventDefault();
            imageError.textContent = 'Please upload at least 2 images';
            return false;
          }
          try {
            JSON.parse(matchBioJson.value);
          } catch (e) {
            event.preventDefault();
            alert('Invalid JSON format for match bio');
            return false;
          }
          
          // Show loading overlay
          loadingOverlay.style.display = 'flex';
          loadingMessage.textContent = 'Analyzing images and generating message...';
          
          return true;
        });
        
        function preventDefaults(e) {
          e.preventDefault();
          e.stopPropagation();
        }
      });
    </script>
    <div class="loading-overlay" id="loadingOverlay">
        <div class="loading-content">
            <div class="spinner"></div>
            <p id="loadingMessage">Analyzing images...</p>
        </div>
    </div>
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
            <div class="bio">{{ match_bio_formatted|safe }}</div>
        </div>
        
        <div class="section">
            <div class="section-title">Image Context</div>
            <div class="bio">
                {% if image_tags %}
                <div style="margin-bottom: 10px;">
                    {% for tag in image_tags %}
                    <span style="display: inline-block; background: #e1eaff; color: #3758ca; padding: 3px 8px; border-radius: 12px; margin: 2px; font-size: 12px;">{{ tag }}</span>
                    {% endfor %}
                </div>
                {% endif %}
            </div>
        </div>
        
        <div class="section">
            <div class="section-title">Message Settings</div>
            <div class="bio">
                <strong>Length:</strong> {{ sentence_count }} sentence(s)<br>
                <strong>Tone:</strong> {{ tone|capitalize }}<br>
                <strong>Creativity:</strong> {{ creativity }}
            </div>
        </div>
        
        <div class="section">
            <div class="section-title">Token Usage</div>
            <div class="bio">
                <div style="display: flex; align-items: center; margin-bottom: 10px;">
                    <div style="flex: 1; height: 8px; background: #e2e8f0; border-radius: 4px; overflow: hidden; margin-right: 10px;">
                        <div style="height: 100%; width: {{ (completion_tokens / total_tokens * 100)|round }}%; background: #4a6ee0;"></div>
                    </div>
                    <div style="font-size: 13px; color: #4a5568; min-width: 100px; text-align: right;">
                        {{ completion_tokens }} / {{ total_tokens }}
                    </div>
                </div>
                <div style="font-size: 13px; color: #718096;">
                    <strong>Prompt tokens:</strong> {{ prompt_tokens }} &nbsp;&nbsp; 
                    <strong>Response tokens:</strong> {{ completion_tokens }} &nbsp;&nbsp;
                    <strong>Total:</strong> {{ total_tokens }}
                </div>
            </div>
        </div>
        
        <div class="section">
            <div class="section-title">Generated Message</div>
            <div class="message">{{ generated_message }}</div>
        </div>
        
        <div style="text-align: center; margin-top: 30px; display: flex; gap: 15px; justify-content: center;">
            <a href="{{ url_for('index') }}" class="btn" style="background-color: #718096; width: auto;">← Back</a>
            <a href="{{ url_for('index') }}" class="btn" style="width: auto;">Generate Another Message</a>
        </div>
    </div>
</body>
</html>
"""

def analyze_image(image_data):
    """
    Production-level image analysis using Google Cloud Vision API.
    Accepts base64 image data (string) or file object and returns descriptive text.
    """
    try:
        client = vision.ImageAnnotatorClient()
        if isinstance(image_data, str) and image_data.startswith('data:image'):
            content = base64.b64decode(image_data.split(',')[1])
        else:
            content = image_data.read()
        image = vision.Image(content=content)
        label_response = client.label_detection(image=image)
        labels = label_response.label_annotations
        label_descriptions = [label.description for label in labels[:3]]
        landmark_response = client.landmark_detection(image=image)
        landmarks = landmark_response.landmark_annotations
        landmark_descriptions = [landmark.description for landmark in landmarks] if landmarks else []
        web_response = client.web_detection(image=image)
        web_detection = web_response.web_detection
        web_entities = web_detection.web_entities
        web_descriptions = [entity.description for entity in web_entities if entity.description] if web_entities else []
        descriptions = list(set(label_descriptions + landmark_descriptions + web_descriptions))
        return descriptions[:3]
    except Exception as e:
        print("Error analyzing image with Google Cloud Vision:", e)
        return ["unknown"]

@app.route("/", methods=["GET"])
def index():
    return render_template_string(INDEX_HTML)

@app.route("/generate_message", methods=["POST"])
def generate_message():
    # Retrieve base64 data from hidden inputs
    image1_data = request.form.get('image1')
    image2_data = request.form.get('image2')

    # If not provided via hidden inputs, check file uploads
    if not image1_data or not image2_data:
        if 'image1' in request.files and 'image2' in request.files:
            image1_data = request.files['image1'].read()
            image2_data = request.files['image2'].read()
            # Convert to base64 for consistent handling
            image1_data = "data:image/jpeg;base64," + base64.b64encode(image1_data).decode('utf-8')
            image2_data = "data:image/jpeg;base64," + base64.b64encode(image2_data).decode('utf-8')
        else:
            return jsonify({"status": "error", "error": "Missing image data."}), 400

    user_bio = request.form.get("user_bio")
    match_bio_json = request.form.get("match_bio_json")
    if not user_bio or not match_bio_json:
        return jsonify({"status": "error", "error": "Missing user_bio or match_bio_json."}), 400

    try:
        match_bio = json.loads(match_bio_json)
    except Exception as e:
        return jsonify({"status": "error", "error": "Invalid match_bio_json format."}), 400

    tags1 = analyze_image(image1_data)
    tags2 = analyze_image(image2_data)
    image_descriptions = list(set(tags1 + tags2))
    image_context = ", ".join(image_descriptions)
    
    # Print image annotation details to console for debugging
    print("=== IMAGE ANNOTATION DETAILS ===")
    print(f"Image 1 tags: {tags1}")
    print(f"Image 2 tags: {tags2}")
    print(f"Combined image context: {image_context}")
    print("===============================")

    # Format match bio for display
    match_bio_formatted = ""
    if "name" in match_bio:
        match_bio_formatted += f"Name: {match_bio['name']}<br>"
    if "age" in match_bio:
        match_bio_formatted += f"Age: {match_bio['age']}<br>"
    if "bio" in match_bio:
        match_bio_formatted += f"Bio: {match_bio['bio']}<br>"
    if "interests" in match_bio and match_bio["interests"]:
        match_bio_formatted += f"Interests: {', '.join(match_bio['interests'])}"

    # Get form parameters with defaults
    sentence_count = request.form.get("sentence_count", "2")
    tone = request.form.get("tone", "friendly")
    creativity_str = request.form.get("creativity", "7")
    
    try:
        sentence_count = int(sentence_count)
    except ValueError:
        sentence_count = 2
        
    try:
        creativity = float(creativity_str) / 10
    except ValueError:
        creativity = 0.7
    
    # More intelligent filtering of image tags
    # If we have multiple similar concepts, prioritize the most specific ones
    filtered_tags = []
    generic_concepts = ["nature", "person", "photography", "landscape", "portrait"]
    
    # First add specific tags that aren't generic concepts
    for tag in image_descriptions:
        if tag.lower() not in generic_concepts:
            filtered_tags.append(tag)
    
    # Then add generic concepts only if we don't have enough specific tags
    if len(filtered_tags) < 2:
        for tag in image_descriptions:
            if tag.lower() in generic_concepts and tag not in filtered_tags:
                filtered_tags.append(tag)
                if len(filtered_tags) >= 3:
                    break
    
    # If we still don't have tags, use the original ones
    if not filtered_tags and image_descriptions:
        filtered_tags = image_descriptions
    
    enhanced_image_context = ", ".join(filtered_tags)
        
    # Build the prompt with tone and specific instructions
    tone_instructions = {
        "friendly": "Keep the tone warm and personable, like talking to a potential friend. Be genuine and approachable.",
        "witty": "Add a touch of clever humor or playfulness, with a bit of wordplay or light teasing if appropriate.",
        "flirty": "Add a subtle flirtatious element while remaining respectful. Include a tasteful compliment if appropriate.",
        "casual": "Keep it very relaxed and conversational, like texting a friend. Use a laid-back style.",
        "confident": "Write with a clear sense of self-assurance and directness, while remaining warm and engaging.",
        "unhinged": "Be boldly flirtatious, playful, and completely uninhibited while still being genuinely charming. Use humor that's edgy but never disrespectful. Be memorable and authentic in a way that stands out from typical dating messages."
    }
    
    tone_instruction = tone_instructions.get(tone, tone_instructions["friendly"])
    
    prompt = (
        f"User Bio: {user_bio}\n"
        f"Match Bio: {match_bio.get('bio', '')}\n"
        f"Match Name: {match_bio.get('name', '')}\n"
        f"Match Age: {match_bio.get('age', '')}\n"
        f"Match Interests: {', '.join(match_bio.get('interests', []))}\n"
        f"Image context: {enhanced_image_context}\n\n"
        f"TONE INSTRUCTION: {tone_instruction}\n\n"
        f"Create a first dating app message with approximately {sentence_count} sentence(s). "
        f"If the image context includes recognizable activities, interests or locations, incorporate them naturally "
        f"to show you've paid attention to their profile pictures."
    )

    openai_api_key = os.environ.get("OPENAI_API_KEY")
    if not openai_api_key:
        return jsonify({"status": "error", "error": "OPENAI_API_KEY not set in environment."}), 500

    client = OpenAI(api_key=openai_api_key)

    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini-2024-07-18",
            messages=[
                {"role": "system", "content": "You are an expert dating app first message generator for men messaging women. Your specialty is creating authentic, genuine first messages that don't sound generic or fake. Pay close attention to the image context provided and incorporate those details naturally to show you've actually looked at their profile. Adapt your tone based on the match's age - younger (18-24) should be more casual and playful, mid-range (25-35) balanced and interesting, older (36+) slightly more mature but still fun. When referencing image details, be specific rather than vague. Absolutely never create details that weren't mentioned (like fake names or invented scenarios). Include only 1 question maximum, placed at the end. Keep your messages conversational and genuine - write as a real person would text, not like marketing copy. Do not use emojis or be creepy."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=150,
            temperature=creativity,
        )
        generated_message = completion.choices[0].message.content.strip()
        
        # Get token count information
        prompt_tokens = completion.usage.prompt_tokens
        completion_tokens = completion.usage.completion_tokens
        total_tokens = completion.usage.total_tokens
    except Exception as e:
        return jsonify({"status": "error", "error": f"OpenAI API error: {e}"}), 500

    if "application/json" in request.headers.get("Accept", ""):
        return jsonify({"status": "success", "data": {"generated_message": generated_message}})
    else:
        return render_template_string(
            RESULT_HTML,
            generated_message=generated_message,
            user_bio=user_bio,
            match_bio_formatted=match_bio_formatted,
            image1_data=image1_data,
            image2_data=image2_data,
            image_tags=filtered_tags,
            sentence_count=sentence_count,
            tone=tone,
            creativity=creativity,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens
        )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
