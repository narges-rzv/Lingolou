# Performance Optimizations Plan

## Context

The app suffers from intermittent slowdowns during normal user actions. Initially suspected to be scale-to-zero (which has been fixed separately), but several additional root causes exist in the backend's SQLite locking behavior, event loop blocking in async handlers, and N+1 query patterns.

---

## Root Causes (by severity)

### 1. CRITICAL: SQLite lock contention from background tasks
**Files:** `webapp/models/database.py:48-61`, `webapp/services/generation.py:88-90`

`StaticPool` gives the entire app a **single shared SQLite connection**. Background tasks (`generate_story`, `generate_audio`) create a `db = SessionLocal()` and **hold it open for 10–30+ minutes** while looping through chapter generation. During that time, any write from a user request (create story, vote, etc.) must wait for an exclusive lock on that single connection — causing all user-facing writes to block until the background task releases its lock or yields.

SQLite DELETE journal mode (required for SMB) makes this worse: exclusive write locks are held for the full duration of each write, not just the statement.

**Fix:** Add `busy_timeout` PRAGMA so SQLite retries instead of immediately failing/hanging. Also restructure background task to commit and re-open the DB session between chapters (freeing the write lock between steps).

```python
# In _set_sqlite_pragma, add:
cursor.execute("PRAGMA busy_timeout=5000")  # retry for 5s instead of SQLITE_BUSY
```

And in `generation.py`, close and re-open the DB session between chapters instead of holding it the entire duration.

### 2. CRITICAL: `subprocess.run()` blocks the async event loop
**Files:** `webapp/api/stories.py:655`, `webapp/api/public.py:537`

Both `download_combined_audio` endpoints call synchronous `subprocess.run()` (ffmpeg, up to 120s timeout) directly inside an `async def` handler. This **blocks the entire Uvicorn event loop** — no other requests can be served while ffmpeg runs.

**Fix:** Wrap with `asyncio.to_thread()`:
```python
result = await asyncio.to_thread(subprocess.run, [...], capture_output=True, text=True, timeout=120)
```

### 3. HIGH: N+1 queries on all story list endpoints
**Files:** `webapp/api/stories.py:101-125`, `webapp/api/public.py:65-101`

`list_stories` and `list_public_stories` fetch N stories and then access `s.world.name`, `s.owner.username`, and `len(s.chapters)` in the list comprehension — each triggering a separate DB query. 20 stories = 60+ extra queries.

**Fix:** Add eager loading:
```python
from sqlalchemy.orm import joinedload, selectinload

stories = (
    db.query(Story)
    .options(joinedload(Story.world), selectinload(Story.chapters))
    .filter(...)
    .all()
)
```

### 4. MEDIUM: Frontend polls task status every 2 seconds with no backoff
**File:** `frontend/src/components/TaskProgress.tsx:63`

During a 15-minute generation, this fires 450+ requests. Each request hits the server and Redis. This compounds the SQLite contention in issue #1.

**Fix:** Implement exponential backoff starting at 2s, capping at 15s:
```typescript
const delay = Math.min(2000 * Math.pow(1.5, pollCount), 15000);
```

---

## Files to Modify

| File | Change |
|------|--------|
| `webapp/models/database.py` | Add `PRAGMA busy_timeout=5000` |
| `webapp/services/generation.py` | Re-open DB session per chapter; avoid holding session for full task duration |
| `webapp/api/stories.py` | Add `joinedload` to list_stories; wrap ffmpeg subprocess with `asyncio.to_thread` |
| `webapp/api/public.py` | Add `joinedload` to list_public_stories; wrap ffmpeg subprocess with `asyncio.to_thread` |
| `frontend/src/components/TaskProgress.tsx` | Exponential backoff for polling interval |

---

## Verification

1. Start a story generation task
2. While it runs, perform normal user actions (list stories, create story, vote) — these should respond in <500ms
3. Download combined audio in a separate tab — should not freeze other tabs
4. Monitor task progress polling — interval should increase over time in DevTools Network tab
5. Run `make test` to confirm no regressions
