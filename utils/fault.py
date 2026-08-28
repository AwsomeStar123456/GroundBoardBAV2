# utils/fault.py
"""Best-effort error screen + red LEDs so a crash does not freeze blank."""

from utils.led import RED


def _short(text, n=16):
    if text is None:
        return ""
    try:
        s = str(text)
    except Exception:
        return "Error"
    if len(s) <= n:
        return s
    return s[: n - 1] + "."


def show_error(display=None, leds=None, title="Error", line1="", line2=""):
    try:
        if leds is not None:
            if hasattr(leds, "fill"):
                leds.fill(RED)
            elif hasattr(leds, "strip"):
                leds.strip.fill(RED)
                leds.strip.show()
    except Exception:
        pass

    try:
        if display is not None:
            display.show_message(*[
                "RunwaySense",
                _short(title, 16),
                "",
                _short(line1, 16),
                _short(line2, 16),
                "Check / Retry",
            ])
    except Exception:
        try:
            print("ERROR:", title, line1, line2)
        except Exception:
            pass


def exception_lines(exc):
    name = type(exc).__name__ if exc is not None else "Error"
    msg = ""
    try:
        msg = str(exc)
    except Exception:
        msg = ""
    return name, msg
