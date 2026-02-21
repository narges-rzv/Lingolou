# TODO

## Deployment
- [ ] Move from ACI to Azure Container Apps
- [ ] Enable Azure Blob Storage for audio files (azure-storage-blob SDK)
- [ ] Re-enable Redis for task store (needs proper volume support)
- [ ] Set up HTTPS (requires custom domain first)

## CI/CD
- [ ] Set up CI pipeline triggered by git tags
- [ ] Switch Docker image labeling from `latest` to versioned tags (auto bump)
- [ ] Auto-delete old container images from ACR

## UX
- [ ] Add ETag/Last-Modified cache headers for index.html (avoid stale SPA after deploys)

## Testing
- [ ] Improve overall test coverage (frontend currently 31%)

## Database
- [ ] Add Alembic migrations
