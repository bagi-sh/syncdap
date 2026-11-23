"""Rockbox .scrobbler.log parser.

Parses Audioscrobbler Portable Player Log format (v1.0 / v1.1) written by Rockbox.

Firmware Quirk Mitigations:
- Several Rockbox builds (e.g., modern DAP ports) have a known bug where they write
  local wall-clock time into the timestamps while hardcoding `#TZ/UTC` into the log header.
  To prevent scrobbles being shifted by hours, syncdap overwrites the header `#TZ` by
  defaulting to the host computer's local UTC offset (or explicit --timezone / --tz-offset).
- Repeated listens of the same song (identical artist and track) are strictly preserved
  and submitted, as users frequently repeat tracks during listening sessions.
- Resilient UTF-8 decoding (errors='replace') ensures malformed characters written by
  legacy DAP ID3 readers never crash synchronization.
"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import time
import re

FOURTEEN_DAYS_SECONDS = 14 * 86400
UUID_PATTERN = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")


@dataclass
class ScrobbleEntry:
    artist: str
    album: str
    track: str
    track_number: int | None
    duration: int
    rating: str
    timestamp: int
    raw_timestamp: int
    mbid: str
    status: str  # 'valid', 'skipped_rating', 'expired', 'duplicate', 'invalid'
    line_num: int
    status_reason: str = ""


@dataclass
class LogParseResult:
    log_version: str
    timezone_directive: str
    client_directive: str
    effective_tz_offset_hours: float
    effective_tz_source: str
    total_lines: int
    entries: list[ScrobbleEntry]

    @property
    def valid_entries(self) -> list[ScrobbleEntry]:
        return [e for e in self.entries if e.status == "valid"]

    @property
    def skipped_rating(self) -> list[ScrobbleEntry]:
        return [e for e in self.entries if e.status == "skipped_rating"]

    @property
    def expired(self) -> list[ScrobbleEntry]:
        return [e for e in self.entries if e.status == "expired"]

    @property
    def duplicates(self) -> list[ScrobbleEntry]:
        return [e for e in self.entries if e.status == "duplicate"]

    @property
    def invalid(self) -> list[ScrobbleEntry]:
        return [e for e in self.entries if e.status == "invalid"]


def get_system_utc_offset_hours() -> float:
    """Infer current host system UTC offset in hours."""
    offset = datetime.now().astimezone().utcoffset()
    return offset.total_seconds() / 3600.0 if offset else 0.0


def parse_scrobbler_log(
    log_path: Path,
    tz_offset_hours: float | None = None,
    last_scrobbled_timestamp: int = 0,
    current_time: int | None = None,
) -> LogParseResult:
    """Parse a .scrobbler.log file and partition entries according to Last.fm rules."""
    now = current_time if current_time is not None else int(time.time())
    min_valid_timestamp = now - FOURTEEN_DAYS_SECONDS

    log_version = "1.1"
    timezone_directive = "UTC"
    client_directive = ""
    entries: list[ScrobbleEntry] = []

    if not log_path.is_file():
        system_offset = get_system_utc_offset_hours()
        return LogParseResult(
            log_version=log_version,
            timezone_directive=timezone_directive,
            client_directive=client_directive,
            effective_tz_offset_hours=system_offset,
            effective_tz_source="host system",
            total_lines=0,
            entries=[],
        )

    # Errors='replace' ensures non-UTF-8 bytes written by DAP don't crash parser
    content = log_path.read_text(encoding="utf-8", errors="replace")
    lines = content.splitlines()

    # Step 1: Detect directives
    for line in lines:
        stripped = line.strip()
        if not stripped.startswith("#"):
            continue
        if stripped.startswith("#AUDIOSCROBBLER/"):
            log_version = stripped.replace("#AUDIOSCROBBLER/", "").strip()
        elif stripped.startswith("#TZ/"):
            timezone_directive = stripped.replace("#TZ/", "").strip().upper()
        elif stripped.startswith("#CLIENT/"):
            client_directive = stripped.replace("#CLIENT/", "").strip()

    # Calculate effective UTC offset:
    # Always prioritize explicit tz_offset_hours (from --tz-offset/--timezone or config).
    # If not provided, default to host computer's UTC offset, overwriting #TZ from log file.
    if tz_offset_hours is not None:
        effective_tz_hours = float(tz_offset_hours)
        effective_offset_sec = int(effective_tz_hours * 3600)
        effective_tz_source = f"explicit offset ({effective_tz_hours:+g}h, overwriting log #TZ/{timezone_directive})"
    else:
        effective_tz_hours = get_system_utc_offset_hours()
        effective_offset_sec = int(effective_tz_hours * 3600)
        effective_tz_source = f"host system ({effective_tz_hours:+g}h, overwriting log #TZ/{timezone_directive})"

    # Step 2: Parse data rows
    for line_num, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        parts = line.split("\t")
        if len(parts) < 7:
            # Malformed row
            entries.append(
                ScrobbleEntry(
                    artist="",
                    album="",
                    track="",
                    track_number=None,
                    duration=0,
                    rating="",
                    timestamp=0,
                    raw_timestamp=0,
                    mbid="",
                    status="invalid",
                    line_num=line_num,
                    status_reason="Fewer than 7 tab-separated fields",
                )
            )
            continue

        artist = parts[0].strip()
        album = parts[1].strip() if len(parts) > 1 else ""
        track = parts[2].strip() if len(parts) > 2 else ""

        # Validate mandatory metadata
        if not artist or artist.lower() == "<untagged>":
            entries.append(
                ScrobbleEntry(
                    artist=artist,
                    album=album,
                    track=track,
                    track_number=None,
                    duration=0,
                    rating="",
                    timestamp=0,
                    raw_timestamp=0,
                    mbid="",
                    status="invalid",
                    line_num=line_num,
                    status_reason="Empty or untagged artist",
                )
            )
            continue

        if not track:
            entries.append(
                ScrobbleEntry(
                    artist=artist,
                    album=album,
                    track=track,
                    track_number=None,
                    duration=0,
                    rating="",
                    timestamp=0,
                    raw_timestamp=0,
                    mbid="",
                    status="invalid",
                    line_num=line_num,
                    status_reason="Empty track title",
                )
            )
            continue

        # Track number
        track_num: int | None = None
        raw_tn = parts[3].strip() if len(parts) > 3 else ""
        if raw_tn.isdigit():
            val = int(raw_tn)
            if val > 0:
                track_num = val

        # Duration in seconds
        duration = 0
        raw_dur = parts[4].strip() if len(parts) > 4 else ""
        if raw_dur.isdigit():
            duration = int(raw_dur)

        # Rating (L = Listened, S = Skipped)
        rating = parts[5].strip().upper() if len(parts) > 5 else "L"

        # Timestamp
        raw_ts = 0
        raw_ts_str = parts[6].strip() if len(parts) > 6 else ""
        try:
            raw_ts = int(raw_ts_str)
        except ValueError:
            entries.append(
                ScrobbleEntry(
                    artist=artist,
                    album=album,
                    track=track,
                    track_number=track_num,
                    duration=duration,
                    rating=rating,
                    timestamp=0,
                    raw_timestamp=0,
                    mbid="",
                    status="invalid",
                    line_num=line_num,
                    status_reason=f"Non-numeric timestamp: {raw_ts_str}",
                )
            )
            continue

        # Adjust timestamp according to timezone directive
        adjusted_ts = raw_ts - effective_offset_sec if effective_offset_sec != 0 else raw_ts

        # MusicBrainz ID
        mbid = ""
        if len(parts) > 7:
            candidate_mbid = parts[7].strip()
            if UUID_PATTERN.match(candidate_mbid):
                mbid = candidate_mbid

        # Determine status
        status = "valid"
        reason = ""

        if rating != "L":
            status = "skipped_rating"
            reason = f"Rating is '{rating}' (track was skipped)"
        elif adjusted_ts <= last_scrobbled_timestamp:
            status = "duplicate"
            reason = f"Timestamp {adjusted_ts} <= watermark {last_scrobbled_timestamp}"
        elif adjusted_ts < min_valid_timestamp:
            status = "expired"
            reason = f"Timestamp is older than 14 days ({adjusted_ts} < {min_valid_timestamp})"

        entries.append(
            ScrobbleEntry(
                artist=artist,
                album=album,
                track=track,
                track_number=track_num,
                duration=duration,
                rating=rating,
                timestamp=adjusted_ts,
                raw_timestamp=raw_ts,
                mbid=mbid,
                status=status,
                line_num=line_num,
                status_reason=reason,
            )
        )

    return LogParseResult(
        log_version=log_version,
        timezone_directive=timezone_directive,
        client_directive=client_directive,
        effective_tz_offset_hours=effective_tz_hours,
        effective_tz_source=effective_tz_source,
        total_lines=len(lines),
        entries=entries,
    )
