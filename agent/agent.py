import platform
import psutil
import requests
import json
import uuid
import time
import sys
import os

# Try to import WMI for Windows specific info
try:
    import wmi
    w = wmi.WMI()
except ImportError:
    w = None


# Configuration
DEFAULT_SERVER_URL = "http://localhost:5000/api/report"

def load_config():
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
                return config.get('server_url', DEFAULT_SERVER_URL)
        except:
            pass
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

def get_cpu_info():
    try:
        # Use py-cpuinfo if installed for better brand string, else fallback
        try:
            import cpuinfo
            info = cpuinfo.get_cpu_info()
            brand = info.get('brand_raw', platform.processor())
            hz = info.get('hz_advertised_friendly', '')
        except ImportError:
            brand = platform.processor()
            hz = ""

        return {
            "brand": brand,
            "hz": hz,
            "count": psutil.cpu_count(logical=True),
            "usage_percent": psutil.cpu_percent(interval=1)
        }
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

def get_disk_info():
    disks = []
    try:
        partitions = psutil.disk_partitions()
        for partition in partitions:
            try:
                if 'cdrom' in partition.opts or partition.fstype == '':
                    continue
                partition_usage = psutil.disk_usage(partition.mountpoint)
                disks.append({
                    "device": partition.device,
                    "mountpoint": partition.mountpoint,
                    "fstype": partition.fstype,
                    "total": partition_usage.total,
                    "percent": partition_usage.percent
                })
            except PermissionError:
                continue
    except:
        pass
    return disks

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

def get_windows_hardware_info():
    manufacturer = "Unknown"
    serial = "Unknown"
    if w:
        try:
            system = w.Win32_ComputerSystem()[0]
            manufacturer = system.Manufacturer
            bios = w.Win32_BIOS()[0]
            serial = bios.SerialNumber
        except:
            pass
    return manufacturer, serial

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
    print(f"Starting SGML Agent...")
    print(f"Target Server: {SERVER_URL}")
    
    # 1. Gather all data
    print("Collecting system info...")
    sys_info = get_system_info()
    
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
    
    # Unique ID based on MAC or Serial
    unique_id = str(uuid.getnode())
    
    payload = {
        "uuid": unique_id,
        "hostname": sys_info.get('node_name'),
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
        print("Sending report to server...")
        headers = {'Content-Type': 'application/json'}
        response = requests.post(SERVER_URL, data=json.dumps(payload), headers=headers)
        
        if response.status_code == 200:
            print("✅ Report sent successfully!")
        else:
            print(f"❌ Server returned status: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"❌ Failed to send report: {e}")

if __name__ == "__main__":
    collect_and_send()
    # Keep window open if double clicked
    print("\nDone. Closing in 5 seconds...")
    time.sleep(5)
