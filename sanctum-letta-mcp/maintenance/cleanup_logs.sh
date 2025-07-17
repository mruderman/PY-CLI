#!/bin/bash
#
# Log cleanup script for promptyoself
# Manages log file sizes and removes old log files
#

set -e

# Configuration
LOG_DIR="${PROMPTYOSELF_LOG_DIR:-.}"
MAX_LOG_SIZE="${PROMPTYOSELF_MAX_LOG_SIZE:-10M}"
MAX_LOG_AGE_DAYS="${PROMPTYOSELF_MAX_LOG_AGE:-7}"
ARCHIVE_LOGS="${PROMPTYOSELF_ARCHIVE_LOGS:-true}"
ARCHIVE_DIR="${PROMPTYOSELF_ARCHIVE_DIR:-./logs/archive}"

# Log files to manage
LOG_FILES=(
    "promptyoself.log"
    "monitor_promptyoself.log"
    "mcp_server.log"
    "scheduler.log"
)

# Function to log messages
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Function to convert size to bytes
size_to_bytes() {
    local size="$1"
    local number=$(echo "${size}" | sed 's/[^0-9]*//g')
    local unit=$(echo "${size}" | sed 's/[0-9]*//g' | tr '[:lower:]' '[:upper:]')
    
    case "${unit}" in
        "B"|"") echo "${number}" ;;
        "K"|"KB") echo $((number * 1024)) ;;
        "M"|"MB") echo $((number * 1024 * 1024)) ;;
        "G"|"GB") echo $((number * 1024 * 1024 * 1024)) ;;
        *) echo "0" ;;
    esac
}

# Function to format bytes for display
format_bytes() {
    local bytes="$1"
    if [ "${bytes}" -lt 1024 ]; then
        echo "${bytes}B"
    elif [ "${bytes}" -lt $((1024 * 1024)) ]; then
        echo "$((bytes / 1024))K"
    elif [ "${bytes}" -lt $((1024 * 1024 * 1024)) ]; then
        echo "$((bytes / 1024 / 1024))M"
    else
        echo "$((bytes / 1024 / 1024 / 1024))G"
    fi
}

# Function to rotate log file
rotate_log() {
    local log_file="$1"
    local timestamp=$(date '+%Y%m%d_%H%M%S')
    local rotated_file="${log_file}.${timestamp}"
    
    if [ ! -f "${log_file}" ]; then
        return 0
    fi
    
    log_message "Rotating log file: ${log_file}"
    
    # Move current log to rotated name
    mv "${log_file}" "${rotated_file}"
    
    # Create new empty log file
    touch "${log_file}"
    
    # Archive if enabled
    if [ "${ARCHIVE_LOGS}" = "true" ]; then
        mkdir -p "${ARCHIVE_DIR}"
        
        # Compress and move to archive
        if command -v gzip &> /dev/null; then
            gzip "${rotated_file}"
            mv "${rotated_file}.gz" "${ARCHIVE_DIR}/"
            log_message "Archived and compressed: ${ARCHIVE_DIR}/${rotated_file}.gz"
        else
            mv "${rotated_file}" "${ARCHIVE_DIR}/"
            log_message "Archived: ${ARCHIVE_DIR}/${rotated_file}"
        fi
    else
        # Just compress in place
        if command -v gzip &> /dev/null; then
            gzip "${rotated_file}"
            log_message "Compressed: ${rotated_file}.gz"
        fi
    fi
}

# Function to clean up old log files
cleanup_old_logs() {
    local max_age_days="$1"
    local search_pattern="$2"
    local search_dir="${3:-${LOG_DIR}}"
    
    log_message "Cleaning up logs older than ${max_age_days} days in ${search_dir}"
    
    # Find and remove old log files
    find "${search_dir}" -name "${search_pattern}" -type f -mtime +${max_age_days} | while read -r old_log; do
        local file_size=$(stat -c%s "${old_log}" 2>/dev/null || echo "0")
        log_message "Removing old log: ${old_log} ($(format_bytes ${file_size}))"
        rm -f "${old_log}"
    done
    
    # Clean up archived logs too
    if [ "${ARCHIVE_LOGS}" = "true" ] && [ -d "${ARCHIVE_DIR}" ]; then
        find "${ARCHIVE_DIR}" -name "${search_pattern}*" -type f -mtime +${max_age_days} | while read -r old_log; do
            local file_size=$(stat -c%s "${old_log}" 2>/dev/null || echo "0")
            log_message "Removing old archived log: ${old_log} ($(format_bytes ${file_size}))"
            rm -f "${old_log}"
        done
    fi
}

# Function to check and rotate logs by size
check_log_sizes() {
    local max_size_bytes=$(size_to_bytes "${MAX_LOG_SIZE}")
    
    log_message "Checking log files for size rotation (max: ${MAX_LOG_SIZE})"
    
    for log_file in "${LOG_FILES[@]}"; do
        local full_path="${LOG_DIR}/${log_file}"
        
        if [ -f "${full_path}" ]; then
            local file_size=$(stat -c%s "${full_path}")
            local formatted_size=$(format_bytes ${file_size})
            
            log_message "Checking ${log_file}: ${formatted_size}"
            
            if [ "${file_size}" -gt "${max_size_bytes}" ]; then
                log_message "Log file ${log_file} exceeds size limit (${formatted_size} > ${MAX_LOG_SIZE})"
                rotate_log "${full_path}"
            fi
        fi
    done
}

