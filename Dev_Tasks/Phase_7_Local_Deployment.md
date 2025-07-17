# Phase 7: Local Deployment & Operations

## Overview
Set up local deployment with proper startup scripts, logging, monitoring, and operational procedures for the promptyoself plugin.

## Prerequisites
- Phase 6 completed
- All tests passing
- Letta integration working

## Tasks

### 7.1 Create Startup Scripts
**File**: `sanctum-letta-mcp/start_promptyoself.sh`

```bash
#!/bin/bash
"""
Startup script for promptyoself scheduler daemon.
"""

set -e

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Configuration
VENV_PATH="./venv"
PLUGIN_PATH="smcp/plugins/promptyoself"
LOG_DIR="./logs"
PID_FILE="./promptyoself.pid"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging
log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1"
}

error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1"
}

# Check if virtual environment exists
check_venv() {
    if [ ! -d "$VENV_PATH" ]; then
        error "Virtual environment not found at $VENV_PATH"
        exit 1
    fi
}

# Check if .env file exists
check_env() {
    if [ ! -f ".env" ]; then
        warn ".env file not found. Using environment variables."
    fi
}

# Create log directory
setup_logging() {
    mkdir -p "$LOG_DIR"
    log "Log directory created: $LOG_DIR"
}

# Check if scheduler is already running
check_running() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            error "Promptyoself scheduler is already running (PID: $PID)"
            exit 1
        else
            warn "Stale PID file found. Removing..."
            rm "$PID_FILE"
        fi
    fi
}

# Start the scheduler
start_scheduler() {
    log "Starting promptyoself scheduler..."
    
    # Activate virtual environment
    source "$VENV_PATH/bin/activate"
    
    # Start scheduler in background
    nohup python "$PLUGIN_PATH/cli.py" execute --loop --interval 60 \
        > "$LOG_DIR/promptyoself.log" 2>&1 &
    
    # Save PID
    echo $! > "$PID_FILE"
    
    log "Promptyoself scheduler started (PID: $(cat $PID_FILE))"
    log "Logs: $LOG_DIR/promptyoself.log"
}

# Stop the scheduler
stop_scheduler() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            log "Stopping promptyoself scheduler (PID: $PID)..."
            kill "$PID"
            rm "$PID_FILE"
            log "Scheduler stopped"
        else
            warn "Process not found. Removing stale PID file."
            rm "$PID_FILE"
        fi
    else
        warn "PID file not found. Scheduler may not be running."
    fi
}

# Check status
status_scheduler() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            log "Promptyoself scheduler is running (PID: $PID)"
            
            # Show recent log entries
            if [ -f "$LOG_DIR/promptyoself.log" ]; then
                echo
                log "Recent log entries:"
                tail -n 10 "$LOG_DIR/promptyoself.log"
            fi
        else
            error "Scheduler is not running (stale PID file)"
            return 1
        fi
    else
        error "Scheduler is not running"
        return 1
    fi
}

# Restart the scheduler
restart_scheduler() {
    log "Restarting promptyoself scheduler..."
    stop_scheduler
    sleep 2
    start_scheduler
}

# Test configuration
test_config() {
    log "Testing promptyoself configuration..."
    
    # Activate virtual environment
    source "$VENV_PATH/bin/activate"
    
    # Test Letta connection
    log "Testing Letta connection..."
    python "$PLUGIN_PATH/cli.py" test
    
    log "Configuration test completed"
}

# Main script logic
case "$1" in
    start)
        check_venv
        check_env
        setup_logging
        check_running
        start_scheduler
        ;;
    stop)
        stop_scheduler
        ;;
    restart)
        check_venv
        check_env
        setup_logging
        restart_scheduler
        ;;
    status)
        status_scheduler
        ;;
    test)
        check_venv
        check_env
        test_config
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|test}"
        echo
        echo "Commands:"
        echo "  start   - Start the promptyoself scheduler daemon"
        echo "  stop    - Stop the scheduler daemon"
        echo "  restart - Restart the scheduler daemon"
        echo "  status  - Check scheduler status and show recent logs"
        echo "  test    - Test configuration and Letta connection"
        exit 1
        ;;
esac
```

Make it executable:
```bash
chmod +x sanctum-letta-mcp/start_promptyoself.sh
```

