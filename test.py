from utils.api_services import *
from utils.network_common_handler import *
from utils.pos_printing_service import *
from utils.printer_detection_service import *
from utils.printer_detection_service_zeroconf import *
from utils.settings_handler import *
import os


if __name__ == '__main__':
    var = os.getenv('NUMBER_OF_PROCESSORS')  # Gets the AppData folder path
    print(var)