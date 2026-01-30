# Ops Foundation

Operational documentation and runbooks for the Superset production deployment.

## Zielbild Architektur

The target architecture runs Apache Superset behind an Nginx reverse proxy,
backed by PostgreSQL as the metadata database and Redis for caching and Celery
task brokering. All components are containerised and orchestrated with
Docker Compose for reproducible deployments.

```
                ┌──────────┐
  Clients ────▶ │  Nginx   │
                └────┬─────┘
                     │
              ┌──────▼──────┐
              │  Gunicorn   │
              │  (Superset) │
              └──┬──────┬───┘
                 │      │
        ┌────────▼┐  ┌──▼──────┐
        │ Postgres │  │  Redis  │
        └─────────┘  └─────────┘
```

## Komponentenuebersicht

| Komponente | Rolle | Port |
|---|---|---|
| Nginx | TLS termination, reverse proxy, static files | 443 / 80 |
| Gunicorn | WSGI application server for Superset | 8088 (internal) |
| Superset | BI platform (Flask backend + React frontend) | - |
| PostgreSQL | Metadata store (users, dashboards, charts) | 5432 (internal) |
| Redis | Cache backend and Celery broker | 6379 (internal) |
| Celery Worker | Async query execution, alerts, reports | - |
| Celery Beat | Periodic task scheduler | - |

## Deployment-Optionen

1. **Docker Compose (gewaehlt)** - single-node deployment for small/medium teams.
   See [ADR-0001](decisions/ADR-0001-deployment.md).
2. **Kubernetes / Helm** - for larger-scale or multi-tenant deployments.
   Not in scope for the initial rollout.
3. **Managed cloud services** - e.g. Preset Cloud. Evaluated but dismissed for
   data-sovereignty requirements.

## Betrieb und Verantwortlichkeiten

| Bereich | Verantwortlich | Artefakte |
|---|---|---|
| Deployment & Infra | Platform / DevOps | `docker-compose.yml`, Nginx config |
| Secrets Management | Platform / DevOps | `.env`, secret store |
| Monitoring & Alerting | Platform / DevOps | Runbooks under `/ops/runbooks/` |
| User Management | BI Team | RBAC configuration in Superset |
| Dashboard Reviews | BI Team | Review checklists under `/ops/checklists/` |
| Incident Response | Platform + BI Team | Runbooks under `/ops/runbooks/` |
| Architecture Decisions | Team Lead / Architect | ADRs under `/ops/decisions/` |
