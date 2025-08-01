from getmac import get_mac_address
import time

def get_mac_with_retry(ip, retries=3, delay=1):
    #Attempt to get the MAC address, retrying on failure.
    for _ in range(retries):
        mac_address = get_mac_address(ip=str(ip))
        if mac_address is not None:
            return mac_address
        time.sleep(delay)  # Wait for a moment before retrying
    return None