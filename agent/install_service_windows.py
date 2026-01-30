"""
GreenOps Agent Windows Service Installer
Installs the agent as a Windows service
"""

import sys
import os
import win32serviceutil
import win32service
import win32event
import servicemanager
import socket
import time
import logging

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agent import GreenOpsAgent

class GreenOpsService(win32serviceutil.ServiceFramework):
    """Windows Service for GreenOps Agent"""
    
    _svc_name_ = "GreenOpsAgent"
    _svc_display_name_ = "GreenOps Carbon Governance Agent"
    _svc_description_ = "Monitors system idle time and manages power settings to reduce carbon emissions"
    
    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.stop_event = win32event.CreateEvent(None, 0, 0, None)
        self.is_running = False
        
        # Setup logging
        logging.basicConfig(
            filename='greenops_service.log',
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
    
    def SvcStop(self):
        """Stop the service"""
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.stop_event)
        self.is_running = False
        logging.info("Service stop requested")
    
    def SvcDoRun(self):
        """Run the service"""
        self.is_running = True
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, '')
        )
        logging.info("Service started")
        self.main()
    
    def main(self):
        """Main service loop"""
        try:
            agent = GreenOpsAgent()
            
            while self.is_running:
                # Check if stop event is set
                if win32event.WaitForSingleObject(self.stop_event, 0) == win32event.WAIT_OBJECT_0:
                    break
                
                # Run monitoring cycle
                agent.run_cycle()
                
                # Wait for next cycle or stop event
                win32event.WaitForSingleObject(self.stop_event, agent.stats.stats.get('check_interval', 60) * 1000)
            
            logging.info("Service stopped")
        except Exception as e:
            logging.error(f"Service error: {e}", exc_info=True)

def install_service():
    """Install the Windows service"""
    try:
        win32serviceutil.InstallService(
            pythonClassString=f"{__name__}.GreenOpsService",
            serviceName=GreenOpsService._svc_name_,
            displayName=GreenOpsService._svc_display_name_,
            description=GreenOpsService._svc_description_,
            startType=win32service.SERVICE_AUTO_START
        )
        print(f"✅ Service '{GreenOpsService._svc_display_name_}' installed successfully")
        print(f"   To start: net start {GreenOpsService._svc_name_}")
    except Exception as e:
        print(f"❌ Failed to install service: {e}")

def uninstall_service():
    """Uninstall the Windows service"""
    try:
        win32serviceutil.RemoveService(GreenOpsService._svc_name_)
        print(f"✅ Service '{GreenOpsService._svc_display_name_}' uninstalled successfully")
    except Exception as e:
        print(f"❌ Failed to uninstall service: {e}")

def start_service():
    """Start the Windows service"""
    try:
        win32serviceutil.StartService(GreenOpsService._svc_name_)
        print(f"✅ Service '{GreenOpsService._svc_display_name_}' started")
    except Exception as e:
        print(f"❌ Failed to start service: {e}")

def stop_service():
    """Stop the Windows service"""
    try:
        win32serviceutil.StopService(GreenOpsService._svc_name_)
        print(f"✅ Service '{GreenOpsService._svc_display_name_}' stopped")
    except Exception as e:
        print(f"❌ Failed to stop service: {e}")

if __name__ == '__main__':
    if len(sys.argv) == 1:
        # Run as service
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(GreenOpsService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        # Handle command line arguments
        if sys.argv[1] == 'install':
            install_service()
        elif sys.argv[1] == 'uninstall' or sys.argv[1] == 'remove':
            uninstall_service()
        elif sys.argv[1] == 'start':
            start_service()
        elif sys.argv[1] == 'stop':
            stop_service()
        elif sys.argv[1] == 'restart':
            stop_service()
            time.sleep(2)
            start_service()
        else:
            print("""
GreenOps Agent Windows Service Installer

Usage:
    python install_service_windows.py install     - Install service
    python install_service_windows.py uninstall   - Uninstall service
    python install_service_windows.py start       - Start service
    python install_service_windows.py stop        - Stop service
    python install_service_windows.py restart     - Restart service

After installation, the service will start automatically on boot.
            """)
