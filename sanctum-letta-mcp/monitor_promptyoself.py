#!/usr/bin/env python3
"""
Comprehensive monitoring script for the promptyoself plugin.
Monitors database health, scheduler status, Letta connectivity, and overall system health.
"""

import os
import sys
import json
import time
import logging
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from pathlib import Path

# Add the smcp package to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "smcp"))

from smcp.plugins.promptyoself.db import get_session, PromptSchedule, initialize_db
from smcp.plugins.promptyoself.letta_client import test_letta_connection, list_available_agents
from smcp.plugins.promptyoself.scheduler import get_due_schedules


class PromptyoselfMonitor:
    """Comprehensive monitoring for promptyoself system."""
    
    def __init__(self):
        self.db_path = os.environ.get("PROMPTYOSELF_DB", "promptyoself.db")
        self.log_level = os.environ.get("MONITOR_LOG_LEVEL", "INFO")
        self.setup_logging()
        
    def setup_logging(self):
        """Configure logging for the monitor."""
        logging.basicConfig(
            level=getattr(logging, self.log_level),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler('monitor_promptyoself.log')
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def check_database_health(self) -> Dict[str, Any]:
        """Check database connectivity and integrity."""
        try:
            # Check if database file exists
            if not os.path.exists(self.db_path):
                return {
                    "status": "error",
                    "message": f"Database file not found: {self.db_path}",
                    "file_exists": False
                }
            
            # Check database size
            db_size = os.path.getsize(self.db_path)
            
            # Test connection
            session = get_session()
            try:
                # Test basic query
                total_schedules = session.query(PromptSchedule).count()
                active_schedules = session.query(PromptSchedule).filter(PromptSchedule.active == True).count()
                
                # Check for due schedules
                due_schedules = get_due_schedules()
                
                # Check recent activity
                recent_cutoff = datetime.utcnow() - timedelta(hours=24)
                recent_executions = session.query(PromptSchedule).filter(
                    PromptSchedule.last_run >= recent_cutoff
                ).count()
                
                return {
                    "status": "healthy",
                    "file_exists": True,
                    "file_size_bytes": db_size,
                    "total_schedules": total_schedules,
                    "active_schedules": active_schedules,
                    "due_schedules": len(due_schedules),
                    "recent_executions_24h": recent_executions,
                    "connection_test": "success"
                }
            finally:
                session.close()
                
        except Exception as e:
            return {
                "status": "error",
                "message": f"Database health check failed: {str(e)}",
                "file_exists": os.path.exists(self.db_path)
            }
    
    def check_letta_connectivity(self) -> Dict[str, Any]:
        """Check connection to Letta server."""
        try:
            # Test basic connection
            conn_result = test_letta_connection()
            
            if conn_result["status"] == "success":
                # Also test agent listing
                agents_result = list_available_agents()
                
                return {
                    "status": "healthy",
                    "connection_test": "success",
                    "agent_count": conn_result.get("agent_count", 0),
                    "agents_accessible": agents_result["status"] == "success"
                }
            else:
                return {
                    "status": "unhealthy",
                    "connection_test": "failed",
                    "error_message": conn_result.get("message", "Unknown error")
                }
                
        except Exception as e:
            return {
                "status": "error",
                "message": f"Letta connectivity check failed: {str(e)}"
            }
    
    def check_scheduler_status(self) -> Dict[str, Any]:
        """Check scheduler process status (if running as daemon)."""
        try:
            # Check if scheduler process is running
            pid_file = "promptyoself_scheduler.pid"
            
            if os.path.exists(pid_file):
                with open(pid_file, 'r') as f:
                    pid = int(f.read().strip())
                
                # Check if process is actually running
                try:
                    os.kill(pid, 0)  # Signal 0 just checks if process exists
                    process_running = True
                except ProcessLookupError:
                    process_running = False
                
                return {
                    "status": "running" if process_running else "stopped",
                    "pid_file_exists": True,
                    "pid": pid,
                    "process_running": process_running
                }
            else:
                return {
                    "status": "stopped",
                    "pid_file_exists": False,
                    "message": "No PID file found - scheduler may not be running"
                }
                
        except Exception as e:
            return {
                "status": "error",
                "message": f"Scheduler status check failed: {str(e)}"
            }
    
    def check_system_resources(self) -> Dict[str, Any]:
        """Check system resource usage."""
        try:
            # Check disk space
            disk_usage = os.statvfs('.')
            free_bytes = disk_usage.f_bavail * disk_usage.f_frsize
            total_bytes = disk_usage.f_blocks * disk_usage.f_frsize
            
            # Check log file sizes
            log_files = ['monitor_promptyoself.log', 'promptyoself.log']
            log_sizes = {}
            
            for log_file in log_files:
                if os.path.exists(log_file):
                    log_sizes[log_file] = os.path.getsize(log_file)
            
            return {
                "status": "healthy",
                "disk_free_bytes": free_bytes,
                "disk_total_bytes": total_bytes,
                "disk_usage_percent": ((total_bytes - free_bytes) / total_bytes) * 100,
                "log_file_sizes": log_sizes
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"System resource check failed: {str(e)}"
            }
    
    def check_environment_config(self) -> Dict[str, Any]:
        """Check environment configuration."""
        try:
            required_vars = ["LETTA_API_KEY", "LETTA_BASE_URL"]
            optional_vars = ["PROMPTYOSELF_DB", "MONITOR_LOG_LEVEL"]
            
            config_status = {}
            
            for var in required_vars:
                value = os.getenv(var)
                config_status[var] = {
                    "set": value is not None,
                    "value": value if value else None
                }
            
            for var in optional_vars:
                value = os.getenv(var)
                config_status[var] = {
                    "set": value is not None,
                    "value": value if value else None
                }
            
            # Check if all required vars are set
            all_required_set = all(config_status[var]["set"] for var in required_vars)
            
            return {
                "status": "healthy" if all_required_set else "warning",
                "all_required_set": all_required_set,
                "configuration": config_status
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Environment config check failed: {str(e)}"
            }
    
    def get_recent_activity(self) -> Dict[str, Any]:
        """Get recent system activity summary."""
        try:
            session = get_session()
            try:
                # Get schedules that ran in last 24 hours
                recent_cutoff = datetime.utcnow() - timedelta(hours=24)
                recent_runs = session.query(PromptSchedule).filter(
                    PromptSchedule.last_run >= recent_cutoff
                ).order_by(PromptSchedule.last_run.desc()).all()
                
                # Get upcoming schedules in next 24 hours
                upcoming_cutoff = datetime.utcnow() + timedelta(hours=24)
                upcoming_runs = session.query(PromptSchedule).filter(
                    PromptSchedule.active == True,
                    PromptSchedule.next_run <= upcoming_cutoff
                ).order_by(PromptSchedule.next_run).all()
                
                recent_activity = []
                for schedule in recent_runs:
                    recent_activity.append({
                        "id": schedule.id,
                        "agent_id": schedule.agent_id,
                        "prompt_text": schedule.prompt_text[:100] + "..." if len(schedule.prompt_text) > 100 else schedule.prompt_text,
                        "last_run": schedule.last_run.isoformat(),
                        "schedule_type": schedule.schedule_type
                    })
                
                upcoming_activity = []
                for schedule in upcoming_runs:
                    upcoming_activity.append({
                        "id": schedule.id,
                        "agent_id": schedule.agent_id,
                        "prompt_text": schedule.prompt_text[:100] + "..." if len(schedule.prompt_text) > 100 else schedule.prompt_text,
                        "next_run": schedule.next_run.isoformat(),
                        "schedule_type": schedule.schedule_type
                    })
                
                return {
                    "status": "success",
                    "recent_executions": recent_activity,
                    "upcoming_executions": upcoming_activity,
                    "recent_count": len(recent_activity),
                    "upcoming_count": len(upcoming_activity)
                }
                
            finally:
                session.close()
                
        except Exception as e:
            return {
                "status": "error",
                "message": f"Recent activity check failed: {str(e)}"
            }
    
    def run_full_health_check(self) -> Dict[str, Any]:
        """Run comprehensive health check."""
        self.logger.info("Starting comprehensive health check...")
        
        health_report = {
            "timestamp": datetime.utcnow().isoformat(),
            "checks": {
                "database": self.check_database_health(),
                "letta_connectivity": self.check_letta_connectivity(),
                "scheduler": self.check_scheduler_status(),
                "system_resources": self.check_system_resources(),
                "environment": self.check_environment_config(),
                "recent_activity": self.get_recent_activity()
            }
        }
        
        # Determine overall health status
        error_count = sum(1 for check in health_report["checks"].values() 
                         if check.get("status") == "error")
        warning_count = sum(1 for check in health_report["checks"].values() 
                           if check.get("status") in ["warning", "unhealthy"])
        
        if error_count > 0:
            overall_status = "critical"
        elif warning_count > 0:
            overall_status = "warning"
        else:
            overall_status = "healthy"
        
        health_report["overall_status"] = overall_status
        health_report["summary"] = {
            "total_checks": len(health_report["checks"]),
            "errors": error_count,
            "warnings": warning_count,
            "healthy": len(health_report["checks"]) - error_count - warning_count
        }
        
        self.logger.info(f"Health check completed. Overall status: {overall_status}")
        return health_report
    
    def run_continuous_monitoring(self, interval_seconds: int = 300):
        """Run continuous monitoring loop."""
        self.logger.info(f"Starting continuous monitoring with {interval_seconds}s interval...")
        
        try:
            while True:
                health_report = self.run_full_health_check()
                
                # Log summary
                summary = health_report["summary"]
                self.logger.info(f"Health check: {summary['healthy']} healthy, "
                               f"{summary['warnings']} warnings, {summary['errors']} errors")
                
                # Alert on critical issues
                if health_report["overall_status"] == "critical":
                    self.logger.error("CRITICAL: System health check failed!")
                    for check_name, check_result in health_report["checks"].items():
                        if check_result.get("status") == "error":
                            self.logger.error(f"  {check_name}: {check_result.get('message', 'Unknown error')}")
                
                # Sleep until next check
                time.sleep(interval_seconds)
                
        except KeyboardInterrupt:
            self.logger.info("Monitoring interrupted by user")
        except Exception as e:
            self.logger.error(f"Monitoring loop failed: {e}")


def main():
    """Main entry point for the monitoring script."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Promptyoself monitoring script")
    parser.add_argument("--mode", choices=["check", "monitor"], default="check",
                       help="Run single health check or continuous monitoring")
    parser.add_argument("--interval", type=int, default=300,
                       help="Monitoring interval in seconds (default: 300)")
    parser.add_argument("--format", choices=["json", "text"], default="text",
                       help="Output format")
    parser.add_argument("--component", choices=["database", "letta", "scheduler", "system", "environment", "activity"],
                       help="Check specific component only")
    
    args = parser.parse_args()
    
    monitor = PromptyoselfMonitor()
    
    if args.mode == "check":
        if args.component:
            # Run specific component check
            check_methods = {
                "database": monitor.check_database_health,
                "letta": monitor.check_letta_connectivity,
                "scheduler": monitor.check_scheduler_status,
                "system": monitor.check_system_resources,
                "environment": monitor.check_environment_config,
                "activity": monitor.get_recent_activity
            }
            
            result = check_methods[args.component]()
        else:
            # Run full health check
            result = monitor.run_full_health_check()
        
        if args.format == "json":
            print(json.dumps(result, indent=2))
        else:
            # Text format
            print(f"Promptyoself Health Check - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print("=" * 60)
            
            if args.component:
                print(f"{args.component.title()} Status: {result.get('status', 'unknown')}")
                if result.get('message'):
                    print(f"Message: {result['message']}")
            else:
                print(f"Overall Status: {result['overall_status'].upper()}")
                print(f"Summary: {result['summary']['healthy']} healthy, "
                      f"{result['summary']['warnings']} warnings, {result['summary']['errors']} errors")
                
                for check_name, check_result in result["checks"].items():
                    status = check_result.get("status", "unknown")
                    print(f"  {check_name}: {status}")
                    if check_result.get("message"):
                        print(f"    {check_result['message']}")
    
    elif args.mode == "monitor":
        monitor.run_continuous_monitoring(args.interval)


if __name__ == "__main__":
    main()