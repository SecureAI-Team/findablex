#!/bin/bash
# Database restore script

set -e

BACKUP_FILE="$1"
DB_CONTAINER="${DB_CONTAINER:-findablex-db}"
DB_USER="${DB_USER:-findablex}"
DB_NAME="${DB_NAME:-findablex}"

if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: $0 <backup_file.sql.gz>"
    echo ""
    echo "Available backups:"
    ls -la /opt/findablex/backups/*.sql.gz 2>/dev/null || echo "No backups found"
    exit 1
fi

if [ ! -f "$BACKUP_FILE" ]; then
    echo "ERROR: Backup file not found: $BACKUP_FILE"
    exit 1
fi

echo "WARNING: This will overwrite the current database!"
read -p "Are you sure? (yes/no): " confirm
if [ "$confirm" != "yes" ]; then
    echo "Aborted."
    exit 0
fi

echo "[$(date)] Stopping application services..."
docker compose stop api worker beat crawler 2>/dev/null || true

echo "[$(date)] Restoring database from $BACKUP_FILE..."
gunzip -c "$BACKUP_FILE" | docker exec -i $DB_CONTAINER psql -U $DB_USER $DB_NAME

echo "[$(date)] Starting application services..."
docker compose start api worker beat crawler 2>/dev/null || true

echo "[$(date)] Restore completed successfully!"
