# ADR-0001: Deployment mit Docker Compose

## Status

Accepted

## Kontext

Superset muss produktiv betrieben werden. Das Team benoetigt eine
reproduzierbare, wartbare Deployment-Strategie, die ohne dediziertes
Kubernetes-Cluster auskommt.

## Entscheidung

Wir deployen Superset mit **Docker Compose** und den folgenden Komponenten:

- **Gunicorn** als WSGI-Server (multi-worker, pre-fork)
- **PostgreSQL** als Metadaten-Datenbank
- **Redis** als Cache und Celery-Broker
- **Nginx** als Reverse Proxy mit TLS-Terminierung
- **Celery Worker + Beat** fuer asynchrone Queries und Scheduled Tasks

## Begruendung

### Wiederholbarkeit
Docker Compose definiert die gesamte Infrastruktur deklarativ in einer Datei.
Environments (Dev, Staging, Prod) lassen sich durch `.env`-Dateien und
Override-Files differenzieren. Rollbacks erfolgen durch Image-Tag-Wechsel.

### Separation of Concerns
Jede Komponente laeuft in einem eigenen Container mit eigenem Lifecycle,
eigenem Health-Check und eigenen Ressource-Limits. Das vereinfacht Debugging,
Scaling einzelner Komponenten und unabhaengige Updates.

### Security Baseline
- Container laufen als non-root User.
- Interne Services (PostgreSQL, Redis) sind nicht nach aussen exponiert.
- TLS wird an der Nginx-Schicht terminiert.
- Secrets werden via `.env` und Secret-Store injiziert, nicht im Image.

## Konsequenzen

- Single-Node-Deployment begrenzt die horizontale Skalierbarkeit.
- Bei Bedarf kann spaeter auf Kubernetes migriert werden; die Container-Images
  bleiben identisch.
- Das Team muss Backup-Strategien fuer PostgreSQL-Volumes definieren.
