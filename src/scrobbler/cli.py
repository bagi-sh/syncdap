"""CLI entrypoint for syncdap scrobbler.

Handles actions:
  - sync   : parse .scrobbler.log, filter, submit batches of 50 to Last.fm, archive, and rotate log
  - auth   : authenticate desktop session with Last.fm
  - status : display account info, session health, watermark, and pending log tracks
  - logout : revoke local credentials
"""

import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import sys
import time

lib_dir = Path(__file__).resolve().parent.parent
if str(lib_dir) not in sys.path:
    sys.path.insert(0, str(lib_dir))

from scrobbler.auth import authenticate, logout
from scrobbler.client import LastFmError, scrobble_tracks
from scrobbler.parser import LogParseResult, parse_scrobbler_log
from scrobbler.state import (
    archive_log,
    load_session,
    load_state,
    save_state,
)
from share.config import (
    get_config_value,
    get_lastfm_session_path,
    get_scrobbler_state_path,
)
from share.icons import ICONS, format_error_dual


def resolve_log_path(target: str | None, root_dir: str | None) -> Path:
    """Resolve target .scrobbler.log from positional arg or root_dir."""
    if target:
        p = Path(target).expanduser().resolve()
        if p.is_dir():
            return p / ".scrobbler.log"
        return p

    base = Path(root_dir).expanduser().resolve() if root_dir else Path.cwd()
    return base / ".scrobbler.log"


def format_duration(seconds: int) -> str:
    """Format duration in mm:ss format."""
    if seconds <= 0:
        return "—"
    m, s = divmod(seconds, 60)
    return f"{m}:{s:02d}"


def handle_auth(args: argparse.Namespace) -> int:
    session = authenticate(force=args.yes, quiet=args.quiet)
    return 0 if session else 1


def handle_logout(args: argparse.Namespace) -> int:
    logout(quiet=args.quiet)
    return 0


def resolve_tz_offset(cli_arg: float | None) -> float | None:
    """Resolve timezone offset enforcing strict precedence:
    1: CLI flag (--tz-offset)
    2: Environment override (SYNCDAP_CLI_TZ_OFFSET / SYNCDAP_TZ_OFFSET)
    3: Local configuration file (scrobbler_tz_offset)
    4: Log header (#TZ) / None
    """
    if cli_arg is not None:
        return cli_arg
    env_tz = os.environ.get("SYNCDAP_CLI_TZ_OFFSET") or os.environ.get("SYNCDAP_TZ_OFFSET")
    if env_tz:
        try:
            return float(env_tz)
        except ValueError:
            pass
    cfg_tz = (
        get_config_value("scrobbler_tz_offset")
        or get_config_value("scrobbler-tz-offset")
        or get_config_value("scrobbler.tz_offset")
        or get_config_value("scrobbler.timezone")
    )
    if cfg_tz:
        try:
            return float(cfg_tz)
        except ValueError:
            pass
    return None


def resolve_batch_size(cli_arg: int | None) -> int:
    """Resolve submission batch size enforcing strict precedence:
    1: CLI flag (--batch-size)
    2: Environment override (SYNCDAP_CLI_SCROBBLER_BATCH_SIZE)
    3: Local configuration file (scrobbler_batch_size)
    4: Installation default (SCROBBLER_BATCH_SIZE = 50)
    """
    if cli_arg is not None:
        return max(1, min(50, cli_arg))
    env_bs = os.environ.get("SYNCDAP_CLI_SCROBBLER_BATCH_SIZE") or os.environ.get("SYNCDAP_SCROBBLER_BATCH_SIZE")
    if env_bs:
        try:
            return max(1, min(50, int(env_bs)))
        except ValueError:
            pass
    cfg_bs = get_config_value("scrobbler_batch_size") or get_config_value("scrobbler-batch-size")
    if cfg_bs:
        try:
            return max(1, min(50, int(cfg_bs)))
        except ValueError:
            pass
    return SCROBBLER_BATCH_SIZE


