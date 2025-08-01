import json
import os
import sys

app_data_folder = os.getenv('APPDATA')  # Gets the AppData folder path
token_file_path = os.path.join(app_data_folder, "AskyPrint", "token.auth")

# Create directory if it doesn't exist
os.makedirs(os.path.dirname(token_file_path), exist_ok=True)


# def get_config_path(relative_path):
#     try:
#         base_path = sys._MEIPASS  # When bundled
#     except AttributeError:
#         base_path = os.path.abspath(".")  # When running as script
#     return os.path.join(base_path, relative_path)
def get_config_path(filename):
    if getattr(sys, 'frozen', False):
        base_path = os.path.dirname(sys.executable)
    else:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, filename)

def get_config_params():
    config_path = get_config_path("config.json")
    try:
        with open(config_path,"r") as config:
            return json.loads(config.read())
    except:
        print("no config file was found, please create a config file to continue....")

def get_token():
    try:
        with open(token_file_path,"r") as token_file:
            return token_file.read()
    except:
        return None