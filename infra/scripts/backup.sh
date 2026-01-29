#!/bin/bash
# Database backup script

set -e

# Configuration
BACKUP_DIR="${BACKUP_DIR:-/opt/findablex/backups}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
DB_CONTAINER="${DB_CONTAINER:-findablex-db}"
DB_USER="${DB_USER:-findablex}"
DB_NAME="${DB_NAME:-findablex}"
OSS_BUCKET="${OSS_BUCKET:-}"

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Generate timestamp
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/findablex_${TIMESTAMP}.sql.gz"

echo "[$(date)] Starting backup..."

# Dump database
docker exec -t $DB_CONTAINER pg_dump -U $DB_USER $DB_NAME | gzip > "$BACKUP_FILE"

# Verify backup
if [ -s "$BACKUP_FILE" ]; then
    SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    echo "[$(date)] Backup completed: $BACKUP_FILE ($SIZE)"
else
    echo "[$(date)] ERROR: Backup file is empty!"
    exit 1
fi

# Upload to OSS (if configured)
if [ -n "$OSS_BUCKET" ]; then
    echo "[$(date)] Uploading to OSS..."
    aliyun oss cp "$BACKUP_FILE" "oss://$OSS_BUCKET/backups/" || echo "OSS upload failed"
fi

# Clean old backups
echo "[$(date)] Cleaning backups older than $RETENTION_DAYS days..."
find "$BACKUP_DIR" -name "findablex_*.sql.gz" -mtime +$RETENTION_DAYS -delete

echo "[$(date)] Backup process completed."
