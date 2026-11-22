# Shell Coordinator: cli.sh

`src/sh/cli.sh` is the central command-line argument parser, help system, and validation coordinator.

---

## 1. Responsibilities

* **Help Generation:** Outputs top-level resource lists and per-resource action manuals according to the `cli-ux-messaging` standard.
* **Option Normalization:** Parses standard POSIX/GNU flags (`-h`, `-V`, `-v`, `-q`, `-n`, `-y`, `-r`, `-t`, `-F`, `--json`, `--plain`, `--icons`, `--no-icons`).
* **Entity & Subcommand Routing:** Resolves command entities (`library`, `artist`, `album`, `track`, `playlist`, `covers`, `lyrics`, `tags`, `config`) and enforces required subactions and targets.
* **Dual-Audience Error Handling:** Reports CLI syntax errors on `stderr` with exit code `2` and copy-pasteable examples.

---

## 2. Help Output Engine

### Top-Level Help (`show_help`)
Invoked when running `syncdap -h` or `syncdap --help`. Lists only top-level resources and global options without cluttering the screen with nested subactions:
```bash
./syncdap --help
```

### Resource-Specific Help (`show_resource_help`)
Invoked when running `syncdap <resource> --help` or `syncdap help <resource>`. Displays only the actions and options relevant to that resource:
```bash
./syncdap library --help
./syncdap artist --help
./syncdap album --help
./syncdap track --help
```

---

## 3. Positionals & Routing Logic

The parser extracts arguments into state variables:
* `SUBCOMMAND`: The primary resource or verb (`library`, `artist`, `album`, `track`, `covers`, etc.).
* `SUBACTION`: The specific operation under that resource (e.g., `status`, `dedup`, `audit`, `optimize`, `fix`).
* `COMMAND_ARGS`: Any remaining positional targets or parameters (such as artist name, file path, or format string).

If a Spotify URL is passed directly as the first argument without a subcommand (e.g., `./syncdap https://open.spotify.com/album/...`), the parser automatically routes the call to `download`.
