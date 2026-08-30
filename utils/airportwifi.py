# utils/airportwifi.py
"""
Aviation helpers on top of the project WiFi class.

Imports the connection logic from wifi.py and adds:
  - generic HTTP GET
  - get_metar()
  - get_https_text()
"""

import gc
import time

try:
    import urequests as requests
except ImportError:
    import requests

from utils.wifi import WiFi


class AirportWiFi(WiFi):
    """
    Same connection API as WiFi, plus METAR and ADS-B helpers.
    """

    # ------------------------------------------------------------------
    # Generic HTTP helper
    # ------------------------------------------------------------------
    def get(self, url, headers=None, timeout=15):
        if not self.is_connected():
            print("Not connected to WiFi")
            return None
        if headers is None:
            headers = {"User-Agent": "Mozilla/5.0 (PicoW)"}
        resp = None
        try:
            gc.collect()
            resp = requests.get(url, headers=headers, timeout=timeout)
            code = resp.status_code
            if code == 200:
                text = resp.text
                return text
            print("HTTP", code)
            if code == 429:
                print("Rate limited – wait before next ADS-B poll")
            return None
        except Exception as e:
            print("Request failed:", type(e).__name__, e)
            return None
        finally:
            if resp is not None:
                try:
                    resp.close()
                except Exception:
                    pass
            gc.collect()

    # ------------------------------------------------------------------
    # Aviation-specific helpers
    # ------------------------------------------------------------------
    def get_metar(self, icao, fmt="raw"):
        """
        Fetch the latest METAR for an airport (ICAO code).
        fmt = "raw" or "json"
        """
        icao = icao.upper().strip()
        url = "https://aviationweather.gov/api/data/metar?ids={}&format={}".format(icao, fmt)
        headers = {"User-Agent": "PicoW-METAR/1.0 (aviation project)"}
        return self.get(url, headers=headers)

    def get_https_text(self, host, path, timeout_s=20):
        import socket, ssl, gc
        gc.collect()
        addr = socket.getaddrinfo(host, 443)[0][-1]
        s = socket.socket()
        s.settimeout(timeout_s)
        s.connect(addr)
        ss = None
        raw = b""
        try:
            try:
                ss = ssl.wrap_socket(s, server_hostname=host)
            except TypeError:
                ss = ssl.wrap_socket(s)
            req = (
                "GET {} HTTP/1.0\r\n"
                "Host: {}\r\n"
                "User-Agent: Mozilla/5.0 (PicoW Aviation)\r\n"
                "Accept: application/json\r\n"
                "Connection: close\r\n\r\n"
            ).format(path, host)
            ss.write(req.encode())
            chunks = []
            while True:
                try:
                    chunk = ss.read(1024)
                except Exception:
                    break
                if not chunk:
                    break
                chunks.append(chunk)
            raw = b"".join(chunks)
        finally:
            if ss is not None:
                try:
                    ss.close()
                except Exception:
                    pass
            try:
                s.close()
            except Exception:
                pass
            gc.collect()

        sep = raw.find(b"\r\n\r\n")
        if sep < 0:
            print("ADS-B: bad HTTP response")
            return None
        header = raw[:sep].decode("latin-1")
        body = raw[sep + 4 :]
        status = 0
        try:
            status = int(header.split("\r\n", 1)[0].split(" ")[1])
        except Exception:
            pass
        if status != 200:
            print("ADS-B HTTP", status)
            return None
        try:
            return body.decode("utf-8")
        except Exception:
            return body.decode("latin-1")
