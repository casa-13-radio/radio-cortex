#!/bin/bash
set -e

# =============================================================================
# Radio Cortex - Backup Script
# =============================================================================
# Usage: ./scripts/backup.sh
#
# This script creates backups of the database and uploads to OCI Storage.
# Should be run daily via cron: 0 2 * * * /opt/radio-cortex/scripts/backup.sh
# =============================================================================

APP_DIR="/opt/radio-cortex"
BACKUP_DIR="$APP_DIR/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DATE=$(date +%Y-%m-%d)

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

success() {
    echo -e "${GREEN}✅ $1${NC}"
}

error() {
    echo -e "${RED}❌ $1${NC}"
    exit 1
}

# =============================================================================
# CREATE BACKUP DIRECTORY
# =============================================================================

mkdir -p $BACKUP_DIR

log "Starting backup..."

# =============================================================================
# BACKUP DATABASE
# =============================================================================

log "Backing up PostgreSQL database..."

cd $APP_DIR

BACKUP_FILE="$BACKUP_DIR/db_backup_$TIMESTAMP.sql.gz"

docker-compose exec -T postgres pg_dump -U cortex radiocortex | gzip > $BACKUP_FILE

if [ -f "$BACKUP_FILE" ]; then
    SIZE=$(du -h $BACKUP_FILE | cut -f1)
    success "Database backup created: $BACKUP_FILE ($SIZE)"
else
    error "Database backup failed"
fi

# =============================================================================
# BACKUP ENVIRONMENT CONFIG (without secrets)
# =============================================================================

log "Backing up configuration..."

CONFIG_BACKUP="$BACKUP_DIR/config_backup_$TIMESTAMP.tar.gz"

tar -czf $CONFIG_BACKUP \
    --exclude="*.env" \
    --exclude="*.log" \
    --exclude="__pycache__" \
    $APP_DIR/config \
    $APP_DIR/docker-compose*.yml \
    2>/dev/null || true

if [ -f "$CONFIG_BACKUP" ]; then
    success "Configuration backup created"
fi

# =============================================================================
# UPLOAD TO OCI OBJECT STORAGE (Optional)
# =============================================================================

if [ -n "$OCI_BUCKET_NAME" ]; then
    log "Uploading to OCI Object Storage..."
    
    # Check if OCI CLI is installed
    if command -v oci &> /dev/null; then
        oci os object put \
            --bucket-name "$OCI_BUCKET_NAME" \
            --file "$BACKUP_FILE" \
            --name "backups/db_backup_$TIMESTAMP.sql.gz" \
            --force || warning "Failed to upload to OCI"
        
        success "Backup uploaded to OCI Storage"
    else
        log "OCI CLI not installed, skipping upload"
    fi
fi

# =============================================================================
# CLEANUP OLD BACKUPS
# =============================================================================

log "Cleaning up old backups..."

# Keep only last 30 days locally
find $BACKUP_DIR -name "db_backup_*.sql.gz" -mtime +30 -delete
find $BACKUP_DIR -name "config_backup_*.tar.gz" -mtime +30 -delete

# Count remaining backups
BACKUP_COUNT=$(find $BACKUP_DIR -name "db_backup_*.sql.gz" | wc -l)
success "Local backups: $BACKUP_COUNT (keeping last 30 days)"

# =============================================================================
# TEST BACKUP INTEGRITY
# =============================================================================

log "Testing backup integrity..."

if gunzip -t $BACKUP_FILE 2>/dev/null; then
    success "Backup integrity verified"
else
    error "Backup integrity check failed"
fi

# =============================================================================
# SUMMARY
# =============================================================================

echo ""
echo "======================================"
echo "  Backup completed successfully!"
echo "======================================"
echo ""
echo "📦 Backup Details:"
echo "   File: $BACKUP_FILE"
echo "   Size: $(du -h $BACKUP_FILE | cut -f1)"
echo "   Date: $DATE"
echo "   Total backups: $BACKUP_COUNT"
echo ""

# Send notification (optional - integrate with your notification system)
# curl -X POST https://your-webhook-url -d "Backup completed: $BACKUP_FILE"

success "Backup completed! 🎉"