import serial
import time

PORT = "COM4"          # Windows esempio
# PORT = "/dev/ttyACM0"  # Linux tipico
# PORT = "/dev/tty.usbmodem12345"  # macOS tipico

BAUD = 115200

ser = serial.Serial(PORT, BAUD, timeout=0.1)
time.sleep(2)  # tempo per reset USB/seriale

def read_accel():
    line = ser.readline().decode("utf-8", errors="ignore").strip()
    if not line:
        return None
    parts = line.split(",")
    if len(parts) < 2:
        return None
    x = int(parts[0])
    y = int(parts[1])
    z = int(parts[2]) if len(parts) > 2 else 0
    return x, y, z

while True:
    v = read_accel()
    if v:
        print(v)