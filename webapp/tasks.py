"""
Celery tasks for story and audio generation.
"""

import json
import os
import sys
import tempfile
from pathlib import Path
from typing import List

from celery import shared_task
from celery.exceptions import SoftTimeLimitExceeded

# Add parent directory to path to import existing modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from webapp.models.database import SessionLocal, Story, Chapter, UsageLog


@shared_task(bind=True, max_retries=2, default_retry_delay=60)
def generate_story_task(
    self,
    story_id: int,
    user_id: int,
    prompt: str,
    num_chapters: int,
    enhance: bool
):
    """
    Celery task to generate story scripts.

    Args:
        story_id: Database ID of the story
        user_id: Database ID of the user
        prompt: Story generation prompt
        num_chapters: Number of chapters to generate
        enhance: Whether to enhance with emotion tags
    """
    from generate_story import load_config, generate_chapter, enhance_chapter, summarize_chapter
    from openai import OpenAI

    db = SessionLocal()

    try:
        # Update task state
        self.update_state(
            state="PROGRESS",
            meta={"progress": 0, "message": "Starting story generation..."}
        )

        story = db.query(Story).filter(Story.id == story_id).first()
        if not story:
            return {"status": "failed", "error": "Story not found"}

        # Load config
        config_path = Path(__file__).parent.parent / "story_config.json"
        config = load_config(str(config_path))

        # Use story's config override if present
        if story.config_json:
            override = json.loads(story.config_json)
            config.update(override)

        client = OpenAI()
        settings = config.get("generation_settings", {})
        model = settings.get("default_model", "gpt-4o")

        previous_summary = ""
        total_steps = num_chapters * (2 if enhance else 1)
        current_step = 0

        for ch_num in range(1, num_chapters + 1):
            # Find or create chapter
            chapter = db.query(Chapter).filter(
                Chapter.story_id == story_id,
                Chapter.chapter_number == ch_num
            ).first()

            if not chapter:
                chapter = Chapter(
                    story_id=story_id,
                    chapter_number=ch_num,
                    status="generating_script"
                )
                db.add(chapter)
                db.commit()

            chapter.status = "generating_script"
            db.commit()

            # Update progress
            self.update_state(
                state="PROGRESS",
                meta={
                    "progress": (current_step / total_steps) * 100,
                    "message": f"Generating chapter {ch_num}..."
                }
            )

            # Generate chapter
            chapter_data = generate_chapter(
                client=client,
                config=config,
                user_prompt=prompt or config.get("default_prompt", ""),
                chapter_num=ch_num,
                total_chapters=num_chapters,
                previous_summary=previous_summary,
                model=model
            )

            chapter.script_json = json.dumps(chapter_data, ensure_ascii=False)
            chapter.title = next(
                (e.get("title") for e in chapter_data if e.get("type") == "scene"),
                f"Chapter {ch_num}"
            )
            db.commit()
            current_step += 1

            # Enhance with emotion tags
            if enhance:
                self.update_state(
                    state="PROGRESS",
                    meta={
                        "progress": (current_step / total_steps) * 100,
                        "message": f"Enhancing chapter {ch_num}..."
                    }
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
            details=json.dumps({
                "story_id": story_id,
                "num_chapters": num_chapters,
                "enhanced": enhance
            })
        )
        db.add(usage_log)

        story.status = "completed"
        db.commit()

        return {
            "status": "completed",
            "story_id": story_id,
            "chapters": num_chapters
        }

    except SoftTimeLimitExceeded:
        story = db.query(Story).filter(Story.id == story_id).first()
        if story:
            story.status = "failed"
            db.commit()
        return {"status": "failed", "error": "Task timed out"}

    except Exception as e:
        story = db.query(Story).filter(Story.id == story_id).first()
        if story:
            story.status = "failed"
            db.commit()

        # Retry on transient errors
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e)

        return {"status": "failed", "error": str(e)}

    finally:
        db.close()


@shared_task(bind=True, max_retries=2, default_retry_delay=60)
def generate_audio_task(
    self,
    story_id: int,
    user_id: int,
    chapter_ids: List[int]
):
    """
    Celery task to generate audio for chapters.

    Args:
        story_id: Database ID of the story
        user_id: Database ID of the user
        chapter_ids: List of chapter IDs to generate audio for
    """
    from generate_audiobook import AudiobookGenerator, create_voice_map

    db = SessionLocal()

    try:
        self.update_state(
            state="PROGRESS",
            meta={"progress": 0, "message": "Starting audio generation..."}
        )

        # Load voice config
        voices_path = Path(__file__).parent.parent / "voices_config.json"
        if not voices_path.exists():
            return {"status": "failed", "error": "Voice config not found"}

        voice_map = create_voice_map(str(voices_path))
        if not voice_map:
            return {"status": "failed", "error": "No voices configured"}

        api_key = os.environ.get("ELEVENLABS_API_KEY")
        if not api_key:
            return {"status": "failed", "error": "ElevenLabs API key not set"}

        generator = AudiobookGenerator(
            api_key=api_key,
            voice_map=voice_map,
            model_id="eleven_v3"
        )

        # Create output directory
        output_dir = Path(__file__).parent / "static" / "audio" / str(story_id)
        output_dir.mkdir(parents=True, exist_ok=True)

        total_chapters = len(chapter_ids)
        total_characters = 0

        for i, chapter_id in enumerate(chapter_ids):
            chapter = db.query(Chapter).filter(Chapter.id == chapter_id).first()
            if not chapter:
                continue

            chapter.status = "generating_audio"
            db.commit()

            self.update_state(
                state="PROGRESS",
                meta={
                    "progress": (i / total_chapters) * 100,
                    "message": f"Generating audio for chapter {chapter.chapter_number}..."
                }
            )

            # Get script
            script_json = chapter.enhanced_json or chapter.script_json
            if not script_json:
                chapter.status = "failed"
                chapter.error_message = "No script available"
                db.commit()
                continue

            script = json.loads(script_json)

            # Count characters for usage tracking
            for entry in script:
                if entry.get("type") == "line":
                    total_characters += len(entry.get("text", ""))

            # Write temp script file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                json.dump(script, f, ensure_ascii=False)
                temp_script_path = f.name

            try:
                output_path = output_dir / f"ch{chapter.chapter_number}.mp3"
                generator.generate_chapter(temp_script_path, str(output_path))

                # Get audio duration
                import subprocess
                result = subprocess.run(
                    ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                     "-of", "default=noprint_wrappers=1:nokey=1", str(output_path)],
                    capture_output=True, text=True
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
            details=json.dumps({
                "story_id": story_id,
                "chapters": len(chapter_ids)
            }),
            characters_used=total_characters
        )
        db.add(usage_log)
        db.commit()

        return {
            "status": "completed",
            "story_id": story_id,
            "chapters_generated": len(chapter_ids)
        }

    except SoftTimeLimitExceeded:
        for chapter_id in chapter_ids:
            chapter = db.query(Chapter).filter(Chapter.id == chapter_id).first()
            if chapter and chapter.status == "generating_audio":
                chapter.status = "failed"
                chapter.error_message = "Task timed out"
                db.commit()
        return {"status": "failed", "error": "Task timed out"}

    except Exception as e:
        for chapter_id in chapter_ids:
            chapter = db.query(Chapter).filter(Chapter.id == chapter_id).first()
            if chapter and chapter.status == "generating_audio":
                chapter.status = "failed"
                chapter.error_message = str(e)
                db.commit()

        if self.request.retries < self.max_retries:
            raise self.retry(exc=e)

        return {"status": "failed", "error": str(e)}

    finally:
        db.close()
