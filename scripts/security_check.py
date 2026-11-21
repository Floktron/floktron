# -*- coding: utf-8 -*-
"""FLOKTRON · security_check.py — the last step of every setup: how well is YOUR computer protected?

    python3 scripts/security_check.py            # report on screen + data/security_check_<date>.txt
    python3 scripts/security_check.py --manual   # also print the checklist of things no script can see

READ ONLY. It only asks the system for its settings (the same as looking at the settings window).
It changes nothing, needs no administrator password, never uses sudo, sends nothing anywhere.
Every ⚠️ / ❌ comes with "how to fix": the PERSON changes the setting, not this script and not an AI agent.
Works on macOS, Windows and Linux; checks that cannot be read on this computer are shown as ❔ with a manual way.
"""
import datetime
import os
import platform
import re
import stat
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")

OK, WARN, BAD, UNK, INFO = "✅", "⚠️", "❌", "❔", "ℹ️"

# Ports that mean "this computer shares something with the network". Listening on 127.0.0.1 only is fine.
SHARING_PORTS = {
    22: "Remote login (SSH)", 139: "Windows file sharing (NetBIOS)", 445: "File sharing (SMB)",
    548: "File sharing (AFP)", 3283: "Remote management (Apple Remote Desktop)", 3389: "Remote Desktop (RDP)",
    5900: "Screen sharing (VNC)", 5985: "Windows remote management (WinRM)", 5986: "Windows remote management (WinRM)",
    3689: "Media sharing (iTunes/Music)", 5000: "AirPlay receiver", 7000: "AirPlay receiver", 631: "Printer sharing",
    11434: "Local AI model server (Ollama)", 2375: "Docker without TLS", 3306: "Database (MySQL)",
    5432: "Database (PostgreSQL)", 6379: "Database (Redis)", 27017: "Database (MongoDB)",
}

# Only these programs may be started, and only to READ a setting. tests/test_security_check.py keeps this list honest.
READ_ONLY_COMMANDS = {
    "fdesetup", "socketfilterfw", "csrutil", "spctl", "defaults", "sysadminctl", "netstat", "sw_vers",
    "tmutil", "id", "uname", "powershell", "netsh", "reg", "ss", "ufw", "firewall-cmd", "lsblk",
}


def run(cmd, timeout=15):
    """Run one read-only command (list of arguments, no shell). Returns (exit code, stdout+stderr) or (None, '')."""
    name = os.path.basename(cmd[0])
    if name.lower().removesuffix(".exe") not in READ_ONLY_COMMANDS:
        raise ValueError(f"not a read-only command: {name}")
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, (r.stdout or "") + (r.stderr or "")
    except (OSError, subprocess.SubprocessError):
        return None, ""


class Report:
    def __init__(self):
        self.rows = []

    def add(self, status, area, what, explain, fix=""):
        self.rows.append(dict(status=status, area=area, what=what, explain=explain, fix=fix))

    def counts(self):
        return {s: sum(1 for r in self.rows if r["status"] == s) for s in (OK, WARN, BAD, UNK, INFO)}

    def text(self, title):
        c = self.counts()
        out = [title, "=" * len(title), "",
               f"{OK} {c[OK]} fine · {WARN} {c[WARN]} worth fixing · {BAD} {c[BAD]} fix first · "
               f"{UNK} {c[UNK]} check by hand · {INFO} {c[INFO]} for your information", ""]
        order = {BAD: 0, WARN: 1, UNK: 2, INFO: 3, OK: 4}
        area = None
        for r in sorted(self.rows, key=lambda r: (r["area"], order[r["status"]])):
            if r["area"] != area:
                area = r["area"]
                out += ["", f"## {area}"]
            out.append(f"{r['status']} {r['what']} — {r['explain']}")
            if r["fix"] and r["status"] in (WARN, BAD, UNK):
                out.append(f"   How to fix (you do it): {r['fix']}")
        return "\n".join(out) + "\n"


# ---------- parsing helpers (tested) ----------

