import sys
import math
import time
import serial
import pygame
from pygame.locals import *

from OpenGL.GL import *
from OpenGL.GLU import *

#audio OSC
from pythonosc.udp_client import SimpleUDPClient

bouncing = SimpleUDPClient("127.0.0.1", 9000)
boom = SimpleUDPClient("127.0.0.1", 9001)
rolling = SimpleUDPClient("127.0.0.1", 9002)

MAX_ROLL_SPEED = 8.0   # da tarare, va bene come punto di partenza
ROLL_ON_THRESHOLD = 0.05


# ---------------------------------------------------
# CONFIGURAZIONE GENERALE
# ---------------------------------------------------
WIN_WIDTH, WIN_HEIGHT = 1000, 700
FPS = 60

MAZE_WIDTH = 20.0
MAZE_DEPTH = 30.0

BALL_RADIUS = 0.6
GRAVITY = 15.0
FRICTION = 0.995

MAX_TILT_DEG = 18.0
TILT_STEP = 0.8

WALL_RESTITUTION = 0.80
WALL_TANGENTIAL = 0.96

START_POS = (0.0, -(MAZE_DEPTH / 2.0) + 3.0)  # (x, z)
START_LIVES = 3

# Buchi: (x, z, r)
HOLES = [
    (-5.0, -6.0, 1.0),
    (3.5, -1.0, 1.0),
    (4.0, 13.0, 1.0),
    (-2.5, 10.0, 1.0),
]

# Traguardo: rettangolo sul piano XZ (x, z, w, d)
GOAL_RECT = (MAZE_WIDTH / 2.0 - 3.0, MAZE_DEPTH / 2.0 - 3.5, 2.2, 2.2)


# ---------------------------------------------------
# UTILS
# ---------------------------------------------------
def clamp(v, vmin, vmax):
    return max(vmin, min(vmax, v))


def point_in_rect(px, pz, rect):
    x, z, w, d = rect
    return (x <= px <= x + w) and (z <= pz <= z + d)


# ---------------------------------------------------
# PALLINA
# ---------------------------------------------------
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


# ---------------------------------------------------
# LABIRINTO
# ---------------------------------------------------
class Maze:
    def __init__(self):
        self.walls = []
        self._build_maze()

    def _build_maze(self):
        w = MAZE_WIDTH
        d = MAZE_DEPTH
        t = 0.7

        self.walls = []

        # -------------------------
        # BORDI (come prima)
        # -------------------------
        self.walls.append((-w / 2.0, -d / 2.0, w, t))             # vicino
        self.walls.append((-w / 2.0, d / 2.0 - t, w, t))          # lontano
        self.walls.append((-w / 2.0, -d / 2.0, t, d))             # sinistra
        self.walls.append((w / 2.0 - t, -d / 2.0, t, d))          # destra

        # Area interna utile (per non sforare)
        xmin = -w / 2.0 + t
        xmax =  w / 2.0 - t
        zmin = -d / 2.0 + t
        zmax =  d / 2.0 - t

      
        self.walls.append((xmin + 0.0, zmin + 6.0, (xmax - xmin) - 6.0, t))
        self.walls.append((xmax - 4.0, zmin + 6.0, t, 10.0))
        self.walls.append((xmin + 4.0, zmin + 16.0, (xmax - xmin) - 4.0, t))
        self.walls.append((xmin + 4.0, zmin + 16.0, t, 8.0))
        self.walls.append((xmax - 8.0, zmax - 9.0, 5.0, t))


    def draw(self):
        # piano
        glColor3f(0.86, 0.86, 0.86)
        glBegin(GL_QUADS)
        glVertex3f(-MAZE_WIDTH / 2, 0, -MAZE_DEPTH / 2)
        glVertex3f(MAZE_WIDTH / 2, 0, -MAZE_DEPTH / 2)
        glVertex3f(MAZE_WIDTH / 2, 0, MAZE_DEPTH / 2)
        glVertex3f(-MAZE_WIDTH / 2, 0, MAZE_DEPTH / 2)
        glEnd()

        # traguardo (patch verde sul piano)
        gx, gz, gw, gd = GOAL_RECT
        glColor3f(0.2, 0.8, 0.2)
        glBegin(GL_QUADS)
        glVertex3f(gx, 0.01, gz)
        glVertex3f(gx + gw, 0.01, gz)
        glVertex3f(gx + gw, 0.01, gz + gd)
        glVertex3f(gx, 0.01, gz + gd)
        glEnd()

        # buchi (dischi scuri)
        glColor3f(0.12, 0.12, 0.12)
        for (hx, hz, r) in HOLES:
            draw_disk(hx, 0.01, hz, r, segments=24)

        # muri
        glColor3f(0.20, 0.20, 0.20)
        wall_height = 1
        for (x, z, w, d) in self.walls:
            x1, x2 = x, x + w
            z1, z2 = z, z + d

            glBegin(GL_QUADS)

            # top
            glVertex3f(x1, wall_height, z1)
            glVertex3f(x2, wall_height, z1)
            glVertex3f(x2, wall_height, z2)
            glVertex3f(x1, wall_height, z2)

            # front
            glVertex3f(x1, 0, z1)
            glVertex3f(x2, 0, z1)
            glVertex3f(x2, wall_height, z1)
            glVertex3f(x1, wall_height, z1)

            # back
            glVertex3f(x1, 0, z2)
            glVertex3f(x2, 0, z2)
            glVertex3f(x2, wall_height, z2)
            glVertex3f(x1, wall_height, z2)

            # left
            glVertex3f(x1, 0, z1)
            glVertex3f(x1, 0, z2)
            glVertex3f(x1, wall_height, z2)
            glVertex3f(x1, wall_height, z1)

            # right
            glVertex3f(x2, 0, z1)
            glVertex3f(x2, 0, z2)
            glVertex3f(x2, wall_height, z2)
            glVertex3f(x2, wall_height, z1)

            glEnd()

    def handle_collisions(self, ball: Ball):
        collided = False

        for (x, z, w, d) in self.walls:
            closest_x = clamp(ball.x, x, x + w)
            closest_z = clamp(ball.z, z, z + d)

            dx = ball.x - closest_x
            dz = ball.z - closest_z
            dist2 = dx * dx + dz * dz

            if dist2 < BALL_RADIUS * BALL_RADIUS:
                collided = True   # COLLISIONE

                dist = math.sqrt(dist2) if dist2 != 0 else 1e-6
                overlap = BALL_RADIUS - dist

                nx = dx / dist
                nz = dz / dist

                ball.x += nx * overlap
                ball.z += nz * overlap

                vdotn = ball.vx * nx + ball.vz * nz
                vnx = vdotn * nx
                vnz = vdotn * nz
                vtx = ball.vx - vnx
                vtz = ball.vz - vnz

                ball.vx = (-vnx * WALL_RESTITUTION) + (vtx * WALL_TANGENTIAL)
                ball.vz = (-vnz * WALL_RESTITUTION) + (vtz * WALL_TANGENTIAL)

        return collided



