# ---------------------------------------------------
# MAZE
# ---------------------------------------------------

import math
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
from levels import LEVELS
from ball import Ball

MAZE_WIDTH = 20.0
MAZE_DEPTH = 30.0
GOAL_RECT = (MAZE_WIDTH / 2.0 - 3.0, MAZE_DEPTH / 2.0 - 3.0, 2.2, 2.2)# Goal: rect in XZ plane (x, z, w, d)
WALL_RESTITUTION = 0.80
WALL_TANGENTIAL = 0.96
BALL_RADIUS = 0.6

def draw_disk(cx, cy, cz, r, segments=24):
    glBegin(GL_TRIANGLE_FAN)
    glVertex3f(cx, cy, cz)
    for i in range(segments + 1):
        a = (i / segments) * 2.0 * math.pi
        glVertex3f(cx + math.cos(a) * r, cy, cz + math.sin(a) * r)
    glEnd()

def clamp(v, vmin, vmax):
    return max(vmin, min(vmax, v))

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
        glVertex3f(gx, 0.25, gz)
        glVertex3f(gx + gw, 0.25, gz)
        glVertex3f(gx + gw, 0.25, gz + gd)
        glVertex3f(gx, 0.25, gz + gd)
        glEnd()

        # buchi (dischi scuri)
        glColor3f(0.12, 0.12, 0.12)
        for (hx, hz, r) in self.holes:
            draw_disk(hx, 0.25, hz, r, segments=24)

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