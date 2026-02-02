"""
Production Superset configuration.

Loaded via SUPERSET_CONFIG_PATH environment variable.
All secrets are read from environment variables — no defaults for sensitive values.
"""

import json
import logging
import os

from celery.schedules import crontab

# ---------------------------------------------------------------------------
# Secret key — required, no fallback
# ---------------------------------------------------------------------------
SECRET_KEY = os.environ["SUPERSET_SECRET_KEY"]

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
DATABASE_DIALECT = os.getenv("DATABASE_DIALECT", "postgresql")
DATABASE_USER = os.getenv("DATABASE_USER", "superset")
DATABASE_PASSWORD = os.environ.get("DATABASE_PASSWORD", "")
DATABASE_HOST = os.getenv("DATABASE_HOST", "postgres")
DATABASE_PORT = os.getenv("DATABASE_PORT", "5432")
DATABASE_DB = os.getenv("DATABASE_DB", "superset")

SQLALCHEMY_DATABASE_URI = (
    f"{DATABASE_DIALECT}://"
    f"{DATABASE_USER}:{DATABASE_PASSWORD}@"
    f"{DATABASE_HOST}:{DATABASE_PORT}/{DATABASE_DB}"
)

EXAMPLES_USER = os.getenv("EXAMPLES_USER", DATABASE_USER)
EXAMPLES_PASSWORD = os.getenv("EXAMPLES_PASSWORD", DATABASE_PASSWORD)
EXAMPLES_HOST = os.getenv("EXAMPLES_HOST", DATABASE_HOST)
EXAMPLES_PORT = os.getenv("EXAMPLES_PORT", DATABASE_PORT)
EXAMPLES_DB = os.getenv("EXAMPLES_DB", DATABASE_DB)

SQLALCHEMY_EXAMPLES_URI = os.getenv(
    "SUPERSET__SQLALCHEMY_EXAMPLES_URI",
    (
        f"{DATABASE_DIALECT}://"
        f"{EXAMPLES_USER}:{EXAMPLES_PASSWORD}@"
        f"{EXAMPLES_HOST}:{EXAMPLES_PORT}/{EXAMPLES_DB}"
    ),
)

# ---------------------------------------------------------------------------
# CSRF protection
# ---------------------------------------------------------------------------
WTF_CSRF_ENABLED = True
WTF_CSRF_EXEMPT_LIST = [
    "superset.views.api.validate_sql_json",
]

# ---------------------------------------------------------------------------
# ProxyFix — trust the nginx reverse proxy headers
# ---------------------------------------------------------------------------
ENABLE_PROXY_FIX = True
PROXY_FIX_CONFIG = {
    "x_for": 1,
    "x_proto": 1,
    "x_host": 1,
    "x_prefix": 1,
    "x_port": 1,
}

# ---------------------------------------------------------------------------
# Redis
# ---------------------------------------------------------------------------
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = os.getenv("REDIS_PORT", "6379")
REDIS_CELERY_DB = os.getenv("REDIS_CELERY_DB", "0")
REDIS_RESULTS_DB = os.getenv("REDIS_RESULTS_DB", "1")

CACHE_CONFIG = {
    "CACHE_TYPE": "RedisCache",
    "CACHE_DEFAULT_TIMEOUT": 300,
    "CACHE_KEY_PREFIX": "superset_",
    "CACHE_REDIS_HOST": REDIS_HOST,
    "CACHE_REDIS_PORT": REDIS_PORT,
    "CACHE_REDIS_DB": REDIS_RESULTS_DB,
}
DATA_CACHE_CONFIG = CACHE_CONFIG
FILTER_STATE_CACHE_CONFIG = CACHE_CONFIG
EXPLORE_FORM_DATA_CACHE_CONFIG = CACHE_CONFIG

# ---------------------------------------------------------------------------
# Celery (broker + result backend via Redis)
# ---------------------------------------------------------------------------
class CeleryConfig:
    broker_url = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_CELERY_DB}"
    result_backend = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_RESULTS_DB}"
    imports = (
        "superset.sql_lab",
        "superset.tasks.scheduler",
        "superset.tasks.thumbnails",
        "superset.tasks.cache",
    )
    worker_prefetch_multiplier = 1
    task_acks_late = False
    beat_schedule = {
        "reports.scheduler": {
            "task": "reports.scheduler",
            "schedule": crontab(minute="*", hour="*"),
        },
        "reports.prune_log": {
            "task": "reports.prune_log",
            "schedule": crontab(minute=10, hour=0),
        },
    }


CELERY_CONFIG = CeleryConfig

# ---------------------------------------------------------------------------
# Logging — JSON to stdout for structured log aggregation
# ---------------------------------------------------------------------------
LOG_LEVEL = os.getenv("SUPERSET_LOG_LEVEL", "INFO")


