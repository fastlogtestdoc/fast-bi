# Runbook: Access Management

Covers the full user lifecycle (onboard, change, offboard), role assignment
process, and break-glass admin procedure.

Roles referenced here are defined in `ops/checklists/rbac-baseline.md`.

---

## 1. User Lifecycle

### Onboard

1. **Request**: New user submits access request with:
   - Full name, email
   - Business justification
   - Requested role (BI_Viewer, BI_Editor, BI_Admin)

2. **Approval**: Line manager or data owner approves the role.

3. **Create account**:

   Via UI (Admin > Security > List Users > +):
   - Set username, first/last name, email
   - Assign the approved role
   - Set an initial password or configure SSO/OAuth

   Via CLI:

   ```bash
   docker compose -f docker-compose.prod.yml run --rm superset-web \
     superset fab create-user \
       --username jdoe \
       --firstname Jane \
       --lastname Doe \
       --email jdoe@example.com \
       --role BI_Viewer \
       --password "initial-password"
   ```

4. **Grant data access**: If the role requires specific dataset or schema
   access, add the corresponding permissions (see RBAC baseline checklist).

5. **Notify user**: Send credentials or SSO instructions.

6. **Log**: Record the onboarding in the access log (spreadsheet, ticket
   system, or wiki).

### Change Role

1. **Request**: User or manager requests role change with justification.

2. **Approval**: Data owner or platform admin approves.

3. **Update role**:

   Via UI: Admin > Security > List Users > edit user > change role.

   Via CLI:

   ```bash
   docker compose -f docker-compose.prod.yml run --rm superset-web \
     superset fab add-role-user \
       --username jdoe \
       --role BI_Editor
   ```

   If replacing a role (not adding), remove the old role as well:

   ```bash
   docker compose -f docker-compose.prod.yml run --rm superset-web \
     superset fab remove-role-user \
       --username jdoe \
       --role BI_Viewer
   ```

4. **Adjust data access**: Add or remove dataset/schema permissions as
   needed for the new role.

5. **Log**: Record the change.

### Offboard

1. **Trigger**: Employee leaves, contractor ends, or access revocation
   requested.

2. **Deactivate account**:

   Via UI: Admin > Security > List Users > edit user > set Active = No.

   This prevents login without deleting dashboards or charts owned by
   the user.

3. **Reassign ownership** (if needed):

   Transfer dashboard/chart ownership to another user via the UI or API
   before deactivation if ongoing maintenance is required.

4. **Revoke SSO/OAuth** (if applicable): Remove the user from the identity
   provider group that grants Superset access.

5. **Log**: Record the offboarding and date.

6. **Delete** (optional): Only delete the user account if there are no
   owned objects or after ownership has been transferred. Deactivation
   is preferred over deletion for audit traceability.

---

## 2. Role Assignment Process

```
Requester          Approver            Platform Admin
   |                  |                     |
   |-- request ------>|                     |
   |                  |-- approve/deny ---->|
   |                  |                     |-- create/update user
   |                  |                     |-- assign role
   |                  |                     |-- grant data access
   |                  |                     |-- log & notify
   |<--------------------------------------|
```

### Rules

- No user may assign themselves a higher role.
- Admin role requires approval from a second Admin or team lead.
- BI_Admin role requires approval from the data owner.
- BI_Editor and BI_Viewer require line manager approval.
- Every role change is logged with: who, what, when, approved by.

### Bulk operations

For onboarding multiple users (e.g. a new team):

```bash
# Prepare a CSV: username,firstname,lastname,email,role,password
while IFS=, read -r user first last email role pw; do
  docker compose -f docker-compose.prod.yml run --rm superset-web \
    superset fab create-user \
      --username "$user" \
      --firstname "$first" \
      --lastname "$last" \
      --email "$email" \
      --role "$role" \
      --password "$pw"
done < users.csv
```

---

## 3. Break-Glass Admin Procedure

Use this when all Admin accounts are locked out or compromised.

### Prerequisites

- Shell access to the Docker host
- Access to `.env` (contains `POSTGRES_USER`, `POSTGRES_PASSWORD`)

### Procedure

```bash
# 1. Source environment
set -a; source .env; set +a

# 2. Create an emergency admin account
docker compose -f docker-compose.prod.yml run --rm superset-web \
  superset fab create-admin \
    --username emergency_admin \
    --email emergency@example.com \
    --password "$(openssl rand -base64 24)" \
    --firstname Emergency \
    --lastname Admin

# Note: capture the generated password from the command above
```

### After regaining access

1. Log in with the emergency admin account.
2. Investigate why the original Admin accounts were unavailable
   (locked, deleted, compromised).
3. Restore or recreate the regular Admin accounts.
4. **Deactivate the emergency admin account immediately** — it is a
   temporary measure only.
5. Document the incident: what happened, when, who executed break-glass,
   and follow-up actions.

### Security notes

- The break-glass procedure bypasses normal approval because it requires
  direct host access, which is itself access-controlled.
- The emergency admin password must be unique and must not be reused.
- All break-glass usage must be reported as a security event.