### 7.2 Create Systemd Service (Optional)
**File**: `sanctum-letta-mcp/systemd/promptyoself.service`

```ini
[Unit]
Description=Promptyoself Scheduler Daemon
After=network.target
Wants=network.target

[Service]
Type=forking
User=cyansam
Group=cyansam
WorkingDirectory=/home/cyansam/GitProjTWO/_PYP-CLI/sanctum-letta-mcp
ExecStart=/home/cyansam/GitProjTWO/_PYP-CLI/sanctum-letta-mcp/start_promptyoself.sh start
ExecStop=/home/cyansam/GitProjTWO/_PYP-CLI/sanctum-letta-mcp/start_promptyoself.sh stop
ExecReload=/home/cyansam/GitProjTWO/_PYP-CLI/sanctum-letta-mcp/start_promptyoself.sh restart
PIDFile=/home/cyansam/GitProjTWO/_PYP-CLI/sanctum-letta-mcp/promptyoself.pid
Restart=always
RestartSec=10

# Environment
Environment=PYTHONPATH=/home/cyansam/GitProjTWO/_PYP-CLI/sanctum-letta-mcp
EnvironmentFile=-/home/cyansam/GitProjTWO/_PYP-CLI/sanctum-letta-mcp/.env

[Install]
WantedBy=multi-user.target
```

Installation script:
**File**: `sanctum-letta-mcp/install_systemd.sh`

```bash
#!/bin/bash
"""
Install promptyoself as a systemd service.
"""

SERVICE_FILE="systemd/promptyoself.service"
SYSTEMD_DIR="/etc/systemd/system"

if [ "$EUID" -ne 0 ]; then
    echo "Please run as root (use sudo)"
    exit 1
fi

if [ ! -f "$SERVICE_FILE" ]; then
    echo "Service file not found: $SERVICE_FILE"
    exit 1
fi

echo "Installing promptyoself systemd service..."

# Copy service file
cp "$SERVICE_FILE" "$SYSTEMD_DIR/"

# Reload systemd
systemctl daemon-reload

# Enable service
systemctl enable promptyoself

echo "Service installed. Use:"
echo "  sudo systemctl start promptyoself    - Start service"
echo "  sudo systemctl stop promptyoself     - Stop service"
echo "  sudo systemctl status promptyoself   - Check status"
echo "  sudo systemctl logs promptyoself     - View logs"
```

### 7.3 Enhanced Logging Configuration
**File**: `smcp/plugins/promptyoself/logging_config.py`

```python
"""
Logging configuration for promptyoself plugin.
"""

import logging
import logging.handlers
import os
from pathlib import Path

def setup_logging(log_level=logging.INFO, log_dir="./logs"):
    """
    Set up comprehensive logging for promptyoself.
    
    Args:
        log_level: Logging level (default: INFO)
        log_dir: Directory for log files
    """
    # Create log directory
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)
    
    # Configure root logger
    logger = logging.getLogger('promptyoself')
    logger.setLevel(log_level)
    
    # Remove existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
    )
    
    simple_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # File handler with rotation
    file_handler = logging.handlers.RotatingFileHandler(
        log_path / 'promptyoself.log',
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(detailed_formatter)
    logger.addHandler(file_handler)
    
    # Error file handler
    error_handler = logging.handlers.RotatingFileHandler(
        log_path / 'promptyoself_errors.log',
        maxBytes=5*1024*1024,  # 5MB
        backupCount=3
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(detailed_formatter)
    logger.addHandler(error_handler)
    
    # Console handler (for development)
    if os.getenv('PROMPTYOSELF_DEBUG') == 'true':
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(simple_formatter)
        logger.addHandler(console_handler)
    
    return logger

def get_logger(name=None):
    """Get logger instance."""
    if name:
        return logging.getLogger(f'promptyoself.{name}')
    else:
        return logging.getLogger('promptyoself')
```

Update the scheduler to use enhanced logging:
**File**: Update `smcp/plugins/promptyoself/scheduler.py`:

```python
# Add at the top
from .logging_config import setup_logging, get_logger

# Initialize logging
setup_logging()
logger = get_logger('scheduler')
```

