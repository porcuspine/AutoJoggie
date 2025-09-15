from pydirectinput import mouseDown, mouseUp
from pynput import keyboard
from time import perf_counter
import random
from tkinter import *
from tkinter import messagebox

class Window:
    MS_PER_FRAME = 16 #~60 FPS
    CLICKING_INIT_COUNTDOWN_MS = 5000
    MOUSE_CLICK_LENGTH_RANGE_MS = (50, 125)
    MOUSE_DOUBLECLICK_GAP_RANGE_MS = (125, 350)

    keyListener = None

    isPaused = False
    doDoubleClick = False

    nextClickIntervalMs = 0
    numClicksRemaining = 0
    waitTimeSecs = 0
    waitVariSecs = 0
    timeAccumulatedMs = 0
    lastUpdateTimeMs = None
    clickTimeUpBookmark = None
    doubleclickDownBookmark = None

    def __init__(self):
        self.root = Tk()
        self.root.title("v0.5")
        self.root.minsize(height=0, width=250)
        self.root.resizable(False, False)

        Label(self.root, text="Number of clicks (0 = inf)").pack(pady=(10,0))
        self.numClicksField = Entry(
            self.root,
            width=10,
            validate="key",
            validatecommand=(self.root.register(self.validate_int_input), "%P"),
        )
        self.numClicksField.insert(0, "0")
        self.numClicksField.pack()

        Label(self.root, text="Guaranteed wait (secs)").pack(pady=(10,0))
        self.waitTimeField = Entry(
            self.root,
            width=10,
            validate="key",
            validatecommand=(self.root.register(self.validate_decimal_input), "%P"),
        )
        self.waitTimeField.insert(0, "3")
        self.waitTimeField.pack()

        Label(self.root, text="Maximum random extra wait (secs)").pack(pady=(10, 0))
        self.waitVariField = Entry(
            self.root,
            width=10,
            validate="key",
            validatecommand=(self.root.register(self.validate_decimal_input), "%P"),
        )
        self.waitVariField.insert(0,"0.2")
        self.waitVariField.pack()

        frame = Frame(self.root)
        frame.pack(pady=(10, 0))
        Label(frame, text="Click twice?").pack(side=LEFT)
        self.doDoubleclick = BooleanVar(value=self.doDoubleClick)
        self.doDoubleclickCheckbox = Checkbutton(frame, variable=self.doDoubleclick)
        self.doDoubleclickCheckbox.pack(side=LEFT)
        Label(self.root, text="(e.g. alching, toggling prayer...)").pack()

        self.startButton = Button(self.root, text="Start", command=self.start_clicking, width = 10)
        self.startButton.pack(pady=(10, 0))

        self.readoutLabel = Label(self.root, text="--------")
        self.readoutLabel.pack(pady=(10, 0))

        self.lastUpdateTimeMs = perf_counter()
        self.keyListener = keyboard.Listener(on_press=self.key_press)
        self.keyListener.start()
        self.awaken()
    
    def awaken(self):
        self.update()
        self.root.after(self.MS_PER_FRAME, self.awaken)

    def start_clicking(self):
        try:
            self.numClicksRemaining = int(self.numClicksField.get())
            self.waitTimeSecs = float(self.waitTimeField.get())
            self.waitVariSecs = float(self.waitVariField.get())
        except ValueError:
            messagebox.showerror("Input Error", "Please correctly and completely fill out the config window", parent=self.root)
            return
        except:
            messagebox.showerror("Error", "An unhandled error occurred", parent=self.root)
            return

        random.seed()

        if (self.numClicksRemaining == 0):
            self.numClicksRemaining = -1

        self.nextClickIntervalMs = self.CLICKING_INIT_COUNTDOWN_MS
        self.timeAccumulatedMs = 0
        self.isPaused = False

    def update(self):
        currentTimeMs = perf_counter() * 1000
        deltaTimeMs = currentTimeMs - self.lastUpdateTimeMs
        self.lastUpdateTimeMs = currentTimeMs
        
        if (self.numClicksRemaining == 0):
            self.readoutLabel.config(text = "Clicking is stopped.\n")
            self.numClicksField.config(state="normal")
            self.waitTimeField.config(state="normal")
            self.waitVariField.config(state="normal")
            self.startButton.config(state="normal")
            self.doDoubleclickCheckbox.config(state="normal")
            return
        
        self.numClicksField.config(state="disabled")
        self.waitTimeField.config(state="disabled")
        self.waitVariField.config(state="disabled")
        self.startButton.config(state="disabled")
        self.doDoubleclickCheckbox.config(state="disabled")

        if (self.isPaused):
            self.readoutLabel.config(text=
                f"{self.get_cycles_remaining()} (Paused)\nNext click: {((self.nextClickIntervalMs-self.timeAccumulatedMs)/1000):.2f}s")
            return

        self.timeAccumulatedMs += deltaTimeMs

        if self.timeAccumulatedMs >= self.nextClickIntervalMs:
            self.readoutLabel.config(text=f"{self.get_cycles_remaining()}\nNext click: Now")
            self.readoutLabel.update_idletasks()
            self.resolve_click(doDoubleClick = self.doDoubleclick.get())
        else:
            self.readoutLabel.config(text=
                f"{self.get_cycles_remaining()}\nNext click: {((self.nextClickIntervalMs-self.timeAccumulatedMs)/1000):.2f}s")

    def resolve_click(self, doDoubleClick = False):
        if (self.clickTimeUpBookmark == None and
                (self.doubleclickDownBookmark == None or self.timeAccumulatedMs >= self.doubleclickDownBookmark)):
            self.clickTimeUpBookmark = self.timeAccumulatedMs + random.uniform(*self.MOUSE_CLICK_LENGTH_RANGE_MS)
            mouseDown()
            return

        if (self.clickTimeUpBookmark != None and self.timeAccumulatedMs >= self.clickTimeUpBookmark):
            self.clickTimeUpBookmark = None
            mouseUp()
            if (doDoubleClick):
                if (self.doubleclickDownBookmark == None):
                    self.doubleclickDownBookmark = self.timeAccumulatedMs + random.uniform(*self.MOUSE_DOUBLECLICK_GAP_RANGE_MS)
                    return
                elif (self.timeAccumulatedMs >= self.doubleclickDownBookmark):
                    self.doubleclickDownBookmark = None

            self.numClicksRemaining -= 1
            self.timeAccumulatedMs = 0
            self.nextClickIntervalMs = (self.waitTimeSecs + random.uniform(0, self.waitVariSecs))*1000
    
    def get_cycles_remaining(self):
        if self.numClicksRemaining < 0:
            return "Clicking infinitely!"
        else:
            return f"{self.numClicksRemaining} clicks left."

    def validate_decimal_input(self, char):
        if char == "":
            return True
        if char.count('.') > 1:
            return False
        return all(c in "0123456789." for c in char)

    def validate_int_input(self, char):
        if char == "":
            return True
        return all(c in "0123456789" for c in char)
    
    def key_press(self, key):
        if (key == keyboard.Key.end):
            self.numClicksRemaining = 0
        elif (key == keyboard.Key.pause):
            self.isPaused = not self.isPaused
            if (not self.isPaused):
                self.nextClickIntervalMs = self.CLICKING_INIT_COUNTDOWN_MS
                self.timeAccumulatedMs = 0
                self.doubleclickDownBookmark = None
    
    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    window = Window()
    window.run()
