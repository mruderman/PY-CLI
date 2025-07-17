#!/bin/bash
#
# System health check script for promptyoself
# Comprehensive system diagnostics and health reporting
#

set -e

# Configuration
HEALTH_CHECK_TIMEOUT="${PROMPTYOSELF_HEALTH_TIMEOUT:-30}"
ALERT_THRESHOLD_CPU="${PROMPTYOSELF_CPU_THRESHOLD:-80}"
ALERT_THRESHOLD_MEMORY="${PROMPTYOSELF_MEMORY_THRESHOLD:-80}"
ALERT_THRESHOLD_DISK="${PROMPTYOSELF_DISK_THRESHOLD:-90}"
REPORT_FORMAT="${PROMPTYOSELF_REPORT_FORMAT:-text}"
REPORT_FILE="${PROMPTYOSELF_REPORT_FILE:-system_health_report.txt}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to log messages with timestamp
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Function to print colored output
print_status() {
    local status="$1"
    local message="$2"
    
    case "${status}" in
        "OK"|"HEALTHY")
            echo -e "${GREEN}✓ ${message}${NC}"
            ;;
        "WARNING"|"WARN")
            echo -e "${YELLOW}⚠ ${message}${NC}"
            ;;
        "ERROR"|"CRITICAL")
            echo -e "${RED}✗ ${message}${NC}"
            ;;
        "INFO")
            echo -e "${BLUE}ℹ ${message}${NC}"
            ;;
        *)
            echo "  ${message}"
            ;;
    esac
}

# Function to check system load
check_system_load() {
    local load_avg=$(uptime | awk -F'load average:' '{print $2}' | awk '{print $1}' | tr -d ',')
    local cpu_count=$(nproc)
    local load_percent=$(echo "scale=2; ${load_avg} * 100 / ${cpu_count}" | bc -l)
    
    echo "System Load:"
    echo "  Load Average: ${load_avg}"
    echo "  CPU Cores: ${cpu_count}"
    echo "  Load Percentage: ${load_percent}%"
    
    if (( $(echo "${load_percent} > ${ALERT_THRESHOLD_CPU}" | bc -l) )); then
        print_status "WARNING" "High system load: ${load_percent}%"
        return 1
    else
        print_status "OK" "System load normal: ${load_percent}%"
        return 0
    fi
}

# Function to check memory usage
check_memory_usage() {
    local memory_info=$(free -m)
    local total_mem=$(echo "${memory_info}" | awk '/^Mem:/ {print $2}')
    local used_mem=$(echo "${memory_info}" | awk '/^Mem:/ {print $3}')
    local free_mem=$(echo "${memory_info}" | awk '/^Mem:/ {print $4}')
    local mem_percent=$(echo "scale=2; ${used_mem} * 100 / ${total_mem}" | bc -l)
    
    echo "Memory Usage:"
    echo "  Total Memory: ${total_mem}MB"
    echo "  Used Memory: ${used_mem}MB"
    echo "  Free Memory: ${free_mem}MB"
    echo "  Memory Usage: ${mem_percent}%"
    
    if (( $(echo "${mem_percent} > ${ALERT_THRESHOLD_MEMORY}" | bc -l) )); then
        print_status "WARNING" "High memory usage: ${mem_percent}%"
        return 1
    else
        print_status "OK" "Memory usage normal: ${mem_percent}%"
        return 0
    fi
}

# Function to check disk usage
check_disk_usage() {
    local disk_info=$(df -h . | tail -n 1)
    local total_disk=$(echo "${disk_info}" | awk '{print $2}')
    local used_disk=$(echo "${disk_info}" | awk '{print $3}')
    local free_disk=$(echo "${disk_info}" | awk '{print $4}')
    local disk_percent=$(echo "${disk_info}" | awk '{print $5}' | tr -d '%')
    
    echo "Disk Usage:"
    echo "  Total Disk: ${total_disk}"
    echo "  Used Disk: ${used_disk}"
    echo "  Free Disk: ${free_disk}"
    echo "  Disk Usage: ${disk_percent}%"
    
    if [ "${disk_percent}" -gt "${ALERT_THRESHOLD_DISK}" ]; then
        print_status "WARNING" "High disk usage: ${disk_percent}%"
        return 1
    else
        print_status "OK" "Disk usage normal: ${disk_percent}%"
        return 0
    fi
}

