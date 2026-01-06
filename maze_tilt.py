import math
import time
import serial
import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
from pythonosc.udp_client import SimpleUDPClient

bouncing = SimpleUDPClient("127.0.0.1", 9000)
boom = SimpleUDPClient("127.0.0.1", 9001)
rolling = SimpleUDPClient("127.0.0.1", 9002)

MAX_ROLL_SPEED = 8.0   
ROLL_ON_THRESHOLD = 0.05
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
HOLE_VIBRATION_MAX = 220   # PWM max
HOLE_VIBRATION_MIN = 40    # min vibration
GOAL_RECT = (MAZE_WIDTH / 2.0 - 3.0, MAZE_DEPTH / 2.0 - 3.5, 2.2, 2.2)# Goal: rect in XZ plane (x, z, w, d)


LEVELS = {

    1: {
        "walls": [            
            # muro verticale dall’alto, x = 7 da sx, lungo 15
        ("min", "max", 10.0, -29.0, "T", 15.0),

        # muro orizzontale da sx, z = 25 dall’alto, lungo 10
        ("min", "max", 0.0, -5.0, 10.0, "T"),
        ],
        "holes": [              
            (3.0, 13.0, 1.0),
        ]
    },

    2: {
        "walls": [            
            ("min", "min", 0.0, 6.0, 15.0, "T"),            
            ("max", "min", -15.0, 12.0, 15.0, "T"),            
            ("min", "min", 0.0, 18.0, 15.0, "T"),            
            ("max", "min", -15.0, 24.0, 15.0, "T"),
        ],
        "holes": [           
            (-2.0, -5.0, 1.0),
            (-2.0, 7.0, 1.0),
            (3.0, 14.0, 1.0),
        ]
    },

    3: {
        "walls": [
            ("min", "min", 0.0, 6.0, "FULL-8", "T"), 
            ("max", "min", -4.0, 6.0, "T", 10.0),
            ("min", "min", 4.0, 16.0, "FULL-4", "T"),
            ("min", "min", 4.0, 16.0, "T", 8.0),
            ("max", "max", -8.0, -9.0, 5.0, "T"),
        ],
        "holes": [
            (-5.0, -6.0, 1.0),
            (3.5, -1.0, 1.0),
            (4.0, 13.0, 1.0),
            (-2.5, 10.0, 1.0),
        ]
    }

    
}


# ---------------------------------------------------
# UTILS
# ---------------------------------------------------
def clamp(v, vmin, vmax):
    return max(vmin, min(vmax, v))

def point_in_rect(px, pz, rect):
    x, z, w, d = rect
    return (x <= px <= x + w) and (z <= pz <= z + d)


# ---------------------------------------------------
# BALL
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
# MAZE
# ---------------------------------------------------
class Maze:
    def __init__(self, level=1):
        self.level = level
        self.walls = []
        self.holes = []
        self.holes_area = []
        self._build_maze()

    def add_internal_walls(self, wall_defs, xmin, xmax, zmin, zmax, t):
        for (x_ref, z_ref, dx, dz, w, d) in wall_defs:
            x0 = xmin if x_ref == "min" else xmax
            z0 = zmin if z_ref == "min" else zmax

            if isinstance(w, str) and w.startswith("FULL"):
                offset = float(w.split("-")[1])
                w = (xmax - xmin) - offset
            if w == "T":
                w = t

            if d == "T":
                d = t

            x = x0 + dx
            z = z0 + dz

            self.walls.append((x, z, w, d))



    def _build_maze(self):
        w = MAZE_WIDTH
        d = MAZE_DEPTH
        t = 0.7

        self.walls = []

        # -------------------------
        # BORDER
        # -------------------------
        self.walls.append((-w / 2.0, -d / 2.0, w, t))             # near
        self.walls.append((-w / 2.0, d / 2.0 - t, w, t))          # far
        self.walls.append((-w / 2.0, -d / 2.0, t, d))             # left
        self.walls.append((w / 2.0 - t, -d / 2.0, t, d))          # right

        # Area interna utile (per non sforare)
        xmin = -w / 2.0 + t
        xmax =  w / 2.0 - t
        zmin = -d / 2.0 + t
        zmax =  d / 2.0 - t

        level_data = LEVELS.get(self.level, LEVELS[1])

        # ---- muri ----
        self.add_internal_walls(
            level_data["walls"],
            xmin, xmax, zmin, zmax, t
        )

        # ---- buchi ----
        self.holes = level_data["holes"]

        # ---- hole areas (derivate automaticamente) ----
        self.holes_area = [
            (x, z, r * 3.0) for (x, z, r) in self.holes
        ]

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
        for (hx, hz, r) in self.holes:
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
    glDisable(GL_LIGHTING) #  No lighting: constant colors, no change with inclination
    glDisable(GL_LIGHT0)
    glClearColor(0.85, 0.90, 0.98, 1.0) # lighter background
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
# ---------------------------------------------------
# UI 2D HUD (OPENGL SAFE)
# ---------------------------------------------------
def draw_text_gl(x, y, text, font, color=(10, 10, 10)):
    text_surface = font.render(text, True, color)
    text_data = pygame.image.tostring(text_surface, "RGBA", True)
    width, height = text_surface.get_size()

    glWindowPos2d(x, WIN_HEIGHT - y - height)
    glDrawPixels(width, height, GL_RGBA, GL_UNSIGNED_BYTE, text_data)


