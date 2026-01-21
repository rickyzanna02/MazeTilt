import math
import pygame
from pygame.locals import *
from OpenGL.GL import *
from pythonosc.udp_client import SimpleUDPClient
import argparse
import csv
import os
from levels import LEVELS
from ball import Ball
from maze import Maze
from accelerometer import AccelController

MODALITA_MAP = {
    0: "Solo video",
    1: "Video + Audio",
    2: "Video + Audio + Vibrazione"
}

MAX_ROLL_SPEED = 16.0 
ROLL_ON_THRESHOLD = 0.05
COLLISION_SPEED_THRESHOLD = 0.15
WIN_WIDTH, WIN_HEIGHT = 1000, 700
FPS = 60
MAZE_WIDTH = 20.0
MAZE_DEPTH = 30.0
BALL_RADIUS = 0.6
GRAVITY = 50
FRICTION = 0.99
MAX_TILT_DEG = 18
START_POS = (0.0, -(MAZE_DEPTH / 2.0) + 3.0)  # (x, z)
START_LIVES = 3
HOLE_VIBRATION_MAX = 180   # PWM max
HOLE_VIBRATION_MIN = 40    # min vibration
GOAL_RECT = (MAZE_WIDTH / 2.0 - 3.0, MAZE_DEPTH / 2.0 - 3.5, 2.2, 2.2)# Goal: rect in XZ plane (x, z, w, d)


UI_BG_ALPHA = 160
PANEL_W, PANEL_H = 420, 320
PANEL_X = (WIN_WIDTH - PANEL_W) // 2
PANEL_Y = (WIN_HEIGHT - PANEL_H) // 2

INPUT_W, INPUT_H = 300, 32
INPUT_X = PANEL_X + 60
NAME_Y = PANEL_Y + 80
ATTEMPT_Y = PANEL_Y + 130

BUTTON_W, BUTTON_H = 140, 36
BUTTON_X = PANEL_X + (PANEL_W - BUTTON_W) // 2
BUTTON_Y = PANEL_Y + 260
LABEL_TO_INPUT_GAP = 30
FIELD_GAP = 80   # distanza tra Nome e Tentativo (label -> label)

NAME_LABEL_Y = PANEL_Y + 60
NAME_INPUT_Y = NAME_LABEL_Y + LABEL_TO_INPUT_GAP

ATT_LABEL_Y = NAME_LABEL_Y + FIELD_GAP
ATT_INPUT_Y = ATT_LABEL_Y + LABEL_TO_INPUT_GAP

def draw_input_panel(font, player_name, attempt, active_field):
    # sfondo scuro
    overlay = pygame.Surface((WIN_WIDTH, WIN_HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, UI_BG_ALPHA))
    data = pygame.image.tostring(overlay, "RGBA", True)
    glDrawPixels(WIN_WIDTH, WIN_HEIGHT, GL_RGBA, GL_UNSIGNED_BYTE, data)

    # pannello centrale
    panel = pygame.Surface((PANEL_W, PANEL_H))
    panel.fill((240, 240, 240))
    pygame.draw.rect(panel, (50, 50, 50), panel.get_rect(), 2)

    # testi
    panel.blit(font.render("Inserisci dati", True, (0, 0, 0)), (120, 20))
    panel.blit(font.render("Nome:", True, (0, 0, 0)), (40, NAME_LABEL_Y - PANEL_Y))
    panel.blit(font.render("Tentativo:", True, (0, 0, 0)), (40, ATT_LABEL_Y - PANEL_Y))

    # input box
    name_color = (0, 120, 255) if active_field == "name" else (0, 0, 0)
    att_color = (0, 120, 255) if active_field == "attempt" else (0, 0, 0)

    pygame.draw.rect(panel, name_color, (60, NAME_INPUT_Y - PANEL_Y, INPUT_W, INPUT_H), 2)
    pygame.draw.rect(panel, att_color, (60, ATT_INPUT_Y - PANEL_Y, INPUT_W, INPUT_H), 2)

    panel.blit(font.render(player_name, True, (0, 0, 0)), (65, NAME_INPUT_Y - PANEL_Y + 5))
    panel.blit(font.render(attempt, True, (0, 0, 0)), (65, ATT_INPUT_Y - PANEL_Y + 5))

    # bottone
    pygame.draw.rect(panel, (0, 200, 0), (BUTTON_X - PANEL_X, BUTTON_Y - PANEL_Y, BUTTON_W, BUTTON_H))
    panel.blit(font.render("START", True, (255, 255, 255)),
               (BUTTON_X - PANEL_X + 35, BUTTON_Y - PANEL_Y + 7))

    # draw panel
    panel_data = pygame.image.tostring(panel, "RGBA", True)
    glWindowPos2d(PANEL_X, WIN_HEIGHT - PANEL_Y - PANEL_H)
    glDrawPixels(PANEL_W, PANEL_H, GL_RGBA, GL_UNSIGNED_BYTE, panel_data)



