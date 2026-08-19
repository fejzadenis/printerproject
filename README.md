# AskyPrint

A Windows desktop client that turns incoming orders into printed receipts. It finds
thermal printers on its own — over USB, the local network or Bonjour/Zeroconf — keeps a
print queue running in the background from the system tray, and speaks both ESC/POS and
StarPRNT so it works across printer families.

## Features

- **Automatic printer discovery** — separate detection paths for USB devices, network
  scanning and Zeroconf, plus a dedicated StarPRNT discovery service.
- **Two protocols** — receipts are composed as ESC/POS and translated to StarPRNT when
  the target printer requires it.
- **Background printing** — a worker thread drains a print queue, so the interface stays
  responsive while jobs are sent to the printer.
- **Tray application** — runs minimised in the system tray with a single-instance lock,
  so only one copy can be active at a time.
- **Authenticated backend** — signs in against the AskyPrint API and stores its token
  and settings under the user's `AppData` directory.
- **Receipt content** — barcode and QR code generation alongside text and images.

## Stack

| Layer | Technology |
| --- | --- |
| Interface | PyQt5 (Qt Designer `.ui` files) |
| Printing | python-escpos, StarPRNT SDK via pythonnet |
| Discovery | pyusb, pyserial, zeroconf, WMI, getmac |
| Codes | python-barcode, qrcode |
| Packaging | PyInstaller |

## Layout

```
main.py       application entry point, tray icon, print queue
ui/           Qt Designer screens: login, main window, printer selection, settings
utils/        printer detection, ESC/POS→StarPRNT translation, API client, settings
StarPRNTSDK/  vendor SDK for Star printers
```

## Running

```bash
pip install -r requirements.txt
```

```bash
python main.py
```

Windows only — the application depends on `pywin32`, WMI and the Star SDK.
