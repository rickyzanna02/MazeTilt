import subprocess
import os
import platform


def start_pd():
    # ======================
    # CONFIGURAZIONE PATCH
    # ======================

    PATCH_GROUPS = [
        {
            "dir": "PureDataAudio",
            "patches": [
                "audioPatch.pd",
            ]
        },
        {
            "dir": "Pd_serial_communication_send_receive", 
            "patches": [
                "Main_Pd_serial_communication_send_receive.pd",                 
            ]
        }
    ]

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

    system = platform.system()

    if system == "Windows":
        PD_BIN = r"C:\Program Files\Pd\bin\pd.exe"
        PD_CMD = [PD_BIN, "-nogui", "-rt"]
    elif system == "Linux":
        PD_CMD = ["pd", "-nogui", "-rt"]
    else:
        raise RuntimeError(f"Sistema non supportato: {system}")

    cmd = PD_CMD[:]

    # ======================
    # CARICAMENTO PATCH
    # ======================
    for group in PATCH_GROUPS:
        patch_dir = os.path.join(BASE_DIR, group["dir"])

        for patch in group["patches"]:
            patch_path = os.path.join(patch_dir, patch)
            if not os.path.isfile(patch_path):
                raise FileNotFoundError(f"Patch non trovata: {patch_path}")
            cmd.extend(["-open", patch_path])

    # ======================
    # AVVIO IN BACKGROUND
    # ======================
    return subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )


# ENTRY POINT
if __name__ == "__main__":
    print("Avvio Pure Data...")
    start_pd()
    print("Pure Data avviato in background.")
