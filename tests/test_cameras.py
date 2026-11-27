# -*- coding: utf-8 -*-
"""Site cameras (TEST · FICTIONAL): status from the latest frame, demo cameras are link-only and never fetched,
passwords never shown, only images are saved, the dashboard block. No network, no real camera."""
import datetime
import io
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import cameras as cm  # noqa: E402
import dashboard as db  # noqa: E402

JPG = b"\xff\xd8\xff\xe0" + b"0" * 64
NOW = datetime.datetime(2026, 11, 27, 19, 40)


def cfg(items, lang="en"):
    return {"company": {"language": lang}, "cameras": {"enabled": True, "every_minutes": 15, "items": items}}


class Resp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_mask_hides_password():
    assert cm.mask("rtsp://admin:s3cret@10.0.0.2:554/s") == "rtsp://admin:***@10.0.0.2:554/s"
    assert "s3cret" not in cm.mask("http://u:s3cret@cam/snap.jpg")


def test_snapshot_saved_and_demo_never_fetched(tmp_path):
    calls = []

    def opener(req, timeout=0):
        calls.append(req.full_url)
        return Resp(JPG)
    c = cfg([{"id": "gate", "name": "Gate (TEST)", "snapshot": "http://192.0.2.20/snap.jpg"},
             {"id": "demo1", "name": "Camera 1", "demo": True, "url": "https://example.org/cam", "snapshot": "http://example.org/x.jpg"}])
    res = cm.snap(c, str(tmp_path), opener=opener)
    assert calls == ["http://192.0.2.20/snap.jpg"]
    assert res[0]["ok"] and not res[1]["ok"]
    assert (tmp_path / "cameras" / "gate.jpg").read_bytes() == JPG
    assert not (tmp_path / "cameras" / "demo1.jpg").exists()


def test_not_an_image_is_refused(tmp_path):
    c = cfg([{"id": "gate", "snapshot": "http://192.0.2.20/snap.jpg"}])
    ok, note = cm.snap_one(c, str(tmp_path), cm.ccfg(c)["items"][0], opener=lambda r, timeout=0: Resp(b"<html>login</html>"))
    assert not ok and not (tmp_path / "cameras" / "gate.jpg").exists()


def test_status_fresh_stale_never_link(tmp_path):
    d = tmp_path / "cameras"
    d.mkdir()
    for n, age in (("a", 10), ("b", 6 * 60)):
        p = d / f"{n}.jpg"
        p.write_bytes(JPG)
        t = time.mktime((NOW - datetime.timedelta(minutes=age)).timetuple())
        os.utime(p, (t, t))
    c = cfg([{"id": "a", "snapshot": "http://192.0.2.1/s.jpg"}, {"id": "b", "snapshot": "http://192.0.2.2/s.jpg"},
             {"id": "c", "snapshot": "rtsp://192.0.2.3/s"}, {"id": "d", "demo": True, "url": "https://example.org/cam"}])
    r = cm.collect(c, str(tmp_path), NOW)
    assert [x["st"] for x in r["cams"]] == ["ok", "warn", "warn", "idle"]
    assert r["on"] == 1 and r["off"] == 2 and r["attention"]


def test_only_https_links(tmp_path):
    r = cm.collect(cfg([{"id": "d", "demo": True, "url": "javascript:alert(1)"}]), str(tmp_path), NOW)
    assert r["cams"][0]["url"] == ""


def test_dashboard_block_marks_examples(tmp_path):
    c = cfg([{"id": "demo1", "name": "Камера 1", "demo": True, "url": "https://example.org/cam", "source": "Example Cams"}], "ru")
    D = db.collect(c, str(tmp_path), NOW)
    D["_outdir"] = str(tmp_path)
    page = db.render(D)
    assert 'id="cameras"' in page and "пример" in page and "не объект клиента" in page and "Example Cams" in page
    assert "<iframe" not in page


def test_no_block_when_off(tmp_path):
    D = db.collect({"company": {"language": "en"}}, str(tmp_path), NOW)
    D["_outdir"] = str(tmp_path)
    assert 'id="cameras"' not in db.render(D)


def test_button_labels():
    """Own camera → «View site»; a link-only public example keeps «Open camera» (TEST · FICTIONAL)."""
    import cameras
    for lang, own, demo in (("en", "View site", "Open camera"), ("ru", "Смотреть объект", "Открыть камеру"),
                            ("lv", "Skatīt objektu", "Atvērt kameru")):
        L = cameras.texts(lang)
        assert (L["open"], L["open_demo"]) == (own, demo)
