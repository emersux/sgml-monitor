import platform
import psutil
import requests
import json
import uuid
import time
import sys
import os
import datetime
import multiprocessing
import subprocess

# Try to import WMI for Windows specific info
try:
    import wmi
    w = wmi.WMI()
except ImportError:
    w = None

# Configuration
DEFAULT_SERVER_URL = "http://localhost:5000/api/report"

# Determine the directory where the executable (or script) is located
if getattr(sys, 'frozen', False):
    APP_DIR = os.path.dirname(sys.executable)
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))

# Setup logging to a file in the same directory
LOG_FILE = os.path.join(APP_DIR, 'agent_monitor.log')

def log(message):
    try:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(LOG_FILE, 'a') as f:
            f.write(f"[{timestamp}] {message}\n")
    except:
        pass # Fallback if permission denied

def load_config():
    config_path = os.path.join(APP_DIR, 'config.json')
    # Print to console for immediate debug
    print(f"DEBUG: APP_DIR is {APP_DIR}")
    print(f"DEBUG: Looking for config at: {config_path}")
    log(f"Looking for config at: {config_path}")
    
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
                url = config.get('server_url', DEFAULT_SERVER_URL)
                log(f"Config loaded. URL: {url}")
                print(f"DEBUG: Config loaded. URL: {url}")
                return url
        except Exception as e:
            log(f"Error loading config: {e}")
            print(f"DEBUG: Error loading config from {config_path}: {e}")
            pass
    else:
        log("Config file not found. Using default URL.")
        print(f"DEBUG: Config file not found at {config_path}")
        
    return DEFAULT_SERVER_URL

SERVER_URL = load_config()



def get_size(bytes, suffix="B"):
    """
    Scale bytes to its proper format
    e.g:
        1253656 => '1.20MB'
        1253656678 => '1.17GB'
    """
    factor = 1024
    for unit in ["", "K", "M", "G", "T", "P"]:
        if bytes < factor:
            return f"{bytes:.2f}{unit}{suffix}"
        bytes /= factor

def get_system_info():
    try:
        uname = platform.uname()
        return {
            "system": uname.system,
            "node_name": uname.node,
            "release": uname.release,
            "version": uname.version,
            "machine": uname.machine,
            "processor": uname.processor
        }
    except:
        return {}

    except:
        return {}

def get_memory_info():
    try:
        svmem = psutil.virtual_memory()
        return {
            "total": svmem.total,
            "available": svmem.available,
            "percent": svmem.percent,
            "used": svmem.used
        }
    except:
        return {}

# Disk info function moved below


def get_network_info():
    try:
        # Get primary IP
        s = requests.socket.socket(requests.socket.AF_INET, requests.socket.SOCK_DGRAM)
        s.settimeout(0)
        try:
            # doesn't even have to be reachable
            s.connect(('10.254.254.254', 1))
            ip = s.getsockname()[0]
        except Exception:
            ip = '127.0.0.1'
        finally:
            s.close()
        return ip
    except:
        return "Unknown"

def get_geolocation():
    try:
        response = requests.get('https://ipinfo.io/json', timeout=5)
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return {"city": "Unknown", "region": "Unknown", "country": "Unknown"}


import winreg

def get_registry_value(key_path, value_name):
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as key:
            value, _ = winreg.QueryValueEx(key, value_name)
            return value
    except:
        return None

def run_cmd_simple(cmd_args):
    # Simple command runner for wmic/hostname (no powershell complexity)
    try:
        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
        process = subprocess.Popen(cmd_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, startupinfo=startupinfo)
        out, _ = process.communicate(timeout=5)
        return out.strip()
    except:
        return ""


# Try to import WMI (already in requirements)
try:
    import wmi
except ImportError:
    wmi = None

def get_cpu_info():
    brand = platform.processor()
    hz_str = ""
    usage = 0
    
    # 1. Try Registry for Name (Fastest)
    brand_reg = get_registry_value(r"HARDWARE\DESCRIPTION\System\CentralProcessor\0", "ProcessorNameString")
    if brand_reg:
        brand = brand_reg
        
    # 2. Try WMI for Usage/Cores
    try:
        if wmi:
            w = wmi.WMI()
            for processor in w.Win32_Processor():
                if not brand_reg: brand = processor.Name
                hz_str = f"{processor.MaxClockSpeed / 1000:.2f} GHz"
                break # Just first CPU
    except:
        pass

    return {
        "brand": brand,
        "hz": hz_str,
        "count": psutil.cpu_count(logical=True),
        "usage_percent": psutil.cpu_percent(interval=1)
    }

def get_windows_hardware_info():
    manufacturer = "Unknown"
    serial = "Unknown"
    
    if wmi:
        try:
            w = wmi.WMI()
            # BIOS
            for bios in w.Win32_BIOS():
                manufacturer = bios.Manufacturer
                serial = bios.SerialNumber
                break
                
            # Fallback for serial
            if serial.lower() == 'to be filled by o.e.m.':
                 for board in w.Win32_BaseBoard():
                      serial = board.SerialNumber
                      break
        except:
             pass
             
    return manufacturer, serial