def open_ports(text, kind):
    """Ports listening on ALL network interfaces (not only 127.0.0.1 / ::1). kind: 'bsd' | 'win' | 'ss'."""
    ports = set()
    for line in text.splitlines():
        u = line.upper()
        if kind == "bsd":       # macOS netstat -an: tcp4  0  0  *.22  *.*  LISTEN
            if "LISTEN" not in u:
                continue
            parts = line.split()
            if len(parts) < 4:
                continue
            local = parts[3]
            m = re.match(r"^(\*|0\.0\.0\.0|::|\[::\])[.:](\d+)$", local)
        elif kind == "win":     # TCP  0.0.0.0:445  0.0.0.0:0  LISTENING
            if "LISTENING" not in u:
                continue
            parts = line.split()
            if len(parts) < 2:
                continue
            m = re.match(r"^(0\.0\.0\.0|\[::\]):(\d+)$", parts[1])
        else:                   # ss -tlnH: LISTEN 0 128 0.0.0.0:22 0.0.0.0:*
            parts = line.split()
            if len(parts) < 4 or not parts[0].upper().startswith("LISTEN"):
                continue
            m = re.match(r"^(\*|0\.0\.0\.0|\[::\]|::)(?:%\S+)?:(\d+)$", parts[3])
        if m:
            ports.add(int(m.group(2)))
    return ports


def secret_in_text(text):
    """True if a settings text holds a real-looking password/token value (not a placeholder or *_env name)."""
    for m in re.finditer(r"(?im)^\s*([a-z_]*(?:password|passwd|token|secret|api_key)[a-z_]*)\s*[:=]\s*['\"]?([^'\"#\s]+)", text):
        key, val = m.group(1).lower(), m.group(2)
        if key.endswith("_env") or len(val) < 6 or val.upper() == val and "_" in val:
            continue
        if val.lower() in ("none", "null", "false", "true", "changeme"):
            continue
        return True
    return False


# ---------- checks for every computer: FLOKTRON itself ----------

def check_floktron(rep):
    a = "1. FLOKTRON folder and your data"
    cfg = os.path.join(ROOT, "config", "config.yaml")
    if os.path.exists(cfg):
        txt = open(cfg, encoding="utf-8", errors="ignore").read()
        if secret_in_text(txt):
            rep.add(BAD, a, "Password or token written in config.yaml",
                    "anyone who opens or copies the folder gets it",
                    "delete the value from the file, change that password, save the new one in the keychain / "
                    "environment variable (docs/GMAIL_TEST.md step 4, docs/TELEGRAM.md)")
        else:
            rep.add(OK, a, "No passwords in config.yaml", "passwords live in the keychain or an environment variable")
    else:
        rep.add(INFO, a, "config.yaml not found", "setup is not finished yet — run the check again at the end")
    for name in (".env", "secrets.txt", "passwords.txt"):
        for d in (ROOT, os.path.join(ROOT, "config"), DATA):
            p = os.path.join(d, name)
            if os.path.isfile(p) and secret_in_text(open(p, encoding="utf-8", errors="ignore").read()):
                rep.add(WARN, a, f"Passwords in a plain file ({os.path.relpath(p, ROOT)})",
                        "a plain text file is copied by backups and cloud sync together with everything else",
                        "move them to the system keychain / environment variable and delete the file")
    if os.name == "posix":
        loose = []
        for p in (cfg, DATA):
            if os.path.exists(p) and os.stat(p).st_mode & (stat.S_IRWXG | stat.S_IRWXO):
                loose.append(os.path.relpath(p, ROOT))
        if loose:
            rep.add(WARN, a, "Other users of this computer can read " + ", ".join(loose),
                    "settings and the base are only for you",
                    "chmod 600 config/config.yaml && chmod 700 data")
        else:
            rep.add(OK, a, "Settings and data readable only by you", "file permissions are tight")
    gi = os.path.join(ROOT, ".gitignore")
    if os.path.exists(gi) and all(x in open(gi, encoding="utf-8").read() for x in ("config/config.yaml", "data/*")):
        rep.add(OK, a, "Settings and data never go to git", ".gitignore protects config.yaml and data/")
    else:
        rep.add(WARN, a, ".gitignore is missing or changed", "settings or data could end up in a repository",
                "restore .gitignore from the FLOKTRON repository")
    low = ROOT.lower()
    cloud = next((n for k, n in (("mobile documents", "iCloud Drive"), ("google drive", "Google Drive"), ("googledrive", "Google Drive"),
                                 ("onedrive", "OneDrive"), ("dropbox", "Dropbox")) if k in low), None)
    if cloud:
        rep.add(INFO, a, f"FLOKTRON folder is in {cloud}",
                "good: version history restores a damaged base. Sync is not a backup — a deleted or encrypted file "
                "is deleted everywhere. Keep one extra copy that is NOT always connected (section 5 of the manual list)")
    else:
        rep.add(WARN, a, "FLOKTRON folder is only on this disk", "a broken disk or a lost laptop takes the bases with it",
                "keep the folder in a cloud with version history, or back it up regularly (docs/STORAGE.md)")