# ---------------------------------------------------
# OPENGL HELPERS
# ---------------------------------------------------
def draw_sphere(radius, slices=18, stacks=18):
    quad = gluNewQuadric()
    gluSphere(quad, radius, slices, stacks)
    gluDeleteQuadric(quad)


def draw_disk(cx, cy, cz, r, segments=24):
    glBegin(GL_TRIANGLE_FAN)
    glVertex3f(cx, cy, cz)
    for i in range(segments + 1):
        a = (i / segments) * 2.0 * math.pi
        glVertex3f(cx + math.cos(a) * r, cy, cz + math.sin(a) * r)
    glEnd()


def init_opengl():
    glEnable(GL_DEPTH_TEST)

    # ✅ Niente illuminazione: colori costanti, non cambia con inclinazione
    glDisable(GL_LIGHTING)
    glDisable(GL_LIGHT0)

    # (opzionale) disabilita anche cose che possono interferire
    glDisable(GL_COLOR_MATERIAL)
    glDisable(GL_NORMALIZE)

    # sfondo più chiaro
    glClearColor(0.85, 0.90, 0.98, 1.0)

    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(50.0, WIN_WIDTH / WIN_HEIGHT, 0.1, 200.0)
    glMatrixMode(GL_MODELVIEW)



def setup_fixed_camera_handheld():
    # un po' più alta (così con tilt su non perdi il labirinto)
    eye_x, eye_y, eye_z = (0.0, 28.0, 25)
    center_x, center_y, center_z = (0.0, 0.0, 0.0)
    up_x, up_y, up_z = (0.0, 1.0, 0.0)

    gluLookAt(eye_x, eye_y, eye_z,
              center_x, center_y, center_z,
              up_x, up_y, up_z)


# ---------------------------------------------------
# UI 2D OVERLAY (Pygame sopra OpenGL)
# ---------------------------------------------------
def draw_overlay_text(screen, font, lines, x=15, y=15):
    # disegna testo 2D usando Pygame (sopra OpenGL)
    yy = y
    for line in lines:
        surf = font.render(line, True, (10, 10, 10))
        screen.blit(surf, (x, yy))
        yy += surf.get_height() + 4


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

        # Evita divisioni strane se az ~ 0
        # Angoli da accelerazione (approssimazione statica)
        # roll  ~ inclinazione sx/dx (usa asse X rispetto a Z)
        roll  = math.degrees(math.atan2(ax, az if abs(az) > 1e-6 else 1e-6))
        # pitch ~ inclinazione avanti/indietro (usa asse Y rispetto a Z)
        pitch = math.degrees(math.atan2(ay, az if abs(az) > 1e-6 else 1e-6))

        # ---- Mappa sui tilt del tuo gioco ----
        # Nel tuo rendering:
        #   glRotatef(tilt_x_deg, 1,0,0)  (pitch)
        #   glRotatef(-tilt_z_deg, 0,0,1) (roll)
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
        self.ser.write(b'V')



