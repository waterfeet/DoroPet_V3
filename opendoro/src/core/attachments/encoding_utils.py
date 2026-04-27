import re
import chardet

_ENCODING_PRIORITY = [
    "utf-8",
    "gbk",
    "gb2312",
    "gb18030",
    "big5",
    "shift_jis",
    "euc-kr",
    "latin-1",
    "windows-1252",
    "utf-16",
]


def _decode_with(raw: bytes, encoding: str) -> str:
    try:
        return raw.decode(encoding, errors="replace")
    except (UnicodeDecodeError, LookupError):
        return ""


def _replacement_ratio(text: str) -> float:
    if not text:
        return 1.0
    return text.count("\ufffd") / len(text)


def decode_file(raw: bytes) -> tuple:
    best_text = ""
    best_ratio = 2.0
    best_encoding = "utf-8"

    detected = chardet.detect(raw)
    hint = detected.get("encoding")
    confidence = detected.get("confidence", 0)

    trust_hint = hint and confidence >= 0.95 and hint.lower() != "ascii"

    trial_encodings = _ENCODING_PRIORITY[:]
    if trust_hint and hint.lower() not in trial_encodings:
        trial_encodings.insert(0, hint.lower())

    for enc in trial_encodings:
        text = _decode_with(raw, enc)
        if not text:
            continue
        ratio = _replacement_ratio(text)
        if ratio < best_ratio or (ratio == best_ratio and enc == "utf-8"):
            best_ratio = ratio
            best_text = text
            best_encoding = enc

    return best_text, best_encoding


_HTML_META_RE = re.compile(
    br'<meta[^>]+charset\s*=\s*["\']?([a-zA-Z0-9_\-]+)["\']?',
    re.IGNORECASE,
)


def decode_html_file(raw: bytes) -> tuple:
    meta_encoding = None
    head = raw[:4096]
    match = _HTML_META_RE.search(head)
    if match:
        meta_encoding = match.group(1).decode("ascii", errors="replace").lower()

    if meta_encoding:
        text = _decode_with(raw, meta_encoding)
        if text and _replacement_ratio(text) < 0.01:
            return text, meta_encoding

    detected = chardet.detect(raw)
    hint = detected.get("encoding")
    confidence = detected.get("confidence", 0)

    trust_hint = hint and confidence >= 0.95 and hint.lower() != "ascii"

    trial_encodings = _ENCODING_PRIORITY[:]
    if trust_hint and hint.lower() not in trial_encodings:
        trial_encodings.insert(0, hint.lower())

    best_text = ""
    best_ratio = 2.0
    best_encoding = "utf-8"

    for enc in trial_encodings:
        text = _decode_with(raw, enc)
        if not text:
            continue
        ratio = _replacement_ratio(text)
        if ratio < best_ratio or (ratio == best_ratio and enc == "utf-8"):
            best_ratio = ratio
            best_text = text
            best_encoding = enc

    return best_text, best_encoding
