import math
import pygame
from pygame import Vector2

# ----------------------------
# Config
# ----------------------------
WIDTH, HEIGHT = 1100, 750
FPS = 120

# Maze grid size (keep modest to render nicely)
GRID_W, GRID_H = 14, 10

MARGIN = 60
WALL_THICK = 10          # in pixels (screen space)
WALL_HEIGHT = 26         # pseudo-3D "extrusion" height
WALL_LIP = 10            # vertical projection offset for 3D look

BALL_RADIUS = 14

# Physics
G = 1600.0               # "gravity" magnitude (px/s^2)
MAX_TILT = math.radians(18)   # max tilt angle in radians
TILT_SPEED = math.radians(60) # rad/s change when holding arrow

MU_ROLL = 1.25           # rolling/plane friction (damping)
REST = 0.35              # restitution (bounciness) vs walls
MU_WALL = 0.65           # wall friction (tangential damping when in contact)

# Visual colors
BG = (18, 20, 26)
FLOOR = (40, 44, 56)
FLOOR_GRID = (55, 60, 76)
WALL_TOP = (210, 214, 232)
WALL_SIDE = (165, 170, 190)
WALL_FRONT = (135, 140, 165)
BALL = (245, 120, 90)
BALL_SHADOW = (0, 0, 0, 90)
EXIT = (100, 220, 140)
TEXT = (235, 235, 245)


# ----------------------------
# Maze definition
# 0 = empty cell
# 1 = wall block (we will generate wall rectangles around these blocks)
# We'll build a "thick walls" outline from a grid of occupied wall tiles.
# ----------------------------
MAZE_TILES = [
    "11111111111111",
    "1.....1......1",
    "1.111.1.1111.1",
    "1.1...1....1.1",
    "1.1.111111.1.1",
    "1.1......1.1.1",
    "1.11111..1.1.1",
    "1......111.1.1",
    "1.111......1.1",
    "11111111111111",
]

# Start & exit (grid coords in cell-space; exit is a "hole" region on floor)
START_CELL = (1, 1)
EXIT_CELL = (12, 8)


# ----------------------------
# Helpers: circle-rect collision
# ----------------------------
def clamp(x, a, b):
    return a if x < a else b if x > b else x

def circle_rect_collision(circle_pos, radius, rect):
    """
    Returns (colliding: bool, normal: Vector2, penetration: float, closest_point: Vector2)
    normal points from rect to circle (push-out direction).
    """
    cx, cy = circle_pos.x, circle_pos.y
    closest_x = clamp(cx, rect.left, rect.right)
    closest_y = clamp(cy, rect.top, rect.bottom)
    closest = Vector2(closest_x, closest_y)

    delta = circle_pos - closest
    dist2 = delta.length_squared()
    if dist2 >= radius * radius:
        return False, Vector2(), 0.0, closest

    dist = math.sqrt(dist2) if dist2 > 1e-12 else 0.0
    if dist > 1e-6:
        normal = delta / dist
        penetration = radius - dist
        return True, normal, penetration, closest

    # Circle center exactly on/inside corner/edge (rare). Pick a normal by minimal overlap.
    # Compute overlaps to each side and push out smallest.
    left_overlap = abs(cx - rect.left)
    right_overlap = abs(rect.right - cx)
    top_overlap = abs(cy - rect.top)
    bottom_overlap = abs(rect.bottom - cy)

    m = min(left_overlap, right_overlap, top_overlap, bottom_overlap)
    if m == left_overlap:
        return True, Vector2(-1, 0), radius, closest
    if m == right_overlap:
        return True, Vector2(1, 0), radius, closest
    if m == top_overlap:
        return True, Vector2(0, -1), radius, closest
    return True, Vector2(0, 1), radius, closest


# ----------------------------
# Build wall rectangles from tile grid
# We'll create "solid wall blocks" rectangles and also keep them as rects for collision.
# Simpler: each wall tile becomes a rect, and collisions work fine.
# ----------------------------
def build_world_geometry():
    # Compute cell size to fit entire maze on screen
    usable_w = WIDTH - 2 * MARGIN
    usable_h = HEIGHT - 2 * MARGIN
    cell = min(usable_w / GRID_W, usable_h / GRID_H)
    cell = int(cell)

    # Center maze
    world_w = GRID_W * cell
    world_h = GRID_H * cell
    ox = (WIDTH - world_w) // 2
    oy = (HEIGHT - world_h) // 2

    wall_rects = []
    for y in range(GRID_H):
        for x in range(GRID_W):
            if MAZE_TILES[y][x] == "1":
                r = pygame.Rect(ox + x * cell, oy + y * cell, cell, cell)
                wall_rects.append(r)

    start_pos = Vector2(
        ox + (START_CELL[0] + 0.5) * cell,
        oy + (START_CELL[1] + 0.5) * cell
    )

    exit_rect = pygame.Rect(
        ox + EXIT_CELL[0] * cell + cell * 0.20,
        oy + EXIT_CELL[1] * cell + cell * 0.20,
        cell * 0.60,
        cell * 0.60,
    )

    world_bounds = pygame.Rect(ox, oy, world_w, world_h)

    return cell, (ox, oy), wall_rects, start_pos, exit_rect, world_bounds


