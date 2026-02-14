# Refactor Plan: Remove Celery/Redis

## Why Remove Celery?

1. **Simplify deployment** — No Redis dependency means cheaper cloud hosting
2. **Redis Cloud free tier** works but adds complexity
3. **Memorystore** costs ~$30/mo for a small project
4. **For low traffic** (1-5 users, 10-20 generations/hour), Celery is overkill

## Current Architecture

```
[Frontend] → [FastAPI] → [Redis] → [Celery Worker]
                              ↓
                         [Background Task]
                              ↓
                         [OpenAI / ElevenLabs]
```

**Files involved:**
- `webapp/celery_app.py` — Celery configuration
- `webapp/tasks.py` — Background tasks (generate_story_task, generate_audio_task)
- `webapp/api/stories.py` — Endpoints that dispatch Celery tasks

## Proposed Architecture

### Option A: FastAPI BackgroundTasks (Simplest)

```
[Frontend] → [FastAPI] → [BackgroundTasks]
                              ↓
                         [In-process async task]
                              ↓
                         [OpenAI / ElevenLabs]
```

**Pros:**
- No external dependencies
- Works on Cloud Run out of the box
- Simple to implement

**Cons:**
- Tasks die if server restarts mid-generation
- No task persistence or retry across restarts
- Progress tracking needs in-memory store (lost on restart)

**Best for:** MVP, low traffic, single instance

### Option B: Cloud Tasks + Cloud Run Jobs (Google Cloud Native)

```
[Frontend] → [FastAPI] → [Cloud Tasks Queue]
                              ↓
                         [Cloud Run Job]
                              ↓
                         [OpenAI / ElevenLabs]
```

**Pros:**
- Managed queue, automatic retries
- Scales to zero (pay only when running)
- Tasks persist across restarts

**Cons:**
- Google Cloud lock-in
- More setup (Cloud Tasks API, separate job container)
- Slightly more complex than Option A

**Best for:** Production on Google Cloud

### Recommendation

**Start with Option A** (FastAPI BackgroundTasks) for simplicity. Migrate to Option B later if needed.

---

## Migration Plan: Option A (FastAPI BackgroundTasks)

### Step 1: Create async task functions

Move task logic from `webapp/tasks.py` to new file `webapp/services/generation.py` (or rename existing):

```python
# webapp/services/generation.py
import asyncio
from webapp.models.database import SessionLocal

# In-memory task status store
task_status = {}  # {task_id: {status, progress, message, result}}

async def generate_story_async(task_id: str, story_id: int, ...):
    task_status[task_id] = {"status": "running", "progress": 0}
    try:
        # ... generation logic ...
        task_status[task_id] = {"status": "completed", "progress": 100}
    except Exception as e:
        task_status[task_id] = {"status": "failed", "error": str(e)}
```

### Step 2: Update API endpoints

Replace Celery task dispatch with BackgroundTasks:

```python
# webapp/api/stories.py
from fastapi import BackgroundTasks

@router.post("/{story_id}/generate")
async def generate_story(
    story_id: int,
    background_tasks: BackgroundTasks,
    ...
):
    task_id = f"story_{story_id}_{int(time.time())}"
    background_tasks.add_task(generate_story_async, task_id, story_id, ...)
    return {"task_id": task_id}
```

### Step 3: Update task status endpoint

Read from in-memory store instead of Celery:

```python
@router.get("/tasks/{task_id}")
async def get_task_status(task_id: str):
    status = task_status.get(task_id)
    if not status:
        raise HTTPException(404, "Task not found")
    return status
```

### Step 4: Remove Celery files

- Delete `webapp/celery_app.py`
- Delete or repurpose `webapp/tasks.py`
- Remove `celery[redis]` and `redis` from `requirements.txt`
- Remove `REDIS_URL` from environment/docs

### Step 5: Update frontend

No changes needed — API contract stays the same (POST to generate, poll task status).

