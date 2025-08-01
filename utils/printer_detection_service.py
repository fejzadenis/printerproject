import socket
import ipaddress
import threading
import queue
from . import network_common_handler
import win32print

# Define the port commonly used by POS printers
POS_PRINTER_PORT = 9100

def get_device_name(ip):
    # Try to retrieve the device name (hostname) from the IP address.
    try:
        hostname, _, _ = socket.gethostbyaddr(str(ip))
        return hostname
    except (socket.herror, socket.gaierror):
        # These exceptions are raised if the hostname could not be found
        return None

def scan_ip(ip, data_queue):
    # Check if the POS printer is available at the given IP address.
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1)  # Set timeout for the connection attempt
            sock.connect((str(ip), POS_PRINTER_PORT))
            mac_address = network_common_handler.get_mac_with_retry(str(ip))
            data_queue.put(
                {
                    "name": get_device_name(ip),
                    "port": str(POS_PRINTER_PORT),
                    "ip": str(ip),
                    "mac": mac_address,
                    "is_star_printer": False,
                }
            )
    except (socket.timeout, ConnectionRefusedError):
        pass  # Ignore timeouts and connection errors
    except:
        print(f"Got error checking IP address {ip}")



def get_usb_printers():
    printers = []
    for printer in win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS):
        name = printer[2]
        info = {
            "name": name,
            "type": "usb",
            "ip": None,
            "mac": None
        }
        printers.append(info)
    return printers

def get_ip_network_printers():
    # Scan the specified network for POS printers.
    data_queue = queue.Queue()
    threads = []
    for ip in ipaddress.IPv4Network(get_local_network()):
        thread = threading.Thread(target=scan_ip, args=(ip, data_queue))
        threads.append(thread)
        thread.start()

    # Wait for all threads to complete
    for thread in threads:
        thread.join()

    # Collect results from the queue
    printer_list_data = []
    while not data_queue.empty():
        printer_list_data.append(data_queue.get())

    return printer_list_data

def get_local_network():
    # Get the hostname of the current machine
    hostname = socket.gethostname()
    
    # Get the IP address of the current machine
    ip_address = socket.gethostbyname(hostname)
    
    # Convert the IP address to an IPv4Address object
    ip = ipaddress.ip_address(ip_address)
    
    # Determine the network by finding the subnet mask
    network = ipaddress.ip_network(ip).supernet(new_prefix=24)  # Assumes /24 for the subnet
    
    return str(network)

if __name__ == "__main__":
    printers = get_ip_network_printers()  # Scan for printers
    print(printers)  # Print the results