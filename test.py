from pythonosc.udp_client import SimpleUDPClient
import time

# Configurazione OSC
IP = "127.0.0.1"
PORT = 2222

client = SimpleUDPClient(IP, PORT)

while True:
    client.send_message("/V", 1)
    time.sleep(3)
    client.send_message("/V", 0)
    time.sleep(3)