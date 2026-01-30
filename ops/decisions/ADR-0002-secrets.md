# ADR-0002: Secrets Management

## Status

Accepted

## Kontext

Superset benoetigt Zugangsdaten fuer PostgreSQL, Redis, SMTP, OAuth-Provider
und Datenbank-Verbindungen. Diese Secrets muessen sicher verwaltet werden.

## Entscheidung

1. **Secrets werden ausschliesslich ueber `.env`-Dateien und/oder einen
   externen Secret-Store bereitgestellt.**
2. **Keine Secrets in Git** - weder im Code, noch in Konfigurationsdateien,
   noch in Docker-Images.
3. `.env`-Dateien sind in `.gitignore` eingetragen und werden nur auf dem
   Zielsystem abgelegt.
4. Fuer Produktion wird ein externer Secret-Store (z.B. HashiCorp Vault,
   AWS Secrets Manager oder SOPS) evaluiert und bei Bedarf integriert.

## Regeln

- `SECRET_KEY`, `SQLALCHEMY_DATABASE_URI`, `REDIS_URL` und alle Passwoerter
  muessen ueber Environment-Variablen konfiguriert werden.
- Docker Compose referenziert Secrets via `env_file` oder `environment` mit
  Variablen-Substitution aus `.env`.
- Private Keys (`*.pem`, `*.key`) werden nicht ins Repository eingecheckt.
- CI/CD-Pipelines beziehen Secrets aus dem jeweiligen Pipeline-Secret-Store
  (z.B. GitHub Actions Secrets).

## Konsequenzen

- Entwickler muessen eine lokale `.env`-Datei pflegen (Template wird als
  `.env.example` bereitgestellt).
- Onboarding-Dokumentation muss die Secret-Konfiguration beschreiben.
- Secret-Rotation erfordert Container-Neustarts oder ein Signal an Gunicorn.
