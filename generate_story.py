#!/usr/bin/env python3
"""
Story Script Generator for Lingolou Language Learning App

Uses OpenAI to generate JSON story scripts, then enhances them with
emotion tags for ElevenLabs voice synthesis.
"""

import json
import os
import argparse
from pathlib import Path
from openai import OpenAI


DEFAULT_PROMPT = """Create a children's story for language learning featuring the PAW Patrol characters.
The story should teach basic Farsi (Persian) words and phrases to English-speaking children.

Characters:
- NARRATOR: Tells the story
- RYDER: The human leader
- CHASE: Police pup, brave and loyal
- MARSHALL: Fire pup, clumsy but enthusiastic
- SKYE: Aviation pup, cheerful and confident
- ROCKY: Recycling pup, clever and resourceful
- RUBBLE: Construction pup, strong and friendly
- ZUMA: Water rescue pup, laid-back and cool
- EVEREST: Snow rescue pup, adventurous
- POUYA: A new Farsi-speaking pup who teaches the others

The story should:
1. Have an exciting adventure plot appropriate for ages 4-8
2. Introduce 5-10 Farsi words/phrases naturally through dialogue
3. Include Pouya teaching the other pups simple Farsi expressions
4. Have moments of humor and teamwork
5. Be split into 3 chapters with clear scene breaks
"""

STORY_SYSTEM_PROMPT = """You are a children's story writer creating scripts for an audiobook language learning app.

Generate stories in JSON format. Each chapter is a JSON array with the following entry types:

1. Scene markers:
   {"type": "scene", "id": "ch1_s1", "title": "Scene Title"}

2. Background/ambience descriptions (for audio production):
   {"type": "bg", "value": "Description of environment sounds"}

3. Music cues:
   {"type": "music", "value": "Music description", "volume": 0.25}

4. Character dialogue:
   {"type": "line", "speaker": "CHARACTER_NAME", "lang": "en", "text": "Dialogue text"}

   For Farsi lines, include transliteration and translation:
   {"type": "line", "speaker": "POUYA", "lang": "fa", "text": "سلام!", "transliteration": "Salâm!", "gloss_en": "Hello!"}

5. Pauses:
   {"type": "pause", "seconds": 0.5}

6. Sound effects:
   {"type": "sfx", "value": "Description of sound effect"}

7. Performance markers (crowd reactions):
   {"type": "performance", "value": "LAUGH"} or {"type": "performance", "value": "CHEER"}

8. Chapter end:
   {"type": "end", "value": "END_CHAPTER_1"}

Valid speakers: NARRATOR, RYDER, CHASE, MARSHALL, SKYE, ROCKY, RUBBLE, ZUMA, EVEREST, POUYA, ALL_PUPS, ALL_PUPS_AND_RYDER

Important:
- Keep dialogue natural and age-appropriate
- Include pauses after important Farsi words for learning
- Use sfx and music cues to make the story engaging
- Each chapter should be 2-4 scenes
- Farsi text must use actual Persian script with accurate transliteration
"""

ENHANCE_SYSTEM_PROMPT = """You are an audio director adding emotion and delivery tags to a story script.

Add emotion tags in square brackets at the START of each line's text field. The tag describes HOW the line should be spoken.

Example transformations:
- "Ready for action, Ryder!" → "[excited] Ready for action, Ryder!"
- "We have to help her!" → "[determined] We have to help her!"
- "سلام!" → "[friendly] سلام!"

Available emotion tags:
- High energy: excited, enthusiastic, happy, cheerful, playful, laughing
- Calm/steady: warm, gentle, calm, relaxed, steady, matter-of-fact
- Confident: confident, commanding, determined, proud, strong
- Teaching: teacherly, encouraging, clear, thoughtful
- Concerned: concerned, worried, serious, urgent, alarmed
- Uncertain: confused, sheepish, careful, trying
- Positive: pleased, smiling, welcoming, friendly, amused
- Narrative: adventurous, curious, hopeful, teasing
- Alert: alert, focused, reassuring, bright

Guidelines:
- Match the emotion to the context and punctuation
- NARRATOR lines often use: warm, matter-of-fact, adventurous, curious, hopeful
- Exclamations (!) often pair with: excited, enthusiastic, alarmed, determined
- Questions (?) often pair with: curious, confused, concerned
- Teaching moments use: teacherly, encouraging, clear
- Keep the JSON structure exactly the same, only add [emotion] tags to text fields
- Only add tags to "line" type entries

Return the complete enhanced JSON.
"""


def generate_chapter(
    client: OpenAI,
    prompt: str,
    chapter_num: int,
    total_chapters: int,
    previous_summary: str = "",
    model: str = "gpt-4o"
) -> dict:
    """Generate a single chapter using OpenAI."""

    chapter_prompt = f"""{prompt}

Generate Chapter {chapter_num} of {total_chapters}.

{"Previous chapter summary: " + previous_summary if previous_summary else "This is the first chapter - introduce the characters and set up the adventure."}

{"Continue the story, building tension." if chapter_num == 2 else ""}
{"This is the final chapter - resolve the adventure with a satisfying conclusion." if chapter_num == total_chapters else ""}

Return ONLY valid JSON array, no markdown formatting or explanation."""

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": STORY_SYSTEM_PROMPT},
            {"role": "user", "content": chapter_prompt}
        ],
        temperature=0.8,
        max_tokens=4000
    )

    content = response.choices[0].message.content.strip()

    # Remove markdown code blocks if present
    if content.startswith("```"):
        lines = content.split("\n")
        content = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])

    return json.loads(content)


