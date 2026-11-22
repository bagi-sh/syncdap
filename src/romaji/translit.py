"""pykakasi character transliteration helpers."""

import re
import unicodedata
import pykakasi
from share import AUDIO_EXTENSIONS, SYMBOL_REPLACEMENTS
from share import sanitize_filename as base_sanitize_filename

# Initialize pykakasi converter
_kakasi = pykakasi.kakasi()

# Japanese verb and adjective inflection endings (okurigana) that attach to kanji stems
OKURIGANA_PATTERNS = re.compile(
    r'^(?:[ただてで]|たら|だら|たり|だり|ない|なかった|ず|ぬ|る|れる|られる|せる|させる|れた|れたら|れば|い|かった|く|ければ|さ|ます|ました|たい|たく|り|き|ち|し)$'
)

# Particles and small words kept lowercase in middle of titles
PARTICLES = {
    'no', 'wo', 'wa', 'ga', 'ni', 'to', 'de', 'mo', 'na', 'he', 'e',
    'kara', 'made', 'in', 'on', 'at', 'of', 'and', 'the', 'a', 'an'
}


def is_kanji(s: str) -> bool:
    return bool(re.search(r'[\u4e00-\u9fff]', s))


def is_hiragana(s: str) -> bool:
    return bool(re.search(r'^[\u3040-\u309f]+$', s))


def contains_japanese(text: str) -> bool:
    """Check if text contains Japanese Hiragana, Katakana, Kanji, or iteration mark."""
    if not text:
        return False
    return bool(re.search(r'[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\u3005]', text))


def capitalize_romaji_title(text: str) -> str:
    """Apply standard Title Case to Romanized titles/folders preserving particles and acronyms."""
    def cap_word(w: str, is_first: bool = False) -> str:
        if not w:
            return w
        if len(w) > 1 and w.isupper():
            return w
        wl = w.lower()
        if not is_first and wl in PARTICLES:
            return wl
        return w[0].upper() + w[1:].lower() if len(w) > 1 else w.upper()

    tokens = re.split(r'(\s+|[-–—/()[\],.:;])', text)
    res = []
    is_first = True
    for t in tokens:
        if not t:
            continue
        if re.match(r'^\s+$', t) or re.match(r'^[-–—/()[\],.:;]+$', t):
            res.append(t)
            if re.search(r'[-–—/([.:;]', t):
                is_first = True
        else:
            res.append(cap_word(t, is_first))
            is_first = False
    return ''.join(res)


def sanitize_filename(name: str, for_folder: bool = False) -> str:
    """Sanitize name for FAT32 / exFAT filesystems."""
    sanitized = base_sanitize_filename(name)
    if for_folder:
        sanitized = capitalize_romaji_title(sanitized)
    return sanitized


def to_romaji(text: str, for_filename: bool = False, for_folder: bool = False, for_tag: bool = False) -> str:
    """
    Transliterate Japanese Kana/Kanji to Romaji using Hepburn romanization.
    Handles verb/adjective okurigana, iteration marks (々), wave dashes (〜),
    and spacing around punctuation.
    """
    if not text:
        return text

    text = re.sub(r'([\u4e00-\u9fff])々', r'\1\1', text)
    text = re.sub(r'\s*[〜～~]\s*(.*?)\s*[〜～~]\s*', r' - \1 - ', text)
    text = re.sub(r'[〜～~]', ' - ', text)
    text = re.sub(r'――+', ' - ', text)

    normalized = unicodedata.normalize('NFKC', text)

    for old_sym, new_sym in SYMBOL_REPLACEMENTS.items():
        normalized = normalized.replace(old_sym, new_sym)

    if not contains_japanese(normalized):
        if for_filename or for_folder:
            return sanitize_filename(normalized, for_folder=for_folder)
        return re.sub(r'\s+', ' ', normalized).strip()

    normalized = re.sub(r'([a-zA-Z0-9\u3040-\u30ff\u4e00-\u9fff])([(\[])', r'\1 \2', normalized)
    normalized = re.sub(r'([)\]])([a-zA-Z0-9\u3040-\u30ff\u4e00-\u9fff])', r'\1 \2', normalized)

    items = _kakasi.convert(normalized)
    tokens = []
    prev_was_kanji = False

    for item in items:
        orig = item['orig']
        hep = item['hepburn']

        if prev_was_kanji and is_hiragana(orig) and OKURIGANA_PATTERNS.match(orig):
            if tokens:
                tokens[-1] += hep
                prev_was_kanji = False
                continue

        if 'kurikaesi' in hep:
            hep = orig

        if contains_japanese(orig):
            tokens.append(hep)
            prev_was_kanji = is_kanji(orig)
        else:
            tokens.append(orig)
            prev_was_kanji = False

    out = []
    for t in tokens:
        if not t:
            continue
        if out and re.search(r'[a-zA-Z0-9]$', out[-1]) and re.search(r'^[a-zA-Z0-9]', t):
            out.append(' ')
        out.append(t)

    converted = ''.join(out)
    converted = re.sub(r'\s*-\s*', ' - ', converted)
    converted = re.sub(r'\s+([,.:;?!~）\)])', r'\1', converted)
    converted = re.sub(r'([（\(])\s+', r'\1', converted)
    converted = re.sub(r' +', ' ', converted).strip()

    if for_folder:
        return sanitize_filename(converted, for_folder=True)

    if for_filename:
        return sanitize_filename(converted, for_folder=False)

    if for_tag:
        return capitalize_romaji_title(converted)

    return converted
