import subprocess
import os
import platform


def start_pd():
    PATCHES = [
        "rolling.pd",
        "bouncing.pd",
        "boom.pd",
        "win.pd"
    ]

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    PATCH_DIR = os.path.join(BASE_DIR, "PureDataAudio")

    system = platform.system()

    if system == "Windows":
        PD_BIN = r"C:\Program Files\Pd\bin\pd.exe"
        PD_CMD = [PD_BIN, "-nogui", "-rt"]
    elif system == "Linux":
        PD_CMD = ["pd", "-nogui", "-rt"]
    else:
        raise RuntimeError(f"Sistema non supportato: {system}")

    cmd = PD_CMD[:]

    for patch in PATCHES:
        patch_path = os.path.join(PATCH_DIR, patch)
        if not os.path.isfile(patch_path):
            raise FileNotFoundError(f"Patch non trovata: {patch_path}")
        cmd.extend(["-open", patch_path])

    # DSP ON
    cmd.extend(["-send", "pd dsp 1"])

    # Avvio in background
    return subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )


#  ENTRY POINT
if __name__ == "__main__":
    print("Avvio Pure Data...")
    start_pd()
    print("Pure Data avviato in background.")
