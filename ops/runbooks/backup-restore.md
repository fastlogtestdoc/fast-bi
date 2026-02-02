# Runbook: Backup & Restore (PostgreSQL)

Covers full database backup via `pg_dump`, restore procedure, and consistency
considerations.

All commands assume you are in the repository root with the production stack
running.

---

## Backup

### Full backup (custom format, compressed)

```bash
docker compose -f docker-compose.prod.yml exec postgres \
  pg_dump -U superset -d superset -Fc -Z6 \
  > "backup_superset_$(date +%Y%m%d_%H%M%S).dump"
```

| Flag | Purpose |
|---|---|
| `-Fc` | Custom format (supports parallel restore, selective restore) |
| `-Z6` | Compression level 6 (good balance of speed and size) |

### Plain-SQL backup (alternative)

```bash
docker compose -f docker-compose.prod.yml exec postgres \
  pg_dump -U superset -d superset --clean --if-exists \
  > "backup_superset_$(date +%Y%m%d_%H%M%S).sql"
```

### Verify backup file

```bash
# Custom format: list contents
pg_restore -l backup_superset_*.dump | head -20

# Plain SQL: check file size and first lines
ls -lh backup_superset_*.sql
head -30 backup_superset_*.sql
```

### Scheduled backups

For automated daily backups, add a cron job on the Docker host:

```bash
0 3 * * * cd /path/to/repo && docker compose -f docker-compose.prod.yml exec -T postgres pg_dump -U superset -d superset -Fc -Z6 > /backups/superset_$(date +\%Y\%m\%d).dump 2>&1
```

---

## Restore

### Downtime impact

Restoring a database **requires stopping Superset services** to avoid
writes during the restore. PostgreSQL itself stays running.

### Step-by-step restore

```bash
# 1. Stop Superset services (keep postgres and redis running)
docker compose -f docker-compose.prod.yml stop \
  superset-web superset-worker superset-scheduler nginx

# 2. Drop and recreate the target database
docker compose -f docker-compose.prod.yml exec postgres \
  psql -U superset -d postgres -c "DROP DATABASE IF EXISTS superset;"
docker compose -f docker-compose.prod.yml exec postgres \
  psql -U superset -d postgres -c "CREATE DATABASE superset OWNER superset;"

# 3a. Restore from custom-format dump
docker compose -f docker-compose.prod.yml exec -T postgres \
  pg_restore -U superset -d superset --no-owner --role=superset \
  < backup_superset_20250101_030000.dump

# 3b. OR restore from plain-SQL dump
docker compose -f docker-compose.prod.yml exec -T postgres \
  psql -U superset -d superset \
  < backup_superset_20250101_030000.sql

# 4. Verify data
docker compose -f docker-compose.prod.yml exec postgres \
  psql -U superset -d superset -c "SELECT count(*) FROM ab_user;"

# 5. Restart Superset services
docker compose -f docker-compose.prod.yml up -d
```

### Restore to a different database name (non-destructive test)

```bash
# Create a test database
docker compose -f docker-compose.prod.yml exec postgres \
  psql -U superset -d postgres -c "CREATE DATABASE superset_restore_test OWNER superset;"

# Restore into it
docker compose -f docker-compose.prod.yml exec -T postgres \
  pg_restore -U superset -d superset_restore_test --no-owner --role=superset \
  < backup_superset_20250101_030000.dump

# Verify, then drop when done
docker compose -f docker-compose.prod.yml exec postgres \
  psql -U superset -d superset_restore_test -c "SELECT count(*) FROM ab_user;"
docker compose -f docker-compose.prod.yml exec postgres \
  psql -U superset -d postgres -c "DROP DATABASE superset_restore_test;"
```

---

## Consistency Notes

- **pg_dump produces a consistent snapshot** — it uses a single transaction,
  so the backup reflects the database state at the moment `pg_dump` starts.
- Superset can remain running during backup. Writes that occur after
  `pg_dump` begins are not included in the dump.
- For restore, Superset services **must be stopped** to prevent migrations
  or user activity from conflicting with the restore.
- Redis state (cache, Celery task queue) is **not backed up**. After a
  restore, the cache is stale and will be rebuilt on the next request.

---

## Backup Retention

Recommended minimum retention:

| Cadence | Keep |
|---|---|
| Daily | 7 days |
| Weekly | 4 weeks |
| Monthly | 6 months |

Remove old backups:

```bash
# Delete backups older than 7 days
find /backups -name "superset_*.dump" -mtime +7 -delete
```
