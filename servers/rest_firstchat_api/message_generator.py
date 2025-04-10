"""
message_generator.py

Core functionality for the First Chat message generation service:
- Image analysis with Google Cloud Vision
- OpenAI message generation
- Async processing to ensure scalability

This module contains the business logic separate from the API routes.
"""

import os
import base64
import json
import time
from typing import List, Dict, Any, Optional, Tuple, Union
import asyncio

from google.cloud import vision
from openai import AsyncOpenAI
import dotenv
dotenv.load_dotenv()

async def analyze_image_async(image_data: str) -> List[str]:
    """
    Asynchronously analyzes image using Google Cloud Vision API.
    Accepts base64 encoded image data (string) or a URL and returns descriptive tags.
    
    Args:
        image_data: Base64 encoded image data or URL to image
        
    Returns:
        List of descriptive tags extracted from the image
    """
    try:
        # Use asyncio to prevent blocking I/O during API calls
        loop = asyncio.get_event_loop()
        
        # Create vision client
        client = vision.ImageAnnotatorClient()
        
        # Process input data - could be base64 or URL
        if isinstance(image_data, str):
            if image_data.startswith('data:image'):
                # Handle data URI format
                content = base64.b64decode(image_data.split(',')[1])
                image = vision.Image(content=content)
            elif image_data.startswith(('http://', 'https://')):
                # Handle URL - download image content
                print(f"Downloading image from URL: {image_data[:100]}...")
                try:
                    import requests
                    response = requests.get(image_data, timeout=10)
                    content = response.content
                    image = vision.Image(content=content)
                except Exception as download_error:
                    print(f"Error downloading image: {download_error}")
                    
                    # Create image from URL directly as fallback
                    image = vision.Image()
                    image.source.image_uri = image_data
            else:
                # Try to decode as raw base64
                try:
                    content = base64.b64decode(image_data)
                    image = vision.Image(content=content)
                except:
                    print("Could not process image data as base64, using default tags")
                    return ["person", "portrait", "photo"]
        else:
            print("Invalid image data type, using default tags")
            return ["person", "portrait", "photo"]
            
        # Make API calls concurrently to improve performance
        label_future = loop.run_in_executor(
            None, 
            lambda: client.label_detection(image=image)
        )
        
        landmark_future = loop.run_in_executor(
            None,
            lambda: client.landmark_detection(image=image)
        )
        
        web_future = loop.run_in_executor(
            None,
            lambda: client.web_detection(image=image)
        )
        
        # Await all API responses
        label_response = await label_future
        landmark_response = await landmark_future
        web_response = await web_future
        
        # Process label results
        labels = label_response.label_annotations
        label_descriptions = [label.description for label in labels[:3]]
        
        # Process landmark results
        landmarks = landmark_response.landmark_annotations
        landmark_descriptions = [landmark.description for landmark in landmarks] if landmarks else []
        
        # Process web detection results
        web_detection = web_response.web_detection
        web_entities = web_detection.web_entities if web_detection else []
        web_descriptions = [entity.description for entity in web_entities if entity.description] if web_entities else []
        
        # Combine and filter unique descriptions
        descriptions = list(set(label_descriptions + landmark_descriptions + web_descriptions))
        return descriptions[:3]  # Return top 3 descriptions
    except Exception as e:
        print(f"Error analyzing image with Google Cloud Vision: {e}")
        return ["person", "portrait", "photo"]  # Return generic tags as fallback


async def filter_image_tags(image_descriptions: List[str]) -> List[str]:
    """
    Intelligently filters image tags to prioritize specific concepts over generic ones.
    
    Args:
        image_descriptions: List of image tags from vision API
        
    Returns:
        Filtered list of the most relevant tags
    """
    # Define generic concepts that should only be included if more specific ones aren't available
    generic_concepts = ["nature", "person", "photography", "landscape", "portrait"]
    
    filtered_tags = []
    
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
        
    return filtered_tags


