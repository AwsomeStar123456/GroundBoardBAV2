# utils/airportwifi.py
"""
Aviation helpers on top of the project WiFi class.

METAR is fetched over plain HTTP first (Iowa State IEM).
aviationweather.gov HTTPS is only a fallback — TLS on Pico W
starts failing after the board has been up a while.
"""

import gc
import socket

try:
    import urequests as requests
except ImportError:
    try:
        import requests
    except ImportError:
        requests = None

from utils.wifi import WiFi


def _extract_metar_line(body_text, station):
    if not body_text:
        return None
    text = body_text.strip()
    if not text:
        return None
    station = (station or "").upper()
    lines = text.replace("\r", "\n").split("\n")
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        lower = line.lower()
        if lower.startswith("station,") or lower.startswith("<"):
            continue
        if "," in line:
            parts = line.split(",", 2)
            if len(parts) >= 3 and parts[2].strip():
                return parts[2].strip()
        if line.startswith("METAR ") or line.startswith("SPECI "):
            return line
        if station and line.startswith(station):
            return line
        if "KT" in line and len(line) > 20:
            return line
    return lines[0].strip() if lines else None


class AirportWiFi(WiFi):
    """
    Same connection API as WiFi, plus METAR helpers.
    """

    def get(self, url, headers=None, timeout=15):
        if not self.is_connected():
            print("Not connected to WiFi")
            return None
        if requests is None:
            print("urequests not available")
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
                print("Rate limited")
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

    def get_http_text(self, host, path, timeout_s=15, max_bytes=2048):
        s = None
        try:
            gc.collect()
            addr = socket.getaddrinfo(host, 80)[0][-1]
            print("Resolved", host, "to", addr)
            s = socket.socket()
            s.settimeout(timeout_s)
            s.connect(addr)
            req = (
                "GET {} HTTP/1.0\r\n"
                "Host: {}\r\n"
                "User-Agent: GroundBoardBA\r\n"
                "Accept: text/plain,*/*\r\n"
                "Connection: close\r\n\r\n"
            ).format(path, host)
            s.send(req.encode())
            buf = bytearray()
            while len(buf) < max_bytes:
                try:
                    chunk = s.recv(256)
                except Exception:
                    break
                if not chunk:
                    break
                buf.extend(chunk)
            sep = buf.find(b"\r\n\r\n")
            if sep < 0:
                print("HTTP: bad response")
                return None
            header = bytes(buf[:sep]).decode("latin-1")
            status = 0
            try:
                status = int(header.split("\r\n", 1)[0].split(" ")[1])
            except Exception:
                pass
            if status != 200:
                print("HTTP", status)
                return None
            body = bytes(buf[sep + 4 :])
            try:
                return body.decode("utf-8")
            except Exception:
                return body.decode("latin-1")
        except Exception as e:
            print("HTTP get failed:", e)
            return None
        finally:
            if s is not None:
                try:
                    s.close()
                except Exception:
                    pass
            gc.collect()

    def get_metar(self, icao, fmt="raw"):
        icao = (icao or "").upper().strip()
        if not icao:
            return None

        iem_path = (
            "/cgi-bin/request/asos.py?station={}"
            "&data=metar&hours=2&tz=UTC&format=onlycomma"
            "&latlon=no&elev=no&missing=empty&trace=empty"
            "&direct=no&report_type=3"
        ).format(icao)

        print("METAR IEM HTTP", icao)
        body = self.get_http_text("mesonet.agron.iastate.edu", iem_path, timeout_s=15)
        line = _extract_metar_line(body, icao) if body else None
        if line:
            print("METAR raw:", line)
            return line

        print("METAR IEM failed, trying aviationweather.gov")
        url = "https://aviationweather.gov/api/data/metar?ids={}&format={}".format(icao, fmt)
        text = self.get(url, headers={"User-Agent": "PicoW-METAR/1.0 (aviation project)"})
        if not text:
            return None
        line = _extract_metar_line(text, icao)
        if line:
            print("METAR raw:", line)
        return line

    def get_https_text(self, host, path, timeout_s=20):
        import ssl
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
            print("HTTPS: bad HTTP response")
            return None
        header = raw[:sep].decode("latin-1")
        body = raw[sep + 4 :]
        status = 0
        try:
            status = int(header.split("\r\n", 1)[0].split(" ")[1])
        except Exception:
            pass
        if status != 200:
            print("HTTPS HTTP", status)
            return None
        try:
            return body.decode("utf-8")
        except Exception:
            return body.decode("latin-1")