def get_user_info():
    username = "Nenhum usuário logado"
    domain = ""
    hostname = platform.node()
    
    if wmi:
        try:
            w = wmi.WMI()
            found = False
            # Method: Owner of explorer.exe
            for process in w.Win32_Process(Name='explorer.exe'):
                try:
                    owner_sid = process.GetOwnerSid() # Can fail
                    owner = process.GetOwner()
                    if owner:
                         user = owner.get('User', '')
                         dom = owner.get('Domain', '')
                         if user:
                             username = user
                             domain = dom
                             found = True
                             break
                except:
                    pass
            
            if not found:
                 # Fallback: ComputerSystem UserName
                 for cs in w.Win32_ComputerSystem():
                      if cs.UserName:
                           username = cs.UserName
                           break

        except:
            pass
            
    return {
        "username": username,
        "domain": domain,
        "hostname": hostname
    }

def get_disk_info():
    disks = []
    try:
        # psutil is good for usage, let's keep it but formatted nicely
        partitions = psutil.disk_partitions()
        for partition in partitions:
            try:
                if 'cdrom' in partition.opts or partition.fstype == '':
                    continue
                partition_usage = psutil.disk_usage(partition.mountpoint)
                
                # Format bytes to GB
                total_gb = f"{partition_usage.total / (1024**3):.1f} GB"
                free_gb = f"{partition_usage.free / (1024**3):.1f} GB"
                
                disks.append({
                    "device": partition.device,
                    "mountpoint": partition.mountpoint,
                    "fstype": partition.fstype,
                    "total": str(partition_usage.total),
                    "total_fmt": total_gb,
                    "free_fmt": free_gb,
                    "percent": partition_usage.percent
                })
            except PermissionError:
                continue
    except:
        pass
    return disks

def get_installed_software():
    software_list = []
    if w:
        # NOTE: Win32_Product is slow. 
        # For a better implementation, reading Registry is recommended.
        # This is a basic implementation.
        try:
            # Using Win32_InstalledWin32Program or just skipping for speed in demo
            # Let's try to get just top 10 to avoid hanging
            # or use a faster method if possible.
            # Actually, let's use a powershell command via subprocess which is faster and safer
            import subprocess
            cmd = 'Get-ItemProperty HKLM:\\Software\\Wow6432Node\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\* | Select-Object DisplayName, DisplayVersion, Publisher'
            process = subprocess.Popen(["powershell", "-Command", cmd], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            result = process.communicate() 
            
            if result[0]:
                lines = result[0].split('\n')
                # Parse the output (simple approximation)
                # Output format is objects, we might want to use ConvertTo-Json
                 
            # improved command
            cmd_json = 'Get-ItemProperty HKLM:\\Software\\Wow6432Node\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\* | Select-Object DisplayName, DisplayVersion, Publisher | ConvertTo-Json'
            process = subprocess.Popen(["powershell", "-Command", cmd_json], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            result = process.communicate()
            if result[0]:
                data = json.loads(result[0])
                # data can be list or dict
                if isinstance(data, dict): data = [data]
                for item in data:
                    if item.get('DisplayName'):
                        software_list.append({
                            "name": item.get('DisplayName'),
                            "version": item.get('DisplayVersion', 'N/A'),
                            "vendor": item.get('Publisher', 'N/A')
                        })
        except Exception as e:
            print(f"Error getting software: {e}")
            pass
            
    return software_list


def collect_and_send():
    print(f"Starting SGML Agent... (VERSION: 2.0 - REQUEST TIMEOUT FIX)")
    print(f"Target Server: {SERVER_URL}")
    
    # 1. Gather all data
    print("Collecting system info...")
    sys_info = get_system_info()
    user_info = get_user_info() # New field
    
    print("Collecting CPU/Mem info...")
    cpu_info = get_cpu_info()
    mem_info = get_memory_info()
    
    print("Collecting disk info...")
    disk_info = get_disk_info()
    
    print("Collecting network info...")
    ip_address = get_network_info()
    
    print("Collecting hardware info...")
    manufacturer, serial = get_windows_hardware_info()
    
    print("Collecting geolocation...")
    geo = get_geolocation()
    
    print("Collecting software list (this may take a moment)...")
    software = get_installed_software()
    
    uptime = time.time() - psutil.boot_time()
    
    # Unique ID based on MAC or Serial (prefer serial if available)
    if serial and serial != "Unknown":
         unique_id = serial
    else:
         unique_id = str(uuid.getnode())
    
    payload = {
        "uuid": unique_id,
        "hostname": user_info.get('hostname'),
        "user_info": user_info, # New field sent to server
        "ip": ip_address,
        "os": sys_info,
        "cpu": cpu_info,
        "memory": mem_info,
        "disk": disk_info,
        "uptime": uptime,
        "manufacturer": manufacturer,
        "serial_number": serial,
        "geolocation": geo,
        "software": software,
        "metrics": {
            "cpu_usage": cpu_info.get('usage_percent'),
            "memory_usage": mem_info.get('percent')
        }
    }
    
    # 2. Send to server
    try:
        log("Sending report to server...")
        print("Sending report to server...")
        headers = {'Content-Type': 'application/json'}
        # Add timeout to prevent hanging
        response = requests.post(SERVER_URL, data=json.dumps(payload), headers=headers, timeout=30)
        
        if response.status_code == 200:
            log("✅ Report sent successfully!")
            print("✅ Report sent successfully!")
        else:
            log(f"❌ Server returned status: {response.status_code}")
            log(f"Response: {response.text}")
            print(f"❌ Server returned status: {response.status_code}")
            print(response.text)
    except Exception as e:
        log(f"❌ Failed to send report: {e}")
        print(f"❌ Failed to send report: {e}")

if __name__ == "__main__":
    multiprocessing.freeze_support()
    log("Manual execution started.")
    collect_and_send()
    # Keep window open if double clicked
    print("\nDone. Closing in 5 seconds...")
    time.sleep(5)
