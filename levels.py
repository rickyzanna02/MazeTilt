# levels.py

MAZE_WIDTH = 20.0
MAZE_DEPTH = 30.0

# Walls (x_ref, z_ref, dx, dz, w, d)
# x_ref, z_ref = "min" bordo minimo (sinistra o vicino) or "max" bordo massimo (destra o lontano)
# dx, dz = coordinate offset del muro rispetto al riferimento
# w, d = larghezza e profondità del muro; "T" indica che lo spessore thickness

# Holes (x, z, r)
# x, z = coordinate del centro del buco
# r = raggio del buco

LEVELS = {
    1: {
        "walls": [
            ("min", "max", 10.0, -29.0, "T", 15.0),
            ("min", "max", 0.0, -5.0, 10.0, "T"),
        ],
        "holes": [
            (3.0, 12.5, 1.0),
        ]
    },

    2: {
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
    },

    3: {
        "walls": [
            ("min", "min", 0.0, 6.0, 15.0, "T"),
            ("max", "min", -15.0, 12.0, 15.0, "T"),
            ("min", "min", 0.0, 18.0, 15.0, "T"),
            ("max", "min", -15.0, 24.0, 15.0, "T"),
        ],
        "holes": [
            (-2.0, -5.0, 1.0),
            (-2.0, 7.0, 1.0),
            (3.0, 13.5, 1.0),
        ]
    },

    4: {
        "walls": [
            ("min", "min", 11.0, 0.0, "T", 6.0),
            ("min", "min", 3.0, 5.25, 8.5, "T"),
            ("min", "min", 0.0, 12.5, 15.0, "T"),
            ("min", "min", 15.0, 7.25, "T", 6.0),
            ("max", "max", -12.0, -9.0, 12.0, "T"),
            ("max", "max", -5.0, -4.0, "T", 4.0),
        ],
        "holes": [
            (-4.0, -4.0, 1.0),
            (6.0, -9.0, 1.0),
            (2.0, 1.0, 1.0),
            (-4.0, 11.0, 1.0),
        ]
    },

    5: {
        "walls": [
            ("max", "min", -9.0, 6.0, 9.0, "T"),
            ("min", "min", 9.0, 6.0, "T", 6.0),
            ("max", "min", -14.0, 12.0, 5.0, "T"),
            ("min", "min", 0.0, 18.0, 12.0, "T"),
            ("max", "max", -8.0, -5.0, 8.0, "T"),
            ("min", "max", 3.0, -10.0, "T", 4.0),
        ],
        "holes": [
            (-2.5, -4.5, 1.0),
            (3.5, 1.5, 1.0),
            (5.5, -4.0, 1.0),
            (0.0, 9.5, 1.0),
            (-6.0, 12.0, 1.0),
            (5.5, 13.0, 1.0),
        ]
    }
}