# ---------------------------------------------------
# UTILS
# ---------------------------------------------------
def clamp(v, vmin, vmax):
    return max(vmin, min(vmax, v))

def point_in_rect(px, pz, rect):
    x, z, w, d = rect
    return (x <= px <= x + w) and (z <= pz <= z + d)

def draw_sphere(radius, slices=16, stacks=16):
    for i in range(stacks):
        lat0 = math.pi * (-0.5 + float(i) / stacks)
        z0  = math.sin(lat0)
        zr0 = math.cos(lat0)

        lat1 = math.pi * (-0.5 + float(i + 1) / stacks)
        z1  = math.sin(lat1)
        zr1 = math.cos(lat1)

        glBegin(GL_TRIANGLE_STRIP)
        for j in range(slices + 1):
            lng = 2 * math.pi * float(j) / slices
            x = math.cos(lng)
            y = math.sin(lng)

            glVertex3f(radius * x * zr0,
                       radius * z0,
                       radius * y * zr0)

            glVertex3f(radius * x * zr1,
                       radius * z1,
                       radius * y * zr1)
        glEnd()



def perspective(fovy, aspect, znear, zfar):
    f = 1.0 / math.tan(math.radians(fovy) / 2.0)

    m = [
        f / aspect, 0.0, 0.0,  0.0,
        0.0, f,       0.0,  0.0,
        0.0, 0.0, (zfar + znear) / (znear - zfar), -1.0,
        0.0, 0.0, (2.0 * zfar * znear) / (znear - zfar), 0.0
    ]

    glMultMatrixf(m)


def init_opengl():
    glEnable(GL_DEPTH_TEST)
    glDisable(GL_LIGHTING)
    glClearColor(0.85, 0.90, 0.98, 1.0)

    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    perspective(50.0, WIN_WIDTH / WIN_HEIGHT, 0.1, 200.0)

    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()


def setup_fixed_camera_handheld():
    glLoadIdentity()

    # arretra la camera
    glTranslatef(0.0, -1.0, -38.0)

    # inclina verso il basso
    glRotatef(42.0, 1.0, 0.0, 0.0)



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


