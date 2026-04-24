"""Generate ui/assets/autodoku.ico from ui/assets/autodoku.svg.

Uses PyQt6 to render the SVG at multiple resolutions and Pillow to pack
them into a proper multi-size ICO file.  Run from the repo root:

    .venv\\Scripts\\python tools\\make_ico.py
"""
from __future__ import annotations

import io
import sys
from pathlib import Path

# ── Qt rendering ──────────────────────────────────────────────────────────────
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPainter, QPixmap
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtWidgets import QApplication

# ── Pillow packing ────────────────────────────────────────────────────────────
from PIL import Image

REPO_ROOT = Path(__file__).resolve().parent.parent
SVG_PATH  = REPO_ROOT / "ui" / "assets" / "autodoku.svg"
ICO_PATH  = REPO_ROOT / "ui" / "assets" / "autodoku.ico"

SIZES = [256, 128, 64, 48, 32, 16]


def main() -> None:
    app = QApplication(sys.argv)  # noqa: F841  (must stay alive during rendering)

    if not SVG_PATH.exists():
        print(f"ERROR: SVG not found at {SVG_PATH}")
        sys.exit(1)

    renderer = QSvgRenderer(str(SVG_PATH))
    pil_images: list[Image.Image] = []

    for size in SIZES:
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.end()

        # QPixmap → PIL Image via temp file
        tmp = REPO_ROOT / f"_tmp_icon_{size}.png"
        pixmap.save(str(tmp), "PNG")
        pil_images.append(Image.open(str(tmp)).copy())
        tmp.unlink(missing_ok=True)

    # Save all sizes into one ICO
    pil_images[0].save(
        str(ICO_PATH),
        format="ICO",
        sizes=[(s, s) for s in SIZES],
        append_images=pil_images[1:],
    )
    print(f"ICO written: {ICO_PATH}  ({ICO_PATH.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