# ----------------------------
# Pseudo-3D rendering
# We keep maze fixed; "3D" is extruded walls and a slight vertical offset.
# ----------------------------
def draw_floor(surface, bounds, cell):
    pygame.draw.rect(surface, FLOOR, bounds, border_radius=10)

    # subtle grid
    for x in range(1, GRID_W):
        px = bounds.left + x * cell
        pygame.draw.line(surface, FLOOR_GRID, (px, bounds.top), (px, bounds.bottom), 1)
    for y in range(1, GRID_H):
        py = bounds.top + y * cell
        pygame.draw.line(surface, FLOOR_GRID, (bounds.left, py), (bounds.right, py), 1)

def draw_wall_block(surface, rect, height=WALL_HEIGHT, lip=WALL_LIP):
    """
    Draw a single wall tile as an extruded block:
    - top face (lighter)
    - front face (darker)
    - side face (mid)
    We fake a light direction: top-left.
    """
    # "3D" offset: extrude upwards-left
    off = Vector2(-lip, -lip)

    top = [
        (rect.left + off.x, rect.top + off.y),
        (rect.right + off.x, rect.top + off.y),
        (rect.right + off.x, rect.bottom + off.y),
        (rect.left + off.x, rect.bottom + off.y),
    ]

    # vertical offset for height (screen-space)
    h = Vector2(0, -height)

    top_h = [(p[0] + h.x, p[1] + h.y) for p in top]
    base = [(rect.left, rect.top), (rect.right, rect.top), (rect.right, rect.bottom), (rect.left, rect.bottom)]

    # Draw side faces (two faces: "front" and "right" based on our fake projection)
    # We treat bottom-right edges as "front"
    # Face between base and top_h
    # Front face: base bottom edge to top bottom edge
    front = [base[3], base[2], top_h[2], top_h[3]]
    side = [base[1], base[2], top_h[2], top_h[1]]

    pygame.draw.polygon(surface, WALL_FRONT, front)
    pygame.draw.polygon(surface, WALL_SIDE, side)
    pygame.draw.polygon(surface, WALL_TOP, top_h)

    # Outline for readability
    pygame.draw.polygon(surface, (25, 28, 35), top_h, 2)
    pygame.draw.polygon(surface, (25, 28, 35), front, 2)
    pygame.draw.polygon(surface, (25, 28, 35), side, 2)

def draw_exit(surface, exit_rect):
    pygame.draw.rect(surface, EXIT, exit_rect, border_radius=10)
    pygame.draw.rect(surface, (20, 25, 22), exit_rect, 3, border_radius=10)