# ---------------------------------------------------
# MAIN
# ---------------------------------------------------
def main():
    pygame.init()
    screen = pygame.display.set_mode((WIN_WIDTH, WIN_HEIGHT), DOUBLEBUF | OPENGL)
    pygame.display.set_caption("Labirinto 3D – vite, buchi, traguardo")
    clock = pygame.time.Clock()

    accel = AccelController(port="COM4", baud=115200, timeout=0.0)

    init_opengl()

    maze = Maze()
    ball = Ball(*START_POS)

    lives = START_LIVES
    state = "PLAY"  # PLAY, WIN, GAME_OVER

    tilt_x_deg = 0.0
    tilt_z_deg = 0.0

    running = True
    rolling_on = False
    while running:
        dt = clock.tick(FPS) / 1000.0

        for event in pygame.event.get():
            if event.type == QUIT:
                running = False

        keys = pygame.key.get_pressed()

        # Restart dopo win/gameover con R
        if keys[K_r] and state in ("WIN", "GAME_OVER"):
            lives = START_LIVES
            state = "PLAY"
            ball.reset()
            tilt_x_deg = 0.0
            tilt_z_deg = 0.0
            accel.tilt_x_deg = 0.0
            accel.tilt_z_deg = 0.0

        # Reset soft (SPACE) solo durante gioco
        if keys[K_SPACE] and state == "PLAY":
            ball.reset()
            tilt_x_deg = 0.0
            tilt_z_deg = 0.0
            accel.tilt_x_deg = 0.0
            accel.tilt_z_deg = 0.0

        if state == "PLAY":
            # --- INPUT DA ACCELEROMETRO ---
            tilt_x_deg, tilt_z_deg = accel.update()

            tilt_x_deg = clamp(tilt_x_deg, -MAX_TILT_DEG, MAX_TILT_DEG)
            tilt_z_deg = clamp(tilt_z_deg, -MAX_TILT_DEG, MAX_TILT_DEG)

            # fisica + collisioni
            ball.update(dt, tilt_x_deg, tilt_z_deg)
            hit_wall = maze.handle_collisions(ball)

            # ---------------------------------------------------
            # ROLLING SOUND (ON/OFF + VELOCITY)
            # ---------------------------------------------------

            # velocità reale della pallina
            speed = math.sqrt(ball.vx * ball.vx + ball.vz * ball.vz)

            if speed > ROLL_ON_THRESHOLD:
                # accendi rolling se era spento
                if not rolling_on:
                    rolling.send_message("/rolling/on", 1)
                    rolling_on = True

                # mappa velocità fisica -> velocity sonora
                rolling_velocity = min((speed / MAX_ROLL_SPEED) * 5.0, 5.0)

                rolling.send_message("/rolling/velocity", rolling_velocity)

            else:
                # spegni rolling se la pallina è ferma
                if rolling_on:
                    rolling.send_message("/rolling/on", 0)
                    rolling_on = False

            if hit_wall:
                bouncing.send_message("/bouncing", 1)
                accel.vibra()

            # caduta nei buchi
            fell = False
            for (hx, hz, r) in HOLES:
                if math.hypot(ball.x - hx, ball.z - hz) < (r - BALL_RADIUS * 0.25):
                    fell = True
                    boom.send_message("/boom", 1)
                    break

            if fell:
                lives -= 1
                if lives <= 0:
                    state = "GAME_OVER"
                    boom.send_message("/boom", 1)
                    rolling.send_message("/rolling/on", 0)
                    rolling_on = False
                else:
                    ball.reset()
                    tilt_x_deg = 0.0
                    tilt_z_deg = 0.0
                    accel.tilt_x_deg = 0.0
                    accel.tilt_z_deg = 0.0
                    boom.send_message("/boom", 1)

            # vittoria
            if point_in_rect(ball.x, ball.z, GOAL_RECT):
                state = "WIN"
                boom.send_message("/boom", 1)
                rolling.send_message("/rolling/on", 0)
                rolling_on = False

        # -------- RENDER 3D --------
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()
        setup_fixed_camera_handheld()

        glPushMatrix()
        glRotatef(tilt_x_deg, 1, 0, 0)
        glRotatef(-tilt_z_deg, 0, 0, 1)

        maze.draw()

        glPushMatrix()
        glTranslatef(ball.x, BALL_RADIUS, ball.z)
        glColor3f(1.0, 0.2, 0.2)
        draw_sphere(BALL_RADIUS)
        glPopMatrix()

        glPopMatrix()
        pygame.display.flip()

    accel.close()
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()

