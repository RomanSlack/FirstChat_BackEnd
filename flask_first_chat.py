#!/usr/bin/env python3
'''
Requirements:
pip install flask openai pillow
'''

import os
import json
import base64
from io import BytesIO
from flask import Flask, request, jsonify
from PIL import Image
import openai
import dotenv
dotenv.load_dotenv()


# Initialize Flask app
app = Flask(__name__)

# Configure OpenAI
client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

def analyze_image(image_file):
    """
    Simple image analysis function that returns sample tags.
    In a production environment, you might use a lightweight model here.
    """
    try:
        img = Image.open(image_file)
        # Get basic image info
        width, height = img.size
        format_type = img.format
        
        # Convert image to base64 for potential API usage
        buffered = BytesIO()
        img.save(buffered, format=format_type)
        img_str = base64.b64encode(buffered.getvalue()).decode()
        
        # For demo purposes, just return placeholder tags
        # In production, you could use a lightweight model or service
        sample_tags = ["outdoors", "smiling", "hobby"]
        
        return {
            "success": True,
            "tags": sample_tags,
            "image_data": img_str
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@app.route('/generate_message', methods=['POST'])
def generate_message():
    try:
        # Extract form data
        user_bio = request.form.get('user_bio', '')
        match_bio_json = request.form.get('match_bio_json', '{}')
        
        # Parse match bio JSON
        try:
            match_bio = json.loads(match_bio_json)
        except json.JSONDecodeError:
            return jsonify({
                "status": "error",
                "error": "Invalid match_bio_json format"
            }), 400
        
        # Process images
        image_tags = []
        image_files = []
        
        for key in ['image1', 'image2']:
            if key in request.files:
                image_file = request.files[key]
                if image_file.filename:
                    analysis = analyze_image(image_file)
                    if analysis["success"]:
                        image_tags.extend(analysis["tags"])
                        image_files.append({
                            "filename": image_file.filename,
                            "tags": analysis["tags"]
                        })
        
        # Remove duplicates from tags
        image_tags = list(set(image_tags))
        
        # Build prompt for OpenAI
        prompt = f"""
Generate a friendly, engaging first message for a dating app conversation.

MY BIO: {user_bio}

THEIR PROFILE: {json.dumps(match_bio, indent=2)}

IMAGE TAGS: {', '.join(image_tags)}

The message should:
1. Be brief and casual (under 200 characters if possible)
2. Reference something specific from their bio or images
3. Ask one open-ended question
4. Be friendly but not overly familiar or intense
5. Avoid generic openers like "hey" or "how are you"

FIRST MESSAGE:
"""
        
        # Call OpenAI API with GPT-3.5-turbo for cost efficiency
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that generates engaging first messages for dating apps."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=150,  # Limit token usage
            temperature=0.7
        )
        
        # Extract the generated message
        generated_message = response.choices[0].message.content.strip()
        
        return jsonify({
            "status": "success",
            "data": {
                "generated_message": generated_message,
                "image_info": image_files
            }
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500

if __name__ == '__main__':
    # Check if API key is set
    if not os.environ.get("OPENAI_API_KEY"):
        print("Warning: OPENAI_API_KEY environment variable not set.")
        print("Set it with: export OPENAI_API_KEY='your-api-key'")
    
    # Run Flask app
    app.run(host='0.0.0.0', port=8000, debug=True)

'''
USAGE:

# Run the server
export OPENAI_API_KEY='your-api-key'
python flask_first_chat.py

# Test with curl
curl -X POST \
  -F "image1=@/path/to/image1.jpg" \
  -F "image2=@/path/to/image2.jpg" \
  -F "user_bio=I love hiking and photography. Looking for someone to share adventures with." \
  -F "match_bio_json={\"name\":\"Alice\",\"age\":28,\"bio\":\"Coffee addict and hiking enthusiast. I love exploring new trails and finding hidden cafes.\"}" \
  http://localhost:8080/generate_message
'''