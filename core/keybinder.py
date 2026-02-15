"""
Module providing a Keybinder class to manage the assignment and retrieval of a keybind.
"""

from pynput import keyboard

class Keybinder:
    """
    Class to store and retrieve a keybind, and assign a new keybind if actively listening (managed externally).
    """

    def __init__(self, default_key:keyboard.Key|keyboard.KeyCode|None = None):
        """
        Args:
            default_key (keyboard.Key | keyboard.KeyCode | None): Optional default keybind upon initialization. Defaults to None (unassigned).
        """

        self._isListening = False
        self._assignedKey = default_key
    
    @property
    def is_listening(self) -> bool:
        """Whether the keybinder is currently listening for a new key assignment."""

        return self._isListening
    
    @property
    def get_key(self) -> keyboard.Key|keyboard.KeyCode|None:
        """The currently assigned keybind as (keyboard.Key | keyboard.KeyCode), or None if unassigned."""

        return self._assignedKey

    def set_listening(self, value:bool):
        """
        Set whether the Keybinder is listening for a new key assignment.
        Args:
            value (bool): Whether the Keybinder should accept a new key for assignment.
        """

        self._isListening = value

    def try_set_key(self, key:keyboard.Key|keyboard.KeyCode|None):
        """
        Assign the provided key if Keybinder is listening, then stop listening. If not listening, does nothing.
        Args:
            key (keyboard.Key | keyboard.KeyCode | None): The key to assign if currently listening.
        """

        if not self.is_listening: return
        self._assignedKey = key
        self._isListening = False