def draw_ball(surface, pos, radius, z=0.0):
    # Shadow
    shadow_surf = pygame.Surface((radius * 3, radius * 3), pygame.SRCALPHA)
    pygame.draw.circle(shadow_surf, BALL_SHADOW, (radius * 1.5, radius * 1.6), int(radius * 1.1))
    surface.blit(shadow_surf, (pos.x - radius * 1.5, pos.y - radius * 1.5))

    # Ball (slight lift by z)
    p = (int(pos.x), int(pos.y - z))
    pygame.draw.circle(surface, BALL, p, radius)
    pygame.draw.circle(surface, (30, 30, 35), p, radius, 2)

    # Simple highlight
    pygame.draw.circle(surface, (255, 200, 185), (p[0] - radius // 3, p[1] - radius // 3), max(3, radius // 4))


# ----------------------------
# Game
# ----------------------------
def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Labirinto Tilt (pseudo-3D) - Pygame")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("consolas", 18)

    cell, origin, wall_rects, start_pos, exit_rect, world_bounds = build_world_geometry()

    # Ball state
    ball_pos = start_pos.copy()
    ball_vel = Vector2(0, 0)

    # Tilt angles (pitch/roll)
    tilt_x = 0.0  # affects +x acceleration
    tilt_y = 0.0  # affects +y acceleration

    won = False

    def reset():
        nonlocal ball_pos, ball_vel, tilt_x, tilt_y, won
        ball_pos = start_pos.copy()
        ball_vel = Vector2(0, 0)
        tilt_x = 0.0
        tilt_y = 0.0
        won = False

    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0
        dt = min(dt, 1/30)  # safety clamp

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                if event.key == pygame.K_r:
                    reset()

        keys = pygame.key.get_pressed()

        # Update tilt with arrows
        if keys[pygame.K_LEFT]:
            tilt_x -= TILT_SPEED * dt
        if keys[pygame.K_RIGHT]:
            tilt_x += TILT_SPEED * dt
        if keys[pygame.K_UP]:
            tilt_y -= TILT_SPEED * dt
        if keys[pygame.K_DOWN]:
            tilt_y += TILT_SPEED * dt

        tilt_x = clamp(tilt_x, -MAX_TILT, MAX_TILT)
        tilt_y = clamp(tilt_y, -MAX_TILT, MAX_TILT)

        if not won:
            # Gravity projected on plane by tilt (simple model)
            ax = G * math.sin(tilt_x)
            ay = G * math.sin(tilt_y)
            acc = Vector2(ax, ay)

            # Integrate
            ball_vel += acc * dt

            # Rolling friction (damping proportional to speed)
            # v' = v * exp(-mu*dt) approx -> v *= (1 - mu*dt) for small dt
            damp = max(0.0, 1.0 - MU_ROLL * dt)
            ball_vel *= damp

            # Move
            ball_pos += ball_vel * dt

            # Keep inside world bounds (treat bounds as walls)
            # We'll collide ball with bounds rectangle (as four walls)
            boundary_walls = [
                pygame.Rect(world_bounds.left - 10000, world_bounds.top - 10000, 10000, world_bounds.height + 20000),  # left
                pygame.Rect(world_bounds.right, world_bounds.top - 10000, 10000, world_bounds.height + 20000),          # right
                pygame.Rect(world_bounds.left - 10000, world_bounds.top - 10000, world_bounds.width + 20000, 10000),   # top
                pygame.Rect(world_bounds.left - 10000, world_bounds.bottom, world_bounds.width + 20000, 10000),        # bottom
            ]

            contact_normals = []

            def resolve_with_rect(r):
                nonlocal ball_pos, ball_vel
                coll, n, pen, _ = circle_rect_collision(ball_pos, BALL_RADIUS, r)
                if not coll:
                    return
                # Push out
                ball_pos += n * pen

                # Split velocity into normal/tangent
                vn = ball_vel.dot(n)
                vt = ball_vel - vn * n

                # Reflect normal component with restitution if moving into wall
                if vn < 0:
                    vn_post = -vn * REST
                else:
                    vn_post = vn

                # Wall friction: reduce tangent when in contact
                # Stronger when impact is stronger
                wall_damp = max(0.0, 1.0 - MU_WALL * dt * (1.0 + abs(vn) / 600.0))
                vt *= wall_damp

                ball_vel = vn_post * n + vt
                contact_normals.append(n)

            # Collide with maze walls (each wall tile is a solid block)
            for wr in wall_rects:
                resolve_with_rect(wr)

            # Collide with boundaries
            for br in boundary_walls:
                resolve_with_rect(br)

            # Win condition: center enters exit rect AND speed is small enough (feels like "falling in")
            if exit_rect.collidepoint(ball_pos.x, ball_pos.y):
                if ball_vel.length() < 220:
                    won = True
                    ball_vel *= 0

        # ----------------------------
        # Render
        # ----------------------------
        screen.fill(BG)

        draw_floor(screen, world_bounds, cell)
        draw_exit(screen, exit_rect)

        # Draw walls (sorted for nicer overlap). Sort by y then x.
        for wr in sorted(wall_rects, key=lambda r: (r.bottom, r.right)):
            draw_wall_block(screen, wr)

        # Ball "height" a bit affected by tilt magnitude (tiny illusion)
        z = 4.0 + 10.0 * (abs(tilt_x) + abs(tilt_y)) / (2 * MAX_TILT)
        draw_ball(screen, ball_pos, BALL_RADIUS, z=z)

        # HUD
        info1 = f"Tilt X: {math.degrees(tilt_x):5.1f}°   Tilt Y: {math.degrees(tilt_y):5.1f}°"
        info2 = f"Vel: {ball_vel.length():6.1f} px/s   (Frecce per inclinare)   R: reset   ESC: esci"
        t1 = font.render(info1, True, TEXT)
        t2 = font.render(info2, True, TEXT)
        screen.blit(t1, (20, 18))
        screen.blit(t2, (20, 40))

        if won:
            msg = "HAI VINTO! (premi R per ricominciare)"
            tm = pygame.font.SysFont("consolas", 34, bold=True).render(msg, True, (255, 245, 210))
            rect = tm.get_rect(center=(WIDTH // 2, 90))
            pygame.draw.rect(screen, (20, 22, 28), rect.inflate(30, 18), border_radius=14)
            screen.blit(tm, rect)

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
