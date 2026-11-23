"""Universal audio metadata inspection and tag writing."""

import json
import os
import re
import subprocess

import mutagen
from mutagen.flac import FLAC, Picture
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, TIT2, TPE1, TPE2, TALB, TRCK, TDRC, TCON, APIC
from mutagen.mp4 import MP4, MP4Cover
from mutagen.oggvorbis import OggVorbis
from mutagen.oggopus import OggOpus
from mutagen.wave import WAVE

from .constants import AUDIO_EXTENSIONS, IGNORED_DIRS, LOSSLESS_EXTENSIONS, ID3_VERSION
from .text import clean_string, parse_filename_metadata
from .covers import has_embedded_cover as has_embedded_cover_fast


def find_audio_files(root_dir: str) -> list[str]:
    """Scan root_dir recursively for audio files excluding ignored system directories."""
    audio_files = []
    root_path = os.path.abspath(root_dir)

    if os.path.isfile(root_path):
        ext = os.path.splitext(root_path)[1].lower()
        if ext in AUDIO_EXTENSIONS:
            return [root_path]
        return []

    for dirpath, dirnames, filenames in os.walk(root_path):
        dirnames[:] = [
            d for d in dirnames
            if d.lower() not in IGNORED_DIRS and not d.startswith('.Trash')
        ]
        for f in filenames:
            ext = os.path.splitext(f)[1].lower()
            if ext in AUDIO_EXTENSIONS:
                audio_files.append(os.path.join(dirpath, f))

    return sorted(audio_files)


# ==============================================================================
# Universal Audio Metadata Reading & Writing
# ==============================================================================

def read_audio_metadata(file_path: str, fallback_to_filename: bool = True) -> dict:
    """
    Universally extract tags, embedded URLs, and front cover art from an audio file.
    Returns dict with keys: artist, title, album, album_artist, track_num,
    total_tracks, year, genre, duration, spotify_url, youtube_url, cover_data, cover_mime.
    """
    meta = {
        'artist': '',
        'title': '',
        'album': '',
        'album_artist': '',
        'track_num': '',
        'total_tracks': '',
        'year': '',
        'genre': '',
        'duration': None,
        'spotify_url': '',
        'youtube_url': '',
        'cover_data': None,
        'cover_mime': 'image/jpeg',
    }
    if not file_path or not os.path.isfile(file_path):
        return meta

    ext = os.path.splitext(file_path)[1].lower()

    try:
        audio = mutagen.File(file_path)
        if audio is not None:
            if hasattr(audio, 'info') and hasattr(audio.info, 'length'):
                meta['duration'] = float(audio.info.length)

            if isinstance(getattr(audio, 'tags', None), ID3):
                tags = audio.tags
                for k, v in tags.items():
                    if 'WOAS' in k:
                        meta['spotify_url'] = getattr(v, 'url', str(v)).strip()
                    elif 'COMM' in k:
                        txt = str(getattr(v, 'text', [''])[0])
                        if 'youtube.com' in txt or 'youtu.be' in txt:
                            meta['youtube_url'] = txt.strip()
                    elif isinstance(v, APIC) and v.type in (3, 0) and not meta['cover_data']:
                        meta['cover_data'] = v.data
                        meta['cover_mime'] = v.mime or 'image/jpeg'

                if 'TIT2' in tags:
                    meta['title'] = clean_string(tags['TIT2'].text)
                if 'TPE1' in tags:
                    meta['artist'] = clean_string(tags['TPE1'].text)
                if 'TALB' in tags:
                    meta['album'] = clean_string(tags['TALB'].text)
                if 'TPE2' in tags:
                    meta['album_artist'] = clean_string(tags['TPE2'].text)
                if 'TCON' in tags:
                    meta['genre'] = clean_string(tags['TCON'].text)
                if 'TDRC' in tags:
                    meta['year'] = clean_string(tags['TDRC'].text)[:4]
                if 'TRCK' in tags:
                    tr = clean_string(tags['TRCK'].text).split('/')
                    meta['track_num'] = tr[0]
                    if len(tr) > 1:
                        meta['total_tracks'] = tr[1]

            elif ext == '.m4a' and audio.tags:
                tags = audio.tags
                meta['title']        = clean_string(tags.get('\xa9nam', tags.get('title', [''])))
                meta['artist']       = clean_string(tags.get('\xa9ART', tags.get('artist', [''])))
                meta['album']        = clean_string(tags.get('\xa9alb', tags.get('album', [''])))
                meta['album_artist'] = clean_string(tags.get('aART', tags.get('albumartist', [''])))
                meta['genre']        = clean_string(tags.get('\xa9gen', tags.get('genre', [''])))
                meta['year']         = clean_string(tags.get('\xa9day', tags.get('date', [''])))[:4]

                tr_val = tags.get('trkn', [(0, 0)])[0]
                if isinstance(tr_val, (tuple, list)):
                    meta['track_num'] = str(tr_val[0]) if tr_val[0] else ''
                    if len(tr_val) > 1 and tr_val[1]:
                        meta['total_tracks'] = str(tr_val[1])

                covs = tags.get('covr', [])
                if covs and not meta['cover_data']:
                    meta['cover_data'] = bytes(covs[0])
                    meta['cover_mime'] = 'image/png' if getattr(covs[0], 'imageformat', None) == MP4Cover.FORMAT_PNG else 'image/jpeg'

            elif audio.tags:
                tags = audio.tags
                meta['title']        = clean_string(tags.get('title', ['']))
                meta['artist']       = clean_string(tags.get('artist', ['']))
                meta['album']        = clean_string(tags.get('album', ['']))
                meta['album_artist'] = clean_string(tags.get('albumartist', tags.get('album_artist', [''])))
                meta['genre']        = clean_string(tags.get('genre', ['']))
                meta['year']         = clean_string(tags.get('date', ['']))[:4]

                tr_val = clean_string(tags.get('tracknumber', tags.get('track_number', [''])))
                if isinstance(tr_val, tuple):
                    meta['track_num'] = str(tr_val[0]) if tr_val[0] else ''
                    if len(tr_val) > 1 and tr_val[1]:
                        meta['total_tracks'] = str(tr_val[1])
                elif '/' in str(tr_val):
                    parts = str(tr_val).split('/')
                    meta['track_num'] = parts[0]
                    meta['total_tracks'] = parts[1]
                else:
                    meta['track_num'] = str(tr_val)

                tot_val = clean_string(tags.get('totaltracks', tags.get('trackcount', [''])))
                if tot_val and not meta['total_tracks']:
                    meta['total_tracks'] = str(tot_val)

    except Exception:
        pass

    if fallback_to_filename and (not meta['title'] or not meta['artist'] or not meta['album']):
        fn_meta = parse_filename_metadata(file_path)
        meta['title'] = meta['title'] or fn_meta.get('title', '')
        meta['artist'] = meta['artist'] or fn_meta.get('artist', '')
        meta['album'] = meta['album'] or fn_meta.get('album', '')
        if not meta['track_num'] and fn_meta.get('track_no'):
            meta['track_num'] = str(int(fn_meta['track_no']))

    return meta