def check_account(rep, system):
    a = "2. Your user account"
    if os.name == "posix" and os.geteuid() == 0:
        rep.add(BAD, a, "Running as root", "every mistake or bad file gets full power over the computer",
                "run FLOKTRON as an ordinary user")
        return
    if system == "Darwin":
        code, out = run(["id", "-Gn"])
        if code == 0 and "admin" in out.split():
            rep.add(WARN, a, "Your everyday account is an administrator",
                    "a program you run can change the system after one password prompt",
                    "create a second admin account for installs, then make your own account a Standard one "
                    "(System Settings → Users & Groups). Optional, but the safest way")
        elif code == 0:
            rep.add(OK, a, "Everyday account is not an administrator", "installs need a separate admin password")
    elif system == "Windows":
        try:
            import ctypes
            admin = bool(ctypes.windll.shell32.IsUserAnAdmin())
        except Exception:
            admin = None
        if admin:
            rep.add(WARN, a, "This window runs with administrator rights", "FLOKTRON never needs them",
                    "close it and start FLOKTRON from a normal window")
        elif admin is False:
            rep.add(OK, a, "Not running with administrator rights", "as it should be")


# ---------- macOS ----------

def check_mac(rep):
    a = "3. Computer protection (macOS)"
    code, ver = run(["sw_vers", "-productVersion"])
    chip = "Apple silicon" if platform.machine() == "arm64" else "Intel"
    rep.add(INFO, a, f"macOS {ver.strip() or '?'} on {chip}",
            "security fixes come only with updates — keep the newest version your Mac supports")
    code, out = run(["fdesetup", "status"])
    if "FileVault is On" in out:
        rep.add(OK, a, "Disk encryption (FileVault) is on", "a stolen Mac does not give away your files")
    elif "FileVault is Off" in out:
        rep.add(BAD, a, "Disk encryption (FileVault) is off", "anyone with the Mac in hands can read the disk",
                "System Settings → Privacy & Security → FileVault → Turn On. Keep the recovery key safe, not on this Mac")
    else:
        rep.add(UNK, a, "Disk encryption (FileVault)", "could not read it", "System Settings → Privacy & Security → FileVault")
    fw = "/usr/libexec/ApplicationFirewall/socketfilterfw"
    code, out = run([fw, "--getglobalstate"])
    if re.search(r"enabled|State = [12]", out):
        rep.add(OK, a, "Firewall is on", "incoming connections are controlled")
        code, out = run([fw, "--getstealthmode"])
        if re.search(r"stealth mode (is )?on|enabled", out, re.I):
            rep.add(OK, a, "Stealth mode is on", "the Mac does not answer network scans")
        elif out:
            rep.add(WARN, a, "Stealth mode is off", "the Mac answers anyone who scans the network",
                    "System Settings → Network → Firewall → Options → Enable stealth mode")
    elif re.search(r"disabled|State = 0", out):
        rep.add(BAD, a, "Firewall is off", "every sharing service is open to the network",
                "System Settings → Network → Firewall → On")
    else:
        rep.add(UNK, a, "Firewall", "could not read it", "System Settings → Network → Firewall")
    code, out = run(["csrutil", "status"])
    if "enabled" in out:
        rep.add(OK, a, "System Integrity Protection is on", "system files cannot be changed by programs")
    elif "disabled" in out:
        rep.add(BAD, a, "System Integrity Protection is off", "malware can change system files",
                "restart into Recovery → Terminal → csrutil enable (only if you did not turn it off on purpose)")
    code, out = run(["spctl", "--status"])
    if "enabled" in out:
        rep.add(OK, a, "Gatekeeper is on", "apps from unknown developers are checked before they open")
    elif "disabled" in out:
        rep.add(BAD, a, "Gatekeeper is off", "any downloaded program opens without a check",
                "System Settings → Privacy & Security → Allow applications from: App Store & Known Developers")
    keys = {}
    for k in ("AutomaticCheckEnabled", "CriticalUpdateInstall", "AutomaticallyInstallMacOSUpdates"):
        code, out = run(["defaults", "read", "/Library/Preferences/com.apple.SoftwareUpdate", k])
        keys[k] = out.strip() if code == 0 else None
    if keys["CriticalUpdateInstall"] == "1" and keys["AutomaticCheckEnabled"] != "0":
        rep.add(OK, a, "Security updates install automatically", "fixes arrive without waiting for you")
    elif keys["CriticalUpdateInstall"] == "0" or keys["AutomaticCheckEnabled"] == "0":
        rep.add(WARN, a, "Automatic security updates are off", "known holes stay open until you remember to update",
                "System Settings → General → Software Update → Automatic Updates → turn on all, at least "
                "'Install Security Responses and system files'")
    else:
        rep.add(UNK, a, "Automatic updates", "not set explicitly (macOS default is on)",
                "System Settings → General → Software Update → Automatic Updates")
    code, out = run(["defaults", "read", "/Library/Preferences/com.apple.loginwindow", "autoLoginUser"])
    if code == 0 and out.strip():
        rep.add(BAD, a, "Automatic login is on", "the Mac opens without a password after a restart",
                "System Settings → Users & Groups → Automatically log in as → Off")
    else:
        rep.add(OK, a, "No automatic login", "a password is needed after a restart")
    code, out = run(["defaults", "read", "/Library/Preferences/com.apple.loginwindow", "GuestEnabled"])
    if code == 0 and out.strip() == "1":
        rep.add(WARN, a, "Guest account is on", "anyone can use the Mac without a password",
                "System Settings → Users & Groups → Guest User → Off")
    code, out = run(["sysadminctl", "-screenLock", "status"])
    m = re.search(r"screenLock delay is (\d+|immediate)", out)
    if "immediate" in out or (m and m.group(1).isdigit() and int(m.group(1)) <= 60):
        rep.add(OK, a, "Screen lock asks for the password at once", "a Mac left open locks itself")
    elif "off" in out.lower():
        rep.add(BAD, a, "Screen lock without password", "anyone at your desk gets your accounts",
                "System Settings → Lock Screen → Require password after screen saver begins → Immediately")
    elif m:
        rep.add(WARN, a, f"Password asked {m.group(1)} s after the screen locks", "a short gap someone can use",
                "System Settings → Lock Screen → Require password → Immediately")
    else:
        rep.add(UNK, a, "Screen lock", "could not read it", "System Settings → Lock Screen → Require password → Immediately")
    code, out = run(["tmutil", "destinationinfo"])
    if code == 0 and "Name" in out:
        rep.add(OK, a, "Time Machine has a backup disk", "keep it encrypted and unplugged between backups")
    elif "No destinations" in out:
        rep.add(WARN, a, "No Time Machine backup disk", "a broken disk or ransomware can take everything",
                "System Settings → General → Time Machine → Add Backup Disk → tick Encrypt Backup")
    code, out = run(["netstat", "-an", "-p", "tcp"])
    report_ports(rep, open_ports(out, "bsd") if code == 0 else None,
                 "System Settings → General → Sharing — switch off what you do not use; for a program, set it to listen on 127.0.0.1")
    names = []
    for d in (os.path.expanduser("~/Library/LaunchAgents"), "/Library/LaunchAgents", "/Library/LaunchDaemons"):
        try:
            names += [f.removesuffix(".plist") for f in os.listdir(d) if f.endswith(".plist") and not f.startswith("com.apple.")]
        except OSError:
            pass
    if names:
        shown = ", ".join(sorted(names)[:25]) + (" …" if len(names) > 25 else "")
        rep.add(UNK, a, f"{len(names)} programs start by themselves", f"{shown}. Do you know each of them?",
                "unknown names: search them on the web; remove what you do not use in "
                "System Settings → General → Login Items & Extensions")


