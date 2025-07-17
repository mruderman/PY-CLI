#!/bin/bash
# 
# Promptyoself Scheduler Management Script
# 
# This script manages the promptyoself scheduler daemon for Letta prompt scheduling.
# It provides commands to start, stop, restart, check status, and test the scheduler.
#

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${SCRIPT_DIR}/venv"
PYTHON_BIN="${VENV_DIR}/bin/python"
PLUGIN_DIR="${SCRIPT_DIR}/smcp/plugins/promptyoself"
CLI_SCRIPT="${PLUGIN_DIR}/cli.py"
PIDFILE="${SCRIPT_DIR}/promptyoself.pid"
LOGFILE="${SCRIPT_DIR}/promptyoself.log"
INTERVAL="${PROMPTYOSELF_INTERVAL:-60}"
DB_PATH="${PROMPTYOSELF_DB_PATH:-${SCRIPT_DIR}/promptyoself.db}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${1}" | tee -a "${LOGFILE}"
}

# Check if virtual environment exists
check_venv() {
    if [[ ! -f "${PYTHON_BIN}" ]]; then
        log "${RED}ERROR: Virtual environment not found at ${VENV_DIR}${NC}"
        log "${YELLOW}Please run: python -m venv venv && ./venv/bin/pip install -r requirements.txt${NC}"
        exit 1
    fi
}

# Check if plugin exists
check_plugin() {
    if [[ ! -f "${CLI_SCRIPT}" ]]; then
        log "${RED}ERROR: Promptyoself CLI not found at ${CLI_SCRIPT}${NC}"
        exit 1
    fi
}

# Check if process is running
is_running() {
    if [[ -f "${PIDFILE}" ]]; then
        local pid=$(cat "${PIDFILE}")
        if kill -0 "${pid}" 2>/dev/null; then
            return 0
        else
            # PID file exists but process is dead
            rm -f "${PIDFILE}"
            return 1
        fi
    else
        return 1
    fi
}

# Get process status
get_status() {
    if is_running; then
        local pid=$(cat "${PIDFILE}")
        echo "running (PID: ${pid})"
    else
        echo "stopped"
    fi
}

# Start the scheduler
start_scheduler() {
    log "${BLUE}Starting promptyoself scheduler...${NC}"
    
    check_venv
    check_plugin
    
    if is_running; then
        log "${YELLOW}Scheduler is already running (PID: $(cat "${PIDFILE}"))${NC}"
        return 0
    fi
    
    # Ensure log file exists
    touch "${LOGFILE}"
    
    # Set required environment variables
    export PYTHONPATH="${SCRIPT_DIR}"
    export PROMPTYOSELF_DB_PATH="${DB_PATH}"
    
    # Check environment variables
    if [[ -z "${LETTA_API_KEY}" ]]; then
        log "${RED}ERROR: LETTA_API_KEY environment variable not set${NC}"
        log "${YELLOW}Please set LETTA_API_KEY before starting the scheduler${NC}"
        exit 1
    fi
    
    # Start scheduler in background
    log "${BLUE}Starting scheduler with interval: ${INTERVAL}s${NC}"
    log "${BLUE}Database path: ${DB_PATH}${NC}"
    log "${BLUE}Log file: ${LOGFILE}${NC}"
    
    nohup "${PYTHON_BIN}" -m smcp.plugins.promptyoself.cli execute --loop --interval "${INTERVAL}" \
        >> "${LOGFILE}" 2>&1 &
    
    local pid=$!
    echo "${pid}" > "${PIDFILE}"
    
    # Wait a moment to check if process started successfully
    sleep 2
    
    if is_running; then
        log "${GREEN}Scheduler started successfully (PID: ${pid})${NC}"
        return 0
    else
        log "${RED}ERROR: Failed to start scheduler${NC}"
        log "${YELLOW}Check log file for details: ${LOGFILE}${NC}"
        return 1
    fi
}

# Stop the scheduler
stop_scheduler() {
    log "${BLUE}Stopping promptyoself scheduler...${NC}"
    
    if ! is_running; then
        log "${YELLOW}Scheduler is not running${NC}"
        return 0
    fi
    
    local pid=$(cat "${PIDFILE}")
    
    # Send SIGTERM
    if kill "${pid}" 2>/dev/null; then
        log "${BLUE}Sent SIGTERM to process ${pid}${NC}"
        
        # Wait for graceful shutdown
        local count=0
        while kill -0 "${pid}" 2>/dev/null && [[ ${count} -lt 10 ]]; do
            sleep 1
            count=$((count + 1))
        done
        
        # Force kill if still running
        if kill -0 "${pid}" 2>/dev/null; then
            log "${YELLOW}Process still running, sending SIGKILL${NC}"
            kill -9 "${pid}" 2>/dev/null || true
        fi
        
        # Clean up PID file
        rm -f "${PIDFILE}"
        log "${GREEN}Scheduler stopped successfully${NC}"
        return 0
    else
        log "${RED}ERROR: Failed to stop scheduler${NC}"
        return 1
    fi
}

