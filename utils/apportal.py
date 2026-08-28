# utils/apportal.py
"""
Access-point config portal for RunwaySense.

Connect to WIFI_SSID_AP / WIFI_PASSWORD_AP and open http://192.168.4.1
"""

import gc
import socket
import time

import network
import utime

try:
    import machine
except ImportError:
    machine = None

from utils.led import PINK


HTML_HEADER = """\
HTTP/1.1 200 OK
Content-Type: text/html; charset=utf-8
Cache-Control: no-store
Connection: close

"""

HTML_REDIRECT = """\
HTTP/1.1 302 Found
Location: /
Cache-Control: no-store
Connection: close

"""

HTML_PAGE = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>RunwaySense Settings</title>
  <style>
    :root { --ink:#0f172a; --muted:#5b677a; --line:#d7dee8; --card:#fff; --bg:#eef2f6; --blue:#1f6feb; --green:#2da44e; --gray:#6e7781; }
    * { box-sizing: border-box; }
    body { margin:0; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; background:var(--bg); color:var(--ink); }
    .wrap { max-width:520px; margin:0 auto; padding:20px 14px 32px; }
    .brand { text-align:center; margin-bottom:14px; }
    .brand h1 { margin:0; font-size:1.25rem; letter-spacing:.02em; }
    .brand p { margin:4px 0 0; color:var(--muted); font-size:.9rem; }
    .card { background:var(--card); border-radius:12px; padding:16px 16px 18px; box-shadow:0 1px 4px rgba(15,23,42,.08); margin-bottom:14px; }
    h2 { margin:0 0 12px; font-size:1.02rem; }
    label { display:block; margin:12px 0 0; font-weight:650; font-size:.92rem; }
    .hint { margin:6px 0 0; color:var(--muted); font-size:.82rem; font-weight:400; }
    input[type=text], input[type=password], input[type=number], select {
      width:100%; margin-top:6px; padding:10px 12px; border:1px solid var(--line); border-radius:8px; font:inherit; background:#fff;
    }
    input[type=number]::-webkit-outer-spin-button,
    input[type=number]::-webkit-inner-spin-button { -webkit-appearance:none; margin:0; }
    .row { display:grid; grid-template-columns:1fr 1fr; gap:10px; }
    .btns { display:flex; gap:10px; margin-top:16px; flex-wrap:wrap; }
    button, input[type=submit] {
      flex:1; min-width:120px; padding:11px 12px; border:0; border-radius:8px; background:var(--blue); color:#fff; font-weight:700; font:inherit; cursor:pointer;
    }
    input[type=submit][value="Update Software"] { background:var(--green); }
    input[type=submit][value="Scan"] { background:var(--gray); min-width:90px; flex:0 0 110px; }
    input[type=submit][value="Exit AP"] { background:var(--gray); }
    .ssidrow { display:grid; grid-template-columns:1fr 110px; gap:10px; align-items:end; }
    .mono { font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; }
    .ok { color:#1a7f37; text-align:center; }
    .banner { background:#e8f1ff; color:#163a73; border-radius:8px; padding:8px 10px; font-size:.88rem; margin:0 0 12px; text-align:center; }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="brand">
      <h1>Binary Aviation</h1>
      <p>RunwaySense &middot; <span class="mono">__VERSION__</span></p>
    </div>
    <div class="card">
      __BANNER__
      <h2>Board Settings</h2>
      <form method="POST" action="/">
        <div class="row">
          <label>LED Brightness (%)
            <input type="number" name="led_brightness" min="0" max="100" step="1" value="__LED_BRIGHTNESS__">
          </label>
          <label>Crosswind Threshold (kt)
            <input type="number" name="crosswind_threshold" min="0" max="50" step="1" value="__CROSSWIND_THRESHOLD__">
          </label>
        </div>
        <label>Display Mode
          <select name="display_mode">
            <option value="Cycle" __DISPLAY_MODE_CYCLE__>Cycle</option>
            <option value="Static" __DISPLAY_MODE_STATIC__>Static</option>
          </select>
        </label>
        <p class="hint">Cycle rotates METAR pages. Static keeps the summary screen.</p>

        <h2 style="margin-top:22px">Wi-Fi</h2>
        <div class="ssidrow">
          <label>Network SSID
            <input id="ssid_input" type="text" name="ssid" value="__SSID__" autocomplete="off" placeholder="Type or pick from scan">
          </label>
          <label>&nbsp;
            <input type="submit" name="action" value="Scan">
          </label>
        </div>
        __SCAN_RESULTS_BLOCK__
        <p class="hint">Scan, then pick a network to fill the SSID box. You can still type one manually.</p>
        <label>Password
          <input type="password" name="password" value="__PASSWORD__" placeholder="Leave unchanged to keep current">
        </label>
        <p class="hint">Leave password blank to keep the stored password.</p>
        <div class="row">
          <label>Wi-Fi Timeout (s)
            <input type="number" name="wifi_timeout" min="5" max="120" step="1" value="__WIFI_TIMEOUT__">
          </label>
          <label>METAR Interval (s)
            <input type="number" name="metar_interval" min="60" max="3600" step="1" value="__METAR_INTERVAL__">
          </label>
        </div>
        <p class="hint">METAR updates cannot be faster than every 60 seconds.</p>

        <div class="btns">
          <input type="submit" name="action" value="Save">
          <input type="submit" name="action" value="Update Software">
          <input type="submit" name="action" value="Exit AP">
        </div>
      </form>
    </div>
  </div>
</body>
</html>
"""

HTML_SAVED = """\
<!DOCTYPE html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Saved</title>
<style>
  body { font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; background:#eef2f6; margin:0; }
  .wrap { max-width:460px; margin:40px auto; padding:0 14px; }
  .card { background:#fff; border-radius:12px; padding:22px; text-align:center; box-shadow:0 1px 4px rgba(15,23,42,.08); }
</style></head>
<body><div class="wrap"><div class="card">
  <h2>Settings saved</h2>
  <p>The board will reboot and leave AP mode.</p>
  <p>You can disconnect from this Wi-Fi network.</p>
</div></div></body></html>
"""

HTML_UPDATE = """\
<!DOCTYPE html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Update</title>
<style>
  body { font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; background:#eef2f6; margin:0; }
  .wrap { max-width:460px; margin:40px auto; padding:0 14px; }
  .card { background:#fff; border-radius:12px; padding:22px; box-shadow:0 1px 4px rgba(15,23,42,.08); }
  a { display:block; margin-top:16px; text-align:center; background:#6e7781; color:#fff; text-decoration:none; padding:11px; border-radius:8px; font-weight:700; }
</style></head>
<body><div class="wrap"><div class="card">
  <h2>Update Software</h2>
  <p>OTA software update is not enabled in this build. This button is reserved for a later release.</p>
  <a href="/">Back to settings</a>
</div></div></body></html>
"""


def _html_escape(s):
    if s is None:
        return ""
    s = str(s)
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


def _url_decode(s):
    if not s:
        return ""
    out = bytearray()
    i = 0
    while i < len(s):
        ch = s[i]
        if ch == "+":
            out.append(32)
            i += 1
            continue
        if ch == "%" and i + 2 < len(s):
            try:
                out.append(int(s[i + 1:i + 3], 16))
                i += 3
                continue
            except Exception:
                pass
        o = ord(ch)
        if o < 128:
            out.append(o)
        else:
            try:
                out.extend(ch.encode("utf-8"))
            except Exception:
                pass
        i += 1
    try:
        return bytes(out).decode("utf-8")
    except Exception:
        return bytes(out).decode("latin-1")


def _parse_body(body):
    params = {}
    if not body:
        return params
    for part in body.split("&"):
        if "=" in part:
            k, v = part.split("=", 1)
        else:
            k, v = part, ""
        params[_url_decode(k)] = _url_decode(v)
    return params


def _parse_int(value, lo, hi, fallback):
    try:
        n = int(float(str(value).strip()))
    except Exception:
        return fallback
    if n < lo:
        n = lo
    if n > hi:
        n = hi
    return n


def _read_request(cl, max_bytes=4096):
    try:
        cl.settimeout(3)
    except Exception:
        pass
    data = b""
    try:
        while len(data) < max_bytes:
            chunk = cl.recv(512)
            if not chunk:
                break
            data += chunk
            if b"\r\n\r\n" in data:
                header, body = data.split(b"\r\n\r\n", 1)
                clen = 0
                for line in header.decode("latin-1").split("\r\n"):
                    if line.lower().startswith("content-length:"):
                        try:
                            clen = int(line.split(":", 1)[1].strip())
                        except Exception:
                            clen = 0
                        break
                if clen and len(body) < clen:
                    continue
                break
    except Exception:
        return None
    return data if data else None


def _send(cl, payload):
    if isinstance(payload, str):
        payload = payload.encode("utf-8")
    try:
        cl.send(payload)
    except Exception:
        try:
            cl.write(payload)
        except Exception:
            pass


def _decode_ssid(raw):
    if raw is None:
        return ""
    if isinstance(raw, bytes):
        try:
            return raw.decode("utf-8")
        except Exception:
            try:
                return raw.decode("latin-1")
            except Exception:
                return ""
    return str(raw)


def _scan_ssids(limit=25):
    """Scan with STA while AP stays up. Strongest first."""
    sta = None
    seen = {}
    try:
        sta = network.WLAN(network.STA_IF)
        try:
            sta.active(True)
        except Exception:
            pass
        try:
            sta.config(pm=0xa11140)
        except Exception:
            pass
        time.sleep_ms(250)

        for _ in range(3):
            gc.collect()
            try:
                nets = sta.scan()
            except Exception as e:
                print("SSID scan pass failed:", e)
                nets = []
            for net in nets:
                try:
                    ssid = _decode_ssid(net[0]).strip()
                    rssi = net[3]
                    if not ssid:
                        continue
                    if ssid not in seen or rssi > seen[ssid]:
                        seen[ssid] = rssi
                except Exception:
                    pass
            time.sleep_ms(200)
    except Exception as e:
        print("SSID scan failed:", e)
    # Leave STA active; turning it off mid-AP can drop the radio on some Pico W builds.

    ssids = list(seen.keys())
    ssids.sort(key=lambda s: seen.get(s, -999), reverse=True)
    return ssids[:limit]


def _scan_results_html(ssids):
    if not ssids:
        return '<p class="hint">No networks found. Try Scan again.</p>'
    options = ['<option value="">Select a scanned network...</option>']
    for s in ssids:
        esc = _html_escape(s)
        options.append('<option value="{}">{}</option>'.format(esc, esc))
    return (
        '<label>Scan Results'
        '<select onchange="document.getElementById(\'ssid_input\').value=this.value">'
        + "".join(options)
        + "</select></label>"
    )


def _render_settings(cfg, version, banner="", form=None, ssids=None):
    form = form or {}
    dm = str(form.get("display_mode") or cfg.get("DISPLAY_MODE", "Cycle"))
    ssid = form.get("ssid")
    if ssid is None or ssid == "":
        ssid = cfg.get("WIFI_SSID", "")

    def field(name, fallback):
        if name in form and str(form.get(name)).strip() != "":
            return str(form.get(name))
        return str(fallback)

    banner_html = '<div class="banner">{}</div>'.format(_html_escape(banner)) if banner else ""
    scan_block = _scan_results_html(ssids) if ssids is not None else ""

    html = HTML_PAGE
    html = html.replace("__VERSION__", _html_escape(version))
    html = html.replace("__BANNER__", banner_html)
    html = html.replace("__LED_BRIGHTNESS__", field("led_brightness", cfg.get("WEATHER_LED_BRIGHTNESS", 5)))
    html = html.replace("__CROSSWIND_THRESHOLD__", field("crosswind_threshold", cfg.get("WEATHER_LED_CROSSWIND_LIMIT", 5)))
    html = html.replace("__DISPLAY_MODE_CYCLE__", "selected" if dm != "Static" else "")
    html = html.replace("__DISPLAY_MODE_STATIC__", "selected" if dm == "Static" else "")
    html = html.replace("__SSID__", _html_escape(ssid))
    html = html.replace("__PASSWORD__", "")
    html = html.replace("__WIFI_TIMEOUT__", field("wifi_timeout", cfg.get("WIFI_TIMEOUT", 30)))
    html = html.replace("__METAR_INTERVAL__", field("metar_interval", cfg.get("METAR_INTERVAL_S", 300)))
    html = html.replace("__SCAN_RESULTS_BLOCK__", scan_block)
    return HTML_HEADER + html


def _show_ap_display(display, ssid, password, ip):
    if display is None:
        return
    try:
        display.show_message(*[
            "AP Mode",
            "SSID",
            str(ssid),
            "Password",
            str(password),
            str(ip or "192.168.4.1"),
        ])

        display.add_separator(after_row=2)
        display.add_separator(after_row=4)
    except Exception:
        pass


def run_ap_portal(cfg, display=None, leds=None, version="2.0.0.1", should_exit=None):
    """
    Start AP + HTTP server. Blocks until Save (reboot), Exit AP, or should_exit().

    Returns:
        "saved"   settings written, caller should reset
        "exit"    leave AP without reboot
    """
    ap_ssid = cfg.get("WIFI_SSID_AP") or "RunwaySense-Setup"
    ap_pass = cfg.get("WIFI_PASSWORD_AP") or "metar123"

    if leds is not None:
        try:
            leds.fill(PINK)
        except Exception:
            pass

    # Drop station mode so the radio can host the AP cleanly.
    try:
        sta = network.WLAN(network.STA_IF)
        try:
            sta.disconnect()
        except Exception:
            pass
        sta.active(False)
    except Exception:
        pass
    time.sleep_ms(200)

    ap = network.WLAN(network.AP_IF)
    try:
        ap.active(False)
    except Exception:
        pass
    time.sleep_ms(200)

    try:
        ap.config(essid=ap_ssid, password=ap_pass)
    except Exception:
        try:
            ap.config(essid=ap_ssid)
        except Exception:
            pass

    ap.active(True)
    for _ in range(50):
        if ap.active():
            break
        time.sleep_ms(100)

    ip = "192.168.4.1"
    try:
        ip = ap.ifconfig()[0] or ip
    except Exception:
        pass

    print("AP started", ap_ssid, ip)
    _show_ap_display(display, ap_ssid, ap_pass, ip)

    addr = socket.getaddrinfo("0.0.0.0", 80)[0][-1]
    server = socket.socket()
    try:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    except Exception:
        pass
    server.bind(addr)
    server.listen(2)
    try:
        server.settimeout(1)
    except Exception:
        pass

    result = "exit"
    try:
        while True:
            if should_exit is not None:
                try:
                    if should_exit():
                        result = "exit"
                        break
                except Exception:
                    pass

            try:
                cl, remote = server.accept()
            except OSError:
                continue
            except Exception:
                continue

            try:
                raw = _read_request(cl)
                if not raw:
                    cl.close()
                    continue

                header, body = (raw.split(b"\r\n\r\n", 1) + [b""])[:2]
                first = header.decode("latin-1").split("\r\n", 1)[0]
                parts = first.split(" ")
                method = parts[0] if parts else "GET"
                path = parts[1] if len(parts) > 1 else "/"
                if "?" in path:
                    path = path.split("?", 1)[0]

                # Captive-portal probes
                if path not in ("/", "/index.html", "/save"):
                    _send(cl, HTML_REDIRECT)
                    cl.close()
                    continue

                if method == "POST":
                    params = _parse_body(body.decode("latin-1"))
                    action = params.get("action", "Save")

                    if action == "Exit AP":
                        _send(cl, HTML_HEADER + HTML_SAVED.replace("Settings saved", "Leaving AP mode").replace("The board will reboot and leave AP mode.", "Returning to station Wi-Fi."))
                        result = "exit"
                        cl.close()
                        break

                    if action in ("Update", "Update Software"):
                        _send(cl, HTML_HEADER + HTML_UPDATE)
                        cl.close()
                        continue

                    if action == "Scan":
                        if display is not None:
                            try:
                                display.show_message(*["AP Mode", "Scanning", "Wi-Fi", "Networks", "Please", "Wait"])
                            except Exception:
                                pass
                        ssids = _scan_ssids()
                        banner = "{} network{} found".format(len(ssids), "" if len(ssids) == 1 else "s")
                        _send(cl, _render_settings(cfg, version, banner=banner, form=params, ssids=ssids))
                        _show_ap_display(display, ap_ssid, ap_pass, ip)
                        cl.close()
                        continue

                    # Save
                    updates = {
                        "WEATHER_LED_BRIGHTNESS": _parse_int(
                            params.get("led_brightness"), 0, 100, cfg.get("WEATHER_LED_BRIGHTNESS", 5)
                        ),
                        "WEATHER_LED_CROSSWIND_LIMIT": _parse_int(
                            params.get("crosswind_threshold"), 0, 50, cfg.get("WEATHER_LED_CROSSWIND_LIMIT", 5)
                        ),
                        "DISPLAY_MODE": "Static" if params.get("display_mode") == "Static" else "Cycle",
                        "WIFI_TIMEOUT": _parse_int(
                            params.get("wifi_timeout"), 5, 120, cfg.get("WIFI_TIMEOUT", 30)
                        ),
                        "METAR_INTERVAL_S": _parse_int(
                            params.get("metar_interval"), 60, 3600, cfg.get("METAR_INTERVAL_S", 300)
                        ),
                    }
                    ssid = (params.get("ssid") or "").strip()
                    if ssid:
                        updates["WIFI_SSID"] = ssid
                    password = params.get("password")
                    if password is not None and password != "":
                        updates["WIFI_PASSWORD"] = password

                    cfg.update(updates)
                    if leds is not None:
                        try:
                            leds.set_brightness(updates["WEATHER_LED_BRIGHTNESS"])
                            leds.fill(PINK)
                        except Exception:
                            pass

                    _send(cl, HTML_HEADER + HTML_SAVED)
                    cl.close()
                    result = "saved"
                    time.sleep(1)
                    break

                _send(cl, _render_settings(cfg, version))
            except Exception as e:
                print("AP request error:", e)
            finally:
                try:
                    cl.close()
                except Exception:
                    pass
            gc.collect()
    finally:
        try:
            server.close()
        except Exception:
            pass
        try:
            ap.active(False)
        except Exception:
            pass
        time.sleep_ms(200)

    return result
