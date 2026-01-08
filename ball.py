# ---------------------------------------------------
# BALL
# ---------------------------------------------------
import math

GRAVITY = 15.0
FRICTION = 0.995

class Ball:
    def __init__(self, x, z):
        self.start_x = x
        self.start_z = z
        self.x = float(x)
        self.z = float(z)
        self.vx = 0.0
        self.vz = 0.0

    def reset(self):
        self.x = float(self.start_x)
        self.z = float(self.start_z)
        self.vx = 0.0
        self.vz = 0.0

    def update(self, dt, tilt_x_deg, tilt_z_deg):
        tx = math.radians(tilt_x_deg)
        tz = math.radians(tilt_z_deg)

        ax = GRAVITY * math.sin(tz)
        az = GRAVITY * math.sin(tx)

        self.vx += ax * dt
        self.vz += az * dt

        self.vx *= FRICTION
        self.vz *= FRICTION

        self.x += self.vx * dt
        self.z += self.vz * dt