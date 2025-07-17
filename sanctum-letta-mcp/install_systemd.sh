#!/bin/bash
#
# SystemD installation script for promptyoself
# Sets up user, directories, and systemd services
#

set -e

# Configuration
INSTALL_DIR="/opt/promptyoself"
SERVICE_USER="promptyoself"
SERVICE_GROUP="promptyoself"
LOG_DIR="/var/log/promptyoself"
DATA_DIR="/opt/promptyoself/data"
CONFIG_FILE="/etc/default/promptyoself"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    local status="$1"
    local message="$2"
    
    case "${status}" in
        "OK")
            echo -e "${GREEN}✓ ${message}${NC}"
            ;;
        "WARNING")
            echo -e "${YELLOW}⚠ ${message}${NC}"
            ;;
        "ERROR")
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

# Function to log messages
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Function to check if running as root
check_root() {
    if [ "$EUID" -ne 0 ]; then
        print_status "ERROR" "This script must be run as root"
        echo "Usage: sudo $0 [command]"
        exit 1
    fi
}

# Function to create service user
create_service_user() {
    print_status "INFO" "Creating service user and group..."
    
    # Create group if it doesn't exist
    if ! getent group "${SERVICE_GROUP}" >/dev/null; then
        groupadd --system "${SERVICE_GROUP}"
        print_status "OK" "Created group: ${SERVICE_GROUP}"
    else
        print_status "OK" "Group already exists: ${SERVICE_GROUP}"
    fi
    
    # Create user if it doesn't exist
    if ! getent passwd "${SERVICE_USER}" >/dev/null; then
        useradd --system --gid "${SERVICE_GROUP}" --home-dir "${INSTALL_DIR}" \
                --shell /bin/false --comment "Promptyoself service user" "${SERVICE_USER}"
        print_status "OK" "Created user: ${SERVICE_USER}"
    else
        print_status "OK" "User already exists: ${SERVICE_USER}"
    fi
}

# Function to create directories
create_directories() {
    print_status "INFO" "Creating directories..."
    
    # Create install directory
    mkdir -p "${INSTALL_DIR}"
    print_status "OK" "Created install directory: ${INSTALL_DIR}"
    
    # Create data directory
    mkdir -p "${DATA_DIR}"
    print_status "OK" "Created data directory: ${DATA_DIR}"
    
    # Create log directory
    mkdir -p "${LOG_DIR}"
    print_status "OK" "Created log directory: ${LOG_DIR}"
    
    # Create backup directory
    mkdir -p "${DATA_DIR}/backups"
    print_status "OK" "Created backup directory: ${DATA_DIR}/backups"
    
    # Set ownership
    chown -R "${SERVICE_USER}:${SERVICE_GROUP}" "${INSTALL_DIR}" "${DATA_DIR}" "${LOG_DIR}"
    print_status "OK" "Set ownership for directories"
    
    # Set permissions
    chmod 755 "${INSTALL_DIR}" "${DATA_DIR}" "${LOG_DIR}"
    chmod 750 "${DATA_DIR}/backups"
    print_status "OK" "Set permissions for directories"
}

# Function to install application files
install_application() {
    print_status "INFO" "Installing application files..."
    
    # Copy application files
    if [ -d "smcp" ]; then
        cp -r smcp "${INSTALL_DIR}/"
        print_status "OK" "Copied smcp directory"
    else
        print_status "ERROR" "smcp directory not found in current directory"
        exit 1
    fi
    
    # Copy monitoring script
    if [ -f "monitor_promptyoself.py" ]; then
        cp monitor_promptyoself.py "${INSTALL_DIR}/"
        print_status "OK" "Copied monitoring script"
    else
        print_status "ERROR" "monitor_promptyoself.py not found in current directory"
        exit 1
    fi
    
    # Copy maintenance scripts
    if [ -d "maintenance" ]; then
        cp -r maintenance "${INSTALL_DIR}/"
        print_status "OK" "Copied maintenance scripts"
    else
        print_status "WARNING" "maintenance directory not found"
    fi
    
    # Copy requirements and other files
    for file in requirements.txt run_tests.py pytest.ini; do
        if [ -f "${file}" ]; then
            cp "${file}" "${INSTALL_DIR}/"
            print_status "OK" "Copied ${file}"
        else
            print_status "WARNING" "${file} not found"
        fi
    done
    
    # Set ownership
    chown -R "${SERVICE_USER}:${SERVICE_GROUP}" "${INSTALL_DIR}"
    print_status "OK" "Set ownership for application files"
}