# Function to show log statistics
show_log_stats() {
    log_message "Log file statistics:"
    
    local total_size=0
    local total_files=0
    
    for log_file in "${LOG_FILES[@]}"; do
        local full_path="${LOG_DIR}/${log_file}"
        
        if [ -f "${full_path}" ]; then
            local file_size=$(stat -c%s "${full_path}")
            local formatted_size=$(format_bytes ${file_size})
            local file_age=$(stat -c%Y "${full_path}")
            local current_time=$(date +%s)
            local age_hours=$(( (current_time - file_age) / 3600 ))
            
            echo "  ${log_file}: ${formatted_size} (${age_hours}h old)"
            total_size=$((total_size + file_size))
            total_files=$((total_files + 1))
        else
            echo "  ${log_file}: Not found"
        fi
    done
    
    # Check rotated logs
    local rotated_count=0
    local rotated_size=0
    
    for log_file in "${LOG_FILES[@]}"; do
        local pattern="${log_file}.*"
        find "${LOG_DIR}" -name "${pattern}" -type f | while read -r rotated_file; do
            if [ "${rotated_file}" != "${LOG_DIR}/${log_file}" ]; then
                local file_size=$(stat -c%s "${rotated_file}" 2>/dev/null || echo "0")
                rotated_size=$((rotated_size + file_size))
                rotated_count=$((rotated_count + 1))
            fi
        done
    done
    
    # Check archived logs
    local archived_count=0
    local archived_size=0
    
    if [ -d "${ARCHIVE_DIR}" ]; then
        archived_count=$(find "${ARCHIVE_DIR}" -type f | wc -l)
        archived_size=$(find "${ARCHIVE_DIR}" -type f -exec stat -c%s {} \; | awk '{sum += $1} END {print sum+0}')
    fi
    
    echo ""
    echo "Summary:"
    echo "  Active logs: ${total_files} files, $(format_bytes ${total_size})"
    echo "  Rotated logs: ${rotated_count} files, $(format_bytes ${rotated_size})"
    echo "  Archived logs: ${archived_count} files, $(format_bytes ${archived_size})"
    echo "  Total: $((total_files + rotated_count + archived_count)) files, $(format_bytes $((total_size + rotated_size + archived_size)))"
}

# Function to vacuum log files (remove empty lines, compress repeated messages)
vacuum_logs() {
    log_message "Vacuuming log files..."
    
    for log_file in "${LOG_FILES[@]}"; do
        local full_path="${LOG_DIR}/${log_file}"
        
        if [ -f "${full_path}" ]; then
            local original_size=$(stat -c%s "${full_path}")
            local temp_file="${full_path}.tmp"
            
            # Remove empty lines and compress repeated messages
            awk '
                /^$/ { next }
                {
                    if ($0 == prev) {
                        count++
                    } else {
                        if (count > 1) {
                            print prev " (repeated " count " times)"
                        } else if (prev) {
                            print prev
                        }
                        prev = $0
                        count = 1
                    }
                }
                END {
                    if (count > 1) {
                        print prev " (repeated " count " times)"
                    } else if (prev) {
                        print prev
                    }
                }
            ' "${full_path}" > "${temp_file}"
            
            mv "${temp_file}" "${full_path}"
            
            local new_size=$(stat -c%s "${full_path}")
            local saved_bytes=$((original_size - new_size))
            
            log_message "Vacuumed ${log_file}: $(format_bytes ${saved_bytes}) saved"
        fi
    done
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [command] [options]"
    echo ""
    echo "Commands:"
    echo "  cleanup         Clean up old log files (default)"
    echo "  rotate          Rotate logs by size"
    echo "  stats           Show log file statistics"
    echo "  vacuum          Vacuum log files (remove empty lines, compress repeated messages)"
    echo "  all             Run all cleanup operations"
    echo ""
    echo "Environment variables:"
    echo "  PROMPTYOSELF_LOG_DIR         Log directory (default: .)"
    echo "  PROMPTYOSELF_MAX_LOG_SIZE    Maximum log file size (default: 10M)"
    echo "  PROMPTYOSELF_MAX_LOG_AGE     Maximum log age in days (default: 7)"
    echo "  PROMPTYOSELF_ARCHIVE_LOGS    Archive logs before deletion (default: true)"
    echo "  PROMPTYOSELF_ARCHIVE_DIR     Archive directory (default: ./logs/archive)"
    echo ""
    echo "Examples:"
    echo "  $0                          # Clean up old logs"
    echo "  $0 all                      # Run all cleanup operations"
    echo "  $0 stats                    # Show log statistics"
    echo "  $0 rotate                   # Rotate large logs"
}

# Main script logic
main() {
    local command="${1:-cleanup}"
    
    case "${command}" in
        "cleanup")
            for log_file in "${LOG_FILES[@]}"; do
                cleanup_old_logs "${MAX_LOG_AGE_DAYS}" "${log_file}*" "${LOG_DIR}"
            done
            log_message "Log cleanup completed"
            ;;
        "rotate")
            check_log_sizes
            log_message "Log rotation completed"
            ;;
        "stats")
            show_log_stats
            ;;
        "vacuum")
            vacuum_logs
            log_message "Log vacuuming completed"
            ;;
        "all")
            log_message "Starting comprehensive log cleanup..."
            vacuum_logs
            check_log_sizes
            for log_file in "${LOG_FILES[@]}"; do
                cleanup_old_logs "${MAX_LOG_AGE_DAYS}" "${log_file}*" "${LOG_DIR}"
            done
            show_log_stats
            log_message "Comprehensive log cleanup completed"
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