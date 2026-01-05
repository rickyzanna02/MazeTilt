import serial
import time
ser = serial.Serial("COM4", 115200, timeout=0.01)

def leggi_accelerometro():
    try:
        line = ser.readline().decode().strip()
        if line:
            x, y, z = map(int, line.split(','))
            return x, y, z
    except:
        pass
    return None

def vibra():
    ser.write(b'V')


if __name__ == "__main__":
    print("Lettura accelerometro e test vibrazione")
    for _ in range(10):
        acc = leggi_accelerometro()
        if acc:
            print(f"Accelerometro: x={acc[0]} y={acc[1]} z={acc[2]}")
        else:
            print("Nessun dato ricevuto")
        time.sleep(0.5)

    print("Test vibrazione")
    vibra()
    print("Vibrazione inviata")