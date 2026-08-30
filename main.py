import gc,micropython,time
from utime import sleep
from utils.config import Config
from utils.button import Button
from utils.i2cdisplay import I2CDisplay
from utils.led import WeatherLights
from utils.airportwifi import AirportWiFi
from utils.metar import setDisplay, setDisplayPage
from utils.led import PINK, BLUE, RED
from utils.apportal import run_ap_portal
import updates
try:
    import machine
except ImportError:
    machine = None

gc.collect()
print("=== bare boot ===")
micropython.mem_info()

"""
This section initalizes all global variables.
"""
software_version = "2.0.0.5"
sync_handled = True
ap_requested = False
ap_exit_requested = False
in_ap_mode = False

#Load the config.json file
system_cfg = Config()

if(system_cfg.get("CONFIG_VERSION",0) is not 0):
    print("Loaded config.json successfully")
else:
    print("Failed to load config.json")

METAR_INTERVAL_S = system_cfg.get("METAR_INTERVAL_S", 60)   # every 60 s
DISPLAY_INTERVAL_S = system_cfg.get("DISPLAY_INTERVAL_S", 5)   # every 5 s
DISPLAY_MODE = system_cfg.get("DISPLAY_MODE", "Cycle")   # Cycle or Static
POLL_S           = 0.25   # how often the loop wakes up to check buttons / time .25


#Set up I2C Display
display = I2CDisplay(scl=system_cfg.get("DISPLAY_PIN_SCL"), sda=system_cfg.get("DISPLAY_PIN_SDA"))

display.show_message(*["Binary Aviation", "RunwaySense", "", "", "Display", "Initialized"])
sleep(1)

#Set up Buttons
def set_sync(_):
    global sync_handled
    # Function that is scheduled when AP button is pressed.
    sync_handled = False
    print("Sync button pressed!")

def on_sync_button():
    # Schedule the function to run in the main thread.
    micropython.schedule(set_sync, None)

def switch_to_ap_mode(_):
    global ap_requested, ap_exit_requested, in_ap_mode
    print("AP button pressed!")
    if in_ap_mode:
        ap_exit_requested = True
    else:
        ap_requested = True

def on_ap_button():
    # Schedule the function to run in the main thread.
    micropython.schedule(switch_to_ap_mode, None)

def _ap_should_exit():
    return ap_exit_requested

def enter_ap_mode():
    global ap_requested, ap_exit_requested, in_ap_mode, wifi, wifi_status
    global METAR_INTERVAL_S, DISPLAY_INTERVAL_S, DISPLAY_MODE, last_metar, last_display_update, display_index
    global metar_fail_count, last_wifi_attempt, wifi_backoff_s, wifi_fault

    ap_requested = False
    ap_exit_requested = False
    in_ap_mode = True

    print("Entering AP mode")

    display.show_message(*["Binary Aviation", "RunwaySense", "", "Starting", "AP Mode", ""])
    try:
        led_weather.fill(PINK)
    except Exception:
        pass

    result = "exit"
    try:
        result = run_ap_portal(
            system_cfg,
            display=display,
            leds=led_weather,
            version=software_version,
            should_exit=_ap_should_exit,
        )
    except Exception as e:
        print("AP portal error:", e)
        result = "exit"

    in_ap_mode = False
    ap_exit_requested = False

    if result in ("saved", "update"):
        if result == "update":
            display.show_message(*["Update Mode", "Rebooting", "Keep Power", "Connected", "", ""])
        else:
            display.show_message(*["Binary Aviation", "RunwaySense", "Settings", "Saved", "Rebooting", ""])
        sleep(2)
        if machine is not None:
            try:
                machine.reset()
            except Exception:
                pass

    # Left AP without reboot — reload settings and go back to STA.
    system_cfg.load()
    METAR_INTERVAL_S = system_cfg.get("METAR_INTERVAL_S", 60)
    DISPLAY_INTERVAL_S = system_cfg.get("DISPLAY_INTERVAL_S", 10)
    DISPLAY_MODE = system_cfg.get("DISPLAY_MODE", "Cycle")
    try:
        led_weather.set_brightness(system_cfg.get("WEATHER_LED_BRIGHTNESS", 5))
    except Exception:
        pass

    wifi_status = False
    last_metar = 0
    last_display_update = 0
    display_index = 0
    metar_fail_count = 0
    last_wifi_attempt = 0
    wifi_backoff_s = 5
    wifi_fault = None
    display.show_message(*["Binary Aviation", "RunwaySense", "Leaving", "AP Mode", "Reconnecting", "WiFi"])
    sleep(1)

