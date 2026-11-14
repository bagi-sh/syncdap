# ==============================================================================
# Module: lib/patch/metadata.py
# Purpose: Metadata extraction and tag transference for audio format upgrades
# ==============================================================================

import os
import mutagen
from mutagen.flac import FLAC, Picture
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, TIT2, TPE1, TALB, TRCK, TDRC, TCON, APIC
from mutagen.mp4 import MP4, MP4Cover


def extract_metadata_from_file(file_path):
    """Extract metadata, source URLs, and cover data from an existing audio file."""
    ext = os.path.splitext(file_path)[1].lower()
    meta = {
        'artist': '',
        'title': '',
        'album': '',
        'track_num': '',
        'tracks_count': '',
        'year': '',
        'genre': '',
        'spotify_url': '',
        'youtube_url': '',
        'cover_data': None,
        'cover_mime': 'image/jpeg'
    }

    try:
        if ext == '.mp3':
            audio = MP3(file_path, ID3=ID3)
            if audio.tags:
                for k, v in audio.tags.items():
                    if 'WOAS' in k:
                        meta['spotify_url'] = getattr(v, 'url', str(v)).strip()
                    elif 'COMM' in k:
                        txt = str(getattr(v, 'text', [''])[0])
                        if 'youtube.com' in txt or 'youtu.be' in txt:
                            meta['youtube_url'] = txt.strip()
                    elif isinstance(v, APIC) and v.type in (3, 0) and not meta['cover_data']:
                        meta['cover_data'] = v.data
                        meta['cover_mime'] = v.mime or 'image/jpeg'

                if 'TIT2' in audio.tags:
                    meta['title'] = str(audio.tags['TIT2'].text[0])
                if 'TPE1' in audio.tags:
                    meta['artist'] = str(audio.tags['TPE1'].text[0])
                if 'TALB' in audio.tags:
                    meta['album'] = str(audio.tags['TALB'].text[0])
                if 'TCON' in audio.tags:
                    meta['genre'] = str(audio.tags['TCON'].text[0])
                if 'TDRC' in audio.tags:
                    meta['year'] = str(audio.tags['TDRC'].text[0])[:4]
                if 'TRCK' in audio.tags:
                    tr = str(audio.tags['TRCK'].text[0]).split('/')
                    meta['track_num'] = tr[0]
                    if len(tr) > 1:
                        meta['tracks_count'] = tr[1]

        else:
            m = mutagen.File(file_path)
            if m and m.tags:
                meta['title'] = str(m.tags.get('title', [''])[0])
                meta['artist'] = str(m.tags.get('artist', [''])[0])
                meta['album'] = str(m.tags.get('album', [''])[0])
                meta['genre'] = str(m.tags.get('genre', [''])[0])
                meta['year'] = str(m.tags.get('date', [''])[0])[:4]
                meta['track_num'] = str(m.tags.get('tracknumber', [''])[0])

    except Exception:
        pass

    if not meta['title'] or not meta['artist']:
        base = os.path.splitext(os.path.basename(file_path))[0]
        if ' - ' in base:
            parts = base.split(' - ')
            meta['artist'] = parts[-1].strip()
            title_part = ' - '.join(parts[:-1]).strip()
            if ' ' in title_part and title_part.split(' ')[0].isdigit():
                meta['track_num'] = title_part.split(' ')[0]
                meta['title'] = ' '.join(title_part.split(' ')[1:]).strip()
            else:
                meta['title'] = title_part

    if not meta['album']:
        parent = os.path.basename(os.path.dirname(os.path.abspath(file_path)))
        if parent and parent != '.':
            meta['album'] = parent

    return meta


def transfer_tags_to_file(dest_file, meta, cover_path=None):
    """Write preserved metadata and cover art into the newly downloaded audio file."""
    ext = os.path.splitext(dest_file)[1].lower()

    img_data = meta['cover_data']
    mime_type = meta['cover_mime']
    if not img_data and cover_path and os.path.isfile(cover_path):
        try:
            with open(cover_path, 'rb') as f:
                img_data = f.read()
            mime_type = 'image/png' if cover_path.lower().endswith('.png') else 'image/jpeg'
        except Exception:
            pass

    try:
        if ext == '.flac':
            audio = FLAC(dest_file)
            if meta['title']:
                audio['title'] = meta['title']
            if meta['artist']:
                audio['artist'] = meta['artist']
            if meta['album']:
                audio['album'] = meta['album']
            if meta['year']:
                audio['date'] = str(meta['year'])
            if meta['genre']:
                audio['genre'] = meta['genre']
            if meta['track_num']:
                audio['tracknumber'] = str(meta['track_num'])
            if meta['tracks_count']:
                audio['totaltracks'] = str(meta['tracks_count'])

            if img_data:
                pic = Picture()
                pic.data = img_data
                pic.type = 3
                pic.mime = mime_type
                audio.clear_pictures()
                audio.add_picture(pic)
            audio.save()

        elif ext == '.mp3':
            audio = MP3(dest_file, ID3=ID3)
            if audio.tags is None:
                audio.add_tags()
            tags = audio.tags
            if meta['title']:
                tags.setall('TIT2', [TIT2(encoding=3, text=meta['title'])])
            if meta['artist']:
                tags.setall('TPE1', [TPE1(encoding=3, text=meta['artist'])])
            if meta['album']:
                tags.setall('TALB', [TALB(encoding=3, text=meta['album'])])
            if meta['year']:
                tags.setall('TDRC', [TDRC(encoding=3, text=str(meta['year']))])
            if meta['genre']:
                tags.setall('TCON', [TCON(encoding=3, text=meta['genre'])])
            if meta['track_num']:
                tr_str = f"{meta['track_num']}/{meta['tracks_count']}" if meta['tracks_count'] else str(meta['track_num'])
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
            audio.save(v2_version=3)

        elif ext == '.m4a':
            audio = MP4(dest_file)
            if audio.tags is None:
                audio.add_tags()
            if meta['title']:
                audio.tags['\xa9nam'] = [meta['title']]
            if meta['artist']:
                audio.tags['\xa9ART'] = [meta['artist']]
            if meta['album']:
                audio.tags['\xa9alb'] = [meta['album']]
            if meta['year']:
                audio.tags['\xa9day'] = [str(meta['year'])]
            if meta['genre']:
                audio.tags['\xa9gen'] = [str(meta['genre'])]
            if meta['track_num']:
                t_num = int(meta['track_num']) if str(meta['track_num']).isdigit() else 1
                t_tot = int(meta['tracks_count']) if str(meta['tracks_count']).isdigit() else 0
                audio.tags['trkn'] = [(t_num, t_tot)]
            if img_data:
                cov_fmt = MP4Cover.FORMAT_PNG if 'png' in mime_type else MP4Cover.FORMAT_JPEG
                audio.tags['covr'] = [MP4Cover(img_data, imageformat=cov_fmt)]
            audio.save()

    except Exception:
        pass
