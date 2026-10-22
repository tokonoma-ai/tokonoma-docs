# External PostgreSQL

If you need an external database, choose and prepare it before the first installation. It stores MCP memory and, when enabled, the telemetry metastore. The server must be reachable from the cluster by DNS name on port `5432`.

This setup has not been validated on managed services such as Amazon RDS or Cloud SQL. The chart is tested against its bundled PostgreSQL 18 with pgvector 0.8.6. Talk to Tokonoma before using an external database in production.

Run `kubectl` from a workstation with cluster access and SQL in an administrative database session. Edit the `values.yaml` prepared during [installation](install.md), following [input conventions](install.md#inputs-and-placeholders).

| Input | Source and when required |
|---|---|
| `REPLACE_WITH_KUBE_CONTEXT` | Intended cluster context from `kubectl config get-contexts`; required for cluster commands. |
| `REPLACE_WITH_DATABASE_HOST` | DNS name supplied by the database administrator; required in `values.yaml`. |
| `REPLACE_WITH_POSTGRES_PASSWORD` | Password for the `tokonoma` database role and its Kubernetes Secret. |

With `telemetryPlatform: true`, keep database `tokonoma`, user `tokonoma`, Secret name `toko-postgres`, and Secret key `password`. These match the bundled search backend. Use a URL-safe password containing letters, digits, `.`, `_`, `~`, or `-` because the search backend places it in a PostgreSQL URI.

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

The `tokonoma` role must own the database and be able to create schemas and tables. Tokonoma creates and updates its schema at startup. On PostgreSQL 15 and later, only the database owner can create tables in `public` by default.

After a PostgreSQL or pgvector upgrade, the server also tries to update the extension and rebuild indexes. If the role lacks those rights, it logs the required commands and continues starting. Run those commands as an administrative user.

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

The chart creates an `ExternalName` Service called `toko-postgres` that points to `postgres.host`. The MCP server and optional telemetry backend use it to reach the same database.

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