# ---------- Windows ----------

def ps(command):
    return run(["powershell", "-NoProfile", "-NonInteractive", "-Command", command], timeout=30)


def check_windows(rep):
    a = "3. Computer protection (Windows)"
    rel, ver = platform.release(), platform.version()
    build = int(ver.split(".")[-1]) if ver.split(".")[-1].isdigit() else 0
    if rel == "10" and build < 22000:
        rep.add(BAD, a, "Windows 10", "Microsoft ended free security updates on 14.10.2025",
                "move to Windows 11, or join Extended Security Updates")
    else:
        rep.add(INFO, a, f"Windows {'11' if build >= 22000 else rel} (build {build or '?'})",
                "keep Windows Update on")
    code, out = run(["netsh", "advfirewall", "show", "allprofiles", "state"])
    states = re.findall(r"State\s+(ON|OFF)", out, re.I)
    if states and all(s.upper() == "ON" for s in states):
        rep.add(OK, a, "Firewall is on for all networks", "incoming connections are controlled")
    elif states:
        rep.add(BAD, a, "Firewall is off for some networks", "the computer is open to those networks",
                "Settings → Privacy & security → Windows Security → Firewall & network protection → turn on all")
    else:
        rep.add(UNK, a, "Firewall", "could not read it", "Windows Security → Firewall & network protection")
    code, out = ps("$s=Get-MpComputerStatus; \"$($s.AntivirusEnabled) $($s.RealTimeProtectionEnabled) $($s.AntivirusSignatureAge)\"")
    p = out.split()
    if code == 0 and len(p) >= 3 and p[0] == "True" and p[1] == "True":
        age = int(p[2]) if p[2].isdigit() else 0
        rep.add(OK if age <= 3 else WARN, a, "Microsoft Defender protects in real time",
                f"virus definitions {age} day(s) old", "Windows Security → Virus & threat protection → Check for updates")
    elif code == 0 and p:
        rep.add(BAD, a, "Real-time virus protection is off", "a bad file runs unnoticed",
                "Windows Security → Virus & threat protection → Manage settings → Real-time protection → On "
                "(if another antivirus is installed, it takes this role — then it is fine)")
    else:
        rep.add(UNK, a, "Virus protection", "could not read it", "Windows Security → Virus & threat protection")
    code, out = ps("(New-Object -ComObject Shell.Application).NameSpace('C:').Self.ExtendedProperty('System.Volume.BitLockerProtection')")
    v = out.strip()
    if v in ("1", "3", "5"):
        rep.add(OK, a, "Disk encryption (BitLocker / Device encryption) is on", "a stolen laptop does not give away your files")
    elif v in ("2", "0", "4", "6"):
        rep.add(BAD, a, "Disk C: is not encrypted", "anyone with the laptop in hands can read the disk",
                "Settings → Privacy & security → Device encryption (Home) or BitLocker (Pro) → On; keep the recovery key off this PC")
    else:
        rep.add(UNK, a, "Disk encryption", "could not read it", "Settings → Privacy & security → Device encryption / BitLocker")
    code, out = run(["reg", "query", r"HKLM\System\CurrentControlSet\Control\Terminal Server", "/v", "fDenyTSConnections"])
    if "0x1" in out:
        rep.add(OK, a, "Remote Desktop is off", "nobody can log in over the network")
    elif "0x0" in out:
        rep.add(WARN, a, "Remote Desktop is on", "a password guess from the network opens the PC",
                "Settings → System → Remote Desktop → Off (if you do not use it)")
    code, out = run(["reg", "query", r"HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System", "/v", "EnableLUA"])
    if "0x0" in out:
        rep.add(BAD, a, "User Account Control is off", "programs get admin rights without asking",
                "Control Panel → User Accounts → Change User Account Control settings → default level")
    elif "0x1" in out:
        rep.add(OK, a, "User Account Control is on", "admin rights need your confirmation")
    code, out = run(["netstat", "-an"])
    report_ports(rep, open_ports(out, "win") if code == 0 else None,
                 "Settings → Network & internet → Advanced sharing settings → File and printer sharing Off on public networks; "
                 "uninstall or stop programs you do not use")


