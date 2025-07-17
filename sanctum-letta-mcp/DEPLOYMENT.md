# Promptyoself Deployment Guide

This guide provides comprehensive instructions for deploying the Promptyoself plugin in production environments.

## Overview

Promptyoself is a self-hosted prompt scheduler for Letta agents delivered as a Sanctum MCP CLI plugin. It provides automated prompt scheduling with cron-like functionality and interval-based scheduling.

## Prerequisites

- Linux system with systemd (Ubuntu 20.04+, CentOS 8+, or equivalent)
- Python 3.8 or higher
- SQLite 3
- Root/sudo access for system installation
- Network access to your Letta server

## Quick Start

### 1. System Installation

```bash
# Clone the repository
git clone <repository-url>
cd sanctum-letta-mcp

# Install as system service
sudo ./install_systemd.sh install

# Configure your Letta API key
sudo nano /etc/default/promptyoself

# Start services
sudo ./install_systemd.sh start

# Check status
sudo ./install_systemd.sh status
```

### 2. Configuration

Edit `/etc/default/promptyoself` to configure:

```bash
# Letta configuration
LETTA_BASE_URL=https://your-letta-server.com/
LETTA_API_KEY=your-api-key-here

# Database configuration
PROMPTYOSELF_DB=/opt/promptyoself/data/promptyoself.db

# Logging configuration
PROMPTYOSELF_LOG_LEVEL=INFO
PROMPTYOSELF_LOG_DIR=/var/log/promptyoself
```

### 3. Basic Usage

```bash
# Add the plugin to your MCP server configuration
# Register a recurring prompt
promptyoself register --agent-id "agent-123" --prompt "Daily standup" --cron "0 9 * * MON-FRI"

# List scheduled prompts
promptyoself list

# Check system health
python3 /opt/promptyoself/monitor_promptyoself.py --mode check
```

## Detailed Deployment

### Manual Installation

If you prefer manual installation or need to customize the setup:

#### 1. Create Service User

```bash
sudo groupadd --system promptyoself
sudo useradd --system --gid promptyoself --home-dir /opt/promptyoself \
    --shell /bin/false --comment "Promptyoself service user" promptyoself
```

#### 2. Create Directories

```bash
sudo mkdir -p /opt/promptyoself/{data,logs}
sudo mkdir -p /var/log/promptyoself
sudo chown -R promptyoself:promptyoself /opt/promptyoself /var/log/promptyoself
```

#### 3. Install Application

```bash
# Copy application files
sudo cp -r smcp /opt/promptyoself/
sudo cp monitor_promptyoself.py /opt/promptyoself/
sudo cp -r maintenance /opt/promptyoself/
sudo cp requirements.txt /opt/promptyoself/

# Set ownership
sudo chown -R promptyoself:promptyoself /opt/promptyoself
```

#### 4. Setup Virtual Environment

```bash
sudo -u promptyoself python3 -m venv /opt/promptyoself/venv
sudo -u promptyoself /opt/promptyoself/venv/bin/pip install -r /opt/promptyoself/requirements.txt
```

#### 5. Initialize Database

```bash
sudo -u promptyoself PYTHONPATH=/opt/promptyoself \
    /opt/promptyoself/venv/bin/python /opt/promptyoself/smcp/plugins/promptyoself/db.py
```

#### 6. Install SystemD Services

```bash
sudo cp systemd/*.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable promptyoself promptyoself-monitor promptyoself-mcp
```

### Docker Deployment

For containerized deployment:

#### 1. Create Dockerfile