### Step 6: Update documentation

- Remove Celery/Redis from README setup
- Remove Redis from CLAUDE.md
- Update architecture diagrams

---

## Files to Modify

| File | Change |
|------|--------|
| `webapp/api/stories.py` | Replace Celery dispatch with BackgroundTasks |
| `webapp/services/generation.py` | Move task logic here (async functions) |
| `webapp/celery_app.py` | **Delete** |
| `webapp/tasks.py` | **Delete** (logic moved to services) |
| `requirements.txt` | Remove `celery[redis]`, `redis` |
| `webapp/requirements.txt` | Remove `celery[redis]`, `redis` |
| `README.md` | Remove Celery/Redis setup instructions |
| `CLAUDE.md` | Update architecture, remove Celery references |

## Testing the Migration

1. Start backend only: `uvicorn webapp.main:app --reload`
2. Create a story via UI
3. Click "Generate" — should work without Celery worker
4. Check task progress polling works
5. Verify audio generation works

## Rollback Plan

Keep `celery_app.py` and `tasks.py` in a branch until migration is verified.

---

## Cloud Deployment (Post-Refactor)

After removing Celery, deployment simplifies to:

| Service | Purpose | Cost |
|---------|---------|------|
| Cloud Run | Backend API | ~$0 (free tier) |
| Cloud SQL (PostgreSQL) | Database | ~$7-10/mo |
| Cloud Storage | Audio files | ~$0.02/GB |
| Secret Manager | API keys | Free |

**No Redis needed.**

## Future: Option B Migration

If you outgrow Option A (need persistence, retries, multiple instances):

1. Create a Cloud Run Job for generation tasks
2. Set up Cloud Tasks queue
3. API pushes to queue instead of BackgroundTasks
4. Job pulls from queue and processes

This is more work but scales better.

---

## Appendix: Current Celery Tasks (webapp/tasks.py)

### generate_story_task

**Signature:**
```python
generate_story_task(story_id, user_id, prompt, num_chapters, enhance)
```

**What it does:**
1. Loads story config from `story_config.json`
2. For each chapter:
   - Creates/updates Chapter record with status="generating_script"
   - Calls `generate_chapter()` from `generate_story.py`
   - Stores result in `chapter.script_json`
   - If enhance=True, calls `enhance_chapter()` and stores in `chapter.enhanced_json`
   - Calls `summarize_chapter()` for context continuity
3. Updates progress via `self.update_state()`
4. Logs usage in UsageLog table
5. Sets `story.status = "completed"`

**Dependencies:**
- `generate_story.py`: `load_config`, `generate_chapter`, `enhance_chapter`, `summarize_chapter`
- OpenAI client

### generate_audio_task

**Signature:**
```python
generate_audio_task(story_id, user_id, chapter_ids)
```

**What it does:**
1. Loads voice config from `voices_config.json`
2. Creates `AudiobookGenerator` from `generate_audiobook.py`
3. For each chapter:
   - Sets status="generating_audio"
   - Gets script from `chapter.enhanced_json` or `chapter.script_json`
   - Writes temp script file
   - Calls `generator.generate_chapter()`
   - Gets duration via ffprobe
   - Stores `chapter.audio_path` and `chapter.audio_duration`
4. Updates progress via `self.update_state()`
5. Logs usage with character count

**Dependencies:**
- `generate_audiobook.py`: `AudiobookGenerator`, `create_voice_map`
- ElevenLabs API key
- ffprobe (for duration)

### Progress Tracking Pattern

Current Celery pattern:
```python
self.update_state(state="PROGRESS", meta={"progress": 50, "message": "..."})
```

New BackgroundTasks pattern:
```python
task_status[task_id] = {"status": "running", "progress": 50, "message": "..."}
```

### Error Handling

Current: Celery retries up to 2 times with 60s delay
New: No automatic retry (could add manual retry button in UI)
