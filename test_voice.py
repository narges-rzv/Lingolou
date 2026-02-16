#!/usr/bin/env python3
"""
Voice Testing Utility for Lingolou

Test individual voices and lines before generating full chapters.
Useful for:
- Testing voice IDs work correctly
- Adjusting voice settings (stability, style, etc.)
- Testing multilingual pronunciation
"""

from __future__ import annotations

import argparse
import json
import os
import sys

import requests

API_BASE = "https://api.elevenlabs.io/v1"


def list_voices(api_key: str) -> list[dict]:
    """Fetch and display available voices from ElevenLabs."""
    headers = {"xi-api-key": api_key}
    response = requests.get(f"{API_BASE}/voices", headers=headers)

    if response.status_code != 200:
        print(f"Error fetching voices: {response.status_code}")
        return []

    voices = response.json().get("voices", [])

    print(f"\nFound {len(voices)} voices:\n")
    print(f"{'Name':<30} {'Voice ID':<30} {'Labels'}")
    print("-" * 90)

    for voice in voices:
        name = voice.get("name", "Unknown")
        voice_id = voice.get("voice_id", "")
        labels = voice.get("labels", {})
        label_str = ", ".join(f"{k}={v}" for k, v in labels.items())
        print(f"{name:<30} {voice_id:<30} {label_str}")

    return voices


def test_voice(
    api_key: str,
    voice_id: str,
    text: str,
    output_path: str,
    stability: float = 0.5,
    similarity_boost: float = 0.75,
    style: float = 0.0,
    model_id: str = "eleven_v3",
) -> bool:
    """Generate test audio with specified voice and settings."""
    headers = {"Accept": "audio/mpeg", "Content-Type": "application/json", "xi-api-key": api_key}

    payload = {
        "text": text,
        "model_id": model_id,
        "voice_settings": {
            "stability": stability,
            "similarity_boost": similarity_boost,
            "style": style,
            "use_speaker_boost": True,
        },
    }

    print(f"\nGenerating test audio...")
    print(f"  Voice ID: {voice_id}")
    print(f"  Model: {model_id}")
    print(f"  Settings: stability={stability}, similarity={similarity_boost}, style={style}")
    print(f"  Text: {text}")

    response = requests.post(
        f"{API_BASE}/text-to-speech/{voice_id}",
        json=payload,
        headers=headers,
        params={"output_format": "mp3_44100_128"},
    )

    if response.status_code != 200:
        print(f"\nError: {response.status_code} - {response.text}")
        return False

    with open(output_path, "wb") as f:
        f.write(response.content)

    print(f"\nSaved to: {output_path}")
    return True


def test_from_story(
    api_key: str, voices_config: str, story_path: str, line_index: int, output_path: str, model_id: str = "eleven_v3"
) -> bool:
    """Test a specific line from a story file."""
    # Load voices config
    with open(voices_config, "r") as f:
        voices = json.load(f)

    # Load story
    with open(story_path, "r", encoding="utf-8") as f:
        story = json.load(f)

    # Find the line
    lines = [e for e in story if e.get("type") == "line"]

    if line_index >= len(lines):
        print(f"Error: Line index {line_index} out of range (0-{len(lines) - 1})")
        return False

    line = lines[line_index]
    speaker = line.get("speaker", "NARRATOR")
    text = line.get("text", "")
    lang = line.get("lang", "en")

    print(f"\nTesting line {line_index}:")
    print(f"  Speaker: {speaker}")
    print(f"  Language: {lang}")
    print(f"  Text: {text}")

    if speaker not in voices:
        print(f"  Warning: No voice configured for {speaker}, using NARRATOR")
        speaker = "NARRATOR"

    voice_config = voices.get(speaker, voices.get("NARRATOR"))
    if not voice_config:
        print("Error: No voice configuration found")
        return False

    return test_voice(
        api_key=api_key,
        voice_id=voice_config["voice_id"],
        text=text,
        output_path=output_path,
        stability=voice_config.get("stability", 1.0),
        similarity_boost=voice_config.get("similarity_boost", 0.95),
        style=voice_config.get("style", 0.0),
        model_id=model_id,
    )


def main():
    parser = argparse.ArgumentParser(description="Test ElevenLabs voices")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # List voices command
    list_parser = subparsers.add_parser("list", help="List available voices")
    list_parser.add_argument("--api-key", help="ElevenLabs API key")

    # Test voice command
    test_parser = subparsers.add_parser("test", help="Test a voice with custom text")
    test_parser.add_argument("--api-key", help="ElevenLabs API key")
    test_parser.add_argument("--voice-id", required=True, help="Voice ID to test")
    test_parser.add_argument("--text", required=True, help="Text to speak")
    test_parser.add_argument("--output", "-o", default="test_output.mp3", help="Output file")
    test_parser.add_argument("--stability", type=float, default=1.0)
    test_parser.add_argument("--similarity", type=float, default=0.95)
    test_parser.add_argument("--style", type=float, default=0.0)
    test_parser.add_argument("--model", default="eleven_v3")

    # Test from story command
    story_parser = subparsers.add_parser("story-line", help="Test a line from story file")
    story_parser.add_argument("--api-key", help="ElevenLabs API key")
    story_parser.add_argument("--voices", required=True, help="Voice config JSON")
    story_parser.add_argument("--story", required=True, help="Story JSON file")
    story_parser.add_argument("--line", type=int, required=True, help="Line index (0-based)")
    story_parser.add_argument("--output", "-o", default="test_line.mp3", help="Output file")
    story_parser.add_argument("--model", default="eleven_v3")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    api_key = getattr(args, "api_key", None) or os.environ.get("ELEVENLABS_API_KEY")
    if not api_key:
        print("Error: API key required. Use --api-key or set ELEVENLABS_API_KEY")
        return 1

    if args.command == "list":
        list_voices(api_key)

    elif args.command == "test":
        test_voice(
            api_key=api_key,
            voice_id=args.voice_id,
            text=args.text,
            output_path=args.output,
            stability=args.stability,
            similarity_boost=args.similarity,
            style=args.style,
            model_id=args.model,
        )

    elif args.command == "story-line":
        test_from_story(
            api_key=api_key,
            voices_config=args.voices,
            story_path=args.story,
            line_index=args.line,
            output_path=args.output,
            model_id=args.model,
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