```dockerfile
FROM python:3.11-slim

# Create user
RUN groupadd --system promptyoself && \
    useradd --system --gid promptyoself promptyoself

# Set working directory
WORKDIR /opt/promptyoself

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY smcp/ smcp/
COPY monitor_promptyoself.py .
COPY maintenance/ maintenance/

# Set ownership
RUN chown -R promptyoself:promptyoself /opt/promptyoself

# Create data directory
RUN mkdir -p /opt/promptyoself/data && \
    chown promptyoself:promptyoself /opt/promptyoself/data

# Switch to service user
USER promptyoself

# Initialize database
RUN python smcp/plugins/promptyoself/db.py

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python monitor_promptyoself.py --mode check --component database || exit 1

# Start command
CMD ["python", "smcp/plugins/promptyoself/cli.py", "execute", "--loop"]
```

#### 2. Docker Compose

```yaml
version: '3.8'

services:
  promptyoself:
    build: .
    container_name: promptyoself-scheduler
    environment:
      - LETTA_BASE_URL=https://your-letta-server.com/
      - LETTA_API_KEY=your-api-key-here
      - PROMPTYOSELF_DB=/opt/promptyoself/data/promptyoself.db
      - PROMPTYOSELF_LOG_LEVEL=INFO
    volumes:
      - promptyoself-data:/opt/promptyoself/data
    restart: unless-stopped
    depends_on:
      - promptyoself-mcp

  promptyoself-mcp:
    build: .
    container_name: promptyoself-mcp
    command: ["python", "smcp/mcp_server.py", "--host", "0.0.0.0", "--port", "8000"]
    ports:
      - "8000:8000"
    environment:
      - LETTA_BASE_URL=https://your-letta-server.com/
      - LETTA_API_KEY=your-api-key-here
      - PROMPTYOSELF_DB=/opt/promptyoself/data/promptyoself.db
      - MCP_PORT=8000
    volumes:
      - promptyoself-data:/opt/promptyoself/data
    restart: unless-stopped

  promptyoself-monitor:
    build: .
    container_name: promptyoself-monitor
    command: ["python", "monitor_promptyoself.py", "--mode", "monitor", "--interval", "300"]
    environment:
      - LETTA_BASE_URL=https://your-letta-server.com/
      - LETTA_API_KEY=your-api-key-here
      - PROMPTYOSELF_DB=/opt/promptyoself/data/promptyoself.db
      - MONITOR_LOG_LEVEL=INFO
    volumes:
      - promptyoself-data:/opt/promptyoself/data
    restart: unless-stopped
    depends_on:
      - promptyoself

volumes:
  promptyoself-data:
```

## Configuration Reference

### Environment Variables

#### Core Configuration
- `LETTA_BASE_URL`: URL of your Letta server
- `LETTA_API_KEY`: API key for Letta authentication
- `PROMPTYOSELF_DB`: Database file path (default: `promptyoself.db`)

#### Logging Configuration
- `PROMPTYOSELF_LOG_LEVEL`: Log level (DEBUG, INFO, WARNING, ERROR)
- `PROMPTYOSELF_LOG_DIR`: Log directory path
- `PROMPTYOSELF_LOG_CONSOLE`: Enable console logging (true/false)
- `PROMPTYOSELF_LOG_FILE`: Enable file logging (true/false)
- `PROMPTYOSELF_LOG_STRUCTURED`: Enable structured JSON logging (true/false)

#### MCP Configuration
- `MCP_PORT`: MCP server port (default: 8000)
- `MCP_PLUGINS_DIR`: Plugin directory path

#### Monitoring Configuration
- `MONITOR_LOG_LEVEL`: Monitor log level
- `PROMPTYOSELF_HEALTH_TIMEOUT`: Health check timeout in seconds
- `PROMPTYOSELF_CPU_THRESHOLD`: CPU usage alert threshold (%)
- `PROMPTYOSELF_MEMORY_THRESHOLD`: Memory usage alert threshold (%)
- `PROMPTYOSELF_DISK_THRESHOLD`: Disk usage alert threshold (%)

### Service Configuration

#### SystemD Services

Three systemd services are provided:

1. **promptyoself.service**: Main scheduler service
2. **promptyoself-monitor.service**: Health monitoring service
3. **promptyoself-mcp.service**: MCP server service