class JsonFormatter(logging.Formatter):
    """Minimal JSON log formatter for stdout-based log pipelines."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info and record.exc_info[0] is not None:
            log_entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_entry)


LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"
LOGGING_CONFIGURATOR = None  # use LOG_FORMAT / custom setup below

CUSTOM_LOGGING_CONFIG: dict = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": f"{__name__}.JsonFormatter",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
            "stream": "ext://sys.stdout",
        },
    },
    "root": {
        "level": LOG_LEVEL,
        "handlers": ["console"],
    },
}

LOGGING_CONFIG_CLASS = "superset.utils.logging_configurator.LoggingConfigurator"

# Override the Flask/Superset default with our custom dict
import superset.utils.log as _superset_log  # noqa: E402

_superset_log.LOGGING_CONFIGURATOR = None

# Apply the dict-config directly — Superset merges this if present
import logging.config as _lc  # noqa: E402

_lc.dictConfig(CUSTOM_LOGGING_CONFIG)

# ---------------------------------------------------------------------------
# Feature flags
# ---------------------------------------------------------------------------
FEATURE_FLAGS = {
    "ALERT_REPORTS": True,
}

SQLLAB_CTAS_NO_LIMIT = True

# ---------------------------------------------------------------------------
# Authentication — DB (default) or OIDC/OAuth, controlled via AUTH_TYPE env var
# ---------------------------------------------------------------------------
from flask_appbuilder.const import AUTH_DB, AUTH_OAUTH  # noqa: E402

_AUTH_TYPE_MAP = {
    "DB": AUTH_DB,
    "OAUTH": AUTH_OAUTH,
}
AUTH_TYPE = _AUTH_TYPE_MAP.get(os.getenv("AUTH_TYPE", "DB").upper(), AUTH_DB)

if AUTH_TYPE == AUTH_OAUTH:
    OIDC_CLIENT_ID = os.environ["OIDC_CLIENT_ID"]
    OIDC_CLIENT_SECRET = os.environ["OIDC_CLIENT_SECRET"]
    OIDC_DISCOVERY_URL = os.environ["OIDC_DISCOVERY_URL"]
    OIDC_SCOPES = os.getenv("OIDC_SCOPES", "openid email profile").split()
    OIDC_REDIRECT_URI = os.getenv(
        "OIDC_REDIRECT_URI",
        "http://localhost:8080/oauth-authorized/oidc",
    )
    OIDC_USERNAME_CLAIM = os.getenv("OIDC_USERNAME_CLAIM", "preferred_username")
    OIDC_EMAIL_CLAIM = os.getenv("OIDC_EMAIL_CLAIM", "email")
    OIDC_GROUPS_CLAIM = os.getenv("OIDC_GROUPS_CLAIM", "groups")

    OAUTH_PROVIDERS = [
        {
            "name": "oidc",
            "icon": "fa-openid",
            "token_key": "access_token",
            "remote_app": {
                "client_id": OIDC_CLIENT_ID,
                "client_secret": OIDC_CLIENT_SECRET,
                "server_metadata_url": OIDC_DISCOVERY_URL,
                "api_base_url": OIDC_DISCOVERY_URL.rsplit(
                    "/.well-known", 1
                )[0] + "/",
                "client_kwargs": {"scope": " ".join(OIDC_SCOPES)},
                "redirect_uri": OIDC_REDIRECT_URI,
            },
        },
    ]

    # Allow auto-creation of users on first OIDC login
    AUTH_USER_REGISTRATION = True
    AUTH_USER_REGISTRATION_ROLE = "BI_Viewer"

    # -- Group → Role mapping --------------------------------------------------
    # Keys: group names from the IdP groups claim
    # Values: Superset role names (must exist in Superset)
    AUTH_ROLES_MAPPING = json.loads(
        os.getenv(
            "OIDC_ROLES_MAPPING",
            json.dumps(
                {
                    "superset-admins": ["Admin"],
                    "superset-bi-admins": ["BI_Admin"],
                    "superset-editors": ["BI_Editor"],
                    "superset-viewers": ["BI_Viewer"],
                }
            ),
        )
    )
    AUTH_ROLES_SYNC_AT_LOGIN = True

    # -- Custom security manager for OIDC userinfo ----------------------------
    from superset.security.manager import (  # noqa: E402
        SupersetSecurityManager,
    )

    class OIDCSecurityManager(SupersetSecurityManager):
        """Extract user info and group memberships from the OIDC token."""

        def oauth_user_info(
            self, provider: str, response: dict | None = None
        ) -> dict:
            if provider != "oidc":
                return {}
            me = self.appbuilder.sm.oauth_remotes[provider].get("userinfo")
            data = me.json() if me else {}
            return {
                "username": data.get(OIDC_USERNAME_CLAIM, ""),
                "email": data.get(OIDC_EMAIL_CLAIM, ""),
                "first_name": data.get("given_name", ""),
                "last_name": data.get("family_name", ""),
                "role_keys": data.get(OIDC_GROUPS_CLAIM, []),
            }

    CUSTOM_SECURITY_MANAGER = OIDCSecurityManager