# Function to check process health
check_process_health() {
    local processes_to_check=(
        "python.*mcp_server.py"
        "python.*promptyoself.*cli.py"
        "python.*monitor_promptyoself.py"
    )
    
    echo "Process Health:"
    
    local process_issues=0
    
    for process_pattern in "${processes_to_check[@]}"; do
        local pid=$(pgrep -f "${process_pattern}" || echo "")
        
        if [ -n "${pid}" ]; then
            local process_info=$(ps -p "${pid}" -o pid,ppid,pcpu,pmem,cmd --no-headers)
            local cpu_usage=$(echo "${process_info}" | awk '{print $3}')
            local mem_usage=$(echo "${process_info}" | awk '{print $4}')
            
            echo "  ${process_pattern}: PID ${pid}"
            echo "    CPU: ${cpu_usage}%, Memory: ${mem_usage}%"
            
            # Check if process is consuming too many resources
            if (( $(echo "${cpu_usage} > 50" | bc -l) )); then
                print_status "WARNING" "High CPU usage for ${process_pattern}: ${cpu_usage}%"
                process_issues=$((process_issues + 1))
            fi
            
            if (( $(echo "${mem_usage} > 20" | bc -l) )); then
                print_status "WARNING" "High memory usage for ${process_pattern}: ${mem_usage}%"
                process_issues=$((process_issues + 1))
            fi
        else
            print_status "WARNING" "Process not found: ${process_pattern}"
            process_issues=$((process_issues + 1))
        fi
    done
    
    if [ "${process_issues}" -eq 0 ]; then
        print_status "OK" "All processes healthy"
        return 0
    else
        print_status "WARNING" "${process_issues} process issues found"
        return 1
    fi
}

# Function to check network connectivity
check_network_connectivity() {
    local letta_url="${LETTA_BASE_URL:-https://cyansociety.a.pinggy.link/}"
    local timeout="${HEALTH_CHECK_TIMEOUT}"
    
    echo "Network Connectivity:"
    
    # Check internet connectivity
    if ping -c 1 -W 5 8.8.8.8 >/dev/null 2>&1; then
        print_status "OK" "Internet connectivity available"
    else
        print_status "ERROR" "No internet connectivity"
        return 1
    fi
    
    # Check Letta server connectivity
    if command -v curl >/dev/null 2>&1; then
        local http_status=$(curl -s -o /dev/null -w "%{http_code}" --max-time "${timeout}" "${letta_url}" || echo "000")
        
        if [ "${http_status}" -eq 200 ] || [ "${http_status}" -eq 401 ]; then
            print_status "OK" "Letta server reachable (HTTP ${http_status})"
        else
            print_status "ERROR" "Letta server unreachable (HTTP ${http_status})"
            return 1
        fi
    else
        print_status "WARNING" "curl not available, skipping Letta connectivity check"
    fi
    
    return 0
}

# Function to check file system health
check_filesystem_health() {
    local important_files=(
        "promptyoself.db"
        "smcp/plugins/promptyoself/cli.py"
        "smcp/mcp_server.py"
        "monitor_promptyoself.py"
    )
    
    echo "File System Health:"
    
    local file_issues=0
    
    for file_path in "${important_files[@]}"; do
        if [ -f "${file_path}" ]; then
            local file_size=$(stat -c%s "${file_path}")
            local file_age=$(stat -c%Y "${file_path}")
            local current_time=$(date +%s)
            local age_hours=$(( (current_time - file_age) / 3600 ))
            
            echo "  ${file_path}: $(format_bytes ${file_size}), ${age_hours}h old"
            
            # Check if file is readable
            if [ ! -r "${file_path}" ]; then
                print_status "ERROR" "File not readable: ${file_path}"
                file_issues=$((file_issues + 1))
            fi
            
            # Check if database file is not corrupted (if sqlite3 is available)
            if [[ "${file_path}" == *.db ]] && command -v sqlite3 >/dev/null 2>&1; then
                if ! sqlite3 "${file_path}" "PRAGMA integrity_check;" | grep -q "ok"; then
                    print_status "ERROR" "Database corruption detected: ${file_path}"
                    file_issues=$((file_issues + 1))
                fi
            fi
        else
            print_status "ERROR" "File not found: ${file_path}"
            file_issues=$((file_issues + 1))
        fi
    done
    
    if [ "${file_issues}" -eq 0 ]; then
        print_status "OK" "All important files healthy"
        return 0
    else
        print_status "ERROR" "${file_issues} file system issues found"
        return 1
    fi
}