#### Service Management

```bash
# Start all services
sudo systemctl start promptyoself promptyoself-monitor promptyoself-mcp

# Stop all services
sudo systemctl stop promptyoself promptyoself-monitor promptyoself-mcp

# Restart services
sudo systemctl restart promptyoself

# Check service status
sudo systemctl status promptyoself

# View logs
sudo journalctl -u promptyoself -f
```

## Monitoring and Maintenance

### Health Monitoring

The monitoring script provides comprehensive health checks:

```bash
# Run full health check
python3 /opt/promptyoself/monitor_promptyoself.py --mode check

# Check specific component
python3 /opt/promptyoself/monitor_promptyoself.py --mode check --component database

# Generate health report
python3 /opt/promptyoself/monitor_promptyoself.py --mode check --format json > health_report.json

# Start continuous monitoring
python3 /opt/promptyoself/monitor_promptyoself.py --mode monitor --interval 300
```

### Database Maintenance

```bash
# Create database backup
./maintenance/backup_database.sh

# List existing backups
./maintenance/backup_database.sh list

# Restore from backup
./maintenance/backup_database.sh restore backup_file.db.gz

# Verify backup integrity
./maintenance/backup_database.sh verify backup_file.db.gz
```

### Log Management

```bash
# Clean up old logs
./maintenance/cleanup_logs.sh

# Show log statistics
./maintenance/cleanup_logs.sh stats

# Rotate large logs
./maintenance/cleanup_logs.sh rotate

# Run comprehensive cleanup
./maintenance/cleanup_logs.sh all
```

### System Health Checks

```bash
# Check system health
./maintenance/system_health.sh

# Generate health report
./maintenance/system_health.sh report

# Check specific component
./maintenance/system_health.sh memory
./maintenance/system_health.sh disk
./maintenance/system_health.sh processes
```

## Security Considerations

### File Permissions

- Application files: `755` (promptyoself:promptyoself)
- Database files: `644` (promptyoself:promptyoself)
- Log files: `644` (promptyoself:promptyoself)
- Configuration files: `640` (root:promptyoself)

### Network Security

- MCP server binds to `0.0.0.0:8000` by default
- Consider using a reverse proxy (nginx/Apache) for production
- Implement firewall rules to restrict access
- Use TLS/SSL for external connections

### API Security

- Store Letta API key in environment variables, not in code
- Use environment file with restricted permissions
- Rotate API keys regularly
- Monitor API usage for anomalies

## Troubleshooting

### Common Issues

#### Service Won't Start

```bash
# Check service status
sudo systemctl status promptyoself

# Check logs
sudo journalctl -u promptyoself -n 50

# Check configuration
sudo -u promptyoself python3 -c "import smcp.plugins.promptyoself.cli; print('Import successful')"
```

#### Database Issues

```bash
# Check database integrity
sqlite3 /opt/promptyoself/data/promptyoself.db "PRAGMA integrity_check;"

# Reset database
sudo -u promptyoself python3 /opt/promptyoself/smcp/plugins/promptyoself/db.py

# Check permissions
ls -la /opt/promptyoself/data/
```

#### Letta Connection Issues

```bash
# Test connection
sudo -u promptyoself PYTHONPATH=/opt/promptyoself \
    /opt/promptyoself/venv/bin/python /opt/promptyoself/smcp/plugins/promptyoself/cli.py test

# Check network connectivity
curl -v https://your-letta-server.com/

# Verify API key
echo $LETTA_API_KEY
```

#### Performance Issues

```bash
# Check system resources
./maintenance/system_health.sh

# Monitor process usage
top -u promptyoself

# Check log file sizes
du -h /var/log/promptyoself/
```

### Log Analysis

#### Common Log Patterns