# Backward-compatible alias
get_audio_metadata = read_audio_metadata


def write_audio_metadata(
    file_path: str,
    meta: dict,
    cover_data: bytes | None = None,
    cover_mime: str = 'image/jpeg',
) -> bool:
    """
    Universally write clean metadata and front cover artwork into an audio file.
    Enforces ID3v2.3 compatibility for Rockbox DAPs on MP3.
    """
    if not file_path or not os.path.isfile(file_path):
        return False

    ext = os.path.splitext(file_path)[1].lower()
    title = str(meta.get('title') or '').strip()
    artist = str(meta.get('artist') or '').strip()
    album = str(meta.get('album') or '').strip()
    album_artist = str(meta.get('album_artist') or artist).strip()
    year = str(meta.get('year') or '').strip()[:4]
    genre = str(meta.get('genre') or '').strip()
    track_num = str(meta.get('track_num') or '').strip()
    total_tracks = str(meta.get('total_tracks') or meta.get('tracks_count') or '').strip()

    img_data = cover_data or meta.get('cover_data')
    mime_type = cover_mime or meta.get('cover_mime') or 'image/jpeg'

    try:
        if ext == '.mp3':
            audio = MP3(file_path, ID3=ID3)
            if audio.tags is None:
                audio.add_tags()
            tags = audio.tags
            if title:
                tags.setall('TIT2', [TIT2(encoding=3, text=title)])
            if artist:
                tags.setall('TPE1', [TPE1(encoding=3, text=artist)])
            if album:
                tags.setall('TALB', [TALB(encoding=3, text=album)])
            if album_artist:
                tags.setall('TPE2', [TPE2(encoding=3, text=album_artist)])
            if year:
                tags.setall('TDRC', [TDRC(encoding=3, text=year)])
            if genre:
                tags.setall('TCON', [TCON(encoding=3, text=genre)])
            if track_num:
                tr_str = f"{track_num}/{total_tracks}" if total_tracks else str(track_num)
                tags.setall('TRCK', [TRCK(encoding=3, text=tr_str)])

            if img_data:
                tags.delall('APIC')
                tags.add(APIC(
                    encoding=3,
                    mime=mime_type,
                    type=3,
                    desc='Cover',
                    data=img_data
                ))
            audio.save(v2_version=ID3_VERSION)
            return True

        elif ext == '.flac':
            audio = FLAC(file_path)
            if title:
                audio['title'] = [title]
            if artist:
                audio['artist'] = [artist]
            if album:
                audio['album'] = [album]
            if album_artist:
                audio['albumartist'] = [album_artist]
            if year:
                audio['date'] = [year]
            if genre:
                audio['genre'] = [genre]
            if track_num:
                audio['tracknumber'] = [str(track_num)]
            if total_tracks:
                audio['totaltracks'] = [str(total_tracks)]

            if img_data:
                pic = Picture()
                pic.data = img_data
                pic.type = 3
                pic.mime = mime_type
                pic.desc = ''
                audio.clear_pictures()
                audio.add_picture(pic)
            audio.save()
            return True

        elif ext == '.m4a':
            audio = MP4(file_path)
            if audio.tags is None:
                audio.add_tags()
            tags = audio.tags
            if title:
                tags['\xa9nam'] = [title]
            if artist:
                tags['\xa9ART'] = [artist]
            if album:
                tags['\xa9alb'] = [album]
            if album_artist:
                tags['aART'] = [album_artist]
            if year:
                tags['\xa9day'] = [year]
            if genre:
                tags['\xa9gen'] = [genre]
            if track_num:
                t_num = int(track_num) if str(track_num).isdigit() else 1
                t_tot = int(total_tracks) if str(total_tracks).isdigit() else 0
                tags['trkn'] = [(t_num, t_tot)]
            if img_data:
                cov_fmt = MP4Cover.FORMAT_PNG if 'png' in mime_type.lower() else MP4Cover.FORMAT_JPEG
                tags['covr'] = [MP4Cover(img_data, imageformat=cov_fmt)]
            audio.save()
            return True

        elif ext in ('.ogg', '.opus'):
            import base64
            audio = OggOpus(file_path) if ext == '.opus' else OggVorbis(file_path)
            if title:
                audio['title'] = [title]
            if artist:
                audio['artist'] = [artist]
            if album:
                audio['album'] = [album]
            if album_artist:
                audio['albumartist'] = [album_artist]
            if year:
                audio['date'] = [year]
            if genre:
                audio['genre'] = [genre]
            if track_num:
                audio['tracknumber'] = [str(track_num)]
            if total_tracks:
                audio['totaltracks'] = [str(total_tracks)]

            if img_data:
                pic = Picture()
                pic.type = 3
                pic.mime = mime_type
                pic.data = img_data
                pic_data = base64.b64encode(pic.write()).decode('ascii')
                audio['metadata_block_picture'] = [pic_data]
            audio.save()
            return True

    except Exception:
        pass
    return False