btn_sync = Button(system_cfg.get("BUTTON_PIN_SYNC"), callback=on_sync_button, debounce_ms=2000)
btn_sync.enable()

btn_ap = Button(system_cfg.get("BUTTON_PIN_AP"), callback=on_ap_button, debounce_ms=2000)
btn_ap.enable()

display.show_message(*["Binary Aviation", "RunwaySense", "", "", "Buttons", "Initialized"])
sleep(1)

#Set up LEDs
display.show_message(*["Binary Aviation", "RunwaySense", "", "", "LEDs", "Initalizing"])

led_weather = WeatherLights(pin=system_cfg.get("WEATHER_LED_PIN"),brightness=system_cfg.get("WEATHER_LED_BRIGHTNESS"),headings=system_cfg.get("WEATHER_LED_HEADINGS"))
led_weather.startup(clear=False)


display.show_message(*["Binary Aviation", "RunwaySense", "", "", "LEDs", "Initialized"])
sleep(1)
display.clear()
sleep(1)

# ----- GitHub update mode (set from AP "Update Software") -----
if system_cfg.get("UPDATE_MODE"):
    print("Update Mode Enabled")
    display.show_message(*["Update Mode", "Starting", "Please Do Not", "Turn Off", "Power", ""])
    try:
        led_weather.fill((255, 255, 255))
    except Exception:
        pass
    sleep(2)

    update_wifi = AirportWiFi()

    def _update_connect():
        ok = update_wifi.connect(
            system_cfg.get("WIFI_SSID"),
            system_cfg.get("WIFI_PASSWORD"),
            timeout=system_cfg.get("WIFI_TIMEOUT"),
            display=display,
        )
        return bool(ok)

    def _update_progress(i, total, path):
        name = path.split("/")[-1] if path else ""
        display.show_message(*[
            "Update Mode",
            "{}/{}".format(i, total),
            name,
            "Please Do Not",
            "Turn Off",
            "Power",
        ])

    ok, info = updates.run_update(
        cfg=system_cfg,
        connect_fn=_update_connect,
        progress_fn=_update_progress,
    )
    try:
        system_cfg.set("UPDATE_MODE", False)
    except Exception:
        pass

    if ok:
        display.show_message(*["Update Mode", "Success", "Unit", "Restarting", "", ""])
        sleep(3)
        if machine is not None:
            try:
                machine.reset()
            except Exception:
                pass
    else:
        print("Update failed:", info)
        reason = ""
        try:
            reason = str(info.get("reason") if isinstance(info, dict) else info)
        except Exception:
            reason = "failed"
        if isinstance(info, dict) and info.get("failed"):
            try:
                reason = str(info["failed"][0].get("error") or reason)
            except Exception:
                pass
        display.show_message(*["Update Mode", "Failed", "Turn Unit", "Off / On", "Error", reason[:16]])
        while True:
            sleep(5)

#SW Version
display.show_message(*["Binary Aviation", "RunwaySense", "", "", "Initalization", "Complete"])
sleep(3)
display.clear()
sleep(1)

#SW Version
display.show_message(*["Binary Aviation", "RunwaySense", "", "", "Software Version", f"{software_version}"])
sleep(3)
display.clear()
sleep(1)

if ap_requested:
    enter_ap_mode()


#Set up WiFi
wifi = AirportWiFi()

last_metar = 0
last_display_update = 0
display_index = 0
metar= None
wifi_status = False
metar_fail_count = 0
last_wifi_attempt = 0
wifi_backoff_s = 5
wifi_fault = None
METAR_FAILS_BEFORE_RECONNECT = 3
WIFI_BACKOFF_MAX_S = 60

gc.collect()
print("=== After Setup Entering Main Loop ===")
micropython.mem_info()

def show_wifi_fault(kind, line3, line4, line5, line6):
    global wifi_fault
    if wifi_fault == kind:
        return
    wifi_fault = kind
    try:
        display.show_message(*["Binary Aviation", "RunwaySense", line3, line4, line5, line6])
    except Exception:
        pass
    try:
        led_weather.fill(BLUE)
    except Exception:
        pass


