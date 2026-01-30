"""
macOS Idle Time Detection
"""

import subprocess

def get_idle_minutes_macos():
    """
    Get system idle time in minutes on macOS
    Uses IOHIDIdleTime from ioreg
    """
    try:
        # Get idle time in nanoseconds
        cmd = 'ioreg -c IOHIDSystem | awk \'/HIDIdleTime/ {print $NF/1000000000; exit}\''
        output = subprocess.check_output(cmd, shell=True).decode().strip()
        
        idle_seconds = float(output)
        idle_minutes = idle_seconds / 60
        
        return idle_minutes
    except Exception as e:
        print(f"Error getting idle time on macOS: {e}")
        return 0