def handle_status(args: argparse.Namespace) -> int:
    session = load_session()
    state = load_state()
    log_file = resolve_log_path(args.target, args.root_dir)

    log_present = log_file.is_file()
    parse_res: LogParseResult | None = None
    if log_present:
        tz_offset = resolve_tz_offset(args.tz_offset)
        parse_res = parse_scrobbler_log(
            log_file,
            tz_offset_hours=tz_offset,
            last_scrobbled_timestamp=state.get("last_scrobbled_timestamp", 0),
        )

    if args.json:
        data = {
            "authenticated": session is not None,
            "username": session["username"] if session else None,
            "session_file": str(get_lastfm_session_path()),
            "last_scrobbled_timestamp": state.get("last_scrobbled_timestamp", 0),
            "total_scrobbled": state.get("total_scrobbled", 0),
            "log_path": str(log_file) if log_present else None,
            "effective_tz_offset_hours": parse_res.effective_tz_offset_hours if parse_res else None,
            "effective_tz_source": parse_res.effective_tz_source if parse_res else None,
            "total_in_log": len(parse_res.entries) if parse_res else 0,
            "pending_scrobbles": len(parse_res.valid_entries) if parse_res else 0,
            "skipped_rating": len(parse_res.skipped_rating) if parse_res else 0,
            "expired": len(parse_res.expired) if parse_res else 0,
            "duplicates": len(parse_res.duplicates) if parse_res else 0,
        }
        print(json.dumps(data, indent=2))
        return 0

    if args.plain:
        user_str = session["username"] if session else "UNAUTHENTICATED"
        pending_str = str(len(parse_res.valid_entries)) if parse_res else "0"
        total_str = str(state.get("total_scrobbled", 0))
        print(f"{user_str}\t{total_str}\t{pending_str}\t{log_file if log_present else ''}")
        return 0

    # Human table / dashboard output
    print(f"{ICONS.music} Last.fm Scrobbler Status\n")
    if session:
        print(f"  Account:       {session['username']} (Authenticated)")
        auth_time = session.get("authenticated_at")
        if auth_time and auth_time.isdigit():
            auth_dt = datetime.fromtimestamp(int(auth_time)).strftime("%Y-%m-%d %H:%M:%S")
            print(f"  Linked At:     {auth_dt}")
    else:
        print(f"  Account:       {ICONS.warn} Not authenticated (run 'syncdap scrobbler auth')")

    last_ts = state.get("last_scrobbled_timestamp", 0)
    last_dt_str = datetime.fromtimestamp(last_ts).strftime("%Y-%m-%d %H:%M:%S") if last_ts > 0 else "None"
    print(f"  Watermark:     {last_dt_str} (Total scrobbled: {state.get('total_scrobbled', 0)})")

    if log_present and parse_res:
        print(f"\n  Log File:      {log_file}")
        print(f"  Log Format:    Audioscrobbler v{parse_res.log_version} (log #TZ: {parse_res.timezone_directive})")
        print(f"  Applied TZ:    {parse_res.effective_tz_source}")
        if parse_res.client_directive:
            print(f"  DAP Client:    {parse_res.client_directive}")
        print(f"  Pending:       {len(parse_res.valid_entries)} tracks ready to submit")
        if parse_res.skipped_rating:
            print(f"  Skipped (S):   {len(parse_res.skipped_rating)} tracks (filtered out)")
        if parse_res.duplicates:
            print(f"  Already Synced: {len(parse_res.duplicates)} tracks (<= watermark)")
        if parse_res.expired:
            print(f"  Expired (>14d): {len(parse_res.expired)} tracks (exceeds Last.fm 14d limit)")
    else:
        print(f"\n  Log File:      No .scrobbler.log found at {log_file}")

    return 0


def render_sync_table(entries: list, total_count: int) -> None:
    """Render preview table of parsed scrobbles for CLI."""
    print(f"{'STATUS':<7} {'TRACK':<32} {'ARTIST':<24} {'DURATION':<8} {'TIMESTAMP'}")
    print(f"{'─' * 6}  {'─' * 31} {'─' * 23} {'─' * 8} {'─' * 19}")

    for e in entries[:40]:  # Limit preview to 40 items if large
        status_symbol = ICONS.ok if e.status == "valid" else (ICONS.warn if e.status == "expired" else ICONS.info)
        dt_str = datetime.fromtimestamp(e.timestamp).strftime("%Y-%m-%d %H:%M") if e.timestamp > 0 else "—"
        track_disp = (e.track[:29] + "…") if len(e.track) > 30 else e.track
        artist_disp = (e.artist[:21] + "…") if len(e.artist) > 22 else e.artist
        dur_disp = format_duration(e.duration)
        print(f"{status_symbol:<7} {track_disp:<32} {artist_disp:<24} {dur_disp:<8} {dt_str}")

    if total_count > 40:
        print(f"  … and {total_count - 40} more tracks")