def draw_hud_gl(font, level, max_level, lives, state):
    y = 20
    line_h = 24

    draw_text_gl(20, y, f"Level: {level} / {max_level}", font)
    y += line_h
    draw_text_gl(20, y, f"Lives: {lives}", font)
    y += line_h

    if state == "GAME_OVER":
        y += line_h
        draw_text_gl(20, y, "GAME OVER (R to restart)", font, (180, 0, 0))
    elif state == "WIN":
        y += line_h
        draw_text_gl(20, y, "YOU WIN! (R to restart)", font, (0, 120, 0))



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

        # roll  ~ inclinazione sx/dx (usa asse X rispetto a Z)
        roll  = math.degrees(math.atan2(ax, az if abs(az) > 1e-6 else 1e-6))
        # pitch ~ inclinazione avanti/indietro (usa asse Y rispetto a Z)
        pitch = math.degrees(math.atan2(ay, az if abs(az) > 1e-6 else 1e-6))

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

# ---------------------------------------------------
# MAIN
# ---------------------------------------------------
def main():
    pygame.init()
    ###
    font = pygame.font.SysFont("Arial", 20, bold=True)

    current_level = 1
    max_level = max(LEVELS.keys())

    maze = Maze(level=current_level)
    ball = Ball(*START_POS)

    lives = START_LIVES
    state = "PLAY"   # PLAY, WIN, GAME_OVER

    ##



    screen = pygame.display.set_mode((WIN_WIDTH, WIN_HEIGHT), DOUBLEBUF | OPENGL)
    pygame.display.set_caption("Labirinto 3D – vite, buchi, traguardo")
    clock = pygame.time.Clock()

    accel = AccelController(port="COM4", baud=115200, timeout=0.0)

    init_opengl()

    current_level = 1
    max_level = max(LEVELS.keys())

    maze = Maze(level=1)
    ball = Ball(*START_POS)


    lives = START_LIVES
    state = "PLAY"  # PLAY, WIN, GAME_OVER

    tilt_x_deg = 0.0
    tilt_z_deg = 0.0

    running = True
    rolling_on = False

    def reset_tilt(accel):
        accel.tilt_x_deg = 0.0
        accel.tilt_z_deg = 0.0
        return 0.0, 0.0   

    def load_level(level):
        nonlocal maze, ball
        maze = Maze(level=level)
        ball.reset()
        reset_tilt(accel) 

    while running:
        dt = clock.tick(FPS) / 1000.0

        for event in pygame.event.get():
            if event.type == QUIT:
                running = False

        keys = pygame.key.get_pressed()

        # Restart dopo win/gameover con R
        if keys[K_r] and state in ("WIN", "GAME_OVER"):
            lives = START_LIVES
            current_level = 1
            maze = Maze(level=current_level)
            ball.reset()
            reset_tilt(accel)
            state = "PLAY"


        # Reset soft (SPACE) solo durante gioco
        if keys[K_SPACE] and state == "PLAY":
            ball.reset()
            

            reset_tilt(accel)

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

            # ---------------------------------------------------
            # HOLE AREA → VIBRAZIONE CONTINUA PROPORZIONALE
            # ---------------------------------------------------

            hole_vibration = 0
            inside_area = False

            for (hx, hz, area_r) in maze.holes_area:
                dist = math.hypot(ball.x - hx, ball.z - hz)

                if dist < area_r:
                    inside_area = True

                    # trova raggio del buco vero
                    hole_r = next(r for (x, z, r) in maze.holes if x == hx and z == hz)

                    # normalizza distanza (0 = centro buco, 1 = bordo area)
                    t = clamp((dist - hole_r) / (area_r - hole_r), 0.0, 1.0)

                    # inverti: più vicino → più vibrazione
                    intensity = HOLE_VIBRATION_MIN + (1.0 - t) * (HOLE_VIBRATION_MAX - HOLE_VIBRATION_MIN)

                    hole_vibration = int(intensity)
                    break

            # invio comando al teensy
            if inside_area:
                accel.ser.write(f"H:{hole_vibration}\n".encode())
            else:
                accel.ser.write(b"H:0\n")



            # caduta nei buchi
            fell = False
            for (hx, hz, r) in maze.holes:
                if math.hypot(ball.x - hx, ball.z - hz) < (r - BALL_RADIUS * 0.25):
                    fell = True
                    boom.send_message("/boom", 1)
                    break

            if fell:
                lives -= 1
                boom.send_message("/boom", 1)
                if lives <= 0:
                    state = "GAME_OVER"                    
                    rolling.send_message("/rolling/on", 0)
                    rolling_on = False
                else:
                    ball.reset()                   
                    reset_tilt(accel)
                    

            # vittoria
            if point_in_rect(ball.x, ball.z, GOAL_RECT):
                boom.send_message("/boom", 1)
                rolling.send_message("/rolling/on", 0)
                rolling_on = False

                if current_level < max_level:
                    current_level += 1
                    maze = Maze(level=current_level)
                    ball.reset()
                    reset_tilt(accel)
                    state = "PLAY"
                else:
                    state = "WIN"



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

        # ---------- HUD OPENGL ----------
        glDisable(GL_DEPTH_TEST)

        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        draw_hud_gl(font, current_level, max_level, lives, state)

        glDisable(GL_BLEND)
        glEnable(GL_DEPTH_TEST)

        pygame.display.flip()




    accel.close()
    pygame.quit()
    

if __name__ == "__main__":
    main()

