# Chapter 8.3.9: Resource Command Reference: `syncdap scrobbler`

> **The Syncdap Book Navigation:** [← Previous Section](08-tags.md) • [Table of Contents](../../index.md) • [Next Section →](10-config.md)

---

## Pedagogical Context & Prerequisites
This section documents Last.fm scrobbler commands: sync, auth, status, and logout.

---

The `scrobbler` resource parses Rockbox `.scrobbler.log` playback logs and submits scrobbles to Last.fm.

---

## 1. Syntax

```text
syncdap scrobbler [action] [target] [options]
```

Where `[action]` defaults to `sync` when omitted.

---

## 2. Actions

| Action | Target | Description | Example Invocation |
|---|---|---|---|
| **`sync`** *(default)* | `[LOG_PATH]` | Parse `.scrobbler.log`, submit batches of 50 to Last.fm, archive log, and rotate DAP file. | `syncdap scrobbler sync -r /mnt/dap` |
| **`auth`** | None | Launch desktop browser authentication flow and terminal polling. | `syncdap scrobbler auth` |
| **`status`** | `[LOG_PATH]` | Display authenticated user, watermark timestamp, and pending scrobbles. | `syncdap scrobbler status -r /mnt/dap` |
| **`logout`** | None | Revoke local Last.fm session credentials. | `syncdap scrobbler logout` |

---

## 3. Resource Options

* **`--timezone <HOURS>` / `--tz-offset <HOURS>`**: Set an explicit UTC offset (e.g. `-3` or `0`). By default, `syncdap` uses the host computer's local UTC offset, automatically overwriting whatever `#TZ` directive (such as `#TZ/UTC`) Rockbox wrote in `.scrobbler.log`.
* **`--keep-log`**: Retain `.scrobbler.log` on the DAP after upload instead of removing it.
* **`-y, --yes`**: Skip confirmation prompts (e.g., when overwriting an existing authenticated session).

---

## 4. Invocations

### Authenticate Account
```bash
syncdap scrobbler auth
```
Opens browser to authorize Syncdap and polls Last.fm until granted, saving credentials to `~/.config/syncdap/lastfm.conf` with `0600` permissions.

### Check Status & Pending Scrobbles
```bash
syncdap scrobbler status -r /mnt/dap
syncdap scrobbler status -r /mnt/dap --json
```

### Dry-Run Sync
```bash
syncdap scrobbler sync -r /mnt/dap --dry-run
```

### Sync & Rotate Log
```bash
syncdap scrobbler -r /mnt/dap
```
Submits valid tracks, archives `.scrobbler.log` to `~/.config/syncdap/logs/`, updates `~/.config/syncdap/scrobbler.state`, and removes `.scrobbler.log` from the player.

---

## 5. Firmware Compatibility & Log Quirks

These design decisions specifically mitigate bugs and discrepancies observed in various Rockbox community builds and hardware ports:
* **Timezone (#TZ) Overwriting**: Certain Rockbox builds rewrite the log header to `#TZ/UTC` even when the player RTC is configured to a local timezone (e.g. UTC-3). `syncdap` defaults to the host workstation's timezone to ensure timestamps are accurately offset to UTC.
* **Repeated Plays**: All playback instances of a song with `rating == "L"` are uploaded; `syncdap` never discards duplicate tracks within a log.
* **Encoding Fault Tolerance**: Malformed characters written to `.scrobbler.log` by legacy tag readers are automatically sanitized without aborting the synchronization pipeline.

---

## Summary & Next Steps
To conclude our resource reference, we examine persistent configuration actions with `syncdap config`.

---

> **The Syncdap Book Navigation:** [← Previous Section](08-tags.md) • [Table of Contents](../../index.md) • [Next Section →](10-config.md)
