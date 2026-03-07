#!/bin/bash
# Backup script for Invitation App
# Copies the entire app folder to a Synology NAS via SMB/CIFS mount
# Requires cifs-utils: sudo apt install cifs-utils
# Can be run manually or via cron (e.g. daily at 2am):
#   0 2 * * * /path/to/invitation-app/backup.sh >> /path/to/invitation-app/backup.log 2>&1

set -e

APP_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$APP_DIR"

# Load backup settings from .env using grep (avoids shell expansion issues)
get_env() { grep -s "^$1=" .env | head -1 | cut -d'=' -f2-; }

NAS_HOST="$(get_env BACKUP_NAS_HOST)"
NAS_USER="$(get_env BACKUP_NAS_USER)"
NAS_PASSWORD="$(get_env BACKUP_NAS_PASSWORD)"
NAS_SHARE="$(get_env BACKUP_NAS_SHARE)"
NAS_FOLDER="$(get_env BACKUP_NAS_FOLDER)"
KEEP_DAYS="$(get_env BACKUP_KEEP_DAYS)"
KEEP_DAYS="${KEEP_DAYS:-30}"

if [ -z "$NAS_HOST" ] || [ -z "$NAS_USER" ] || [ -z "$NAS_PASSWORD" ] || [ -z "$NAS_SHARE" ]; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') ERROR: Backup settings not configured in .env"
    echo "  Required: BACKUP_NAS_HOST, BACKUP_NAS_USER, BACKUP_NAS_PASSWORD, BACKUP_NAS_SHARE"
    exit 1
fi

MOUNT_POINT="/mnt/nas_backup"
TIMESTAMP=$(date '+%Y-%m-%d_%H%M%S')
BACKUP_NAME="invitation-app_${TIMESTAMP}"

echo "$(date '+%Y-%m-%d %H:%M:%S') Starting backup to //${NAS_HOST}/${NAS_SHARE}/${NAS_FOLDER}/${BACKUP_NAME}"

# Create mount point
sudo mkdir -p "$MOUNT_POINT"

# Mount NAS share via SMB/CIFS
UID_VAL=$(id -u)
GID_VAL=$(id -g)
sudo mount -t cifs "//${NAS_HOST}/${NAS_SHARE}" "$MOUNT_POINT" \
    -o "username=${NAS_USER},password=${NAS_PASSWORD},uid=${UID_VAL},gid=${GID_VAL},file_mode=0777,dir_mode=0777,forceuid,forcegid"

echo "$(date '+%Y-%m-%d %H:%M:%S') NAS mounted successfully"

# Ensure cleanup on exit
cleanup() {
    sudo umount "$MOUNT_POINT" 2>/dev/null || true
}
trap cleanup EXIT

# Create destination folder
DEST_DIR="${MOUNT_POINT}/${NAS_FOLDER}"
DEST_PATH="${DEST_DIR}/${BACKUP_NAME}"
mkdir -p "$DEST_DIR"

# Copy app folder, excluding unnecessary files
rsync -a \
    --exclude='venv/' \
    --exclude='__pycache__/' \
    --exclude='*.pyc' \
    --exclude='.claude/' \
    --exclude='backup.log' \
    "$APP_DIR/" "$DEST_PATH/"

echo "$(date '+%Y-%m-%d %H:%M:%S') Backup complete: ${DEST_PATH}"

# Clean up old backups
if [ "$KEEP_DAYS" -gt 0 ]; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') Cleaning up backups older than ${KEEP_DAYS} days..."
    find "$DEST_DIR" -maxdepth 1 -name 'invitation-app_*' -type d -mtime +${KEEP_DAYS} -exec rm -rf {} +
    echo "$(date '+%Y-%m-%d %H:%M:%S') Cleanup done."
fi
