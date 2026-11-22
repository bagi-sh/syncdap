# Contributing to syncdap

Thank you for your interest in contributing to `syncdap`! This document provides clear guidelines for reporting bugs, suggesting new features, and submitting code changes.

---

## 1. Project Philosophy & Scope

`syncdap` is a dedicated synchronization and maintenance tool designed primarily for **Rockbox firmware** and audiophile Digital Audio Players (DAPs).

* **Rockbox-First Architecture:** All default behavior strictly adheres to Rockbox indexing, database, and hardware requirements (such as `ALBUMARTIST` tag unification, standalone `cover.jpg` extraction, and FAT32 path length limits).
* **Broad Hardware Support:** Enhancements for non-Rockbox DAPs or generic portable players are welcome as long as they **never break or degrade Rockbox compatibility**.
* **Out of Scope:** Graphic user interfaces (GUIs), streaming music playback engines, or player-specific proprietary software bridges.

---

## 2. Communication & Community

* **GitHub Only:** All official project discussions, questions, issue tracking, and code reviews take place exclusively on **GitHub Issues** and **GitHub Discussions**. Third-party chat platforms (Discord, Telegram, Matrix) are not actively monitored by maintainers.
* **Security Disclosures:** For sensitive vulnerability reports, please email the maintainer directly at **bagi.aq@proton.me** instead of opening a public issue.
* **Code of Conduct:** Please review and follow our [Code of Conduct](CODE_OF_CONDUCT.md) in all community interactions.

---

## 3. Local Development Setup

### System Prerequisites
To run and develop `syncdap`, your system needs:
* **Linux environment**
* **Bash 4.0+**
* **Python 3.10+**
* System utilities: `ffmpeg`, `yt-dlp`, `curl`, `grep`
* **`uv`** (recommended) or `pip` for Python package management

### Getting Started
1. Fork and clone the repository:
   ```bash
   git clone https://github.com/your-username/syncdap.git
   cd syncdap
   ```
2. Verify system dependencies:
   ```bash
   ./syncdap status
   ```
3. Test dry-run execution without modifying your files:
   ```bash
   ./syncdap library status -n
   ```

---

## 4. Code Standards & Guidelines

### Python Standards
* **Formatting:** Follow PEP 8 guidelines strictly.
* **Docstrings:** Use PEP 257 multi-line docstrings (`"""..."""`) for all modules, classes, and public functions. **Never use stacked `#` banner headers.**
* **Iconography:** Never use graphical emojis (such as ❌, ⚠️, 🚀) in CLI logs. Always import monochromatic symbols from `share.icons.ICONS`:
  ```python
  from share.icons import ICONS
  print(f"{ICONS.ok} Task completed.")
  ```
* **Type Annotations:** Provide Python type hints on all new public function signatures.

### Shell Script Standards
* **Interpreter & Flags:** All scripts in `src/sh/` must begin with `#!/usr/bin/env bash` and execute with `set -uo pipefail`.
* **Portability:** Use standard POSIX/GNU commands. All shell scripts must pass `bash -n` syntax checks and follow `shellcheck` recommendations.
* **Signal Handling:** Any script creating temporary directories must register a trap cleanup:
  ```bash
  trap cleanup EXIT INT TERM
  ```

### CLI UX & Messaging Standard
All commands and subcommands must follow the `cli-ux-messaging` design pattern:
* **Asymmetric Verbosity:**
  * **Success:** Emit a single, clean confirmation line on `stdout`.
  * **Failure:** Route errors to `stderr` using the **Dual-Audience Architecture** (a clear headline for users, followed by indented `Cause:`, `Target:`, and a copy-pasteable `Fix:` for developers).
* **Standard Exit Codes:**
  * `0`: Success (including `-h`, `-V`, and clean dry runs).
  * `1`: General runtime, I/O, or API failure.
  * `2`: Invalid CLI syntax, unrecognized option, or missing argument.
* **Stream Discipline:** Never print progress indicators or error logs to `stdout`—reserve `stdout` strictly for command data and machine-readable `--json` or `--plain` output.

---

## 5. Pre-Submission Checklist

Before opening a pull request, run this verification suite locally:

```bash
# 1. Validate shell syntax across all scripts
bash -n syncdap src/sh/*.sh

# 2. Compile check all Python source files
python3 -m compileall -q src

# 3. Test CLI argument parsing and help output
./syncdap -h
./syncdap library --help
./syncdap artist --help
./syncdap album --help
./syncdap track --help

# 4. Verify machine-readable output integrity
./syncdap status --json | jq .
```

---

## 6. Git & Pull Request Workflow

1. **Branching:** Create a descriptive branch off `main`:
   ```bash
   git checkout -b feat/artist-filter
   ```
2. **Commit Messages:** Follow [Conventional Commits](https://www.conventionalcommits.org/):
   * `feat(scope): add new feature`
   * `fix(scope): resolve bug`
   * `refactor(scope): internal code cleanup`
   * `docs(scope): documentation updates`
3. **Pull Request Submission:**
   * Provide a concise description of the change and the rationale.
   * Include the exact commands used to verify the change.
   * Ensure your PR leaves the repository clean without uncommitted test files.

---

## 7. Review & Maintainer Expectations

`syncdap` is currently maintained by a solo developer. Pull requests and issues will be reviewed as time permits. Constructive discussions, clear test cases, and focused pull requests make reviews faster and easier to merge.
