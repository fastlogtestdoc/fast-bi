# Runbook: Healthchecks

Describes every health endpoint in the production Compose stack, expected
responses, and manual verification commands.

All commands assume you are in the repository root.

---

## Overview

| Service | Method | Target | Interval | Healthy response |
|---|---|---|---|---|
| nginx | HTTP GET | `localhost:8080/health` (host) | 30 s | HTTP 200 |
| superset-web | HTTP GET | `localhost:8088/health` (container-internal) | 30 s | HTTP 200, `"OK"` |
| postgres | CLI | `pg_isready` | 10 s | exit 0, "accepting connections" |
| redis | CLI | `redis-cli ping` | 10 s | `PONG` |
| superset-worker | CLI | `celery inspect ping` | 30 s | `{"ok": "pong"}` |
| superset-scheduler | — | disabled | — | (no healthcheck) |

---

## Manual Checks

### Nginx (reverse proxy)

The primary external health check goes through nginx on **host port 8080**:

```bash
curl -sf http://localhost:8080/health
# Expected: HTTP 200 with the Superset health payload
# This proves both nginx AND superset-web are reachable.
```

If this fails but superset-web is healthy, the issue is nginx itself:

```bash
docker compose -f docker-compose.prod.yml logs --tail 20 nginx
```

### Superset Web (Gunicorn)

superset-web is **not exposed to the host** — port 8088 is only reachable
inside the Docker network. Use `docker compose exec` to run the check
container-internally:

```bash
docker compose -f docker-compose.prod.yml exec superset-web \
  curl -f http://localhost:8088/health
# Expected: HTTP 200, body "OK"
```

Container-level healthcheck status:

```bash
docker inspect --format='{{.State.Health.Status}}' superset_prod_web
# Expected: healthy
```

Last 3 healthcheck results:

```bash
docker inspect --format='{{range .State.Health.Log}}{{.ExitCode}} {{.Output}}{{end}}' superset_prod_web
```

### PostgreSQL

```bash
docker compose -f docker-compose.prod.yml exec postgres \
  pg_isready -U superset -d superset
# Expected: /var/run/postgresql:5432 - accepting connections
```

Deeper check — verify the database is queryable:

```bash
docker compose -f docker-compose.prod.yml exec postgres \
  psql -U superset -d superset -c "SELECT 1;"
# Expected: single row with value 1
```

### Redis

```bash
docker compose -f docker-compose.prod.yml exec redis redis-cli ping
# Expected: PONG
```

Check memory usage and connected clients:

```bash
docker compose -f docker-compose.prod.yml exec redis redis-cli info memory | head -5
docker compose -f docker-compose.prod.yml exec redis redis-cli info clients | head -5
```

### Celery Worker

```bash
docker compose -f docker-compose.prod.yml exec superset-worker \
  celery -A superset.tasks.celery_app:app inspect ping
# Expected: -> celery@<hostname>: OK  {"ok": "pong"}
```

Check active tasks:

```bash
docker compose -f docker-compose.prod.yml exec superset-worker \
  celery -A superset.tasks.celery_app:app inspect active
```

### Celery Scheduler (Beat)

Beat has no built-in healthcheck. Verify it is running:

```bash
docker compose -f docker-compose.prod.yml ps superset-scheduler
# Expected: running (no restarts)
```

Check that it is scheduling tasks:

```bash
docker compose -f docker-compose.prod.yml logs --tail 10 superset-scheduler
# Expected: recent "Scheduler: Sending due task" lines
```

---

## All-Services Quick Check

```bash
docker compose -f docker-compose.prod.yml ps --format "table {{.Service}}\t{{.Status}}"
```

Expected output (approximate):

```
SERVICE              STATUS
nginx                Up (healthy)
postgres             Up (healthy)
redis                Up (healthy)
superset-init        Exited (0)
superset-scheduler   Up
superset-web         Up (healthy)
superset-worker      Up (healthy)
```

---

## Unhealthy Container Behaviour

Docker Compose `restart: unless-stopped` will restart containers that crash,
but **not** containers marked unhealthy. If a container is stuck in
`unhealthy` state:

```bash
# Restart a single service
docker compose -f docker-compose.prod.yml restart superset-web

# Or recreate it
docker compose -f docker-compose.prod.yml up -d --force-recreate superset-web
```
