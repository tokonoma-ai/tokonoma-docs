# Back up and restore PostgreSQL

The bundled PostgreSQL in chart 0.38.0 has one replica. Its persistent volume survives an ordinary Helm uninstall, but that is not a backup or a high-availability database. Keep independent backups and test recovery before an upgrade or retirement.

This recipe covers the bundled database, including saved records and application state. It does not back up Helm values, Kubernetes Secrets, object-storage telemetry, or other components' volumes. Keep those through their existing protected backup workflows. For [external PostgreSQL](external-postgres.md), use the database owner's backup and recovery process.

Run from an authorized workstation. Examples use namespace `tokonoma`, StatefulSet `toko-postgres`, and container `postgres`; replace them consistently if your installation overrides them. Use a new backup filename outside this repository each time. Backups contain customer data, OAuth state, and other sensitive application content: restrict access and retain them under your organization's policy.

## Create a database backup

Confirm the database is ready, then create a private local directory:

```sh
kubectl --context REPLACE_WITH_KUBE_CONTEXT -n tokonoma rollout status statefulset/toko-postgres --timeout=5m
install -d -m 700 "REPLACE_WITH_BACKUP_DIRECTORY"
umask 077
```

Stream a custom-format dump to the workstation. The command uses the database user and database configured in the container. It reads the password inside the pod without displaying it or copying it into the local command:

```sh
kubectl --context REPLACE_WITH_KUBE_CONTEXT -n tokonoma exec statefulset/toko-postgres -c postgres -- \
  sh -c 'exec env PGPASSWORD="$POSTGRES_PASSWORD" pg_dump --format=custom --username="$POSTGRES_USER" --dbname="$POSTGRES_DB"' \
  > "REPLACE_WITH_BACKUP_DIRECTORY/tokonoma-REPLACE_WITH_BACKUP_ID.dump"
```

Expect exit status `0` and a nonempty local file. Do not add a TTY (`-t`) to a binary transfer. If the command fails, treat its output file as incomplete. `pg_dump` takes a consistent database snapshot while the application runs; changes committed after that snapshot are not included.

Check that the same PostgreSQL client can read the archive's table of contents:

```sh
test -s "REPLACE_WITH_BACKUP_DIRECTORY/tokonoma-REPLACE_WITH_BACKUP_ID.dump"
kubectl --context REPLACE_WITH_KUBE_CONTEXT -n tokonoma exec -i statefulset/toko-postgres -c postgres -- \
  pg_restore --list < "REPLACE_WITH_BACKUP_DIRECTORY/tokonoma-REPLACE_WITH_BACKUP_ID.dump" > /dev/null
```

Expect both commands to exit `0` without output. This checks archive readability, not recovery. Record the backup time, chart and application versions, PostgreSQL image, and protected configuration/Secret backup locations. Copy the dump to approved backup storage before relying on it.

## Test recovery in isolation

Have the database owner prepare an isolated PostgreSQL instance with an empty database and the matching PostgreSQL/pgvector image. For chart 0.38.0, the bundled image is PostgreSQL 18 with pgvector 0.8.6. Use a fresh database without precreated application tables or extensions so the archive can create them. Match the source database's locale settings where needed. The target pod must set `POSTGRES_USER`, `POSTGRES_DB`, and `POSTGRES_PASSWORD` for this recovery database.

Verify the scratch context, namespace, and pod with the owner before restoring. The target must have no production callers. This command restores into its configured database without dropping existing objects:

```sh
kubectl --context REPLACE_WITH_RECOVERY_KUBE_CONTEXT -n REPLACE_WITH_RECOVERY_NAMESPACE \
  exec -i REPLACE_WITH_ISOLATED_POSTGRES_POD -c postgres -- \
  sh -c 'exec env PGPASSWORD="$POSTGRES_PASSWORD" pg_restore --exit-on-error --no-owner --no-privileges --username="$POSTGRES_USER" --dbname="$POSTGRES_DB"' \
  < "REPLACE_WITH_BACKUP_DIRECTORY/tokonoma-REPLACE_WITH_BACKUP_ID.dump"
```

Expect exit status `0`. Stop and investigate any error; do not rerun against a partly restored database. Recreate the empty scratch database through the database owner's workflow before another attempt. Compare expected record counts and representative saved records with the source snapshot. If testing through an isolated Tokonoma instance, keep its external integrations and unattended work disabled so restored state cannot send messages, query customer systems, or start investigations.

Production recovery needs a separate, approved maintenance plan: pause writers, preserve the current data, restore to a fresh compatible database, and verify it before switching application connections. Preserve the original database and credentials until recovery is confirmed. A Helm rollback does not restore database contents; repeat the [installation health and functional checks](install.md#4-verify) after a recovery.
