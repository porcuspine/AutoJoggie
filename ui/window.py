"""
This module contains the Window class, which is responsible for creating the application's user interface and 
handles the user's interactions with the autoclicker.
"""

from core.keybinder import Keybinder
from core.autoclicker import Autoclicker, ClickCycleType
from ui.field_validator import FieldValidator
from tkinter import Tk, Frame, Label, Button, Entry, Checkbutton
from tkinter import messagebox
from tkinter import BooleanVar
from tkinter import PhotoImage
from functools import partial
from pynput import keyboard
from typing import Literal

VER = "0.7.1"

class AutoclickerWindow:
    """
    Class to create and manage the user interface and facilitate user interactions with the autoclicker.
    """

    UI_UPDATE_MS = 50 ##:Time in milliseconds between UI updates. 50ms = ~20 FPS.
    KEYBIND_HINT_PASSIVE = "Click here to rebind" ##:Text to display on keybind buttons when not actively listening for a new keybind.
    KEYBIND_HINT_ACTIVE = "Press any key..." ##:Text to display on keybind buttons while actively listening for a new keybind.

    def __init__(self, autoclicker:Autoclicker, ico_path:str):
        """
        Args:
            autoclicker (Autoclicker): The Autoclicker object to manage with this UI.
        """

        self.root = Tk()
        self.root.title(f'AutoJoggie v{VER}')
        self._icon = PhotoImage(file=ico_path) ##type:ignore
        self.root.iconphoto(True, self._icon) ##type:ignore
        self.root.minsize(height=0, width=250)
        self.root.resizable(False, False)
        self.root.attributes('-topmost', True) ##type:ignore

        self._autoclicker = autoclicker
        self._keyListener = keyboard.Listener(on_press=self._handle_keypress)
        self._pauseKeybind = Keybinder(default_key=keyboard.Key.home)
        self._stopKeybind = Keybinder(default_key=keyboard.Key.end)
        self.__alive__ = False ##:Whether the UI loop is currently running. Should be set only within start()

        self._build()

    def __update__(self):
        """Internal ui update method."""

        self._set_ui_state("normal" if not self._autoclicker.is_active else "disabled")

        if not self._autoclicker.is_active:
            readoutText = "{Clicker is inactive}"
            self.readoutLabel.config(text=readoutText)
            return

        readoutText = str()
        nextClick = self._autoclicker.peek_next_click
        timeLeftLabel = "Now!" if nextClick is None or nextClick.is_click_up else f"{nextClick.time_remaining/1000:.2f}s"
        if self._autoclicker.is_paused:
            if self._autoclicker.clicks_left == -1:
                readoutText = f"(Clicking is paused)\n"
            else:
                readoutText = f"{self._autoclicker.clicks_left} clicks left.\n(Clicking is paused)"
        elif self._autoclicker.clicks_left < 0:
            readoutText = f"Clicking infinitely!\nNext click: {timeLeftLabel}"
        else:
            readoutText = f"{self._autoclicker.clicks_left} clicks left.\nNext click: {timeLeftLabel}"
        self.readoutLabel.config(text=readoutText)

    def __uiloop__(self):
        """Method to update the UI at a regular interval defined by UI_UPDATE_MS. Should be called only once to start the loop."""

        self.__update__()
        self.root.after(AutoclickerWindow.UI_UPDATE_MS, self.__uiloop__)

    def start(self):
        """
        Activate the UI if not so already.
        Will show a message box and destroy the window if a fatal error occurs during runtime.
        """

        if self.__alive__:
            return

        try:
            self.__alive__ = True
            self._keyListener.start()
            self.__uiloop__()
            self.root.mainloop()
        except:
            self.__alive__ = False
            messagebox.showerror("Fatal Error!", "A fatal error occurred", parent=self.root)
            self.root.destroy()
            return
    
    @staticmethod
    def format_keybind_name(keybinder:Keybinder) -> str:
        """
        @staticmethod

        Format a keybinder's assigned key into a user-friendly string for display in the UI.
        Args:
            keybinder (Keybinder): The Keybinder whose assigned key to format.
        """

        key = keybinder.get_key
        if key is None:
            return "unbound"
        if isinstance(key, keyboard.KeyCode):
            return key.char.upper() if key.char else '□'
        else:
            name = key.name.replace('_', ' ').title()
            if name.endswith(' R'):
                name = f"Right {name[:-2]}"
            elif name.endswith(' L'):
                name = f"Left {name[:-2]}"
            return name

    def _build(self):
        """Build the window's components and layout."""

        bindsFrame = Frame(self.root)
        bindsFrame.pack(pady=10)

        pauseColumn = Frame(bindsFrame)
        pauseColumn.pack(side="left", padx=15)
        self.pauseBindLabel = Label(pauseColumn)
        self.pauseBindLabel.pack()
        self.pauseBindButton = Button(pauseColumn, text=AutoclickerWindow.KEYBIND_HINT_PASSIVE, width=16, 
            command=partial(self._set_keybind_listening, self._pauseKeybind))
        self.pauseBindButton.pack(pady=(4,0))

        stopColumn = Frame(bindsFrame)
        stopColumn.pack(side="left", padx=15)
        self.stopBindLabel = Label(stopColumn)
        self.stopBindLabel.pack()
        self.stopBindButton = Button(stopColumn, text=AutoclickerWindow.KEYBIND_HINT_PASSIVE, width=16,
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
        self.waitTimeField.insert(0, "2.75")
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
        Label(checkboxFrame, text="Click twice?").pack(side="left")
        self._doubleclick = BooleanVar(value=True)
        self.doDoubleclickCheckbox = Checkbutton(checkboxFrame, variable=self._doubleclick, pady=0)
        self.doDoubleclickCheckbox.pack(side="left")
        Label(self.root, text="(e.g. alching, toggling prayer...)").pack(pady=(0,10))

        self.startButton = Button(self.root, text="Start", command=self._try_start, width = 10)
        self.startButton.pack(pady=(10, 0))

        self.readoutLabel = Label(self.root, text="")
        self.readoutLabel.pack(pady=(10, 10))

        self._update_keybind_hints()
        self._set_ui_state("normal")

    def _set_ui_state(self, state:Literal["normal", "disabled"]):
        """
        Set the state of the UI components to either "normal" or "disabled".
        Args:
            state (Literal['normal', 'disabled']): The state to set the UI components to.
        """

        self.numClicksField.config(state=state)
        self.waitTimeField.config(state=state)
        self.waitVariField.config(state=state)
        self.startButton.config(state=state)
        self.doDoubleclickCheckbox.config(state=state)
        self.pauseBindButton.config(state=state)
        self.stopBindButton.config(state=state)
    
    def _set_keybind_listening(self, keybind:Keybinder|None):
        """
        Enable listening for the given keybinder and disable the other, or
        disable listening for both keybinders if None is given.

        Calls _update_keybind_hints().
        """

        self._pauseKeybind.set_listening(keybind is self._pauseKeybind)
        self._stopKeybind.set_listening(keybind is self._stopKeybind)
        self._update_keybind_hints()
    
    def _update_keybind_hints(self):
        """Update the text of the keybind buttons and labels based on current state."""

        self.pauseBindButton.config(text=AutoclickerWindow.KEYBIND_HINT_ACTIVE if self._pauseKeybind.is_listening else AutoclickerWindow.KEYBIND_HINT_PASSIVE)
        self.stopBindButton.config(text=AutoclickerWindow.KEYBIND_HINT_ACTIVE if self._stopKeybind.is_listening else AutoclickerWindow.KEYBIND_HINT_PASSIVE)
        self.pauseBindLabel.config(text=f"PAUSE: [{AutoclickerWindow.format_keybind_name(self._pauseKeybind)}]")
        self.stopBindLabel.config(text=f"STOP: [{AutoclickerWindow.format_keybind_name(self._stopKeybind)}]")

    def _try_start(self):
        """
        Retrieve parameters from the UI and validate them, displaying an error messagebox if invalid.
        Then request to start the autoclicker with the given parameters.
        Does nothing if the autoclicker is already active.
        """

        if self._autoclicker.is_active:
            return
        try:
            numClicks = int(self.numClicksField.get() or -1)
            if numClicks == 0: numClicks = -1
            waitTimeMs = float(self.waitTimeField.get()) * 1000
            waitVariMs = float(self.waitVariField.get()) * 1000
            doDoubleClick = bool(self._doubleclick.get())
        except ValueError:
            messagebox.showerror("Input Error", "Please correctly and completely fill out the config window.", parent=self.root)
            return
        self._autoclicker.start(waitTimeMs, waitVariMs, numClicks, ClickCycleType.TOGGLER if doDoubleClick else ClickCycleType.SINGLE)
    
    def _stop_clicker(self):
        """Call .stop() on the autoclicker."""

        self._autoclicker.stop()

    def _handle_keypress(self, key:keyboard.Key|keyboard.KeyCode|None):
        """
        Digest a provided keypress.
        
        If Esc is pressed, unbinds any listening keybinders and returns.
        If the pressed key corresponds to the pause or stop keybinds, triggers the corresponding action and returns.
        If neither of the previous cases, assigns the pressed key to any listening keybinders. 
        
        Args:
            key (keyboard.Key | keyboard.KeyCode | None): The key that was pressed.
        """

        if key is None: return
        if key == keyboard.Key.esc:
            self._pauseKeybind.try_set_key(None)
            self._stopKeybind.try_set_key(None)
            self._set_keybind_listening(None)
            return
        if key == self._pauseKeybind.get_key:
            self._autoclicker.pause(not self._autoclicker.is_paused)
            return
        if key == self._stopKeybind.get_key:
            self._stop_clicker()
            return
        self._pauseKeybind.try_set_key(key)
        self._stopKeybind.try_set_key(key)
        self._update_keybind_hints()