# ---------- Linux ----------

def check_linux(rep):
    a = "3. Computer protection (Linux)"
    rep.add(INFO, a, f"Linux {platform.release()}", "keep the system updated")
    code, out = run(["ufw", "status"])
    if "Status: active" in out:
        rep.add(OK, a, "Firewall (ufw) is on", "incoming connections are controlled")
    elif "inactive" in out:
        rep.add(BAD, a, "Firewall (ufw) is off", "every service is open to the network", "sudo ufw enable (after allowing ssh if you use it)")
    else:
        code, out = run(["firewall-cmd", "--state"])
        if "running" in out:
            rep.add(OK, a, "Firewall (firewalld) is on", "incoming connections are controlled")
        else:
            rep.add(UNK, a, "Firewall", "could not read it without admin rights", "sudo ufw status  or  sudo nft list ruleset")
    code, out = run(["lsblk", "-o", "TYPE"])
    if code == 0:
        if "crypt" in out:
            rep.add(OK, a, "Disk encryption (LUKS) found", "a stolen disk does not give away your files")
        else:
            rep.add(WARN, a, "No disk encryption found", "on a laptop anyone with the disk reads it",
                    "on a laptop: encrypt at the next reinstall (LUKS); on a server in a data centre: ask the provider")
    if os.path.exists("/etc/apt/apt.conf.d/20auto-upgrades"):
        txt = open("/etc/apt/apt.conf.d/20auto-upgrades", encoding="utf-8", errors="ignore").read()
        if 'Unattended-Upgrade "1"' in txt:
            rep.add(OK, a, "Security updates install automatically", "unattended-upgrades is on")
        else:
            rep.add(WARN, a, "Automatic security updates are off", "known holes stay open",
                    "sudo dpkg-reconfigure -plow unattended-upgrades")
    code, out = run(["ss", "-tlnH"])
    report_ports(rep, open_ports(out, "ss") if code == 0 else None,
                 "stop services you do not use (sudo systemctl disable --now <name>); bind programs to 127.0.0.1; "
                 "for SSH use keys only (PasswordAuthentication no)")