def attempt_wifi(force=False):
    global wifi_status, last_wifi_attempt, wifi_backoff_s, wifi_fault
    last_wifi_attempt = time.ticks_ms()
    ok = wifi.connect(
        system_cfg.get("WIFI_SSID"),
        system_cfg.get("WIFI_PASSWORD"),
        timeout=system_cfg.get("WIFI_TIMEOUT"),
        display=display,
        reset_radio=force or (not wifi.is_connected()),
    )
    if wifi.is_connected():
        wifi_backoff_s = 5
        wifi_status = True
        wifi_fault = None
        return True
    wifi_status = False
    wifi_backoff_s = min(int(wifi_backoff_s * 2), WIFI_BACKOFF_MAX_S)
    print("WiFi retry backoff now {}s".format(wifi_backoff_s))
    return False


try:
    
    while True:
        now = time.ticks_ms()

        # ----- WiFi keep-alive -----
        if wifi.is_connected() is False:
            wifi_status = False
            due = (last_wifi_attempt == 0 or
                   time.ticks_diff(now, last_wifi_attempt) >= wifi_backoff_s * 1000)
            if due:
                attempt_wifi(force=True)
            if wifi.is_connected() is False:
                show_wifi_fault(
                    "ap",
                    "{}".format(system_cfg.get("WIFI_SSID")),
                    "Not on WiFi",
                    "Retry {}s".format(wifi_backoff_s),
                    "Check Router",
                )

        # ----- METAR (own interval) -----
        # Fetch whenever associated. Do not require NTP / wifi_status first.
        if wifi.is_connected() and (time.ticks_diff(now, last_metar) >= METAR_INTERVAL_S * 1000 or last_metar == 0):
            print("Refreshing METAR data...")
            gc.collect()
            fresh = wifi.get_metar(icao=system_cfg.get("METAR_STATION_ID"))
            #fresh = "KJFK 252155Z 28018G30KT 1 1/2SM +TSRA BR BKN012CB OVC025 18/16 A2975 RMK AO2 TSB45"
            print(fresh)
            if fresh is not None:
                metar = fresh
                last_metar = now
                metar_fail_count = 0
                wifi_status = True
                wifi_backoff_s = 5
                wifi_fault = None
                display.show_message(*["Binary Aviation", "RunwaySense", "", "Fetching", "New METAR", "Data"])
                if DISPLAY_MODE == "Static":
                    setDisplay(display, metar, led_weather, crosswind_limit=system_cfg.get("WEATHER_LED_CROSSWIND_LIMIT", 5))
                if DISPLAY_MODE == "Cycle":
                    last_display_update = now
                    display_index = 0
            else:
                metar_fail_count += 1
                print("METAR fetch failed ({}/{})".format(metar_fail_count, METAR_FAILS_BEFORE_RECONNECT))
                # Keep last good METAR on the display. Only go blue if we have none.
                if metar is None:
                    show_wifi_fault(
                        "metar",
                        "{}".format(system_cfg.get("METAR_STATION_ID")),
                        "METAR Failed",
                        "Attempt {}".format(metar_fail_count),
                        "Retrying",
                    )
                    retry_s = 30 if METAR_INTERVAL_S > 30 else METAR_INTERVAL_S
                    last_metar = now - (METAR_INTERVAL_S - retry_s) * 1000
                else:
                    last_metar = now
                if metar_fail_count >= METAR_FAILS_BEFORE_RECONNECT:
                    print("METAR failed repeatedly — forcing WiFi reconnect")
                    metar_fail_count = 0
                    wifi_status = False
                    try:
                        wifi.disconnect()
                    except Exception:
                        pass
                    sleep(1)
                    attempt_wifi(force=True)

        if (time.ticks_diff(now, last_display_update) >= DISPLAY_INTERVAL_S * 1000 and metar != None and DISPLAY_MODE == "Cycle"):
            print("Changing display data current index: " + str(display_index))
            display_index = setDisplayPage(display, metar, led_weather, system_cfg.get("WEATHER_LED_CROSSWIND_LIMIT", 5),system_cfg.get("METAR_STATION_ID"),display_index)
            last_display_update = now

        # ----- Button / sync handling -----
        if sync_handled is False:
            print("Skipping due to sync press")
            sync_handled = True
            last_metar = 0
            last_display_update = 0
            display_index = 0
            metar_fail_count = 0
            wifi_fault = None

        if ap_requested:
            enter_ap_mode()

        time.sleep(POLL_S)

except Exception as e:
    print("Error in main loop:", e)
    try:
        led_weather.fill(RED)
    except Exception:
        pass
    display.show_message(*["Binary Aviation", "RunwaySense", "Error", "Occurred", "Restart", "Unit"])
