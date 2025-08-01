import os
import sys
import clr

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

from StarMicronics.StarIO import Factory, PortException
from enum import Enum
from typing import List, Dict, Optional, Callable, Any

class StarResultCode:
    Succeeded = 0
    ErrorFailed = -1
    ErrorInUse = -2
    ErrorPaperPresent = -3

class Result(Enum):
    Success = 0
    ErrorUnknown = 1
    ErrorOpenPort = 2
    ErrorBeginCheckedBlock = 3
    ErrorEndCheckedBlock = 4
    ErrorWritePort = 5
    ErrorReadPort = 6

class PeripheralStatus(Enum):
    Invalid = 0
    Impossible = 1
    Connect = 2
    Disconnect = 3

class CommunicationResult:
    def __init__(self, result=Result.ErrorUnknown, code=StarResultCode.ErrorFailed):
        self.result = result
        self.code = code

def send_commands(commands: bytes, port_name: str, port_settings: str, timeout: int) -> CommunicationResult:
    result = Result.ErrorUnknown
    code = StarResultCode.ErrorFailed
    port = None
    try:
        result = Result.ErrorOpenPort
        port = Factory.I.GetPort(port_name, port_settings, timeout)
        result = Result.ErrorBeginCheckedBlock
        status = port.BeginCheckedBlock()
        if status.Offline:
            message = "Printer is Offline."
            if status.ReceiptPaperEmpty:
                message += "\nPaper is Empty."
            if status.CoverOpen:
                message += "\nCover is Open."
            raise PortException(message)
        result = Result.ErrorWritePort
        commands_length = len(commands)
        written_length = port.WritePort(commands, 0, commands_length)
        if written_length != commands_length:
            raise PortException("WritePort failed.")
        result = Result.ErrorEndCheckedBlock
        status = port.EndCheckedBlock()
        if status.Offline:
            message = "Printer is Offline."
            if status.ReceiptPaperEmpty:
                message += "\nPaper is Empty."
            if status.CoverOpen:
                message += "\nCover is Open."
            raise PortException(message)
        result = Result.Success
        code = StarResultCode.Succeeded
    except PortException as ex:
        code = ex.ErrorCode
    finally:
        if port:
            Factory.I.ReleasePort(port)
    return CommunicationResult(result, code)