def report_ports(rep, ports, fix):
    a = "4. Open doors to the network"
    if ports is None:
        rep.add(UNK, a, "Open ports", "could not read the list", fix)
        return
    risky = sorted(p for p in ports if p in SHARING_PORTS)
    other = sorted(p for p in ports if p not in SHARING_PORTS)
    for p in risky:
        rep.add(WARN, a, f"Port {p} is open to the network — {SHARING_PORTS[p]}",
                "fine only if you use it on purpose; otherwise it is an open door", fix)
    if other:
        rep.add(UNK, a, "Other programs listen to the network on ports " + ", ".join(map(str, other[:20])),
                "usually apps (sync, chat, development tools); check you know them",
                "macOS: sudo lsof -nP -iTCP -sTCP:LISTEN · Windows: netstat -abno (as admin) · Linux: sudo ss -tlnp — "
                "you see which program owns each port")
    if not risky and not other:
        rep.add(OK, a, "No open ports to the network", "nothing on this computer waits for connections from outside")


MANUAL = """
## Things no script can see — go through them once (5–10 minutes)

5. Accounts and backups
[ ] Two-step login (2FA) on: the FLOKTRON mailbox, your main mailbox, your cloud (Apple ID / Google / Microsoft),
    GitHub if you use it, Telegram (Settings → Privacy → Two-Step Verification), your domain and website hosting, the bank.
[ ] FLOKTRON uses its own mailbox with an app password — not your main mailbox and not your main password.
[ ] Cloud end-to-end encryption where it exists: iCloud → Advanced Data Protection; Proton is encrypted by default;
    Google Drive / OneDrive — protect the account with 2FA and a security key or passkey.
[ ] Backups 3-2-1: the cloud with version history + ONE copy that is not always connected
    (an encrypted external disk you plug in once a week). Ransomware cannot reach an unplugged disk.
[ ] "Find My" / "Find my device" is on — a lost laptop can be locked or wiped.

6. The network around you
[ ] Router: own admin password (not the one on the sticker), latest firmware, WPA2/WPA3, WPS off, UPnP off,
    no port forwarding you did not set up yourself. Guests and smart devices — on the guest network.
[ ] Public Wi-Fi: no admin pages, banks or FLOKTRON setup there without your own hotspot or a VPN you trust.
[ ] Optional: a DNS that blocks known malware sites — Quad9 9.9.9.9 or Cloudflare 1.1.1.2 (router or network settings).

7. Apps and the AI assistant
[ ] Privacy settings → Full Disk Access, Accessibility, Screen Recording, Input Monitoring, Automation:
    only apps you use and trust. (FLOKTRON on a Mac may need Full Disk Access for Python — that also means any
    Python script you run gets it; run only scripts you know.)
[ ] Browser extensions: remove the ones you do not use; each one sees the pages you are signed in to.
[ ] Your AI assistant has access to ONE folder (the FLOKTRON folder), not the whole disk.
[ ] Never paste passwords, tokens or calendar links into a chat; if it happened — change them (Telegram: /revoke).
[ ] Open unknown files and scripts only in a test account or a virtual machine (macOS: UTM; Windows: Windows Sandbox
    in Pro editions; Linux: a VM) — never on the computer that holds your bases.

8. Extra free tools (optional)
macOS — Objective-See (open source): LuLu (asks before a program connects out), KnockKnock (what starts by itself),
BlockBlock (warns when something new adds itself to start-up), OverSight (camera / microphone).
Windows — Microsoft Defender is built in and enough for most; Windows Sandbox for unknown files.
Linux — ClamAV for scanning files you receive; fail2ban on a server with SSH.
A paid antivirus can be added on top at any time — this check is the base it stands on.
"""


