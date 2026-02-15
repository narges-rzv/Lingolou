# Refactor Plan — Next Session

## Phase 1: Housekeeping
1. **Add test artifacts to `.gitignore`**: `.coverage`, `htmlcov/`, `frontend/coverage/`, `frontend/playwright-report/`, `frontend/test-results/`, `stories/`
2. **Consolidate requirements.txt**: Merge root `requirements.txt` and `webapp/requirements.txt` into a single `requirements.txt` at root. Update CLAUDE.md instruction "Add to both requirements.txt" → "Add to requirements.txt". Fix duplicate `httpx` entry.
3. **Remove or relocate `skill.md`**: It's outdated session context sitting in the repo root. Either delete it or move relevant parts to CLAUDE.md / memory.
4. **Commit all uncommitted source files**: The ~20 modified/new files (BYOK, public library, votes, reports, settings, crypto, Celery removal) are the working code. Commit them as a feature commit.

## Phase 2: Code Review & Tighten
5. **Review each modified backend file** for:
   - Unused imports
   - Inconsistent error handling
   - Missing input validation
   - TODO/FIXME comments that should be resolved
   - Hardcoded values that should be config
6. **Review each modified frontend file** for:
   - Unused imports/variables
   - Console.log statements left in
   - Inconsistent error handling
   - Accessibility issues
7. **Review database models** for:
   - Missing indexes
   - Cascade delete consistency
   - Column types/constraints

## Phase 3: Test Updates
8. **Update CLAUDE.md** project structure to include all current files (public.py, votes.py, reports.py, crypto.py, tests/, etc.)
9. **Run full test suite** (`make test`) and fix any failures caused by refactoring
10. **Add any missing test coverage** for newly committed code
11. **Update README** if any setup steps changed

## Uncommitted Files Inventory

### Modified (existing files changed):
- `frontend/src/api.js` — likely BYOK/public API additions
- `frontend/src/app.css` — new styles
- `frontend/src/components/Navbar.jsx` — new nav links (Settings, Public Stories)
- `frontend/src/components/TaskProgress.jsx` — updates
- `frontend/src/main.jsx` — new routes
- `frontend/src/pages/EditStory.jsx` — updates
- `frontend/src/pages/NewStory.jsx` — BYOK key status, free tier
- `frontend/src/pages/StoryDetail.jsx` — visibility, share, voting
- `generate_audiobook.py` — updates
- `requirements.txt` — new deps
- `webapp/api/auth.py` — API key endpoints
- `webapp/api/stories.py` — generation with BYOK/free tier
- `webapp/main.py` — new routers, middleware
- `webapp/models/database.py` — new models (Vote, Report, PlatformBudget)
- `webapp/models/schemas.py` — new schemas
- `webapp/services/auth.py` — updates
- `webapp/services/generation.py` — migrated from Celery

### Deleted:
- `webapp/celery_app.py` — replaced by BackgroundTasks
- `webapp/tasks.py` — merged into generation.py

### New (untracked):
- `frontend/src/components/BudgetBanner.jsx`
- `frontend/src/components/PublicChapterList.jsx`
- `frontend/src/components/PublicScriptViewer.jsx`
- `frontend/src/context/LanguageContext.jsx`
- `frontend/src/languages.js`
- `frontend/src/pages/PublicStories.jsx`
- `frontend/src/pages/PublicStoryDetail.jsx`
- `frontend/src/pages/Settings.jsx`
- `frontend/src/pages/SharedStoryView.jsx`
- `webapp/api/public.py`
- `webapp/api/reports.py`
- `webapp/api/votes.py`
- `webapp/services/crypto.py`
