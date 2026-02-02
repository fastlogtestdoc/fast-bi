# Runbook: Release Process

Describes versioning, tagging, image promotion, and rollback.

---

## Versionierung

This project follows [Semantic Versioning](https://semver.org/):

```
MAJOR.MINOR.PATCH   (e.g. 1.2.3)
```

| Component | When to bump |
|---|---|
| MAJOR | Breaking changes (config format, API, migration incompatibility) |
| MINOR | New features, non-breaking enhancements |
| PATCH | Bug fixes, security patches, dependency updates |

---

## Release Workflow

### 1. Prepare

```bash
# Ensure you are on a clean, up-to-date master/main
git checkout master && git pull origin master

# Verify CI is green on the latest commit
gh run list --branch master --limit 5
```

### 2. Tag

```bash
# Create an annotated tag
git tag -a v1.2.3 -m "Release v1.2.3: <short summary>"

# Push the tag
git push origin v1.2.3
```

### 3. CI builds the image

The `ci.yml` workflow triggers on push to master. Every commit produces an
image tagged with its short SHA in GHCR:

```
ghcr.io/<owner>/<repo>/superset:<short-sha>
```

To promote a specific commit as a release, re-tag the image:

```bash
# Pull the CI-built image
docker pull ghcr.io/<owner>/<repo>/superset:abc1234

# Tag it with the release version
docker tag ghcr.io/<owner>/<repo>/superset:abc1234 \
           ghcr.io/<owner>/<repo>/superset:v1.2.3
docker tag ghcr.io/<owner>/<repo>/superset:abc1234 \
           ghcr.io/<owner>/<repo>/superset:latest

# Push release tags
docker push ghcr.io/<owner>/<repo>/superset:v1.2.3
docker push ghcr.io/<owner>/<repo>/superset:latest
```

### 4. Deploy

Update `.env` on the target host:

```bash
SUPERSET_IMAGE_TAG=v1.2.3
```

Then pull and recreate:

```bash
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
```

---

## Rollback

### Quick rollback (previous image)

```bash
# Set the previous version in .env
SUPERSET_IMAGE_TAG=v1.2.2

# Recreate with previous image
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
```

### Rollback with database migration revert

If the new version included a DB migration that needs reverting:

```bash
# 1. Run downgrade with the NEW image (it contains the migration code)
docker compose -f docker-compose.prod.yml run --rm superset-web \
  superset db downgrade -1

# 2. Then switch to the old image
# Edit .env: SUPERSET_IMAGE_TAG=v1.2.2
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
```

### Identify which image is running

```bash
docker compose -f docker-compose.prod.yml ps --format json | \
  jq -r '.[] | select(.Service=="superset-web") | .Image'
```

---

## Image Tags Reference

| Tag pattern | Source | Mutable? |
|---|---|---|
| `abc1234` (short SHA) | CI on every push to master | No (immutable) |
| `v1.2.3` | Manual promotion after QA | No (by convention) |
| `latest` | Points to the most recent release | Yes (re-tagged) |

---

## Checklist Before Releasing

- [ ] CI pipeline green on the target commit
- [ ] Trivy scan passed (no HIGH/CRITICAL unfixed)
- [ ] DB migrations tested (upgrade + downgrade)
- [ ] `.env.example` updated if new variables were added
- [ ] `ops/runbooks/` updated if operational procedures changed
- [ ] Git tag created and pushed
- [ ] Image re-tagged with version and `latest`