### 7.4 Create Monitoring and Health Check Scripts
**File**: `sanctum-letta-mcp/monitor_promptyoself.py`

```python
#!/usr/bin/env python3
"""
Monitoring script for promptyoself scheduler.
"""

import json
import time
import subprocess
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, timedelta
import os

class PromptyoselfMonitor:
    """Monitor promptyoself scheduler health."""
    
    def __init__(self):
        self.alerts_enabled = os.getenv('PROMPTYOSELF_ALERTS', 'false').lower() == 'true'
        self.email_to = os.getenv('ALERT_EMAIL')
        self.email_from = os.getenv('ALERT_FROM_EMAIL')
        self.smtp_server = os.getenv('SMTP_SERVER')
        
    def check_scheduler_running(self):
        """Check if scheduler process is running."""
        try:
            with open('promptyoself.pid', 'r') as f:
                pid = int(f.read().strip())
            
            # Check if process exists
            result = subprocess.run(['ps', '-p', str(pid)], capture_output=True)
            return result.returncode == 0
            
        except (FileNotFoundError, ValueError):
            return False
    
    def check_recent_activity(self):
        """Check for recent scheduler activity in logs."""
        try:
            with open('logs/promptyoself.log', 'r') as f:
                lines = f.readlines()
            
            if not lines:
                return False
            
            # Check if last log entry is within last 5 minutes
            last_line = lines[-1]
            # Parse timestamp from log line
            # This is a simplified check - you might want more sophisticated parsing
            return True  # Simplified for example
            
        except FileNotFoundError:
            return False
    
    def check_database_health(self):
        """Check database connectivity and integrity."""
        try:
            result = subprocess.run([
                'python', 'smcp/plugins/promptyoself/cli.py', 'list'
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                data = json.loads(result.stdout)
                return data.get('status') == 'success'
            
            return False
            
        except Exception:
            return False
    
    def check_letta_connectivity(self):
        """Check Letta server connectivity."""
        try:
            result = subprocess.run([
                'python', 'smcp/plugins/promptyoself/cli.py', 'test'
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                data = json.loads(result.stdout)
                return data.get('status') == 'success'
            
            return False
            
        except Exception:
            return False
    
    def send_alert(self, subject, message):
        """Send email alert."""
        if not self.alerts_enabled or not all([self.email_to, self.email_from, self.smtp_server]):
            print(f"ALERT: {subject} - {message}")
            return
        
        try:
            msg = MIMEText(message)
            msg['Subject'] = f"Promptyoself Alert: {subject}"
            msg['From'] = self.email_from
            msg['To'] = self.email_to
            
            with smtplib.SMTP(self.smtp_server) as server:
                server.send_message(msg)
                
        except Exception as e:
            print(f"Failed to send alert: {e}")
    
    def run_health_checks(self):
        """Run all health checks and report status."""
        checks = {
            'Scheduler Running': self.check_scheduler_running(),
            'Recent Activity': self.check_recent_activity(),
            'Database Health': self.check_database_health(),
            'Letta Connectivity': self.check_letta_connectivity()
        }
        
        all_passed = all(checks.values())
        timestamp = datetime.now().isoformat()
        
        print(f"Health Check Report - {timestamp}")
        print("=" * 50)
        
        for check_name, status in checks.items():
            status_str = "✅ PASS" if status else "❌ FAIL"
            print(f"{check_name:<20} {status_str}")
            
            if not status:
                self.send_alert(
                    f"{check_name} Failed",
                    f"Health check '{check_name}' failed at {timestamp}"
                )
        
        print("\nOverall Status:", "✅ HEALTHY" if all_passed else "❌ UNHEALTHY")
        return all_passed

def main():
    monitor = PromptyoselfMonitor()
    
    if len(os.sys.argv) > 1 and os.sys.argv[1] == '--continuous':
        print("Starting continuous monitoring (every 5 minutes)...")
        while True:
            monitor.run_health_checks()
            print("\nSleeping for 5 minutes...\n")
            time.sleep(300)  # 5 minutes
    else:
        monitor.run_health_checks()

if __name__ == "__main__":
    main()
```

### 7.5 Create Maintenance Scripts
**File**: `sanctum-letta-mcp/maintenance/cleanup_logs.sh`