def save_results(name, attempt, modalita, livello, result, time_sec, wall_hits, lives):
    os.makedirs("results", exist_ok=True)
    filename = os.path.join("results", "results.csv")
    file_exists = os.path.isfile(filename)

    with open(filename, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        if not file_exists:
            writer.writerow([
                "Nome",
                "Tentativo",
                "Modalità_ID",
                "Modalità",
                "Livello_raggiunto",
                "Esito",
                "Tempo_totale_sec",
                "Collisioni_muri",
                "Vite_rimanenti"
            ])

        writer.writerow([
            name,
            attempt,
            modalita,
            MODALITA_MAP.get(modalita, "Sconosciuta"),
            livello,
            result,
            f"{time_sec:.2f}",
            wall_hits,
            lives
        ])



# ---------------------------------------------------
# MAIN
# ---------------------------------------------------
def main():
       
    parser = argparse.ArgumentParser(description="Labirinto 3D multimodale")
    parser.add_argument("--audio", action="store_true", help="Abilita audio OSC")
    parser.add_argument("--vibration", action="store_true", help="Abilita vibrazioni ERM")
    args = parser.parse_args()
    modalita=0
    if args.audio and args.vibration:
        modalita=2
    elif args.audio:
        modalita=1
    

    ENABLE_AUDIO = args.audio
    ENABLE_VIBRATION = args.vibration

    if ENABLE_VIBRATION:
        vibration = SimpleUDPClient("127.0.0.1", 2222)
    else:
        vibration = None
    

    if ENABLE_AUDIO:
        bouncing = SimpleUDPClient("127.0.0.1", 9000)
        boom = SimpleUDPClient("127.0.0.1", 9001)
        rolling = SimpleUDPClient("127.0.0.1", 9002)
        win=SimpleUDPClient("127.0.0.1",9003)
    else:
        bouncing = boom = rolling = win = None

    pygame.init()
    font = pygame.font.SysFont("Arial", 20, bold=True)
    current_level = 1
    max_level = max(LEVELS.keys())
    maze = Maze(level=current_level)
    ball = Ball(*START_POS, gravity=GRAVITY, friction=FRICTION)
    lives = START_LIVES
    start_time = None
    total_time = 0.0
    wall_collisions = 0
    player_name = ""
    attempt_number = ""
    input_field = "name"   # "name" | "attempt"
    state = "INPUT"   # INPUT, PLAY, WIN, GAME_OVER
    screen = pygame.display.set_mode((WIN_WIDTH, WIN_HEIGHT), DOUBLEBUF | OPENGL)
    pygame.display.set_caption("MazeTilt")
    clock = pygame.time.Clock()
    accel = AccelController()

    init_opengl()   

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

            # -------- INPUT TASTIERA --------
            if state == "INPUT" and event.type == KEYDOWN:

                # ---------- TAB: cambia focus SEMPRE ----------
                if event.key == K_TAB:
                    input_field = "attempt" if input_field == "name" else "name"

                # ---------- ENTER ----------
                elif event.key == K_RETURN:
                    if input_field == "name":
                        # ENTER su nome -> vai a tentativo
                        input_field = "attempt"

                    elif input_field == "attempt":
                        # ENTER su tentativo -> prova a partire
                        if player_name.strip() != "" and attempt_number != "":
                            state = "PLAY"
                            start_time = pygame.time.get_ticks()

                # ---------- BACKSPACE ----------
                elif event.key == K_BACKSPACE:
                    if input_field == "name":
                        player_name = player_name[:-1]
                    else:
                        attempt_number = attempt_number[:-1]

                # ---------- INPUT CARATTERI ----------
                else:
                    if input_field == "name" and event.unicode.isprintable():
                        player_name += event.unicode

                    elif input_field == "attempt" and event.unicode.isdigit():
                        attempt_number += event.unicode


            # -------- INPUT MOUSE --------
            if state == "INPUT" and event.type == MOUSEBUTTONDOWN:
                mx, my = event.pos

                # click su campo nome
                if INPUT_X <= mx <= INPUT_X + INPUT_W and NAME_INPUT_Y <= my <= NAME_INPUT_Y + INPUT_H:
                    input_field = "name"

                # click su campo tentativo
                elif INPUT_X <= mx <= INPUT_X + INPUT_W and ATT_INPUT_Y <= my <= ATT_INPUT_Y + INPUT_H:
                    input_field = "attempt"

                # click su bottone START
                elif (BUTTON_X <= mx <= BUTTON_X + BUTTON_W and
                    BUTTON_Y <= my <= BUTTON_Y + BUTTON_H):
                    if player_name.strip() != "" and attempt_number != "":
                        state = "PLAY"
                        start_time = pygame.time.get_ticks()


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
            player_name = ""
            attempt_number = ""
            input_field = "name"
            state = "INPUT"

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
                vibration.send_message("/V", 1)

            # ---------------------------------------------------
            # HOLE AREA -> VIBRAZIONE CONTINUA PROPORZIONALE
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

                    # inverti: più vicino -> più vibrazione
                    intensity = HOLE_VIBRATION_MIN + (1.0 - t) * (HOLE_VIBRATION_MAX - HOLE_VIBRATION_MIN)

                    hole_vibration = int(intensity)
                    break

            # invio comando al teensy
            if inside_area:
                if ENABLE_VIBRATION:
                    vibration.send_message("/H", hole_vibration)
            else:
                if ENABLE_VIBRATION:
                    vibration.send_message("/H", 0)

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
                    save_results(player_name, attempt_number, modalita, current_level, "GAME_OVER", total_time, wall_collisions, lives)    
                    if ENABLE_VIBRATION:
                        vibration.send_message("/H", 0)
                    if ENABLE_AUDIO:
                        rolling.send_message("/rolling/on", 0)
                    rolling_on = False
                else:
                    ball.reset()                   
                    reset_tilt(accel)                    

            # vittoria
            if point_in_rect(ball.x, ball.z, GOAL_RECT):
                if ENABLE_AUDIO:
                    win.send_message("/win", 1)
                    rolling.send_message("/rolling/on", 0)
                if ENABLE_VIBRATION:
                    vibration.send_message("/H", 0)
                rolling_on = False

                if current_level < max_level:
                    current_level += 1
                    maze = Maze(level=current_level)
                    ball.reset()
                    reset_tilt(accel)
                    state = "PLAY"
                else:
                    state = "WIN"
                    save_results(player_name, attempt_number, modalita, current_level, "WIN", total_time, wall_collisions, lives) 

        # -------- RENDER 3D --------
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()
        setup_fixed_camera_handheld()

        glPushMatrix()

        glRotatef(tilt_x_deg, 1, 0, 0)
        glRotatef(-tilt_z_deg, 0, 0, 1)

        glTranslatef(0.0, 3.0, 0.0)

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

        if state == "INPUT":
            draw_input_panel(font, player_name, attempt_number, input_field)

        draw_hud_gl(font, current_level, max_level, lives, state, total_time, wall_collisions)

        glDisable(GL_BLEND)
        glEnable(GL_DEPTH_TEST)

        pygame.display.flip()

    if ENABLE_AUDIO:
        rolling.send_message("/rolling/on", 0)
    if ENABLE_VIBRATION:
        vibration.send_message("/H", 0)

    accel.close()
    pygame.quit()


if __name__ == "__main__":
    main()

