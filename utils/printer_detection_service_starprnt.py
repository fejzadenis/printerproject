import os
import sys
import clr
import threading
import queue

if hasattr(sys, '_MEIPASS'):
    # PyInstaller extracts files to _MEIPASS during runtime
    dll_dir = os.path.join(sys._MEIPASS, 'StarPRNTSDK')
else:
    # Use the local directory during development
    script_dir = os.path.dirname(os.path.abspath(__file__))
    dll_dir = os.path.join(script_dir, '..\\StarPRNTSDK')
    
# Add the DLL directory to sys.path
sys.path.append(dll_dir)

# Add reference to the StarIO assembly
clr.AddReference('StarIO')
clr.AddReference('StarIOExtension')

from StarMicronics.StarIO import Factory, PrinterInterfaceType


# def get_device_name(ip):
#     # Try to retrieve the device name (hostname) from the IP address.
#     try:
#         hostname, _, _ = socket.gethostbyaddr(str(ip))
#         return hostname
#     except (socket.herror, socket.gaierror):
#         # These exceptions are raised if the hostname could not be found
#         return None

def get_device_ip(port_info):
    # Extract the IP address from the port information
    ip = port_info.PortName.split(":")[1]
    return ip

def scan_printers(data_queue):
    try:
        # Search for all printers
        printers = Factory.I.SearchPrinter(PrinterInterfaceType.Ethernet)
        for port_info in printers:
            #print(f"Port: {port_info.PortName}, Model: {port_info.ModelName}")
            data_queue.put(
                {
                    "name": port_info.ModelName,
                    "port": port_info.PortName,
                    "ip": get_device_ip(port_info),
                    "mac": port_info.MacAddress,
                    "is_star_printer": True,
                }
            )
    except:
        print(f"Got error in scan_printers")

def get_ip_network_printers():
    # Scan the specified network for POS printers.
    data_queue = queue.Queue()
    thread = threading.Thread(target=scan_printers, args=(data_queue,))
    thread.start()
    thread.join()

    # Collect results from the queue
    printer_list_data = []
    while not data_queue.empty():
        printer_list_data.append(data_queue.get())

    return printer_list_data

if __name__ == "__main__":
    printers = get_ip_network_printers()  # Scan for printers
    print(printers)  # Print the results