# Function to setup virtual environment
setup_virtualenv() {
    print_status "INFO" "Setting up virtual environment..."
    
    # Create virtual environment
    python3 -m venv "${INSTALL_DIR}/venv"
    print_status "OK" "Created virtual environment"
    
    # Activate and install requirements
    source "${INSTALL_DIR}/venv/bin/activate"
    
    # Upgrade pip
    pip install --upgrade pip
    print_status "OK" "Upgraded pip"
    
    # Install requirements
    if [ -f "${INSTALL_DIR}/requirements.txt" ]; then
        pip install -r "${INSTALL_DIR}/requirements.txt"
        print_status "OK" "Installed Python requirements"
    else
        print_status "WARNING" "requirements.txt not found, skipping package installation"
    fi
    
    # Set ownership
    chown -R "${SERVICE_USER}:${SERVICE_GROUP}" "${INSTALL_DIR}/venv"
    print_status "OK" "Set ownership for virtual environment"
}

# Function to create configuration file
create_config_file() {
    print_status "INFO" "Creating configuration file..."
    
    cat > "${CONFIG_FILE}" <<EOF
# Promptyoself service configuration
# This file is sourced by systemd services

# Database configuration
PROMPTYOSELF_DB=${DATA_DIR}/promptyoself.db
PROMPTYOSELF_BACKUP_DIR=${DATA_DIR}/backups

# Logging configuration
PROMPTYOSELF_LOG_DIR=${LOG_DIR}
PROMPTYOSELF_LOG_LEVEL=INFO
PROMPTYOSELF_LOG_CONSOLE=false
PROMPTYOSELF_LOG_FILE=true
PROMPTYOSELF_LOG_STRUCTURED=false

# Letta configuration
LETTA_BASE_URL=https://cyansociety.a.pinggy.link/
# LETTA_API_KEY=your-api-key-here

# MCP configuration
MCP_PORT=8000
MCP_PLUGINS_DIR=${INSTALL_DIR}/smcp/plugins

# Python path
PYTHONPATH=${INSTALL_DIR}

# Monitoring configuration
MONITOR_LOG_LEVEL=INFO
PROMPTYOSELF_HEALTH_TIMEOUT=30
PROMPTYOSELF_CPU_THRESHOLD=80
PROMPTYOSELF_MEMORY_THRESHOLD=80
PROMPTYOSELF_DISK_THRESHOLD=90
EOF
    
    # Set permissions
    chmod 640 "${CONFIG_FILE}"
    chown root:${SERVICE_GROUP} "${CONFIG_FILE}"
    print_status "OK" "Created configuration file: ${CONFIG_FILE}"
}

# Function to install systemd services
install_systemd_services() {
    print_status "INFO" "Installing systemd services..."
    
    # Copy service files
    local service_files=(
        "promptyoself.service"
        "promptyoself-monitor.service"
        "promptyoself-mcp.service"
    )
    
    for service_file in "${service_files[@]}"; do
        if [ -f "systemd/${service_file}" ]; then
            cp "systemd/${service_file}" "/etc/systemd/system/"
            print_status "OK" "Installed ${service_file}"
        else
            print_status "WARNING" "systemd/${service_file} not found"
        fi
    done
    
    # Reload systemd
    systemctl daemon-reload
    print_status "OK" "Reloaded systemd daemon"
    
    # Enable services
    for service_file in "${service_files[@]}"; do
        local service_name="${service_file%.*}"
        if systemctl enable "${service_name}"; then
            print_status "OK" "Enabled ${service_name}"
        else
            print_status "WARNING" "Failed to enable ${service_name}"
        fi
    done
}

# Function to setup logrotate
setup_logrotate() {
    print_status "INFO" "Setting up log rotation..."
    
    cat > "/etc/logrotate.d/promptyoself" <<EOF
${LOG_DIR}/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 644 ${SERVICE_USER} ${SERVICE_GROUP}
    postrotate
        systemctl reload promptyoself || true
        systemctl reload promptyoself-monitor || true
        systemctl reload promptyoself-mcp || true
    endscript
}
EOF
    
    print_status "OK" "Created logrotate configuration"
}

# Function to initialize database
initialize_database() {
    print_status "INFO" "Initializing database..."
    
    # Run database initialization as service user
    sudo -u "${SERVICE_USER}" -g "${SERVICE_GROUP}" \
        PYTHONPATH="${INSTALL_DIR}" \
        "${INSTALL_DIR}/venv/bin/python" \
        "${INSTALL_DIR}/smcp/plugins/promptyoself/db.py"
    
    print_status "OK" "Database initialized"
}

# Function to run post-install checks
run_post_install_checks() {
    print_status "INFO" "Running post-install checks..."
    
    # Check if services are installed
    local services=("promptyoself" "promptyoself-monitor" "promptyoself-mcp")
    for service in "${services[@]}"; do
        if systemctl is-enabled "${service}" >/dev/null 2>&1; then
            print_status "OK" "Service ${service} is enabled"
        else
            print_status "WARNING" "Service ${service} is not enabled"
        fi
    done
    
    # Check file permissions
    if [ -r "${CONFIG_FILE}" ]; then
        print_status "OK" "Configuration file is readable"
    else
        print_status "WARNING" "Configuration file is not readable"
    fi
    
    # Check if database can be accessed
    if sudo -u "${SERVICE_USER}" -g "${SERVICE_GROUP}" \
        PYTHONPATH="${INSTALL_DIR}" \
        "${INSTALL_DIR}/venv/bin/python" -c "import smcp.plugins.promptyoself.db; print('Database accessible')" >/dev/null 2>&1; then
        print_status "OK" "Database is accessible"
    else
        print_status "WARNING" "Database is not accessible"
    fi
}