async def generate_message_async(
    image1_data: str,
    image2_data: str,
    user_bio: str,
    match_bio: Dict[str, Any],
    sentence_count: int = 2,
    tone: str = "friendly",
    creativity: float = 0.7
) -> Dict[str, Any]:
    """
    Asynchronously generates a personalized first message for a dating app.
    
    Args:
        image1_data: Base64 encoded first image
        image2_data: Base64 encoded second image
        user_bio: User's profile bio text
        match_bio: Match's profile information as a dictionary
        sentence_count: Target number of sentences in generated message
        tone: Message tone (friendly, witty, flirty, casual, confident, compliment)
        creativity: Creativity level from 0.0 to 1.0
        
    Returns:
        Dict containing generated message, image tags, and token usage statistics
    """
    # Process both images concurrently
    tags1_task = analyze_image_async(image1_data)
    tags2_task = analyze_image_async(image2_data)
    
    # Await image analysis results
    tags1 = await tags1_task
    tags2 = await tags2_task
    
    # Combine and deduplicate image descriptions
    image_descriptions = list(set(tags1 + tags2))
    
    # Filter tags for relevance
    filtered_tags = await filter_image_tags(image_descriptions)
    enhanced_image_context = ", ".join(filtered_tags)
    
    # Debug image tags
    print("=== IMAGE ANNOTATION DETAILS ===")
    print(f"Image 1 tags: {tags1}")
    print(f"Image 2 tags: {tags2}")
    print(f"Filtered image context: {enhanced_image_context}")
    print("===============================")
    
    # Define tone instructions based on selected tone
    tone_instructions = {
        "friendly": "Write in a naturally chill and friendly way, like you're genuinely interested in chatting casually. Keep it simple, approachable, and authentic—think texting someone you'd like to be friends with.",

        "witty": "Keep it playful and clever without forcing jokes. Aim for a subtle sense of humor or quick observation that's smart but casual, like you’re chatting with someone you're comfortable with.",

        "flirty": "Stay lightly flirtatious but respectful and tasteful. Give a genuine, subtle compliment or playful comment naturally inspired by their profile—nothing overly forward or awkward.",

        "casual": "Write as if you’re just naturally starting a low-pressure, relaxed conversation. Imagine texting someone you know a bit already—be chill, straightforward, and real.",

        "confident": "Speak clearly and with easy-going self-assurance, but stay warm and friendly. Keep your message direct and genuine, reflecting quiet confidence without coming across as arrogant or intense.",

        "compliment": "Give one thoughtful, specific compliment clearly inspired by their profile photos or bio. Keep it simple, sincere, and Gen Z authentic—nothing generic or exaggerated. Talk casually like an 18–20-year-old would naturally compliment someone they genuinely noticed."
    }

    tone_instruction = tone_instructions.get(tone, tone_instructions["friendly"])
    
    # Construct prompt for OpenAI
    # Create custom sentence count instruction
    sentence_instruction = ""
    if sentence_count == 1:
        sentence_instruction = "Create a brief, concise one-liner first message - just a single short sentence (maximum 20 words). Keep it punchy and to the point."
    else:
        sentence_instruction = f"Create a first dating app message with exactly {sentence_count} sentences. Make sure there are {sentence_count} distinct sentences, not one long run-on sentence."
    
    prompt = (
        f"User Bio: {user_bio}\n"
        f"Match Bio: {match_bio.get('bio', '')}\n"
        f"Match Name: {match_bio.get('name', '')}\n"
        f"Match Age: {match_bio.get('age', '')}\n"
        f"Match Interests: {', '.join(match_bio.get('interests', []))}\n"
        f"Image context: {enhanced_image_context}\n\n"
        f"TONE INSTRUCTION: {tone_instruction}\n\n"
        f"SENTENCE COUNT INSTRUCTION: {sentence_instruction}\n"
        f"If the image context includes recognizable activities, interests or locations, incorporate them naturally "
        f"to show you've paid attention to their profile pictures."
    )
    
    # Get API key for OpenAI
    openai_api_key = os.environ.get("OPENAI_API_KEY")
    if not openai_api_key:
        raise ValueError("OPENAI_API_KEY not set in environment")
    
    # Create async client
    client = AsyncOpenAI(api_key=openai_api_key)
    
    # Generate message with OpenAI
    completion = await client.chat.completions.create(
        model="gpt-4.5-preview-2025-02-27",  # Can be configurable in production gpt-4o-mini-2024-07-18
        messages=[
            {
                "role": "system", 
                "content": "You're a chill, genuine Gen Z guy (around 18) crafting an engaging first message to a girl on a dating app. Your style is conversational, playful, and a bit witty—like texting a friend you're interested in, not writing a formal intro. Always reference only specific details clearly provided in the image tags or bio, making it obvious you genuinely paid attention without sounding overly detailed or stalkerish. Never assume or invent details about images; only mention activities, locations, or context explicitly described in the provided image tags. In 'compliment' mode, offer a thoughtful, specific compliment based solely on the image details explicitly provided. Keep your language casual and authentic, exactly how a real Gen Z young adult texts someone they’re interested in. Use current Gen Z slang naturally, but stay genuine. End each message with one relevant and engaging question to smoothly open a conversation. Absolutely no emojis, no guessing or assuming details, and nothing creepy."
            },
            {
                "role": "user", 
                "content": prompt
            },
        ],
        max_tokens=200,
        temperature=creativity,
    )
    
    # Extract generated message and token statistics
    generated_message = completion.choices[0].message.content.strip()
    prompt_tokens = completion.usage.prompt_tokens
    completion_tokens = completion.usage.completion_tokens
    total_tokens = completion.usage.total_tokens
    
    # Format match bio for display
    match_bio_formatted = ""
    if "name" in match_bio:
        match_bio_formatted += f"Name: {match_bio['name']}\n"
    if "age" in match_bio:
        match_bio_formatted += f"Age: {match_bio['age']}\n"
    if "bio" in match_bio:
        match_bio_formatted += f"Bio: {match_bio['bio']}\n"
    if "interests" in match_bio and match_bio["interests"]:
        match_bio_formatted += f"Interests: {', '.join(match_bio['interests'])}"
    
    # Save the prompt and completion to a log file
    log_entry = {
        "timestamp": time.time(),
        "prompt": prompt,
        "completion": generated_message,
        "image_tags": filtered_tags,
        "match_bio": match_bio,
        "user_bio": user_bio,
        "system_prompt": "You're a chill, genuine Gen Z guy (around 18) crafting an engaging first message to a girl on a dating app. Your style is naturally conversational, playful, and a little witty—think casual texts between friends, not formal intros. Always reference specific, real details clearly visible from her profile pictures or bio, making it obvious you paid attention without sounding stalkerish. Pay special attention to details in the images and highlight something genuinely interesting or unique about them in a respectful way. When in 'compliment' mode, focus primarily on giving a thoughtful, specific compliment based on what you can see in their photos. Your message should sound exactly how a real Gen Z young adult would text someone they're interested in, casual yet engaging. Use current Gen Z language patterns and slang where appropriate, but stay authentic. End with one relevant, interesting question to spark conversation. Absolutely no emojis, no made-up details, and definitely nothing creepy.",
        "settings": {
            "sentence_count": sentence_count,
            "tone": tone,
            "creativity": creativity,
            "model": "gpt-4o-mini-2024-07-18"
        },
        "token_usage": {
            "prompt_tokens": prompt_tokens, 
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens
        }
    }
    
    # Ensure log directory exists
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
    os.makedirs(log_dir, exist_ok=True)
    
    # Write to log file with timestamp
    log_file = os.path.join(log_dir, f"api_requests_{time.strftime('%Y-%m-%d')}.jsonl")
    with open(log_file, "a") as f:
        f.write(json.dumps(log_entry) + "\n")
    
    # Return complete result with all data
    return {
        "generated_message": generated_message,
        "image_tags": filtered_tags,
        "token_usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens
        },
        "settings": {
            "sentence_count": sentence_count,
            "tone": tone,
            "creativity": creativity
        },
        "prompt": prompt  # Include the prompt in the response
    }