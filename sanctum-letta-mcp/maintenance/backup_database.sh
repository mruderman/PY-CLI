#!/bin/bash
#
# Database backup script for promptyoself
# Creates timestamped backups of the SQLite database
#

set -e

# Configuration
DB_FILE="${PROMPTYOSELF_DB:-promptyoself.db}"
BACKUP_DIR="${PROMPTYOSELF_BACKUP_DIR:-./backups}"
RETENTION_DAYS="${PROMPTYOSELF_BACKUP_RETENTION:-30}"
LOG_FILE="${BACKUP_DIR}/backup.log"

# Create backup directory if it doesn't exist
mkdir -p "${BACKUP_DIR}"

# Function to log messages
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "${LOG_FILE}"
}

# Function to create backup
create_backup() {
    local timestamp=$(date '+%Y%m%d_%H%M%S')
    local backup_file="${BACKUP_DIR}/promptyoself_${timestamp}.db"
    
    log_message "Starting database backup..."
    
    # Check if database file exists
    if [ ! -f "${DB_FILE}" ]; then
        log_message "ERROR: Database file not found: ${DB_FILE}"
        exit 1
    fi
    
    # Create backup using sqlite3 .backup command for consistency
    if command -v sqlite3 &> /dev/null; then
        log_message "Creating backup using sqlite3..."
        sqlite3 "${DB_FILE}" ".backup ${backup_file}"
    else
        log_message "sqlite3 not found, using cp command..."
        cp "${DB_FILE}" "${backup_file}"
    fi
    
    # Verify backup was created
    if [ -f "${backup_file}" ]; then
        local original_size=$(stat -c%s "${DB_FILE}")
        local backup_size=$(stat -c%s "${backup_file}")
        log_message "Backup created successfully: ${backup_file}"
        log_message "Original size: ${original_size} bytes, Backup size: ${backup_size} bytes"
        
        # Compress backup
        if command -v gzip &> /dev/null; then
            log_message "Compressing backup..."
            gzip "${backup_file}"
            backup_file="${backup_file}.gz"
            log_message "Backup compressed: ${backup_file}"
        fi
        
        echo "${backup_file}"
    else
        log_message "ERROR: Failed to create backup"
        exit 1
    fi
}

# Function to cleanup old backups
cleanup_old_backups() {
    log_message "Cleaning up backups older than ${RETENTION_DAYS} days..."
    
    # Find and remove old backup files
    find "${BACKUP_DIR}" -name "promptyoself_*.db*" -mtime +${RETENTION_DAYS} -type f | while read -r old_backup; do
        log_message "Removing old backup: ${old_backup}"
        rm -f "${old_backup}"
    done
    
    log_message "Cleanup completed"
}

# Function to verify backup integrity
verify_backup() {
    local backup_file="$1"
    
    if [[ "${backup_file}" == *.gz ]]; then
        # Decompress for verification
        local temp_db="/tmp/promptyoself_verify_$(date +%s).db"
        gunzip -c "${backup_file}" > "${temp_db}"
        backup_file="${temp_db}"
    fi
    
    log_message "Verifying backup integrity..."
    
    if command -v sqlite3 &> /dev/null; then
        if sqlite3 "${backup_file}" "PRAGMA integrity_check;" | grep -q "ok"; then
            log_message "Backup integrity check passed"
        else
            log_message "ERROR: Backup integrity check failed"
            exit 1
        fi
    else
        log_message "WARNING: sqlite3 not available, skipping integrity check"
    fi
    
    # Clean up temp file if created
    if [[ "${backup_file}" == /tmp/promptyoself_verify_* ]]; then
        rm -f "${backup_file}"
    fi
}

# Function to list existing backups
list_backups() {
    log_message "Existing backups:"
    find "${BACKUP_DIR}" -name "promptyoself_*.db*" -type f -printf "%T@ %Tc %p\n" | sort -n | cut -d' ' -f2- | while read -r backup_info; do
        echo "  ${backup_info}"
    done
}

# Function to restore from backup
restore_backup() {
    local backup_file="$1"
    local target_file="${2:-${DB_FILE}}"
    
    if [ -z "${backup_file}" ]; then
        log_message "ERROR: No backup file specified"
        echo "Usage: $0 restore <backup_file> [target_file]"
        exit 1
    fi
    
    if [ ! -f "${backup_file}" ]; then
        log_message "ERROR: Backup file not found: ${backup_file}"
        exit 1
    fi
    
    log_message "Restoring backup from ${backup_file} to ${target_file}..."
    
    # Create backup of current database before restore
    if [ -f "${target_file}" ]; then
        local pre_restore_backup="${target_file}.pre_restore_$(date +%s)"
        cp "${target_file}" "${pre_restore_backup}"
        log_message "Created pre-restore backup: ${pre_restore_backup}"
    fi
    
    # Restore the backup
    if [[ "${backup_file}" == *.gz ]]; then
        gunzip -c "${backup_file}" > "${target_file}"
    else
        cp "${backup_file}" "${target_file}"
    fi
    
    # Verify restored database
    if command -v sqlite3 &> /dev/null; then
        if sqlite3 "${target_file}" "PRAGMA integrity_check;" | grep -q "ok"; then
            log_message "Database restored successfully and integrity check passed"
        else
            log_message "ERROR: Restored database failed integrity check"
            exit 1
        fi
    fi
    
    log_message "Restore completed successfully"
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [command] [options]"
    echo ""
    echo "Commands:"
    echo "  backup          Create a new backup (default)"
    echo "  list            List existing backups"
    echo "  restore <file>  Restore from backup file"
    echo "  cleanup         Clean up old backups"
    echo "  verify <file>   Verify backup integrity"
    echo ""
    echo "Environment variables:"
    echo "  PROMPTYOSELF_DB              Database file path (default: promptyoself.db)"
    echo "  PROMPTYOSELF_BACKUP_DIR      Backup directory (default: ./backups)"
    echo "  PROMPTYOSELF_BACKUP_RETENTION Backup retention in days (default: 30)"
    echo ""
    echo "Examples:"
    echo "  $0                          # Create backup"
    echo "  $0 backup                   # Create backup"
    echo "  $0 list                     # List backups"
    echo "  $0 restore backup.db.gz     # Restore from backup"
    echo "  $0 cleanup                  # Clean old backups"
}

# Main script logic
main() {
    local command="${1:-backup}"
    
    case "${command}" in
        "backup")
            backup_file=$(create_backup)
            verify_backup "${backup_file}"
            cleanup_old_backups
            log_message "Backup process completed successfully"
            ;;
        "list")
            list_backups
            ;;
        "restore")
            restore_backup "$2" "$3"
            ;;
        "cleanup")
            cleanup_old_backups
            ;;
        "verify")
            if [ -z "$2" ]; then
                log_message "ERROR: No backup file specified for verification"
                show_usage
                exit 1
            fi
            verify_backup "$2"
            ;;
        "help"|"-h"|"--help")
            show_usage
            ;;
        *)
            log_message "ERROR: Unknown command: ${command}"
            show_usage
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"