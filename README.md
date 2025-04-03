# FirstChat REST API

A high-performance, scalable REST API for generating personalized first messages for dating apps.

## Features

- **Asynchronous Processing**: Uses FastAPI and asyncio for non-blocking I/O
- **Image Analysis**: Processes images using Google Cloud Vision API to extract context
- **AI Message Generation**: Uses OpenAI to generate personalized conversation starters
- **Validation**: Full request/response validation with Pydantic
- **API Documentation**: Auto-generated via Swagger/OpenAPI

## Setup

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Set required environment variables:

```bash
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/google-credentials.json
export OPENAI_API_KEY=your_openai_api_key
```

3. Run the server:

```bash
uvicorn app:app --host 0.0.0.0 --port 8002 --reload
```

## API Endpoints

### Health Check

```
GET /health
```

Returns server status and version information.

### Generate Message

```
POST /generate_message
```

Accepts JSON with:

- `image1`: Base64 encoded image (can include data URI prefix)
- `image2`: Base64 encoded image (can include data URI prefix)
- `user_bio`: The user's bio text
- `match_bio`: Object containing name, age, bio, and interests
- `sentence_count`: Number of sentences in generated message (1-5)
- `tone`: Message tone (friendly, witty, flirty, casual, confident)
- `creativity`: Creativity level (0.0-1.0)

## Example Request

```json
{
  "image1": "base64encodedimage...",
  "image2": "base64encodedimage...",
  "user_bio": "I'm a 28-year-old software engineer who loves hiking and photography...",
  "match_bio": {
    "name": "Emma",
    "age": 27,
    "bio": "Adventure seeker and coffee enthusiast. Love hiking and exploring new places.",
    "interests": ["hiking", "travel", "photography", "coffee"]
  },
  "sentence_count": 2,
  "tone": "friendly",
  "creativity": 0.7
}
```

## Documentation

When the server is running, visit:
- http://localhost:8002/docs for Swagger UI
- http://localhost:8002/redoc for ReDoc UI