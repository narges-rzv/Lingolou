# Lingolou - Language Learning Audiobook Generator

A complete pipeline for generating children's language learning audiobooks:
1. **Story Generation** - Create story scripts using OpenAI
2. **Emotion Enhancement** - Add voice emotion tags automatically
3. **Audio Generation** - Convert to audiobook using ElevenLabs

Designed for kids' language learning apps with support for multiple characters, languages (English + Farsi), emotions, and concurrent group dialogue.

## Features

- **AI Story Generation**: Create story scripts with OpenAI GPT-4
- **Multi-character voices**: Each character gets their own distinct voice
- **Multilingual support**: Uses `eleven_v3` model for English and Farsi
- **Emotion tags**: `[excited]`, `[warm]`, `[concerned]` etc. control voice delivery
- **Group dialogue**: `ALL_PUPS` generates concurrent chatter by mixing voices
- **Pauses & pacing**: Respects pause markers and adds natural spacing

## Prerequisites

- **Python 3.9+**
- **ffmpeg** (for audio processing)
- **Redis** (for Celery background task queue)
- **API Keys**: OpenAI (story generation) + ElevenLabs (audio generation)

## Setup

### 1. Install system dependencies

```bash
# macOS
brew install ffmpeg redis

# Ubuntu/Debian
sudo apt install ffmpeg redis-server
```

### 2. Create a virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Python packages

```bash
pip install -r requirements.txt
pip install email-validator
```

### 4. Set API keys

```bash
export OPENAI_API_KEY="your-openai-key"
export ELEVENLABS_API_KEY="your-elevenlabs-key"
export REDIS_URL="redis://localhost:6379/0"  # optional, this is the default
```

### 5. Configure voices

Copy the example and fill in your ElevenLabs voice IDs:

```bash
cp voices_config.example.json voices_config.json
```

You can list available voices with:

```bash
python test_voice.py list
```

### 6. Start Redis

```bash
# macOS (run as background service)
brew services start redis

# Or run in a dedicated terminal
redis-server
```

### 7. Start the Celery worker

In a dedicated terminal:

```bash
source venv/bin/activate
celery -A webapp.celery_app worker --loglevel=info
```

### 8. Start the FastAPI server

In another terminal:

```bash
source venv/bin/activate
python -m uvicorn webapp.main:app --reload --host 0.0.0.0 --port 8000
```

The API docs are at http://localhost:8000/docs.

## Project Structure

```
Lingolou/
├── stories/
│   └── s1/                       # Story 1
│       ├── ch1.json              # Chapter 1 (base)
│       ├── ch1_enhanced.json     # Chapter 1 (with emotion tags)
│       └── ...
├── generate_story.py             # Story generation script (OpenAI)
├── generate_audiobook.py         # Audio generation script (ElevenLabs)
├── test_voice.py                 # Voice testing utility
├── story_config.json             # Story generation config (prompts, characters, settings)
├── voices_config.json            # Your voice configuration
└── voices_config.example.json    # Example template
```

## Quick Start (CLI)

```bash
# Generate a 3-chapter story
python generate_story.py -o stories/s2

# Generate the audiobook
python generate_audiobook.py stories/s2 --voices voices_config.json
```

---

## Story Generation

### Generate with default prompt

```bash
python generate_story.py -o stories/s2
```

### Generate with custom prompt

```bash
python generate_story.py -o stories/s2 -p "Create a story about space exploration teaching Spanish to kids..."
```

### Generate from prompt file

```bash
python generate_story.py -o stories/s2 --prompt-file my_prompt.txt
```

### Use custom config

```bash
python generate_story.py -o stories/s2 --config my_story_config.json
```

### Full options

```
usage: generate_story.py [-h] [--config CONFIG] [--prompt PROMPT]
                         [--prompt-file FILE] --output OUTPUT
                         [--chapters N] [--model MODEL]
                         [--no-enhance] [--api-key KEY]

Options:
  --config           Path to config JSON file (default: story_config.json)
  --prompt, -p       Story prompt/description (overrides config)
  --prompt-file      Read prompt from a text file
  --output, -o       Output directory for story files (required)
  --chapters, -n     Number of chapters (default from config)
  --model, -m        OpenAI model (default from config)
  --no-enhance       Skip emotion tag enhancement
  --api-key          OpenAI API key (or set OPENAI_API_KEY env var)
```

### Story Configuration

All story generation settings are in `story_config.json`:

