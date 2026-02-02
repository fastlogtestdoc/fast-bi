# Runbook: Incident Response

Defines priority classification, first-response checks per service, and
escalation criteria for the production Superset stack.

---

## Priority Classification

| Priority | Definition | Examples | Response target |
|---|---|---|---|
| **P1 — Critical** | Platform completely unavailable or data integrity at risk | Nginx/Superset return 5xx for all users; PostgreSQL down; data corruption suspected | Acknowledge within 15 min |
| **P2 — Major** | Significant functionality degraded | Celery workers down (no async queries, no reports); severe performance degradation; login broken | Acknowledge within 1 hour |
| **P3 — Minor** | Limited impact, workaround available | Single dashboard failing; cache cold after Redis restart; intermittent slow queries | Acknowledge within 4 hours |

---

## First Checks (all incidents)

Run this regardless of priority to establish baseline:

```bash
# 1. Service status overview
docker compose -f docker-compose.prod.yml ps --format "table {{.Service}}\t{{.Status}}"

# 2. Recent container restarts
docker compose -f docker-compose.prod.yml ps --format json | \
  python3 -c "import sys,json; [print(f'{s[\"Service\"]}: {s[\"Status\"]}') for s in json.load(sys.stdin)]"

# 3. External health endpoint
curl -sf -o /dev/null -w "%{http_code}" http://localhost:8080/health
# Expected: 200

# 4. Disk space on Docker host
df -h /var/lib/docker

# 5. Container resource usage
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}"
```

---

## Service-Specific Checks

### Nginx

```bash
# Check config validity
docker compose -f docker-compose.prod.yml exec nginx nginx -t

# Recent error log
docker compose -f docker-compose.prod.yml logs --tail 30 nginx | grep -i error
```

| Symptom | Likely cause | Action |
|---|---|---|
| 502 Bad Gateway | superset-web unreachable | Check superset-web healthcheck and logs |
| 503 Service Unavailable | superset-web not yet healthy | Wait for healthcheck or restart superset-web |
| Connection refused on port 8080 | nginx container down | `docker compose -f docker-compose.prod.yml restart nginx` |

### Superset Web

```bash
# Internal health
docker compose -f docker-compose.prod.yml exec superset-web \
  curl -sf http://localhost:8088/health

# Application logs (last 50 lines)
docker compose -f docker-compose.prod.yml logs --tail 50 superset-web

# Check Gunicorn worker count
docker compose -f docker-compose.prod.yml exec superset-web \
  ps aux | grep gunicorn
```

| Symptom | Likely cause | Action |
|---|---|---|
| `KeyError: 'SUPERSET_SECRET_KEY'` | Missing env variable | Fix `.env`, recreate container |
| `OperationalError: could not connect` | PostgreSQL unreachable | Check postgres service |
| OOM killed | Insufficient memory | Increase host memory or reduce Gunicorn workers |

### PostgreSQL

```bash
# Connection test
docker compose -f docker-compose.prod.yml exec postgres \
  pg_isready -U superset -d superset

# Active connections
docker compose -f docker-compose.prod.yml exec postgres \
  psql -U superset -d superset -c "SELECT count(*) FROM pg_stat_activity;"

# Long-running queries (> 60s)
docker compose -f docker-compose.prod.yml exec postgres \
  psql -U superset -d superset -c "SELECT pid, now()-query_start AS duration, query FROM pg_stat_activity WHERE state='active' AND now()-query_start > interval '60s';"

# Disk usage
docker compose -f docker-compose.prod.yml exec postgres \
  psql -U superset -d superset -c "SELECT pg_size_pretty(pg_database_size('superset'));"
```

| Symptom | Likely cause | Action |
|---|---|---|
| `FATAL: password authentication failed` | Wrong credentials | Verify `POSTGRES_PASSWORD` in `.env` |
| `FATAL: too many connections` | Connection leak | Restart superset-web; consider pgbouncer |
| Disk full | Volume full | Expand volume or clean WAL logs |

### Redis

```bash
# Ping
docker compose -f docker-compose.prod.yml exec redis redis-cli ping

# Memory usage
docker compose -f docker-compose.prod.yml exec redis redis-cli info memory | grep used_memory_human

# Key count
docker compose -f docker-compose.prod.yml exec redis redis-cli dbsize
```

| Symptom | Likely cause | Action |
|---|---|---|
| `MISCONF Redis is configured to save RDB snapshots` | Disk full or permissions | Check volume space |
| Connection refused | Container crashed | Check logs, restart redis |
| High memory | Cache not expiring | Verify `CACHE_DEFAULT_TIMEOUT` in config |

### Celery Worker

```bash
# Ping workers
docker compose -f docker-compose.prod.yml exec superset-worker \
  celery -A superset.tasks.celery_app:app inspect ping

# Active tasks
docker compose -f docker-compose.prod.yml exec superset-worker \
  celery -A superset.tasks.celery_app:app inspect active

# Reserved (queued) tasks
docker compose -f docker-compose.prod.yml exec superset-worker \
  celery -A superset.tasks.celery_app:app inspect reserved

# Recent logs
docker compose -f docker-compose.prod.yml logs --tail 30 superset-worker
```

| Symptom | Likely cause | Action |
|---|---|---|
| No response to ping | Worker crashed | Check logs, restart worker |
| Tasks stuck in reserved | Worker busy or hung | Restart worker container |
| `ConnectionError` to Redis | Redis down | Fix redis first |

### Celery Scheduler (Beat)

```bash
docker compose -f docker-compose.prod.yml logs --tail 20 superset-scheduler
```

| Symptom | Likely cause | Action |
|---|---|---|
| No "Sending due task" logs | Beat not running or PID file stale | Restart scheduler |
| Duplicate task execution | Multiple beat instances | Ensure only one scheduler runs |

---

## Escalation Criteria

| Escalate when | To whom |
|---|---|
| P1 not resolved within 30 min | Team lead / on-call manager |
| Data corruption suspected | DBA + team lead |
| Repeated P2 incidents (3+ in 24 h) | Team lead for root-cause review |
| Security breach suspected (unusual access patterns, leaked credentials) | Security team immediately |
| Infrastructure failure (host down, disk failure) | Infrastructure / platform team |

---

## Post-Incident

After every P1 and recurring P2:

1. **Collect evidence**: logs, metrics, timestamps, commands run
2. **Write a brief post-mortem**: what happened, root cause, fix applied
3. **Identify preventive actions**: monitoring gap, missing alert, config error
4. **File follow-up tasks**: track preventive actions to completion
