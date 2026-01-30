"""
Linux Power Management - Enhanced
Supports sleep and hibernate operations
"""

import subprocess
import os

def sleep_linux():
    """
    Put Linux system to sleep (suspend to RAM)
    """
    try:
        # Try systemctl first (systemd)
        subprocess.run(['systemctl', 'suspend'], check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        try:
            # Fallback to pm-suspend
            subprocess.run(['pm-suspend'], check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            # Last resort: write to /sys/power/state (requires root)
            try:
                with open('/sys/power/state', 'w') as f:
                    f.write('mem')
            except PermissionError:
                print("Error: Insufficient permissions to suspend system")
                print("Please run with sudo or configure sudoers")
                raise

def hibernate_linux():
    """
    Hibernate Linux system (suspend to disk)
    """
    try:
        # Try systemctl first (systemd)
        subprocess.run(['systemctl', 'hibernate'], check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        try:
            # Fallback to pm-hibernate
            subprocess.run(['pm-hibernate'], check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            # Last resort: write to /sys/power/state (requires root)
            try:
                with open('/sys/power/state', 'w') as f:
                    f.write('disk')
            except PermissionError:
                print("Error: Insufficient permissions to hibernate system")
                print("Please run with sudo or configure sudoers")
                raise

def check_hibernate_support():
    """
    Check if hibernate is supported on this system
    """
    try:
        with open('/sys/power/state', 'r') as f:
            states = f.read().strip()
            return 'disk' in states
    except:
        return False

def get_power_state():
    """
    Get current power state
    """
    try:
        with open('/sys/power/state', 'r') as f:
            return f.read().strip()
    except:
        return "unknown"
