# Chapter 8.3.10: Resource Command Reference: `syncdap config`

> **The Syncdap Book Navigation:** [← Previous Section](09-scrobbler.md) • [Table of Contents](../../index.md) • [Next Section →](../../index.md)

---

## Pedagogical Context & Prerequisites
This final reference section documents persistent configuration management: get, set, list, and reset.

---

The `config` resource manages persistent settings stored in `~/.config/syncdap/config`.

---

## 1. Syntax

```text
syncdap config [action]
syncdap config <key>=<value>
syncdap config set <key> <value>
syncdap config get <key>
```

---

## 2. Invocations

### Inspecting Settings
```bash
# List all active configuration settings
syncdap config list
```

### Initializing Configuration with Complete Defaults
```bash
# Generate default config file if none exists
syncdap config init

# Overwrite existing config file with all defaults
syncdap config init --force
```

### Modifying Settings
```bash
# Direct key=value syntax
syncdap config format=flac
syncdap config threads=8
syncdap config cover_name=cover.jpg
syncdap config cover_resolution=600
syncdap config audit_threshold=600
syncdap config scrobbler_batch_size=50

# Alternative set syntax
syncdap config set icons true
syncdap config set spotdl_throttled_rate 150K
```

### Retrieving a Setting
```bash
syncdap config get root_dir
syncdap config get format
```

---

## 3. Configuration Keys Matrix

| Category | Key | Valid Options | Default | Description |
|---|---|---|---|---|
| **Core** | `format` | `mp3`, `flac`, `m4a`, `opus`, `ogg`, `wav` | `mp3` | Target audio format for media ingestion and patching |
| **Core** | `threads` | Integer (`1`–`32`) | `4` | Concurrency worker threads |
| **Core** | `root_dir` | Directory path | `.` | Default music root or DAP mount |
| **Core** | `icons` | `auto`, `true`, `false` | `auto` | Terminal symbol rendering tier |
| **Core** | `assume_yes` | `true`, `false` | `false` | Skip interactive confirmation prompts |
| **Covers** | `cover_name` | Filename | `cover.jpg` | Canonical external artwork filename |
| **Covers** | `cover_resolution` | Integer | `600` | Target download artwork resolution in px |
| **Covers** | `cover_filenames` | Comma-separated | `cover.jpg,cover.jpeg,folder.jpg...` | Recognized cover filenames for traversal |
| **Lyrics** | `synced_only` | `true`, `false` | `false` | Enforce timestamped lyrics |
| **Tags** | `id3_version` | `3`, `4` | `3` | Target ID3v2 version (3 = ID3v2.3 UTF-16) |
| **Tags** | `clean_ghost_files`| `true`, `false` | `true` | Purge OS ghost files (`._*`, `Thumbs.db`) |
| **Tags** | `ignored_dirs` | Comma-separated | `lost.dir,.trash,.rockbox...` | System folders excluded from traversal |
| **Audit** | `audit_threshold` | Seconds | `600` | Duration threshold to audit long tracks |
| **Audit** | `audit_ratio` | Float | `1.5` | Ratio to classify full-album continuous rips |
| **Scrobbler**| `scrobbler_keep_log`| `true`, `false` | `false` | Retain log on DAP after sync |
| **Scrobbler**| `scrobbler_tz_offset`| Integer / Float | *(auto)* | Explicit UTC timezone offset override |
| **Scrobbler**| `scrobbler_batch_size`| Integer (`1`–`50`) | `50` | Maximum tracks per Last.fm batch |
| **Network** | `spotdl_providers` | Space-separated | `youtube youtube-music soundcloud bandcamp` | Priority audio providers for spotDL |
| **Network** | `spotdl_max_retries`| Integer | `1` | Max download retries in spotDL |
| **Network** | `spotdl_throttled_rate`| Rate string | `100K` | Rate throttling argument for yt-dlp |
---

## 4. Strict Precedence Hierarchy

Configuration and preference values follow a strict 3-tier precedence rule:
1. **Tier 1: CLI Flags** (highest priority) — Overrides everything when specified on the command line.
2. **Tier 2: Local Configuration** — Loaded from active config file (`~/.config/syncdap/config` or `-c/--config`). Overrides installation defaults.
3. **Tier 3: Installation Defaults** (lowest priority) — Built-in hardcoded fallback values.

Keys support both hyphenated (`root-dir`, `synced-only`) and underscored (`root_dir`, `synced_only`) formatting interchangeably. Custom config files passed via `-c/--config` take precedence over default user configuration files, while CLI flags retain supreme priority over custom configuration files.

---

## Summary & Next Steps
You have completed the full reference manual of **The Syncdap Book**. Return to the master Table of Contents to revisit any chapter.

---

> **The Syncdap Book Navigation:** [← Previous Section](09-scrobbler.md) • [Table of Contents](../../index.md) • [Next Section →](../../index.md)
