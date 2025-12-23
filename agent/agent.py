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


def run_powershell(cmd):
    try:
        import subprocess
        # Force UTF-8 encoding for output to handle special chars correctly
        full_cmd = f'$OutputEncoding = [Console]::OutputEncoding = [Text.Encoding]::UTF8; {cmd} | ConvertTo-Json -Depth 1'
        
        # specific fix for "creation flag" to hide window not needed in service but good for testing
        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
        process = subprocess.Popen(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", full_cmd], 
                                   stdout=subprocess.PIPE, 
                                   stderr=subprocess.PIPE, 
                                   text=True, 
                                   encoding='utf-8',
                                   startupinfo=startupinfo)
        result, error = process.communicate(timeout=15)
        
        if error:
            log(f"PS Error: {error}")

        if result:
            try:
                return json.loads(result)
            except:
                return result.strip()
    except Exception as e:
        log(f"PS Exception: {e}")
    return None

def get_windows_hardware_info():
    manufacturer = "Unknown"
    serial = "Unknown"
    
    try:
        # Get Serial Number (Service Tag) - Critical
        # Win32_BIOS usually has the vendor specific SerialNumber
        data = run_powershell("Get-CimInstance -ClassName Win32_BIOS | Select-Object Manufacturer, SerialNumber")
        if data:
            if isinstance(data, list): data = data[0]
            manufacturer = data.get('Manufacturer', 'Unknown').strip()
            serial = data.get('SerialNumber', 'Unknown').strip()
            
            # Fallback if Serial is empty or generic
            if not serial or serial.lower() == 'to be filled by o.e.m.':
                 # Try getting from baseboard
                 bb_data = run_powershell("Get-CimInstance -ClassName Win32_BaseBoard | Select-Object SerialNumber")
                 if bb_data:
                     if isinstance(bb_data, list): bb_data = bb_data[0]
                     serial = bb_data.get('SerialNumber', serial)
    except:
        pass
        
    return manufacturer, serial

def get_user_info():
    try:
        # Win32_ComputerSystem UserName is the currently logged on interactive user
        data = run_powershell("Get-CimInstance -ClassName Win32_ComputerSystem | Select-Object UserName, Domain, Name")
        if data:
            if isinstance(data, list): data = data[0]
            
            username = data.get('UserName')
            # If standard method fails (often empty if RDP or locked), try finding explorer.exe owner
            if not username:
                 try:
                     # Advanced fallback: get owner of explorer.exe
                     exp_data = run_powershell("Get-CimInstance -ClassName Win32_Process -Filter \"Name='explorer.exe'\" | Invoke-CimMethod -MethodName GetOwner | Select-Object User, Domain")
                     if exp_data:
                         if isinstance(exp_data, list): exp_data = exp_data[0]
                         u = exp_data.get('User', '')
                         d = exp_data.get('Domain', '')
                         if u:
                             username = f"{d}\\{u}" if d else u
                 except:
                     pass
            
            return {
                "username": username if username else "Nenhum usuário logado",
                "domain": data.get('Domain', 'Unknown'),
                "hostname": data.get('Name', 'Unknown')
            }
    except Exception as e:
        log(f"User Info Error: {e}")
        
    return {"username": "Unknown", "domain": "Unknown", "hostname": platform.node()}

def get_cpu_info():
    try:
        # Get Name directly from Win32_Processor which matches Task Manager
        data = run_powershell("Get-CimInstance -ClassName Win32_Processor | Select-Object Name, NumberOfCores, MaxClockSpeed")
        brand = "Unknown CPU"
        cores = 0
        hz = ""
        
        if data:
             if isinstance(data, list): data = data[0]
             brand = data.get('Name', brand).strip()
             cores = data.get('NumberOfCores', 0)
             hz = f"{data.get('MaxClockSpeed', 0) / 1000:.2f} GHz"

        return {
            "brand": brand,
            "hz": hz,
            "count": cores,
            "usage_percent": psutil.cpu_percent(interval=1)
        }
    except:
         return {"brand": platform.processor(), "count": psutil.cpu_count(), "usage_percent": 0}

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
