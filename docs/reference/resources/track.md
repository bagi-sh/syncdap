# Resource Reference: track

The `track` resource scopes operations to an individual audio file.

---

## 1. Syntax

```text
syncdap track <action> <audio_file> [options]
```

Where `<audio_file>` is a valid path to an existing audio file (`.flac`, `.mp3`, `.m4a`, `.opus`, `.ogg`, `.wav`).

---

## 2. Actions

### `status`
Inspects audio metrics (format, bitrate, sample rate, channels, duration) and metadata tag fields for a single track.
```bash
syncdap track status ./Bohemian_Rhapsody.flac
syncdap track status ./Bohemian_Rhapsody.flac --json
```

### `audit`
Checks if the track's duration deviates from the official duration recorded on iTunes/MusicBrainz.
```bash
syncdap track audit ./LongTrack.flac
```

### `expand`
Splits a single-file album rip into individual tracks.
```bash
syncdap track expand ./FullAlbumRip.mp3
```

### `patch`
Transcodes or upgrades the single track to the target audio format.
```bash
# Transcode track to FLAC
syncdap track patch flac ./Track.wav

# Transcode track to MP3
syncdap track patch mp3 ./Track.flac
```

### `romaji`
Transliterates Japanese Kanji/Kana metadata tags in the track and its associated `.lrc` file to Hepburn Romaji.
```bash
syncdap track romaji ./Zenzenzense.flac
```
