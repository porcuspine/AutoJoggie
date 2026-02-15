
from ui.window import AutoclickerWindow
from core.autoclicker import Autoclicker

VER = "0.7"

if __name__ == "__main__":
    window = AutoclickerWindow(autoclicker=Autoclicker(), version=VER)
    window.start()