```bash
# Find errors in logs
grep -i error /var/log/promptyoself/*.log

# Find failed prompt executions
grep "Failed to deliver prompt" /var/log/promptyoself/promptyoself.log

# Monitor scheduler activity
grep "Executed.*prompts" /var/log/promptyoself/promptyoself.log

# Check health monitoring
grep "Health check" /var/log/promptyoself/monitor_promptyoself.log
```

## Performance Optimization

### Resource Tuning

#### Memory Usage

```bash
# Monitor memory usage
sudo systemctl status promptyoself | grep Memory

# Adjust memory limits in systemd
sudo systemctl edit promptyoself
```

#### CPU Usage

```bash
# Monitor CPU usage
sudo systemctl status promptyoself | grep CPU

# Adjust CPU limits in systemd
sudo systemctl edit promptyoself
```

### Database Optimization

```bash
# Vacuum database
sqlite3 /opt/promptyoself/data/promptyoself.db "VACUUM;"

# Analyze database
sqlite3 /opt/promptyoself/data/promptyoself.db "ANALYZE;"

# Check database size
du -h /opt/promptyoself/data/promptyoself.db
```

## Backup and Recovery

### Automated Backups

Set up automated backups using cron:

```bash
# Edit crontab for promptyoself user
sudo crontab -u promptyoself -e

# Add backup job (daily at 2 AM)
0 2 * * * /opt/promptyoself/maintenance/backup_database.sh

# Add log cleanup job (weekly)
0 3 * * 0 /opt/promptyoself/maintenance/cleanup_logs.sh all
```

### Recovery Procedures

#### Database Recovery

```bash
# Stop services
sudo systemctl stop promptyoself promptyoself-monitor

# Restore database
sudo -u promptyoself /opt/promptyoself/maintenance/backup_database.sh restore backup_file.db.gz

# Verify restoration
sqlite3 /opt/promptyoself/data/promptyoself.db "SELECT COUNT(*) FROM schedules;"

# Start services
sudo systemctl start promptyoself promptyoself-monitor
```

#### Full System Recovery

```bash
# Reinstall application
sudo ./install_systemd.sh install

# Restore configuration
sudo cp /backup/promptyoself.conf /etc/default/promptyoself

# Restore database
sudo -u promptyoself /opt/promptyoself/maintenance/backup_database.sh restore backup_file.db.gz

# Start services
sudo ./install_systemd.sh start
```

## Scaling Considerations

### Horizontal Scaling

For high-availability deployments:

1. **Load Balancer**: Use nginx/HAProxy for MCP server
2. **Shared Database**: Use PostgreSQL instead of SQLite
3. **Container Orchestration**: Deploy with Kubernetes/Docker Swarm
4. **Monitoring**: Integrate with Prometheus/Grafana

### Vertical Scaling

For increased capacity:

1. **Increase Resources**: Adjust systemd resource limits
2. **Optimize Database**: Use proper indexing and query optimization
3. **Tune Scheduler**: Adjust execution intervals and batch sizes
4. **Monitor Performance**: Use profiling tools to identify bottlenecks

## Integration

### MCP Client Integration

```json
{
  "mcpServers": {
    "promptyoself": {
      "command": "python",
      "args": ["/opt/promptyoself/smcp/mcp_server.py"],
      "env": {
        "LETTA_BASE_URL": "https://your-letta-server.com/",
        "LETTA_API_KEY": "your-api-key-here"
      }
    }
  }
}
```

### API Integration

The MCP server exposes the following tools:

- `promptyoself.register`: Register new prompt schedules
- `promptyoself.list`: List existing schedules
- `promptyoself.execute`: Execute due prompts
- `promptyoself.test`: Test Letta connection
- `promptyoself.agents`: List available agents

## Support

For issues and questions:

1. Check the logs: `/var/log/promptyoself/`
2. Run health checks: `monitor_promptyoself.py --mode check`
3. Review configuration: `/etc/default/promptyoself`
4. Consult documentation: This file and inline code comments

## License

This project is licensed under the MIT License. See the LICENSE file for details.