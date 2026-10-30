# External PostgreSQL

Tokonoma supports an external PostgreSQL database with pgvector. Prepare it before installation and allow connections from the cluster to its DNS name on port `5432`. It stores saved records and application state.

The bundled database uses PostgreSQL 18 with pgvector 0.8.6. Amazon RDS and Cloud SQL have not been validated; provider certificate verification and snapshot recovery remain untested. Contact Tokonoma before using an external database in production.

Run `kubectl` from a workstation with cluster access and SQL in an administrative database session. Edit the `values.yaml` prepared during [installation](install.md), following [input conventions](install.md#inputs-and-placeholders).

| Input | Source and when required |
|---|---|
| `REPLACE_WITH_KUBE_CONTEXT` | Intended cluster context from `kubectl config get-contexts`; required for cluster commands. |
| `REPLACE_WITH_DATABASE_HOST` | DNS name supplied by the database administrator; required in `values.yaml`. |
| `REPLACE_WITH_POSTGRES_PASSWORD` | Password for the `tokonoma` database role and its Kubernetes Secret. |

With `telemetryPlatform: true`, use database and user `tokonoma`, Secret `toko-postgres`, and key `password`. The password must contain only letters, digits, `.`, `_`, `~`, or `-`, including passwords supplied through an existing Secret.

Changing the database host does not migrate existing records. For an existing installation, back up and migrate the data before switching hosts, then use the [upgrade guide](upgrading.md) with the updated `values.yaml`. Do not run the new-database SQL against an existing database without reviewing it.

## 1. Prepare the database

Have the database administrator create the role, database, and `vector` extension. In a `psql` administrative session, run:

```sql
CREATE ROLE tokonoma LOGIN PASSWORD 'REPLACE_WITH_POSTGRES_PASSWORD';
CREATE DATABASE tokonoma OWNER tokonoma;
\c tokonoma
CREATE EXTENSION IF NOT EXISTS vector;
```

Confirm the role, database, and `vector` extension exist before starting Tokonoma; the server does not create the extension. Protect the password in database session history.

The `tokonoma` role must own the database and be able to create schemas and tables. Tokonoma creates and updates its schema at startup.

When Tokonoma starts after a PostgreSQL or pgvector upgrade, it checks for required extension updates and index rebuilds. If startup logs list commands that need administrator privileges, have the database administrator run them.

## 2. Create the password Secret

[Prepare the namespace](credentials.md#prepare-the-namespace-for-secrets) and follow [credential setup](credentials.md#supply-credentials-in-commands). Fill the password placeholder locally with the same password used for the database role, then create the Secret:

```sh
kubectl --context REPLACE_WITH_KUBE_CONTEXT -n tokonoma create secret generic toko-postgres \
  --from-literal=password='REPLACE_WITH_POSTGRES_PASSWORD'
```

Expect `secret/toko-postgres created`. An existing secret-management workflow may create the same Secret instead. If the Secret already exists, verify its owner and password through that workflow before proceeding; do not replace it blindly.

## 3. Save the values

Merge these settings into the existing `postgres` section in `values.yaml`:

```yaml
postgres:
  enabled: false
  host: REPLACE_WITH_DATABASE_HOST
  auth:
    username: tokonoma
    database: tokonoma
    existingSecret: toko-postgres
    secretKey: password
```

[Install Tokonoma](install.md#3-install) with the updated `values.yaml`; no prior bundled database installation is needed.

## 4. Verify after installation

After Helm reports `STATUS: deployed`, confirm the MCP rollout:

```sh
kubectl --context REPLACE_WITH_KUBE_CONTEXT -n tokonoma rollout status deployment/toko-mcp --timeout=5m
```

Expect `successfully rolled out`. Then inspect startup logs:

```sh
kubectl --context REPLACE_WITH_KUBE_CONTEXT -n tokonoma logs deployment/toko-mcp --tail=100
```

Look for `memory module: schema applied`. The pod can run even if the memory store fails, so rollout alone does not verify the database. The optional [memory access check](install.md#connect-and-confirm-memory-access) tests a saved record.

For `password authentication failed`, check that the Secret matches the database role's password. For `memory module: ensure_schema failed`, check the `vector` extension and database ownership.
