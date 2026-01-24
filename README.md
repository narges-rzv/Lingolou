# Lingolou - Language Learning Audiobook Generator

A tool for generating audiobooks from JSON story scripts using ElevenLabs API. Designed for kids' language learning apps with support for multiple characters, languages (English + Farsi), emotions, and concurrent group dialogue.

## Features

- **Multi-character voices**: Each character gets their own distinct voice
- **Multilingual support**: Uses `eleven_multilingual_v2` model for English and Farsi
- **Emotion detection**: Automatically adjusts voice parameters based on punctuation (!, ?, ...)
- **Group dialogue**: `ALL_PUPS` and `ALL_PUPS_AND_RYDER` generate concurrent chatter by mixing multiple voices
- **Pauses & pacing**: Respects pause markers and adds natural spacing between lines

## Prerequisites

1. **Python 3.9+**
2. **ffmpeg** (for audio processing)
   ```bash
   brew install ffmpeg
   ```
3. **Python packages**
   ```bash
   pip install requests
   ```
4. **ElevenLabs API key** - Get one at [elevenlabs.io](https://elevenlabs.io)

## Project Structure

```
Lingolou/
├── stories/
│   └── s1/                    # Story 1
│       ├── ch1.json           # Chapter 1
│       ├── ch2.json           # Chapter 2
│       └── ...
├── generate_audiobook.py      # Main generation script
├── test_voice.py              # Voice testing utility
├── voices_config.json         # Your voice configuration
└── voices_config.example.json # Example template
```

## Setup

### 1. Set your API key

```bash
export ELEVENLABS_API_KEY="your-api-key-here"
```

### 2. Configure voices

List your available ElevenLabs voices:
```bash
python test_voice.py list
```

Edit `voices_config.json` with your voice IDs:
```json
{
  "NARRATOR": {
    "voice_id": "your-narrator-voice-id",
    "stability": 0.6,
    "similarity_boost": 0.8,
    "style": 0.2,
    "use_speaker_boost": true
  },
  "RYDER": {
    "voice_id": "your-ryder-voice-id",
    "stability": 0.5,
    "similarity_boost": 0.75,
    "style": 0.3,
    "use_speaker_boost": true
  }
  // ... add all characters
}
```

## Usage

### Generate a single chapter

```bash
python generate_audiobook.py stories/s1 --voices voices_config.json -c ch1
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
  --chapter, -c CHAPTER Specific chapter (e.g., 'ch1'). Omit to generate all.
  --model MODEL         ElevenLabs model ID (default: eleven_multilingual_v2)
```

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

## Voice Settings Guide

| Parameter | Range | Effect |
|-----------|-------|--------|
| `stability` | 0-1 | Higher = more consistent, Lower = more variable/emotional |
| `similarity_boost` | 0-1 | How closely to match the original voice |
| `style` | 0-1 | Higher = more expressive delivery |
| `use_speaker_boost` | bool | Enhances voice clarity |

**Character presets:**
- **Narrator**: Higher stability (0.6), lower style (0.2) - calm, clear
- **Marshall**: Lower stability (0.4), higher style (0.5) - excitable, energetic
- **Pouya**: Moderate stability (0.55) - clear for teaching

## JSON Story Format

Stories are JSON arrays with different entry types:

```json
[
  { "type": "scene", "id": "ch1_s1", "title": "Scene Title" },
  { "type": "bg", "value": "Background ambience description" },
  { "type": "music", "value": "Music description", "volume": 0.25 },
  {
    "type": "line",
    "speaker": "POUYA",
    "lang": "fa",
    "text": "سلام!",
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

### Group Speakers

When the script encounters `ALL_PUPS` or `ALL_PUPS_AND_RYDER`, it automatically:
1. Generates audio for each character in the group
2. Mixes all voices together for concurrent chatter effect

Groups are defined as:
- `ALL_PUPS`: CHASE, MARSHALL, SKYE, ROCKY, RUBBLE, ZUMA, EVEREST
- `ALL_PUPS_AND_RYDER`: All pups + RYDER

No need to configure these in `voices_config.json` - just configure the individual characters.

## Emotion Handling

The script automatically adjusts voice parameters based on text:

| Text Pattern | Effect |
|--------------|--------|
| `!` exclamation | More expressive, less stable |
| `?` question | Slightly more expressive |
| `...` ellipsis | More stable, hesitant |
| `ALL CAPS` | Maximum expressiveness |

Character-specific adjustments are also applied (e.g., Marshall is always more excitable).
