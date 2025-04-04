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
from typing import List, Dict, Any, Optional, Tuple, Union
import asyncio

from google.cloud import vision
from openai import AsyncOpenAI
import dotenv
dotenv.load_dotenv()

async def analyze_image_async(image_data: str) -> List[str]:
    """
    Asynchronously analyzes image using Google Cloud Vision API.
    Accepts base64 image data (string) and returns descriptive tags.
    
    Args:
        image_data: Base64 encoded image data, may include data URI prefix
        
    Returns:
        List of descriptive tags extracted from the image
    """
    try:
        # Use asyncio to prevent blocking I/O during API calls
        loop = asyncio.get_event_loop()
        
        # Create vision client
        client = vision.ImageAnnotatorClient()
        
        # Process base64 data - handle data URI format if present
        if isinstance(image_data, str) and image_data.startswith('data:image'):
            content = base64.b64decode(image_data.split(',')[1])
        else:
            # Already raw base64
            content = base64.b64decode(image_data)
            
        # Create vision Image object
        image = vision.Image(content=content)
        
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
        return ["unknown"]


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
        tone: Message tone (friendly, witty, flirty, casual, confident)
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
        "friendly": "Keep the tone warm and personable, like talking to a potential friend. Be genuine and approachable.",
        "witty": "Add a touch of clever humor or playfulness, with a bit of wordplay or light teasing if appropriate.",
        "flirty": "Add a subtle flirtatious element while remaining respectful. Include a tasteful compliment if appropriate.",
        "casual": "Keep it very relaxed and conversational, like texting a friend. Use a laid-back style.",
        "confident": "Write with a clear sense of self-assurance and directness, while remaining warm and engaging."
    }
    
    tone_instruction = tone_instructions.get(tone, tone_instructions["friendly"])
    
    # Construct prompt for OpenAI
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
    
    # Get API key for OpenAI
    openai_api_key = os.environ.get("OPENAI_API_KEY")
    if not openai_api_key:
        raise ValueError("OPENAI_API_KEY not set in environment")
    
    # Create async client
    client = AsyncOpenAI(api_key=openai_api_key)
    
    # Generate message with OpenAI
    completion = await client.chat.completions.create(
        model="gpt-4o-mini-2024-07-18",  # Can be configurable in production
        messages=[
            {
                "role": "system", 
                "content": "You are an expert dating app first message generator for men messaging women. Your specialty is creating authentic, genuine first messages that don't sound generic or fake. Pay close attention to the image context provided and incorporate those details naturally to show you've actually looked at their profile. Adapt your tone based on the match's age - younger (18-24) should be more casual and playful, mid-range (25-35) balanced and interesting, older (36+) slightly more mature but still fun. When referencing image details, be specific rather than vague. Absolutely never create details that weren't mentioned (like fake names or invented scenarios). Include only 1 question maximum, placed at the end. Keep your messages conversational and genuine - write as a real person would text, not like marketing copy. Do not use emojis or be creepy."
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
        }
    }