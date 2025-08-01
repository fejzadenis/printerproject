from zeroconf import Zeroconf, ServiceBrowser
import socket
import time
from . import network_common_handler

class MyListener:
    def __init__(self):
        self.devices = []

    def add_service(self, zeroconf, type, name):
        # Only add services of type "_ipp._tcp.local."
        if type == "_ipp._tcp.local.":
            info = zeroconf.get_service_info(type, name)
            if info:
                # Convert byte IP address to standard string format
                ip_address = socket.inet_ntoa(info.addresses[0])  # Convert to string
                mac_address = network_common_handler.get_mac_with_retry(ip_address)
                # Remove the service type from the name
                service_name = name.split("._ipp._tcp.local.")[0]
                self.devices.append({'name': service_name, 'port': '', 'ip': ip_address, 'mac':mac_address, 'is_star_printer': False})

def discover_devices(timeout=5):
    zeroconf = Zeroconf()
    listener = MyListener()

    # Wait for a certain time to discover devices
    time.sleep(timeout)
    
    # Close the Zeroconf instance to stop service discovery
    zeroconf.close()
    
    return listener.devices

if __name__ == "__main__":
    devices = discover_devices(timeout=10)  # Change the timeout as needed
    print(devices)