# Restart the scheduler
restart_scheduler() {
    log "${BLUE}Restarting promptyoself scheduler...${NC}"
    stop_scheduler
    sleep 2
    start_scheduler
}

# Show scheduler status
show_status() {
    local status=$(get_status)
    log "${BLUE}Promptyoself scheduler status: ${status}${NC}"
    
    if is_running; then
        local pid=$(cat "${PIDFILE}")
        local uptime=$(ps -o etime= -p "${pid}" 2>/dev/null | tr -d ' ' || echo "unknown")
        log "${BLUE}Uptime: ${uptime}${NC}"
        log "${BLUE}Log file: ${LOGFILE}${NC}"
        log "${BLUE}Database: ${DB_PATH}${NC}"
        log "${BLUE}Interval: ${INTERVAL}s${NC}"
    fi
}

# Test the scheduler components
test_scheduler() {
    log "${BLUE}Testing promptyoself scheduler components...${NC}"
    
    check_venv
    check_plugin
    
    # Set environment variables
    export PYTHONPATH="${SCRIPT_DIR}"
    export PROMPTYOSELF_DB_PATH="${DB_PATH}"
    
    # Test Letta connection
    log "${BLUE}Testing Letta connection...${NC}"
    if "${PYTHON_BIN}" -m smcp.plugins.promptyoself.cli test; then
        log "${GREEN}✓ Letta connection test passed${NC}"
    else
        log "${RED}✗ Letta connection test failed${NC}"
        return 1
    fi
    
    # Test database access
    log "${BLUE}Testing database access...${NC}"
    if "${PYTHON_BIN}" -m smcp.plugins.promptyoself.cli list >/dev/null 2>&1; then
        log "${GREEN}✓ Database access test passed${NC}"
    else
        log "${RED}✗ Database access test failed${NC}"
        return 1
    fi
    
    # Test agent listing
    log "${BLUE}Testing agent listing...${NC}"
    if "${PYTHON_BIN}" -m smcp.plugins.promptyoself.cli agents >/dev/null 2>&1; then
        log "${GREEN}✓ Agent listing test passed${NC}"
    else
        log "${RED}✗ Agent listing test failed${NC}"
        return 1
    fi
    
    log "${GREEN}All tests passed! Scheduler is ready to run.${NC}"
    return 0
}

# Show scheduler logs
show_logs() {
    if [[ -f "${LOGFILE}" ]]; then
        local lines="${1:-50}"
        log "${BLUE}Showing last ${lines} lines of scheduler log:${NC}"
        tail -n "${lines}" "${LOGFILE}"
    else
        log "${YELLOW}Log file not found: ${LOGFILE}${NC}"
    fi
}

# Monitor scheduler (follow logs)
monitor_scheduler() {
    if [[ -f "${LOGFILE}" ]]; then
        log "${BLUE}Monitoring scheduler logs (Press Ctrl+C to stop):${NC}"
        tail -f "${LOGFILE}"
    else
        log "${YELLOW}Log file not found: ${LOGFILE}${NC}"
        return 1
    fi
}

# Show help
show_help() {
    echo "Usage: $0 {start|stop|restart|status|test|logs|monitor|help}"
    echo ""
    echo "Commands:"
    echo "  start    - Start the promptyoself scheduler daemon"
    echo "  stop     - Stop the promptyoself scheduler daemon"
    echo "  restart  - Restart the promptyoself scheduler daemon"
    echo "  status   - Show scheduler status"
    echo "  test     - Test scheduler components"
    echo "  logs     - Show recent scheduler logs (default: 50 lines)"
    echo "  monitor  - Monitor scheduler logs in real-time"
    echo "  help     - Show this help message"
    echo ""
    echo "Environment variables:"
    echo "  LETTA_API_KEY            - Letta API key (required)"
    echo "  LETTA_BASE_URL          - Letta server URL (optional)"
    echo "  PROMPTYOSELF_INTERVAL   - Scheduler interval in seconds (default: 60)"
    echo "  PROMPTYOSELF_DB_PATH    - Database file path (default: ./promptyoself.db)"
    echo ""
    echo "Examples:"
    echo "  $0 start                 # Start scheduler"
    echo "  $0 status                # Check status"
    echo "  $0 logs 100              # Show last 100 log lines"
    echo "  $0 test                  # Run component tests"
    echo "  PROMPTYOSELF_INTERVAL=30 $0 start  # Start with 30s interval"
}

# Main command dispatcher
main() {
    case "${1:-help}" in
        start)
            start_scheduler
            ;;
        stop)
            stop_scheduler
            ;;
        restart)
            restart_scheduler
            ;;
        status)
            show_status
            ;;
        test)
            test_scheduler
            ;;
        logs)
            show_logs "${2}"
            ;;
        monitor)
            monitor_scheduler
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            log "${RED}ERROR: Unknown command: ${1}${NC}"
            show_help
            exit 1
            ;;
    esac
}

# Run main function
main "$@"