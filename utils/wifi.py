import network
import time
import gc
import ntptime
import utime 

try:
    import urequests as requests
except ImportError:
    import requests

class WiFi:

    def __init__(self):
        self.wlan = network.WLAN(network.STA_IF)

        try:
            self.wlan.active(False)
        except Exception:
            pass
        utime.sleep(.25)

        try:
            self.wlan.active(True)
        except Exception:
            pass
        utime.sleep(.25)

        #Disable Power Saving
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

        # Sort strongest → weakest
        return sorted(seen.keys(), key=lambda s: seen[s], reverse=True)

    def connect(self, ssid, password, timeout=15, display=None):
        """
        Connect to a WiFi network.
        Returns True on success, False on failure.
        """

        if(display is not None):
            display.show_message(*["WiFi", "Connecting", "SSID", f"{ssid}", "Resetting", "WiFi"])

        if self.wlan.isconnected():
            self.wlan.disconnect()
            time.sleep_ms(500)

        try:
            self.wlan.active(False)
        except Exception:
            pass
        utime.sleep(.25)

        try:
            self.wlan.active(True)
        except Exception:
            pass
        utime.sleep(1)

        print(self.scan())

        if(display is not None):
            display.show_message(*["WiFi", "Connecting", "SSID", f"{ssid}", "Starting", "Connection"])

        utime.sleep(1)

        print(f"Connecting to {ssid} ...")
        self.wlan.connect(ssid, password)

        i = timeout
        while i > 0:
            if self.wlan.isconnected():
                break

            # Check for definitive failures and stop early
            try:
                status = self.wlan.status()
                print(status)
            except Exception:
                status = None

            if status in (-3, -2, -1):          # wrong password / no AP / connect fail
                print(f"Early fail, status={status}")
                break

            print(f"Waiting for connection... {i} seconds remaining")

            if display is not None:
                display.show_message(*[
                    "WiFi", "Connecting",
                    "SSID", f"{ssid}",
                    "Time Remaining", f"{i}"
                ])

            time.sleep(1)
            i -= 1

        if not self.wlan.isconnected():
            # Get the last status from the driver
            try:
                status = self.wlan.status()
            except Exception:
                status = None

            # Map to a human-readable reason
            if status == -3:
                reason = "Bad Password"
            elif status == -2:
                reason = "AP Not Found"
            elif status == -1:
                reason = "Connect Failed"
            else:
                reason = "Timeout"

            print(f"Failed to connect. status={status} → {reason}")

            if display is not None:
                display.show_message(*[
                    "WiFi",
                    "Failed Connection",
                    "SSID", f"{ssid}",
                    "Reason", reason
                ])

            utime.sleep(10)

            return False

        print("Connected, IP:", self.wlan.ifconfig()[0])

        # ----- Robust NTP sync -----
        try:
            import ntptime
            # Use a more reliable server
            ntptime.host = "time.google.com"          # or "time.google.com"
            ntptime.settime()
            print("Time synced:", utime.gmtime())

            if(display is not None):
                display.show_message(*["WiFi", "Connected", "SSID", f"{ssid}", "Internet Check", "Pass"])

            utime.sleep(10)

            if(display is not None):
                display.clear()

            return True

        except Exception as e:
            print("NTP failed:", e)

            if(display is not None):
                display.show_message(*["WiFi", "Connected", "SSID", f"{ssid}", "Internet Check", "Failed"])

            utime.sleep(10)
            
            if(display is not None):
                display.clear()

            return False

    def check_connection(self):
        
        try:
            import ntptime
            # Use a more reliable server
            ntptime.host = "time.google.com"          # or "time.google.com"
            ntptime.settime()
            print("Time synced:", utime.gmtime())

            return True

        except Exception as e:
            print("NTP failed:", e)
            
            return False

    def is_connected(self):
        return self.wlan.isconnected()

    def disconnect(self):
        self.wlan.disconnect()
        print("Disconnected")

    def get_ip(self):
        if self.is_connected():
            return self.wlan.ifconfig()[0]
        return None

    def status(self):
        """Human-readable status string."""
        if self.is_connected():
            return f"Connected ({self.get_ip()})"
        return "Not connected"