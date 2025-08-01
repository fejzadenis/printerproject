from escpos.printer import Network

from . import communication
from . import api_services
from . import escpos_to_starprnt
import threading
import os
import base64
import binascii
import time
import win32print
import win32ui

app_data_folder = os.getenv('APPDATA')  # Gets the AppData folder path
temp_file_path = os.path.join(app_data_folder, "AskyPrint", "tmp")

# Create directory if it doesn't exist
os.makedirs(os.path.dirname(temp_file_path), exist_ok=True)





def execute_usb_print(data, ulid, printer_name):
    try:
        hPrinter = win32print.OpenPrinter(printer_name)
        hJob = win32print.StartDocPrinter(hPrinter, 1, ("Asky Job", None, "RAW"))
        win32print.StartPagePrinter(hPrinter)
        win32print.WritePrinter(hPrinter, data.encode('utf-8'))  # or encode in 'latin-1' if using ESC/POS
        win32print.EndPagePrinter(hPrinter)
        win32print.EndDocPrinter(hPrinter)
        win32print.ClosePrinter(hPrinter)
    except Exception as e:
        print(f"[{printer_name}] USB print error: {e}")

def set_printer_paper_status(ip,mac_address):
    try:
        p = Network(ip)
        paper_status= p.paper_status()
        api_services.update_paper_availability(mac_address,paper_status)
        p.close()
    except:
        print(f"Unable to update paper availability on {ip}")

def get_paper_availability(ip):
    try:
        p = Network(ip)
        paper_status= p.paper_status()
        p.close()
        return True
    except:
        print(f"Status Failed of {ip}")
        return False

def update_printer_status(printer_list = list, update_list = list):
    req_body = {
    "printers": []
    }
    for mac_address in update_list:
        printer_ip = get_ip_by_mac(mac_address,printer_list)
        if printer_ip:
            status = get_paper_availability(printer_ip)
            if status:
                req_body["printers"].append({
                    "mac": mac_address,
                    "paper_availability": status,
                    "status": "online"
                })
            else:
                req_body["printers"].append({
                    "mac": mac_address,
                    "status": "offline"
                })
        else:
            req_body["printers"].append({
                "mac": mac_address,
            })
    try:
       api_services.update_printer_status(req_body)
       print("Printer list updated successfully")
    except:
        print("Got error updating printer list")

def is_base64(s):
    if not isinstance(s, str):
        return False
    try:
        # Strip whitespace/newlines
        s_clean = s.strip()
        # Base64 strings must have a length divisible by 4
        if len(s_clean) % 4 != 0:
            return False
        # Try decoding and re-encoding
        decoded = base64.b64decode(s_clean, validate=True)
        encoded = base64.b64encode(decoded).decode('utf-8')
        return s_clean == encoded
    except (binascii.Error, ValueError):
        return False

def cleanup_temp_files(paths):
    for path in paths:
        try:
            if os.path.exists(path):
                os.remove(path)
        except Exception as e:
            print(f"Failed to delete {path}: {e}")

def execute_print(ip,data,ulid,mac_id,printer):
    start_time = time.time()
    print(f"[{ulid}] START print @ {start_time:.2f} on {ip} for {mac_id}")

    try:
        #print("TASK ID",ulid)
        #print("IP:",ip)
        #print("DATA : ","data")

        mode = "w+b"
        if is_base64(data):
            decoded_data = base64.b64decode(data)
        else:
            decoded_data = data
            if isinstance(data, str):
                mode = "w+"
        
        os.makedirs(os.path.dirname(f"{temp_file_path}/"), exist_ok=True)
        with open(f"{temp_file_path}/{ulid}.bin",mode) as print_job_bin:
            print_job_bin.write(decoded_data)

        try:
            with open(f"{temp_file_path}/{ulid}.bin", "rb") as file:  # read the file in binary mode
                print_data = file.read()
            
            #print(print_data)
            if printer['is_star_printer']:
                print(f"[{ulid}] Detected STAR printer")
                json_path = os.path.join(temp_file_path, f"receipt_{ulid}.json")
                
                instructions, image_files = escpos_to_starprnt.parse_escpos_stream(print_data, temp_file_path, ulid)
                escpos_to_starprnt.write_json(json_path, instructions)
                
                builder_start = time.time()
                star_commands = escpos_to_starprnt.run_builder(printer['port'], printer['name'], json_path)
                print(f"[{ulid}] Builder took {time.time() - builder_start:.2f}s")

                image_files.append(json_path)
                threading.Thread(target=cleanup_temp_files, args=(image_files,)).start()
                if star_commands is None:
                    raise ValueError("Builder returned None, check if the printer is a STAR printer or if the builder is correctly configured.")
                
                send_start = time.time()
                communication.send_commands(star_commands, printer['port'], '', 10000)
                print(f"[{ulid}] Send took {time.time() - send_start:.2f}s")    
            elif printer.get('connection_type') == 'usb':
                print(f"[{ulid}] Detected USB printer")
                if isinstance(print_data, bytes):
                    print_data_str = print_data.decode('utf-8', errors='ignore')
                else:
                    print_data_str = print_data
                execute_usb_print(print_data_str, ulid, printer['name'])
            else:
                p = Network(ip)
                p._raw(print_data)
                p.close()
            api_services.post_sucess_printing_job(ulid)
            print("Sucessfully executed print for ",ulid)
        except Exception as e:
            print("Failed executing print for ",ulid)
            print(e)
            api_services.post_failed_printing_job(ulid)

        os.remove(f"{temp_file_path}/{ulid}.bin")
        # if printer['is_star_printer'] == False:
        #     set_printer_paper_status(ip,mac_id)
        
    except Exception as e:
        print("Failed to execute print for ulid: ",ulid)
        print(e)

    print(f"[{ulid}] End print @ {time.time() - start_time:.2f}s on {ip} for {mac_id}")

def create_print_execution_thread(ip,data,ulid,mac_id,printer):
    thread = threading.Thread(target=execute_print, args=(ip,data,ulid,mac_id,printer))
    thread.daemon = True
    thread.start()
    
def get_ip_by_mac(mac_address, device_list):
    for device in device_list:
        if device['mac'] == mac_address:
            return device['ip']
    return None  # Return None if the MAC address is not found
