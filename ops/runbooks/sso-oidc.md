# Runbook: SSO / OIDC Authentication

Describes how to enable, test, and troubleshoot OpenID Connect (OIDC)
authentication for the production Superset stack.

---

## Prerequisites

| Requirement | Details |
|---|---|
| Identity Provider (IdP) | Keycloak, Azure AD, Okta, Google Workspace, or any OIDC-compliant IdP |
| Client registration | A confidential client registered at the IdP with redirect URI |
| Discovery URL | The IdP's `/.well-known/openid-configuration` endpoint |
| Groups claim | IdP configured to include group memberships in the ID token or userinfo |

---

## 1. Setup

### 1.1 Register a client at the IdP

Create a confidential OIDC client with:

- **Redirect URI**: `https://<superset-host>/oauth-authorized/oidc`
  (use `http://localhost:8080/oauth-authorized/oidc` for local testing)
- **Scopes**: `openid`, `email`, `profile`
- **Grant type**: Authorization Code
- **Token endpoint auth**: Client secret (POST or Basic)

Note the **Client ID**, **Client Secret**, and **Discovery URL**.

### 1.2 Configure `.env`

Uncomment and fill in the OIDC section in `.env`:

```bash
AUTH_TYPE=OAUTH

OIDC_CLIENT_ID=superset-prod
OIDC_CLIENT_SECRET=your-client-secret-here
OIDC_DISCOVERY_URL=https://idp.example.com/realms/main/.well-known/openid-configuration
OIDC_SCOPES=openid email profile
OIDC_REDIRECT_URI=https://superset.example.com/oauth-authorized/oidc
OIDC_USERNAME_CLAIM=preferred_username
OIDC_EMAIL_CLAIM=email
OIDC_GROUPS_CLAIM=groups
```

### 1.3 Configure group-to-role mapping (optional)

Override the default mapping via `OIDC_ROLES_MAPPING` in `.env`:

```bash
OIDC_ROLES_MAPPING={"idp-admins":["Admin"],"analytics-team":["BI_Editor"],"everyone":["BI_Viewer"]}
```

Keys are IdP group names. Values are lists of Superset role names.
Users not matching any group receive the `BI_Viewer` role (default
registration role).

### 1.4 Restart the stack

```bash
docker compose -f docker-compose.prod.yml up -d
```

No changes to `docker-compose.prod.yml` are needed — the config reads
`AUTH_TYPE` from the `.env` file that is already mounted.

---

## 2. How It Works

```
Browser                 Nginx           Superset           IdP
  |                       |                |                |
  |-- GET /login -------->|--------------->|                |
  |                       |  302 redirect  |                |
  |<--------------------------------------------->|         |
  |                       |                |   authorize    |
  |-- callback + code --->|--------------->|                |
  |                       |                |-- token ------>|
  |                       |                |<-- id_token ---|
  |                       |                |-- userinfo --->|
  |                       |                |<-- claims -----|
  |                       |                |                |
  |                       |  create/update user + map roles |
  |<-- session cookie ----|<---------------|                |
```

1. User clicks "Sign In with oidc" on the login page.
2. Superset redirects to the IdP authorization endpoint.
3. After authentication, IdP redirects back with an authorization code.
4. Superset exchanges the code for tokens and fetches userinfo.
5. `OIDCSecurityManager.oauth_user_info()` extracts username, email,
   and group memberships from the configured claims.
6. `AUTH_ROLES_MAPPING` maps IdP groups to Superset roles.
7. If the user does not exist, they are auto-created with the
   `BI_Viewer` role (configurable via `AUTH_USER_REGISTRATION_ROLE`).
8. Roles are synced on every login (`AUTH_ROLES_SYNC_AT_LOGIN = True`).

---

## 3. Testing

### 3.1 Quick smoke test

```bash
# 1. Open the login page — should show "Sign In with oidc" button
curl -sf http://localhost:8080/login/ | grep -o "oauth-authorized"

# 2. Verify the discovery URL is reachable from the container
docker compose -f docker-compose.prod.yml exec superset-web \
  curl -sf "${OIDC_DISCOVERY_URL}" | python3 -m json.tool | head -5
```

