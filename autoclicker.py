import time
import threading
import random

from tkinter import *
from tkinter import messagebox
from collections import deque
from pydirectinput import mouseDown, mouseUp
from pynput import keyboard
from functools import partial

VER = "v0.6.3"

class ClickTimer:
    def __init__(self, timeToMs:float, isMouseDown:bool):
        self._timeToMs = timeToMs
        self._clickDown = isMouseDown
    
    def ingest_delta(self, timeDeltaMs:float):
        if self._timeToMs > 0:
            self._timeToMs -= timeDeltaMs
        if self._timeToMs < 0:
            self._timeToMs = 0
    
    def is_ready(self) -> bool:
        return self._timeToMs <= 0
    
    def get_time(self) -> float:
        return self._timeToMs
    
    def is_click_down(self) -> bool:
        return self._clickDown

class Autoclicker:
    UPDATE_INTERVAL_SECS = .033 # 33ms = ~30 FPS
    START_COUNTDOWN_MS = 5000
    UNPAUSE_COUNTDOWN_MS = 3000
    MOUSE_CLICK_LENGTH_RANGE_MS = (50, 125)
    MOUSE_DOUBLECLICK_GAP_RANGE_MS = (125, 350)

    _clicks = 0
    _waitTimeSecs = 0.0
    _waitVariSecs = 0.0
    _doDoubleClick = False
    _isPaused = False

    def __init__(self):
        self._interval = Autoclicker.UPDATE_INTERVAL_SECS
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._clicksQueue = deque()

    def start(self, waitTimeSecs:float, waitVariSecs:float, numClicks:int = -1, doDoubleClick:bool = False):
        if self._thread.is_alive():
            return

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)

        random.seed()
        self._clicks = numClicks
        self._waitTimeSecs = waitTimeSecs
        self._waitVariSecs = waitVariSecs
        self._doDoubleClick = doDoubleClick
        self._isPaused = False

        self._queue_click(Autoclicker.START_COUNTDOWN_MS)
        self._thread.start()
    
    def stop(self):
        self._stop_event.set()

    def pause(self, setPause:bool):
        if not self.is_active():
            return
        
        self._isPaused = setPause
        if not self._isPaused:
            if len(self._clicksQueue) > 0:
                self._clicksQueue[0]._timeToMs = Autoclicker.UNPAUSE_COUNTDOWN_MS
    
    def is_active(self) -> bool:
        return self._thread.is_alive()
    
    def is_paused(self) -> bool:
        return self._isPaused
    
    def get_clicks(self) -> int:
        return self._clicks
    
    def get_next_click_time(self) -> float | None:
        if len(self._clicksQueue) > 0:
            return self._clicksQueue[0].get_time()
        else:
            return None

    def _run(self):
        lastUpdateTime = time.perf_counter()
        while not self._stop_event.is_set():
            thisUpdateTime = time.perf_counter()
            deltaTime = (thisUpdateTime - lastUpdateTime) * 1000
            lastUpdateTime = thisUpdateTime
            self._update(deltaTime)
            time.sleep(self._interval)

    def _update(self, deltaMs):
        if self.is_paused():
            return

        self._clicksQueue[0].ingest_delta(deltaMs)
        if not self._clicksQueue[0].is_ready():
            return

        click = self._clicksQueue.popleft()
        self._do_click(click.is_click_down())

        if len(self._clicksQueue) == 0:
            if (self._clicks > 0):
                self._clicks -= 1

        if self._clicks == 0:
            self.stop()
        else:
            nextClickTimeMs = self._waitTimeSecs + random.uniform(0, self._waitVariSecs)
            self._queue_click(nextClickTimeMs)

    def _queue_click(self, timeUntilMs:float):
        holdTime = random.uniform(*self.MOUSE_CLICK_LENGTH_RANGE_MS)
        self._clicksQueue.append(ClickTimer(timeUntilMs, True))
        self._clicksQueue.append(ClickTimer(holdTime, False))
        if self._doDoubleClick:
            doubleClickTime = random.uniform(*self.MOUSE_DOUBLECLICK_GAP_RANGE_MS)
            holdTime = random.uniform(*self.MOUSE_CLICK_LENGTH_RANGE_MS)
            self._clicksQueue.append(ClickTimer(doubleClickTime, True))
            self._clicksQueue.append(ClickTimer(holdTime, False))

    def _do_click(self, isMouseDown:bool):
        if isMouseDown: mouseDown()
        else: mouseUp()

