"""
FirstChat REST API

A FastAPI implementation of the dating message generator service that provides:
- Health check endpoint
- Message generation endpoint accepting JSON payload with base64 images
- Fully async processing for high scalability
- Proper validation and error handling

Usage:
    uvicorn app:app --host 0.0.0.0 --port 8002

Environment variables required:
- GOOGLE_APPLICATION_CREDENTIALS: Path to Google Cloud service account JSON
- OPENAI_API_KEY: Your OpenAI API key
"""

import os
import time
import json
from typing import Dict, List, Optional, Any, Union

import uvicorn
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, validator
from pydantic.json import pydantic_encoder

from message_generator import generate_message_async

# Initialize FastAPI app
app = FastAPI(
    title="FirstChat API",
    description="API for generating personalized first messages for dating apps",
    version="1.0.1",
)

# Create logs directory if it doesn't exist
logs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
os.makedirs(logs_dir, exist_ok=True)

# Add CORS middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Input models for validation
class MatchBio(BaseModel):
    """Match bio schema with required fields."""
    name: str
    age: Optional[int] = None
    bio: str
    interests: List[str] = Field(default_factory=list)

class MessageRequest(BaseModel):
    """Request schema for message generation endpoint."""
    image1: str = Field(..., description="Base64 encoded image (can include data:image prefix)")
    image2: str = Field(..., description="Base64 encoded image (can include data:image prefix)")
    user_bio: str = Field(..., description="User's profile bio text")
    match_bio: MatchBio = Field(..., description="Match's profile information")
    sentence_count: int = Field(2, description="Number of sentences in the message", ge=1, le=5)
    tone: str = Field("friendly", description="Message tone (friendly, witty, flirty, casual, confident, unhinged, freaky)")
    creativity: float = Field(0.7, description="Creativity level (0.0 to 1.0)", ge=0.0, le=1.0)
    
    @validator('tone')
    def validate_tone(cls, v):
        valid_tones = ["friendly", "witty", "flirty", "casual", "confident", "unhinged", "freaky"]
        if v.lower() not in valid_tones:
            raise ValueError(f"Tone must be one of: {', '.join(valid_tones)}")
        return v.lower()
    
    @validator('image1', 'image2')
    def validate_image(cls, v):
        # Check if it's a data URI format or raw base64
        if v.startswith('data:image'):
            parts = v.split(',', 1)
            if len(parts) != 2:
                raise ValueError("Invalid data URI format")
        return v

class HealthResponse(BaseModel):
    """Response schema for health check endpoint."""
    status: str
    version: str
    timestamp: float

class MessageResponse(BaseModel):
    """Response schema for message generation endpoint."""
    status: str
    data: Dict[str, Any]
    processing_time: float

# Dependency to check if required env variables are set
def verify_environment():
    if not os.environ.get("OPENAI_API_KEY"):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, 
            detail="OPENAI_API_KEY not set in environment"
        )
    if not os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, 
            detail="GOOGLE_APPLICATION_CREDENTIALS not set in environment"
        )
    return True

# Health check endpoint
@app.get(
    "/health", 
    response_model=HealthResponse,
    summary="Health check endpoint",
    description="Returns the current status of the API service"
)
async def health():
    return {
        "status": "ok",
        "version": "1.0.0",
        "timestamp": time.time()
    }

# Message generation endpoint
@app.post(
    "/generate_message", 
    response_model=MessageResponse,
    summary="Generate a dating app first message",
    description="Generate a personalized first message based on profile information and images"
)
async def generate_message(
    request: MessageRequest, 
    env_check: bool = Depends(verify_environment)
):
    start_time = time.time()
    
    try:
        # Process the message generation request asynchronously
        result = await generate_message_async(
            image1_data=request.image1,
            image2_data=request.image2,
            user_bio=request.user_bio,
            match_bio=request.match_bio.dict(),
            sentence_count=request.sentence_count,
            tone=request.tone,
            creativity=request.creativity
        )
        
        # Return successful response with timing information
        return {
            "status": "success",
            "data": result,
            "processing_time": time.time() - start_time
        }
    except ValueError as e:
        # Handle validation errors
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        # Handle unexpected errors
        print(f"Error generating message: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating message: {str(e)}"
        )

# Add endpoint to view logs
@app.get(
    "/logs", 
    response_model=List[str],
    summary="List available log files",
    description="Returns a list of available API request log files"
)
async def list_logs(env_check: bool = Depends(verify_environment)):
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
    try:
        files = [f for f in os.listdir(log_dir) if f.startswith("api_requests_") and f.endswith(".jsonl")]
        return sorted(files, reverse=True)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing log files: {str(e)}"
        )

@app.get(
    "/logs/{filename}", 
    response_model=List[Dict[str, Any]],
    summary="Get log file contents",
    description="Returns the contents of a specific log file"
)
async def get_log_file(filename: str, env_check: bool = Depends(verify_environment)):
    if not filename.startswith("api_requests_") or not filename.endswith(".jsonl"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid log filename format"
        )
    
    log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs", filename)
    
    if not os.path.exists(log_file):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Log file not found"
        )
    
    try:
        entries = []
        with open(log_file, 'r') as f:
            for line in f:
                if line.strip():
                    entries.append(json.loads(line))
        return entries
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error reading log file: {str(e)}"
        )

# Run the API server if executed as main module
if __name__ == "__main__":
    print("Starting FirstChat API server on http://0.0.0.0:8002")
    print("API documentation available at http://localhost:8002/docs")
    uvicorn.run(app, host="0.0.0.0", port=8002)