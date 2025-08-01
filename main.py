# Qt Imports
from PyQt5.QtWidgets import QApplication, QMainWindow,QMessageBox,QSystemTrayIcon,QMenu,QAction,QProgressDialog
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import QThread, pyqtSignal , Qt
from ui.login_screen import Ui_LoginWindow  
from ui.main_window_screen import Ui_MainWindow
import random
from ui.settings_screen import Ui_SettingsWindow

# Other Imports
import sys
import os
import re
import json
import time
import threading
from tendo import singleton

# Custom utility imports
import utils.api_services as api_handler
import utils.printer_detection_service as auto_printer
import utils.printer_detection_service_zeroconf as auto_printer_zeroconf
import utils.printer_detection_service_starprnt as auto_printer_starprnt
import utils.pos_printing_service as pos_printing_service
from utils.printer_detection_service import get_usb_printers

from queue import Queue

app_data_folder = os.getenv('APPDATA')  # Gets the AppData folder path
token_file_path = os.path.join(app_data_folder, "AskyPrint", "token.auth")
settings_file_path = os.path.join(app_data_folder,"AskyPrint","settings.json")

# Create the settings file if not already created
if not os.path.exists(settings_file_path):
    with open(settings_file_path, "w+") as file:
        json.dump({
            "SCANNING_PORTS":[],
            "USER_EMAIL":""
            }, file,)

# Create directory if it doesn't exist
os.makedirs(os.path.dirname(token_file_path), exist_ok=True)
me = singleton.SingleInstance()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()  # Create an instance of the UI class for the main window
        self.ui.setupUi(self)      # Setup the main window UI
        self.setFixedSize(self.size())
        
        # Create the system tray icon
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon("resources\\Asky_Logo_black_500.png"))  # Replace with your icon file path

        # Create a menu for the tray icon
        tray_menu = QMenu()
        restore_action = QAction("Restore", self)
        restore_action.triggered.connect(self.restore_window)
        tray_menu.addAction(restore_action)

        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.exit_app)
        tray_menu.addAction(exit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.tray_icon_activated)
        
        # Buttons
        self.ui.logout_button.clicked.connect(self.logout)
        self.ui.settings_button.clicked.connect(self.open_settings_window)
        self.ui.refresh_printer_list_button.clicked.connect(lambda: self.fetch_printers_list(open_loader=True))
        
        # Check if main thread is running
        self.is_main_thread_running = False
        
        # Check session state
        self.check_login_status()

        # Show the tray icon
        self.tray_icon.show()
        
        # Show loading screen and prepare printer list data
        self.fetch_printers_list()
    
    def check_login_status(self):
        try:
            status = api_handler.get_login_state()["status"]
            print(status)
            if status == 401:
                self.logout()
        except:
            self.show_quick_error_message("An error has occurred while connecting, Please check your connection")
            self.tray_icon.hide()
            QApplication.quit()
            
            
            
    def fetch_printers_list(self,open_loader=True):
        # Create the progress dialog
        if open_loader:
            self.loading_screen = QProgressDialog("Getting online printers, Please wait...", None, 0, 0, self)
            self.loading_screen.setWindowTitle("Asky Print")
            self.loading_screen.setWindowFlags(self.windowFlags() & ~Qt.WindowCloseButtonHint)
            self.loading_screen.setCancelButton(None)  # Disable cancel button
            self.loading_screen.setWindowModality(Qt.ApplicationModal)  # Make the dialog modal
            self.loading_screen.setFixedSize(300,100)
            self.loading_screen.show()

        # start the thread to get online printers
        self.printer_list_thread = FetchPrinterListThread()
        self.printer_list_thread.task_finished.connect(self.on_printer_list_generated)
        self.printer_list_thread.start()

    def on_printer_list_generated(self,printer_data):
        try:
            self.loading_screen.close()
        except:
            print("Error closing loading screen")
        
        # start the main thread for printing tasks execution
        if not self.is_main_thread_running:
            # Main printer Thread
            self.main_thread = MainWorkerThread(printer_data)
            self.main_thread.update_signal.connect(self.on_main_thread_update)
            self.main_thread.connection_signal.connect(self.set_connection_update)
            print("Main Thread Started")
            self.main_thread.start()
            self.is_main_thread_running = True
            
    def set_connection_update(self,status):
        if status == True:
            self.ui.connection_label.setText("🟢 Connected to Server")
        else:
            self.ui.connection_label.setText("🔴 Server Disconnected")
    def on_main_thread_update(self,message):
        print(message)
    
    def closeEvent(self, event):
        event.ignore()
        self.hide()

    def tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            self.restore_window()

    def restore_window(self):
        self.show()
        self.activateWindow()

    def exit_app(self):
        self.tray_icon.hide()
        QApplication.quit()
            
    def show_quick_error_message(self,message):
        QMessageBox.critical(self,"Error", message)
        
    def open_settings_window(self):
        self.settings_window = SettingsWindow()  # Create an instance of the main window
        self.settings_window.show()   # Show the main window
    
    def logout(self):
        os.remove(token_file_path)
        os.execl(sys.executable, os.path.abspath(__file__), *sys.argv)
        
    
        

class LoginWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_LoginWindow() 
        self.ui.setupUi(self)
        self.setFixedSize(self.size())

        # Connect signals to slots here
        self.ui.user_login_button_input.clicked.connect(self.handle_login) 
        self.ui.user_password_input.returnPressed.connect(self.handle_login)
        self.ui.forgot_password_button.clicked.connect(self.handle_forgot_password)
        
        # Get saved username from settings file
        with open(settings_file_path, "r") as file:
            json_data = json.load(file)

        # Modify the data
        self.ui.user_id_input.setText(json_data["USER_EMAIL"])
        
    def handle_forgot_password(self):
        res = api_handler.handle_forgot_password(self.ui.user_id_input.text())
        res_json = res.json()
        if res.status_code == 200:
            self.show_info_message(res_json["status"])
            print("Password reset link sent")
        else:
            errors = res_json["errors"]
            if 'email' in errors:
                self.ui.id_error_label.setText(errors["email"][0])
        
    def handle_login(self):
        # Logic to handle login button click
        res = api_handler.handle_login(self.ui.user_id_input.text(),self.ui.user_password_input.text())
        res_json = res.json()
        if res.status_code == 200:  
            print("Login successful!")
            with open(token_file_path,'w+') as token_file:
                token_file.write(res_json['token'])
                
            # Set username to settings file
            with open(settings_file_path, "r") as file:
                json_data = json.load(file)

            # Modify the data
            json_data["USER_EMAIL"] = self.ui.user_id_input.text()

            # Write the modified data back to the file
            with open(settings_file_path, "w") as file:
                json.dump(json_data, file, indent=4)
                
            self.open_main_window()
        else:
            print("Login Failed!")
            errors = res_json["errors"]
            if 'email' in errors:
                self.ui.id_error_label.setText(errors["email"][0])
            if 'password' in errors:
                self.ui.password_error_label.setText(errors["password"][0])
                
    def open_main_window(self):
        self.main_window = MainWindow()  # Create an instance of the main window
        self.main_window.show()            # Show the main window
        self.close()                       # Close the login window
        
    def show_info_message(self,message):
        QMessageBox.information(self,"Info", message)      

class SettingsWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_SettingsWindow()  # Create an instance of the UI class for the main window
        self.ui.setupUi(self)      # Setup the main window UI
        self.setFixedSize(self.size())
        
        self.load_port_settings()
        
        self.ui.port_remove_button.clicked.connect(self.remove_port_entry)
        self.ui.port_add_button.clicked.connect(self.add_port_entry)
        self.ui.done_button.clicked.connect(self.save_settings)
    
    def get_list_widget_items(self):
        items = []
        for index in range(self.ui.port_list.count()):
            items.append(self.ui.port_list.item(index).text())
        return items
        
    def remove_port_entry(self):
        selected_row = self.ui.port_list.currentRow()

        if selected_row >= 0:  # Check if an item is selected
            self.ui.port_list.takeItem(selected_row)   # Remove the item at the selected index
    
    def load_port_settings(self):
        if os.path.exists(settings_file_path):
            with open(settings_file_path,"r") as settings_file:
                ports_list = json.loads(settings_file.read())["SCANNING_PORTS"]
                for port in ports_list:
                    self.ui.port_list.addItem(str(port))
        
    def add_port_entry(self):
        port_number = self.ui.new_port_input.text()
        pattern_match = bool(re.match(r'^\d{1,6}$', port_number))
        if pattern_match:
            if not port_number in self.get_list_widget_items():
                self.ui.port_list.addItem(port_number)
                self.ui.new_port_input.setText("")
            else:
                self.show_quick_error_message("Port is already added")
        else:
            self.show_quick_error_message("Please input a valid port number (Max 6 digit)")
            
    def save_settings(self):
        port_arr = self.get_list_widget_items()
        int_port_array = list(map(int, port_arr))
        
        with open(settings_file_path, "r") as file:
            json_data = json.load(file)

        # Modify the data
        json_data["SCANNING_PORTS"] = int_port_array

        # Write the modified data back to the file
        with open(settings_file_path, "w") as file:
            json.dump(json_data, file, indent=4)
        self.close()
    
    def save_username(self,username):
        with open(settings_file_path, "r") as file:
            json_data = json.load(file)

        # Modify the data
        json_data["USER_EMAIL"] = username

        # Write the modified data back to the file
        with open(settings_file_path, "w") as file:
            json.dump(json_data, file, indent=4)
            
    def show_quick_error_message(self,message):
        QMessageBox.critical(self,"Error", message)     
          
