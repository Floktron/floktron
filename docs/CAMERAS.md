# Site cameras — is the camera online, the latest frame, a link to open it

The dashboard shows the cameras of your sites next to tasks and work time: gate, yard, warehouse, shop. For each
camera you see whether it is online, the latest frame and when it was taken. A camera that went quiet appears under
**Needs your attention**.

**What it is for:** security and the state of a site (is the yard quiet at night, is the gate closed, did the
delivery arrive). **What it is not for:** watching how people work. See *The rules* below.

## How it works

| Step | What happens |
|---|---|
| 1 | You list your cameras in `config.yaml → cameras` |
| 2 | `python3 scripts/cameras.py snap` takes **one frame** from every camera (your scheduler or `run.py` calls it every `every_minutes`, 15 by default) |
| 3 | The frame is saved as `data/cameras/<id>.jpg` and **overwritten** next time. There is no archive and no recording |
| 4 | The dashboard shows the frame, «online» / «no fresh frame», and a button to open the camera's own page or app |

The video stays in your cameras and your recorder (NVR, the maker's cloud). FLOKTRON does not replace the recorder,
does not stream video and sends nothing anywhere.

## Which cameras work

| Address in the config | Typical cameras | Needs |
|---|---|---|
| `snapshot: "http://192.168.1.20/snapshot.jpg"` | most IP cameras and recorders; the ONVIF snapshot address | nothing |
| `snapshot: "rtsp://user:pass@192.168.1.21:554/stream2"` | any camera with an RTSP stream (Hikvision, Dahua, Axis, Reolink, Ubiquiti…) | `ffmpeg` installed (`brew install ffmpeg`, `winget install ffmpeg`, `apt install ffmpeg`). One frame is taken, then the connection closes |
| `url: "https://…"` | a page or app to open the camera live | — |

Use the **second (small) stream** of a camera for snapshots: it is lighter. Passwords stay in your config;
FLOKTRON never prints them (`user:***@`). Keep the cameras inside your network: do not open RTSP to the internet.

```yaml
cameras:
  enabled: true
  every_minutes: 15
  items:
    - {id: gate, name: "Gate", place: "Site Park 12", snapshot: "http://192.168.1.20/snapshot.jpg", url: "https://…your camera app…"}
    - {id: yard, name: "Yard", place: "Site Park 12", snapshot: "rtsp://user:pass@192.168.1.21:554/stream2"}
```

Check: `python3 scripts/cameras.py snap`, then `python3 scripts/cameras.py list`, then rebuild the dashboard.

## Examples with public city webcams

To show how the block looks before your own cameras are connected, a camera can be marked `demo: true`. It is a
**link only**: FLOKTRON never fetches, copies or embeds it, and the dashboard marks it **example** with the source:

```yaml
    - {id: demo1, name: "Camera 1 · Vanšu bridge", place: "Riga · example", demo: true,
       url: "https://balticlivecam.com/cameras/latvia/riga/vansu-bridge/", source: "Baltic Live Cam (balticlivecam.com)"}
```

Public webcams belong to their owners. Linking to their page is fine; showing their picture or video inside your
own page needs the owner's permission (check their terms). Never present a public webcam as a customer's site.

## The rules (EU; check with your lawyer)

- Cameras for **security of property and safety** on a site, in a warehouse or a shop are normal and lawful when
  people are informed: a sign «video surveillance» and full information (who, why, how long it is kept, their rights)
  — GDPR Art. 5, 6, 13.
- **Not allowed:** constant watching of how a particular person works; cameras in rest rooms, changing rooms,
  toilets (EDPB Guidelines 3/2019 on video devices; in Latvia — the Data State Inspectorate guidance and the Labour Law).
- Systematic monitoring of employees → a DPIA (GDPR Art. 35). Keep recordings only as long as needed (your recorder's
  setting; you and your lawyer decide).
- No face recognition: faces are special category data (GDPR Art. 9). FLOKTRON does not analyse frames at all.
- Work time is counted with buttons ([WORKTIME](WORKTIME.md)), **never** with cameras.

Responsibility for the purpose and for informing people stays with the employer (you).
