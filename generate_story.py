#!/usr/bin/env python3
"""
Story Script Generator for Lingolou Language Learning App

Uses OpenAI to generate JSON story scripts, then enhances them with
emotion tags for ElevenLabs voice synthesis.

Configuration is loaded from story_config.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING, cast

from openai import OpenAI
from openai.types.chat import ChatCompletionChunk

if TYPE_CHECKING:
    from collections.abc import Callable

    from openai import Stream

DEFAULT_CONFIG_PATH = Path(__file__).parent / "story_config.json"


def load_config(config_path: str | None = None) -> dict:
    """Load configuration from JSON file."""
    path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH

    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _build_language_level_instruction(config: dict) -> str:
    """Build the language-level sandwiching instruction for the system prompt."""
    level = config.get("language_level", 3)
    target_language = config.get("target_language", {})
    if isinstance(target_language, dict):
        lang_name = target_language.get("name", "the target language")
    else:
        lang_name = str(target_language)
    pct = level * 10

    instruction = (
        f"\n\nLANGUAGE TEACHING APPROACH:\n"
        f'This is a language-learning audiobook using the "sandwiching" technique:\n'
        f"1. A character says a word or short phrase in {lang_name}\n"
        f"2. Pause briefly so the listener can repeat\n"
        f"3. Another character repeats or explains the meaning in English\n"
        f"4. The {lang_name} phrase is said once more for reinforcement\n"
        f"\n"
        f"LANGUAGE LEVEL: {level}/10\n"
        f"Approximately {pct}% of all dialogue should be in {lang_name}."
    )

    if level <= 5:
        instruction += (
            f"\n\nBEGINNER LEVEL: Another character must explicitly translate or explain "
            f"each {lang_name} word/phrase in English. Keep target language to short words "
            f"and simple phrases (1-4 words). Use lots of repetition."
        )
    else:
        instruction += (
            f"\n\nADVANCED LEVEL: Characters may use longer {lang_name} sentences. "
            f"English explanation is optional — context, gestures, and repetition should "
            f"suffice. Dialogue can flow more naturally between languages."
        )

    return instruction


def build_story_system_prompt(config: dict) -> str:
    """Build the system prompt for story generation, incorporating config."""
    base_prompt = config.get("story_system_prompt", "")

    # Add character list
    characters = config.get("characters", {})
    if characters:
        char_list = "\n".join(f"- {name}: {desc}" for name, desc in characters.items())
        base_prompt += f"\n\nCharacters:\n{char_list}"

    # Add valid speakers
    speakers = config.get("valid_speakers", [])
    if speakers:
        base_prompt += f"\n\nValid speakers: {', '.join(speakers)}"

    # Add language level / sandwiching instructions
    base_prompt += _build_language_level_instruction(config)

    return base_prompt


def build_chapter_prompt(
    config: dict, user_prompt: str, chapter_num: int, total_chapters: int, previous_summary: str = ""
) -> str:
    """Build the prompt for generating a specific chapter."""
    prompt = user_prompt

    # Add character descriptions if not already in user prompt
    characters = config.get("characters", {})
    if characters and "Characters:" not in user_prompt:
        char_list = "\n".join(f"- {name}: {desc}" for name, desc in characters.items())
        prompt += f"\n\nCharacters:\n{char_list}"

    prompt += f"\n\nGenerate Chapter {chapter_num} of {total_chapters}."

    if previous_summary:
        prompt += f"\n\nPrevious chapter summary: {previous_summary}"
    else:
        prompt += "\n\nThis is the first chapter - introduce the characters and set up the adventure."

    if chapter_num == 2 and total_chapters > 2:
        prompt += "\n\nContinue the story, building tension."

    if chapter_num == total_chapters:
        prompt += "\n\nThis is the final chapter - resolve the adventure with a satisfying conclusion."

    prompt += "\n\nReturn ONLY valid JSON array, no markdown formatting or explanation."

    return prompt


def _stream_openai_response(
    client: OpenAI,
    messages: list[dict[str, str]],
    model: str,
    max_tokens: int,
    on_progress: Callable[[int], None] | None = None,
    progress_interval: int = 500,
) -> str:
    """
    Stream an OpenAI chat completion, calling on_progress with word count periodically.

    Args:
        client: OpenAI client instance.
        messages: Chat messages to send.
        model: Model name.
        max_tokens: Max completion tokens.
        on_progress: Optional callback receiving word count so far.
        progress_interval: Call on_progress every N chars of accumulated content.

    Returns:
        The full response content string.
    """
    raw_stream = client.chat.completions.create(
        model=model,
        messages=messages,  # type: ignore[arg-type]
        max_completion_tokens=max_tokens,
        stream=True,
    )
    stream = cast("Stream[ChatCompletionChunk]", raw_stream)

    content = ""
    last_reported_len = 0

    for chunk in stream:
        delta = chunk.choices[0].delta if chunk.choices else None
        if delta and delta.content:
            content += delta.content
            if on_progress and (len(content) - last_reported_len) >= progress_interval:
                last_reported_len = len(content)
                word_count = len(content.split())
                on_progress(word_count)

    # Final progress report
    if on_progress:
        on_progress(len(content.split()))

    return content.strip()


def generate_chapter(
    client: OpenAI,
    config: dict,
    user_prompt: str,
    chapter_num: int,
    total_chapters: int,
    previous_summary: str = "",
    model: str | None = None,
    on_progress: Callable[[int], None] | None = None,
) -> list:
    """Generate a single chapter using OpenAI."""
    settings = config.get("generation_settings", {})
    model = model or settings.get("default_model", "gpt-4.1")

    system_prompt = build_story_system_prompt(config)
    chapter_prompt = build_chapter_prompt(config, user_prompt, chapter_num, total_chapters, previous_summary)

    content = _stream_openai_response(
        client=client,
        messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": chapter_prompt}],
        model=model,
        max_tokens=settings.get("story_max_tokens", 16000),
        on_progress=on_progress,
    )

    if not content:
        raise ValueError("Empty response from model")

    # Remove markdown code blocks if present
    if content.startswith("```"):
        lines = content.split("\n")
        content = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])

    return json.loads(content)


def summarize_chapter(client: OpenAI, config: dict, chapter: list, model: str | None = None) -> str:
    """Generate a brief summary of a chapter for continuity."""
    settings = config.get("generation_settings", {})
    model = model or settings.get("default_model", "gpt-4.1")

    # Extract dialogue for context
    lines = [e.get("text", "") for e in chapter if e.get("type") == "line"]
    text_sample = " ".join(lines[:20])

    summary_system_msg = "Summarize this story chapter in 2-3 sentences for continuity with the next chapter."

    return _stream_openai_response(
        client=client,
        messages=[{"role": "system", "content": summary_system_msg}, {"role": "user", "content": text_sample}],
        model=model,
        max_tokens=settings.get("summary_max_tokens", 200),
    )


def enhance_chapter(
    client: OpenAI,
    config: dict,
    chapter: list,
    model: str | None = None,
    on_progress: Callable[[int], None] | None = None,
) -> list:
    """Add emotion tags to a chapter using OpenAI."""
    settings = config.get("generation_settings", {})
    model = model or settings.get("default_model", "gpt-4.1")

    enhance_prompt = config.get("enhance_system_prompt", "Add emotion tags to dialogue.")

    chapter_json = json.dumps(chapter, ensure_ascii=False, indent=2)
    user_content = f"Add emotion tags to this story script:\n\n{chapter_json}"

    content = _stream_openai_response(
        client=client,
        messages=[{"role": "system", "content": enhance_prompt}, {"role": "user", "content": user_content}],
        model=model,
        max_tokens=settings.get("enhance_max_tokens", 16000),
        on_progress=on_progress,
    )

    if not content:
        raise ValueError("Empty enhance response from model")

    # Remove markdown code blocks if present
    if content.startswith("```"):
        lines = content.split("\n")
        content = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])

    return json.loads(content)


def generate_story(
    config: dict,
    prompt: str,
    output_dir: str,
    num_chapters: int | None = None,
    model: str | None = None,
    enhance: bool = True,
) -> str:
    """
    Generate a complete story with multiple chapters.

    Args:
        config: Configuration dictionary
        prompt: Story description/requirements
        output_dir: Directory to save the story files
        num_chapters: Number of chapters to generate
        model: OpenAI model to use
        enhance: Whether to add emotion tags

    Returns:
        Path to the output directory
    """
    client = OpenAI()
    settings = config.get("generation_settings", {})

    num_chapters = num_chapters or settings.get("default_chapters", 3)
    model = model or settings.get("default_model", "gpt-4.1")

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Save config used for this generation
    config_copy_path = output_path / "story_config_used.json"
    with open(config_copy_path, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

    previous_summary = ""

    for ch_num in range(1, num_chapters + 1):
        print(f"\n{'=' * 50}")
        print(f"Generating Chapter {ch_num}/{num_chapters}...")
        print("=" * 50)

        # Generate chapter
        chapter = generate_chapter(
            client=client,
            config=config,
            user_prompt=prompt,
            chapter_num=ch_num,
            total_chapters=num_chapters,
            previous_summary=previous_summary,
            model=model,
        )

        # Save base chapter
        base_path = output_path / f"ch{ch_num}.json"
        with open(base_path, "w", encoding="utf-8") as f:
            json.dump(chapter, f, ensure_ascii=False, indent=2)
        print(f"Saved: {base_path}")

        # Enhance with emotion tags
        if enhance:
            print(f"Enhancing Chapter {ch_num} with emotion tags...")
            enhanced = enhance_chapter(client, config, chapter, model)

            enhanced_path = output_path / f"ch{ch_num}_enhanced.json"
            with open(enhanced_path, "w", encoding="utf-8") as f:
                json.dump(enhanced, f, ensure_ascii=False, indent=2)
            print(f"Saved: {enhanced_path}")

        # Get summary for next chapter
        if ch_num < num_chapters:
            print("Generating summary for continuity...")
            previous_summary = summarize_chapter(client, config, chapter, model)

    print(f"\n{'=' * 50}")
    print(f"Story generation complete!")
    print(f"Output directory: {output_path}")
    print("=" * 50)

    return str(output_path)


def main() -> int | None:
    """CLI entry point for story generation."""
    parser = argparse.ArgumentParser(description="Generate story scripts using OpenAI")
    parser.add_argument(
        "--config", default=str(DEFAULT_CONFIG_PATH), help=f"Path to config JSON file (default: {DEFAULT_CONFIG_PATH})"
    )
    parser.add_argument("--prompt", "-p", help="Story prompt/description (overrides config default_prompt)")
    parser.add_argument("--prompt-file", help="Read prompt from a text file")
    parser.add_argument("--output", "-o", required=True, help="Output directory for story files (e.g., stories/s2)")
    parser.add_argument("--chapters", "-n", type=int, help="Number of chapters to generate (default from config)")
    parser.add_argument("--model", "-m", help="OpenAI model to use (default from config)")
    parser.add_argument("--no-enhance", action="store_true", help="Skip emotion tag enhancement")
    parser.add_argument("--api-key", help="OpenAI API key (or set OPENAI_API_KEY env var)")

    args = parser.parse_args()

    # Set API key if provided
    if args.api_key:
        os.environ["OPENAI_API_KEY"] = args.api_key

    if not os.environ.get("OPENAI_API_KEY"):
        print("Error: OpenAI API key required. Use --api-key or set OPENAI_API_KEY")
        return 1

    # Load config
    try:
        config = load_config(args.config)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        return 1

    # Get prompt (priority: prompt-file > prompt arg > config default)
    if args.prompt_file:
        with open(args.prompt_file, "r") as f:
            prompt = f.read()
    elif args.prompt:
        prompt = args.prompt
    else:
        prompt = config.get("default_prompt", "Create a children's story for language learning.")

    try:
        generate_story(
            config=config,
            prompt=prompt,
            output_dir=args.output,
            num_chapters=args.chapters,
            model=args.model,
            enhance=not args.no_enhance,
        )
    except Exception as e:
        print(f"Error: {e}")
        raise

    return 0


if __name__ == "__main__":
    sys.exit(main())
