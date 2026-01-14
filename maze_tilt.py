import math
import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
from pythonosc.udp_client import SimpleUDPClient
import argparse
from levels import LEVELS
from ball import Ball
from maze import Maze
from accelerometer import AccelController

MAX_ROLL_SPEED = 8.0   
ROLL_ON_THRESHOLD = 0.05
COLLISION_SPEED_THRESHOLD = 0.15
WIN_WIDTH, WIN_HEIGHT = 1000, 700
FPS = 60
MAZE_WIDTH = 20.0
MAZE_DEPTH = 30.0
BALL_RADIUS = 0.6
GRAVITY = 15.0
FRICTION = 0.9985
MAX_TILT_DEG = 18.0
START_POS = (0.0, -(MAZE_DEPTH / 2.0) + 3.0)  # (x, z)
START_LIVES = 3
HOLE_VIBRATION_MAX = 220   # PWM max
HOLE_VIBRATION_MIN = 40    # min vibration
GOAL_RECT = (MAZE_WIDTH / 2.0 - 3.0, MAZE_DEPTH / 2.0 - 3.5, 2.2, 2.2)# Goal: rect in XZ plane (x, z, w, d)

# ---------------------------------------------------
# UTILS
# ---------------------------------------------------
def clamp(v, vmin, vmax):
    return max(vmin, min(vmax, v))

def point_in_rect(px, pz, rect):
    x, z, w, d = rect
    return (x <= px <= x + w) and (z <= pz <= z + d)

def draw_sphere(radius, slices=18, stacks=18):
    quad = gluNewQuadric()
    gluSphere(quad, radius, slices, stacks)
    gluDeleteQuadric(quad)

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


def draw_text_gl(x, y, text, font, color=(10, 10, 10)):
    text_surface = font.render(text, True, color)
    text_data = pygame.image.tostring(text_surface, "RGBA", True)
    width, height = text_surface.get_size()

    glWindowPos2d(x, WIN_HEIGHT - y - height)
    glDrawPixels(width, height, GL_RGBA, GL_UNSIGNED_BYTE, text_data)


def draw_hud_gl(font, level, max_level, lives, state, time_sec, wall_hits):
    y = 20
    line_h = 24

    draw_text_gl(20, y, f"Level: {level} / {max_level}", font)
    y += line_h
    draw_text_gl(20, y, f"Lives: {lives}", font)
    y += line_h
    draw_text_gl(20, y, f"Time: {time_sec:.1f} s", font)
    y += line_h
    draw_text_gl(20, y, f"Wall collisions: {wall_hits}", font)
    y += line_h

    if state == "GAME_OVER":
        y += line_h
        draw_text_gl(20, y, "GAME OVER (R to restart)", font, (180, 0, 0))
    elif state == "WIN":
        y += line_h
        draw_text_gl(20, y, "YOU WIN! (R to restart)", font, (0, 120, 0))


