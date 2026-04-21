"""
modules/cell_format.py
Excel cell value formatters and colour resolution helpers.
"""

import datetime
import re


# ── Theme-colour index ────────────────────────────────────────────────────────
_THEME_COLORS: dict[int, str] = {
    0: "FFFFFF", 1: "000000", 2: "EEECE1", 3: "1F497D",
    4: "4F81BD", 5: "C0504D", 6: "9BBB59", 7: "8064A2",
    8: "4BACC6", 9: "F79646",
}


def _resolve_color(color_obj, default: str = "FFFFFF") -> str:
    if color_obj is None:
        return default
    t = color_obj.type
    if t == "rgb":
        rgb = color_obj.rgb or ""
        if len(rgb) == 8 and rgb not in ("00000000", "FF000000"):
            return rgb[2:]
        if len(rgb) == 6:
            return rgb
        return default
    if t == "theme":
        base = _THEME_COLORS.get(color_obj.theme, default)
        tint = color_obj.tint or 0.0
        if tint != 0.0:
            r, g, b = int(base[0:2], 16), int(base[2:4], 16), int(base[4:6], 16)
            if tint > 0:
                r, g, b = int(r + (255 - r) * tint), int(g + (255 - g) * tint), int(b + (255 - b) * tint)
            else:
                r, g, b = int(r * (1 + tint)), int(g * (1 + tint)), int(b * (1 + tint))
            return f"{max(0, min(255, r)):02X}{max(0, min(255, g)):02X}{max(0, min(255, b)):02X}"
        return base
    if t == "indexed":
        indexed_map = {
            0: "000000", 1: "FFFFFF", 2: "FF0000", 3: "00FF00", 4: "0000FF",
            5: "FFFF00", 6: "FF00FF", 7: "00FFFF", 64: "000000", 65: "FFFFFF",
        }
        return indexed_map.get(color_obj.indexed, default)
    return default


def format_cell_value(value) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime.datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S") if (value.hour or value.minute) else value.strftime("%Y-%m-%d")
    if isinstance(value, datetime.date):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if value == int(value):
            return f"{int(value)}.0"
        formatted = f"{value:.10f}".rstrip("0")
        if "." not in formatted:
            formatted += ".0"
        return formatted
    from modules.normalization import normalize_str
    return normalize_str(str(value).strip())


def _apply_date_number_format(dt, nf: str) -> str:
    if not nf or nf.lower() in ("general", "@", ""):
        return dt.strftime("%m-%d-%Y")
    fmt    = re.sub(r"\[.*?\]", "", nf)
    fmt    = re.sub(r'["_*\\]', "", fmt)
    result = fmt
    result = re.sub(r"(?i)(?<=h)mm", "__MIN__", result)
    result = re.sub(r"(?i)mm(?=ss)", "__MIN__", result)

    def _tok(m):
        tok = m.group(0).lower()
        return {
            "yyyy": "%Y", "yy": "%y", "mmmm": "%B", "mmm": "%b",
            "mm": "%m", "__min__": "%M", "m": "%m", "dd": "%d", "d": "%d",
            "hh": "%H", "h": "%H", "ss": "%S", "s": "%S",
            "am/pm": "%p", "a/p": "%p",
        }.get(tok, m.group(0))

    result = re.sub(r"(?i)yyyy|yy|mmmm|mmm|__min__|mm|dd|hh|ss|am/pm|a/p|d|h|s|m", _tok, result)
    try:
        return dt.strftime(result)
    except Exception:
        return dt.strftime("%m-%d-%Y")


def format_cell_value_with_fmt(cell) -> str:
    value = cell.value
    if value is None:
        return ""
    nf = (cell.number_format or "").strip()
    if isinstance(value, (datetime.datetime, datetime.date)):
        return _apply_date_number_format(value, nf)
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, (int, float)):
        decimal_places = None
        if nf and nf.lower() not in ("general", "@", ""):
            clean_nf    = re.sub(r'[$€£¥"_*\\]', "", nf)
            is_date_fmt = (
                any(x in clean_nf.lower() for x in ["yy", "mm", "dd", "hh", "ss"])
                and not any(ch in clean_nf for ch in ["0", "#"])
            )
            if not is_date_fmt:
                if "." in clean_nf:
                    after_dot      = re.sub(r"\[.*?\]", "", clean_nf.split(".")[1])
                    decimal_places = sum(1 for ch in after_dot if ch in "0#")
                else:
                    decimal_places = 0
        if decimal_places is not None:
            fval = float(value)
            return str(int(round(fval))) if decimal_places == 0 else f"{fval:.{decimal_places}f}"
        if isinstance(value, int):
            return str(value)
        fval      = float(value)
        remainder = fval - int(fval)
        if remainder == 0.0:
            return f"{fval:.2f}"
        formatted = f"{fval:.10f}".rstrip("0")
        if "." not in formatted:
            formatted += ".00"
        elif len(formatted.split(".")[1]) < 2:
            formatted = f"{fval:.2f}"
        return formatted
    from modules.normalization import normalize_str
    return normalize_str(str(value).strip())