# Function to check log file health
check_log_health() {
    local log_files=(
        "promptyoself.log"
        "monitor_promptyoself.log"
        "mcp_server.log"
    )
    
    echo "Log File Health:"
    
    local log_issues=0
    local total_log_size=0
    
    for log_file in "${log_files[@]}"; do
        if [ -f "${log_file}" ]; then
            local file_size=$(stat -c%s "${log_file}")
            total_log_size=$((total_log_size + file_size))
            
            echo "  ${log_file}: $(format_bytes ${file_size})"
            
            # Check for recent errors in log files
            if [ -r "${log_file}" ]; then
                local error_count=$(grep -c "ERROR" "${log_file}" 2>/dev/null || echo "0")
                local warning_count=$(grep -c "WARNING" "${log_file}" 2>/dev/null || echo "0")
                
                if [ "${error_count}" -gt 0 ]; then
                    print_status "WARNING" "${error_count} errors found in ${log_file}"
                    log_issues=$((log_issues + 1))
                fi
                
                if [ "${warning_count}" -gt 10 ]; then
                    print_status "WARNING" "${warning_count} warnings found in ${log_file}"
                fi
            fi
        else
            echo "  ${log_file}: Not found"
        fi
    done
    
    echo "  Total log size: $(format_bytes ${total_log_size})"
    
    if [ "${log_issues}" -eq 0 ]; then
        print_status "OK" "Log files healthy"
        return 0
    else
        print_status "WARNING" "${log_issues} log issues found"
        return 1
    fi
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

# Function to run Python monitoring script
run_python_monitoring() {
    if [ -f "monitor_promptyoself.py" ]; then
        echo "Running Python monitoring script..."
        python3 monitor_promptyoself.py --mode check --format json 2>/dev/null | jq '.' 2>/dev/null || {
            echo "Python monitoring script failed or jq not available"
            return 1
        }
    else
        print_status "WARNING" "Python monitoring script not found"
        return 1
    fi
}

# Function to generate health report
generate_health_report() {
    local report_file="$1"
    local issues_found=0
    
    {
        echo "Promptyoself System Health Report"
        echo "Generated: $(date)"
        echo "================================"
        echo ""
        
        echo "System Load Check:"
        check_system_load || issues_found=$((issues_found + 1))
        echo ""
        
        echo "Memory Usage Check:"
        check_memory_usage || issues_found=$((issues_found + 1))
        echo ""
        
        echo "Disk Usage Check:"
        check_disk_usage || issues_found=$((issues_found + 1))
        echo ""
        
        echo "Process Health Check:"
        check_process_health || issues_found=$((issues_found + 1))
        echo ""
        
        echo "Network Connectivity Check:"
        check_network_connectivity || issues_found=$((issues_found + 1))
        echo ""
        
        echo "File System Health Check:"
        check_filesystem_health || issues_found=$((issues_found + 1))
        echo ""
        
        echo "Log File Health Check:"
        check_log_health || issues_found=$((issues_found + 1))
        echo ""
        
        echo "Summary:"
        if [ "${issues_found}" -eq 0 ]; then
            echo "✅ System is healthy - no issues found"
        else
            echo "⚠️  ${issues_found} issues found - requires attention"
        fi
    } | tee "${report_file}"
    
    return "${issues_found}"
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [command] [options]"
    echo ""
    echo "Commands:"
    echo "  check           Run full health check (default)"
    echo "  report          Generate health report file"
    echo "  monitor         Run continuous monitoring"
    echo "  load            Check system load only"
    echo "  memory          Check memory usage only"
    echo "  disk            Check disk usage only"
    echo "  processes       Check process health only"
    echo "  network         Check network connectivity only"
    echo "  filesystem      Check file system health only"
    echo "  logs            Check log file health only"
    echo ""
    echo "Environment variables:"
    echo "  PROMPTYOSELF_HEALTH_TIMEOUT     Network timeout in seconds (default: 30)"
    echo "  PROMPTYOSELF_CPU_THRESHOLD      CPU alert threshold % (default: 80)"
    echo "  PROMPTYOSELF_MEMORY_THRESHOLD   Memory alert threshold % (default: 80)"
    echo "  PROMPTYOSELF_DISK_THRESHOLD     Disk alert threshold % (default: 90)"
    echo "  PROMPTYOSELF_REPORT_FORMAT      Report format (default: text)"
    echo "  PROMPTYOSELF_REPORT_FILE        Report file path (default: system_health_report.txt)"
    echo ""
    echo "Examples:"
    echo "  $0                              # Run full health check"
    echo "  $0 report                       # Generate health report"
    echo "  $0 memory                       # Check memory usage only"
}

# Main script logic
main() {
    local command="${1:-check}"
    
    case "${command}" in
        "check")
            log_message "Starting comprehensive health check..."
            generate_health_report "/dev/null"
            local exit_code=$?
            if [ "${exit_code}" -eq 0 ]; then
                log_message "Health check completed successfully"
            else
                log_message "Health check completed with ${exit_code} issues"
            fi
            exit "${exit_code}"
            ;;
        "report")
            log_message "Generating health report: ${REPORT_FILE}"
            generate_health_report "${REPORT_FILE}"
            log_message "Health report generated: ${REPORT_FILE}"
            ;;
        "monitor")
            log_message "Starting continuous monitoring..."
            while true; do
                generate_health_report "/dev/null"
                sleep 60
            done
            ;;
        "load")
            check_system_load
            ;;
        "memory")
            check_memory_usage
            ;;
        "disk")
            check_disk_usage
            ;;
        "processes")
            check_process_health
            ;;
        "network")
            check_network_connectivity
            ;;
        "filesystem")
            check_filesystem_health
            ;;
        "logs")
            check_log_health
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

# Ensure bc is available for calculations
if ! command -v bc >/dev/null 2>&1; then
    echo "Warning: bc command not found. Some calculations may fail."
fi

# Run main function with all arguments
main "$@"