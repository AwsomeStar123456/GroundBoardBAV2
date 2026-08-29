# utils/metar.py
from utils.i2cdisplay import I2CDisplay
from framebuf import FrameBuffer, MONO_VLSB, MONO_HMSB, MONO_HLSB
import math
import utime
"""
METAR / SPECI parsing – works with raw text and JSON.
"""

#Wind Bytes
ByteArrow = bytearray(b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x18\x00\x00<\x00\x00~\x00\x00\xdb\x00\x80\x99\x01\xc0\x18\x03\x00\x18\x00\x00\x18\x00\x00\x18\x00\x00\x18\x00\x00\x18\x00\x00\x18\x00\x00\x18\x00\x00\x18\x00\x00\x18\x00\x00\x08\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')
ByteCalm = bytearray(b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x3c\x00\x00\xff\x00\x03\x81\xc0\x03\x00\xc0\x06\x00\x60\x04\x00\x20\x0c\x18\x30\x0c\x3c\x30\x0c\x3c\x30\x0c\x18\x30\x04\x00\x20\x06\x00\x60\x03\x00\xc0\x03\x81\xc0\x00\xff\x00\x00\x3c\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')

#Weather Bytes
ByteThunderSnow = bytearray(b'\x00\x00\x00\x00\x00\x00\x00\xf8\x00\x01\x84\x00\x03\x02\x00\x02\x01\xe0\x02\x01\x10\x0e\x00\x08\x18\x00\x04 \x00\x04 \x00\x04 \x00\x04 \x0c\x08\x10\x1c\x18\x0f9\xe0\x000\x00\x00x@\x00\x10\xe0\x10 @8D\x00\x10\x0e\x08\x01\x04\x1c\x03\x80\x08\x01\x00\x00')
ByteThunderHail = bytearray(b'\x00\x00\x00\x00\x00\x00\x00\xf8\x00\x01\x84\x00\x03\x02\x00\x02\x01\xe0\x02\x01\x10\x0e\x00\x08\x18\x00\x04 \x00\x04 \x00\x04 \x00\x04 \x0c\x08\x10\x1c\x18\x0f9\xe0\x000\x00\x00x\x18\x0c\x10(\x14 P(F`3\x0a\x00\x05\x14\x00\x0a\x18\x00\x0c\x00\x00')
ByteThunderStorm = bytearray(b'\x00\x00\x00\x00\x00\x00\x00\x1f\x00\x80!\x00\xc0@\x00@\x80\x07@\x80\x08p\x00\x10\x18\x00 \x04\x00 \x04\x00 \x04\x00 \x040\x10\x088\x18\xf0\x9c\x07\x00\x0c\x00 \x1e\x000\x08\x03\x18\x84\x01\x00\x82\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')
ByteFreezeRain = bytearray(b'\x00\x00\x00\x00\x00\x00\x000\x00\x00\xcc\x00\x01\x02\x00\x02\x02\x00\x02\x01\xf0\x02\x00\x08\x1e\x00\x0c0\x10\x04 \x10\x04 \xd6\x04 8\x040\xfe\x08\x1c\xd6p\x00\x10\x00\x00\x10\x00\x00\x00\x00\x00\x00\x00\x04\x10 \x0c0`\x18`\xc00\xc1\x80\x00\x00\x00')
ByteFreezeDrizzle = bytearray(b'\x00\x00\x00\x00\x00\x00\x000\x00\x00\xcc\x00\x01\x02\x00\x02\x02\x00\x02\x01\xf0\x02\x00\x08\x1e\x00\x0c0\x10\x04 \x10\x04 \xd6\x04 8\x040\xfe\x08\x1c\xd6p\x00\x10\x00\x00\x10\x00\x00\x00\x00\x00\x00\x00\x04\x00 \x0c\x00`\x08`\xc0\x00\xc0\x00\x00\x00\x00')
ByteFreezeFog = bytearray(b'\x00\x00\x00\x00\x00\x00\x000\x00\x00\xcc\x00\x01\x02\x00\x02\x02\x00\x02\x01\xf0\x02\x00\x08\x1e\x00\x0c0\x10\x04 \x10\x04 \xd6\x04 8\x040\xfe\x08\x1c\xd6p\x00\x10\x00\x00\x00\x00\x0f\xff\xf0\x00\x00\x00\x00\x00\x00\x7f\xff\x80\x00\x00\x00\x00\x00\x00\x0f\xff\xf0')
ByteRain = bytearray(b'\x00\x00\x00\x00\x00\x00\x00\x0c\x00\x003\x00\x80@\x00@@\x00@\x80\x0f@\x00\x10x\x000\x0c\x00 \x04\x00 \x04\x00 \x04\x00 \x0c\x00\x10\xf8\xff\x0f\x00\x00\x00\x00\x00\x00@\x88\x01\x00\x80\x00\x10"\x00\x08 \x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')
ByteSnow = bytearray(b'\x00\x00\x00\x00\x00\x00\x000\x00\x00\xcc\x00\x01\x02\x00\x02\x02\x00\x02\x01\xf0\x02\x00\x08\x1e\x00\x0c0\x10\x04 \x10\x04 \xd6\x04 8\x040\xfe\x08\x1c\xd6p\x00\x10\x00\x00\x00\x00\x00\x80@\x11\xc0\xe08\x84@\x10\x0e\x04\x00\x04\x0e\x00\x00\x04\x00\x00\x00')
ByteSnowHail = bytearray(b'\x00\x00\x00\x00\x00\x00\x000\x00\x00\xcc\x00\x01\x02\x00\x02\x02\x00\x02\x01\xf0\x02\x00\x08\x1e\x00\x0c0\x10\x04 \x10\x04 \xd6\x04 8\x040\xfe\x08\x1c\xd6p\x00\x10\x00\x00\x00\x00\x00\x000\x06\x00P\x0a\x00\xa0\x14\x18\xc0\x18(\x00\x00P\x00\x00`\x00')
ByteHail = bytearray(b'\x00>\x00\x00\xff\x80\x01\x80\xc0\x03\x00`\x07\x000>\x000`\x00\x1c@\x00\x0e\xc0\x00\x03\xc0\x00\x03\xc0\x00\x03\xc0\x00\x03`\x00\x03?\xff\xfe\x1f\xff\xfc\x00\x00\x00\x000\x00\x0cP\xc0\x14\xa1@)B\x8cQ\x85\x14`\x06(\x00\x00P\x00\x00`')
ByteHaze = bytearray(b'\x00|\x00\x00\xff\x01\x80\x01\x03\xc0\x00\x06\xe0\x00\x0c|\x00\x0c\x06\x008\x02\x00p\x03\x00\xc0\x03\x00\xc0\x03\x00\xc0\x03\x00\xc0\x06\x00\xc0\xfc\xff\x7f\xf8\xff?\x00\x00\x00\x80\xff\x0f\xc0\xff\x1f\x00\x00\x00\xf8\x7f\x00\xfc\xff\x00\x00\x00\x00\xc0\xff\x03\xe0\xff\x07')
ByteCloudy = bytearray(b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x0e\x00\x803\x00\x80@\x00@\xc0\x00@\x80\x0f`\x00\x10x\x00 \x0c\x00 \x04\x00 \x04\x00 \x04\x000\x08\x00\x10\xf8\xff\x0f\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')
BytePartlyCloudy = bytearray(b'\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x01\x00\x04!\x00\x08\x10\x00\x90\x03\x00`\x06\x00 \xf8\x01\x10\x0c\x03\x17\x04\x02 \x02<`\x02`\x10\x03\xc0\x88\x00\x80D\x00\x80@\x00\x80\xc0\x00@\x80\x01`\x00\xff\x1f\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')
ByteSunny = bytearray(b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x18\x00\x00\x18\x00 \x00\x04@\x00\x02\x00<\x00\x00f\x00\x00\x81\x00\x80\x81\x01\x98\x00\x19\x98\x00\x19\x80\x81\x01\x00\x81\x00\x00f\x00\x00<\x00@\x00\x02 \x00\x04\x00\x18\x00\x00\x18\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')


fbthundersnow = FrameBuffer(ByteThunderSnow, 24, 24, MONO_HLSB)
fbthunderhail = FrameBuffer(ByteThunderHail, 24, 24, MONO_HLSB)
fbthunderstorm = FrameBuffer(ByteThunderStorm, 24, 24, MONO_HMSB)
fbfreezerain = FrameBuffer(ByteFreezeRain, 24, 24, MONO_HLSB)
fbfreezedrizzle = FrameBuffer(ByteFreezeDrizzle, 24, 24, MONO_HLSB)
fbfreezefog = FrameBuffer(ByteFreezeFog, 24, 24, MONO_HLSB)
fbrain = FrameBuffer(ByteRain, 24, 24, MONO_HMSB)
fbsnow = FrameBuffer(ByteSnow, 24, 24, MONO_HLSB)
fbsnowhail = FrameBuffer(ByteSnowHail, 24, 24, MONO_HLSB)
fbhail = FrameBuffer(ByteHail, 24, 24, MONO_HLSB)
fbhaze = FrameBuffer(ByteHaze, 24, 24, MONO_HMSB)
fbovercast = FrameBuffer(ByteCloudy, 24, 24, MONO_HMSB)
fbpartlycloudy = FrameBuffer(BytePartlyCloudy, 24, 24, MONO_HMSB)
fbsunny = FrameBuffer(ByteSunny, 24, 24, MONO_HMSB)


def _safe_int(v):
    try:
        return int(v)
    except:
        return None

def _safe_float(v):
    try:
        return float(v)
    except:
        return None


def _parse_wind_from_raw(raw):
    """Robust wind parser for raw METAR/SPECI (no fancy regex)."""
    if not raw:
        return None, None, None, True, True

    raw = raw.upper()

    # Find the wind group – it always ends with KT and sits after the time group
    # Examples: 20013KT  20013G26KT  VRB04KT  VRB04G12KT  00000KT
    tokens = raw.split()
    wind_token = None
    for t in tokens:
        if t.endswith("KT") and len(t) >= 5:
            wind_token = t
            break

    if not wind_token:
        return None, None, None, True, True

    # Remove the KT
    core = wind_token[:-2]

    is_variable = False
    wind_dir = None
    speed = None
    gust = None

    if core.startswith("VRB"):
        is_variable = True
        core = core[3:]          # strip VRB
    else:
        # First 3 characters are direction
        if len(core) >= 5 and core[:3].isdigit():
            wind_dir = _safe_int(core[:3])
            if wind_dir is not None:
                wind_dir %= 360
            core = core[3:]
        else:
            is_variable = True

    # Now core is like "13" or "13G26"
    if "G" in core:
        parts = core.split("G")
        speed = _safe_float(parts[0])
        if len(parts) > 1:
            gust = _safe_float(parts[1])
    else:
        speed = _safe_float(core)

    is_calm = (speed is None) or (speed <= 0)

    return wind_dir, speed, gust, is_variable, is_calm


def parse_wind(metar):
    """
    Returns dict with dir, speed, gust, is_variable, is_calm
    Accepts raw string or JSON dict.
    """
    if isinstance(metar, str):
        d, s, g, var, calm = _parse_wind_from_raw(metar)
        return {
            "dir": d,
            "speed": s,
            "gust": g,
            "is_variable": var,
            "is_calm": calm,
        }

    # JSON path
    if not isinstance(metar, dict):
        return {"dir": None, "speed": None, "gust": None,
                "is_variable": True, "is_calm": True}

    wdir = metar.get("wdir")
    is_variable = False
    wind_dir = None

    if wdir is not None:
        wdir_str = str(wdir).strip().upper()
        if wdir_str in ("VRB", "VAR"):
            is_variable = True
        else:
            wind_dir = _safe_int(wdir_str)
            if wind_dir is not None:
                wind_dir %= 360
            else:
                is_variable = True
    else:
        is_variable = True

    speed = _safe_float(metar.get("wspd"))
    gust  = _safe_float(metar.get("wgst"))
    is_calm = (speed is None) or (speed <= 0)

    return {
        "dir": wind_dir,
        "speed": speed,
        "gust": gust,
        "is_variable": is_variable,
        "is_calm": is_calm,
    }


def _strip_rmk(metar):
    """
    Return METAR text up to (but not including) the RMK section.

    Remarks often contain historical precip groups (RAB…, SNE…, etc.)
    that must not be treated as current weather.
    """
    if not isinstance(metar, str):
        return metar
    upper = metar.upper()
    # Split on whole-token RMK so we don't clip words that merely contain it
    idx = upper.find(" RMK ")
    if idx == -1:
        # also handle RMK at start of a line or end without trailing space
        idx = upper.find(" RMK")
    if idx == -1 and upper.startswith("RMK "):
        return ""
    if idx != -1:
        return metar[:idx].rstrip()
    return metar

def decode_metar_vis_alt(metar):
    """
    Extract visibility and altimeter from a raw METAR/SPECI.

    Returns:
        (visibility, altimeter)

    Examples:
        ("10SM", "A3012")
        ("1 1/2SM", "A2994")
        ("9999", "Q1013")
        ("CAVOK", "Q1018")
        (None, None) if not found
    """
    if not isinstance(metar, str):
        return None, None

    tokens = metar.upper().replace("=", "").split()

    vis = None
    alt = None

    # Altimeter is unique: Axxxx or Qxxxx
    for t in tokens:
        if len(t) == 5 and t[0] in ("A", "Q") and t[1:].isdigit():
            alt = t
            break

    # Visibility sits after the wind group
    i = 0
    n = len(tokens)
    while i < n:
        t = tokens[i]
        if t.endswith("KT") or t.endswith("MPS") or t.endswith("KMH"):
            i += 1
            # optional variable direction: 180V240
            if i < n:
                v = tokens[i]
                if len(v) == 7 and v[3] == "V" and v[:3].isdigit() and v[4:].isdigit():
                    i += 1
            break
        i += 1

    while i < n:
        t = tokens[i]
        if t == "RMK":
            break

        if t == "CAVOK":
            vis = "CAVOK"
            break

        if t.endswith("SM"):
            # "1 1/2SM" is two tokens
            if i > 0 and tokens[i - 1].isdigit() and "/" in t:
                vis = tokens[i - 1] + " " + t
            else:
                vis = t
            break

        # ICAO visibility in meters: 4 digits
        if len(t) == 4 and t.isdigit():
            vis = t
            break

        i += 1

    return vis, alt

def parse_vis_alt(vis, alt):
    """
    Convert raw tokens into numbers.
    visibility: statute miles (float) or meters (int) — None if CAVOK/unknown
    altimeter: inHg if Axxxx, hPa if Qxxxx
    """
    vis_val = None
    vis_unit = None
    alt_val = None
    alt_unit = None

    if vis == "CAVOK":
        vis_val = 10.0
        vis_unit = "SM"          # treat as 10SM+
    elif vis and vis.endswith("SM"):
        s = vis[:-2].replace("P", "").replace("M", "")  # P6SM / M1/4SM
        if " " in s:             # 1 1/2
            whole, frac = s.split()
            num, den = frac.split("/")
            vis_val = int(whole) + float(num) / float(den)
        elif "/" in s:           # 3/4
            num, den = s.split("/")
            vis_val = float(num) / float(den)
        elif s.isdigit():
            vis_val = float(s)
        vis_unit = "SM"
    elif vis and vis.isdigit() and len(vis) == 4:
        vis_val = int(vis)
        vis_unit = "M"

    if alt and alt[0] == "A" and alt[1:].isdigit():
        alt_val = int(alt[1:]) / 100.0     # A3012 -> 30.12
        alt_unit = "inHg"
    elif alt and alt[0] == "Q" and alt[1:].isdigit():
        alt_val = int(alt[1:])             # Q1013 -> 1013
        alt_unit = "hPa"

    return vis_val, vis_unit, alt_val, alt_unit

def condition_str(metar):
    """
    Returns a list: [intensity, phenomenon]

    intensity   → "Light", "Heavy", or "" (moderate / none)
    phenomenon  → "Rain", "Thunder", "Freezing Rain", "None", etc.

    Only the body of the METAR is used; everything after RMK is ignored.
    """
    if not isinstance(metar, str):
        return ["", "None"]

    tokens = _strip_rmk(metar).upper().split()

    for t in tokens:
        # ----- Intensity -----
        intensity = ""
        clean = t
        
        if t.startswith("+"):
            intensity = "Heavy"
            clean = t[1:]
        elif t.startswith("-"):
            intensity = "Light"
            clean = t[1:]

        # ----- Thunderstorm -----
        if clean.startswith("TS"):
            # if "RA" in clean:
            #     return [intensity, "Thunder Rain"]
            if "SN" in clean:
                return [intensity, "Thunder Snow"]
            if "GR" in clean or "GS" in clean:
                return [intensity, "Thunder Hail"]
            return [intensity, "Thunderstorm"]

        # ----- Freezing precipitation -----
        if clean.startswith("FZRA"):
            return [intensity, "Frz Rain"]
        if clean.startswith("FZDZ"):
            return [intensity, "Frz Drizzle"]
        if clean.startswith("FZFG"):
            return ["", "Freezing Fog"]

        # ----- Precipitation -----
        if clean.startswith("RA"):
            return [intensity, "Rain"]
        if clean.startswith("DZ"):
            return [intensity, "Drizzle"]
        if clean.startswith("SN") or clean.startswith("SG"):
            return [intensity, "Snow"]
        if clean.startswith("PL"):
            return [intensity, "Ice Pellets"]
        if clean.startswith("GR"):
            return [intensity, "Hail"]
        if clean.startswith("GS"):
            return [intensity, "Small Hail"]
        if clean.startswith("IC"):
            return ["", "Ice Crystals"]
        if clean.startswith("UP"):
            return [intensity, "Unkn Precip"]

        # ----- Obscuration / other -----
        if clean.startswith("FG"):
            return ["", "Fog"]
        if clean.startswith("BR"):
            return ["", "Mist"]
        if clean.startswith("HZ"):
            return ["", "Haze"]
        if clean.startswith("FU"):
            return ["", "Smoke"]
        if clean.startswith("VA"):
            return ["", "Volcanic Ash"]
        if clean.startswith("DU") or clean.startswith("BLDU"):
            return ["", "Blowing Dust"]
        if clean.startswith("SA") or clean.startswith("BLSA") or clean.startswith("SS"):
            return ["", "Blowing Sand"]
        if clean.startswith("DS"):
            return ["", "Duststorm"]
        if clean.startswith("PO"):
            return ["", "Dust Whirls"]
        if clean.startswith("SQ"):
            return ["", "Squalls"]
        if clean.startswith("FC"):
            return ["", "Funnel Cloud"]
        if clean.startswith("PY"):
            return ["", "Spray"]

        # ----- Vicinity -----
        if clean.startswith("VC"):
            if "TS" in clean:
                return ["", "Thunder Near"]
            if "SH" in clean or "RA" in clean:
                return ["", "Showers Near"]
            if "FG" in clean:
                return ["", "Fog Near"]
            if "SN" in clean:
                return ["", "Snow Near"]
            return ["", "Weather Near"]

        # ----- Showers -----
        if clean.startswith("SH"):
            if "RA" in clean:
                return [intensity, "Rain Showers"]
            if "SN" in clean:
                return [intensity, "Snow Showers"]
            if "GR" in clean or "GS" in clean:
                return [intensity, "Hail Showers"]
            return [intensity, "Showers"]

    # Nothing found
    return ["", "None"]

def condition_str_list(metar):
    """
    Returns a list: [intensity, phenomenon]

    intensity   → "Light", "Heavy", or "" (moderate / none)
    phenomenon  → "Rain", "Thunder", "Freezing Rain", "None", etc.

    Only the body of the METAR is used; everything after RMK is ignored.
    """
    
    if not isinstance(metar, str):
        return [["", "None"]]

    tokens = _strip_rmk(metar).upper().split()
    list_of_conditions = []

    for t in tokens:
        # ----- Intensity -----
        intensity = ""
        clean = t
        
        if t.startswith("+"):
            intensity = "Heavy"
            clean = t[1:]
        elif t.startswith("-"):
            intensity = "Light"
            clean = t[1:]

        # ----- Thunderstorm -----
        if clean.startswith("TS"):
            # if "RA" in clean:
            #     return [intensity, "Thunder Rain"]
            if "SN" in clean:
                list_of_conditions.append([intensity, "Thunder Snow"])
                continue
            if "GR" in clean or "GS" in clean:
                list_of_conditions.append([intensity, "Thunder Hail"])
                continue
            if "RA" in clean:
                list_of_conditions.append([intensity, "Thunder Rain"])
                continue
            list_of_conditions.append([intensity, "Thunderstorm"])
            continue

        # ----- Freezing precipitation -----
        if clean.startswith("FZRA"):
            list_of_conditions.append([intensity, "Frz Rain"])
            continue
        if clean.startswith("FZDZ"):
            list_of_conditions.append([intensity, "Frz Drizzle"])
            continue
        if clean.startswith("FZFG"):
            list_of_conditions.append(["", "Freezing Fog"])
            continue

        # ----- Precipitation -----
        if clean.startswith("RA"):
            list_of_conditions.append([intensity, "Rain"])
            continue
        if clean.startswith("DZ"):
            list_of_conditions.append([intensity, "Drizzle"])
            continue
        if clean.startswith("SN") or clean.startswith("SG"):
            list_of_conditions.append([intensity, "Snow"])
            continue
        if clean.startswith("PL"):
            list_of_conditions.append([intensity, "Ice Pellets"])
            continue
        if clean.startswith("GR"):
            list_of_conditions.append([intensity, "Hail"])
            continue
        if clean.startswith("GS"):
            list_of_conditions.append([intensity, "Small Hail"])
            continue
        if clean.startswith("IC"):
            list_of_conditions.append(["", "Ice Crystals"])
            continue
        if clean.startswith("UP"):
            list_of_conditions.append([intensity, "Unkn Precip"])
            continue

        # ----- Obscuration / other -----
        if clean.startswith("FG"):
            list_of_conditions.append(["", "Fog"])
            continue
        if clean.startswith("BR"):
            list_of_conditions.append(["", "Mist"])
            continue
        if clean.startswith("HZ"):
            list_of_conditions.append(["", "Haze"])
            continue
        if clean.startswith("FU"):
            list_of_conditions.append(["", "Smoke"])
            continue
        if clean.startswith("VA"):
            list_of_conditions.append(["", "Volcanic Ash"])
            continue
        if clean.startswith("DU") or clean.startswith("BLDU"):
            list_of_conditions.append(["", "Blowing Dust"])
            continue
        if clean.startswith("SA") or clean.startswith("BLSA") or clean.startswith("SS"):
            list_of_conditions.append(["", "Blowing Sand"])
            continue
        if clean.startswith("DS"):
            list_of_conditions.append(["", "Duststorm"])
            continue
        if clean.startswith("PO"):
            list_of_conditions.append(["", "Dust Whirls"])
            continue
        if clean.startswith("SQ"):
            list_of_conditions.append(["", "Squalls"])
            continue
        if clean.startswith("FC"):
            list_of_conditions.append(["", "Funnel Cloud"])
            continue
        if clean.startswith("PY"):
            list_of_conditions.append(["", "Spray"])
            continue

        # ----- Vicinity -----
        if clean.startswith("VC"):
            if "TS" in clean:
                list_of_conditions.append(["", "Thunder Near"])
                continue
            if "SH" in clean or "RA" in clean:
                list_of_conditions.append(["", "Showers Near"])
                continue
            if "FG" in clean:
                list_of_conditions.append(["", "Fog Near"])
                continue
            if "SN" in clean:
                list_of_conditions.append(["", "Snow Near"])
                continue
            list_of_conditions.append(["", "Weather Near"])
            continue

        # ----- Showers -----
        if clean.startswith("SH"):
            if "RA" in clean:
                list_of_conditions.append([intensity, "Rain Showers"])
                continue
            if "SN" in clean:
                list_of_conditions.append([intensity, "Snow Showers"])
                continue
            if "GR" in clean or "GS" in clean:
                list_of_conditions.append([intensity, "Hail Showers"])
                continue
            list_of_conditions.append([intensity, "Showers"])
            continue

    if(len(list_of_conditions) == []):
        # Nothing found
        list_of_conditions.append(["", "None"])

    return list_of_conditions

def cloud_info(metar):
    """
    Returns a tuple: (coverage_str, ceiling_ft)

    coverage_str : "Overcast", "Broken", "Scattered", "Few", or "Clear"
    ceiling_ft   : lowest BKN/OVC/VV base in feet, or None if no ceiling

    Works with raw METAR text. Everything after RMK is ignored.
    """
    if not isinstance(metar, str):
        return "Clear", None

    tokens = _strip_rmk(metar).upper().split()

    has_ovc = False
    has_bkn = False
    has_sct = False
    has_few = False
    ceiling = None

    for t in tokens:
        # Vertical visibility (counts as a ceiling)
        if t.startswith("VV") and len(t) >= 5 and t[2:].isdigit():
            base = int(t[2:]) * 100
            if ceiling is None or base < ceiling:
                ceiling = base
            has_ovc = True          # treat VV as overcast for coverage
            continue

        # Normal cloud layers: FEW/SCT/BKN/OVC + 3-digit height
        if len(t) >= 6 and t[:3] in ("FEW", "SCT", "BKN", "OVC") and t[3:6].isdigit():
            cover = t[:3]
            base = int(t[3:6]) * 100

            if cover == "OVC":
                has_ovc = True
                if ceiling is None or base < ceiling:
                    ceiling = base
            elif cover == "BKN":
                has_bkn = True
                if ceiling is None or base < ceiling:
                    ceiling = base
            elif cover == "SCT":
                has_sct = True
            elif cover == "FEW":
                has_few = True

    # Decide coverage (highest significance wins)
    if has_ovc:
        coverage = "Overcast"
    elif has_bkn:
        coverage = "Broken"
    elif has_sct:
        coverage = "Scattered"
    elif has_few:
        coverage = "Few"
    else:
        coverage = "Clear"

    return coverage, ceiling

def cloud_info_list(metar):
    """
    Returns a list: [[coverage_str, height_ft], ...]

    coverage_str : "Overcast", "Broken", "Scattered", "Few", or "Clear"
    height_ft    : layer base in feet (VV height for vertical visibility),
                   or None if Clear / no height

    One entry per cloud group in the METAR body.
    Everything after RMK is ignored.
    """
    if not isinstance(metar, str):
        return [["Clear", None]]

    tokens = _strip_rmk(metar).upper().split()
    list_of_clouds = []

    COVER_MAP = {
        "OVC": "Overcast",
        "BKN": "Broken",
        "SCT": "Scattered",
        "FEW": "Few",
    }

    for t in tokens:
        # Vertical visibility (indefinite ceiling) — treat as Overcast
        if t.startswith("VV") and len(t) >= 5 and t[2:5].isdigit():
            height = int(t[2:5]) * 100
            list_of_clouds.append(["Overcast", height])
            continue

        # Normal layers: FEW/SCT/BKN/OVC + 3-digit height
        # Handles suffixes like BKN040CB / FEW015TCU
        if (
            len(t) >= 6
            and t[:3] in COVER_MAP
            and t[3:6].isdigit()
        ):
            coverage = COVER_MAP[t[:3]]
            height = int(t[3:6]) * 100
            list_of_clouds.append([coverage, height])
            continue

        # Explicit clear / no significant cloud
        if t in ("CLR", "SKC", "NSC", "NCD", "CAVOK"):
            list_of_clouds.append(["Clear", None])
            continue

    if len(list_of_clouds) == 0:
        list_of_clouds.append(["Clear", None])

    return list_of_clouds

def summarize(metar):
    wind = parse_wind(metar)
    return {
        "condition": condition_str(metar),
        "wind_dir": wind["dir"],
        "wind_speed": wind["speed"],
        "wind_gust": wind["gust"],
        "wind_variable": wind["is_variable"],
        "wind_calm": wind["is_calm"],
        "raw": metar if isinstance(metar, str) else None,
    }

def decode_wind(metar):
    """
    Decode wind from a raw METAR/SPECI string.

    Returns a list: [speed, gust, direction]

    Rules:
      - Calm wind          → [0, 0, 0]
      - Variable direction → direction = -1
      - No gust            → gust = 0
    """
    if not isinstance(metar, str):
        return [0, 0, 0]

    tokens = metar.upper().split()

    wind_token = None
    for t in tokens:
        if t.endswith("KT") and len(t) >= 5:
            wind_token = t
            break

    if not wind_token:
        return [0, 0, 0]

    # Strip "KT"
    core = wind_token[:-2]

    # ----- Variable or direction -----
    if core.startswith("VRB"):
        direction = -1
        core = core[3:]
    else:
        if len(core) >= 5 and core[:3].isdigit():
            direction = int(core[:3]) % 360
            core = core[3:]
        else:
            # malformed – treat as calm
            return [0, 0, 0]

    # ----- Speed and gust -----
    if "G" in core:
        parts = core.split("G")
        try:
            speed = int(parts[0])
        except:
            speed = 0
        try:
            gust = int(parts[1])
        except:
            gust = 0
    else:
        try:
            speed = int(core)
        except:
            speed = 0
        gust = 0

    # Calm
    if speed <= 0:
        return [0, 0, 0]

    return [speed, gust, direction]

def _label(value, index):
    if value is None:
        return "None"
    if isinstance(value, (list, tuple)):
        if len(value) > index and value[index]:
            return value[index]
        return "None"
    return value


def getFrameBufferForWeather(phenomenainfo, cloudinfo):
    phenomena = _label(phenomenainfo, 1)
    cloudcoverage = _label(cloudinfo, 0)

    if phenomena != "None":
        if phenomena == "Thunder Snow":
            return fbthundersnow
        elif phenomena == "Thunder Hail":
            return fbthunderhail
        elif phenomena in ("Thunderstorm", "Thunder Near", "Squalls", "Funnel Cloud","Thunder Rain"):
            return fbthunderstorm
        elif phenomena == "Frz Rain":
            return fbfreezerain
        elif phenomena == "Frz Drizzle":
            return fbfreezedrizzle
        elif phenomena == "Freezing Fog":
            return fbfreezefog
        elif phenomena in ("Rain", "Drizzle", "Rain Showers", "Showers", "Showers Near"):
            return fbrain
        elif phenomena in ("Snow", "Ice Pellets", "Snow Showers", "Snow Near"):
            return fbsnow
        elif phenomena in ("Hail", "Small Hail", "Hail Showers"):
            return fbhail
        elif phenomena == "Ice Crystals":
            return fbsnowhail
        elif phenomena == "Unkn Precip":
            return fbpartlycloudy
        elif phenomena in (
            "Fog", "Mist", "Haze", "Smoke", "Volcanic Ash",
            "Blowing Dust", "Blowing Sand", "Duststorm", "Dust Whirls",
            "Spray", "Fog Near", "Weather Near"
        ):
            return fbhaze
        else:
            return fbpartlycloudy
    else:
        if cloudcoverage in ("Overcast", "Broken"):
            return fbovercast
        elif cloudcoverage in ("Scattered", "Few"):
            return fbpartlycloudy
        else:
            return fbsunny




def decode_metar_time(metar):
    """
    Decode the observation time from a raw METAR/SPECI string.

    Returns a string like: "2026-07-25 03:01"
    or None if the time group cannot be found.
    """
    if not isinstance(metar, str):
        return None

    tokens = metar.upper().split()

    # Look for the standard time group: DDHHMMZ  (e.g. 250301Z)
    time_token = None
    for t in tokens:
        if len(t) == 7 and t.endswith("Z") and t[:6].isdigit():
            time_token = t
            break

    if not time_token:
        return None

    day    = int(time_token[0:2])
    hour   = int(time_token[2:4])
    minute = int(time_token[4:6])

    # Current UTC time as reference
    now = utime.gmtime()          # (year, month, day, hour, min, sec, ...)
    year  = now[0]
    month = now[1]
    today = now[2]

    # METARs are never more than a few hours old.
    # If the day number is more than 1 day ahead of today,
    # it belongs to the previous month (or previous year).
    if day > today + 1:
        month -= 1
        if month < 1:
            month = 12
            year -= 1

    return "{:04d}-{:02d}-{:02d} {:02d}:{:02d}".format(
        year, month, day, hour, minute
    )

def ceiling_from_layers(layers):
    """
    Find the ceiling from cloud_info_list() output.

    Ceiling = lowest Broken or Overcast layer
    (VV is already stored as Overcast by cloud_info_list).

    Returns:
        [coverage_str, height_ft]  e.g. ["Broken", 5500]
        ["Unlimited", None]        if no BKN/OVC layer
    """
    if not layers:
        return ["Unlimited", None]

    ceiling = None

    for coverage, height in layers:
        if coverage in ("Broken", "Overcast") and height is not None:
            if ceiling is None or height < ceiling[1]:
                ceiling = [coverage, height]

    if ceiling is None:
        return ["Unlimited", None]

    return ceiling

def decode_metar_temp_dew(metar):
    """
    Extract temperature and dewpoint from a raw METAR/SPECI.

    Returns:
        (temp_c, dewpoint_c) as ints
        (None, None) if the group is missing

    Examples:
        "22/17"    -> (22, 17)
        "M08/M11"  -> (-8, -11)
        "03/M02"   -> (3, -2)
    """
    if not isinstance(metar, str):
        return None, None

    body = metar.upper().split(" RMK")[0]
    tokens = body.replace("=", "").split()

    def parse_part(part):
        if not part:
            return None
        sign = -1 if part.startswith("M") else 1
        digits = part[1:] if part.startswith("M") else part
        if digits.isdigit() and 2 <= len(digits) <= 3:
            return sign * int(digits)
        return None

    for t in tokens:
        if t.count("/") != 1:
            continue
        left, right = t.split("/")
        temp = parse_part(left)
        dew = parse_part(right)
        if temp is not None and dew is not None:
            return temp, dew

    return 0, 0

def weather_info_list(metar):
    """
    Returns [[intensity, name], ...] from the METAR body.
    intensity: "+", "-", "VC", or ""
    name: matches getFrameBufferForWeather labels
    """
    if not isinstance(metar, str):
        return []

    DESC = ("MI", "PR", "BC", "DR", "BL", "SH", "TS", "FZ")
    PREC = ("DZ", "RA", "SN", "SG", "IC", "PL", "GR", "GS", "UP")
    OBS  = ("BR", "FG", "FU", "VA", "DU", "SA", "HZ", "PY")
    OTH  = ("PO", "SQ", "FC", "SS", "DS")
    ROOTS = DESC + PREC + OBS + OTH

    def is_wx_token(t):
        s = t
        if s.startswith("VC"):
            s = s[2:]
        elif s.startswith("+") or s.startswith("-"):
            s = s[1:]
        if not s or len(s) % 2:
            return False
        i = 0
        while i < len(s):
            if s[i:i + 2] not in ROOTS:
                return False
            i += 2
        return True

    def parse_token(t):
        intensity = ""
        s = t
        if s.startswith("VC"):
            intensity = "VC"
            s = s[2:]
        elif s.startswith("+") or s.startswith("-"):
            intensity = s[0]
            s = s[1:]

        parts = [s[i:i + 2] for i in range(0, len(s), 2)]
        has = lambda code: code in parts

        if intensity == "VC":
            if has("TS"):
                return [intensity, "Thunder Near"]
            if has("SH"):
                return [intensity, "Showers Near"]
            if has("FG"):
                return [intensity, "Fog Near"]
            if has("SN"):
                return [intensity, "Snow Near"]
            return [intensity, "Weather Near"]

        if has("TS") and has("SN"):
            name = "Thunder Snow"
        elif has("TS") and (has("GR") or has("GS")):
            name = "Thunder Hail"
        elif has("TS") and has("RA"):
            name = "Thunder Rain"
        elif has("TS"):
            name = "Thunderstorm"
        elif has("FZ") and has("RA"):
            name = "Frz Rain"
        elif has("FZ") and has("DZ"):
            name = "Frz Drizzle"
        elif has("FZ") and has("FG"):
            name = "Freezing Fog"
        elif has("SH") and has("RA"):
            name = "Rain Showers"
        elif has("SH") and has("SN"):
            name = "Snow Showers"
        elif has("SH") and (has("GR") or has("GS")):
            name = "Hail Showers"
        elif has("SH"):
            name = "Showers"
        elif has("RA"):
            name = "Rain"
        elif has("DZ"):
            name = "Drizzle"
        elif has("SN"):
            name = "Snow"
        elif has("PL"):
            name = "Ice Pellets"
        elif has("GR"):
            name = "Hail"
        elif has("GS"):
            name = "Small Hail"
        elif has("IC"):
            name = "Ice Crystals"
        elif has("UP"):
            name = "Unkn Precip"
        elif has("FG"):
            name = "Fog"
        elif has("BR"):
            name = "Mist"
        elif has("HZ"):
            name = "Haze"
        elif has("FU"):
            name = "Smoke"
        elif has("VA"):
            name = "Volcanic Ash"
        elif has("BL") and has("DU"):
            name = "Blowing Dust"
        elif has("BL") and has("SA"):
            name = "Blowing Sand"
        elif has("DS"):
            name = "Duststorm"
        elif has("PO"):
            name = "Dust Whirls"
        elif has("SQ"):
            name = "Squalls"
        elif has("FC"):
            name = "Funnel Cloud"
        elif has("PY"):
            name = "Spray"
        else:
            name = parts[0] if parts else "Weather"

        return [intensity, name]

    body = metar.upper().split(" RMK")[0]
    tokens = body.replace("=", "").split()
    out = []
    for t in tokens:
        if is_wx_token(t):
            out.append(parse_token(t))
    return out


def _wx_extra(intensity):
    if intensity == "+":
        return "Heavy"
    if intensity == "-":
        return "Light"
    return ""

def flight_category(vis_sm, ceiling_ft):
    """
    vis_sm     float statute miles, or None
    ceiling_ft int feet, or None for unlimited
    """
    ceil = 99999 if ceiling_ft is None else ceiling_ft
    vis = 99.0 if vis_sm is None else float(vis_sm)

    if ceil < 500 or vis < 1.0:
        return "LIFR"
    if ceil <= 1000 or vis <= 3.0:
        return "IFR"
    if ceil <= 3000 or vis <= 5.0:
        return "MVFR"
    return "VFR"


def setDisplay(display, metar, ledobject, crosswind_limit):
    """
    Updates the I2C display with METAR info.
    """

    # Clear previous content
    display.clear()

    print("List of conditions found in METAR:")
    print(condition_str_list(metar))

    print("List of cloud layers found in METAR:")
    print(cloud_info_list(metar))

    # Figure out what the top two rows should say.
    phenomenainfo=condition_str(metar)
    print(phenomenainfo)

    cloudinfo=cloud_info(metar)
    print(cloudinfo)

    if(phenomenainfo[1] is not "None"):

        if(phenomenainfo[0] is ""):
            display.set_row(0, f"   {phenomenainfo[1]}")  # e.g., "Rain", "Clear", "Thunder" …
        else:
            display.set_row(0, f"   {phenomenainfo[0]}")  # e.g., "Rain", "Clear", "Thunder" …
            display.set_row(1, f"   {phenomenainfo[1]}")  # e.g., "Rain", "Clear", "Thunder" …

    else:
        if(cloudinfo[0] is not None):
            display.set_row(0, f"   {cloudinfo[0]}")  # e.g., "Overcast", "Broken", etc.

        if(cloudinfo[1] is not None):
            display.set_row(1, f"   {cloudinfo[1]} ft")

    display.add_bitmap("test", getFrameBufferForWeather(phenomenainfo, cloudinfo), x=4, y=0, layer="bg")

    windinfo = decode_wind(metar)
    winddirection=(windinfo[2] + 180) % 360
    print(windinfo)

    if(windinfo[0] is 0):         # Wind is Calm
        display.set_row(2, f"   Wind")
        display.set_row(3, f"   Calm")
    elif(windinfo[2] is -1):      # Wind is Variable

        if(windinfo[1] is not 0): #Variable with Gusts
            display.set_row(2, f"   VRB @ {windinfo[0]}kt")
            display.set_row(3, f"   Gust {windinfo[1]}kt")
        else:                     #Variable without Gusts
            display.set_row(2, f"   Variable")
            display.set_row(3, f"   {windinfo[0]}kt")
    else:                         # Wind is from a specific direction
        if(windinfo[1] is not 0): #Specific with Gusts
            display.set_row(2, f"   {windinfo[2]} @ {windinfo[0]}kt")
            display.set_row(3, f"   Gust {windinfo[1]}kt")
        else:                     #Specific without Gusts
            display.set_row(2, f"   {windinfo[2]} @ {windinfo[0]}kt")

    if(windinfo[0] is not 0 and windinfo[2] is not -1):  # Wind is not Calm or Variable
        display.set_rotated_bitmap(key="arrow",bitmap_bytes=ByteArrow,width=24,height=24,x=4,y=24,degrees=winddirection,layer="bg")
        ledobject.update(wind_dir=windinfo[2], wind_speed=windinfo[0], calm_threshold=crosswind_limit)
    elif(windinfo[2] is -1):
        calm_fb = FrameBuffer(ByteCalm, 24, 24, MONO_HLSB)
        display.add_bitmap("calm", calm_fb, x=4, y=24, layer="bg")
        ledobject.update(wind_dir=-1, wind_speed=windinfo[0], calm_threshold=crosswind_limit)
    else:
        calm_fb = FrameBuffer(ByteCalm, 24, 24, MONO_HLSB)
        display.add_bitmap("calm", calm_fb, x=4, y=24, layer="bg")
        ledobject.update(wind_dir=0, wind_speed=0, calm_threshold=crosswind_limit)

    print(decode_metar_time(metar))
    display.set_row(4, "Metar Observed")
    display.set_row(5, f"{decode_metar_time(metar)}")

    # Refresh the display to show updates
    display.refresh()

def setDisplayPage(display, metar, ledobject, crosswind_limit, icao, currentpage):
    """
    Updates the I2C display with METAR info.
    Returns the next page index, or 0 after the last dynamic page.
    """
    display.clear()

    wx_list = weather_info_list(metar)
    cloud_list = cloud_info_list(metar)
    if cloud_list == [["Clear", None]]:
        cloud_list = []

    wx_pages = (len(wx_list) + 1) // 2
    cloud_pages = (len(cloud_list) + 1) // 2
    fixed_pages = 4
    total_pages = fixed_pages + wx_pages + cloud_pages

    if currentpage < 0 or currentpage >= total_pages:
        currentpage = 0

    if currentpage == 0:
        #display.set_row(0, "Binary Aviation")
        display.set_row(0, "RunwaySense")
        display.add_separator(after_row=1)
        display.set_row(2, "METAR Airport")
        display.set_row(3, "{}".format(icao))
        display.add_separator(after_row=3)
        display.set_row(4, "Metar Observed")
        display.set_row(5, "{}".format(decode_metar_time(metar)))

        windinfo = decode_wind(metar)
        winddirection = (windinfo[2] + 180) % 360

        if windinfo[0] != 0 and windinfo[2] != -1:
            ledobject.update(wind_dir=windinfo[2], wind_speed=windinfo[0], calm_threshold=crosswind_limit)
        elif windinfo[2] == -1:
            ledobject.update(wind_dir=-1, wind_speed=windinfo[0], calm_threshold=crosswind_limit)
        else:
            ledobject.update(wind_dir=0, wind_speed=0, calm_threshold=crosswind_limit)


    elif currentpage == 1:
        windinfo = decode_wind(metar)
        winddirection = (windinfo[2] + 180) % 360

        display.set_row(0, "Wind Conditions")

        if windinfo[0] == 0:
            display.set_row(1, "   Wind")
            display.set_row(2, "   Calm")
        elif windinfo[2] == -1:
            if windinfo[1] != 0:
                display.set_row(1, "   VRB @ {}kt".format(windinfo[0]))
                display.set_row(2, "   Gust {}kt".format(windinfo[1]))
            else:
                display.set_row(1, "   Variable")
                display.set_row(2, "   {}kt".format(windinfo[0]))
        else:
            if windinfo[1] != 0:
                display.set_row(1, "   {} @ {}kt".format(windinfo[2], windinfo[0]))
                display.set_row(2, "   Gust {}kt".format(windinfo[1]))
            else:
                display.set_row(1, "   {} @ {}kt".format(windinfo[2], windinfo[0]))

        if windinfo[0] != 0 and windinfo[2] != -1:
            display.set_rotated_bitmap(
                key="arrow", bitmap_bytes=ByteArrow,
                width=24, height=24, x=4, y=10,
                degrees=winddirection, layer="bg"
            )
            #ledobject.update(wind_dir=windinfo[2], wind_speed=windinfo[0], calm_threshold=crosswind_limit)
        elif windinfo[2] == -1:
            display.add_bitmap("calm", FrameBuffer(ByteCalm, 24, 24, MONO_HLSB), x=4, y=10, layer="bg")
            #ledobject.update(wind_dir=-1, wind_speed=windinfo[0], calm_threshold=crosswind_limit)
        else:
            display.add_bitmap("calm", FrameBuffer(ByteCalm, 24, 24, MONO_HLSB), x=4, y=10, layer="bg")
            #ledobject.update(wind_dir=0, wind_speed=0, calm_threshold=crosswind_limit)

        display.add_separator(after_row=2)

        ceiling = ceiling_from_layers(cloud_info_list(metar))
        if ceiling[1] is None:

            display.set_row(3, "Conditions")

            phenomenainfo=condition_str(metar)
            #print(phenomenainfo)

            cloudinfo=cloud_info(metar)
            #print(cloudinfo)

            if(phenomenainfo[1] is not "None"):

                if(phenomenainfo[0] is ""):
                    display.set_row(4, f"   {phenomenainfo[1]}")  # e.g., "Rain", "Clear", "Thunder" …
                else:
                    display.set_row(4, f"   {phenomenainfo[0]}")  # e.g., "Rain", "Clear", "Thunder" …
                    display.set_row(5, f"   {phenomenainfo[1]}")  # e.g., "Rain", "Clear", "Thunder" …

            else:
                if(cloudinfo[0] is not None):
                    display.set_row(4, f"   {cloudinfo[0]}")  # e.g., "Overcast", "Broken", etc.

                if(cloudinfo[1] is not None):
                    display.set_row(5, f"   {cloudinfo[1]} ft")

            display.add_bitmap("ceiling", getFrameBufferForWeather(phenomenainfo, cloudinfo), x=4, y=44, layer="bg")

        else:
            display.set_row(3, "Current Ceiling")
            display.set_row(4, "   {}".format(ceiling[0]))
            display.set_row(5, "   {} ft".format(ceiling[1]))
            ceiling_fb = getFrameBufferForWeather("None", ceiling)
            if ceiling_fb is not None:
                display.add_bitmap("ceiling", ceiling_fb, x=4, y=44, layer="bg")

    elif currentpage == 2:
        vis, alt = decode_metar_vis_alt(metar)
        vis_val, vis_unit, alt_val, alt_unit = parse_vis_alt(vis, alt)
        ceiling = ceiling_from_layers(cloud_info_list(metar))
        cat = flight_category(vis_val if vis_unit == "SM" else None, ceiling[1])

        display.set_row(0, "Visibility")
        display.set_row(1, "{} {}".format(vis_val, vis_unit))
        display.add_separator(after_row=1)
        display.set_row(2, "Altimeter")
        display.set_row(3, "{} {}".format(alt_val, alt_unit))
        display.add_separator(after_row=3)
        display.set_row(4, "Flight Category")
        display.set_row(5, "{}".format(cat))

    elif currentpage == 3:
        temp, dew = decode_metar_temp_dew(metar)
        spread = temp - dew if temp is not None and dew is not None else 0

        display.set_row(0, "Temperature")
        display.set_row(1, "{} C".format(temp if temp is not None else "--"))
        display.add_separator(after_row=1)
        display.set_row(2, "Dew Point")
        display.set_row(3, "{} C".format(dew if dew is not None else "--"))
        display.add_separator(after_row=3)
        display.set_row(4, "Spread")
        display.set_row(5, "{} C".format(spread if spread is not None else "--"))
    elif currentpage < fixed_pages + wx_pages:
        page_i = currentpage - fixed_pages
        start = page_i * 2
        items = wx_list[start:start + 2]

        display.set_row(0, "Weather")
        if wx_pages > 1:
            display.set_row(1, "{}/{}".format(page_i + 1, wx_pages))

        display.add_separator(after_row=1)

        if len(items) >= 1:
            extra = _wx_extra(items[0][0])
            if extra:
                display.set_row(2, "   {}".format(extra))
                display.set_row(3, "   {}".format(items[0][1]))
            else:
                display.set_row(2, "   {}".format(items[0][1]))
            fb = getFrameBufferForWeather(items[0], "None")
            if fb is not None:
                display.add_bitmap("wx0", fb, x=4, y=21, layer="bg")

        display.add_separator(after_row=3)

        if len(items) >= 2:
            extra = _wx_extra(items[1][0])
            if extra:
                display.set_row(4, "   {}".format(extra))
                display.set_row(5, "   {}".format(items[1][1]))
            else:
                display.set_row(4, "   {}".format(items[1][1]))
            fb = getFrameBufferForWeather(items[1], "None")
            if fb is not None:
                display.add_bitmap("wx1", fb, x=4, y=42, layer="bg")
    else:
        page_i = currentpage - fixed_pages - wx_pages
        start = page_i * 2
        items = cloud_list[start:start + 2]

        display.set_row(0, "Cloud Layers")
        if cloud_pages > 1:
            display.set_row(1, "{}/{}".format(page_i + 1, cloud_pages))

        display.add_separator(after_row=1)

        if len(items) >= 1:
            height = "Unlimited" if items[0][1] is None else "{} ft".format(items[0][1])
            display.set_row(2, "   {}".format(items[0][0]))
            display.set_row(3, "   {}".format(height))
            fb = getFrameBufferForWeather("None", items[0])
            if fb is not None:
                display.add_bitmap("cld0", fb, x=4, y=21, layer="bg")

        display.add_separator(after_row=3)

        if len(items) >= 2:
            height = "Unlimited" if items[1][1] is None else "{} ft".format(items[1][1])
            display.set_row(4, "   {}".format(items[1][0]))
            display.set_row(5, "   {}".format(height))
            fb = getFrameBufferForWeather("None", items[1])
            if fb is not None:
                display.add_bitmap("cld1", fb, x=4, y=42, layer="bg")

    display.refresh()

    next_page = currentpage + 1
    if next_page >= total_pages:
        return 0
    return next_page