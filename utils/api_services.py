import requests
from . import settings_handler
import json

# ----------------------- CONFIG FILE ----------------------- 
CONFIG = settings_handler.get_config_params()
HOST = CONFIG["host"]
TOKEN = settings_handler.get_token()
DEFAULT_HEADERS = { "Accept":"application/json", "Content-Type":"application/json"}
DEFAULT_HEADERS_TOKEN = DEFAULT_HEADERS.copy()
DEFAULT_HEADERS_TOKEN["Authorization"] = f"Bearer {TOKEN}"
PRINTER_PAPER_STATUS = { 0:"paper_end", 1:"near_end", 2:"paper_present" }
# ----------------------- CONFIG FILE ----------------------- 


# ----------------------- API HANDLERS ----------------------- 
# Refresh token
def refetch_token():
    TOKEN = settings_handler.get_token()
    DEFAULT_HEADERS_TOKEN["Authorization"] = f"Bearer {TOKEN}"

# Login API
def handle_login(email,password):
    req_params = {
            'type':'email',
            'email':email,
            'password':password
        }
        
    res = requests.get(f"{HOST}/api/admin/login/",params=req_params,headers=DEFAULT_HEADERS,timeout=10)
    return(res)

# Forgot Password API
def handle_forgot_password(email):
    req_params = {
            'email':email,
        }
        
    res = requests.get(f"{HOST}/api/admin/password/reset",params=req_params,headers=DEFAULT_HEADERS,timeout=10)
    return(res)

def get_login_state():
    refetch_token()
    res = requests.get(f"{HOST}/api/v1/admin",headers=DEFAULT_HEADERS_TOKEN,timeout=10)
    return({
        "status":res.status_code
        })

def get_available_printers():
    res = requests.get(f"{HOST}/api/v1/admin/printers/network-printers",headers=DEFAULT_HEADERS_TOKEN,timeout=10)
    return({
        "status":res.status_code,
        "data":res.json()
        })
    
def post_detected_printers(printers_data, connection_type):
    payload = {
        "printers": printers_data,
        "connection": connection_type
    }

    print("\n--- POST Payload ---")
    print(json.dumps(payload, indent=2))  # 🔍 Add this line

    res = requests.post(
        f"{HOST}/api/v1/admin/printers/network-printers",
        headers=DEFAULT_HEADERS_TOKEN,
        data=json.dumps(payload),
        timeout=10
    )
    return {
        "status": res.status_code,
        "text": res.text  # 🔍 Add to see error details
    }
    
def get_pending_printing_status():
    print("📡 Fetching pending printing status...")
    try:
        res = requests.get(
            f"{HOST}/api/v1/admin/printers/lan/network-printers/pending-tasks",
            headers=DEFAULT_HEADERS_TOKEN,
            timeout=10
        )
        print(f"✅ Status Code: {res.status_code}")
        print("📄 Response JSON:", res.json())
        return {
            "status": res.status_code,
            "data": res.json()
        }
    except Exception as e:
        print("❌ Failed to fetch pending printing status:", e)
        return {"status": 500, "data": {}}

def get_pending_printing_jobs():
    print("📡 Fetching pending printing jobs...")
    try:
        res = requests.get(
            f"{HOST}/api/v1/admin/printers/lan/network-printers/print-jobs",
            headers=DEFAULT_HEADERS_TOKEN,
            timeout=10
        )
        print(f"✅ Status Code: {res.status_code}")
        print("📄 Response JSON:", res.json())
        return {
            "status": res.status_code,
            "data": res.json()
        }
    except Exception as e:
        print("❌ Failed to fetch pending printing jobs:", e)
        return {"status": 500, "data": {}}

def post_sucess_printing_job(ulid):
    print(f"📤 Reporting SUCCESS for print job ULID: {ulid}")
    try:
        res = requests.post(
            f"{HOST}/api/v1/admin/printers/lan/network-printers/print-jobs/{ulid}/success",
            headers=DEFAULT_HEADERS_TOKEN,
            timeout=10
        )
        print(f"✅ Status Code: {res.status_code}")
        return {"status": res.status_code}
    except Exception as e:
        print(f"❌ Failed to report success for ULID {ulid}: {e}")
        return {"status": 500}

def post_failed_printing_job(ulid):
    print(f"📤 Reporting FAILURE for print job ULID: {ulid}")
    try:
        res = requests.post(
            f"{HOST}/api/v1/admin/printers/lan/network-printers/print-jobs/{ulid}/failed",
            headers=DEFAULT_HEADERS_TOKEN,
            timeout=10
        )
        print(f"✅ Status Code: {res.status_code}")
        return {"status": res.status_code}
    except Exception as e:
        print(f"❌ Failed to report failure for ULID {ulid}: {e}")
        return {"status": 500}


def update_paper_availability(mac_address,paper_status):
    params = {
    'mac': mac_address,
    'paper_availability': PRINTER_PAPER_STATUS[paper_status],
    }
    res = requests.patch(f"{HOST}/api/v1/admin/printers/lan/network-printers/paper-availability",params=params, headers=DEFAULT_HEADERS_TOKEN,timeout=10)
    print(res.status_code)
    return({
        "status":res.status_code,
        "data":res.json()
        })

def update_printer_status(data):
    printers_update_data = data
    res = requests.patch(f"{HOST}/api/v1/admin/printers/lan/network-printers/update", headers=DEFAULT_HEADERS_TOKEN,data=json.dumps(printers_update_data),timeout=10)
    print(res.status_code)
    return({
        "status":res.status_code,
        "data":res.json()
        })


# ----------------------- API HANDLERS -----------------------  
    
if __name__ == "__main__":
    print(get_available_printers())