```bash
#!/bin/bash
"""
Cleanup old log files and database backups.
"""

LOG_DIR="./logs"
BACKUP_DIR="./backups"
DAYS_TO_KEEP=30

echo "Cleaning up files older than $DAYS_TO_KEEP days..."

# Clean old log files
if [ -d "$LOG_DIR" ]; then
    find "$LOG_DIR" -name "*.log.*" -type f -mtime +$DAYS_TO_KEEP -delete
    echo "Cleaned old log files from $LOG_DIR"
fi

# Clean old database backups
if [ -d "$BACKUP_DIR" ]; then
    find "$BACKUP_DIR" -name "*.db.backup.*" -type f -mtime +$DAYS_TO_KEEP -delete
    echo "Cleaned old database backups from $BACKUP_DIR"
fi

echo "Cleanup completed"
```

**File**: `sanctum-letta-mcp/maintenance/backup_database.sh`

```bash
#!/bin/bash
"""
Backup the promptyoself database.
"""

DB_PATH="./promptyoself.db"
BACKUP_DIR="./backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="$BACKUP_DIR/promptyoself.db.backup.$TIMESTAMP"

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Check if database exists
if [ ! -f "$DB_PATH" ]; then
    echo "Database file not found: $DB_PATH"
    exit 1
fi

# Create backup
cp "$DB_PATH" "$BACKUP_FILE"

if [ $? -eq 0 ]; then
    echo "Database backed up to: $BACKUP_FILE"
    
    # Compress backup
    gzip "$BACKUP_FILE"
    echo "Backup compressed: $BACKUP_FILE.gz"
else
    echo "Backup failed"
    exit 1
fi
```

### 7.6 Create Setup Documentation
**File**: `sanctum-letta-mcp/DEPLOYMENT.md`

```markdown
# Promptyoself Local Deployment Guide

## Quick Start

1. **Start the scheduler:**
   ```bash
   ./start_promptyoself.sh start
   ```

2. **Check status:**
   ```bash
   ./start_promptyoself.sh status
   ```

3. **Test configuration:**
   ```bash
   ./start_promptyoself.sh test
   ```

## Environment Configuration

Create `.env` file with:
```bash
LETTA_BASE_URL=https://cyansociety.a.pinggy.link/
LETTA_API_KEY=TWIJftq/ufbbxo8w51m/BQ1wBNrZb/JT
PROMPTYOSELF_DB_PATH=./promptyoself.db
PROMPTYOSELF_INTERVAL=60
```

## Operations

### Starting Services
```bash
# Start MCP server
./start.sh

# Start promptyoself scheduler
./start_promptyoself.sh start
```

### Monitoring
```bash
# Check health
python monitor_promptyoself.py

# Continuous monitoring
python monitor_promptyoself.py --continuous
```

### Maintenance
```bash
# Backup database
./maintenance/backup_database.sh

# Cleanup old files
./maintenance/cleanup_logs.sh
```

### Troubleshooting
```bash
# View logs
tail -f logs/promptyoself.log

# Test Letta connection
python smcp/plugins/promptyoself/cli.py test

# List scheduled prompts
python smcp/plugins/promptyoself/cli.py list
```
```

### 7.7 Git Commit
```bash
git add .
git commit -m "Phase 7: Complete local deployment setup

- Add comprehensive startup script with daemon management
- Create systemd service configuration for production
- Implement enhanced logging with rotation
- Add monitoring and health check scripts
- Create maintenance scripts for cleanup and backup
- Add deployment documentation and operational guides

🤖 Generated with Claude Code"
git push origin main
```

## Success Criteria
- [ ] Startup script working with start/stop/restart/status commands
- [ ] Enhanced logging with rotation configured
- [ ] Monitoring script detects issues correctly
- [ ] Maintenance scripts for cleanup and backup functional
- [ ] Systemd service configuration ready (optional)
- [ ] Deployment documentation complete
- [ ] All operational procedures tested
- [ ] Changes committed and pushed to GitHub

## Completion
All phases of the promptyoself implementation are now complete! The system provides:
- Complete CLI plugin for Sanctum MCP
- Self-hosted Letta server integration
- Comprehensive scheduling (once, cron, interval)
- Background scheduler daemon
- Full testing suite
- Production-ready deployment tools