#!/usr/bin/env python3
"""
Audiobook Generator for Lingolou Language Learning App

Converts JSON story scripts into audio using ElevenLabs API.
Supports multiple characters, languages, emotions, and pauses.
"""

import json
import os
import argparse
import time
import subprocess
import tempfile
import shutil
from pathlib import Path
from dataclasses import dataclass
from typing import Optional
import requests


@dataclass
class VoiceConfig:
    """Configuration for a character's voice."""
    voice_id: str
    stability: float = 0.5
    similarity_boost: float = 0.75
    style: float = 0.0  # 0-1, higher = more expressive
    use_speaker_boost: bool = True


class AudiobookGenerator:
    """Generate audiobook from JSON story scripts using ElevenLabs API."""

    API_BASE = "https://api.elevenlabs.io/v1"

    # Define group speakers and their members
    GROUP_SPEAKERS = {
        "ALL_PUPS": ["CHASE", "MARSHALL", "SKYE", "ROCKY", "RUBBLE", "ZUMA", "EVEREST"],
        "ALL_PUPS_AND_RYDER": ["RYDER", "CHASE", "MARSHALL", "SKYE", "ROCKY", "RUBBLE", "ZUMA", "EVEREST"],
    }

    def __init__(
        self,
        api_key: str,
        voice_map: dict[str, VoiceConfig],
        model_id: str = "eleven_multilingual_v2",
        output_format: str = "mp3_44100_128"
    ):
        """
        Initialize the audiobook generator.

        Args:
            api_key: ElevenLabs API key
            voice_map: Mapping of speaker names to VoiceConfig
            model_id: ElevenLabs model ID (eleven_multilingual_v2 recommended for multilingual)
            output_format: Audio output format
        """
        self.api_key = api_key
        self.voice_map = voice_map
        self.model_id = model_id
        self.output_format = output_format
        self.headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": api_key
        }

    def _get_voice_for_speaker(self, speaker: str) -> VoiceConfig:
        """Get voice configuration for a speaker, with fallback to NARRATOR."""
        if speaker in self.voice_map:
            return self.voice_map[speaker]
        # Handle group speakers by using first character or narrator
        if speaker.startswith("ALL_"):
            return self.voice_map.get("NARRATOR", list(self.voice_map.values())[0])
        return self.voice_map.get("NARRATOR", list(self.voice_map.values())[0])

    def _add_ssml_emotions(self, text: str, speaker: str, context: Optional[dict] = None) -> str:
        """
        Enhance text for emotional delivery.

        ElevenLabs responds well to natural punctuation and formatting:
        - Ellipsis (...) creates hesitation/pause
        - Em-dash (—) creates dramatic pause
        - Exclamation marks add energy
        - ALL CAPS for emphasis (use sparingly)
        - Commas for natural breathing pauses
        """
        enhanced = text

        # Ensure ellipsis has proper spacing for natural pause
        enhanced = enhanced.replace("...", " ... ")
        enhanced = enhanced.replace("  ", " ")

        return enhanced.strip()

    def _adjust_voice_for_emotion(
        self,
        voice_config: VoiceConfig,
        text: str,
        speaker: str
    ) -> VoiceConfig:
        """
        Adjust voice settings based on detected emotion in text.

        Returns a modified copy of voice_config with adjusted parameters.
        """
        # Detect emotional indicators
        has_exclamation = "!" in text
        has_question = "?" in text
        has_ellipsis = "..." in text
        is_shouting = text.isupper() and len(text) > 3

        # Start with base config
        stability = voice_config.stability
        style = voice_config.style
        similarity = voice_config.similarity_boost

        # Adjust for excitement/urgency
        if has_exclamation:
            style = min(1.0, style + 0.15)
            stability = max(0.3, stability - 0.1)

        # Adjust for questions (slight upturn, more expressive)
        if has_question:
            style = min(1.0, style + 0.1)

        # Adjust for hesitation/uncertainty
        if has_ellipsis:
            stability = min(0.8, stability + 0.1)
            style = max(0.0, style - 0.1)

        # Adjust for emphasis
        if is_shouting:
            style = min(1.0, style + 0.25)
            stability = max(0.25, stability - 0.15)

        # Character-specific adjustments
        if speaker == "MARSHALL":
            style = min(1.0, style + 0.1)
        elif speaker == "NARRATOR":
            stability = min(0.8, stability + 0.1)
            style = max(0.0, style - 0.05)
        elif speaker == "POUYA":
            stability = min(0.75, stability + 0.05)

        return VoiceConfig(
            voice_id=voice_config.voice_id,
            stability=stability,
            similarity_boost=similarity,
            style=style,
            use_speaker_boost=voice_config.use_speaker_boost
        )

    def _generate_speech(
        self,
        text: str,
        voice_config: VoiceConfig,
        previous_text: Optional[str] = None,
        next_text: Optional[str] = None
    ) -> bytes:
        """
        Generate speech audio for given text using ElevenLabs API.

        Args:
            text: Text to convert to speech
            voice_config: Voice configuration
            previous_text: Previous text for context (improves prosody)
            next_text: Next text for context

        Returns:
            Audio data as bytes
        """
        url = f"{self.API_BASE}/text-to-speech/{voice_config.voice_id}"

        payload = {
            "text": text,
            "model_id": self.model_id,
            "voice_settings": {
                "stability": voice_config.stability,
                "similarity_boost": voice_config.similarity_boost,
                "style": voice_config.style,
                "use_speaker_boost": voice_config.use_speaker_boost
            }
        }

        # Add context for better prosody if available
        if previous_text or next_text:
            payload["previous_text"] = previous_text
            payload["next_text"] = next_text

        response = requests.post(
            url,
            json=payload,
            headers=self.headers,
            params={"output_format": self.output_format}
        )

        if response.status_code != 200:
            raise Exception(f"ElevenLabs API error: {response.status_code} - {response.text}")

        return response.content

    def _generate_silence_mp3(self, duration_seconds: float, output_path: str) -> str:
        """Generate silence MP3 of specified duration using ffmpeg."""
        cmd = [
            "ffmpeg", "-y", "-f", "lavfi",
            "-i", f"anullsrc=r=44100:cl=mono",
            "-t", str(duration_seconds),
            "-c:a", "libmp3lame", "-b:a", "128k",
            output_path
        ]
        subprocess.run(cmd, capture_output=True, check=True)
        return output_path

    def _concatenate_audio_files(self, file_list: list[str], output_path: str):
        """Concatenate multiple MP3 files using ffmpeg."""
        if not file_list:
            return

        # Create a temporary file list for ffmpeg
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            list_file = f.name
            for audio_file in file_list:
                # Escape single quotes in path
                escaped_path = audio_file.replace("'", "'\\''")
                f.write(f"file '{escaped_path}'\n")

        try:
            cmd = [
                "ffmpeg", "-y", "-f", "concat", "-safe", "0",
                "-i", list_file,
                "-c:a", "libmp3lame", "-b:a", "192k",
                output_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"FFmpeg error: {result.stderr}")
                raise Exception(f"FFmpeg concatenation failed: {result.stderr}")
        finally:
            os.unlink(list_file)

    def _mix_audio_files(self, file_list: list[str], output_path: str):
        """Mix multiple MP3 files together (overlay/concurrent playback) using ffmpeg."""
        if not file_list:
            return
        if len(file_list) == 1:
            # Just copy the single file
            shutil.copy(file_list[0], output_path)
            return

        # Build ffmpeg command to mix all audio files
        # Using amix filter to overlay all tracks
        cmd = ["ffmpeg", "-y"]

        # Add all input files
        for audio_file in file_list:
            cmd.extend(["-i", audio_file])

        # Build the amix filter
        n_inputs = len(file_list)
        # amix with normalize=0 to prevent volume reduction, dropout_transition for smooth end
        filter_str = f"amix=inputs={n_inputs}:duration=longest:dropout_transition=0.5,volume={min(2.0, n_inputs * 0.7)}"

        cmd.extend([
            "-filter_complex", filter_str,
            "-c:a", "libmp3lame", "-b:a", "192k",
            output_path
        ])

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"FFmpeg mix error: {result.stderr}")
            raise Exception(f"FFmpeg mixing failed: {result.stderr}")

    def _is_group_speaker(self, speaker: str) -> bool:
        """Check if speaker is a group (multiple voices speaking together)."""
        return speaker in self.GROUP_SPEAKERS

    def _get_group_members(self, speaker: str) -> list[str]:
        """Get list of individual speakers in a group."""
        return self.GROUP_SPEAKERS.get(speaker, [])

    def _process_line(
        self,
        line: dict,
        prev_line: Optional[dict] = None,
        next_line: Optional[dict] = None,
        output_path: str = None,
        temp_dir: str = None
    ) -> Optional[str]:
        """
        Process a single line entry and generate audio.

        Returns path to generated audio file or None.
        """
        speaker = line.get("speaker", "NARRATOR")
        text = line.get("text", "")

        if not text.strip():
            return None

        prev_text = prev_line.get("text") if prev_line and prev_line.get("type") == "line" else None
        next_text = next_line.get("text") if next_line and next_line.get("type") == "line" else None

        display_text = text[:50] + "..." if len(text) > 50 else text

        # Check if this is a group speaker (concurrent chatter)
        if self._is_group_speaker(speaker):
            return self._process_group_line(
                speaker, text, prev_text, next_text, output_path, temp_dir, display_text
            )

        # Single speaker
        print(f"  Generating: [{speaker}] {display_text}")

        voice_config = self._get_voice_for_speaker(speaker)
        adjusted_voice = self._adjust_voice_for_emotion(voice_config, text, speaker)
        enhanced_text = self._add_ssml_emotions(text, speaker)

        audio_bytes = self._generate_speech(
            enhanced_text,
            adjusted_voice,
            previous_text=prev_text,
            next_text=next_text
        )

        with open(output_path, 'wb') as f:
            f.write(audio_bytes)

        return output_path

    def _process_group_line(
        self,
        group_speaker: str,
        text: str,
        prev_text: Optional[str],
        next_text: Optional[str],
        output_path: str,
        temp_dir: str,
        display_text: str
    ) -> Optional[str]:
        """
        Process a group line by generating audio for each member and mixing them.

        Creates concurrent chatter effect by overlaying multiple voices.
        """
        members = self._get_group_members(group_speaker)

        # Filter to only members that have configured voices
        available_members = [m for m in members if m in self.voice_map]

        if not available_members:
            print(f"  Warning: No voices configured for {group_speaker} members, using NARRATOR")
            # Fall back to narrator
            voice_config = self._get_voice_for_speaker("NARRATOR")
            adjusted_voice = self._adjust_voice_for_emotion(voice_config, text, "NARRATOR")
            enhanced_text = self._add_ssml_emotions(text, "NARRATOR")
            audio_bytes = self._generate_speech(enhanced_text, adjusted_voice, prev_text, next_text)
            with open(output_path, 'wb') as f:
                f.write(audio_bytes)
            return output_path

        print(f"  Generating: [{group_speaker}] {display_text}")
        print(f"    Mixing {len(available_members)} voices: {', '.join(available_members)}")

        # Generate audio for each member
        member_audio_files = []
        for i, member in enumerate(available_members):
            voice_config = self.voice_map[member]
            adjusted_voice = self._adjust_voice_for_emotion(voice_config, text, member)
            enhanced_text = self._add_ssml_emotions(text, member)

            audio_bytes = self._generate_speech(
                enhanced_text,
                adjusted_voice,
                previous_text=prev_text,
                next_text=next_text
            )

            # Save to temp file
            member_path = os.path.join(temp_dir, f"group_{group_speaker}_{member}_{i}.mp3")
            with open(member_path, 'wb') as f:
                f.write(audio_bytes)
            member_audio_files.append(member_path)

            # Small delay between API calls for rate limiting
            time.sleep(0.1)

        # Mix all member audio files together
        self._mix_audio_files(member_audio_files, output_path)

        # Clean up individual member files
        for f in member_audio_files:
            try:
                os.unlink(f)
            except OSError:
                pass

        return output_path

    def generate_chapter(
        self,
        story_path: str,
        output_path: str,
        include_scene_markers: bool = True
    ) -> str:
        """
        Generate audio for an entire chapter.

        Args:
            story_path: Path to JSON story file
            output_path: Path for output audio file
            include_scene_markers: Whether to include scene transition pauses

        Returns:
            Path to generated audio file
        """
        with open(story_path, 'r', encoding='utf-8') as f:
            story = json.load(f)

        print(f"Processing {story_path}...")
        print(f"Found {len(story)} entries")

        # Create temp directory for audio segments
        temp_dir = tempfile.mkdtemp(prefix="audiobook_")
        audio_files = []
        segment_index = 0

        try:
            for i, entry in enumerate(story):
                entry_type = entry.get("type")
                prev_entry = story[i - 1] if i > 0 else None
                next_entry = story[i + 1] if i < len(story) - 1 else None

                audio_path = None

                if entry_type == "line":
                    segment_path = os.path.join(temp_dir, f"segment_{segment_index:04d}.mp3")
                    audio_path = self._process_line(entry, prev_entry, next_entry, segment_path, temp_dir)
                    if audio_path:
                        segment_index += 1
                        # Add small pause after each line
                        pause_path = os.path.join(temp_dir, f"segment_{segment_index:04d}.mp3")
                        self._generate_silence_mp3(0.2, pause_path)
                        audio_files.append(audio_path)
                        audio_files.append(pause_path)
                        segment_index += 1
                    time.sleep(0.1)  # Rate limiting

                elif entry_type == "pause":
                    seconds = entry.get("seconds", 0.5)
                    pause_path = os.path.join(temp_dir, f"segment_{segment_index:04d}.mp3")
                    self._generate_silence_mp3(seconds, pause_path)
                    audio_files.append(pause_path)
                    segment_index += 1

                elif entry_type == "scene" and include_scene_markers:
                    print(f"\n=== Scene: {entry.get('title', 'Untitled')} ===")
                    pause_path = os.path.join(temp_dir, f"segment_{segment_index:04d}.mp3")
                    self._generate_silence_mp3(1.0, pause_path)
                    audio_files.append(pause_path)
                    segment_index += 1

                elif entry_type == "sfx":
                    print(f"  [SFX placeholder: {entry.get('value', '')}]")
                    pause_path = os.path.join(temp_dir, f"segment_{segment_index:04d}.mp3")
                    self._generate_silence_mp3(0.3, pause_path)
                    audio_files.append(pause_path)
                    segment_index += 1

                elif entry_type == "performance":
                    print(f"  [Performance placeholder: {entry.get('value', '')}]")
                    pause_path = os.path.join(temp_dir, f"segment_{segment_index:04d}.mp3")
                    self._generate_silence_mp3(0.5, pause_path)
                    audio_files.append(pause_path)
                    segment_index += 1

                elif entry_type == "music":
                    print(f"  [Music cue: {entry.get('value')} at volume {entry.get('volume', 0.25)}]")

                elif entry_type == "bg":
                    print(f"  [Background: {entry.get('value')}]")

                elif entry_type == "end":
                    print(f"\n--- {entry.get('value', 'END')} ---")

            # Concatenate all audio files
            if audio_files:
                print(f"\nConcatenating {len(audio_files)} audio segments...")
                self._concatenate_audio_files(audio_files, output_path)
                print(f"Saved to: {output_path}")
            else:
                print("No audio segments generated.")

        finally:
            # Clean up temp files
            shutil.rmtree(temp_dir, ignore_errors=True)

        return output_path