def handle_sync(args: argparse.Namespace) -> int:
    session = load_session()
    state = load_state()
    log_file = resolve_log_path(args.target, args.root_dir)

    if not log_file.is_file():
        if args.json:
            print(json.dumps({"error": "Log file not found", "path": str(log_file)}, indent=2))
        elif not args.quiet:
            print(
                format_error_dual(
                    "No .scrobbler.log found",
                    cause=f"File does not exist at '{log_file}'",
                    fix="Connect your DAP or specify a target log file path.",
                ),
                file=sys.stderr,
            )
        return 0 if args.dry_run else 1

    # Check session unless dry-run
    if not session and not args.dry_run:
        if args.json:
            print(json.dumps({"error": "Authentication required"}, indent=2))
        else:
            print(
                format_error_dual(
                    "Not authenticated with Last.fm",
                    cause=f"No active session found in {get_lastfm_session_path()}",
                    fix="Run 'syncdap scrobbler auth' to link your account.",
                ),
                file=sys.stderr,
            )
        return 1

    # Timezone offset resolution
    tz_offset = resolve_tz_offset(args.tz_offset)

    # Parse log file
    start_time = time.time()
    last_watermark = state.get("last_scrobbled_timestamp", 0)
    parse_res = parse_scrobbler_log(
        log_file,
        tz_offset_hours=tz_offset,
        last_scrobbled_timestamp=last_watermark,
    )

    valid_tracks = parse_res.valid_entries

    # Machine-readable outputs
    if args.json:
        payload = {
            "log_path": str(log_file),
            "parsed_total": len(parse_res.entries),
            "valid_count": len(valid_tracks),
            "skipped_rating_count": len(parse_res.skipped_rating),
            "duplicate_count": len(parse_res.duplicates),
            "expired_count": len(parse_res.expired),
            "invalid_count": len(parse_res.invalid),
            "dry_run": args.dry_run,
            "tracks": [
                {
                    "artist": t.artist,
                    "album": t.album,
                    "track": t.track,
                    "duration": t.duration,
                    "timestamp": t.timestamp,
                    "status": t.status,
                }
                for t in parse_res.entries
            ],
        }
        if not args.dry_run and valid_tracks and session:
            try:
                session_key = session.get("key") or session.get("session_key", "")
                sub_res = scrobble_tracks(session_key, valid_tracks)
                payload["submitted"] = sub_res["accepted"]
                payload["ignored"] = sub_res["ignored"]
                # Rotate & clean
                archive_log(log_file)
                max_ts = max((t.timestamp for t in valid_tracks), default=last_watermark)
                save_state(
                    last_scrobbled_timestamp=max(max_ts, last_watermark),
                    total_scrobbled=state.get("total_scrobbled", 0) + sub_res["accepted"],
                )
                if not args.keep_log:
                    try:
                        log_file.unlink()
                    except OSError:
                        pass
            except LastFmError as e:
                payload["error"] = e.message
                print(json.dumps(payload, indent=2))
                return 1

        print(json.dumps(payload, indent=2))
        return 0

    if args.plain:
        for t in valid_tracks:
            print(f"{t.status}\t{t.artist}\t{t.album}\t{t.track}\t{t.duration}\t{t.timestamp}")
        return 0

    # Dry-run handling
    if args.dry_run:
        if not args.quiet:
            print(f"{ICONS.info} Simulating Last.fm scrobble sync from {log_file} (dry-run):\n")
            render_sync_table(parse_res.entries, len(parse_res.entries))
            print(
                f"\nSummary: {len(valid_tracks)} valid, {len(parse_res.skipped_rating)} skipped (S), "
                f"{len(parse_res.duplicates)} duplicates, {len(parse_res.expired)} expired."
            )
        return 0

    # Real execution
    if not valid_tracks:
        if not args.quiet:
            print(
                f"{ICONS.ok} No new scrobbles to submit "
                f"({len(parse_res.duplicates)} already synced, {len(parse_res.skipped_rating)} skipped)."
            )
        # Still rotate / delete if all entries are duplicates/skipped to keep DAP clean unless keep-log
        if not args.keep_log and parse_res.entries:
            archive_log(log_file)
            try:
                log_file.unlink()
            except OSError:
                pass
        return 0

    if not args.quiet:
        print(
            f"{ICONS.dl} Submitting {len(valid_tracks)} scrobbles to Last.fm ({session['username']})...",
            file=sys.stderr,
        )

    try:
        session_key = session.get("key") or session.get("session_key", "")
        batch_size = resolve_batch_size(getattr(args, "batch_size", None))
        sub_res = scrobble_tracks(session_key, valid_tracks, batch_size=batch_size)
    except LastFmError as e:
        print(
            format_error_dual(
                "Failed to submit scrobbles to Last.fm",
                cause=e.message,
                state=f"{len(valid_tracks)} tracks preserved on DAP in {log_file}",
                fix="Verify your network connection or re-authenticate: syncdap scrobbler auth",
            ),
            file=sys.stderr,
        )
        return 1

    # Safe post-sync archiving & state update
    archived_file = archive_log(log_file)
    max_ts = max((t.timestamp for t in valid_tracks), default=last_watermark)
    new_total = state.get("total_scrobbled", 0) + sub_res["accepted"]
    save_state(
        last_scrobbled_timestamp=max(max_ts, last_watermark),
        total_scrobbled=new_total,
    )

    # Cleanup log on DAP unless keep-log
    log_removed = False
    if not args.keep_log:
        try:
            log_file.unlink()
            log_removed = True
        except OSError as e:
            if not args.quiet:
                print(
                    f"{ICONS.warn} Could not remove .scrobbler.log on DAP ({e.strerror}). Log entries will be skipped by watermark on future runs.",
                    file=sys.stderr,
                )

    elapsed = round(time.time() - start_time, 2)
    if not args.quiet:
        print(
            f"{ICONS.ok} Synced {sub_res['accepted']} tracks to Last.fm ({session['username']}) in {elapsed}s."
        )
        if args.verbose:
            print(f"  Accepted:  {sub_res['accepted']}")
            print(f"  Ignored:   {sub_res['ignored']}")
            print(f"  Archived:  {archived_file or 'None'}")
            print(f"  DAP Log:   {'Removed' if log_removed else 'Retained'}")

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="syncdap scrobbler",
        description="Rockbox .scrobbler.log synchronization and Last.fm management",
    )
    parser.add_argument(
        "action",
        nargs="?",
        default="sync",
        choices=["sync", "auth", "status", "logout"],
        help="Action to perform: sync (default), auth, status, logout",
    )
    parser.add_argument(
        "target",
        nargs="?",
        default=None,
        help="Optional path to .scrobbler.log or music directory",
    )
    parser.add_argument(
        "-r",
        "--root-dir",
        default=None,
        help="Target music library or DAP mount root",
    )
    parser.add_argument(
        "-n",
        "--dry-run",
        action="store_true",
        help="Simulate execution without modifying files or submitting to Last.fm",
    )
    parser.add_argument(
        "-y",
        "--yes",
        action="store_true",
        help="Skip interactive confirmation prompts",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Show detailed diagnostic output",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Suppress non-error status output",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output machine-readable JSON",
    )
    parser.add_argument(
        "--plain",
        action="store_true",
        help="Output headerless tab-separated plain text",
    )
    parser.add_argument(
        "--tz-offset",
        "--timezone",
        dest="tz_offset",
        type=float,
        default=None,
        help="Explicit UTC offset hours (e.g. -3) to overwrite log file #TZ",
    )
    parser.add_argument(
        "--batch-size",
        dest="batch_size",
        type=int,
        default=None,
        help="Submission batch size (1-50, precedence: CLI -> config -> 50)",
    )
    parser.add_argument(
        "--keep-log",
        action="store_true",
        help="Retain .scrobbler.log on the DAP after successful upload",
    )
    parser.add_argument(
        "-c",
        "--config",
        default=None,
        help="Custom configuration file path",
    )

    args = parser.parse_args()

    if args.config:
        os.environ["SYNCDAP_CONFIG_FILE"] = str(Path(args.config).expanduser().resolve())

    if args.action == "auth":
        return handle_auth(args)
    elif args.action == "logout":
        return handle_logout(args)
    elif args.action == "status":
        return handle_status(args)
    elif args.action == "sync":
        return handle_sync(args)
    else:
        parser.print_help()
        return 2


if __name__ == "__main__":
    sys.exit(main())
