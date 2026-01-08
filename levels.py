# levels.py

MAZE_WIDTH = 20.0
MAZE_DEPTH = 30.0

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
