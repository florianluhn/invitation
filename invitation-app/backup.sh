#!/bin/bash
# Backup script for Invitation App
# Copies the entire app folder to a remote NAS/server via rsync
# Requires sshpass: sudo apt install sshpass
# Can be run manually or via cron (e.g. daily at 2am):
#   0 2 * * * /path/to/invitation-app/backup.sh >> /path/to/invitation-app/backup.log 2>&1

set -e

APP_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$APP_DIR"

# Load settings from .env
if [ -f .env ]; then
    export $(grep -v '^#' .env | grep -v '^\s*$' | xargs)
fi

NAS_HOST="${BACKUP_NAS_HOST:-}"
NAS_USER="${BACKUP_NAS_USER:-}"
NAS_PASSWORD="${BACKUP_NAS_PASSWORD:-}"
NAS_PATH="${BACKUP_NAS_PATH:-}"
KEEP_DAYS="${BACKUP_KEEP_DAYS:-30}"

if [ -z "$NAS_HOST" ] || [ -z "$NAS_USER" ] || [ -z "$NAS_PASSWORD" ] || [ -z "$NAS_PATH" ]; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') ERROR: Backup settings not configured in .env"
    echo "  Required: BACKUP_NAS_HOST, BACKUP_NAS_USER, BACKUP_NAS_PASSWORD, BACKUP_NAS_PATH"
    exit 1
fi

# Check sshpass is installed
if ! command -v sshpass &> /dev/null; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') ERROR: sshpass not installed. Run: sudo apt install sshpass"
    exit 1
fi

TIMESTAMP=$(date '+%Y-%m-%d_%H%M%S')
BACKUP_NAME="invitation-app_${TIMESTAMP}"
REMOTE_DIR="${NAS_PATH}/invitation-app"
REMOTE_BACKUP="${REMOTE_DIR}/${BACKUP_NAME}"

export SSHPASS="${NAS_PASSWORD}"
SSH_OPTS="-o StrictHostKeyChecking=no"

echo "$(date '+%Y-%m-%d %H:%M:%S') Starting backup to ${NAS_USER}@${NAS_HOST}:${REMOTE_BACKUP}"

# Create remote backup directory
sshpass -e ssh ${SSH_OPTS} "${NAS_USER}@${NAS_HOST}" "mkdir -p '${REMOTE_BACKUP}'"

# Rsync the entire app folder, excluding unnecessary files
rsync -az --delete \
    -e "sshpass -e ssh ${SSH_OPTS}" \
    --exclude='venv/' \
    --exclude='__pycache__/' \
    --exclude='*.pyc' \
    --exclude='.claude/' \
    --exclude='backup.log' \
    "$APP_DIR/" "${NAS_USER}@${NAS_HOST}:${REMOTE_BACKUP}/"

echo "$(date '+%Y-%m-%d %H:%M:%S') Backup complete: ${REMOTE_BACKUP}"

# Clean up old backups
if [ "$KEEP_DAYS" -gt 0 ]; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') Cleaning up backups older than ${KEEP_DAYS} days..."
    sshpass -e ssh ${SSH_OPTS} "${NAS_USER}@${NAS_HOST}" "find '${REMOTE_DIR}' -maxdepth 1 -name 'invitation-app_*' -type d -mtime +${KEEP_DAYS} -exec rm -rf {} +"
    echo "$(date '+%Y-%m-%d %H:%M:%S') Cleanup done."
fi
