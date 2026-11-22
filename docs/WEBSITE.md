# Website — your own site, safe by default (Cloudflare recommended, any hosting works)

Optional. Do this **before the Marketing ray**: posts, social profiles, QR codes and e-mail signatures need one
address to point to. Your AI assistant leads you step by step; **you** click in the dashboards, type passwords
and approve every DNS change. The assistant never asks for passwords, tokens or API keys in the chat.

**Live example:** [koagu.com](https://koagu.com) runs on exactly this setup since 15.11.2026 — plain HTML/CSS/JS,
code in a private GitHub repository, hosting on Cloudflare Pages, six languages, forms, no cookie banner.
Steps 3–5 and 7–10 are what runs there, written so anyone can repeat it; step 6 is the recommended baseline on top.

## Why Cloudflare
| What | You get | You do not have to |
|---|---|---|
| **Certificates (HTTPS)** | issued and renewed automatically for your domain and `www` | buy, install or renew a certificate |
| **Protection** | DDoS protection and a global network in front of the site | run or patch a server |
| **Hosting** | static pages served from Cloudflare Pages; every push to GitHub goes live in about a minute | upload files by FTP |
| **Undo** | every change is a git commit; one click (or one revert) brings back the previous version | keep backups by hand |
| **More sites** | one account holds many sites — your shop on a subdomain, a partner's landing page, a product page | buy hosting for each |
| **Price** | the free plan is enough for a small business site with forms | — check current limits on cloudflare.com/plans |

## First question: where is your domain, and do you already have hosting?
Cloudflare is our recommendation, not a condition. The site files are plain HTML/CSS/JS and run on any hosting.
The assistant asks this first and follows one of four paths:

| Path | When | What you do |
|---|---|---|
| **A. All on Cloudflare** (recommended) | new site, or you are free to choose | domain stays at your registrar, its nameservers point to Cloudflare, the site runs on Cloudflare Pages — steps 0–12 below as written |
| **B. Keep DNS at your registrar** | you cannot or do not want to move nameservers (Namecheap, GoDaddy, Hostinger, IONOS, a local registrar…) | site on Cloudflare Pages, `www` points there with a `CNAME`; the bare domain forwards to `www` at the registrar — see *Path B* below |
| **C. Your favourite hosting** | you already pay for hosting or like your provider (Namecheap, GoDaddy, Hostinger, IONOS, Netlify, Vercel, GitHub Pages…) | same files, same checks; only the upload, HTTPS switch, headers and forms change — see *Path C* below |
| **D. Cloudflare in front of your hosting** | site stays where it is, you want the free protection on top | nameservers to Cloudflare (step 2), your site's `A`/`CNAME` record stays and is *proxied* (orange cloud), SSL mode *Full (strict)* |

Step 0 (keep your mail records), step 3 (the files), step 8 (never break a printed link), steps 10–12 (analytics,
legal pages, final check) are the same on every path.

## What you need
| Thing | Notes |
|---|---|
| A domain | from any registrar (where you bought it). You need its login — to change nameservers or DNS records |
| A Cloudflare account | sign up with a **company mailbox**, not a personal one; turn on 2-factor login at once |
| A GitHub account / organization | free; 2-factor login on; the site repository can be private |
| Time | about 1–2 hours of your clicks (estimate), plus waiting for the nameserver change (minutes to a day) |

## Who does what
| Your AI assistant | You |
|---|---|
| writes the site files, `_headers`, `_redirects`, `robots.txt`, `sitemap.xml`, checks them | create the accounts, log in, click *Save* |
| lists the DNS records you have today and compares them after the move | change the nameservers at your registrar |
| tells you which button to press and what you should see | type every password and secret — only into Cloudflare / GitHub |
| checks the live site at the end (step 12) | decide what goes public |

## Step 0 — before you touch anything: list your DNS records
Your domain probably already carries **e-mail**. Losing these records means losing mail.
1. At your current DNS host (usually the registrar) open the DNS zone and **export it or take screenshots**.
2. Mark the records that must survive unchanged: `MX`, `TXT` with `v=spf1`, DKIM (`…._domainkey`), `_dmarc`,
   and every verification `TXT` (Google, Microsoft, your mail provider).
3. Rule for the whole setup: **mail and verification records are never changed or deleted** without the owner's
   explicit OK. The site only adds records for the site.

## Step 1 — accounts
1. Cloudflare: sign up → 2-factor login (app, not SMS) → save recovery codes offline.
2. GitHub: create an organization for the company (keeps the site separate from personal accounts) → 2-factor login.
3. Create a **private** repository, e.g. `company-site`.

## Step 2 — put the domain on Cloudflare
1. Cloudflare dashboard → *Add a domain* → type `example.com` → choose the **Free** plan.
2. Cloudflare imports the DNS records it finds. **Compare with your list from step 0** — add anything missing
   (mail records most of all). Mail records stay *DNS only* (grey cloud).
3. Cloudflare shows two nameservers. At your registrar replace the old nameservers with these two.
4. Wait until the domain shows **Active** (e-mail from Cloudflare). Then send a test e-mail to and from your domain.

*Cannot move nameservers? Use Path B or C above.*

## Step 3 — the site files
No builder, no framework: plain files that open in any browser. The assistant creates this layout:

```
company-site/
├── index.html            # or one folder per language: en/ lv/ ru/ …
├── assets/css/ assets/js/ assets/img/   # images as WebP, file names in Latin letters
├── 404.html
├── robots.txt
├── sitemap.xml
├── _headers              # security headers, cache, noindex for the test address
├── _redirects            # old addresses and printed QR codes → new pages
└── functions/            # only if you have forms (step 8)
```

Add a `README.md` that says what lives where — the next person (or AI assistant) will thank you.

## Step 4 — connect GitHub to Cloudflare Pages
1. Cloudflare → *Workers & Pages* → *Create* → **Pages** → *Connect to Git* → allow access **only to this one repository**.
2. Settings: production branch `main` · Framework preset **None** · Build command **empty** · Build output directory `/`.
3. *Save and Deploy*. The site appears at `company-site.pages.dev` — this is the **test address**.

*Cloudflare is moving Pages and Workers closer together; button names may differ slightly. The settings stay the same.*

## Step 5 — your own domain and certificates
1. Pages project → *Custom domains* → add `example.com`, then add `www.example.com`.
2. Cloudflare creates the records itself and issues the certificates. Wait until both show **Active** — usually minutes.
3. Choose **one main address** (koagu.com uses the bare domain `https://koagu.com`) and use it everywhere:
   canonical tags, sitemap, social profiles.

## Step 6 — HTTPS and security settings (domain → SSL/TLS, Security)
Recommended baseline — open each setting and check it once.

| Setting | Value | Why |
|---|---|---|
| SSL/TLS encryption mode | **Full (strict)** | never fall back to unencrypted traffic |
| Always Use HTTPS | **On** | `http://` becomes `https://` |
| Automatic HTTPS Rewrites | On | fixes old `http://` links inside pages |
| Minimum TLS version | **1.2** | drops outdated clients |
| DNSSEC | **On** → copy the DS record to your registrar | protects against forged DNS answers |
| Bot Fight Mode | optional | blocks simple bots; test your forms after switching it on |

## Step 7 — `_headers`: security and cache (copy, change the project name)
```
# Test addresses *.pages.dev are hidden from search engines
https://company-site.pages.dev/*
  X-Robots-Tag: noindex, nofollow
https://:version.company-site.pages.dev/*
  X-Robots-Tag: noindex, nofollow

/*
  X-Content-Type-Options: nosniff
  X-Frame-Options: SAMEORIGIN
  Referrer-Policy: strict-origin-when-cross-origin
  Permissions-Policy: camera=(), microphone=(), geolocation=()
  Strict-Transport-Security: max-age=31536000; includeSubDomains

/assets/*
  Cache-Control: public, max-age=604800
```
Changing CSS or JS? Add a version to the link (`site.css?v=2`) and raise it each time — visitors get the new file at once.

## Step 8 — `_redirects`: never break a printed link
```
/              /en/        302
/old-page      /en/new/    301
```
- Every address that was ever printed (QR codes on packages, flyers, business cards) gets a line and **is never removed**.
- **Lesson from koagu.com:** the old site sent `example.com → www`, the new one wanted `www → example.com`.
  Browsers remember a 301 for a long time, so old visitors got a redirect loop. Fix: keep the `www` rule **switched
  off** for a few months, let both addresses show the same site, and let the canonical tag point to the main one.
  Switch the rule on only later.

## Step 9 — forms without a server (optional)
Use Cloudflare **Pages Functions** (`functions/api/<name>.js`) and a **D1** database. Settings koagu.com uses:
| Point | How |
|---|---|
| Where data lives | D1 database created with **EU jurisdiction** |
| Spam | hidden honeypot field + minimum time to fill the form + limit of a few requests per hour per visitor |
| Visitor IP | only a **hash** is stored, never the IP itself |
| Retention | records older than 2 years are deleted automatically (state the same in your privacy policy) |
| Reading the requests | a private page behind password login, with CSV export for Excel |
| Login and passwords | Cloudflare → Pages project → *Settings* → *Variables and secrets*, type **Secret**. Never in code, never in the repository |
Your AI assistant writes the function; you create the database, bind it to the project (name `DB`) and enter the secrets.

## Step 10 — analytics and search engines
1. **Cloudflare Web Analytics** (Pages project → *Metrics*, or *Analytics & Logs* → *Web Analytics*): counts visits
   without cookies. With no other cookies on the site you need no cookie banner — check this against the rules of your country.
2. **Google Search Console** → *Domain* property → it gives a `TXT` record → add it in Cloudflare DNS → *Verify*
   → submit `https://example.com/sitemap.xml`. Bing Webmaster Tools can import from Search Console.
3. Each page: title, description, one H1, `canonical`, `hreflang` for every language version, a line in `sitemap.xml`.

## Step 11 — privacy and legal pages
- Privacy policy: what the forms collect, why, how long (step 9), processors (Cloudflare, your mail provider), where to complain.
- Terms of use; company details (name, registration number, address, e-mail) in the footer.
- German-speaking visitors: an *Impressum*; English: a *Legal notice*.
- Only true statements: no invented reviews, clients or logos.

## Step 12 — check before you announce (the assistant does it, you look)
| Check | Expected |
|---|---|
| `https://example.com` | padlock, page opens |
| `http://example.com` | goes to `https://` |
| `https://www.example.com` | same site (or a redirect to the main address) |
| `company-site.pages.dev` | opens, response header `X-Robots-Tag: noindex` |
| Response headers on the main address | the lines from step 7 are there |
| A printed QR / old address | lands on the right new page |
| Forms | a test request arrives; a 6th quick request is refused |
| **E-mail** | a test message to and from your domain still arrives |
| `/sitemap.xml`, `/robots.txt`, a wrong address | open; the wrong address shows your 404 page |

## Path B — DNS stays at your registrar, site on Cloudflare Pages
1. Do steps 1, 3 and 4 (accounts, files, Pages). Skip step 2.
2. Pages project → *Custom domains* → add `www.example.com`. Cloudflare shows a target like `company-site.pages.dev`.
3. At your registrar (DNS / Advanced DNS) add: `CNAME` · host `www` · value `company-site.pages.dev`. Do not touch mail records.
4. Bare domain `example.com`: Cloudflare Pages can serve it only when the domain is on Cloudflare nameservers.
   At the registrar use **URL forwarding / redirect** `example.com → https://www.example.com` (301). If your registrar
   offers `ALIAS`/`ANAME`/`CNAME flattening`, ask the assistant whether it fits.
5. The certificate for `www` is still issued and renewed by Cloudflare. Your main address is `https://www.example.com`.
6. Step 6 (HTTPS rules, DNSSEC) is done at the registrar instead — most offer *DNSSEC* and *HTTPS forwarding* switches.

## Path C — your favourite hosting
The same files work anywhere. What changes:

| Step | On Cloudflare Pages | On classic hosting (cPanel / hPanel / Plesk) | On Netlify / Vercel / GitHub Pages |
|---|---|---|---|
| Upload | push to GitHub | *Git Version Control* in the panel, or File Manager / SFTP into `public_html` | connect the GitHub repository |
| HTTPS | automatic | switch on the free certificate (*AutoSSL*, *Let's Encrypt*, *SSL/TLS*) and *Force HTTPS* | automatic; tick *Enforce HTTPS* |
| Headers (step 7) | `_headers` | `.htaccess` — snippet below | Netlify: `_headers` works as is; Vercel: `vercel.json` → `headers`; GitHub Pages: headers cannot be set |
| Redirects (step 8) | `_redirects` | `.htaccess` — `Redirect 301 /old-page /en/new/` | Netlify: `_redirects` works as is; Vercel: `vercel.json` → `redirects` |
| Forms (step 9) | Pages Functions + D1 | the host's PHP mail form or a form service — choose one that stores data in the EU, and name it in the privacy policy | Netlify Forms / Vercel functions |
| Analytics (step 10) | Web Analytics | Cloudflare Web Analytics works on any host: add its one-line script to every page (no cookies) | same |
| Test address hidden | `_headers` noindex | usually no test address; if the panel gives one, protect it with a password | Netlify / Vercel previews: add `X-Robots-Tag: noindex` for preview domains |

`.htaccess` for Apache hosting (most cPanel plans) — the assistant fills in your redirects:
```
RewriteEngine On
RewriteCond %{HTTPS} off
RewriteRule ^ https://%{HTTP_HOST}%{REQUEST_URI} [L,R=301]

<IfModule mod_headers.c>
  Header always set X-Content-Type-Options "nosniff"
  Header always set X-Frame-Options "SAMEORIGIN"
  Header always set Referrer-Policy "strict-origin-when-cross-origin"
  Header always set Permissions-Policy "camera=(), microphone=(), geolocation=()"
  Header always set Strict-Transport-Security "max-age=31536000; includeSubDomains"
</IfModule>

Redirect 301 /old-page /en/new/
ErrorDocument 404 /404.html
```
Hosting on nginx (no `.htaccess`)? Ask the provider's support to add the same headers and redirects — send them this list.
Later you can still move to Path A or add Path D: the files do not change.

## Day-to-day
- **Change** = edit a file → commit → push → live in about a minute (Path C classic hosting: upload, or pull in the panel).
- **Undo** = revert the commit, or Pages → *Deployments* → older version → *Rollback*.
- **Try first** = push to another branch → Cloudflare gives it its own preview address (hidden from search by step 7).
- **More sites** = one Pages project and one repository per site. Partners get their own project; give people access
  through Cloudflare *Members* with the smallest role needed — never share your own login.

## What FLOKTRON does here — and never does
- The assistant writes and checks files and tells you what to click. **No API token is needed** for this setup.
- It never logs in for you, never stores Cloudflare or GitHub passwords, never changes mail records.
- Want automation later (e.g. a script that publishes a page)? Create a Cloudflare API token limited to that one
  project and keep it in the system keychain — same rule as every FLOKTRON secret ([SECURITY_CHECKUP](SECURITY_CHECKUP.md)).

## If something does not work
| Symptom | Likely cause | Fix |
|---|---|---|
| Mail stopped after the move | `MX`/SPF/DKIM record not imported | add it from your step 0 list, *DNS only* |
| "Too many redirects" | two opposite redirects (`www ↔ bare`), or SSL mode *Flexible* | keep one direction only; SSL mode *Full (strict)* |
| Custom domain stuck on *Pending* | nameservers not changed yet, or an old `A`/`CNAME` for the same name | wait for *Active*; delete the old record for that name |
| Old CSS after a change | browser cache | raise `?v=N` on every page |
| Form answers "error" | database not bound as `DB`, or secrets missing | Pages → *Settings* → *Bindings* / *Variables and secrets* |
| Test address shows up in Google | `_headers` noindex block missing | add it (step 7) |

## Next: the Marketing ray
Now posts, profiles and QR codes have one address. Link posts to the site with UTM labels
(`?utm_source=linkedin&utm_campaign=…`) and see the visits in Web Analytics. Set up the content plan next (setup wizard step 9).