### 3.2 End-to-end login test

1. Open `http://localhost:8080/login/` in a browser.
2. Click "Sign In with oidc".
3. Authenticate at the IdP.
4. Verify redirect back to Superset dashboard.
5. Check user profile: username and email match IdP claims.
6. Check assigned roles: Admin > Security > List Users.

### 3.3 Role mapping test

1. Add the test user to an IdP group (e.g. `superset-editors`).
2. Log out and log back in.
3. Verify the user now has the `BI_Editor` role in Superset.
4. Remove the user from the group and log in again.
5. Verify the role reverts to `BI_Viewer` (default).

### 3.4 Fallback to DB auth

To switch back to database authentication:

```bash
# In .env:
AUTH_TYPE=DB
```

Restart the stack. The login page returns to username/password form.
Existing OIDC-created users remain in the database and can be assigned
passwords manually if needed.

---

## 4. Troubleshooting

### "Sign In with oidc" button missing

**Cause**: `AUTH_TYPE` is not set to `OAUTH` or the env var is not
reaching the container.

```bash
docker compose -f docker-compose.prod.yml exec superset-web \
  env | grep AUTH_TYPE
# Expected: AUTH_TYPE=OAUTH
```

### 302 redirect loop after IdP callback

**Cause**: Redirect URI mismatch between IdP config and `OIDC_REDIRECT_URI`.

- The URI in `.env` must exactly match the one registered at the IdP.
- Check protocol (`http` vs `https`) and trailing slashes.

```bash
docker compose -f docker-compose.prod.yml logs --tail 30 superset-web | grep -i redirect
```

### "Could not fetch token" / SSL errors

**Cause**: Container cannot reach the IdP or TLS certificate is untrusted.

```bash
# Test connectivity from the container
docker compose -f docker-compose.prod.yml exec superset-web \
  curl -v "${OIDC_DISCOVERY_URL}"
```

For self-signed IdP certificates, mount the CA bundle:

```yaml
# In docker-compose override (not docker-compose.prod.yml):
volumes:
  - ./certs/ca.pem:/etc/ssl/certs/custom-ca.pem:ro
environment:
  REQUESTS_CA_BUNDLE: /etc/ssl/certs/custom-ca.pem
```

### User created but no roles assigned

**Cause**: `OIDC_GROUPS_CLAIM` does not match the actual claim name in
the IdP token, or `AUTH_ROLES_MAPPING` keys do not match group names.

Debug the claims received:

```bash
docker compose -f docker-compose.prod.yml logs superset-web | grep -i "oauth_user_info\|role_keys"
```

Verify the IdP includes groups in the userinfo endpoint or ID token.

### "User already exists" conflict

**Cause**: A user with the same username or email was created via DB auth
before OIDC was enabled.

Fix: Deactivate or delete the conflicting local user, then log in via
OIDC to recreate the account.

---

## 5. Environment Variables Reference

| Variable | Required | Default | Description |
|---|---|---|---|
| `AUTH_TYPE` | no | `DB` | `DB` or `OAUTH` |
| `OIDC_CLIENT_ID` | if OAUTH | — | Client ID from IdP |
| `OIDC_CLIENT_SECRET` | if OAUTH | — | Client secret from IdP |
| `OIDC_DISCOVERY_URL` | if OAUTH | — | `/.well-known/openid-configuration` URL |
| `OIDC_SCOPES` | no | `openid email profile` | Space-separated OIDC scopes |
| `OIDC_REDIRECT_URI` | no | `http://localhost:8080/oauth-authorized/oidc` | OAuth callback URL |
| `OIDC_USERNAME_CLAIM` | no | `preferred_username` | Token claim for username |
| `OIDC_EMAIL_CLAIM` | no | `email` | Token claim for email |
| `OIDC_GROUPS_CLAIM` | no | `groups` | Token claim for group memberships |
| `OIDC_ROLES_MAPPING` | no | see `.env.example` | JSON: IdP group → Superset roles |
