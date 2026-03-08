# TODO

## Deployment
- [x] Move from ACI to Azure Container Apps
- [x] Enable Azure Blob Storage for audio files (azure-storage-blob SDK)
- [x] Set up HTTPS (Container Apps provides TLS automatically)
- [x] Custom domain (www.lingolou.app)
- [x] Decommission old ACI deployment
- [x] Auto-delete old container images from ACR (purge step in deploy.yml)

## CI/CD
- [x] Set up CI pipeline triggered by git tags (`.github/workflows/deploy.yml`)
- [x] Switch Docker image labeling from `latest` to versioned tags (`bump-my-version`)
- [x] Set GitHub Actions secrets
- [x] Add lint + test gate before deploy
- [x] CI writes VERSION file from git tag for fast startup

## Performance
- [x] ETag middleware for GET /api/* JSON responses (304 Not Modified)
- [x] Voices cache — in-memory with 1h TTL, non-blocking startup warm
- [x] Version-based fast startup — skip Alembic + seeding when version unchanged
- [x] Embedded Redis in Docker — task state persists across restarts/scale-to-zero
- [x] Frontend 503 retry with exponential backoff for cold-start resilience
- [x] Voice config path fix — env var + auto-copy bundled default

## Testing
- [ ] Improve overall test coverage (frontend currently 31%)
- [ ] Resolve all warnings

## Database
- [x] Add Alembic migrations
- [ ] Populate voice_config_json for all built-in worlds (PAW Patrol, Winnie the Pooh, Bluey, Peppa Pig)

## Future Improvements (optional)
- [ ] PostgreSQL (replace SQLite for production scalability)
- [ ] Add ETag/Last-Modified for index.html (avoid stale SPA after deploys)