def set_audio_genre(file_path: str, genre_name: str) -> bool:
    """Update only the genre tag across audio formats."""
    if not file_path or not os.path.isfile(file_path) or not genre_name:
        return False
    ext = os.path.splitext(file_path)[1].lower()
    try:
        if ext == '.mp3':
            audio = MP3(file_path, ID3=ID3)
            if audio.tags is None:
                audio.add_tags()
            audio.tags.setall('TCON', [TCON(encoding=3, text=genre_name)])
            audio.save(v2_version=ID3_VERSION)
            return True
        elif ext == '.flac':
            audio = FLAC(file_path)
            audio['genre'] = [genre_name]
            audio.save()
            return True
        elif ext == '.m4a':
            audio = MP4(file_path)
            if audio.tags is None:
                audio.add_tags()
            audio.tags['\xa9gen'] = [genre_name]
            audio.save()
            return True
        elif ext in ('.ogg', '.opus'):
            audio = OggOpus(file_path) if ext == '.opus' else OggVorbis(file_path)
            audio['genre'] = [genre_name]
            audio.save()
            return True
    except Exception:
        pass
    return False


# ==============================================================================
# Audio Quality & Fidelity Scoring
# ==============================================================================

def get_file_duration(path: str) -> float:
    """Return duration in seconds via ffprobe (no mutagen), or 0.0 on failure."""
    try:
        cmd = [
            'ffprobe', '-v', 'quiet', '-print_format', 'json',
            '-show_entries', 'format=duration', path
        ]
        out = subprocess.run(cmd, capture_output=True, text=True, check=True).stdout
        return float(json.loads(out).get('format', {}).get('duration', 0.0))
    except Exception:
        return 0.0


def is_lossless(path: str) -> bool:
    """Return True if the file extension indicates a lossless format."""
    return os.path.splitext(path)[1].lower() in LOSSLESS_EXTENSIONS


def get_bitrate_kbps(path: str) -> int:
    """Return audio bitrate in kbps via ffprobe, or 0 on failure."""
    try:
        cmd = [
            'ffprobe', '-v', 'quiet', '-print_format', 'json',
            '-show_entries', 'format=bit_rate', path
        ]
        out = subprocess.run(cmd, capture_output=True, text=True, check=True).stdout
        br = json.loads(out).get('format', {}).get('bit_rate', 0)
        return int(br) // 1000
    except Exception:
        return 0