# Function to start services
start_services() {
    print_status "INFO" "Starting services..."
    
    # Start services in order
    local services=("promptyoself-mcp" "promptyoself" "promptyoself-monitor")
    for service in "${services[@]}"; do
        if systemctl start "${service}"; then
            print_status "OK" "Started ${service}"
        else
            print_status "ERROR" "Failed to start ${service}"
        fi
    done
    
    # Wait a moment for services to start
    sleep 5
    
    # Check service status
    for service in "${services[@]}"; do
        if systemctl is-active "${service}" >/dev/null 2>&1; then
            print_status "OK" "Service ${service} is running"
        else
            print_status "WARNING" "Service ${service} is not running"
        fi
    done
}

# Function to stop services
stop_services() {
    print_status "INFO" "Stopping services..."
    
    local services=("promptyoself-monitor" "promptyoself" "promptyoself-mcp")
    for service in "${services[@]}"; do
        if systemctl stop "${service}"; then
            print_status "OK" "Stopped ${service}"
        else
            print_status "WARNING" "Failed to stop ${service}"
        fi
    done
}

# Function to uninstall
uninstall() {
    print_status "INFO" "Uninstalling promptyoself..."
    
    # Stop services
    stop_services
    
    # Disable services
    local services=("promptyoself" "promptyoself-monitor" "promptyoself-mcp")
    for service in "${services[@]}"; do
        systemctl disable "${service}" || true
        rm -f "/etc/systemd/system/${service}.service"
        print_status "OK" "Removed ${service}"
    done
    
    # Reload systemd
    systemctl daemon-reload
    
    # Remove files
    rm -rf "${INSTALL_DIR}"
    rm -rf "${LOG_DIR}"
    rm -f "${CONFIG_FILE}"
    rm -f "/etc/logrotate.d/promptyoself"
    
    print_status "OK" "Removed files and directories"
    
    # Remove user (optional)
    read -p "Remove service user ${SERVICE_USER}? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        userdel "${SERVICE_USER}" || true
        groupdel "${SERVICE_GROUP}" || true
        print_status "OK" "Removed service user and group"
    fi
    
    print_status "OK" "Uninstall completed"
}

# Function to show service status
show_status() {
    print_status "INFO" "Service status:"
    
    local services=("promptyoself" "promptyoself-monitor" "promptyoself-mcp")
    for service in "${services[@]}"; do
        echo
        echo "=== ${service} ==="
        systemctl status "${service}" --no-pager --lines=5 || true
    done
}

# Function to show logs
show_logs() {
    local service="${1:-promptyoself}"
    local lines="${2:-50}"
    
    print_status "INFO" "Showing logs for ${service}..."
    journalctl -u "${service}" -n "${lines}" --no-pager
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [command] [options]"
    echo ""
    echo "Commands:"
    echo "  install         Install promptyoself systemd services (default)"
    echo "  uninstall       Uninstall promptyoself systemd services"
    echo "  start           Start all services"
    echo "  stop            Stop all services"
    echo "  restart         Restart all services"
    echo "  status          Show service status"
    echo "  logs [service]  Show logs for service"
    echo ""
    echo "Examples:"
    echo "  sudo $0 install     # Install services"
    echo "  sudo $0 start       # Start services"
    echo "  sudo $0 status      # Show status"
    echo "  sudo $0 logs        # Show promptyoself logs"
    echo "  sudo $0 logs promptyoself-monitor  # Show monitor logs"
}

# Main installation function
install() {
    print_status "INFO" "Starting promptyoself installation..."
    
    create_service_user
    create_directories
    install_application
    setup_virtualenv
    create_config_file
    install_systemd_services
    setup_logrotate
    initialize_database
    run_post_install_checks
    
    print_status "OK" "Installation completed successfully!"
    echo
    echo "Next steps:"
    echo "1. Edit ${CONFIG_FILE} to configure your Letta API key"
    echo "2. Start services with: sudo $0 start"
    echo "3. Check status with: sudo $0 status"
    echo "4. View logs with: sudo $0 logs"
}

# Main script logic
main() {
    local command="${1:-install}"
    
    case "${command}" in
        "install")
            check_root
            install
            ;;
        "uninstall")
            check_root
            uninstall
            ;;
        "start")
            check_root
            start_services
            ;;
        "stop")
            check_root
            stop_services
            ;;
        "restart")
            check_root
            stop_services
            sleep 2
            start_services
            ;;
        "status")
            show_status
            ;;
        "logs")
            show_logs "$2" "$3"
            ;;
        "help"|"-h"|"--help")
            show_usage
            ;;
        *)
            print_status "ERROR" "Unknown command: ${command}"
            show_usage
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"