class FieldValidator:
    def is_valid_decimal(chars:str) -> bool:
        if chars == "":
            return True
        if chars.count('.') > 1:
            return False
        return all(c in "0123456789." for c in chars)

    def is_valid_int(chars:str) -> bool:
        if chars == "":
            return True
        return all(c in "0123456789" for c in chars)

class Keybinder:
    HINT_PASSIVE = "Click here to rebind"
    HINT_ACTIVE = "Press any key..."

    def __init__(self, defaultKey:keyboard.Key|None = None):
        self._isListening:bool = False
        self._assignedKey = defaultKey

    def set_listening(self, value:bool):
        self._isListening = value
    
    def is_listening(self) -> bool:
        return self._isListening

    def try_set_key(self, key:keyboard.Key|None):
        if not self.is_listening(): return
        self._assignedKey = key
        self._isListening = False
    
    def get_key(self) -> keyboard.Key|None:
        return self._assignedKey
    
    def get_key_name(self) -> str:
        if self._assignedKey is None:
            return "{unbound!}"
        if isinstance(self._assignedKey, keyboard.KeyCode):
            return self._assignedKey.char.upper()
        elif isinstance(self._assignedKey, keyboard.Key):
            name = self._assignedKey.name.replace('_', ' ').title()
            if name.endswith(' R'):
                name = f"Right {name[:-2]}"
            elif name.endswith(' L'):
                name = f"Left {name[:-2]}"
            return name
        return "err?"
    
    def get_hint(self) -> str:
        return Keybinder.HINT_ACTIVE if self.is_listening() else Keybinder.HINT_PASSIVE

