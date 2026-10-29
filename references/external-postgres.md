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

Check those characters in your secret-management workflow too. A successful Helm render does not validate passwords stored in an existing Secret.

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

## Managed-service acceptance

Local PostgreSQL regression tests do not validate RDS or Cloud SQL compatibility. Work with Tokonoma on an approved non-production database to record the results below. Results apply only to the provider and versions tested.

| Environment | Validation status |
|---|---|
| Local PostgreSQL | PostgreSQL 18.4 to 18.6 and pgvector 0.8.5 to 0.8.6 tested with an ordinary database-owner role. Schema setup, stored records, extension maintenance, Quickwit metadata, encrypted connections, and full database dump/restore passed. |
| Amazon RDS | Not validated. Provider permissions, certificate verification, upgrades, and snapshot restoration remain untested. |
| Cloud SQL | Not validated. Provider permissions, certificate verification, upgrades, and snapshot restoration remain untested. |

The local run on 2026-10-29 used chart source `c43439e6095395b1943a7e190eeded94f6f436a2` on Kubernetes 1.36.1 (ARM64).
Its MCP image was `public.ecr.aws/tokonoma/toko-mcp@sha256:6ea053a6a454290c0688061d0cd9a5befc5b27c3472ba60afbe672f09ffe8751`.
Quickwit used `public.ecr.aws/tokonoma/tokonoma-core:0.9.2` at digest `sha256:8f7a4a7cc24abc6d59d94ba855861ff8ec6ece466ffe7cfe204b92326e4f27d3`.
This run checked encrypted connections and plaintext rejection; it did not establish certificate identity verification or provider snapshot recovery.

1. **Versions and roles:** Record the provider, PostgreSQL and pgvector versions, extension availability, and tested Tokonoma versions. Record the privileges and role memberships of the extension administrator and the ordinary role that owns the application database.
2. **Schemas and operations:** As the ordinary database owner, verify schema setup and real memory, queue, OAuth token-store, and runner operations. Repeat startup and confirm existing data remains accessible.
3. **Database maintenance:** Separately test PostgreSQL or pgvector upgrades. Verify extension updates as the extension owner and index rebuilds as the database owner or authorized administrator. Check startup logs and confirm existing data remains accessible afterward.
4. **Telemetry and encryption:** With telemetry enabled, verify Quickwit creates and uses its metastore tables in the same database. Check encryption and server identity verification for MCP, runner, and Quickwit connections under the provider's unchanged Transport Layer Security (TLS) policy.
5. **Backup and restore:** Restore the backup into an approved non-production target. Verify `public` and `pgmq`, including queue messages, archives, functions, and ownership, then repeat application operations. The unlogged `pgmq.notify_insert_throttle` table holds notification timing metadata and may be empty after restore; queue data must survive.
