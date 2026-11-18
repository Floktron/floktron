# Switch off and remove FLOKTRON

Everything FLOKTRON installs stays on your own computer and in your own mailbox. Nothing is installed anywhere else.
An AI assistant can do these steps when you say: *"Switch off and remove FLOKTRON"*.

## 1. Switch off automatic runs
| System | How |
|---|---|
| Mac | `scripts/install` → double-click **install_mac.command** → type `off`. This removes the `floktron.*` entries from `~/Library/LaunchAgents` |
| Windows | `powershell -File scripts\install\install_windows.ps1 off` — removes the tasks in Task Scheduler → folder `FLOKTRON` |
| Linux | `sh scripts/install/install_linux.sh off` — removes the FLOKTRON lines from `crontab` |

Check: Mac `launchctl list | grep floktron` · Windows Task Scheduler → `FLOKTRON` folder empty · Linux `crontab -l` — nothing found means it is off.

## 2. Remove the mail access
- Gmail: myaccount.google.com → **App passwords** → delete the password made for FLOKTRON.
- Mac Keychain (if used): Keychain Access → search the service name from `config.yaml → mail.keychain_service` → delete.
- Environment variable: close the terminal window, or remove the `export FLOKTRON_MAIL_PASSWORD=…` line if you added it to a profile file.
- If you made a separate mailbox only for FLOKTRON, you can delete it.

## 3. Remove the files
- Keep `data/` and the storage folder if you want the history (bases, reports). Otherwise delete them.
- Delete the FLOKTRON folder. Python and the two packages (`openpyxl`, `PyYAML`) can stay — other programs may use them.
  To remove them: `pip uninstall openpyxl PyYAML`.

## 4. Tell the people
If departments received morning messages, send them one line that the test is over, so nobody waits for tasks.
