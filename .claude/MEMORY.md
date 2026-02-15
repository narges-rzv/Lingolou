# Lingolou Project Memory

## Current State (Feb 2026)
- All test infrastructure is in place and passing (backend + frontend + E2E)
- README was rewritten and committed
- There are ~20 uncommitted source files (features added before test suite): BYOK, public library, votes, reports, settings, crypto, etc.
- These uncommitted changes are the WORKING CODE — they must be committed, not reverted

## Next Session Plan: Full Refactor
See `refactor-plan.md` in this folder for the detailed plan.

Key goals:
1. Consolidate duplicate `requirements.txt` (root vs webapp/) into one
2. Commit all uncommitted source files as a single feature commit
3. Review and tighten all code (loose ends, unused imports, consistency)
4. Update tests to match any refactored code
5. Update README and CLAUDE.md after refactoring
6. Add `.coverage`, `frontend/coverage/`, `frontend/playwright-report/`, `frontend/test-results/`, `stories/` to `.gitignore`

## Testing Infrastructure
- **Backend**: pytest + pytest-cov + pytest-asyncio, tests in `webapp/tests/`
- **Frontend**: Vitest + React Testing Library + MSW v2, tests in `frontend/src/test/`
- **E2E**: Playwright, specs in `frontend/src/e2e/`
- **Run all**: `make test` from project root

## Key Testing Gotchas
- In-memory SQLite requires `StaticPool` (otherwise each connection gets a fresh empty db)
- MSW v2 with jsdom requires full URLs in handlers — set `environmentOptions.jsdom.url` in vitest.config.js
- `URLSearchParams` body in fetch doesn't work with MSW interceptor in jsdom — test construction separately or patch fetch
- Vitest config must exclude `src/e2e/**` to avoid collecting Playwright files

## Structural Issues to Fix
- Two `requirements.txt` files with overlapping deps (root + webapp/) — consolidate to one
- `httpx` listed twice in webapp/requirements.txt
- `.coverage`, `frontend/coverage/`, test artifacts not in `.gitignore`
- `skill.md` in project root is outdated session context — should be removed or moved to memory
- CLAUDE.md project structure section is outdated (missing public.py, votes.py, reports.py, crypto.py, tests/)

## User Preferences
- Prefers clean commits with clear messages
- Wants tests for every new feature
- Asks to push explicitly — don't push without asking
