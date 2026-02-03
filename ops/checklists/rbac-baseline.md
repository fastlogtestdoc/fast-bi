# Checklist: RBAC Baseline

Defines the minimum role and permission model for Superset in production.

---

## Guiding Principle

**Least Privilege** — every user receives only the permissions required for
their specific responsibilities. Broader access is granted explicitly, not
by default.

---

## Roles

| Role | Purpose | Typical users |
|---|---|---|
| **Admin** | Full platform control (users, roles, settings, data sources) | Platform operators, on-call admin |
| **BI_Admin** | Manage data sources, datasets, and schemas; no user/role management | Data engineers, analytics leads |
| **BI_Editor** | Create and edit dashboards and charts using existing datasets | Analysts, report builders |
| **BI_Viewer** | View published dashboards, no editing | Business stakeholders, management |
| **Anonymous** | Unauthenticated access to public dashboards (disabled by default) | External viewers if explicitly enabled |

---

## Permission Matrix

| Capability | Admin | BI_Admin | BI_Editor | BI_Viewer | Anonymous |
|---|---|---|---|---|---|
| Manage users and roles | x | | | | |
| Configure platform settings | x | | | | |
| Add/edit database connections | x | x | | | |
| Add/edit datasets | x | x | | | |
| Run SQL in SQL Lab | x | x | | | |
| Create/edit dashboards | x | x | x | | |
| Create/edit charts | x | x | x | | |
| Export dashboards/charts | x | x | x | | |
| View published dashboards | x | x | x | x | x (*) |
| View published charts | x | x | x | x | x (*) |
| Access SQL Lab (read-only) | x | x | | | |

(*) Anonymous access requires `PUBLIC_ROLE_LIKE = "Gamma"` and the feature
flag `PUBLIC_ROLE_LIKE` to be set. Disabled by default.

---

## Data Source and Schema Access

- Database connections are granted **per role** via Superset's database
  access permissions.
- Schema-level access is controlled through `schema_access` permissions
  on each role.
- Dataset-level access (`datasource_access`) restricts which datasets
  a role can query.
- **Default**: BI_Viewer and BI_Editor receive access only to datasets
  explicitly granted. No blanket `all_database_access`.

### Setup checklist

- [ ] Remove `all_database_access` from all non-Admin roles
- [ ] Grant `database_access` only to BI_Admin for managed databases
- [ ] Grant `schema_access` per schema to BI_Admin
- [ ] Grant `datasource_access` per dataset to BI_Editor and BI_Viewer
- [ ] Verify no role inherits unintended permissions from Gamma or Public

---

## Row-Level Security (RLS)

RLS restricts which **rows** a user sees when querying a dataset.

- Defined via **Security > Row Level Security** in the Superset UI.
- Each rule maps a role + dataset to a SQL `WHERE` clause.
- Example: `region = 'EMEA'` applied to role `BI_Viewer_EMEA`.

### Checklist

- [ ] Identify datasets requiring row-level restrictions
- [ ] Define filter clauses per role
- [ ] Create RLS rules and assign to roles
- [ ] Test with a user in each affected role
- [ ] Document active RLS rules in ops/decisions/ or a wiki

---

## Column-Level Security (CLS)

CLS restricts which **columns** a role can see in a dataset.

- Defined via dataset column permissions in the Superset UI.
- Columns can be marked as restricted; only roles with explicit
  `column_access` can see them.

### Checklist

- [ ] Identify sensitive columns (PII, financial, credentials)
- [ ] Restrict those columns on the dataset
- [ ] Grant `column_access` only to roles that need the data
- [ ] Test that restricted columns are hidden for other roles

---

## Review Cadence

| Action | Frequency |
|---|---|
| Review role assignments | Quarterly |
| Audit RLS/CLS rules | Quarterly |
| Review database/schema grants | After every new data source |
| Remove inactive users | Monthly |
