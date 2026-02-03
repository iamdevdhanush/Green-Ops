#!/usr/bin/env python3
"""
GreenOps Agent - Client-side monitoring agent with power management
Runs on client PCs to monitor, report metrics, and execute power commands
"""

import platform
import socket
import time
import sys
import os
from datetime import datetime

try:
    import requests
    import psutil
except ImportError:
    print("Error: Required packages not installed")
    print("Please install: pip install requests psutil")
    sys.exit(1)


class GreenOpsAgent:
    """GreenOps monitoring agent with power management"""
    
    def __init__(self, server_url, org='PES', department='BCA', lab='LAB1'):
        """
        Initialize agent
        
        Args:
            server_url: GreenOps server URL (e.g., http://localhost:5000)
            org: Organization code (default: PES)
            department: Department code (default: BCA)
            lab: Lab name (default: LAB1)
        """
        self.server_url = server_url.rstrip('/')
        self.org = org
        self.department = department
        self.lab = lab
        self.mac_address = self._get_mac_address()
        self.pc_id = self._generate_pc_id()
        self.hostname = socket.gethostname()
        self.os = self._get_os_info()
        self.last_activity = time.time()
        
    def _get_mac_address(self):
        """Get primary MAC address of the machine"""
        try:
            interfaces = psutil.net_if_addrs()
            
            for interface_name, addresses in interfaces.items():
                if 'lo' in interface_name.lower() or 'loopback' in interface_name.lower():
                    continue
                    
                for addr in addresses:
                    if addr.family == psutil.AF_LINK:
                        mac = addr.address.replace('-', ':').upper()
                        if mac != '00:00:00:00:00:00':
                            return mac
            
            for interface_name, addresses in interfaces.items():
                for addr in addresses:
                    if addr.family == psutil.AF_LINK:
                        mac = addr.address.replace('-', ':').upper()
                        if mac != '00:00:00:00:00:00':
                            return mac
            
            raise Exception("No valid MAC address found")
            
        except Exception as e:
            print(f"Error getting MAC address: {e}")
            sys.exit(1)
    
    def _generate_pc_id(self):
        """Generate PC ID from MAC address"""
        mac_suffix = self.mac_address.replace(':', '')[-4:].upper()
        return f"{self.org}-{self.department}-{self.lab}-{mac_suffix}"
    
    def _get_os_info(self):
        """Get operating system information"""
        try:
            system = platform.system()
            release = platform.release()
            return f"{system} {release}"
        except:
            return "Unknown"
    
    def _get_idle_time(self):
        """Get system idle time in minutes"""
        try:
            current_time = time.time()
            boot_time = psutil.boot_time()
            idle_seconds = current_time - self.last_activity
            return int(idle_seconds / 60)
        except:
            return 0
    
    def _get_system_metrics(self):
        """Get system resource metrics"""
        try:
            return {
                'cpu_usage': psutil.cpu_percent(interval=1),
                'memory_usage': psutil.virtual_memory().percent,
                'disk_usage': psutil.disk_usage('/').percent
            }
        except:
            return {
                'cpu_usage': None,
                'memory_usage': None,
                'disk_usage': None
            }
    
    def _execute_power_command(self, command):
        """Execute power management command"""
        system = platform.system()
        
        try:
            if command == 'SLEEP':
                print(f"⚡ Executing SLEEP command...")
                if system == 'Windows':
                    os.system('rundll32.exe powrprof.dll,SetSuspendState 0,1,0')
                elif system == 'Linux':
                    os.system('systemctl suspend')
                elif system == 'Darwin':  # macOS
                    os.system('pmset sleepnow')
                return True, None
                
            elif command == 'SHUTDOWN':
                print(f"⚡ Executing SHUTDOWN command...")
                if system == 'Windows':
                    os.system('shutdown /s /t 0')
                elif system == 'Linux':
                    os.system('shutdown -h now')
                elif system == 'Darwin':
                    os.system('shutdown -h now')
                return True, None
                
            elif command == 'RESTART':
                print(f"⚡ Executing RESTART command...")
                if system == 'Windows':
                    os.system('shutdown /r /t 0')
                elif system == 'Linux':
                    os.system('shutdown -r now')
                elif system == 'Darwin':
                    os.system('shutdown -r now')
                return True, None
                
            else:
                return False, f"Unknown command: {command}"
                
        except Exception as e:
            return False, str(e)
    
    def check_commands(self):
        """Check for pending power commands from server"""
        try:
            url = f"{self.server_url}/api/agent/commands"
            data = {'mac_address': self.mac_address}
            
            response = requests.post(url, json=data, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                commands = result.get('commands', [])
                
                for cmd in commands:
                    command_id = cmd.get('id')
                    command_type = cmd.get('command')
                    
                    print(f"\n📨 Received {command_type} command (ID: {command_id})")
                    
                    # Execute command
                    success, error = self._execute_power_command(command_type)
                    
                    # Report execution status
                    self.report_command_execution(command_id, success, error)
                    
                    if success:
                        print(f"✓ Command executed successfully")
                        # If sleep/shutdown, the system will go down
                        # so no point continuing the loop
                        if command_type in ['SLEEP', 'SHUTDOWN']:
                            sys.exit(0)
                    else:
                        print(f"✗ Command failed: {error}")
                
                return True
            else:
                return False
                
        except Exception as e:
            # Silently fail - this is called every cycle
            return False
    
    def report_command_execution(self, command_id, success, error):
        """Report command execution status to server"""
        try:
            url = f"{self.server_url}/api/agent/command-status"
            data = {
                'command_id': command_id,
                'status': 'EXECUTED' if success else 'FAILED',
                'error_message': error
            }
            
            requests.post(url, json=data, timeout=5)
            
        except:
            pass  # Silently fail
    
    def register(self):
        """Register machine with server"""
        try:
            url = f"{self.server_url}/api/agent/register"
            data = {
                'mac_address': self.mac_address,
                'pc_id': self.pc_id,
                'department': self.department,
                'lab': self.lab,
                'hostname': self.hostname,
                'os': self.os
            }
            
            response = requests.post(url, json=data, timeout=10)
            
            if response.status_code == 200:
                print(f"✓ Registered successfully as {self.pc_id}")
                print(f"  MAC: {self.mac_address}")
                print(f"  Hostname: {self.hostname}")
                return True
            else:
                print(f"✗ Registration failed: {response.text}")
                return False
                
        except Exception as e:
            print(f"✗ Registration error: {e}")
            return False
    
    def send_heartbeat(self):
        """Send heartbeat to server"""
        try:
            url = f"{self.server_url}/api/agent/heartbeat"
            idle_time = self._get_idle_time()
            
            data = {
                'mac_address': self.mac_address,
                'idle_time_minutes': idle_time
            }
            
            response = requests.post(url, json=data, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                status = result.get('status', 'UNKNOWN')
                return True, status
            else:
                return False, None
                
        except Exception as e:
            return False, None
    
    def send_metrics(self):
        """Send system metrics to server"""
        try:
            url = f"{self.server_url}/api/agent/metrics"
            
            metrics = self._get_system_metrics()
            idle_time = self._get_idle_time()
            
            data = {
                'mac_address': self.mac_address,
                'idle_time_minutes': idle_time,
                'cpu_usage': metrics['cpu_usage'],
                'memory_usage': metrics['memory_usage'],
                'disk_usage': metrics['disk_usage']
            }
            
            response = requests.post(url, json=data, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                energy_waste = result.get('energy_waste_kwh', 0)
                return True, energy_waste
            else:
                return False, 0
                
        except Exception as e:
            return False, 0
    
    def run(self, interval=60):
        """
        Run agent continuously
        
        Args:
            interval: Update interval in seconds (default: 60)
        """
        print("\n" + "="*60)
        print("GreenOps Agent Started (with Power Management)")
        print("="*60)
        print(f"PC ID: {self.pc_id}")
        print(f"MAC Address: {self.mac_address}")
        print(f"Server: {self.server_url}")
        print(f"Update Interval: {interval} seconds")
        print("="*60 + "\n")
        
        # Initial registration
        if not self.register():
            print("Failed to register. Retrying in 30 seconds...")
            time.sleep(30)
            if not self.register():
                print("Registration failed. Exiting.")
                sys.exit(1)
        
        print("\n⚡ Power management enabled")
        print("  - Agent will check for sleep/shutdown commands")
        print("  - Commands are issued from admin dashboard")
        print("\nMonitoring started. Press Ctrl+C to stop.\n")
        
        cycle = 0
        try:
            while True:
                cycle += 1
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # Check for power commands first
                self.check_commands()
                
                # Send heartbeat
                heartbeat_ok, status = self.send_heartbeat()
                
                # Send metrics
                metrics_ok, energy_waste = self.send_metrics()
                
                if heartbeat_ok and metrics_ok:
                    print(f"[{timestamp}] Status: {status} | Energy: {energy_waste:.4f} kWh")
                else:
                    print(f"[{timestamp}] Communication error - retrying...")
                
                time.sleep(interval)
                
        except KeyboardInterrupt:
            print("\n\nAgent stopped by user.")
            sys.exit(0)


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='GreenOps Monitoring Agent with Power Management')
    parser.add_argument('--server', required=True, help='GreenOps server URL')
    parser.add_argument('--org', default='PES', help='Organization code')
    parser.add_argument('--department', default='BCA', help='Department code')
    parser.add_argument('--lab', default='LAB1', help='Lab name')
    parser.add_argument('--interval', type=int, default=60, help='Update interval in seconds')
    
    args = parser.parse_args()
    
    agent = GreenOpsAgent(
        server_url=args.server,
        org=args.org,
        department=args.department,
        lab=args.lab
    )
    
    agent.run(interval=args.interval)


if __name__ == '__main__':
    main()
