"""
message_generator.py

Core functionality for the First Chat message generation service:
- Image analysis with Clarifai image captioning
- OpenAI message generation
- Async processing to ensure scalability

This module contains the business logic separate from the API routes.
"""

import os
import base64
import json
import time
import requests
from typing import List, Dict, Any, Optional, Tuple, Union
import asyncio

from clarifai.client.model import Model
from openai import AsyncOpenAI
import dotenv
dotenv.load_dotenv()

# Clarifai API key loaded from environment
CLARIFAI_PAT = os.environ.get("CLARIFAI_PAT")
CLARIFAI_MODEL_URL = "https://clarifai.com/salesforce/blip/models/general-english-image-caption-blip-2-6_7B"

async def analyze_image_async(image_data: str) -> List[str]:
    """
    Asynchronously analyzes image using Clarifai image captioning model.
    Accepts base64 encoded image data (string) or a URL and returns descriptive captions.
    
    Args:
        image_data: Base64 encoded image data or URL to image
        
    Returns:
        List of descriptive sentences about the image
    """
    try:
        # Process based on input type
        if isinstance(image_data, str):
            if image_data.startswith('data:image'):
                # Handle data URI format - need to save as temp file or use file bytes for Clarifai
                image_bytes = base64.b64decode(image_data.split(',')[1])
                # Use asyncio to run Clarifai prediction in non-blocking way
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    None,
                    lambda: Model(url=CLARIFAI_MODEL_URL, pat=CLARIFAI_PAT).predict_by_bytes(
                        image_bytes, 
                        input_type="image"
                    )
                )
            elif image_data.startswith(('http://', 'https://')):
                # Handle URL
                print(f"Analyzing image from URL: {image_data[:100]}...")
                # Use asyncio to run Clarifai prediction in non-blocking way
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    None,
                    lambda: Model(url=CLARIFAI_MODEL_URL, pat=CLARIFAI_PAT).predict_by_url(
                        image_data
                    )
                )
            else:
                # Try to decode as raw base64
                try:
                    image_bytes = base64.b64decode(image_data)
                    loop = asyncio.get_event_loop()
                    result = await loop.run_in_executor(
                        None,
                        lambda: Model(url=CLARIFAI_MODEL_URL, pat=CLARIFAI_PAT).predict_by_bytes(
                            image_bytes, 
                            input_type="image"
                        )
                    )
                except Exception as e:
                    print(f"Error decoding base64 data: {e}")
                    return ["A person in a portrait photo"]
        else:
            print("Invalid image data type")
            return ["A person in a portrait photo"]
        
        # Extract caption text from Clarifai response
        caption = result.outputs[0].data.text.raw
        
        # Return the caption as a list with one item - the full caption text
        # This maintains compatibility with the rest of the codebase
        return [caption] if caption else ["A person in a portrait photo"]
        
    except Exception as e:
        print(f"Error analyzing image with Clarifai: {e}")
        return ["A person in a portrait photo"]  # Return generic caption as fallback


async def process_image_captions(captions: List[str]) -> List[str]:
    """
    Processes the image captions to ensure we have useful descriptions.
    
    Args:
        captions: List of image captions from Clarifai
        
    Returns:
        Processed list of captions
    """
    # Filter out empty or very short captions
    valid_captions = [caption for caption in captions if caption and len(caption) > 5]
    
    # If no valid captions, return a generic one
    if not valid_captions:
        return ["A photo of a person"]
    
    return valid_captions


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
    captions1_task = analyze_image_async(image1_data)
    captions2_task = analyze_image_async(image2_data)
    
    # Await image analysis results
    captions1 = await captions1_task
    captions2 = await captions2_task
    
    # Process the captions
    processed_captions1 = await process_image_captions(captions1)
    processed_captions2 = await process_image_captions(captions2)
    
    # Combine image descriptions for the prompt
    image_context = "\nImage 1: " + ". ".join(processed_captions1)
    image_context += "\nImage 2: " + ". ".join(processed_captions2)
    
    # For UI display purposes, keep a combined list of all captions
    all_captions = processed_captions1 + processed_captions2
    
    # Debug image captions
    print("=== IMAGE CAPTIONING DETAILS ===")
    print(f"Image 1 caption: {processed_captions1}")
    print(f"Image 2 caption: {processed_captions2}")
    print(f"Combined image context: {image_context}")
    print("================================")
    
    # Define tone instructions based on selected tone
    tone_instructions = {
        "friendly": "Write in a naturally chill and friendly way, like you're genuinely interested in chatting casually. Keep it simple, approachable, and authentic—think texting someone you'd like to be friends with.",

        "witty": "Keep it playful and clever without forcing jokes. Aim for a subtle sense of humor or quick observation that's smart but casual, like you're chatting with someone you're comfortable with.",

        "flirty": "Stay lightly flirtatious but respectful and tasteful. Give a genuine, subtle compliment or playful comment naturally inspired by their profile—nothing overly forward or awkward.",

        "casual": "Write as if you're just naturally starting a low-pressure, relaxed conversation. Imagine texting someone you know a bit already—be chill, straightforward, and real.",

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
        f"Image descriptions: {image_context}\n\n"
        f"TONE INSTRUCTION: {tone_instruction}\n\n"
        f"SENTENCE COUNT INSTRUCTION: {sentence_instruction}\n"
        f"Reference specific details from the image descriptions to show you've paid attention to their profile pictures."
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
                "content": "You're a chill, genuine Gen Z guy (around 18) crafting an engaging first message to a girl on a dating app. Your style is conversational, playful, and a bit witty—like texting a friend you're interested in, not writing a formal intro. Always reference only specific details clearly provided in the image descriptions or bio, making it obvious you genuinely paid attention without sounding overly detailed or stalkerish. Never assume or invent details about images; only mention activities, locations, or context explicitly described in the provided image descriptions. In 'compliment' mode, offer a thoughtful, specific compliment based solely on the image details explicitly provided. Keep your language casual and authentic, exactly how a real Gen Z young adult texts someone they're interested in. Use current Gen Z slang naturally, but stay genuine. End each message with one relevant and engaging question to smoothly open a conversation. Absolutely no emojis, no guessing or assuming details, and nothing creepy."
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
        "image_captions": all_captions,
        "match_bio": match_bio,
        "user_bio": user_bio,
        "system_prompt": "You're a chill, genuine Gen Z guy (around 18) crafting an engaging first message to a girl on a dating app. Your style is conversational, playful, and a bit witty—like texting a friend you're interested in, not writing a formal intro. Always reference only specific details clearly provided in the image descriptions or bio, making it obvious you genuinely paid attention without sounding overly detailed or stalkerish. Never assume or invent details about images; only mention activities, locations, or context explicitly described in the provided image descriptions. In 'compliment' mode, offer a thoughtful, specific compliment based solely on the image details explicitly provided. Keep your language casual and authentic, exactly how a real Gen Z young adult texts someone they're interested in. Use current Gen Z slang naturally, but stay genuine. End each message with one relevant and engaging question to smoothly open a conversation. Absolutely no emojis, no guessing or assuming details, and nothing creepy.",
        "settings": {
            "sentence_count": sentence_count,
            "tone": tone,
            "creativity": creativity,
            "model": "gpt-4.5-preview-2025-02-27"
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
        "image_tags": all_captions,  # We're now returning captions instead of tags
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