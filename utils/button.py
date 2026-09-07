from machine import Pin
import utime


class Button:
    """
    Active-low button with internal pull-up.

    IRQ only records an edge. poll() must confirm the pin is still held
    low before the callback runs. That stops WiFi/LED electrical noise
    from looking like a press.
    """

    def __init__(self, pin_num, callback=None, debounce_ms=1000, hold_ms=50, quiet_ms=800):
        self.pin = Pin(pin_num, Pin.IN, Pin.PULL_UP)
        self.callback = callback
        self.debounce_ms = debounce_ms
        self.hold_ms = hold_ms
        self.quiet_ms = quiet_ms
        self._last_fire = utime.ticks_ms()
        self._enabled_at = utime.ticks_ms()
        self._pending = False
        self._down_at = 0

    def enable(self):
        self._pending = False
        self._enabled_at = utime.ticks_ms()
        self.pin.irq(trigger=Pin.IRQ_FALLING, handler=self._handler)

    def disable(self):
        try:
            self.pin.irq(handler=None)
        except Exception:
            pass
        self._pending = False

    def raw_down(self):
        try:
            return self.pin.value() == 0
        except Exception:
            return False

    def _handler(self, pin):
        # IRQ context: no allocations, no callback.
        try:
            if pin.value() != 0:
                return
            now = utime.ticks_ms()
            if utime.ticks_diff(now, self._enabled_at) < self.quiet_ms:
                return
            if utime.ticks_diff(now, self._last_fire) < self.debounce_ms:
                return
            if not self._pending:
                self._pending = True
                self._down_at = now
        except Exception:
            pass

    def poll(self):
        """
        Call from the main loop (or AP should_exit).
        Returns True once when a press is confirmed.
        """
        now = utime.ticks_ms()

        if not self._pending:
            # Catch a button already held if the falling edge was missed.
            if self.raw_down() and utime.ticks_diff(now, self._enabled_at) >= self.quiet_ms:
                if utime.ticks_diff(now, self._last_fire) >= self.debounce_ms:
                    self._pending = True
                    self._down_at = now
            return False

        if not self.raw_down():
            self._pending = False
            return False

        if utime.ticks_diff(now, self._down_at) < self.hold_ms:
            return False

        self._pending = False
        self._last_fire = now
        if self.callback:
            try:
                self.callback()
            except Exception:
                pass
        return True