class Window:
    UI_UPDATE_MS = 50 # 50ms = ~20 FPS

    def __init__(self):
        self.root = Tk()
        self.root.attributes('-topmost', True)
        self.root.title(VER)
        self.root.minsize(height=0, width=250)
        self.root.resizable(False, False)

        self.autoclicker = Autoclicker()
        self.keyListener = keyboard.Listener(on_press=self.key_press)
        self._pauseKeybind = Keybinder(keyboard.Key.home)
        self._stopKeybind = Keybinder(keyboard.Key.end)

        self._build_gui()

        self.keyListener.start()
        self._uiloop()
        self.root.mainloop()

    def _build_gui(self):
        bindsFrame = Frame(self.root)
        bindsFrame.pack(pady=10)
        pauseColumn = Frame(bindsFrame)
        pauseColumn.pack(side=LEFT, padx=15)
        self.pauseBindLabel = Label(pauseColumn)
        self.pauseBindLabel.pack()
        self.pauseBindButton = Button(pauseColumn, text=Keybinder.HINT_PASSIVE, width=16, 
            command=partial(self._set_keybind_listening, self._pauseKeybind))
        self.pauseBindButton.pack(pady=(4,0))
        stopColumn = Frame(bindsFrame)
        stopColumn.pack(side=LEFT, padx=15)
        self.stopBindLabel = Label(stopColumn)
        self.stopBindLabel.pack()
        self.stopBindButton = Button(stopColumn, text=Keybinder.HINT_PASSIVE, width=16,
            command=partial(self._set_keybind_listening, self._stopKeybind))
        self.stopBindButton.pack(pady=(4,0))
   
        Label(self.root, text="Number of clicks (0 = inf)").pack(pady=(10,0))
        self.numClicksField = Entry(
            self.root,
            width=10,
            validate="key",
            validatecommand=(self.root.register(FieldValidator.is_valid_int), "%P"),
        )
        self.numClicksField.insert(0, "0")
        self.numClicksField.pack()

        Label(self.root, text="Guaranteed wait (secs)").pack(pady=(10,0))
        self.waitTimeField = Entry(
            self.root,
            width=10,
            validate="key",
            validatecommand=(self.root.register(FieldValidator.is_valid_decimal), "%P"),
        )
        self.waitTimeField.insert(0, "2.7")
        self.waitTimeField.pack()

        Label(self.root, text="Maximum random extra wait (secs)").pack(pady=(10, 0))
        self.waitVariField = Entry(
            self.root,
            width=10,
            validate="key",
            validatecommand=(self.root.register(FieldValidator.is_valid_decimal), "%P"),
        )
        self.waitVariField.insert(0,"0.2")
        self.waitVariField.pack()

        checkboxFrame = Frame(self.root)
        checkboxFrame.pack(pady=(10,0))
        Label(checkboxFrame, text="Click twice?").pack(side=LEFT)
        self._doubleclick = BooleanVar(value=True)
        self.doDoubleclickCheckbox = Checkbutton(checkboxFrame, variable=self._doubleclick, pady=0)
        self.doDoubleclickCheckbox.pack(side=LEFT)
        Label(self.root, text="(e.g. alching, toggling prayer...)").pack(pady=(0,10))

        self.startButton = Button(self.root, text="Start", command=self._try_start, width = 10)
        self.startButton.pack(pady=(10, 0))

        self.readoutLabel = Label(self.root, text="")
        self.readoutLabel.pack(pady=(10, 0))

        self._update_keybind_hints()
        self._set_ui_state("normal")

    def _uiloop(self):
        self._update()
        self.root.after(Window.UI_UPDATE_MS, self._uiloop)

    def _update(self):
        nextClickTime = self.autoclicker.get_next_click_time()
        if not nextClickTime is None:
            nextClickTime = nextClickTime / 1000
            if nextClickTime < 0.1: #TODO fix countdown display update accuracy
                nextClickStr = f"Now!"
            else:
                nextClickStr = f"{nextClickTime:.2f}s"
        
        readoutText = str()
        if not self.autoclicker.is_active():
            readoutText = "{Clicker is inactive}"
        elif self.autoclicker.is_paused():
            readoutText = f"{self.autoclicker.get_clicks()} clicks left.\n(Clicking is paused)\n"
        elif self.autoclicker.get_clicks() < 0:
            readoutText = f"Clicking infinitely!\nNext click: {nextClickStr}"
        else:
            readoutText = f"{self.autoclicker.get_clicks()} clicks left.\nNext click: {nextClickStr}"
        self.readoutLabel.config(text=readoutText)

    def _set_ui_state(self, state):
        self.numClicksField.config(state=state)
        self.waitTimeField.config(state=state)
        self.waitVariField.config(state=state)
        self.startButton.config(state=state)
        self.doDoubleclickCheckbox.config(state=state)
        self.pauseBindButton.config(state=state)
        self.stopBindButton.config(state=state)
    
    def _set_keybind_listening(self, keybind:Keybinder|None):
        self._pauseKeybind.set_listening(keybind is self._pauseKeybind)
        self._stopKeybind.set_listening(keybind is self._stopKeybind)
        self._update_keybind_hints()

    def _update_keybind_hints(self):
        self.pauseBindButton.config(text=self._pauseKeybind.get_hint())
        self.stopBindButton.config(text=self._stopKeybind.get_hint())
        self.pauseBindLabel.config(text=f"PAUSE: [{self._pauseKeybind.get_key_name()}]")
        self.stopBindLabel.config(text=f"STOP: [{self._stopKeybind.get_key_name()}]")

    def _try_start(self):
        try:
            numClicks = int(self.numClicksField.get())
            if (numClicks == 0):
                numClicks = -1
            waitTimeMs = float(self.waitTimeField.get()) * 1000
            waitVariMs = float(self.waitVariField.get()) * 1000
            doDoubleClick = bool(self._doubleclick)
        except ValueError:
            messagebox.showerror("Input Error", "Please correctly and completely fill out the config window.", parent=self.root)
            return
        except:
            messagebox.showerror("Unknown Error", "An unhandled error occurred.", parent=self.root)
            return

        self._set_ui_state("disabled")
        self.autoclicker.start(waitTimeMs, waitVariMs, numClicks, doDoubleClick)
    
    def _stop_clicker(self):
        self.autoclicker.stop()
        self._set_ui_state("normal")

    def key_press(self, key):
        if key == keyboard.Key.esc:
            self._pauseKeybind.try_set_key(None)
            self._stopKeybind.try_set_key(None)
            self._set_keybind_listening(None)
            return
        if key == self._pauseKeybind.get_key():
            self.autoclicker.pause(not self.autoclicker.is_paused())
            return
        if key == self._stopKeybind.get_key():
            self.autoclicker.stop()
            return
        self._pauseKeybind.try_set_key(key)
        self._stopKeybind.try_set_key(key)
        self._update_keybind_hints()

if __name__ == "__main__":
    window = Window()
