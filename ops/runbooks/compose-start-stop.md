# Runbook: Docker Compose Start / Stop / Maintain

Applies to `docker-compose.prod.yml` in the repository root.

## Prerequisites

- Docker Engine >= 24 and Docker Compose V2 (`docker compose`)
- `.env` file created from `.env.example` with real secrets filled in

All commands assume you are in the repository root.

---

## Start

```bash
# First-time setup: copy and edit secrets
cp .env.example .env
# Edit .env — set SUPERSET_SECRET_KEY, POSTGRES_PASSWORD, SUPERSET_ADMIN_PASSWORD

# Pull images and start all services (detached)
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
```

The `superset-init` service runs database migrations and creates the admin user
on first start. It exits automatically once finished.

### Verify

```bash
# All containers should be healthy (except superset-init which exits 0)
docker compose -f docker-compose.prod.yml ps

# Health endpoint through nginx
curl -f http://localhost:8080/health
```

---

## Stop

```bash
# Graceful stop (keeps volumes)
docker compose -f docker-compose.prod.yml down

# Stop and remove named volumes (DESTROYS DATA)
docker compose -f docker-compose.prod.yml down -v
```

---

## Logs

```bash
# All services
docker compose -f docker-compose.prod.yml logs -f

# Single service
docker compose -f docker-compose.prod.yml logs -f superset-web
docker compose -f docker-compose.prod.yml logs -f postgres
docker compose -f docker-compose.prod.yml logs -f nginx
```

---

## Reset Volumes

Use this to wipe all persistent state and start from scratch.

```bash
docker compose -f docker-compose.prod.yml down -v
# Verify volumes are removed
docker volume ls | grep superset_prod
# Start fresh
docker compose -f docker-compose.prod.yml up -d
```

---

## Upgrade Images

```bash
# Pull new images
docker compose -f docker-compose.prod.yml pull

# Recreate containers with new images (zero-downtime not guaranteed)
docker compose -f docker-compose.prod.yml up -d --force-recreate

# Verify versions
docker compose -f docker-compose.prod.yml exec superset-web superset version
```

To pin a specific version, set `SUPERSET_IMAGE_TAG` in `.env`:

```bash
SUPERSET_IMAGE_TAG=4.1.1
```

---

## Troubleshooting Checks

### 1. Containers not starting

```bash
docker compose -f docker-compose.prod.yml ps -a
docker compose -f docker-compose.prod.yml logs superset-init
```

Common cause: `superset-init` failed (bad DB credentials, migration error).

### 2. Database connection refused

```bash
# Check postgres is healthy
docker compose -f docker-compose.prod.yml exec postgres pg_isready -U superset
# Check superset can reach postgres
docker compose -f docker-compose.prod.yml exec superset-web \
  python -c "from sqlalchemy import create_engine; e = create_engine('postgresql+psycopg2://superset:YOURPW@postgres:5432/superset'); print(e.connect())"
```

### 3. Redis not reachable

```bash
docker compose -f docker-compose.prod.yml exec redis redis-cli ping
# Expected: PONG
```

### 4. Nginx 502 Bad Gateway

```bash
# superset-web must be healthy before nginx starts
docker compose -f docker-compose.prod.yml ps superset-web
docker compose -f docker-compose.prod.yml logs nginx
```

Fix: wait for superset-web healthcheck to pass, then restart nginx:

```bash
docker compose -f docker-compose.prod.yml restart nginx
```

### 5. Celery worker not processing tasks

```bash
docker compose -f docker-compose.prod.yml exec superset-worker \
  celery -A superset.tasks.celery_app:app inspect active
docker compose -f docker-compose.prod.yml logs superset-worker
```

### 6. Full restart (nuclear option)

```bash
docker compose -f docker-compose.prod.yml down -v
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
```

---

## Ports and URLs

| Service           | Internal Port | Host Port | URL                          |
|-------------------|---------------|-----------|------------------------------|
| nginx             | 80            | 8080      | http://localhost:8080        |
| superset-web      | 8088          | —         | (internal only)              |
| postgres          | 5432          | —         | (internal only)              |
| redis             | 6379          | —         | (internal only)              |
