# Test FLOKTRON with Gmail (step by step)

Goal: run the morning message and reply collection with an ordinary Gmail box — no Proton, no Bridge.
You need: one Gmail address for FLOKTRON (e.g. a new `yourcompany.floktron@gmail.com`) and one or two other
addresses that play the departments.

## 1. Turn on 2-Step Verification (needed for an app password)
1. Open myaccount.google.com → **Security**.
2. **2-Step Verification** → turn it on (phone confirmation).

## 2. Create an app password
1. myaccount.google.com → search box at the top → type **App passwords**.
2. App name: `FLOKTRON` → **Create**.
3. Google shows 16 letters (4 groups of 4). Copy them — this is the password FLOKTRON uses.
   It is not your normal Gmail password and can be deleted any time.

## 3. Fill in the settings
Copy `config/config.gmail-example.yaml` to `config/config.yaml` and replace the example addresses.

## 4. Give FLOKTRON the password (never write it into a file)
macOS / Linux terminal:
```
export FLOKTRON_MAIL_PASSWORD="abcd efgh ijkl mnop"
```
Windows PowerShell:
```
$env:FLOKTRON_MAIL_PASSWORD="abcd efgh ijkl mnop"
```

## 5. Run
```
pip install openpyxl pyyaml
python3 scripts/base_create.py
python3 scripts/send_morning.py --test your.phone.mail@gmail.com   # one test message
python3 scripts/send_morning.py                                     # real messages to the rays
# press buttons on the phone, then:
python3 scripts/collect_replies.py
```

## If something does not work
| Message | Meaning |
|---|---|
| `Username and Password not accepted` | app password wrong, or 2-Step Verification is off |
| `No mail password` | step 4 was not done in this terminal window |
| replies not found | Gmail put them in Spam — FLOKTRON also looks in Spam; check the subject was not changed |
