
from ui.window import AutoclickerWindow
from core.autoclicker import Autoclicker

def abs_path(path:str) -> str:
    """Converts a relative file path to an absolute file path, based on the location of the currently executing script."""

    import sys
    from pathlib import Path

    base_path = getattr(sys, "_MEIPASS", None)
    if base_path:
        return str(Path(base_path) / path)
    return str(Path(__file__).resolve().parent / path)


if __name__ == "__main__":
    window = AutoclickerWindow(autoclicker=Autoclicker(), ico_path=abs_path("icon.png"))
    window.start()