```json
{
  "default_prompt": "Your default story prompt...",

  "characters": {
    "NARRATOR": "Tells the story",
    "RYDER": "The human leader",
    "POUYA": "A new Farsi-speaking pup"
  },

  "valid_speakers": ["NARRATOR", "RYDER", "POUYA", "ALL_PUPS"],

  "target_language": {
    "name": "Farsi",
    "code": "fa"
  },

  "generation_settings": {
    "default_model": "gpt-4o",
    "default_chapters": 3,
    "story_temperature": 0.8,
    "enhance_temperature": 0.4
  },

  "story_system_prompt": "System prompt for story generation...",
  "enhance_system_prompt": "System prompt for emotion enhancement...",

  "emotion_tags": {
    "high_energy": ["excited", "enthusiastic"],
    "calm": ["warm", "gentle"]
  }
}
```

To create a different story (e.g., Spanish learning with different characters), copy and modify `story_config.json`.

---

## Audio Generation

### Generate a single chapter

```bash
python generate_audiobook.py stories/s1 --voices voices_config.json -c ch1_enhanced
```

### Generate all chapters

```bash
python generate_audiobook.py stories/s1 --voices voices_config.json
```

### Specify output directory

```bash
python generate_audiobook.py stories/s1 --voices voices_config.json -o output/
```

### Full options

```
usage: generate_audiobook.py [-h] --voices VOICES [--api-key API_KEY]
                             [--output OUTPUT] [--chapter CHAPTER]
                             [--model MODEL]
                             story_folder

Arguments:
  story_folder          Path to story folder containing chapter JSON files
  --voices VOICES       Path to voice configuration JSON file
  --api-key API_KEY     ElevenLabs API key (or set ELEVENLABS_API_KEY env var)
  --output, -o OUTPUT   Output directory (default: same as story folder)
  --chapter, -c CHAPTER Specific chapter (e.g., 'ch1_enhanced')
  --model MODEL         ElevenLabs model ID (default: eleven_v3)
```

---

## Testing Voices

### List available voices
```bash
python test_voice.py list
```

### Test a voice with custom text
```bash
python test_voice.py test --voice-id "abc123" --text "سلام!" --output test.mp3
```

### Test a specific line from a story
```bash
python test_voice.py story-line --voices voices_config.json --story stories/s1/ch1.json --line 5
```

---

## Voice Configuration

Edit `voices_config.json`:

```json
{
  "NARRATOR": {
    "voice_id": "your-narrator-voice-id",
    "stability": 1.0,
    "similarity_boost": 0.95,
    "style": 0.2,
    "use_speaker_boost": true
  },
  "RYDER": {
    "voice_id": "your-ryder-voice-id",
    "stability": 1.0,
    "similarity_boost": 0.95,
    "style": 0.3,
    "use_speaker_boost": true
  }
}
```

### Voice Settings (eleven_v3)

| Parameter | Valid Values | Effect |
|-----------|--------------|--------|
| `stability` | 0, 0.5, 1.0 | Higher = more consistent delivery |
| `similarity_boost` | 0-1 | How closely to match the voice (0.95 recommended) |
| `style` | 0-1 | Higher = more expressive |
| `use_speaker_boost` | bool | Enhances voice clarity |

---

## JSON Story Format

Stories are JSON arrays with these entry types:

```json
[
  { "type": "scene", "id": "ch1_s1", "title": "Scene Title" },
  { "type": "bg", "value": "Background ambience description" },
  { "type": "music", "value": "Music description", "volume": 0.25 },
  {
    "type": "line",
    "speaker": "POUYA",
    "lang": "fa",
    "text": "[friendly] سلام!",
    "transliteration": "Salâm!",
    "gloss_en": "Hello!"
  },
  { "type": "pause", "seconds": 0.5 },
  { "type": "sfx", "value": "sound effect description" },
  { "type": "performance", "value": "LAUGH" },
  { "type": "end", "value": "END_CHAPTER_1" }
]
```

### Entry Types

| Type | Purpose | Generated Audio |
|------|---------|-----------------|
| `line` | Character dialogue | Speech via ElevenLabs |
| `pause` | Silence | Silent audio segment |
| `scene` | Scene marker | 1 second pause |
| `sfx` | Sound effect placeholder | 0.3 second pause |
| `performance` | LAUGH/CHEER placeholder | 0.5 second pause |
| `music` | Music cue (metadata only) | None |
| `bg` | Background description (metadata) | None |
| `end` | Chapter end marker | None |

### Valid Speakers

