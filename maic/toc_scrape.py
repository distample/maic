"""Pull a chapter list out of a web page the user points at.

Fetching and parsing are kept apart on purpose: `extract_chapters` is pure and
can be tested against saved markup, while `fetch_page` is nothing but network
I/O.
"""

from __future__ import annotations

import re
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from typing import Any, TypedDict

from bs4 import BeautifulSoup

MAX_BYTES = 5 * 1024 * 1024
TIMEOUT_SECONDS = 20
MAX_REDIRECTS = 3
MAX_ROW_CHARS = 200
MIN_LIST_ROWS = 2

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

# Tags that never hold a chapter row, so they are skipped before parsing.
_SKIP_TAGS = frozenset(
    {"script", "style", "head", "title", "meta", "link", "noscript", "svg", "path", "template"}
)

# Longest spellings first: the alternation is first-match-wins, and "гл" would
# otherwise swallow the start of "глава".
_CHAPTER_WORDS = (
    r"глав\w*|гл|chapters?|chap|ch|эпизод\w*|episodes?|ep|част\w*|parts?"
)
_NUMBERED_RE = re.compile(
    r"\b(" + _CHAPTER_WORDS + r")\s*[.\-–—№#:]?\s*(\d+(?:[.,]\d+)?)",
    re.IGNORECASE,
)
# A row that names no chapter word still counts when it opens with a number,
# a separator and a title. The trailing space keeps dates like 09.08.2026 out.
_BARE_NUMBER_RE = re.compile(r"^\s*(\d{1,4}(?:[.,]\d+)?)\s*[.\-–—:)]\s+(\S.*)$")
# Volume words are kept out of the chapter alternation above: fold them in and
# "Том 5. Глава 38" would be read as chapter 5. Searched across the whole row,
# so a volume named after the chapter is found too.
_VOLUME_WORDS = r"том\w*|vol(?:ume)?|book|кн(?:ига)?"
_VOLUME_RE = re.compile(
    r"\b(?:" + _VOLUME_WORDS + r")\s*[.\-–—№#:]?\s*(\d{1,3})\b",
    re.IGNORECASE,
)
# An element that says nothing but "Том 3" is a heading, and every chapter row
# after it belongs to that volume until the next heading. The anchors are the
# point: "Том 1 (главы 1-8)" is deliberately not a heading, and neither is a
# range like "Vol 1-40".
_VOLUME_HEADING_RE = re.compile(
    r"^\s*(?:" + _VOLUME_WORDS + r")\s*[.\-–—№#:]?\s*(\d{1,3})\s*$",
    re.IGNORECASE,
)
_TITLE_LEAD = ":-–—.·|• "


class ScrapedChapter(TypedDict):
    """One chapter as the source page spells it."""

    number: float
    label: str
    title: str
    volume: int | None


# One element that reads as a chapter row: the element, its text, the parsed
# chapter, and the ordinal of the heading its volume was borrowed from (None
# when the row named its own or there was none to borrow).
_Candidate = tuple[Any, str, ScrapedChapter, int | None]


class TocScrapeError(Exception):
    """The page could not be fetched or decoded."""


def _canonical_label(word: str) -> str:
    """Return one spelling for whatever the page called a chapter."""
    lowered = word.lower()
    if lowered.startswith("глав") or lowered == "гл":
        return "Глава"
    if lowered.startswith("эпизод"):
        return "Эпизод"
    if lowered.startswith("част"):
        return "Часть"
    if lowered.startswith("chapter") or lowered in {"chap", "ch"}:
        return "Chapter"
    if lowered.startswith("episode") or lowered == "ep":
        return "Episode"
    if lowered.startswith("part"):
        return "Part"
    return word


def _parse_row(text: str) -> ScrapedChapter | None:
    """Split one line into chapter word, number and title."""
    match = _NUMBERED_RE.search(text)
    if match:
        label = _canonical_label(match.group(1))
        number = match.group(2)
        rest = text[match.end() :]
    else:
        match = _BARE_NUMBER_RE.match(text)
        if not match:
            return None
        label = ""
        number = match.group(1)
        rest = match.group(2)
    title = rest.strip().lstrip(_TITLE_LEAD).strip()
    volume = _VOLUME_RE.search(text)
    return {
        "number": float(number.replace(",", ".")),
        "label": label,
        "title": title,
        "volume": int(volume.group(1)) if volume else None,
    }


def _row_text(element: Any) -> str:
    """Return the element's visible text on a single line."""
    return re.sub(r"\s+", " ", element.get_text(" ", strip=True)).strip()


def _signature(element: Any, with_classes: bool) -> str:
    """Describe where an element sits, so siblings of a list share one key."""
    parts = []
    node = element
    for _ in range(3):
        if node is None or getattr(node, "name", None) is None:
            break
        if with_classes:
            classes = ".".join(sorted(node.get("class") or []))
            parts.append(node.name + "#" + classes)
        else:
            parts.append(node.name)
        node = node.parent
    return "|".join(parts)


