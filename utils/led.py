# utils/led.py
"""
WS2811 / WS2812 LED driver for Pico.
"""

from machine import Pin
import time
import math

try:
    import neopixel
except ImportError:
    neopixel = None


# ---------------------------------------------------------------------------
# Colours (R, G, B)
# ---------------------------------------------------------------------------
OFF     = (0, 0, 0)
RED     = (255, 0, 0)
ORANGE  = (255, 100, 0)
YELLOW  = (255, 255, 0)
GREEN   = (0, 255, 0)
CYAN    = (0, 255, 255)
BLUE    = (0, 0, 255)
MAGENTA = (255, 0, 255)
PINK    = (255, 40, 140)
WHITE   = (255, 255, 255)


def _scale(color, factor):
    """Multiply each channel by factor (0.0–1.0)."""
    return tuple(int(c * factor) for c in color)


# ---------------------------------------------------------------------------
# LED – low-level strip driver
# ---------------------------------------------------------------------------
class LED:
    """
    Driver for a WS2811 / WS2812 strip.

    pin_num    : GPIO number
    num_leds   : number of LEDs
    brightness : 0 – 100 (integer percent)
    order      : "GRB" (most common) or "RGB"
    """

    def __init__(self, pin_num, num_leds, brightness=30, order="GRB"):
        if neopixel is None:
            raise RuntimeError("neopixel module not available")

        self.num_leds = int(num_leds)
        self.brightness = max(0, min(100, int(brightness)))
        self.order = order.upper()
        self.np = neopixel.NeoPixel(Pin(pin_num), self.num_leds)
        self.clear()

    def _to_strip(self, color):
        r, g, b = color
        if self.order == "GRB":
            return (g, r, b)
        return (r, g, b)          # RGB fallback

    def set_brightness(self, brightness):
        self.brightness = max(0, min(100, int(brightness)))

    def clear(self):
        for i in range(self.num_leds):
            self.np[i] = (0, 0, 0)
        self.np.write()

    def fill(self, color, brightness=None):
        br = self.brightness if brightness is None else brightness
        factor = br / 100.0
        c = self._to_strip(_scale(color, factor))
        for i in range(self.num_leds):
            self.np[i] = c
        self.np.write()

    def set(self, index, color, brightness=None):
        """Set one LED. Call show() afterwards."""
        if 0 <= index < self.num_leds:
            br = self.brightness if brightness is None else brightness
            factor = br / 100.0
            self.np[index] = self._to_strip(_scale(color, factor))

    def show(self):
        self.np.write()

    def __len__(self):
        return self.num_leds

    def startup(self, delay_ms=250, clear=False):
        """
        Cycle every colour through every LED, one LED at a time.
        Only one LED is lit at any moment.
        """
        colors = (RED, GREEN, BLUE, WHITE)
        #colors = (OFF,RED,ORANGE,YELLOW,GREEN,CYAN,BLUE,MAGENTA,WHITE)

        for i in range(self.num_leds):
            for color in colors:
                self.set(i, color)
                self.show()
                time.sleep_ms(delay_ms)

        if clear:
            self.clear()


# ---------------------------------------------------------------------------
# Wind helpers
# ---------------------------------------------------------------------------
def angle_diff(a, b):
    """Smallest signed difference a-b in degrees (-180 … +180)."""
    return (a - b + 180) % 360 - 180


def wind_components(runway_heading, wind_dir, wind_speed):
    """
    Return (headwind, crosswind) in knots relative to runway_heading.

    Positive headwind  = wind from the front (good for landing on that runway).
    Positive crosswind = wind from the right.
    """
    # Wind is reported "from". Aircraft on runway faces runway_heading.
    delta = angle_diff(wind_dir, (runway_heading + 180) % 360)
    rad = math.radians(delta)
    head = wind_speed * math.cos(rad)
    cross = wind_speed * math.sin(rad)
    return head, cross


def wind_color(runway_heading, wind_dir, wind_speed, calm_threshold=3.0):
    """
    Colour that represents how favourable the wind is for a given runway heading.

    Returns (color, headwind, crosswind).
    Colour is full strength; overall brightness is applied by the LED strip.
    """
    if wind_speed is None or wind_dir is None:
        return OFF, 0.0, 0.0

    #print("wind_speed:", wind_speed, "calm_threshold:", calm_threshold, "wind_direction:", wind_dir)
    if wind_dir is -1:
        if wind_speed > calm_threshold:
            return YELLOW, -1, -1
        else:
            return GREEN, -1, -1

    head, cross = wind_components(runway_heading, wind_dir, wind_speed)
    abs_cross = abs(cross)

    if wind_speed == 0:
        return GREEN, head, cross

    # Strong tailwind → red
    if head < 0:
        return RED, head, cross

    # Strong crosswind → amber / yellow
    if abs_cross > calm_threshold:
        return YELLOW, head, cross

    # Good headwind → green
    if head > 0:
        return GREEN, head, cross

    # Light / variable
    return GREEN, head, cross


# ---------------------------------------------------------------------------
# WeatherLights – one LED per runway heading
# ---------------------------------------------------------------------------
class WeatherLights:
    """
    Each LED is assigned a runway heading.
    Colour shows how favourable the current wind is for that runway.

    Example:
        wx = WeatherLights(
            pin=0,
            headings=[160, 340],   # LED 0 → 16R, LED 1 → 34L
            brightness=40,
        )
        wx.startup()
        wx.update(wind_dir=10, wind_speed=3)
    """

    def __init__(self, pin, headings, brightness=30, order="GRB", name="WX"):
        if not headings:
            raise ValueError("headings must contain at least one runway heading")

        self.headings = [float(h) for h in headings]
        self.strip = LED(pin, len(self.headings), brightness=brightness, order=order)
        self.name = name
        self._last_wind = (None, None)

    def set_brightness(self, brightness):
        self.strip.set_brightness(brightness)

    def clear(self):
        self.strip.clear()

    def startup(self, delay_ms=250, clear=False):
        self.strip.startup(delay_ms=delay_ms, clear=clear)

    def fill(self, color):
        """Solid colour on every weather LED (AP mode, errors, etc.)."""
        self.strip.fill(color)

    def update(self, wind_dir, wind_speed, calm_threshold=5.0):
        """
        Recolour every LED based on wind relative to its assigned heading.
        Returns list of (heading, headwind, crosswind) for each LED.
        """
        wind_dir=(wind_dir + 180) % 360

        results = []
        factor = self.strip.brightness / 100.0
        for i, hdg in enumerate(self.headings):
            color, head, cross = wind_color(hdg, wind_dir, wind_speed, calm_threshold)
            self.strip.np[i] = self.strip._to_strip(_scale(color, factor))
            results.append((hdg, head, cross))

        self.strip.show()
        self._last_wind = (wind_dir, wind_speed)
        return results

    def status(self):
        return {
            "name": self.name,
            "headings": self.headings,
            "num_leds": len(self.headings),
            "last_wind": self._last_wind,
        }
