# Shell Coordinator: downloader.sh

`src/sh/downloader.sh` manages external media ingestion from Spotify URLs via spotDL.

---

## 1. Responsibilities

* **spotDL Invocation:** Executes spotDL with customized format, thread, and output path parameters.
* **Stream Fallback:** If spotDL fails or tracks encounter rate limits, it logs failed URLs into `erros.spotdl`.
* **Subsequent Rescue:** Feeds failed URLs into the yt-dlp fallback engine (`src/modules/fallback.py`).
* **Progress Logging:** Routes interactive progress bars and download indicators strictly to `stderr`, keeping `stdout` clean.
