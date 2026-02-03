# Runbook: Bootstrap — First Start, Migrations, Admin User

Applies to the production stack (`docker-compose.prod.yml`).

---

## Prerequisites

| Requirement | Check |
|---|---|
| Docker Engine >= 24, Compose V2 | `docker compose version` |
| `.env` created from `.env.example` | `test -f .env && echo OK` |
| Secrets filled in `.env` | `SUPERSET_SECRET_KEY`, `POSTGRES_PASSWORD`, `SUPERSET_ADMIN_PASSWORD` set |

---

## 1. First Start

```bash
# Copy template and fill in real values
cp .env.example .env
# Edit .env — at minimum set:
#   SUPERSET_SECRET_KEY   (openssl rand -base64 42)
#   POSTGRES_PASSWORD
#   SUPERSET_ADMIN_PASSWORD
#   SUPERSET_ADMIN_USERNAME
#   SUPERSET_ADMIN_EMAIL

# Pull images
docker compose -f docker-compose.prod.yml pull

# Start the stack
docker compose -f docker-compose.prod.yml up -d
```

On first start, the `superset-init` service will:

1. Run `superset db upgrade` (apply all Alembic migrations)
2. Create the admin user via `superset fab create-admin`
3. Run `superset init` (create default roles and permissions)
4. Optionally load example data if `SUPERSET_LOAD_EXAMPLES=yes`

Once `superset-init` exits with code 0, `superset-web`, `superset-worker`,
and `superset-scheduler` start automatically.

### Verify

```bash
# All services healthy (superset-init should show Exit 0)
docker compose -f docker-compose.prod.yml ps

# Health endpoint
curl -f http://localhost:8080/health

# Login at http://localhost:8080 with the admin credentials from .env
```

---

## 2. Database Migrations

Migrations run automatically via `superset-init` on every `up`. To run them
manually (e.g. after pulling a new image version):

```bash
# Run migrations inside a one-off container
docker compose -f docker-compose.prod.yml run --rm superset-web \
  superset db upgrade
```

### Check migration status

```bash
docker compose -f docker-compose.prod.yml run --rm superset-web \
  superset db heads
```

### Downgrade (rollback one revision)

```bash
docker compose -f docker-compose.prod.yml run --rm superset-web \
  superset db downgrade -1
```

---

## 3. Admin User

The admin user is created by `superset-init` using:

| Environment variable | Used for |
|---|---|
| `SUPERSET_ADMIN_USERNAME` | Login username |
| `SUPERSET_ADMIN_PASSWORD` | Login password |
| `SUPERSET_ADMIN_EMAIL` | Account email |

### Create additional admin

```bash
docker compose -f docker-compose.prod.yml run --rm superset-web \
  superset fab create-admin \
    --username newadmin \
    --email newadmin@example.com \
    --password "secure-password" \
    --firstname New \
    --lastname Admin
```

### Reset a forgotten password

```bash
docker compose -f docker-compose.prod.yml run --rm superset-web \
  superset fab reset-password \
    --username admin \
    --password "new-secure-password"
```

---

## 4. Typical Errors

### `superset-init` exits with non-zero code

**Symptom**: `superset-web`, `superset-worker`, `superset-scheduler` never start.

```bash
docker compose -f docker-compose.prod.yml logs superset-init
```

| Cause | Fix |
|---|---|
| `FATAL: password authentication failed` | Check `POSTGRES_USER` / `POSTGRES_PASSWORD` in `.env` |
| `Connection refused` on port 5432 | Postgres not healthy yet — check `docker compose ps postgres` |
| `alembic.util.exc.CommandError` | Migration conflict — run `superset db heads` to diagnose |

### `SUPERSET_SECRET_KEY` error on startup

**Symptom**: `KeyError: 'SUPERSET_SECRET_KEY'` in logs.

**Fix**: Ensure `SUPERSET_SECRET_KEY` is set in `.env`. Generate one with:

```bash
openssl rand -base64 42
```

### `CSRF token missing` / 403 on POST requests

**Symptom**: Forms or API calls return HTTP 403.

The production config enables CSRF by default (`WTF_CSRF_ENABLED = True`).
Ensure API clients send the CSRF token from the `/api/v1/security/csrf_token/`
endpoint.

### Redis connection refused

```bash
docker compose -f docker-compose.prod.yml exec redis redis-cli ping
# Expected: PONG
```

If Redis is down, both cache and Celery will fail. Check:

```bash
docker compose -f docker-compose.prod.yml logs redis
```

### Celery worker not picking up tasks

```bash
# Check worker status
docker compose -f docker-compose.prod.yml exec superset-worker \
  celery -A superset.tasks.celery_app:app inspect active

# Check broker connectivity
docker compose -f docker-compose.prod.yml exec superset-worker \
  celery -A superset.tasks.celery_app:app inspect ping
```

### Config not loaded (defaults used instead of production)

**Symptom**: CSRF disabled, no ProxyFix, caching not working.

Verify `SUPERSET_CONFIG_PATH` is set:

```bash
docker compose -f docker-compose.prod.yml exec superset-web \
  env | grep SUPERSET_CONFIG_PATH
# Expected: SUPERSET_CONFIG_PATH=/app/superset_config_prod.py
```

Verify the config file is mounted:

```bash
docker compose -f docker-compose.prod.yml exec superset-web \
  ls -la /app/superset_config_prod.py
```
