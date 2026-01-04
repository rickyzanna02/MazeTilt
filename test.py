from pythonosc.udp_client import SimpleUDPClient

client = SimpleUDPClient("127.0.0.1", 9001)
client.send_message("/bouncing", 1)