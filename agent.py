#!/usr/bin/env python3
"""
GreenOps Agent - Production-Ready Client Monitoring Agent
Reliable communication with exponential backoff, retry logic, and comprehensive error handling
"""

import platform
import socket
import time
import sys
import os
import logging
import json
from datetime import datetime
from typing import Optional, Tuple, Dict, Any

try:
    import requests
    from requests.adapters import HTTPAdapter
    from requests.packages.urllib3.util.retry import Retry
    import psutil
except ImportError:
    print("Error: Required packages not installed")
    print("Please install: pip install requests psutil")
    sys.exit(1)


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('greenops_agent.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('GreenOpsAgent')


class GreenOpsAgent:
    """Production-ready GreenOps monitoring agent with robust error handling"""
    
    # Retry configuration
    MAX_RETRIES = 3
    BACKOFF_FACTOR = 2  # 1s, 2s, 4s
    TIMEOUT = 10  # seconds
    
    # Connection pool
    POOL_CONNECTIONS = 10
    POOL_MAXSIZE = 10
    
    def __init__(self, server_url: str, org='PES', department='BCA', lab='LAB1'):
        """
        Initialize agent with robust HTTP session
        
        Args:
            server_url: GreenOps server URL (e.g., http://localhost:5000)
            org: Organization code
            department: Department code
            lab: Lab name
        """
        self.server_url = server_url.rstrip('/')
        self.org = org
        self.department = department
        self.lab = lab
        
        # System identification
        self.mac_address = self._get_mac_address()
        self.pc_id = self._generate_pc_id()
        self.hostname = socket.gethostname()
        self.os = self._get_os_info()
        
        # State tracking
        self.last_successful_contact = time.time()
        self.consecutive_failures = 0
        self.registered = False
        
        # HTTP session with retry logic
        self.session = self._create_session()
        
        logger.info(f"Agent initialized: {self.pc_id} ({self.mac_address})")
    
    def _create_session(self) -> requests.Session:
        """Create HTTP session with connection pooling and retry logic"""
        session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=self.MAX_RETRIES,
            backoff_factor=self.BACKOFF_FACTOR,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "POST", "PUT", "DELETE", "OPTIONS", "TRACE"]
        )
        
        # Mount adapter with retry strategy
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=self.POOL_CONNECTIONS,
            pool_maxsize=self.POOL_MAXSIZE
        )
        
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # Set default timeout and headers
        session.headers.update({
            'User-Agent': f'GreenOps-Agent/1.0 ({self.hostname})',
            'Content-Type': 'application/json'
        })
        
        return session
    
    def _get_mac_address(self) -> str:
        """Get primary MAC address with fallback logic"""
        try:
            interfaces = psutil.net_if_addrs()
            
            # First pass: non-loopback interfaces
            for interface_name, addresses in interfaces.items():
                if 'lo' in interface_name.lower() or 'loopback' in interface_name.lower():
                    continue
                
                for addr in addresses:
                    if addr.family == psutil.AF_LINK:
                        mac = addr.address.replace('-', ':').upper()
                        if mac != '00:00:00:00:00:00' and mac:
                            logger.info(f"Found MAC address: {mac} on {interface_name}")
                            return mac
            
            # Second pass: any valid MAC
            for interface_name, addresses in interfaces.items():
                for addr in addresses:
                    if addr.family == psutil.AF_LINK:
                        mac = addr.address.replace('-', ':').upper()
                        if mac != '00:00:00:00:00:00' and mac:
                            logger.warning(f"Using fallback MAC: {mac}")
                            return mac
            
            raise Exception("No valid MAC address found")
            
        except Exception as e:
            logger.error(f"Failed to get MAC address: {e}")
            sys.exit(1)
    
    def _generate_pc_id(self) -> str:
        """Generate unique PC ID from MAC address"""
        mac_suffix = self.mac_address.replace(':', '')[-4:].upper()
        return f"{self.org}-{self.department}-{self.lab}-{mac_suffix}"
    
    def _get_os_info(self) -> str:
        """Get operating system information"""
        try:
            system = platform.system()
            release = platform.release()
            return f"{system} {release}"
        except Exception as e:
            logger.warning(f"Could not determine OS: {e}")
            return "Unknown"
    
    def _get_idle_seconds(self) -> int:
        """
        Get REAL system idle time in seconds
        Platform-specific implementations
        """
        system = platform.system()
        
        try:
            if system == 'Windows':
                return self._get_idle_seconds_windows()
            elif system == 'Linux':
                return self._get_idle_seconds_linux()
            elif system == 'Darwin':
                return self._get_idle_seconds_macos()
            else:
                logger.warning(f"Idle detection not implemented for {system}")
                return 0
                
        except Exception as e:
            logger.error(f"Error getting idle time: {e}")
            return 0
    
    def _get_idle_seconds_windows(self) -> int:
        """Get idle time on Windows using ctypes"""
        try:
            import ctypes
            
            class LASTINPUTINFO(ctypes.Structure):
                _fields_ = [
                    ('cbSize', ctypes.c_uint),
                    ('dwTime', ctypes.c_uint)
                ]
            
            lastInputInfo = LASTINPUTINFO()
            lastInputInfo.cbSize = ctypes.sizeof(lastInputInfo)
            
            ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lastInputInfo))
            
            millis = ctypes.windll.kernel32.GetTickCount() - lastInputInfo.dwTime
            return millis // 1000
            
        except Exception as e:
            logger.error(f"Windows idle detection failed: {e}")
            return 0
    
    def _get_idle_seconds_linux(self) -> int:
        """Get idle time on Linux using X11"""
        try:
            import subprocess
            
            # Try xprintidle first
            result = subprocess.run(
                ['xprintidle'],
                capture_output=True,
                text=True,
                timeout=2
            )
            
            if result.returncode == 0:
                millis = int(result.stdout.strip())
                return millis // 1000
            
            # Fallback: check DISPLAY variable and use xdotool
            result = subprocess.run(
                ['xdotool', 'getactivewindow', 'getwindowpid'],
                capture_output=True,
                timeout=2
            )
            
            # If no X11, return 0 (headless server)
            return 0
            
        except FileNotFoundError:
            logger.warning("xprintidle not found - install with: apt install xprintidle")
            return 0
        except Exception as e:
            logger.error(f"Linux idle detection failed: {e}")
            return 0
    
    def _get_idle_seconds_macos(self) -> int:
        """Get idle time on macOS"""
        try:
            import subprocess
            
            result = subprocess.run(
                ['ioreg', '-c', 'IOHIDSystem'],
                capture_output=True,
                text=True,
                timeout=2
            )
            
            for line in result.stdout.split('\n'):
                if 'HIDIdleTime' in line:
                    nanoseconds = int(line.split('=')[1].strip())
                    return nanoseconds // 1_000_000_000
            
            return 0
            
        except Exception as e:
            logger.error(f"macOS idle detection failed: {e}")
            return 0
    
    def _get_system_metrics(self) -> Dict[str, Optional[float]]:
        """Get system resource metrics with error handling"""
        try:
            return {
                'cpu_usage': round(psutil.cpu_percent(interval=1), 2),
                'memory_usage': round(psutil.virtual_memory().percent, 2),
                'disk_usage': round(psutil.disk_usage('/').percent, 2)
            }
        except Exception as e:
            logger.error(f"Failed to get system metrics: {e}")
            return {
                'cpu_usage': None,
                'memory_usage': None,
                'disk_usage': None
            }
    
    def _make_request(self, endpoint: str, data: Dict[str, Any]) -> Tuple[bool, Optional[Dict]]:
        """
        Make HTTP request with timeout and error handling
        
        Returns:
            (success: bool, response_data: dict or None)
        """
        url = f"{self.server_url}{endpoint}"
        
        try:
            response = self.session.post(
                url,
                json=data,
                timeout=self.TIMEOUT
            )
            
            response.raise_for_status()
            
            # Reset failure counter on success
            self.consecutive_failures = 0
            self.last_successful_contact = time.time()
            
            return True, response.json()
            
        except requests.exceptions.Timeout:
            self.consecutive_failures += 1
            logger.error(f"Request timeout to {endpoint}")
            return False, None
            
        except requests.exceptions.ConnectionError:
            self.consecutive_failures += 1
            logger.error(f"Connection failed to {endpoint}")
            return False, None
            
        except requests.exceptions.HTTPError as e:
            self.consecutive_failures += 1
            logger.error(f"HTTP error {e.response.status_code}: {e.response.text}")
            return False, None
            
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON response from {endpoint}")
            return False, None
            
        except Exception as e:
            self.consecutive_failures += 1
            logger.error(f"Unexpected error: {e}", exc_info=True)
            return False, None
    
    def register(self) -> bool:
        """Register machine with server"""
        logger.info("Attempting registration...")
        
        data = {
            'mac_address': self.mac_address,
            'pc_id': self.pc_id,
            'department': self.department,
            'lab': self.lab,
            'hostname': self.hostname,
            'os': self.os,
            'idle_seconds': self._get_idle_seconds()
        }
        
        success, response = self._make_request('/api/agent/register', data)
        
        if success:
            self.registered = True
            logger.info(f"✓ Registered successfully as {self.pc_id}")
            return True
        else:
            logger.error("✗ Registration failed")
            return False
    
    def send_heartbeat(self) -> Tuple[bool, Optional[str]]:
        """
        Send heartbeat with idle time and metrics
        Combined endpoint for efficiency
        
        Returns:
            (success: bool, status: str or None)
        """
        if not self.registered:
            logger.warning("Not registered - attempting registration")
            if not self.register():
                return False, None
        
        idle_seconds = self._get_idle_seconds()
        metrics = self._get_system_metrics()
        
        data = {
            'mac_address': self.mac_address,
            'idle_seconds': idle_seconds,
            'cpu_usage': metrics.get('cpu_usage'),
            'memory_usage': metrics.get('memory_usage'),
            'disk_usage': metrics.get('disk_usage')
        }
        
        success, response = self._make_request('/api/agent/heartbeat', data)
        
        if success and response:
            status = response.get('status', 'UNKNOWN')
            return True, status
        else:
            return False, None
    
    def check_commands(self) -> bool:
        """Check for and execute pending power commands"""
        if not self.registered:
            return False
        
        data = {'mac_address': self.mac_address}
        
        success, response = self._make_request('/api/agent/commands', data)
        
        if not success or not response:
            return False
        
        commands = response.get('commands', [])
        
        for cmd in commands:
            command_id = cmd.get('id')
            command_type = cmd.get('command')
            
            logger.info(f"📨 Received {command_type} command (ID: {command_id})")
            
            # Execute command
            exec_success, error = self._execute_power_command(command_type)
            
            # Report execution status
            self._report_command_execution(command_id, exec_success, error)
            
            if exec_success:
                logger.info(f"✓ Command {command_type} executed successfully")
                
                # If sleep/shutdown, system will go down - exit gracefully
                if command_type in ['SLEEP', 'SHUTDOWN', 'RESTART']:
                    logger.info("System powering down - agent exiting")
                    self.cleanup()
                    sys.exit(0)
            else:
                logger.error(f"✗ Command {command_type} failed: {error}")
        
        return True
    
    def _execute_power_command(self, command: str) -> Tuple[bool, Optional[str]]:
        """
        Execute power management command
        
        Returns:
            (success: bool, error_message: str or None)
        """
        system = platform.system()
        
        try:
            logger.info(f"⚡ Executing {command} command on {system}")
            
            if command == 'SLEEP':
                if system == 'Windows':
                    os.system('rundll32.exe powrprof.dll,SetSuspendState 0,1,0')
                elif system == 'Linux':
                    os.system('systemctl suspend')
                elif system == 'Darwin':
                    os.system('pmset sleepnow')
                return True, None
                
            elif command == 'SHUTDOWN':
                if system == 'Windows':
                    os.system('shutdown /s /t 60')  # 60 second delay
                elif system == 'Linux':
                    os.system('shutdown -h +1')  # 1 minute delay
                elif system == 'Darwin':
                    os.system('shutdown -h +1')
                return True, None
                
            elif command == 'RESTART':
                if system == 'Windows':
                    os.system('shutdown /r /t 60')
                elif system == 'Linux':
                    os.system('shutdown -r +1')
                elif system == 'Darwin':
                    os.system('shutdown -r +1')
                return True, None
                
            elif command == 'LOCK':
                if system == 'Windows':
                    os.system('rundll32.exe user32.dll,LockWorkStation')
                elif system == 'Linux':
                    os.system('xdg-screensaver lock')
                elif system == 'Darwin':
                    os.system('/System/Library/CoreServices/Menu\\ Extras/User.menu/Contents/Resources/CGSession -suspend')
                return True, None
                
            else:
                return False, f"Unknown command: {command}"
                
        except Exception as e:
            logger.error(f"Command execution failed: {e}", exc_info=True)
            return False, str(e)
    
    def _report_command_execution(self, command_id: int, success: bool, error: Optional[str]) -> None:
        """Report command execution status to server"""
        data = {
            'command_id': command_id,
            'status': 'EXECUTED' if success else 'FAILED',
            'result_message': error
        }
        
        self._make_request('/api/agent/command-status', data)
    
    def cleanup(self) -> None:
        """Clean up resources before exit"""
        logger.info("Cleaning up agent resources...")
        try:
            self.session.close()
        except:
            pass
    
    def run(self, interval: int = 60) -> None:
        """
        Run agent continuously with error recovery
        
        Args:
            interval: Update interval in seconds (default: 60)
        """
        print("\n" + "="*70)
        print("GreenOps Agent - Production Ready")
        print("="*70)
        print(f"PC ID: {self.pc_id}")
        print(f"MAC Address: {self.mac_address}")
        print(f"Hostname: {self.hostname}")
        print(f"Server: {self.server_url}")
        print(f"Update Interval: {interval} seconds")
        print(f"Log File: greenops_agent.log")
        print("="*70 + "\n")
        
        # Initial registration with retry
        max_registration_attempts = 5
        for attempt in range(1, max_registration_attempts + 1):
            logger.info(f"Registration attempt {attempt}/{max_registration_attempts}")
            
            if self.register():
                break
            
            if attempt < max_registration_attempts:
                wait_time = min(30 * attempt, 300)  # Max 5 minutes
                logger.warning(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
        
        if not self.registered:
            logger.error("Failed to register after multiple attempts - exiting")
            sys.exit(1)
        
        logger.info("Monitoring started - Press Ctrl+C to stop")
        
        cycle = 0
        
        try:
            while True:
                cycle += 1
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # Check for commands first (most important)
                self.check_commands()
                
                # Send heartbeat with metrics
                success, status = self.send_heartbeat()
                
                if success:
                    logger.info(f"[{timestamp}] Cycle {cycle}: Status={status}")
                    print(f"[{timestamp}] ✓ Status: {status}")
                else:
                    logger.warning(f"[{timestamp}] Cycle {cycle}: Communication failed (attempt {self.consecutive_failures})")
                    print(f"[{timestamp}] ✗ Communication error - retrying...")
                    
                    # If too many failures, try re-registration
                    if self.consecutive_failures >= 5:
                        logger.warning("Too many failures - attempting re-registration")
                        self.registered = False
                        self.register()
                
                # Calculate next interval with backoff on failures
                if self.consecutive_failures > 0:
                    sleep_time = min(interval * (1.5 ** self.consecutive_failures), 300)
                    logger.info(f"Using backoff interval: {sleep_time}s")
                else:
                    sleep_time = interval
                
                time.sleep(sleep_time)
                
        except KeyboardInterrupt:
            logger.info("\nAgent stopped by user")
            print("\n\n✓ Agent stopped gracefully")
            self.cleanup()
            sys.exit(0)
        
        except Exception as e:
            logger.critical(f"Fatal error: {e}", exc_info=True)
            self.cleanup()
            sys.exit(1)


def main():
    """Main entry point with argument parsing"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='GreenOps Monitoring Agent - Production Ready',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '--server',
        required=True,
        help='GreenOps server URL (e.g., http://192.168.1.100:5000)'
    )
    parser.add_argument(
        '--org',
        default='PES',
        help='Organization code (default: PES)'
    )
    parser.add_argument(
        '--department',
        default='BCA',
        help='Department code (default: BCA)'
    )
    parser.add_argument(
        '--lab',
        default='LAB1',
        help='Lab name (default: LAB1)'
    )
    parser.add_argument(
        '--interval',
        type=int,
        default=60,
        help='Update interval in seconds (default: 60)'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging'
    )
    
    args = parser.parse_args()
    
    # Set log level
    if args.debug:
        logging.getLogger('GreenOpsAgent').setLevel(logging.DEBUG)
        logger.debug("Debug logging enabled")
    
    # Validate interval
    if args.interval < 10:
        logger.error("Interval must be at least 10 seconds")
        sys.exit(1)
    
    # Create and run agent
    agent = GreenOpsAgent(
        server_url=args.server,
        org=args.org,
        department=args.department,
        lab=args.lab
    )
    
    agent.run(interval=args.interval)


if __name__ == '__main__':
    main()
