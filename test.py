from pythonosc.udp_client import SimpleUDPClient
import time

boom = SimpleUDPClient("127.0.0.1", 9001)
bouncing = SimpleUDPClient("127.0.0.1", 9000)
boom.send_message("/boom", 1)
time.sleep(0.5)
bouncing.send_message("/bouncing", 1)