def extract_chapters(html: str) -> list[ScrapedChapter]:
    """Return the chapters listed on a page, ascending by volume and number.

    The chapter list is taken to be the largest set of same-shaped elements
    that each name a chapter number. A row that names no volume of its own
    belongs to the last "Том N" heading seen before it in document order,
    but headings are trusted only when at least two of them list chapters.
    """
    soup = BeautifulSoup(html or "", "lxml")
    candidates: list[_Candidate] = []
    current_volume: int | None = None
    headings_seen = 0
    for element in soup.find_all(True):
        if element.name in _SKIP_TAGS:
            continue
        text = _row_text(element)
        if not text or len(text) > MAX_ROW_CHARS:
            continue
        heading = _VOLUME_HEADING_RE.match(text)
        if heading:
            current_volume = int(heading.group(1))
            headings_seen += 1
            continue
        parsed = _parse_row(text)
        if parsed is None:
            continue
        # A row that borrows its volume remembers which heading lent it.
        source = None
        if parsed["volume"] is None and current_volume is not None:
            parsed["volume"] = current_volume
            source = headings_seen
        candidates.append((element, text, parsed, source))
    if not candidates:
        return []

    # Classes are the precise signal. Tag-only grouping is a fallback for
    # pages that carry none: on a page that has them it lumps every unrelated
    # div into one heap that outvotes the real list.
    rows = _largest_group(candidates, with_classes=True)
    if rows is None:
        rows = _largest_group(candidates, with_classes=False)
    if rows is None:
        return []

    # One "Том N" ahead of the list is as likely the last option of a volume
    # dropdown or a badge as a heading. A page laid out by volume has several,
    # each introducing its own rows; short of that, borrowed volumes are given
    # back and the rows stand as they arrived.
    lenders = {source for _element, _text, _parsed, source in rows if source is not None}
    if len(lenders) < 2:
        for _element, _text, parsed, source in rows:
            if source is not None:
                parsed["volume"] = None

    # Numbers restart in every volume on some sites, so a chapter is the pair.
    by_key: dict[tuple[int | None, float], ScrapedChapter] = {}
    for _element, _text, chapter, _source in rows:
        by_key.setdefault((chapter["volume"], chapter["number"]), chapter)
    return [by_key[key] for key in sorted(by_key, key=_chapter_order)]


def _chapter_order(key: tuple[int | None, float]) -> tuple[bool, int, float]:
    """Sort by volume, then number; chapters that name no volume go last."""
    volume, number = key
    return (volume is None, volume or 0, number)


def _largest_group(candidates: list[_Candidate], *, with_classes: bool) -> list[_Candidate] | None:
    """Return the biggest set of same-shaped rows, or None if there is none."""
    groups: dict[str, list[_Candidate]] = {}
    for candidate in candidates:
        groups.setdefault(_signature(candidate[0], with_classes), []).append(candidate)
    best: tuple[tuple[int, int, float], list[_Candidate]] | None = None
    for rows in groups.values():
        if len(rows) < MIN_LIST_ROWS:
            continue
        # A real list calls every row by the same word. A heap of unrelated
        # blocks that merely hold numbers disagrees with itself, so it is
        # ranked by how many rows agree rather than by how many there are.
        agreeing = Counter(parsed["label"] for _, _, parsed, _ in rows).most_common(1)[0][1]
        # Where two sets still tie, shorter rows win: that is the link itself
        # rather than the row around it, which also carries a date and a count.
        score = (agreeing, len(rows), -sum(len(text) for _, text, _, _ in rows) / len(rows))
        if best is None or score > best[0]:
            best = (score, rows)
    return None if best is None else best[1]


class _LimitedRedirects(urllib.request.HTTPRedirectHandler):
    """Stop chasing redirects long before urllib's own limit."""

    max_redirections = MAX_REDIRECTS


def _is_page(content_type: str) -> bool:
    """Tell a web page apart from a download."""
    kind = content_type.split(";")[0].strip().lower()
    return kind.startswith("text/") or kind in {"application/xhtml+xml", "application/xml"}


def _decode(raw: bytes, charset: str | None) -> str:
    """Decode page bytes by header charset, then meta charset, then UTF-8."""
    if not charset:
        match = re.search(rb"charset=[\"']?([\w\-]+)", raw[:4096], re.IGNORECASE)
        if match:
            charset = match.group(1).decode("ascii", "ignore")
    for encoding in (charset, "utf-8"):
        if not encoding:
            continue
        try:
            return raw.decode(encoding)
        except (LookupError, UnicodeDecodeError):
            continue
    return raw.decode("utf-8", "replace")


def fetch_page(url: str) -> str:
    """Download one HTML page and return its text.

    Raises `TocScrapeError` with a message naming the cause: anything the user
    can act on (wrong scheme, dead host, 403, a download instead of a page)
    should read differently from anything else.
    """
    url = (url or "").strip()
    if urllib.parse.urlsplit(url).scheme.lower() not in {"http", "https"}:
        raise TocScrapeError("Only http:// and https:// links are supported")
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": _USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
            "Accept-Language": "ru,en;q=0.8",
        },
    )
    opener = urllib.request.build_opener(_LimitedRedirects())
    try:
        with opener.open(request, timeout=TIMEOUT_SECONDS) as response:
            content_type = response.headers.get("Content-Type", "")
            if content_type and not _is_page(content_type):
                raise TocScrapeError(
                    "The link returned %s, not a web page" % content_type.split(";")[0].strip()
                )
            raw = response.read(MAX_BYTES + 1)
            charset = response.headers.get_content_charset()
    except TocScrapeError:
        raise
    except urllib.error.HTTPError as exc:
        raise TocScrapeError("The site answered %s %s" % (exc.code, exc.reason)) from exc
    except urllib.error.URLError as exc:
        raise TocScrapeError("Could not reach the site: %s" % (exc.reason,)) from exc
    except (TimeoutError, OSError, ValueError) as exc:
        raise TocScrapeError("Could not read the page: %s" % exc) from exc
    if len(raw) > MAX_BYTES:
        raise TocScrapeError("The page is larger than %d MB" % (MAX_BYTES // (1024 * 1024)))
    return _decode(raw, charset)
