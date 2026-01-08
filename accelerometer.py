import time
import serial
import math


class AccelController:
    """
    Legge x,y,z da seriale e li converte in tilt_x_deg / tilt_z_deg.
    - Calibra offset iniziale (board ferma) per azzerare.
    - Usa atan2 per ricavare pitch/roll.
    - Applica smoothing e deadzone.
    """
    def __init__(self, port="COM4", baud=115200, timeout=0.0,
                 calib_samples=60, smooth=0.20, deadzone_deg=0.6):
        self.ser = serial.Serial(port, baud, timeout=timeout)
        time.sleep(2)  # reset USB/seriale

        self.calib_samples = calib_samples
        self._calib_count = 0
        self._sumx = 0.0
        self._sumy = 0.0
        self._sumz = 0.0
        self.ox = 0.0
        self.oy = 0.0
        self.oz = 0.0
        self.calibrated = False

        self.smooth = smooth
        self.deadzone_deg = deadzone_deg

        self.tilt_x_deg = 0.0  # pitch (rotazione asse X nel tuo codice)
        self.tilt_z_deg = 0.0  # roll  (rotazione asse Z nel tuo codice)

        self._last_xyz = None

    def close(self):
        try:
            self.ser.close()
        except Exception:
            pass

    def _parse_line(self, line: str):
        parts = line.strip().split(",")
        if len(parts) < 2:
            return None
        try:
            x = int(parts[0])
            y = int(parts[1])
            z = int(parts[2]) if len(parts) > 2 else 0
            return (x, y, z)
        except ValueError:
            return None

    def read_latest_xyz(self):
        """
        Non blocca: legge tutte le righe disponibili e tiene l'ultima valida.
        """
        latest = None
        while True:
            raw = self.ser.readline()
            if not raw:
                break
            try:
                s = raw.decode("utf-8", errors="ignore")
            except Exception:
                continue
            v = self._parse_line(s)
            if v is not None:
                latest = v
        if latest is not None:
            self._last_xyz = latest
        return self._last_xyz

    def update(self):
        """
        Aggiorna tilt_x_deg / tilt_z_deg.
        Da chiamare una volta per frame.
        """
        xyz = self.read_latest_xyz()
        if xyz is None:
            return (self.tilt_x_deg, self.tilt_z_deg)

        x, y, z = xyz

        # ---- Calibrazione offset iniziale (tenere il sensore fermo) ----
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

       # ---- Rimuovi offset ----
        ax = x - self.ox
        ay = y - self.oy
        az = z - self.oz

        # ---- Rotazione 90° CLOCKWISE attorno a Z ----
        ax_z =  ay
        ay_z = -ax
        az_z =  az

        # ---- Rotazione 180° attorno all'asse X (come prima) ----
        ax_r =  ax_z
        ay_r = -ay_z
        az_r = -az_z


        roll  = math.degrees(math.atan2(ax_r, az_r if abs(az_r) > 1e-6 else 1e-6))
        pitch = math.degrees(math.atan2(ay_r, az_r if abs(az_r) > 1e-6 else 1e-6))

        # Target tilt
        target_tilt_x = pitch
        target_tilt_z = roll

        # Deadzone per non tremare quando "quasi fermo"
        if abs(target_tilt_x) < self.deadzone_deg:
            target_tilt_x = 0.0
        if abs(target_tilt_z) < self.deadzone_deg:
            target_tilt_z = 0.0

        # Smoothing (low-pass)
        a = self.smooth
        self.tilt_x_deg = (1 - a) * self.tilt_x_deg + a * target_tilt_x
        self.tilt_z_deg = (1 - a) * self.tilt_z_deg + a * target_tilt_z

        return (self.tilt_x_deg, self.tilt_z_deg)
    
    def vibra(self):
        self.ser.write(b'V\n') # comando vibrazione mandato al teensy