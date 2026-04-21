"""
modules/logo.py
Loads the ValueMomentum logo — no cropping, no padding, no background box.
Supports .png, .jpg, .jpeg
"""

import base64
import os


def _load_image_b64(filename: str) -> tuple[str, str]:
    cwd = os.getcwd()
    module_dir = os.path.dirname(os.path.abspath(__file__))
    root = os.path.abspath(os.path.join(module_dir, ".."))

    candidates = [
        os.path.join(cwd, filename),
        os.path.join(cwd, "assets", filename),
        os.path.join(root, filename),
        os.path.join(root, "assets", filename),
    ]
    for path in candidates:
        if os.path.exists(path):
            ext = os.path.splitext(path)[1].lower()
            mime = "image/jpeg" if ext in (".jpg", ".jpeg") else "image/png"
            with open(path, "rb") as f:
                return base64.b64encode(f.read()).decode(), mime
    return "", ""


# Left side — Signal Hub screenshot
LOGO_B64, LOGO_MIME = _load_image_b64("Screenshot 2026-04-14 125311.png")

# Right badge — ValueMomentum logo
BADGE_LOGO_B64, BADGE_LOGO_MIME = _load_image_b64("valuemomentum_logo.jpg")


def logo_img_tag(height: int = 200) -> str:
    """Left navbar logo — Signal Hub. Large height for navbar visibility."""
    if not LOGO_B64:
        return ""
    mime = LOGO_MIME or "image/png"
    return (
        f'<img src="data:{mime};base64,{LOGO_B64}" '
        f'style="height:{height}px;width:auto;transform:scale(1.3);" '
        f'display:inline-block;vertical-align:middle;'
        f'margin-right:18px;flex-shrink:0;" />'
    )