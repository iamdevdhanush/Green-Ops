"""
macOS Power Management
"""

import subprocess

def sleep_macos():
    """
    Put macOS system to sleep
    Uses pmset sleepnow command
    """
    try:
        subprocess.run(['pmset', 'sleepnow'], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Failed to sleep macOS system: {e}")
        raise
    except FileNotFoundError:
        print("pmset command not found. Make sure you're running on macOS.")
        raise
