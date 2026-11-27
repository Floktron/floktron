# -*- coding: utf-8 -*-
"""FLOKTRON · cameras.py — site cameras on the dashboard: is each camera online, the latest frame, a link to open it.

What it is for: security and the state of a site (is the site quiet at night, is the gate closed, did the delivery
arrive). It is NOT for watching how people work — that is not allowed in the EU (GDPR, EDPB Guidelines 3/2019);
see docs/CAMERAS.md. No recording, no face recognition, no video through anyone's server: your cameras and your
recorder keep the video, FLOKTRON only keeps ONE latest frame per camera on your computer (overwritten each time).

    python3 scripts/cameras.py [--config config/config.yaml] snap      # take the latest frame of every camera
    python3 scripts/cameras.py [--config config/config.yaml] list      # what the dashboard will show

Config (config.yaml → cameras:):
    cameras:
      enabled: true
      every_minutes: 15          # scripts/run.py / your scheduler calls «snap» this often; older frame = «no frame»
      items:
        - {id: gate, name: "Gate", place: "Site Park 12", snapshot: "http://192.168.1.20/snapshot.jpg"}
        - {id: yard, name: "Yard", place: "Site Park 12", snapshot: "rtsp://user:pass@192.168.1.21:554/stream2"}
        - {id: demo1, name: "Camera 1", place: "Riga, example", url: "https://…", demo: true,
           source: "public city webcam, …"}   # demo = link only, never fetched, marked «example» on the dashboard
Kinds of address: snapshot http(s)://…jpg (most IP cameras and recorders, ONVIF snapshot URI), rtsp://… (needs
ffmpeg installed; one frame is taken, then the connection closes), url — a page to open in the browser.
Passwords in addresses stay in your config; FLOKTRON never prints them (user:***@).
"""
import argparse
import datetime
import os
import re
import shutil
import subprocess
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
MAX_BYTES = 5 * 1024 * 1024
JPEG, PNG = b"\xff\xd8\xff", b"\x89PNG"

TEXT = {
    "en": dict(title="Site cameras", online="online", stale="no fresh frame", never="no frame yet", link="link",
               open="View site", open_demo="Open camera", demo="example", demo_note="Example: a public city webcam, not a customer site. Source: {src}",
               none="No cameras yet — add them to config.yaml → cameras (docs/CAMERAS.md)", k_on="online", k_all="cameras",
               k_off="no fresh frame", shot="frame {t}", rule="Security and the state of the site only — not watching people at work.",
               off="Camera without a fresh frame: {n}"),
    "ru": dict(title="Камеры объекта", online="в сети", stale="нет свежего кадра", never="кадра ещё нет", link="ссылка",
               open="Смотреть объект", open_demo="Открыть камеру", demo="пример", demo_note="Пример: публичная городская камера, не объект клиента. Источник: {src}",
               none="Камер пока нет — добавьте их в config.yaml → cameras (docs/CAMERAS.md)", k_on="в сети", k_all="камер",
               k_off="без свежего кадра", shot="кадр {t}", rule="Только охрана и состояние объекта — не наблюдение за работой людей.",
               off="Камера без свежего кадра: {n}"),
    "lv": dict(title="Objekta kameras", online="tīklā", stale="nav svaiga kadra", never="kadra vēl nav", link="saite",
               open="Skatīt objektu", open_demo="Atvērt kameru", demo="piemērs", demo_note="Piemērs: publiska pilsētas kamera, nevis klienta objekts. Avots: {src}",
               none="Kameru vēl nav — pievienojiet tās config.yaml → cameras (docs/CAMERAS.md)", k_on="tīklā", k_all="kameras",
               k_off="bez svaiga kadra", shot="kadrs {t}", rule="Tikai apsardze un objekta stāvoklis — ne darba novērošana.",
               off="Kamera bez svaiga kadra: {n}"),
}


def texts(lang):
    return TEXT.get(lang) or TEXT["en"]


def ccfg(cfg):
    c = dict(cfg.get("cameras") or {})
    c.setdefault("every_minutes", 15)
    c["items"] = [dict(i) for i in (c.get("items") or []) if isinstance(i, dict)]
    for n, i in enumerate(c["items"], 1):
        i["id"] = re.sub(r"[^a-z0-9_-]", "", str(i.get("id") or f"cam{n}").lower())[:32] or f"cam{n}"
        i.setdefault("name", f"Camera {n}")
    return c


def mask(url):
    """rtsp://user:pass@host → rtsp://user:***@host (never show a password)."""
    return re.sub(r"(://[^/:@]+):[^@/]*@", r"\1:***@", str(url or ""))


def frame_dir(cfg, data=None):
    c = cfg.get("cameras") or {}
    return os.path.expanduser(c.get("dir") or os.path.join(data or DATA, "cameras"))