`NARRATOR`, `RYDER`, `CHASE`, `MARSHALL`, `SKYE`, `ROCKY`, `RUBBLE`, `ZUMA`, `EVEREST`, `POUYA`, `ALL_PUPS`, `ALL_PUPS_AND_RYDER`

### Group Speakers

`ALL_PUPS` and `ALL_PUPS_AND_RYDER` automatically mix all character voices for concurrent chatter.

---

## Emotion Tags

Enhanced chapters use `[emotion]` tags at the start of each line:

```json
{"text": "[excited] Ready for action, Ryder!"}
{"text": "[warm] The morning sun shimmered over Adventure Bay..."}
{"text": "[concerned] A baby penguin? All alone?"}
```

### Available Emotions

| Category | Tags |
|----------|------|
| High energy | `excited`, `enthusiastic`, `happy`, `cheerful`, `playful`, `laughing` |
| Calm | `warm`, `gentle`, `calm`, `relaxed`, `steady`, `matter-of-fact` |
| Confident | `confident`, `commanding`, `determined`, `proud`, `strong` |
| Teaching | `teacherly`, `encouraging`, `clear`, `thoughtful` |
| Concerned | `concerned`, `worried`, `serious`, `urgent`, `alarmed` |
| Uncertain | `confused`, `sheepish`, `careful`, `trying` |
| Positive | `pleased`, `smiling`, `welcoming`, `friendly`, `amused` |
| Narrative | `adventurous`, `curious`, `hopeful`, `teasing` |
| Alert | `alert`, `focused`, `reassuring`, `bright` |

Each emotion maps to specific `stability` and `style` values for natural delivery.

---

## Web App API

The project includes a FastAPI backend with Celery/Redis for background task processing. See [Setup](#setup) for installation and running instructions.

### API Endpoints

#### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register` | Register new user |
| POST | `/api/auth/login` | Login, get JWT token |
| GET | `/api/auth/me` | Get current user info |
| POST | `/api/auth/logout` | Logout |

#### Stories

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/stories/` | List user's stories |
| POST | `/api/stories/` | Create new story |
| GET | `/api/stories/{id}` | Get story with chapters |
| PATCH | `/api/stories/{id}` | Update story metadata |
| DELETE | `/api/stories/{id}` | Delete story |
| POST | `/api/stories/{id}/generate` | Generate story scripts |
| POST | `/api/stories/{id}/generate-audio` | Generate audio files |
| GET | `/api/stories/{id}/chapters/{num}/script` | Get chapter script JSON |
| GET | `/api/stories/tasks/{task_id}` | Check generation task status |
| DELETE | `/api/stories/tasks/{task_id}` | Cancel a running task |

### Example Usage

```bash
# Register
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "username": "user", "password": "secret"}'

# Login
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -d "username=user@example.com&password=secret" | jq -r .access_token)

# Create story
curl -X POST http://localhost:8000/api/stories/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title": "My Story", "num_chapters": 3}'

# Generate story content
curl -X POST http://localhost:8000/api/stories/1/generate \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title": "My Story", "num_chapters": 3, "enhance": true}'

# Check task status
curl http://localhost:8000/api/stories/tasks/story_1_1 \
  -H "Authorization: Bearer $TOKEN"

# Generate audio
curl -X POST http://localhost:8000/api/stories/1/generate-audio \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"story_id": 1}'
```

### Database

SQLite database (`lingolou.db`) stores:
- **Users**: Account info, authentication
- **Stories**: Story metadata, prompts, config
- **Chapters**: Scripts, audio paths, status
- **UsageLog**: API usage tracking per user

### Project Structure (Web App)

```
webapp/
├── main.py              # FastAPI application
├── celery_app.py        # Celery configuration
├── tasks.py             # Celery background tasks
├── api/
│   ├── auth.py          # Auth endpoints
│   └── stories.py       # Story endpoints
├── models/
│   ├── database.py      # SQLAlchemy models
│   └── schemas.py       # Pydantic schemas
├── services/
│   └── auth.py          # Auth logic, JWT
└── static/
    └── audio/           # Generated audio files
```

### Background Tasks (Celery)

Story and audio generation run as background tasks via Celery with Redis:

- **Progress tracking**: Tasks report progress (0-100%) and status messages
- **Retry logic**: Failed tasks automatically retry up to 2 times
- **Time limits**: Soft limit 10 min, hard limit 15 min per task
- **Task cancellation**: Running tasks can be cancelled via API
