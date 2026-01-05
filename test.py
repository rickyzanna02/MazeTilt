import time
from pythonosc.udp_client import SimpleUDPClient

# OSC client verso Pure Data
rolling = SimpleUDPClient("127.0.0.1", 9002)

print("TEST rolling velocity")

# accendi rolling
print("ON")
rolling.send_message("/rolling/on", 1)
time.sleep(1.0)

# salita di velocity
print("Increase velocity")
for v in [0.2, 0.5, 1.0, 2.0, 3.0, 4.0]:
    print(f"velocity = {v}")
    rolling.send_message("/rolling/velocity", v)
    time.sleep(1.5)

# discesa di velocity
print("Decrease velocity")
for v in [3.0, 2.0, 1.0, 0.5, 0.2]:
    print(f"velocity = {v}")
    rolling.send_message("/rolling/velocity", v)
    time.sleep(1.5)

# spegni rolling
print("OFF")
rolling.send_message("/rolling/on", 0)

print("FINE TEST")
