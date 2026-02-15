"""
Module providing a ClickTimer class to manage the timing of mouse-down and mouse-up events 
and a ClickType enum for clarity in representing click types.
"""

from enum import Enum, auto

class ClickType(Enum):
    """
    Represents a mouse-down or mouse-up event.

    Members:
        DOWN: Represents a mouse-down event.
        UP: Represents a mouse-up event.
    """
    DOWN = auto()
    UP = auto()

class ClickTimer:
    """
    Class to manage the timing of mouse-down and mouse-up events. 
    The passage of time must be managed externally via ingest_time_delta(float).
    """
    
    def __init__(self, time_until_ms:float, click_type:ClickType):
        """
        Args:
            time_until_ms (float): The initial time until the click event in milliseconds.
            click_type (ClickType): Whether this ClickTimer represents a mouse-down event or a mouse-up event.
        """

        self._timeToMs = time_until_ms
        self._clickType = click_type

    def ingest_time_delta(self, delta:float):
        """
        Ingest a time delta in milliseconds, reducing the internal timer by that amount.
        Args:
            delta (float): The time delta to ingest in milliseconds.
        """

        self._timeToMs = max(0, self._timeToMs - delta)
    
    @property
    def is_ready(self) -> bool:
        """Whether the timer has reached zero, indicating that the click event should be triggered."""

        return self._timeToMs <= 0
    
    @property
    def time_remaining(self) -> float:
        """The remaining time until the click event in milliseconds."""

        return self._timeToMs
    
    @property
    def click_type(self) -> ClickType:
        """Whether this ClickTimer represents a mouse-down event or a mouse-up event."""

        return self._clickType

    @property
    def is_click_down(self) -> bool:
        """True if this ClickTimer represents a mouse-down event, False otherwise."""
        return self._clickType == ClickType.DOWN

    @property
    def is_click_up(self) -> bool:
        """True if this ClickTimer represents a mouse-up event, False otherwise."""
        return self._clickType == ClickType.UP
