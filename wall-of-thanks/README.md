# Wall of Thanks — API (Thanksgiving 2026)

The thanks-flavoured twin of the Halloween wall: same storage model, same guards,
different words. One PHP file, one JSON file, no database.

```
wall-of-thanks/
├── api.php        <- upload this
└── README.md      <- this file (don't upload, or do — harmless)
```

`data/` is created automatically on the first request, with its own `.htaccess`
guard and an empty `index.html`, so the JSON is never reachable from the web.

## Deploy

1. **Live already at:**

   ```
   public_html/vishal/wall-of-thanks/thanks-giving/api.php
   ```

   which is `https://digitalfueled.in/vishal/wall-of-thanks/thanks-giving/api.php` — the site JS in this repo points at exactly that URL, and it
   currently answers `submissionsOpen: true` with `total: 0`, i.e. **open**.

   > ℹ️ `/vishal/wall-of-thanks/api.php` (one level up) is the **Halloween** wall.
   > Different folder on purpose — same filename, different campaign.

2. **Check it answers:**

   ```bash
   curl -s https://digitalfueled.in/vishal/wall-of-thanks/thanks-giving/api.php
   # {"ok":true,"total":0,"submissionsOpen":true,"closedMessage":"…","messages":[]}
   ```

   The first GET creates `data/`. If the server user cannot create it, make
   `data/` yourself and `chmod 755` it (the endpoint returns a readable hint in
   that case instead of a stack trace).

3. **Nothing else to configure.** The page's Wall of Thanks section
   (`#sec7` → `#w7form` / `#w7wall`) already talks to that URL — it ships in the
   site's scripts embed.

## API contract

| | |
| --- | --- |
| `GET` | `{ ok, total, submissionsOpen, closedMessage, messages:[{id,name,message,timestamp}] }` — newest first, max 300 |
| `POST` | body `{ name, message, website, elapsedMs }` sent as `Content-Type: text/plain;charset=utf-8` (keeps it a "simple" request, no CORS preflight) → `201 { ok:true, message:{…} }` |
| errors | `400` empty / too fast · `403` wall closed · `409` duplicate · `413` too large · `429` throttled · `500` storage not writable |

Every error carries `{ ok:false, error:"human readable text" }` and the page prints
that text under the form verbatim, so tone is controlled from here.

## Guards (all on by default)

- **Honeypot** — the page injects an invisible `website` field; if it is filled the
  API pretends success and stores nothing.
- **Too fast** — `elapsedMs < 2500` is rejected (bot typing speed).
- **Duplicate** — same name + note within 10 minutes → `409`. Checked before the
  rate limiter, so a duplicate never costs a throttle slot.
- **Rate limit** — 15 s between posts and 10 per hour per IP hash, stored in
  `data/throttle.json`.
- **IPs are never stored** — only a salted SHA-256 prefix.
- **Writes are atomic** — temp file + `rename()` inside one `flock()`; a crash can
  never leave half a JSON file. Corrupt files are backed up, not overwritten.
- **Output** — only `id`, `name`, `message`, `timestamp` leave the server, and the
  page renders them with `textContent` only (no HTML injection path).

## Editing

Everything worth touching is at the top of `api.php`:

```php
const SUBMISSIONS_OPEN = true;        // false = seal the wall (form hides, notes stay)
const CLOSED_MESSAGE   = '…';         // wording once sealed
const MAX_NAME_LENGTH  = 40;          // matches the Webflow maxlength
const MAX_MESSAGE_LENGTH = 140;       // matches the Webflow maxlength
const MAX_MESSAGES_TO_RETURN = 300;   // cards per page load
const MAX_MESSAGES_TO_KEEP   = 5000;  // oldest dropped beyond this
const IP_HASH_SALT     = 'wall-of-thanks-v1'; // change this once, keep it
```

Re-upload the file after any change — no build step, no cache to clear.

## Seeding before launch

Add a few real notes so the wall is never empty (the page shows sample cards
until the API returns something):

```bash
curl -s -X POST https://digitalfueled.in/vishal/wall-of-thanks/thanks-giving/api.php \
  -H 'Content-Type: text/plain;charset=utf-8' \
  -d '{"name":"Team Supervity","message":"Every one of you made this year lighter.","elapsedMs":6000}'
```

`elapsedMs` must be ≥ 2500 or the bot guard rejects it. Read the wall back with a
plain `GET`.

## Clearing test entries before launch

`data/messages.json` is the whole wall. To wipe test notes: open it in cPanel →
File Manager (or FTP), replace the contents with `[]`, save. The next `GET` reads
it back as an empty wall — no upload, no re-deploy. (Deleting the file also works;
it is recreated empty on the first request.)

## Closing night

Set `SUBMISSIONS_OPEN = false`, re-upload. The form disappears, every note stays,
and anyone POSTing gets the `CLOSED_MESSAGE` wording.

## Backup

`data/messages.json` is the whole wall — a plain, pretty-printed JSON array. Copy
it down whenever (it is also the answer to "did we lose anything?").
