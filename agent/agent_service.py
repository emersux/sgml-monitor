import win32serviceutil
import win32service
import win32event
import servicemanager
import socket
import time
import sys
import os

# Ensure the directory containing this script is in the path
# so we can import agent
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

import agent

class SGMLAgentService(win32serviceutil.ServiceFramework):
    _svc_name_ = "SGMLMonitor"
    _svc_display_name_ = "SGML Monitor Service"
    _svc_description_ = "Coleta e envia dados de hardware e software para o servidor SGML."

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        self.running = True

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        self.running = False
        win32event.SetEvent(self.hWaitStop)

    def SvcDoRun(self):
        servicemanager.LogMsg(servicemanager.EVENTLOG_INFORMATION_TYPE,
                              servicemanager.PYS_SERVICE_STARTED,
                              (self._svc_name_, ''))
        
        # Change CWD to the directory of the executable/script
        if getattr(sys, 'frozen', False):
            home_dir = os.path.dirname(sys.executable)
        else:
            home_dir = os.path.dirname(os.path.abspath(__file__))
        
        os.chdir(home_dir)
        
        self.main()

    def main(self):
        # Initial run
        try:
            agent.collect_and_send()
        except Exception as e:
            servicemanager.LogErrorMsg(f"SGML Agent Error: {str(e)}")

        # Loop
        while self.running:
            # Check for stop signal every 5 seconds, but only run task every 60s
            # For simplicity, we just use a timeout on the wait event
            rc = win32event.WaitForSingleObject(self.hWaitStop, 60000) # 60 seconds
            if rc == win32event.WAIT_OBJECT_0:
                # Stop signal received
                break
            
            try:
                agent.collect_and_send()
            except Exception as e:
                servicemanager.LogErrorMsg(f"SGML Agent Error: {str(e)}")

if __name__ == '__main__':
    if len(sys.argv) == 1:
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(SGMLAgentService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        win32serviceutil.HandleCommandLine(SGMLAgentService)