def create_voice_map(voice_config_path: Optional[str] = None) -> dict[str, VoiceConfig]:
    """
    Create voice mapping from config file.

    Config file format (JSON):
    {
        "NARRATOR": {"voice_id": "...", "stability": 0.5, ...},
        "RYDER": {"voice_id": "...", ...}
    }
    """
    if voice_config_path and os.path.exists(voice_config_path):
        with open(voice_config_path, 'r') as f:
            config = json.load(f)

        return {
            speaker: VoiceConfig(
                voice_id=vc["voice_id"],
                stability=vc.get("stability", 0.5),
                similarity_boost=vc.get("similarity_boost", 0.75),
                style=vc.get("style", 0.0),
                use_speaker_boost=vc.get("use_speaker_boost", True)
            )
            for speaker, vc in config.items()
        }

    return {}


def main():
    parser = argparse.ArgumentParser(
        description="Generate audiobook from JSON story script using ElevenLabs"
    )
    parser.add_argument(
        "story_folder",
        help="Path to story folder containing chapter JSON files"
    )
    parser.add_argument(
        "--voices",
        required=True,
        help="Path to voice configuration JSON file"
    )
    parser.add_argument(
        "--api-key",
        help="ElevenLabs API key (or set ELEVENLABS_API_KEY env var)"
    )
    parser.add_argument(
        "--output",
        "-o",
        help="Output directory (default: same as story folder)"
    )
    parser.add_argument(
        "--chapter",
        "-c",
        help="Specific chapter to generate (e.g., 'ch1'). If not specified, generates all."
    )
    parser.add_argument(
        "--model",
        default="eleven_multilingual_v2",
        help="ElevenLabs model ID (default: eleven_multilingual_v2)"
    )

    args = parser.parse_args()

    # Get API key
    api_key = args.api_key or os.environ.get("ELEVENLABS_API_KEY")
    if not api_key:
        print("Error: ElevenLabs API key required. Use --api-key or set ELEVENLABS_API_KEY")
        return 1

    # Load voice configuration
    voice_map = create_voice_map(args.voices)
    if not voice_map:
        print("Error: No voices configured. Check your voice config file.")
        return 1

    # Setup generator
    generator = AudiobookGenerator(
        api_key=api_key,
        voice_map=voice_map,
        model_id=args.model
    )

    # Find story files
    story_folder = Path(args.story_folder)
    output_folder = Path(args.output) if args.output else story_folder
    output_folder.mkdir(parents=True, exist_ok=True)

    if args.chapter:
        chapters = [story_folder / f"{args.chapter}.json"]
    else:
        chapters = sorted(story_folder.glob("ch*.json"))

    if not chapters:
        print(f"No chapter files found in {story_folder}")
        return 1

    # Generate audio for each chapter
    for chapter_path in chapters:
        if not chapter_path.exists():
            print(f"Chapter file not found: {chapter_path}")
            continue

        output_path = output_folder / f"{chapter_path.stem}.mp3"

        try:
            generator.generate_chapter(
                str(chapter_path),
                str(output_path)
            )
        except Exception as e:
            print(f"Error generating {chapter_path}: {e}")
            raise

    print("\nAll chapters generated successfully!")
    return 0


if __name__ == "__main__":
    exit(main())
