import network
import time
import gc
import utime

try:
    import urequests as requests
except ImportError:
    import requests


class WiFi:

    def __init__(self):
        self.wlan = network.WLAN(network.STA_IF)
        self._ntp_ok = False

        try:
            self.wlan.active(False)
        except Exception:
            pass
        utime.sleep(0.25)

        try:
            self.wlan.active(True)
        except Exception:
            pass
        utime.sleep(0.25)

        # Disable power saving — Pico W drops traffic in sleep otherwise
        try:
            self.wlan.config(pm=0xa11140)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Connection & scanning
    # ------------------------------------------------------------------
    def scan(self):
        """
        Scan for nearby networks.
        Returns a list of unique SSIDs sorted by signal strength (strongest first).
        """
        nets = self.wlan.scan()
        seen = {}
        for net in nets:
            ssid = net[0].decode("utf-8") if isinstance(net[0], bytes) else str(net[0])
            rssi = net[3]
            if ssid and (ssid not in seen or rssi > seen[ssid]):
                seen[ssid] = rssi

        return sorted(seen.keys(), key=lambda s: seen[s], reverse=True)

    def _reset_radio(self):
        try:
            if self.wlan.isconnected():
                self.wlan.disconnect()
        except Exception:
            pass
        utime.sleep(0.25)

        try:
            self.wlan.active(False)
        except Exception:
            pass
        utime.sleep(0.25)

        try:
            self.wlan.active(True)
        except Exception:
            pass
        utime.sleep(0.5)

        try:
            self.wlan.config(pm=0xa11140)
        except Exception:
            pass

    def connect(self, ssid, password, timeout=15, display=None, reset_radio=True):
        """
        Connect to a WiFi network.
        Returns True when associated and an IP is assigned.
        NTP / internet checks are best-effort and do not fail the connect.
        """
        if timeout is None:
            timeout = 15
        try:
            timeout = int(timeout)
        except Exception:
            timeout = 15
        if timeout < 5:
            timeout = 5

        if display is not None:
            display.show_message(*["WiFi", "Connecting", "SSID", "{}".format(ssid), "Resetting", "WiFi"])

        if reset_radio or not self.wlan.isconnected():
            self._reset_radio()
        elif self.wlan.isconnected():
            ip = self.get_ip()
            print("Already connected, IP:", ip)
            self._sync_time()
            return True

        if display is not None:
            display.show_message(*["WiFi", "Connecting", "SSID", "{}".format(ssid), "Starting", "Connection"])

        try:
            nets = self.scan()
            print(nets)
        except Exception as e:
            print("WiFi scan failed:", e)

        print("Connecting to {} ...".format(ssid))
        try:
            self.wlan.connect(ssid, password)
        except Exception as e:
            print("wlan.connect error:", e)

        i = timeout
        while i > 0:
            if self.wlan.isconnected():
                break

            try:
                status = self.wlan.status()
                print(status)
            except Exception:
                status = None

            # -3 bad password is definitive. -2 AP missing can also be transient
            # right after a radio reset, so only abort it late. Never abort
            # early on -1 (generic fail) — that is common mid-join on Pico W.
            elapsed = timeout - i
            if status == -3:
                print("Early fail, status={}".format(status))
                break
            if status == -2 and elapsed >= 5:
                print("Early fail, status={}".format(status))
                break

            print("Waiting for connection... {} seconds remaining".format(i))

            if display is not None:
                display.show_message(*[
                    "WiFi", "Connecting",
                    "SSID", "{}".format(ssid),
                    "Time Remaining", "{}".format(i)
                ])

            time.sleep(1)
            i -= 1

        if not self.wlan.isconnected():
            try:
                status = self.wlan.status()
            except Exception:
                status = None

            if status == -3:
                reason = "Bad Password"
            elif status == -2:
                reason = "AP Not Found"
            elif status == -1:
                reason = "Connect Failed"
            else:
                reason = "Timeout"

            print("Failed to connect. status={} → {}".format(status, reason))

            if display is not None:
                display.show_message(*[
                    "WiFi",
                    "Failed Connection",
                    "SSID", "{}".format(ssid),
                    "Reason", reason
                ])
                utime.sleep(2)

            return False

        ip = self.get_ip()
        print("Connected, IP:", ip)

        ntp_ok = self._sync_time()

        if display is not None:
            display.show_message(*[
                "WiFi", "Connected",
                "SSID", "{}".format(ssid),
                "IP", "{}".format(ip or "none"),
            ])
            utime.sleep(2)
            display.clear()

        if not ntp_ok:
            print("NTP sync skipped/failed — WiFi still considered connected")

        return True

    def _sync_time(self):
        """Best-effort NTP. Never used as a connectivity gate."""
        try:
            import ntptime
            ntptime.host = "time.google.com"
            ntptime.settime()
            self._ntp_ok = True
            print("Time synced:", utime.gmtime())
            return True
        except Exception as e:
            self._ntp_ok = False
            print("NTP failed:", e)
            return False

    def check_connection(self):
        """
        True when STA is associated and IP traffic works.
        Uses a plain TCP connect so UDP/123 (NTP) or TLS cannot false-fail it.
        """
        if not self.is_connected():
            return False

        gc.collect()
        targets = (
            ("1.1.1.1", 80),
            ("8.8.8.8", 53),
            ("aviationweather.gov", 443),
        )
        import socket
        for host, port in targets:
            s = None
            try:
                addr = socket.getaddrinfo(host, port)[0][-1]
                s = socket.socket()
                s.settimeout(5)
                s.connect(addr)
                print("Internet check ok via {}:{}".format(host, port))
                return True
            except Exception as e:
                print("Internet check {} :{} failed: {}".format(host, port, e))
            finally:
                if s is not None:
                    try:
                        s.close()
                    except Exception:
                        pass
                gc.collect()
        return False

    def is_connected(self):
        try:
            return bool(self.wlan.isconnected())
        except Exception:
            return False

    def disconnect(self):
        try:
            self.wlan.disconnect()
        except Exception:
            pass
        print("Disconnected")

    def get_ip(self):
        if self.is_connected():
            try:
                return self.wlan.ifconfig()[0]
            except Exception:
                return None
        return None

    def status(self):
        """Human-readable status string."""
        if self.is_connected():
            return "Connected ({})".format(self.get_ip())
        return "Not connected"