class FetchPrinterListThread(QThread):
    
    # This is the fetchPrinterList thread to fetch online printer list from the client

    # Attributes:
    #     task finished (pyqtSignal): Signal emitted when task finished

    # Methods:
    #     prepare_printer_list_data(): preapre the pinter list data
    #     merge_lists(): Merge zeroconf and ip fetched printer lists together
    #     run(): run the main function of fetching printer list
    
    task_finished = pyqtSignal(list)

    def run(self):
        data = self.prepare_printer_list_data()
        self.task_finished.emit(data)

    def prepare_printer_list_data(self):
        printer_list = auto_printer.get_ip_network_printers()
        printer_list_zeroconf = auto_printer_zeroconf.discover_devices(timeout=5)
        printer_list_starprnt = auto_printer_starprnt.get_ip_network_printers()
        usb_printers = get_usb_printers()
        return self.merge_lists(printer_list, printer_list_zeroconf, printer_list_starprnt, usb_printers)


    def sanitize_usb_printers(self, printers):
        cleaned = []

        def generate_random_ip():
            return f"192.168.{random.randint(0, 255)}.{random.randint(1, 254)}"

        def generate_random_mac():
            return ":".join(f"{random.randint(0, 255):02x}" for _ in range(6))

        for printer in printers:
            if not printer.get("name"):
                continue

            cleaned.append({
                "name": printer["name"],
                "type": "usb",
                "ip": generate_random_ip(),
                "mac": generate_random_mac(),
                "port": f"usb-{random.randint(1000,9999)}", # Add default if needed
                "is_star_printer": False
            })

        return cleaned

    def merge_lists(self, *lists):
        merged_dict = {}
        print("\n--- Starting merge_lists ---")

        for printer_list in lists:
            print(f"\nReceived list with {len(printer_list)} printers:")
            for entry in printer_list:
                print(f"  Raw Entry: {entry}")

                printer_type = entry.get('type')
                if printer_type == 'usb':
                    unique_key = entry.get('name')
                else:
                    unique_key = entry.get('ip')

                if not unique_key:
                    print("  Skipping due to missing key.")
                    continue

                merged_dict[unique_key] = entry

        printer_list = list(merged_dict.values())

        usb_printers = [p for p in printer_list if p["type"] == "usb"]
        usb_printers = self.sanitize_usb_printers(usb_printers)  # <=== Call using self
        lan_printers = [p for p in printer_list if p["type"] != "usb"]

        print(f"\nUSB Printers ({len(usb_printers)}): {usb_printers}")
        print(f"LAN Printers ({len(lan_printers)}): {lan_printers}")

        print("\n--- Sending USB printers ---")
        res_usb = api_handler.post_detected_printers(usb_printers, "lan")
        print(f"USB Server Response: {res_usb}")

        print("\n--- Sending LAN printers ---")
        

        print("--- merge_lists complete ---\n")
        return printer_list




