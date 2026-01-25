import time
import math
import threading
from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import ThreadingOSCUDPServer


class AccelController:
    """    
    Reads x,y,z via OSC (Pure Data) and converts them to tilt_x_deg / tilt_z_deg.
    Calibration and smoothing are performed.
    """
    def __init__(self,
                 osc_ip="0.0.0.0",
                 osc_port=4444,
                 calib_samples=60,
                 smooth=0.20,
                 deadzone_deg=0.6):

        # ---- OSC state ----
        self._osc_x = None
        self._osc_y = None
        self._osc_z = None
        self._last_xyz = None

        # ---- Setup OSC server ----
        dispatcher = Dispatcher()
        dispatcher.map("/a0", self._on_x)
        dispatcher.map("/a1", self._on_y)
        dispatcher.map("/a2", self._on_z)

        self.server = ThreadingOSCUDPServer(
            (osc_ip, osc_port),
            dispatcher
        )

        self._osc_thread = threading.Thread(
            target=self.server.serve_forever,
            daemon=True
        )
        self._osc_thread.start()

        # ---- Calibration ----
        self.calib_samples = calib_samples
        self._calib_count = 0
        self._sumx = 0.0
        self._sumy = 0.0
        self._sumz = 0.0
        self.ox = 0.0
        self.oy = 0.0
        self.oz = 0.0
        self.calibrated = False

        # ---- Filtering ----
        self.smooth = smooth
        self.deadzone_deg = deadzone_deg

        self.tilt_x_deg = 0.0
        self.tilt_z_deg = 0.0

    # =========================================================
    # OSC callbacks
    # =========================================================
    def _on_x(self, addr, *args):
        if not args:
            return
        self._osc_x = float(args[0])
        self._update_last_xyz()

    def _on_y(self, addr, *args):
        if not args:
            return
        self._osc_y = float(args[0])
        self._update_last_xyz()

    def _on_z(self, addr, *args):
        if not args:
            return
        self._osc_z = float(args[0])
        self._update_last_xyz()


    def _update_last_xyz(self):
        if self._osc_x is None or self._osc_y is None or self._osc_z is None:
            return
        self._last_xyz = (self._osc_x, self._osc_y, self._osc_z)

    # =========================================================
    # API identical to the serial version
    # =========================================================
    def close(self):
        try:
            self.server.shutdown()
        except Exception:
            pass

    def read_latest_xyz(self):
        """
        Non blocking: returns the last received OSC value.
        """
        return self._last_xyz
    
    def update(self):
        xyz = self.read_latest_xyz()
        if xyz is None:
            return (self.tilt_x_deg, self.tilt_z_deg)

        x, y, z = xyz

        # Initial offset calibration
        if not self.calibrated:
            self._sumx += x
            self._sumy += y
            self._sumz += z
            self._calib_count += 1
            if self._calib_count >= self.calib_samples:
                self.ox = self._sumx / self._calib_count
                self.oy = self._sumy / self._calib_count
                self.oz = self._sumz / self._calib_count
                self.calibrated = True
            return (self.tilt_x_deg, self.tilt_z_deg)

        # Remove offset
        ax = x - self.ox
        ay = y - self.oy
        az = z

        roll_deg  = math.degrees(math.atan2(ax, math.sqrt(ay*ay + az*az)))
        pitch_deg = math.degrees(math.atan2(ay, math.sqrt(ax*ax + az*az)))

        target_tilt_x = -pitch_deg
        target_tilt_z = roll_deg

        # Deadzone
        if abs(target_tilt_x) < self.deadzone_deg:
            target_tilt_x = 0.0
        if abs(target_tilt_z) < self.deadzone_deg:
            target_tilt_z = 0.0

        # Smoothing
        a = self.smooth
        self.tilt_x_deg = (1 - a) * self.tilt_x_deg + a * target_tilt_x
        self.tilt_z_deg = (1 - a) * self.tilt_z_deg + a * target_tilt_z

        return (self.tilt_x_deg, self.tilt_z_deg)