def summarize_chapter(client: OpenAI, chapter: list, model: str = "gpt-4o") -> str:
    """Generate a brief summary of a chapter for continuity."""

    # Extract dialogue for context
    lines = [e.get("text", "") for e in chapter if e.get("type") == "line"]
    text_sample = " ".join(lines[:20])  # First 20 lines

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "Summarize this story chapter in 2-3 sentences for continuity with the next chapter."},
            {"role": "user", "content": text_sample}
        ],
        temperature=0.3,
        max_tokens=200
    )

    return response.choices[0].message.content.strip()


def enhance_chapter(client: OpenAI, chapter: list, model: str = "gpt-4o") -> list:
    """Add emotion tags to a chapter using OpenAI."""

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": ENHANCE_SYSTEM_PROMPT},
            {"role": "user", "content": f"Add emotion tags to this story script:\n\n{json.dumps(chapter, ensure_ascii=False, indent=2)}"}
        ],
        temperature=0.4,
        max_tokens=8000
    )

    content = response.choices[0].message.content.strip()

    # Remove markdown code blocks if present
    if content.startswith("```"):
        lines = content.split("\n")
        content = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])

    return json.loads(content)


def generate_story(
    prompt: str,
    output_dir: str,
    num_chapters: int = 3,
    model: str = "gpt-4o",
    enhance: bool = True
) -> str:
    """
    Generate a complete story with multiple chapters.

    Args:
        prompt: Story description/requirements
        output_dir: Directory to save the story files
        num_chapters: Number of chapters to generate
        model: OpenAI model to use
        enhance: Whether to add emotion tags

    Returns:
        Path to the output directory
    """
    client = OpenAI()

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    previous_summary = ""

    for ch_num in range(1, num_chapters + 1):
        print(f"\n{'='*50}")
        print(f"Generating Chapter {ch_num}/{num_chapters}...")
        print('='*50)

        # Generate chapter
        chapter = generate_chapter(
            client=client,
            prompt=prompt,
            chapter_num=ch_num,
            total_chapters=num_chapters,
            previous_summary=previous_summary,
            model=model
        )

        # Save base chapter
        base_path = output_path / f"ch{ch_num}.json"
        with open(base_path, 'w', encoding='utf-8') as f:
            json.dump(chapter, f, ensure_ascii=False, indent=2)
        print(f"Saved: {base_path}")

        # Enhance with emotion tags
        if enhance:
            print(f"Enhancing Chapter {ch_num} with emotion tags...")
            enhanced = enhance_chapter(client, chapter, model)

            enhanced_path = output_path / f"ch{ch_num}_enhanced.json"
            with open(enhanced_path, 'w', encoding='utf-8') as f:
                json.dump(enhanced, f, ensure_ascii=False, indent=2)
            print(f"Saved: {enhanced_path}")

        # Get summary for next chapter
        if ch_num < num_chapters:
            print("Generating summary for continuity...")
            previous_summary = summarize_chapter(client, chapter, model)

    print(f"\n{'='*50}")
    print(f"Story generation complete!")
    print(f"Output directory: {output_path}")
    print('='*50)

    return str(output_path)


def main():
    parser = argparse.ArgumentParser(
        description="Generate story scripts using OpenAI"
    )
    parser.add_argument(
        "--prompt", "-p",
        default=DEFAULT_PROMPT,
        help="Story prompt/description (default: PAW Patrol Farsi learning story)"
    )
    parser.add_argument(
        "--prompt-file",
        help="Read prompt from a text file instead"
    )
    parser.add_argument(
        "--output", "-o",
        required=True,
        help="Output directory for story files (e.g., stories/s2)"
    )
    parser.add_argument(
        "--chapters", "-n",
        type=int,
        default=3,
        help="Number of chapters to generate (default: 3)"
    )
    parser.add_argument(
        "--model", "-m",
        default="gpt-4o",
        help="OpenAI model to use (default: gpt-4o)"
    )
    parser.add_argument(
        "--no-enhance",
        action="store_true",
        help="Skip emotion tag enhancement"
    )
    parser.add_argument(
        "--api-key",
        help="OpenAI API key (or set OPENAI_API_KEY env var)"
    )

    args = parser.parse_args()

    # Set API key if provided
    if args.api_key:
        os.environ["OPENAI_API_KEY"] = args.api_key

    if not os.environ.get("OPENAI_API_KEY"):
        print("Error: OpenAI API key required. Use --api-key or set OPENAI_API_KEY")
        return 1

    # Get prompt
    if args.prompt_file:
        with open(args.prompt_file, 'r') as f:
            prompt = f.read()
    else:
        prompt = args.prompt

    try:
        generate_story(
            prompt=prompt,
            output_dir=args.output,
            num_chapters=args.chapters,
            model=args.model,
            enhance=not args.no_enhance
        )
    except Exception as e:
        print(f"Error: {e}")
        raise

    return 0


if __name__ == "__main__":
    exit(main())
