"""
Background task services for story and audio generation.

Uses in-memory task store with FastAPI BackgroundTasks (no Celery/Redis needed).
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

from webapp.models.database import Chapter, SessionLocal, Story, UsageLog, World

# In-memory task status store
# Keys are task_id strings, values are status dicts
task_store: dict[str, dict[str, Any]] = {}


def update_task_status(
    task_id: str,
    status: str,
    progress: float = 0,
    message: str = "",
    result: dict | None = None,
    words_generated: int | None = None,
    estimated_total_words: int | None = None,
) -> None:
    """Update task status in in-memory store."""
    task_store[task_id] = {
        "task_id": task_id,
        "status": status,
        "progress": progress,
        "message": message,
        "result": result,
        "words_generated": words_generated,
        "estimated_total_words": estimated_total_words,
        "updated_at": datetime.now(UTC).isoformat(),
    }


def get_task_status(task_id: str) -> dict[str, Any] | None:
    """Get task status from in-memory store."""
    return task_store.get(task_id)


def find_active_task_for_story(story_id: int) -> dict[str, Any] | None:
    """Find a running or pending task for the given story_id.

    Task keys follow the pattern: story_{id}_{ts} or audio_{id}_{ts}.
    Returns the most recently updated active task, or None.
    """
    prefixes = (f"story_{story_id}_", f"audio_{story_id}_")
    active = []
    for key, val in task_store.items():
        if any(key.startswith(p) for p in prefixes) and val.get("status") in ("pending", "running"):
            active.append(val)
    if not active:
        return None
    # Return the most recently updated one
    active.sort(key=lambda t: t.get("updated_at", ""), reverse=True)
    return active[0]


def cancel_task(task_id: str) -> bool:
    """Mark a task as cancelled. Returns True if task was running."""
    status = task_store.get(task_id)
    if status and status["status"] in ("pending", "running"):
        task_store[task_id]["status"] = "cancelled"
        task_store[task_id]["message"] = "Task cancelled by user"
        return True
    return False


def generate_story(
    task_id: str,
    story_id: int,
    user_id: int,
    prompt: str,
    num_chapters: int,
    enhance: bool,
    openai_api_key: str | None = None,
    use_platform_key: bool = False,
) -> None:
    """
    Generate story scripts (runs as BackgroundTask).

    This is a synchronous function because the OpenAI SDK calls are blocking.
    FastAPI's BackgroundTasks runs it in a thread pool automatically.
    """
    from openai import OpenAI

    from generate_story import enhance_chapter, generate_chapter, load_config, summarize_chapter

    db = SessionLocal()

    try:
        update_task_status(task_id, "running", 0, "Starting story generation...")

        story = db.query(Story).filter(Story.id == story_id).first()
        if not story:
            update_task_status(task_id, "failed", 0, "Story not found")
            return

        # Load config
        config_path = Path(__file__).parent.parent.parent / "story_config.json"
        config = load_config(str(config_path))

        # Override with world config if story belongs to a world
        if story.world_id:
            world = db.query(World).filter(World.id == story.world_id).first()
            if world:
                if world.characters_json:
                    config["characters"] = json.loads(world.characters_json)
                if world.valid_speakers_json:
                    config["valid_speakers"] = json.loads(world.valid_speakers_json)

        if story.config_json:
            override = json.loads(story.config_json)
            config.update(override)

        client = OpenAI(api_key=openai_api_key) if openai_api_key else OpenAI()
        settings = config.get("generation_settings", {})
        model = settings.get("default_model", "gpt-4o")

        previous_summary = ""
        total_steps = num_chapters * (2 if enhance else 1)
        current_step = 0
        words_generated = 0
        estimated_total_words = num_chapters * 500  # heuristic: ~500 words/chapter

        for ch_num in range(1, num_chapters + 1):
            # Check for cancellation
            if task_store.get(task_id, {}).get("status") == "cancelled":
                story.status = "failed"
                db.commit()
                return

            # Find or create chapter
            chapter = db.query(Chapter).filter(Chapter.story_id == story_id, Chapter.chapter_number == ch_num).first()

            if not chapter:
                chapter = Chapter(story_id=story_id, chapter_number=ch_num, status="generating_script")
                db.add(chapter)
                db.commit()

            chapter.status = "generating_script"
            db.commit()

            progress = (current_step / total_steps) * 100
            update_task_status(
                task_id,
                "running",
                progress,
                f"Generating chapter {ch_num}...",
                words_generated=words_generated,
                estimated_total_words=estimated_total_words,
            )

            # Generate chapter
            chapter_data = generate_chapter(
                client=client,
                config=config,
                user_prompt=prompt or config.get("default_prompt", ""),
                chapter_num=ch_num,
                total_chapters=num_chapters,
                previous_summary=previous_summary,
                model=model,
            )

            chapter.script_json = json.dumps(chapter_data, ensure_ascii=False)
            chapter.title = next(
                (e.get("title") for e in chapter_data if e.get("type") == "scene"), f"Chapter {ch_num}"
            )
            db.commit()
            current_step += 1

            # Count words generated in this chapter
            for entry in chapter_data:
                if entry.get("type") == "line":
                    words_generated += len(entry.get("text", "").split())

            # Enhance with emotion tags
            if enhance:
                progress = (current_step / total_steps) * 100
                update_task_status(
                    task_id,
                    "running",
                    progress,
                    f"Enhancing chapter {ch_num}...",
                    words_generated=words_generated,
                    estimated_total_words=estimated_total_words,
                )

                enhanced_data = enhance_chapter(client, config, chapter_data, model)
                chapter.enhanced_json = json.dumps(enhanced_data, ensure_ascii=False)
                db.commit()
                current_step += 1

            # Get summary for next chapter
            if ch_num < num_chapters:
                previous_summary = summarize_chapter(client, config, chapter_data, model)

            chapter.status = "completed"
            db.commit()

        # Log usage
        usage_log = UsageLog(
            user_id=user_id,
            action="story_generation",
            details=json.dumps({"story_id": story_id, "num_chapters": num_chapters, "enhanced": enhance}),
        )
        db.add(usage_log)

        # Track platform budget if using platform key
        if use_platform_key:
            from webapp.models.database import COST_PER_STORY, PlatformBudget

            budget = db.query(PlatformBudget).first()
            if budget:
                budget.total_spent = round(budget.total_spent + COST_PER_STORY, 2)
                budget.free_stories_generated += 1

        story.status = "completed"
        db.commit()

        update_task_status(
            task_id, "completed", 100, "Story generation completed", {"story_id": story_id, "chapters": num_chapters}
        )

    except Exception as e:
        story = db.query(Story).filter(Story.id == story_id).first()
        if story:
            story.status = "failed"
            db.commit()
        update_task_status(task_id, "failed", 0, str(e))

    finally:
        db.close()


def generate_audio(
    task_id: str,
    story_id: int,
    user_id: int,
    chapter_ids: list[int],
    elevenlabs_api_key: str | None = None,
    voice_override: dict | None = None,
) -> None:
    """
    Generate audio for chapters (runs as BackgroundTask).

    Synchronous function — runs in thread pool via BackgroundTasks.
    """
    from generate_audiobook import AudiobookGenerator, create_voice_map

    db = SessionLocal()

    try:
        update_task_status(task_id, "running", 0, "Starting audio generation...")

        # Check if story has a world with voice config
        story = db.query(Story).filter(Story.id == story_id).first()
        world_voice_config = None
        if story and story.world_id:
            world = db.query(World).filter(World.id == story.world_id).first()
            if world and world.voice_config_json:
                world_voice_config = json.loads(world.voice_config_json)

        if world_voice_config:
            # Build voice map from world config directly
            voice_map = {
                speaker: settings
                for speaker, settings in world_voice_config.items()
                if isinstance(settings, dict) and "voice_id" in settings
            }
        else:
            # Fall back to voices_config.json from disk
            voices_path = Path(__file__).parent.parent.parent / "voices_config.json"
            if not voices_path.exists():
                update_task_status(task_id, "failed", 0, "Voice config not found")
                return

            voice_map = create_voice_map(str(voices_path))

        # Apply user overrides on top of defaults
        if voice_override:
            voice_map.update(voice_override)

        if not voice_map:
            update_task_status(task_id, "failed", 0, "No voices configured")
            return

        api_key = elevenlabs_api_key or os.environ.get("ELEVENLABS_API_KEY")
        if not api_key:
            update_task_status(task_id, "failed", 0, "ElevenLabs API key not set")
            return

        generator = AudiobookGenerator(api_key=api_key, voice_map=voice_map, model_id="eleven_v3")

        # Create output directory
        output_dir = Path(__file__).parent.parent / "static" / "audio" / str(story_id)
        output_dir.mkdir(parents=True, exist_ok=True)

        total_characters = 0

        # Pre-count total entries across all chapters for granular progress
        chapter_scripts = {}  # chapter_id -> parsed script
        total_entries = 0
        for chapter_id in chapter_ids:
            chapter = db.query(Chapter).filter(Chapter.id == chapter_id).first()
            if not chapter:
                continue
            script_json = chapter.enhanced_json or chapter.script_json
            if script_json:
                script = json.loads(script_json)
                chapter_scripts[chapter_id] = script
                total_entries += len(script)
        entries_done = 0

        for chapter_id in chapter_ids:
            # Check for cancellation
            if task_store.get(task_id, {}).get("status") == "cancelled":
                return

            chapter = db.query(Chapter).filter(Chapter.id == chapter_id).first()
            if not chapter:
                continue

            chapter.status = "generating_audio"
            db.commit()

            progress = (entries_done / max(total_entries, 1)) * 100
            update_task_status(
                task_id, "running", progress, f"Generating audio for chapter {chapter.chapter_number}..."
            )

            # Get script
            script = chapter_scripts.get(chapter_id)
            if not script:
                chapter.status = "failed"
                chapter.error_message = "No script available"
                db.commit()
                continue

            # Count characters for usage tracking
            for entry in script:
                if entry.get("type") == "line":
                    total_characters += len(entry.get("text", ""))

            # Progress callback — fires after each entry within a chapter
            def make_callback(ch_num: int, base_done: int) -> Callable[[int, int], None]:
                def _cb(entry_index: int, entry_total: int) -> None:
                    nonlocal entries_done
                    entries_done = base_done + entry_index
                    pct = (entries_done / max(total_entries, 1)) * 100
                    update_task_status(
                        task_id,
                        "running",
                        pct,
                        f"Generating audio for chapter {ch_num} ({entry_index}/{entry_total} segments)...",
                    )

                return _cb

            # Write temp script file
            with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
                json.dump(script, f, ensure_ascii=False)
                temp_script_path = f.name

            try:
                output_path = output_dir / f"ch{chapter.chapter_number}.mp3"
                cb = make_callback(chapter.chapter_number, entries_done)
                generator.generate_chapter(temp_script_path, str(output_path), progress_callback=cb)

                # Get audio duration
                result = subprocess.run(  # noqa: S603
                    [
                        "ffprobe",
                        "-v",
                        "error",
                        "-show_entries",
                        "format=duration",
                        "-of",
                        "default=noprint_wrappers=1:nokey=1",
                        str(output_path),
                    ],
                    capture_output=True,
                    text=True,
                )
                duration = float(result.stdout.strip()) if result.stdout.strip() else None

                chapter.audio_path = f"/static/audio/{story_id}/ch{chapter.chapter_number}.mp3"
                chapter.audio_duration = duration
                chapter.status = "completed"
                db.commit()

            finally:
                os.unlink(temp_script_path)

        # Log usage
        usage_log = UsageLog(
            user_id=user_id,
            action="audio_generation",
            details=json.dumps({"story_id": story_id, "chapters": len(chapter_ids)}),
            characters_used=total_characters,
        )
        db.add(usage_log)
        db.commit()

        update_task_status(
            task_id,
            "completed",
            100,
            "Audio generation completed",
            {"story_id": story_id, "chapters_generated": len(chapter_ids)},
        )

    except Exception as e:
        for chapter_id in chapter_ids:
            chapter = db.query(Chapter).filter(Chapter.id == chapter_id).first()
            if chapter and chapter.status == "generating_audio":
                chapter.status = "failed"
                chapter.error_message = str(e)
                db.commit()
        update_task_status(task_id, "failed", 0, str(e))

    finally:
        db.close()