# ---------------------------------------------------
# MAIN
# ---------------------------------------------------
def main():
       
    parser = argparse.ArgumentParser(description="Labirinto 3D multimodale")
    parser.add_argument("--audio", action="store_true", help="Abilita audio OSC")
    parser.add_argument("--vibration", action="store_true", help="Abilita vibrazioni ERM")
    args = parser.parse_args()

    ENABLE_AUDIO = args.audio
    ENABLE_VIBRATION = args.vibration


    if ENABLE_AUDIO:
        bouncing = SimpleUDPClient("127.0.0.1", 9000)
        boom = SimpleUDPClient("127.0.0.1", 9001)
        rolling = SimpleUDPClient("127.0.0.1", 9002)
    else:
        bouncing = boom = rolling = None

    pygame.init()
    font = pygame.font.SysFont("Arial", 20, bold=True)
    current_level = 1
    max_level = max(LEVELS.keys())
    maze = Maze(level=current_level)
    ball = Ball(*START_POS)
    lives = START_LIVES
    start_time = None
    total_time = 0.0
    wall_collisions = 0
    state = "PLAY"   # PLAY, WIN, GAME_OVER
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
    start_time = pygame.time.get_ticks()
    tilt_x_deg = 0.0
    tilt_z_deg = 0.0
    running = True
    rolling_on = False

    def reset_tilt(accel):
        accel.tilt_x_deg = 0.0
        accel.tilt_z_deg = 0.0
        return 0.0, 0.0   

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
            wall_collisions = 0
            total_time = 0.0
            start_time = pygame.time.get_ticks()

        # Reset soft (SPACE) solo durante gioco
        if keys[K_SPACE] and state == "PLAY":
            ball.reset()
            reset_tilt(accel)

        if state == "PLAY" and start_time is not None:
            total_time = (pygame.time.get_ticks() - start_time) / 1000.0
            # --- INPUT DA ACCELEROMETRO ---
            tilt_x_deg, tilt_z_deg = accel.update()

            tilt_x_deg = clamp(tilt_x_deg, -MAX_TILT_DEG, MAX_TILT_DEG)
            tilt_z_deg = clamp(tilt_z_deg, -MAX_TILT_DEG, MAX_TILT_DEG)

            # fisica + collisioni
            ball.update(dt, tilt_x_deg, tilt_z_deg)
            speed = math.hypot(ball.vx, ball.vz)
            hit_wall = maze.handle_collisions(ball)
            if hit_wall and speed > COLLISION_SPEED_THRESHOLD:
                wall_collisions += 1

            # ---------------------------------------------------
            # ROLLING SOUND (ON/OFF + VELOCITY)
            # ---------------------------------------------------

            # velocità reale della pallina
            speed = math.sqrt(ball.vx * ball.vx + ball.vz * ball.vz)

            if speed > ROLL_ON_THRESHOLD:
                # accendi rolling se era spento
                if not rolling_on:
                    if ENABLE_AUDIO:
                        rolling.send_message("/rolling/on", 1)
                    rolling_on = True

                # mappa velocità fisica -> velocity sonora
                rolling_velocity = min((speed / MAX_ROLL_SPEED) * 5.0, 5.0)

                if ENABLE_AUDIO:
                    rolling.send_message("/rolling/velocity", rolling_velocity)

            else:
                # spegni rolling se la pallina è ferma
                if rolling_on:
                    if ENABLE_AUDIO:                        
                        rolling.send_message("/rolling/on", 0)
                    rolling_on = False

            if hit_wall and ENABLE_AUDIO:
                bouncing.send_message("/bouncing", 1)
            if hit_wall and ENABLE_VIBRATION:
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
                if ENABLE_VIBRATION:
                    accel.ser.write(f"H:{hole_vibration}\n".encode())
            else:
                if ENABLE_VIBRATION:
                    accel.ser.write(b"H:0\n")

            # caduta nei buchi
            fell = False
            for (hx, hz, r) in maze.holes:
                if math.hypot(ball.x - hx, ball.z - hz) < (r - BALL_RADIUS * 0.25):
                    fell = True
                    if ENABLE_AUDIO:
                        boom.send_message("/boom", 1)
                    break

            if fell:
                lives -= 1
                if ENABLE_AUDIO:
                    boom.send_message("/boom", 1)
                if lives <= 0:
                    state = "GAME_OVER"                    
                    if ENABLE_AUDIO:
                        rolling.send_message("/rolling/on", 0)
                    rolling_on = False
                else:
                    ball.reset()                   
                    reset_tilt(accel)                    

            # vittoria
            if point_in_rect(ball.x, ball.z, GOAL_RECT):
                if ENABLE_AUDIO:
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

        draw_hud_gl(font, current_level, max_level, lives, state, total_time, wall_collisions)

        glDisable(GL_BLEND)
        glEnable(GL_DEPTH_TEST)

        pygame.display.flip()

    if ENABLE_AUDIO:
        rolling.send_message("/rolling/on", 0)
    if ENABLE_VIBRATION:
        accel.ser.write(b"H:0\n")

    accel.close()
    pygame.quit()


if __name__ == "__main__":
    main()

