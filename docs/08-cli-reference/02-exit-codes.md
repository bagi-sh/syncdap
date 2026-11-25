# Chapter 8.2: Exit Codes & Dual-Audience Diagnostic Formatting

> **The Syncdap Book Navigation:** [← Previous Section](01-grammar.md) • [Table of Contents](../index.md) • [Next Section →](resources/01-library.md)

---

## Pedagogical Context & Prerequisites
In this section, we document `syncdap`'s standard exit codes (`0`, `1`, `2`) and how diagnostic errors are presented simultaneously for human terminal users and Unix pipeline automations.

---

`syncdap` adheres strictly to standard POSIX exit codes to guarantee predictable automation and shell pipeline integration.

---

## 1. Exit Codes Matrix

| Exit Code | Meaning | Example Triggers |
|---|---|---|
| **`0`** | **Success** | Successful operation completion, `--help`, `--version`, and clean `--dry-run` executions. |
| **`1`** | **Runtime / I/O Failure** | Network timeout during API queries, target audio file not found on disk, or unrecoverable stream error. |
| **`2`** | **CLI Syntax / Invalid Usage** | Unrecognized command, unknown option flag, missing required argument, or invalid action name. |

---

## 2. Dual-Audience Error Schema

Whenever execution fails with a non-zero exit code (`1` or `2`), the error is routed to `stderr` using the **Dual-Audience Architecture**:

```text
[ERR] Plain English headline describing what failed
  Cause:  Technical explanation of the deviation or trigger
  Target: The exact command, file path, or API query that failed
  Fix:    Clear, copy-pasteable remediation command for the developer
```

### Example
```text
$ syncdap artist status
[ERR] Missing artist target
  Cause:  Artist-scoped commands require an artist name or directory
  Target: syncdap artist status <artist>
  Fix:    Example: syncdap artist status 'Queen'
```

---

## Summary & Next Steps
Next, we begin the exhaustive per-resource command reference with `syncdap library`.

---

> **The Syncdap Book Navigation:** [← Previous Section](01-grammar.md) • [Table of Contents](../index.md) • [Next Section →](resources/01-library.md)
