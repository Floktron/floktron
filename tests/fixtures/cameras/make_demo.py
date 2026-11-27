# -*- coding: utf-8 -*-
"""TEST · FICTIONAL — site cameras for an invented company, to see the dashboard block.

    python3 tests/fixtures/cameras/make_demo.py OUT_DIR [--lang ru] [--now "2026-11-27 19:40"]
Writes OUT_DIR/config.yaml and OUT_DIR/cameras/*.jpg (drawn pictures, no real camera); then:
    python3 scripts/dashboard.py --config OUT_DIR/config.yaml --data OUT_DIR
Camera 1 and Camera 2 are public city webcams of Riga — link only, marked «example», never fetched.
The two site cameras are invented (TEST · FICTIONAL): one online, one without a fresh frame."""
import argparse
import datetime
import os
import time

from PIL import Image, ImageDraw

PUBLIC = [  # public city webcams: a link to the owner's page, nothing embedded or copied
    {"id": "demo1", "name": "Camera 1 · Vanšu bridge", "place": "Riga · example", "demo": True,
     "url": "https://balticlivecam.com/cameras/latvia/riga/vansu-bridge/", "source": "Baltic Live Cam (balticlivecam.com)"},
    {"id": "demo2", "name": "Camera 2 · Old Riga panorama", "place": "Riga · example", "demo": True,
     "url": "https://balticlivecam.com/cameras/latvia/riga/panorama-of-riga/", "source": "Baltic Live Cam (balticlivecam.com)"},
]
NAMES = {"ru": ("Камера 1 · Вантовый мост", "Камера 2 · панорама Старой Риги", "Рига · пример", "Ворота (TEST)", "Площадка (TEST)"),
         "lv": ("Kamera 1 · Vanšu tilts", "Kamera 2 · Vecrīgas panorāma", "Rīga · piemērs", "Vārti (TEST)", "Laukums (TEST)"),
         "en": ("Camera 1 · Vanšu bridge", "Camera 2 · Old Riga panorama", "Riga · example", "Gate (TEST)", "Yard (TEST)")}


def picture(path, night, label):
    """A drawn site: fence, cabin, crane, light — so the block has a frame to show (TEST · FICTIONAL)."""
    w, h = 960, 540
    im = Image.new("RGB", (w, h), (18, 28, 46) if night else (176, 196, 214))
    d = ImageDraw.Draw(im)
    d.rectangle([0, 360, w, h], fill=(40, 44, 52) if night else (120, 118, 110))
    d.rectangle([620, 120, 636, 360], fill=(214, 158, 46))                     # crane mast
    d.rectangle([420, 120, 860, 134], fill=(214, 158, 46))                     # jib
    d.line([628, 134, 700, 300], fill=(60, 60, 60), width=3)
    d.rectangle([120, 280, 330, 380], fill=(74, 153, 40) if not night else (40, 80, 30))   # site cabin
    d.rectangle([150, 305, 200, 345], fill=(255, 236, 160) if night else (200, 220, 235))
    for x in range(0, w, 48):                                                   # fence
        d.line([x, 390, x, 470], fill=(170, 170, 170), width=4)
    d.line([0, 400, w, 400], fill=(170, 170, 170), width=3)
    d.line([0, 460, w, 460], fill=(170, 170, 170), width=3)
    if night:
        d.ellipse([760, 330, 790, 360], fill=(255, 245, 200))
    d.rectangle([0, 0, w, 34], fill=(0, 0, 0))
    d.text((12, 10), f"{label}   TEST · FICTIONAL", fill=(255, 255, 255))
    im.save(path, "JPEG", quality=82)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--lang", default="ru")
    ap.add_argument("--now", default="")
    a = ap.parse_args()
    n1, n2, place, gate, yard = NAMES.get(a.lang, NAMES["en"])
    os.makedirs(os.path.join(a.out, "cameras"), exist_ok=True)
    pub = [dict(PUBLIC[0], name=n1, place=place), dict(PUBLIC[1], name=n2, place=place)]
    site = [{"id": "gate", "name": gate, "place": "Objekts Parka 12 (TEST)", "snapshot": "http://192.0.2.20/snapshot.jpg"},
            {"id": "yard", "name": yard, "place": "Objekts Parka 12 (TEST)", "snapshot": "rtsp://user:secret@192.0.2.21:554/stream2"}]
    picture(os.path.join(a.out, "cameras", "gate.jpg"), True, "GATE 19:38")
    picture(os.path.join(a.out, "cameras", "yard.jpg"), False, "YARD 14:02")
    old = time.time() - 6 * 3600
    os.utime(os.path.join(a.out, "cameras", "yard.jpg"), (old, old))            # the yard camera went quiet
    import yaml
    cfg = {"company": {"name": "TEST · FICTIONAL SIA Paraugs Būve", "language": a.lang},
           "cameras": {"enabled": True, "every_minutes": 15, "items": pub + site}}
    with open(os.path.join(a.out, "config.yaml"), "w", encoding="utf-8") as f:
        yaml.safe_dump(cfg, f, allow_unicode=True, sort_keys=False)
    print(f"TEST · FICTIONAL: {len(pub)} public examples + {len(site)} site cameras → {a.out}")


if __name__ == "__main__":
    main()