class PrinterWorkerThread(QThread):
    def __init__(self, printer_info):
        super().__init__()
        self.printer_info = printer_info
        self.queue = Queue()
        self._running = True
        self.lock = threading.Lock()
        self.setObjectName(f"PrinterThread-{self.printer_info['ip']}")

    def run(self):
        while self._running:
            try:
                if not self.queue.empty():
                    job = self.queue.get()

                    if self.printer_info.get("type") == "usb":
                        # USB printing mock using CuteWriter
                        pos_printing_service.execute_usb_print(
                            job["data"],
                            job["ulid"],
                            self.printer_info["name"]  # CutePDF Writer or other name
                        )
                    else:
                        pos_printing_service.execute_print(
                            job["printer_ip"],
                            job["data"],
                            job["ulid"],
                            self.printer_info['mac'],
                            self.printer_info
                        )
                    self.queue.task_done()
                else:
                    time.sleep(0.1)
            except Exception as e:
                print(f"[{self.printer_info.get('ip', 'usb')}] Error in job processing: {e}")
                time.sleep(0.3)

    def stop(self):
        self._running = False

class MainWorkerThread(QThread):
    # This is the main worker thread to get and execute the list of pending printing tasks

    # Attributes:
    #     update_signal (pyqtSignal): Signal emitted with the current count.

    # Methods:
    #     run(): The main execution method of the thread.
    #     stop(): Stops the thread's execution.

    update_signal = pyqtSignal(str)
    connection_signal = pyqtSignal(bool)

    def __init__(self,printers_data):
        super().__init__()
        self._running = True
        self.printer_list_data = printers_data
        self.printer_threads = {}

        # Create and start a thread for each printer
        for printer in printers_data:
            mac = printer.get('mac')
            if mac:
                normalized_mac = mac.lower().strip()
                worker = PrinterWorkerThread(printer)
                worker.start()
                self.printer_threads[normalized_mac] = worker
                print(f"[DEBUG] Registered printer thread for MAC: {normalized_mac}")


    def run(self):
        count = 0
        while self._running:
            print("\n[DEBUG] Registered Printers:")
            for mac, thread in self.printer_threads.items():
                printer_info = getattr(thread, "printer_info", {})  # if you store it
                name = printer_info.get("name", "Unknown")
                ip = printer_info.get("ip", "N/A")
                print(f"  - MAC: {mac}, Name: {name}, IP: {ip}, Thread: {thread}")
            try:
                # Fetch pending print jobs    

                res = api_handler.get_pending_printing_status()



                if res["status"] == 200:
                    if res["data"].get("print_jobs"):

                        jobs_res = api_handler.get_pending_printing_jobs()


                        jobs = jobs_res['data']
                        for job in jobs:

                            printer_mac = job.get("printer_mac")

                            if printer_mac and printer_mac in self.printer_threads:
                                print(f"[DEBUG] Job matched with printer (MAC: {printer_mac})")
                                self.printer_threads[printer_mac].queue.put(job)
                            else:
                                print(f"[WARNING] No matching printer found for job (MAC: {printer_mac}) -> {job}")

                        count += len(jobs)

                    else:
                        print("[DEBUG] No print_jobs flag found in pending status response.")
                else:
                    print(f"[ERROR] Failed to fetch pending printing status, code: {res['status']}")

                        #self.update_signal.emit(f"Processed Jobs: {count}")  # Emit the count of processed jobs
                
                    if res["data"].get("sync_printers"):
                        self.printer_list_thread = FetchPrinterListThread()
                        self.printer_list_thread.task_finished.connect(self.on_printer_list_finished)
                        self.printer_list_thread.start()
                        time.sleep(2)
                
                    if res["data"].get("update_printers"):
                        pos_printing_service.update_printer_status(self.printer_list_data,res["data"]["update_printers_list"])
                        print(self.printer_list_data)
                
                self.connection_signal.emit(True)   
                time.sleep(1)
            except Exception as e:
                print(e)
                self.connection_signal.emit(False)
                print("Disconnection detected , retrying after 2 seconds")
                time.sleep(2)

    def on_printer_list_finished(self):
        print("Finished Fetching Printer List")
    
    def stop(self):
        # Method to stop the thread loop
        self._running = False
        for thread in self.printer_threads.values():
            thread.stop()
        
    def get_mac_address(self,ip, devices_list):
        return next((device['mac'] for device in devices_list if device['ip'] == ip), None)
    
    def get_printer(self, ip, devices_list):
        return next((device for device in devices_list if device['ip'] == ip), None)
        
if __name__ == "__main__":
    app = QApplication(sys.argv)
    if(os.path.exists(token_file_path)):
        main_window = MainWindow()
        main_window.show()  
    else:
        login_window = LoginWindow()
        login_window.show()   
        
      
    sys.exit(app.exec_())