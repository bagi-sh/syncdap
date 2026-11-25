# Chapter 5.6: Transcoding & Quality Upgrade Pipeline (`patch/`)

> **The Syncdap Book Navigation:** [← Previous Section](05-album-expander.md) • [Table of Contents](../index.md) • [Next Section →](07-dedup.md)

---

## Pedagogical Context & Prerequisites
In this section, we inspect the `src/patch/` package, which orchestrates multithreaded ffmpeg transcoding (`flac`, `mp3`, `opus`) while preserving metadata and relinking playlist references.

---

`src/patch/` orchestrates format transcoding and audio quality upgrades, upgrading lower-bitrate tracks to lossless or modern codecs while strictly preserving tags, artwork, and playlist integrity.

---

## 1. Subsystem Architecture

The patch subsystem comprises four specialized components:
- `cli.py`: Parses target format (`flac`, `mp3`, `m4a`, `opus`), filter terms, and thread parameters.
- `worker.py`: Manages parallel transcoding jobs via `ThreadPoolExecutor` and `ffmpeg`.
- `metadata.py`: Extracts existing audio tags and cover art before transcoding and reapplies them to the newly generated file.
- `playlist.py`: Inspects playlists referencing old files and rewrites path extensions to point to the patched file.

---

## 2. Tag & Artwork Preservation Protocol

Transcoding audio with naive ffmpeg calls strips custom ID3 frames, ReplayGain values, and embedded artwork. `metadata.py` prevents metadata loss:

```python
# From src/patch/metadata.py
def transfer_tags_to_file(dest_file: str, meta: dict, cover_path: str | None = None) -> bool:
    img_data = meta.get('cover_data')
    mime_type = meta.get('cover_mime', 'image/jpeg')
    
    # Write preserved metadata and artwork into the transcoded file
    return write_audio_metadata(
        dest_file,
        title=meta.get('title'),
        artist=meta.get('artist'),
        album=meta.get('album'),
        album_artist=meta.get('album_artist'),
        track_num=meta.get('track_num'),
        total_tracks=meta.get('total_tracks'),
        year=meta.get('year'),
        genre=meta.get('genre'),
        cover_data=img_data,
        cover_mime=mime_type,
    )
```

---

## 3. Atomic Replacement & Cleanup

1. Transcoded audio is written to `$TEMP_DIR/<uuid>.<ext>`.
2. Audio duration and integrity are verified with `ffprobe` / `mutagen`.
3. If `keep_old=False`, the old file is purged, and the new file is moved into the album directory.
4. Companion `.lrc` sidecars are renamed to match the new file stem.

---

## 4. CLI Invocations

```bash
# Transcode entire library to FLAC using 4 threads
syncdap library patch flac -r /mnt/dap/Music -t 4

# Transcode a specific album to MP3 (320kbps)
syncdap album patch mp3 "/mnt/dap/Music/Artist/Album"

# Transcode tracks belonging to a specific playlist
syncdap patch flac -P "Favorites"
```

---

## Summary & Next Steps
When libraries contain duplicate songs across multiple bitrates, `dedup.py` eliminates redundancy while prioritizing lossless quality. Next: `dedup.py`.

---

> **The Syncdap Book Navigation:** [← Previous Section](05-album-expander.md) • [Table of Contents](../index.md) • [Next Section →](07-dedup.md)
