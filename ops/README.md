# Operations

## Backups

The app runs an encrypted backup of the whole database every night (at
`BACKUP_HOUR`, in the institution's time zone) and writes it to the folder given
by `BACKUP_HOST_PATH`. In production that is the NAS share. Files older than
`BACKUP_RETENTION_DAYS` (14) are removed, but only after a new backup has
succeeded.

Each run leaves a status in the `job_runs` table: `succeeded`, `skipped` with the
reason (for example, no passphrase set) or `failed`. Admins can read it through
`GET /api/v1/backups/status`, and from step 1.3 in Settings → Data.

**Keep `BACKUP_PASSPHRASE` safe.** It is the only key to these files. If it is
lost, the existing backups cannot be recovered.

## Restore

This replaces the contents of the running database, so first take a fresh backup
if the database is still readable.

Use `app-dev` instead of `app` in these commands in development.

1. Stop the app, so nothing writes during the restore:

   ```bash
   docker compose stop app
   ```

2. Decrypt and restore in a one-off container, with the name of the backup you want
   in `F`. The decrypted dump exists only inside that container and disappears with
   it, so it never reaches the backup share unencrypted. The container's `pg_restore`
   matches the server version. It uses `BACKUP_PASSPHRASE` from `.env`, or asks if
   that is not set:

   ```bash
   docker compose run --rm --no-deps --entrypoint sh app -c '
     F=release_radar_YYYYMMDDTHHMMSSZ.dump.enc
     cp "/backups/$F" /tmp/ &&
     python ops/decrypt_backup.py "/tmp/$F" &&
     PGPASSWORD="$POSTGRES_PASSWORD" pg_restore -h db -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
       --clean --if-exists --no-owner "/tmp/${F%.enc}"'
   ```

3. Start the app again. Migrations run on startup and bring the restored database
   up to the current schema:

   ```bash
   docker compose up -d app
   ```

4. Check that it is healthy:

   ```bash
   curl -s http://127.0.0.1:8000/api/v1/health
   ```

To read a backup somewhere else, `ops/decrypt_backup.py` works on any machine with
Python and the `cryptography` package. It writes the decrypted file next to the
encrypted one, so keep it off shared folders and delete it afterwards.

## Lockout recovery

If nobody can sign in, an operator with access to the host can issue a temporary
password. It is printed to the terminal, and a new password is required at the next
sign-in:

```bash
docker compose exec app python -m app.cli reset-password someone@example.org
```

## Checking single-firing after a deploy

Set `SCHEDULER_TEST_INTERVAL_SECONDS=30` in `.env`, restart the app, wait a few
minutes, then count the runs per slot. Every row must show exactly 1:

```bash
docker compose exec db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT slot, count(*), string_agg(worker, chr(44)) FROM job_runs WHERE job_key = '"'"'scheduler-test'"'"' GROUP BY slot ORDER BY slot DESC LIMIT 10"'
```

Then set the variable back to `0` and restart.
