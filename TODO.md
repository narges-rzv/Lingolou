# TODO

## Deployment
- [x] Move from ACI to Azure Container Apps
- [x] Enable Azure Blob Storage for audio files (azure-storage-blob SDK)
- [x] Set up HTTPS (Container Apps provides TLS automatically)
- [ ] Re-enable Redis for task store (needs proper volume support)
- [ ] Decommission old ACI deployment (`az container delete -g Lingolou -n lingolou`)

## CI/CD
- [x] Set up CI pipeline triggered by git tags (`.github/workflows/deploy.yml`)
- [x] Switch Docker image labeling from `latest` to versioned tags (`bump-my-version`)
- [x] Set GitHub Actions secrets
- [ ] Auto-delete old container images from ACR

## UX
- [ ] Add ETag/Last-Modified cache headers for index.html (avoid stale SPA after deploys)

## Testing
- [ ] Improve overall test coverage (frontend currently 31%)
- [ ] Resolve all warnings

## Database
- [ ] Add Alembic migrations