def main():
    manual = "--manual" in sys.argv
    system = platform.system()
    rep = Report()
    check_floktron(rep)
    check_account(rep, system)
    if system == "Darwin":
        check_mac(rep)
    elif system == "Windows":
        check_windows(rep)
    elif system == "Linux":
        check_linux(rep)
    else:
        rep.add(UNK, "3. Computer protection", f"System {system}", "no automatic checks for it", "see docs/SECURITY_CHECKUP.md")
    now = datetime.datetime.now()
    title = f"FLOKTRON security check · {platform.node() or 'this computer'} · {now:%d.%m.%Y %H:%M}"
    text = rep.text(title)
    text += ("\nThis check only read settings. It changed nothing and sent nothing anywhere.\n"
             "Fix ❌ first, then ⚠️. Run it again afterwards: python3 scripts/security_check.py\n")
    text += MANUAL if manual else "\nThe checklist of what no script can see: python3 scripts/security_check.py --manual\n"
    print(text)
    os.makedirs(DATA, exist_ok=True)
    out = os.path.join(DATA, f"security_check_{now:%Y%m%d_%H%M}.txt")
    with open(out, "w", encoding="utf-8") as f:
        f.write(text)
    if os.name == "posix":
        os.chmod(out, 0o600)
    print(f"Saved: {os.path.relpath(out, ROOT)} (only on this computer)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
