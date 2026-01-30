"""
Windows Power Management - Enhanced
Supports sleep and hibernate operations
"""

import subprocess
import ctypes

def sleep_windows():
    """
    Put Windows system to sleep (suspend to RAM)
    """
    try:
        # Method 1: Using rundll32 with powrprof.dll
        subprocess.run(
            ['rundll32.exe', 'powrprof.dll,SetSuspendState', '0,1,0'],
            shell=True,
            check=True
        )
    except subprocess.CalledProcessError:
        try:
            # Method 2: Using ctypes to call Windows API directly
            ctypes.windll.powrprof.SetSuspendState(False, True, False)
        except Exception as e:
            print(f"Failed to sleep Windows system: {e}")
            raise

def hibernate_windows():
    """
    Hibernate Windows system (suspend to disk)
    """
    try:
        # Method 1: Using rundll32 with powrprof.dll
        # First parameter: 1 = hibernate, 0 = sleep
        subprocess.run(
            ['rundll32.exe', 'powrprof.dll,SetSuspendState', '1,1,0'],
            shell=True,
            check=True
        )
    except subprocess.CalledProcessError:
        try:
            # Method 2: Using ctypes to call Windows API directly
            # SetSuspendState(Hibernate, ForceCritical, DisableWakeEvent)
            ctypes.windll.powrprof.SetSuspendState(True, True, False)
        except Exception as e:
            print(f"Failed to hibernate Windows system: {e}")
            raise

def shutdown_windows(force=False):
    """
    Shutdown Windows system
    Note: GreenOps doesn't use shutdown by default for safety
    """
    try:
        if force:
            subprocess.run(['shutdown', '/s', '/f', '/t', '0'], check=True)
        else:
            subprocess.run(['shutdown', '/s', '/t', '0'], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Failed to shutdown Windows system: {e}")
        raise

def check_hibernate_enabled():
    """
    Check if hibernate is enabled on Windows
    """
    try:
        result = subprocess.run(
            ['powercfg', '/a'],
            capture_output=True,
            text=True,
            check=True
        )
        return 'hibernate' in result.stdout.lower()
    except:
        return False

def enable_hibernate():
    """
    Enable hibernate on Windows (requires admin privileges)
    """
    try:
        subprocess.run(['powercfg', '/hibernate', 'on'], check=True)
        return True
    except subprocess.CalledProcessError:
        print("Failed to enable hibernate. Please run as administrator.")
        return False

def get_power_scheme():
    """
    Get current Windows power scheme
    """
    try:
        result = subprocess.run(
            ['powercfg', '/getactivescheme'],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except:
        return "Unknown"
