# TODO

## Deployment
- [x] Move from ACI to Azure Container Apps
- [x] Enable Azure Blob Storage for audio files (azure-storage-blob SDK)
- [x] Set up HTTPS (Container Apps provides TLS automatically)
- [x] Custom domain (www.lingolou.app)
- [x] Decommission old ACI deployment
- [ ] Auto-delete old container images from ACR

## CI/CD
- [x] Set up CI pipeline triggered by git tags (`.github/workflows/deploy.yml`)
- [x] Switch Docker image labeling from `latest` to versioned tags (`bump-my-version`)
- [x] Set GitHub Actions secrets
- [x] Add lint + test gate before deploy

## UX
- [ ] Add ETag/Last-Modified cache headers for index.html (avoid stale SPA after deploys)

## Testing
- [ ] Improve overall test coverage (frontend currently 31%)
- [ ] Resolve all warnings

## Database
- [ ] Add Alembic migrations

## Future Improvements (optional)
- [ ] Redis for persistent task progress tracking (survives container restarts)
- [ ] PostgreSQL (replace SQLite for production scalability)
