# Automatic runs — switch FLOKTRON on

After this FLOKTRON works by itself: morning messages, collecting replies every 30 minutes, the reply
deadline, evening reminder, news slice, weekly summary. Times are in `config/config.yaml → schedule`.
Weekends and public holidays (LV, LT, EE built in, plus `company.holidays`) are skipped.

The computer must stay on. For "no computer at all" see the end of this page.

## Mac
1. Open the FLOKTRON folder → `scripts/install` → double-click **install_mac.command**.
2. Type `on` and press Enter.
3. First time only: System Settings → Privacy & Security → **Full Disk Access** → add **Python**
   (and Terminal) if the FLOKTRON folder is in iCloud or Documents. Without it macOS blocks the runs silently.
4. Switch off: double-click again and type `off`.

## Windows
1. Install Python from python.org (tick **Add python.exe to PATH**).
2. `scripts/install/install_windows.ps1` → right-click → **Run with PowerShell**.
3. Switch off: `powershell -File scripts\install\install_windows.ps1 off`.

## Linux / small server
```
sh scripts/install/install_linux.sh on     # off — to switch off
```

## Check that it works
```
python3 scripts/run.py status      # last lines of data/run.log
```
Every run writes `=== <date> <job>` and `--- exit 0` (0 = OK). Two runs never write at the same time;
if the base is open in Excel, the run waits up to 10 minutes.

## Without a computer that is always on
| Option | For whom | Cost (estimate) |
|---|---|---|
| Small cloud server (VPS) with Linux, `install_linux.sh on` | technical users | ~5–15 €/month |
| Old laptop / mini-PC at the office, always on | anyone | electricity |
| Hosted FLOKTRON run by a support person for several clients | non-technical clients | to be decided |
