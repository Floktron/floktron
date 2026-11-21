# Security checkup — the last step of every setup

FLOKTRON keeps your data with you: in your mailbox, your cloud, your computer. The authors never see it.
That also means **you are the one who protects it** — not luck, not "it has never happened to me".
So every setup ends the same way: your assistant checks how well your computer is protected, explains
each point in plain words and shows you where to click. When the checkup is done, the system is set up
and protected with what your computer already has. Your own antivirus or other paid tools can be added on top later.

## Where your data lives and what protects it

| Your data | Where it is | What protects it | Checked by |
|---|---|---|---|
| Settings (`config/config.yaml`) | FLOKTRON folder on your computer | no passwords inside; readable only by you | `security_check.py` §1 |
| Mail password, bot token, calendar link | system keychain (Mac) or environment variable | never in a file, never in a chat | §1 + you |
| Bases, letters, replies (`data/`) | FLOKTRON folder (often in your cloud) | file permissions, disk encryption, version history | §1, §3 |
| Your mailbox | your mail provider | 2-step login, a separate mailbox with an app password | manual list §5 |
| The whole computer | your desk / bag | disk encryption, firewall, updates, screen lock | §3, §4 |
| Backups | cloud + one copy that is not always connected | encryption, 3-2-1 rule | §3 + manual list §5 |

## How the checkup runs

**Mode A — the assistant works on your computer:** it runs
```
python3 scripts/security_check.py --manual
```
and reads the report with you, point by point, in your language.

**Mode B — chat only:** open a terminal in the FLOKTRON folder (Mac: Terminal · Windows: PowerShell · Linux: terminal),
type the same line, press Enter, then copy the text into the chat — or send a screenshot.
The report contains no passwords; it shows your computer's name and its settings only.

Mac or Linux: `python3 scripts/security_check.py --manual` · Windows: `py scripts\security_check.py --manual`

The check works on **macOS** (Apple silicon and Intel), **Windows 10/11** and **Linux**, and picks the checks for the
system it runs on. It **only reads** settings — the same as opening the settings window. It changes nothing,
asks for no administrator password and sends nothing anywhere. The report is saved only on your computer:
`data/security_check_<date>.txt`.

## What the marks mean

| Mark | Meaning | What to do |
|---|---|---|
| ❌ | an open door — fix first | the report says where to click; usually 1–2 minutes |
| ⚠️ | worth fixing | fix today or this week |
| ❔ | the script could not see it | check by hand — the report says where to look |
| ℹ️ | for your information | read once |
| ✅ | fine | nothing to do |

**You make every change yourself.** The assistant shows where to click and explains why — it never changes
security settings, never asks for your administrator password and never switches protection off.
After the fixes run the check again: the goal is no ❌, and every ⚠️ either fixed or kept on purpose.

## What is checked

1. **FLOKTRON folder and your data** — no passwords in files, permissions, `.gitignore`, cloud version history.
2. **Your user account** — not root / not running with admin rights; on a Mac a tip about a Standard account.
3. **Computer protection** —
   macOS: FileVault, firewall + stealth mode, System Integrity Protection, Gatekeeper, automatic security updates,
   automatic login, guest account, screen lock, Time Machine, programs that start by themselves.
   Windows: version (Windows 10 no longer gets free security updates since 14.10.2025), firewall, Microsoft Defender,
   disk encryption (BitLocker / Device encryption), Remote Desktop, User Account Control.
   Linux: firewall (ufw / firewalld), disk encryption (LUKS), automatic security updates.
4. **Open doors to the network** — ports listening for connections from outside: remote login, file and screen
   sharing, AirPlay, Remote Desktop, databases, local AI servers. Listening only on 127.0.0.1 is fine.
5–8. **The manual list** (`--manual`): 2-step login everywhere, a separate FLOKTRON mailbox, cloud end-to-end
   encryption, 3-2-1 backups with one unplugged copy, Find My, the router, public Wi-Fi, app permissions,
   browser extensions, the assistant's folder access, unknown files only in a sandbox, free extra tools.

## Which program owns an open port
The report lists ports; to see the program behind each one:

| System | Command (admin password asked by the system, typed by you) |
|---|---|
| macOS | `sudo lsof -nP -iTCP -sTCP:LISTEN` |
| Windows | `netstat -abno` in PowerShell "Run as administrator" |
| Linux | `sudo ss -tlnp` |

Do not know a program? Search its name on the web before you remove it.

## When to run it again
Once a month, after a big system update, after installing new software that talks to the network,
and whenever something feels wrong. The monthly reminder can be one task in your own rays.

## Free extra tools (optional)
- **macOS** — Objective-See, open source: LuLu (asks before a program connects out), KnockKnock (what starts by itself),
  BlockBlock (warns about new start-up items), OverSight (camera and microphone).
- **Windows** — Microsoft Defender is built in; Windows Sandbox (Pro editions) for unknown files.
- **Linux** — ClamAV for received files; fail2ban on a server with SSH.
- **Any computer** — a DNS that blocks known malware sites (Quad9 9.9.9.9, Cloudflare 1.1.1.2); a virtual machine
  (UTM on Mac) for files you do not trust.

Install these only from the developers' own sites or the system's app store.

## What the checkup cannot do
It sees settings, not intentions: it cannot tell whether a program you installed yourself is honest, whether
your password was already stolen, or whether a person with access to the computer changes things by hand.
It is the base — an antivirus, a password manager or a company IT policy can stand on top of it.
