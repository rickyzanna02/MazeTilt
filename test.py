from pythonosc.udp_client import SimpleUDPClient
import time

# Configurazione OSC
IP = "127.0.0.1"
PORT = 9002

client = SimpleUDPClient(IP, PORT)

while True:
    client.send_message("/rolling/on", 1)
    time.sleep(3)
    client.send_message("/rolling/on", 0)
    time.sleep(3)