from machine import Pin
import utime

class Button:


    #pin_num     : GPIO number
    #callback    : function to call when button is pressed
    #debounce_ms : ignore extra presses for this many milliseconds
    def __init__(self, pin_num, callback=None, debounce_ms=1000):
        self.pin = Pin(pin_num, Pin.IN, Pin.PULL_UP)
        self.callback = callback
        self.debounce_ms = debounce_ms
        self._last_press = 0

    def enable(self):
        self.pin.irq(trigger=Pin.IRQ_FALLING, handler=self._handler)

    def _handler(self, pin):
        now = utime.ticks_ms()
        if utime.ticks_diff(now, self._last_press) < self.debounce_ms:
            return                      # still in debounce window → ignore

        self._last_press = now

        if self.callback:
            self.callback()             # call the function you passed in