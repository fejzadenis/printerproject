from PIL import Image
import os, json, sys
import subprocess

if hasattr(sys, '_MEIPASS'):
    # PyInstaller extracts files to _MEIPASS during runtime
    builder_path = os.path.join(sys._MEIPASS, 'StarPRNTSDK')
else:
    # Use the local directory during development
    script_dir = os.path.dirname(os.path.abspath(__file__))
    builder_path = os.path.join(script_dir, '..\\StarPRNTSDK')
builder_path = os.path.join(builder_path, 'StarCommandBuilder.exe')

image_files = []  # add this outside the function

def parse_escpos_stream(data: bytes, file_path: str, ulid):
    instructions = []
    i = 0
    buffer = b""
    
    def flush_text():
        nonlocal buffer
        if buffer:
            text = buffer.decode('ascii', errors='ignore')
            if text.strip():
                instructions.append({"type": "text", "value": text})
            buffer = b""

    while i < len(data):
        if data[i:i+2] == b'\x1b\x40':  # Initialize
            flush_text()
            instructions.append({"type": "init"})
            i += 2
        elif data[i:i+3] == b'\x1b\x45\x01':  # Bold on
            flush_text()
            instructions.append({"type": "bold_on"})
            i += 3
        elif data[i:i+3] == b'\x1b\x45\x00':  # Bold off
            flush_text()
            instructions.append({"type": "bold_off"})
            i += 3
        elif data[i:i+3] == b'\x1b\x2d\x01':  # Underline on
            flush_text()
            instructions.append({"type": "underline_on"})
            i += 3
        elif data[i:i+3] == b'\x1b\x2d\x00':  # Underline off
            flush_text()
            instructions.append({"type": "underline_off"})
            i += 3
        elif data[i:i+3] == b'\x1b\x4d\x00':  # Font A
            flush_text()
            instructions.append({"type": "font_a"})
            i += 3
        elif data[i:i+3] == b'\x1b\x4d\x01':  # Font B
            flush_text()
            instructions.append({"type": "font_b"})
            i += 3
        elif data[i:i+3] == b'\x1d\x21':  # Text scale
            flush_text()
            scale = data[i+2]
            # current_format["scale_w"] = (scale & 0x0F) + 1
            # current_format["scale_h"] = ((scale >> 4) & 0x0F) + 1
            instructions.append({"type": "scale", "value": scale})
            i += 3
        elif data[i:i+3] == b'\x1b\x61\x00':  # Align left
            flush_text()
            instructions.append({"type": "align", "value": "left"})
            i += 3
        elif data[i:i+3] == b'\x1b\x61\x01':  # Align center
            flush_text()
            instructions.append({"type": "align", "value": "center"})
            i += 3
        elif data[i:i+3] == b'\x1b\x61\x02':  # Align right
            flush_text()
            instructions.append({"type": "align", "value": "right"})
            i += 3
        elif data[i] == 0x0A:  # Line feed
            flush_text()
            instructions.append({"type": "feed", "value": 1})
            i += 1
        elif data[i:i+2] == b'\x1b\x64':  # ESC d n
            flush_text()
            n = data[i+2]
            instructions.append({"type": "feed", "value": n})
            i += 3
        elif data[i:i+2] == b'\x1b\x33':  # ESC 3 n - set line spacing
            flush_text()
            spacing = data[i+2]
            instructions.append({"type": "line_spacing", "value": spacing})
            i += 3
        elif data[i:i+3] == b'\x1d\x76\x30':  # Image GS v 0
            flush_text()
            mode = data[i+3]
            xL, xH, yL, yH = data[i+4], data[i+5], data[i+6], data[i+7]
            width = (xH << 8 | xL) * 8
            height = yH << 8 | yL
            size = (width // 8) * height
            raster = data[i+8:i+8+size]

            img = Image.new('1', (width, height), 1)
            for y in range(height):
                for x_byte in range(width // 8):
                    byte = raster[y * (width // 8) + x_byte]
                    for bit in range(8):
                        if byte & (0x80 >> bit):
                            img.putpixel((x_byte * 8 + bit, y), 0)

            img_path = f"{file_path}/{ulid}_{len(instructions)}.bmp"
            img.save(img_path)
            # img_path = os.path.abspath(img_path)
            image_files.append(img_path)
            instructions.append({"type": "image", "value": img_path})
            i += 8 + size
        elif data[i:i+2] == b'\x1d\x56':  # Cut
            flush_text()
            instructions.append({"type": "cut"})
            i += 3
            break
        else:
            buffer += bytes([data[i]])
            i += 1

    flush_text()
    return instructions, image_files

def write_json(file_path, instructions):
    with open(file_path, 'w') as f:
        json.dump(instructions, f, indent=2)

def run_builder(port_name: str, model_name: str, json_path: str) -> bytes:
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

    result = subprocess.run([builder_path, port_name, model_name, json_path], 
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, 
                            startupinfo=startupinfo,
                            creationflags=subprocess.CREATE_NO_WINDOW)
    if result.returncode != 0:
        return None
    print(result.stderr.decode())
    return result.stdout
