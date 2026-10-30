"""Colour themes. Each theme only needs a handful of base colours; every other colour
(soft fills, hover colours, table stripes, ...) is calculated from them, so a new theme is 6 lines."""


def _rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _hex(rgb):
    return "#%02X%02X%02X" % tuple(max(0, min(255, round(v))) for v in rgb)


def mix(a, b, t):
    """Colour between a (t=0) and b (t=1)."""
    ra, rb = _rgb(a), _rgb(b)
    return _hex([ra[i] * (1 - t) + rb[i] * t for i in range(3)])


BLACK, WHITE = "#000000", "#FFFFFF"

# name: (is_dark, background, card, accent, text, muted, line)
BASE = {
    "green":    (False, "#F4F2EB", "#FFFFFF", "#1F6B4F", "#1E2B26", "#6B7A73", "#E2DFD5"),
    "ocean":    (False, "#EEF3F8", "#FFFFFF", "#1F5E9E", "#1B2733", "#667889", "#D9E2EC"),
    "sunset":   (False, "#FBF3EC", "#FFFFFF", "#C2562B", "#2E2019", "#80695C", "#EBDCCF"),
    "purple":   (False, "#F4F0F8", "#FFFFFF", "#6B3FA0", "#241B30", "#74678A", "#E1D8EC"),
    "night":    (True,  "#14181A", "#1E2427", "#3FB287", "#E6ECE9", "#8FA19A", "#2F383B"),
    "midnight": (True,  "#0F1420", "#182033", "#5B9BF0", "#E4EAF5", "#8E9BB5", "#2A3550"),
}
THEME_ORDER = ["green", "ocean", "sunset", "purple", "night", "midnight"]
LIGHT_DEFAULT, DARK_DEFAULT = "green", "night"


def is_dark(name):
    return BASE[name][0]


def palette(name):
    """Returns every colour constant used by the program for the given theme."""
    dark, bg, card, acc, text, muted, line = BASE[name]
    p = {"DARK_MODE": dark, "BG": bg, "CARD": card, "TEXT": text, "MUTED": muted, "LINE": line, "ACCENT": acc}

    # main action colour (button fill, white text on it)
    p["PRIMARY"] = mix(acc, BLACK, 0.32) if dark else acc
    p["PRIMARY_DARK"] = mix(acc, BLACK, 0.48) if dark else mix(acc, BLACK, 0.25)
    soft = 0.80 if dark else 0.88
    p["PRIMARY_SOFT"] = mix(acc, card, soft)

    # warm / danger / blue accents
    p["AMBER"], p["AMBER_DARK"] = "#E8A33D", "#C98A27"
    p["AMBER_TEXT"] = "#F0B85C" if dark else "#B4731A"
    p["AMBER_SOFT"] = mix(p["AMBER"], card, 0.82 if dark else 0.86)
    p["DANGER"], p["DANGER_DARK"] = "#C0443B", "#A2362E"
    p["DANGER_TEXT"] = "#FF8F86" if dark else "#A2362E"
    p["DANGER_SOFT"] = mix(p["DANGER"], card, 0.82 if dark else 0.88)
    p["BLUE"], p["BLUE_DARK"] = "#3F6FB5", "#32588F"
    p["BLUE_TEXT"] = "#6FA3F0" if dark else "#3F6FB5"
    p["ON_AMBER"] = "#2B1D05"
    p["ALERT_FG"] = "#F3C46E" if dark else "#7A4A06"
    p["CH_PURPLE"], p["CH_TEAL"] = ("#A98BE0", "#4FB3B3") if dark else ("#8A5CC2", "#2E8B8B")

    # soft buttons (light green style buttons) and neutral buttons
    p["SOFT_BTN"] = mix(acc, card, 0.78 if dark else 0.84)
    p["SOFT_BTN_HOVER"] = mix(acc, card, 0.66 if dark else 0.72)
    p["SOFT_FG"] = mix(acc, WHITE, 0.25) if dark else p["PRIMARY_DARK"]
    p["NEUTRAL_BTN"] = mix(card, WHITE, 0.12) if dark else mix(bg, text, 0.07)
    p["NEUTRAL_HOVER"] = mix(card, WHITE, 0.20) if dark else mix(bg, text, 0.14)

    # surfaces
    p["FIELD_BG"] = mix(card, BLACK, 0.25) if dark else mix(card, bg, 0.5)
    p["HEAD_BG"] = mix(card, WHITE, 0.06) if dark else mix(bg, text, 0.04)
    p["ODD_BG"] = mix(card, WHITE, 0.03) if dark else mix(card, bg, 0.5)
    p["BOX_BG"] = p["ODD_BG"]
    p["SELECT"] = mix(acc, card, 0.68 if dark else 0.80)
    p["TAB_BG"] = mix(bg, WHITE, 0.07) if dark else mix(bg, text, 0.07)

    # top bar
    p["HEADER"] = mix(acc, bg, 0.62) if dark else acc
    p["HEADER_BTN"] = mix(p["HEADER"], BLACK, 0.25)
    p["HEADER_HOVER"] = mix(p["HEADER"], BLACK, 0.40)
    p["HEADER_SUB"] = mix(p["HEADER"], WHITE, 0.75)
    return p