def track_number_from_filename(fname: str) -> int | None:
    """Extract leading track number from filename (e.g. '03 Title - Artist.mp3' → 3)."""
    m = re.match(r'^(\d+)\s', fname)
    return int(m.group(1)) if m else None


def get_audio_quality_score(file_path: str) -> tuple[int, str]:
    """
    Compute a numerical quality score for audio file.
    Higher is better.
    Lossless (FLAC, ALAC, WAV) > Lossy (AAC/M4A, OPUS, OGG, MP3).
    Corrupted or 0-byte files return -1.
    """
    try:
        size = os.path.getsize(file_path)
        if size == 0:
            return -1, "0-byte file"
    except OSError:
        return -1, "unreadable"

    ext = os.path.splitext(file_path)[1].lower()

    try:
        audio = mutagen.File(file_path)
        if audio is None:
            return 0, f"unknown {ext}"

        # 1. FLAC (Lossless)
        if ext == '.flac' or isinstance(audio, FLAC):
            sample_rate = getattr(audio.info, 'sample_rate', 44100) or 44100
            bits = getattr(audio.info, 'bits_per_sample', 16) or 16
            score = 1000000 + (bits * 10000) + sample_rate
            return score, f"FLAC {bits}-bit {sample_rate}Hz"

        # 2. WAV (Lossless)
        if ext == '.wav' or isinstance(audio, WAVE):
            sample_rate = getattr(audio.info, 'sample_rate', 44100) or 44100
            bits = getattr(audio.info, 'bits_per_sample', 16) or 16
            score = 900000 + (bits * 10000) + sample_rate
            return score, f"WAV {bits}-bit {sample_rate}Hz"

        # 3. M4A (ALAC Lossless or AAC Lossy)
        if ext == '.m4a' or isinstance(audio, MP4):
            codec = getattr(audio.info, 'codec', '')
            if 'alac' in str(codec).lower():
                return 950000, "ALAC Lossless"

            bitrate = getattr(audio.info, 'bitrate', 0) or 0
            bitrate_kbps = bitrate // 1000 if bitrate else 0
            if bitrate_kbps == 0 and getattr(audio.info, 'length', 0) > 0:
                bitrate_kbps = int((size * 8) / (audio.info.length * 1000))
            score = 500000 + bitrate_kbps
            return score, f"M4A/AAC ~{bitrate_kbps}kbps"

        # 4. OPUS
        if ext == '.opus' or isinstance(audio, OggOpus):
            bitrate = getattr(audio.info, 'bitrate', 0) or 0
            bitrate_kbps = bitrate // 1000 if bitrate else 160
            score = 450000 + bitrate_kbps
            return score, f"OPUS ~{bitrate_kbps}kbps"

        # 5. OGG Vorbis
        if ext == '.ogg' or isinstance(audio, OggVorbis):
            bitrate = getattr(audio.info, 'bitrate', 0) or 0
            bitrate_kbps = bitrate // 1000 if bitrate else 192
            score = 400000 + bitrate_kbps
            return score, f"OGG ~{bitrate_kbps}kbps"

        # 6. MP3
        if ext == '.mp3' or isinstance(audio, MP3):
            bitrate = getattr(audio.info, 'bitrate', 0) or 0
            bitrate_kbps = bitrate // 1000 if bitrate else 320
            score = 300000 + bitrate_kbps
            return score, f"MP3 ~{bitrate_kbps}kbps"

    except Exception as e:
        return 10, f"error reading tags: {e}"

    return 50, f"fallback {ext}"


def audio_quality_wins(candidate: str, incumbent: str) -> tuple[bool, str]:
    """
    Compare quality of two audio files. Returns (should_replace: bool, reason: str).
    Uses universal get_audio_quality_score for accurate ranking.
    """
    cand_score, cand_desc = get_audio_quality_score(candidate)
    inc_score, inc_desc = get_audio_quality_score(incumbent)

    if cand_score > inc_score:
        return True, f"candidate ({cand_desc}) > incumbent ({inc_desc})"
    return False, f"incumbent ({inc_desc}) >= candidate ({cand_desc})"


def is_valid_audio(path: str) -> bool:
    """Return True if path points to an existing, non-empty, playable audio file."""
    try:
        if not path or not os.path.isfile(path):
            return False
        if os.path.getsize(path) <= 0:
            return False
        ext = os.path.splitext(path)[1].lower()
        if ext not in AUDIO_EXTENSIONS:
            return False
        dur = get_file_duration(path)
        if dur > 0:
            return True
        meta = read_audio_metadata(path, fallback_to_filename=False)
        return bool(meta.get('duration') and meta['duration'] > 0)
    except Exception:
        return False
