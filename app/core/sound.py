import os
import sys
import threading
import subprocess

def play_shutter_sound():
    def _play():
        try:
            if sys.platform == "win32":
                import winsound
                # Fast dual click sound resembling camera shutter
                winsound.Beep(1800, 35)
                winsound.Beep(2400, 45)
            elif sys.platform == "darwin":
                # Native macOS camera/shutter or system sound
                candidates = [
                    "/System/Library/Components/CoreAudio.component/Contents/SharedSupport/SystemSounds/system/Screen Capture.aif",
                    "/System/Library/Sounds/Tink.aiff",
                    "/System/Library/Sounds/Pop.aiff",
                ]
                for snd in candidates:
                    if os.path.exists(snd):
                        subprocess.run(["afplay", snd], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        break
        except Exception:
            pass

    t = threading.Thread(target=_play, daemon=True)
    t.start()