def frame_path(cfg, data, cam_id):
    return os.path.join(frame_dir(cfg, data), f"{cam_id}.jpg")


def _write(path, blob):
    if not (blob.startswith(JPEG) or blob.startswith(PNG)):
        raise ValueError("not an image")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "wb") as f:
        f.write(blob)
    os.replace(tmp, path)      # one latest frame, overwritten — no archive


def snap_one(cfg, data, cam, timeout=15, opener=None):
    """Take one frame. Returns (ok, note). Demo / link-only cameras are never fetched."""
    src = str(cam.get("snapshot") or "")
    if cam.get("demo") or not src:
        return False, "link only"
    path = frame_path(cfg, data, cam["id"])
    try:
        if src.startswith(("http://", "https://")):
            req = urllib.request.Request(src, headers={"User-Agent": "FLOKTRON-cameras"})
            with (opener or urllib.request.urlopen)(req, timeout=timeout) as r:
                blob = r.read(MAX_BYTES + 1)
            if len(blob) > MAX_BYTES:
                return False, "frame too large"
            _write(path, blob)
            return True, "ok"
        if src.startswith(("rtsp://", "rtsps://")):
            ff = shutil.which("ffmpeg")
            if not ff:
                return False, "rtsp needs ffmpeg (brew install ffmpeg / winget install ffmpeg / apt install ffmpeg)"
            out = subprocess.run([ff, "-nostdin", "-loglevel", "error", "-rtsp_transport", "tcp", "-i", src, "-frames:v", "1",
                                  "-q:v", "4", "-f", "image2", "-vcodec", "mjpeg", "pipe:1"], capture_output=True, timeout=timeout + 10)
            if out.returncode or not out.stdout:
                return False, "no frame from rtsp"
            _write(path, out.stdout[:MAX_BYTES])
            return True, "ok"
        return False, "unknown address (http(s):// snapshot or rtsp://)"
    except Exception as e:  # network, auth, timeout — the camera is simply «offline»
        return False, mask(str(e))[:160]


def snap(cfg, data=None, opener=None):
    res = []
    for cam in ccfg(cfg)["items"]:
        ok, note = snap_one(cfg, data, cam, opener=opener)
        res.append(dict(id=cam["id"], ok=ok, note=note))
    return res


def collect(cfg, data=None, now=None, lang="en"):
    """What the dashboard shows: one card per camera."""
    now = now or datetime.datetime.now()
    c = ccfg(cfg)
    L = texts(lang)
    fresh = datetime.timedelta(minutes=max(1, int(c["every_minutes"])) * 2 + 5)
    cams, att = [], []
    for cam in c["items"]:
        p = frame_path(cfg, data, cam["id"])
        has = os.path.exists(p) and not cam.get("demo")
        when = datetime.datetime.fromtimestamp(os.path.getmtime(p)) if has else None
        if cam.get("demo") or not cam.get("snapshot"):
            st, stx = "idle", L["link"]
        elif when and now - when <= fresh:
            st, stx = "ok", L["online"]
        else:
            st, stx = "warn", L["stale"] if when else L["never"]
        url = str(cam.get("url") or "")
        cams.append(dict(id=cam["id"], name=str(cam.get("name")), place=str(cam.get("place") or ""), st=st, stx=stx,
                         url=url if url.startswith("https://") else "", demo=bool(cam.get("demo")),
                         source=str(cam.get("source") or ""), frame=p if has else "",
                         when=when.strftime("%d.%m %H:%M") if when else ""))
    off = [x["name"] for x in cams if x["st"] == "warn"]
    if off:
        att.append(dict(lvl="warn", text=L["off"].format(n=", ".join(off)), act="scripts/cameras.py snap"))
    return dict(cams=cams, on=sum(1 for x in cams if x["st"] == "ok"), n=len(cams), off=len(off), attention=att)


def load_cfg(path):
    import dashboard
    return dashboard.load_cfg(path)


def main(argv=None):
    ap = argparse.ArgumentParser(description="FLOKTRON site cameras (docs/CAMERAS.md)")
    ap.add_argument("--config", default=os.path.join(ROOT, "config", "config.yaml"))
    ap.add_argument("--data", default=DATA)
    ap.add_argument("cmd", nargs="?", default="list", choices=["snap", "list"])
    a = ap.parse_args(argv)
    cfg = load_cfg(a.config)
    if a.cmd == "snap":
        for r in snap(cfg, a.data):
            print(f'{r["id"]}: {"ok" if r["ok"] else r["note"]}')
        return 0
    for x in collect(cfg, a.data)["cams"]:
        print(f'{x["id"]}: {x["name"]} · {x["stx"]}{" · " + x["when"] if x["when"] else ""}{" · example" if x["demo"] else ""}')
    return 0


if __name__ == "__main__":
    import utf8_console  # noqa: F401
    sys.exit(main())
