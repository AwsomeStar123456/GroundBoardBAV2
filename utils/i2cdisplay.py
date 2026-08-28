# utils/i2cdisplay.py
from machine import I2C, Pin
from lib.ssd1309 import Display
import framebuf
import math


class I2CDisplay:
    WIDTH = 128
    HEIGHT = 64
    CHAR_W = 8
    ROW_H = 11
    MAX_ROWS = 6
    FONT_H = 8

    def __init__(self, scl=5, sda=4, rst=2, flip=True, i2c_id=0, freq=400_000):
        self.display = None
        self.rows = [""] * self.MAX_ROWS
        self._bitmaps_bg = {}
        self._bitmaps_fg = {}
        self._hlines = []          # list of (x, y, w, dash, gap)
        self._border = False
        self._border_inset = 0
        self._dash_len = 4
        self._gap_len = 5

        try:
            self.i2c = I2C(i2c_id, freq=freq, scl=Pin(scl), sda=Pin(sda))
            self.display = Display(i2c=self.i2c, rst=Pin(rst), flip=flip)
            print("Display initialized OK")
        except Exception as e:
            print("Display not found or failed to init:", e)

    # ------------------------------------------------------------------
    # Text
    # ------------------------------------------------------------------
    def set_row(self, row, text):
        if 0 <= row < self.MAX_ROWS:
            self.rows[row] = str(text)

    def clear_rows(self):
        self.rows = [""] * self.MAX_ROWS

    def _draw_centered(self, text, row):
        if self.display is None:
            return
        text = str(text)
        if not text:
            return
        text_width = len(text) * self.CHAR_W
        x = max(0, (self.WIDTH - text_width) // 2)
        y = 1 + row * self.ROW_H
        self.display.monoFB.text(text, x, y)

    def _row_text_bottom(self, row):
        return 1 + row * self.ROW_H + self.FONT_H

    def _separator_y(self, after_row):
        """Pixel row in the 3px gap under a text row."""
        return self._row_text_bottom(after_row) + 1

    # ------------------------------------------------------------------
    # Lines / sections
    # ------------------------------------------------------------------
    def add_hline(self, y=None, after_row=None, x=2, width=121,
                  dash=None, gap=None):
        """
        Queue a dashed horizontal rule for the next refresh.

        y          - absolute pixel row (0-63). Overrides after_row.
        after_row  - draw in the gap below this text row (0-4).
        x, width   - inset from the edges so it does not collide with a border.
        dash, gap  - on/off pixel lengths. Defaults 4 / 3.
        """
        if y is None:
            if after_row is None:
                return
            if not (0 <= after_row <= self.MAX_ROWS - 2):
                return
            y = self._separator_y(after_row)

        if y < 0 or y >= self.HEIGHT:
            return

        x = max(0, int(x))
        width = max(1, min(int(width), self.WIDTH - x))
        dash_len = self._dash_len if dash is None else max(1, int(dash))
        gap_len = self._gap_len if gap is None else max(1, int(gap))
        self._hlines.append((x, int(y), width, dash_len, gap_len))

    def add_separator(self, after_row):
        """Draw a dashed rule in the gap below a text row."""
        self.add_hline(after_row=after_row)

    def clear_hlines(self):
        self._hlines = []

    def set_border(self, enabled=True, inset=0):
        """
        Optional 1px outline around the panel.

        Not a great default: row 5 text already ends on y=63, so inset=0
        overwrites the bottom of the last line. Prefer add_separator().
        """
        self._border = bool(enabled)
        self._border_inset = max(0, int(inset))

    def _draw_dashed_hline(self, fb, x, y, width, dash_len, gap_len):
        """Draw a 1px dashed rule clipped to [x, x+width)."""
        if width <= 0:
            return
        pos = x
        end = x + width
        while pos < end:
            seg_end = min(pos + dash_len, end)
            fb.hline(pos, y, seg_end - pos, 1)
            pos = seg_end + gap_len

    # ------------------------------------------------------------------
    # Bitmaps
    # ------------------------------------------------------------------
    def add_bitmap(self, key, fb, x, y, layer="bg"):
        if fb is None:
            return
        if layer == "fg":
            self._bitmaps_fg[key] = (fb, x, y)
        else:
            self._bitmaps_bg[key] = (fb, x, y)

    def remove_bitmap(self, key):
        self._bitmaps_bg.pop(key, None)
        self._bitmaps_fg.pop(key, None)

    def clear_bitmaps(self):
        self._bitmaps_bg.clear()
        self._bitmaps_fg.clear()

    def set_rotated_bitmap(self, key, bitmap_bytes, width, height, x, y,
                           degrees, layer="bg", quantize_deg=5):
        """
        Rotate a 1-bit bitmap and add it to the display.

        key           - unique name (e.g. "arrow")
        bitmap_bytes  - original bytearray (Arrow, ByteSunny, etc.)
        width, height - size of the bitmap
        x, y          - screen position
        degrees       - clockwise rotation
        layer         - "bg" or "fg"
        quantize_deg  - snap angle to nearest step (default 5°)
        """
        if self.display is None or bitmap_bytes is None:
            return

        deg = float(degrees) % 360.0
        if quantize_deg and quantize_deg > 0:
            deg = round(deg / quantize_deg) * quantize_deg

        fmt = framebuf.MONO_HMSB
        w = int(width)
        h = int(height)

        if deg == 0.0:
            rotated = bitmap_bytes
        else:
            src_fb = framebuf.FrameBuffer(bitmap_bytes, w, h, fmt)
            dst_buf = bytearray(len(bitmap_bytes))
            dst_fb = framebuf.FrameBuffer(dst_buf, w, h, fmt)

            theta = math.radians(deg)
            c = math.cos(theta)
            s = math.sin(theta)
            cx = (w - 1) / 2.0
            cy = (h - 1) / 2.0

            for y_pos in range(h):
                y0 = y_pos - cy
                for x_pos in range(w):
                    x0 = x_pos - cx
                    xs = x0 * c + y0 * s + cx
                    ys = -x0 * s + y0 * c + cy

                    xi = int(xs + 0.5) if xs >= 0 else int(xs - 0.5)
                    yi = int(ys + 0.5) if ys >= 0 else int(ys - 0.5)

                    if 0 <= xi < w and 0 <= yi < h:
                        if src_fb.pixel(xi, yi):
                            dst_fb.pixel(x_pos, y_pos, 1)

            rotated = dst_buf

        fb = framebuf.FrameBuffer(rotated, w, h, fmt)
        self.add_bitmap(key, fb, x, y, layer=layer)

    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------
    def refresh(self):
        if self.display is None:
            return
        self.display.clear_buffers()
        fb = self.display.monoFB

        if self._border:
            i = self._border_inset
            fb.rect(i, i, self.WIDTH - 2 * i, self.HEIGHT - 2 * i, 1)

        for bmp, bx, by in self._bitmaps_bg.values():
            if bmp is not None:
                fb.blit(bmp, bx, by)

        for x, y, w, dash_len, gap_len in self._hlines:
            self._draw_dashed_hline(fb, x, y, w, dash_len, gap_len)

        for i, text in enumerate(self.rows):
            self._draw_centered(text, i)

        for bmp, bx, by in self._bitmaps_fg.values():
            if bmp is not None:
                fb.blit(bmp, bx, by)

        self.display.present()

    def clear(self):
        self.clear_rows()
        self.clear_bitmaps()
        self.clear_hlines()
        self._border = False
        if self.display:
            self.display.clear()

    def show_message(self, *lines):
        self.clear()
        for i, line in enumerate(lines[:self.MAX_ROWS]):
            self.set_row(i, line)
        self.refresh()
