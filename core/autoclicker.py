"""
Module providing an Autoclicker class to manage the timing and execution of mouse clicks in a separate thread.
"""

import time
import threading
import random
from collections import deque
from pydirectinput import mouseDown, mouseUp ##type:ignore
from core.click_timer import ClickTimer, ClickType
from enum import Enum, auto

class ClickCycleType(Enum):
    """
    Represents the type of click cycle for an Autoclicker object to perform.

    Members:
        SINGLE: Perform a single click event (one mouse-down event quickly followed by one mouse-up event).
        TOGGLER: Perform a "toggling" click cycle (two click events in near-succession).
    """
    SINGLE = auto()
    TOGGLER = auto()

class Autoclicker:
    """
    Class to manage the timing and execution of mouse clicks in a separate thread.
    Execution does not begin until start() is called.
    """

    UPDATE_INTERVAL_SECS = .033 ##:Time in seconds between update calls.
    START_COUNTDOWN_MS = 5000 ##:Default time in milliseconds from starting the autoclicker to the first click.
    UNPAUSE_COUNTDOWN_MS = 3000 ##:Default time in milliseconds from unpausing the autoclicker to the next click.
    MOUSE_CLICK_LENGTH_RANGE_MS = (50, 125) ##:Range of time in milliseconds that a mouse click can be held down, randomized per click.
    MOUSE_TOGGLE_GAP_RANGE_MS = (125, 350) ##:Range of time in milliseconds between the first click's mouse-up and the second click's mouse-down for toggling clicks, randomized per click.

    def __init__(self):
        """
        Args:
            None
        """

        self._clicks = 0
        self._waitTimeMs = 0.0
        self._waitVariMs = 0.0
        self._clickCycleType = ClickCycleType.SINGLE
        self._isPaused = False

        #self._lock = threading.Lock() #TODO thread safety
        self._stop_event = threading.Event()
        self._thread : threading.Thread | None = None
        self._clicksQueue = deque[ClickTimer]()

    def __run__(self):
        """
        The main loop of the autoclicker thread. Calls an internal update at the interval defined by 
        UPDATE_INTERVAL_SECS until the stop event is set via stop().
        """

        lastUpdateTime = time.perf_counter()
        while not self._stop_event.is_set():
            thisUpdateTime = time.perf_counter()
            deltaTime = (thisUpdateTime - lastUpdateTime) * 1000
            lastUpdateTime = thisUpdateTime
            self.__update__(deltaTime)
            time.sleep(Autoclicker.UPDATE_INTERVAL_SECS)

    def __update__(self, delta_ms:float):
        """
        Internal update method.
        Args:
            delta_ms (float): The time in milliseconds since the previous update.
        """

        if self.is_paused: return
        if len(self._clicksQueue) == 0:
            self.stop()
            return
        
        self._clicksQueue[0].ingest_time_delta(delta_ms)
        if not self._clicksQueue[0].is_ready: return
        
        click = self._clicksQueue.popleft()
        mouseDown() if click.is_click_down else mouseUp()
        self._decrement_clickcount()
    
    @property
    def is_active(self) -> bool:
        """Whether the autoclicker is currently active (has an executing thread)."""

        return self._thread is not None and self._thread.is_alive()
    
    @property
    def is_paused(self) -> bool:
        """Whether the autoclicker is currently paused. The autoclicker can be active (have an executing thread) but be paused."""

        return self._isPaused
    
    @property
    def clicks_left(self) -> int:
        """The number of clicks remaining before the autoclicker stops, or -1 if set to click indefinitely."""

        return self._clicks
    
    @property
    def peek_next_click(self) -> ClickTimer | None:
        """Retrieve the next scheduled click event as a ClickTimer without removing it from the queue, 
        or None if there is no scheduled next click event."""

        return self._clicksQueue[0] if len(self._clicksQueue) > 0 else None

    def start(self,
            wait_time_ms:float,
            wait_variation_ms:float,
            num_clicks:int = -1,
            click_cycle_type:ClickCycleType = ClickCycleType.SINGLE
        ):
        """
        Start with the specified settings by creating a new thread. If already active, does nothing.
        Args:
            wait_time_ms (float): The base time in milliseconds to wait between clicks.
            wait_variation_ms (float): The maximum additional time in milliseconds to add to the base wait time between clicks, 
                randomized per click.
            num_clicks (int = -1): The number of clicks to execute before stopping, or -1 to click indefinitely. Defaults to -1.
            click_cycle_type (ClickCycleType = ClickCycleType.SINGLE): The type of click cycle to perform. 
                Defaults to ClickCycleType.SINGLE.
        """

        if self.is_active: return
        
        self._stop_event.clear()
        self._clicksQueue.clear()
        self._thread = threading.Thread(target=self.__run__, daemon=True)

        random.seed()
        self._clicks = num_clicks
        self._waitTimeMs = wait_time_ms
        self._waitVariMs = wait_variation_ms
        self._clickCycleType = click_cycle_type
        self._isPaused = False

        self._queue_click(Autoclicker.START_COUNTDOWN_MS)
        self._thread.start()

    def stop(self):
        """
        Clear the queue of all scheduled click events and end the thread cleanly. 
        Does not return until the thread has ended, after one autoclicker's update cycle.
        """

        self._stop_event.set()
        self._clicksQueue.clear()
        if self.is_active:
            assert self._thread is not None
            self._thread.join()

    def pause(self, do_pause:bool):
        """
        Pause or unpause the autoclicker. If unpausing, the next click will be scheduled for UNPAUSE_COUNTDOWN_MS milliseconds.
        If the autoclicker is inactive, does nothing.
        Args:
            do_pause (bool): Whether to pause (True) or unpause (False) the autoclicker.
        """

        if not self.is_active: return
        self._isPaused = do_pause
        if self._isPaused:
            if len(self._clicksQueue) > 0 and self._clicksQueue[0].is_click_up:
                #if user paused between 'down' and 'up', purge interrupted sequence FIXME optimize
                mouseUp()
                self._clicksQueue.clear()
                self._decrement_clickcount()
        else:
            if len(self._clicksQueue) > 0:
                self._clicksQueue[0] = ClickTimer(Autoclicker.UNPAUSE_COUNTDOWN_MS, self._clicksQueue[0].click_type)

    def _queue_click(self, time_ms:float|None = None):
        """
        Queue a click event to be executed after the specified time in milliseconds or after a 
        time determined by the autoclicker's wait time settings if no time is specified.
        Args:
            time_ms (float | None = None): The time in milliseconds to wait before executing the click event, 
                or None to use the autoclicker's wait time settings. Defaults to None
        """

        timeUntil = time_ms if time_ms is not None else (self._waitTimeMs + random.uniform(0, self._waitVariMs))
        holdTime = random.uniform(*self.MOUSE_CLICK_LENGTH_RANGE_MS)
        self._clicksQueue.append(ClickTimer(timeUntil, ClickType.DOWN))
        self._clicksQueue.append(ClickTimer(holdTime, ClickType.UP))
        if self._clickCycleType == ClickCycleType.TOGGLER:
            doubleClickTime = random.uniform(*self.MOUSE_TOGGLE_GAP_RANGE_MS)
            holdTime = random.uniform(*self.MOUSE_CLICK_LENGTH_RANGE_MS)
            self._clicksQueue.append(ClickTimer(doubleClickTime, ClickType.DOWN))
            self._clicksQueue.append(ClickTimer(holdTime, ClickType.UP))
    
    def _decrement_clickcount(self):
        """
        Decrement the click count if not set to click indefinitely, and stop if the click count reaches zero.
        """

        if len(self._clicksQueue) == 0:
            if (self._clicks > 0):
                self._clicks -= 1
            self.stop() if self._clicks == 0 else self._queue_click()
