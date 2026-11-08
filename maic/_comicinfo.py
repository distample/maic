"""ComicInfo.xml reading, shared by the KCC path and the native KFX path.

These functions used to live in ``routes_convert.py``, where only the EPUB
pipeline could reach them.  The native "KFX maic" build needs the same title,
author and chapter data straight from the source folder, and two parsers would
drift: the title a book gets would then depend on which output format was
picked, which is exactly the kind of difference nobody notices until a volume
is already on a device.

The title and author rules follow KCC's ``getMetadata``/``defaultTitle`` so
both paths label a book identically.
"""

import os
import xml.etree.ElementTree as ET
from datetime import date
from typing import Any

# ComicInfo <Manga> values.  Only "YesAndRightToLeft" states a direction; "Yes"
# says the book is manga without saying which way it pages, so it stays unknown
# and the caller's own setting decides.
_MANGA_DIRECTION = {
    "yesandrighttoleft": "rtl",
    "no": "ltr",
}

# Several names go into one author line rather than several: the Kindle shows
# only the first creator, so maic merges them for every format except MOBI.
# The separator is U+201A, which sorts and displays like a comma but does not
# collide with the commas inside a name.
AUTHOR_SEPARATOR = "‚ "


def xml_local_name(tag: object) -> str:
    text = str(tag)
    return text.split("}", 1)[1] if "}" in text else text


def comicinfo_xml_path_for_source(source: str) -> str:
    """Where a source's ComicInfo.xml lives -- inside a folder, or beside a file.

    Returns the first existing candidate, or the most likely one so callers can
    report a path even when nothing is there.
    """
    source_path = source.rstrip("/\\")
    candidates: list[str] = []
    if os.path.isdir(source_path):
        candidates.append(os.path.join(source_path, "ComicInfo.xml"))
        parent = os.path.dirname(source_path)
        if parent and parent != source_path:
            candidates.append(os.path.join(parent, "ComicInfo.xml"))
    else:
        base_dir = os.path.dirname(source_path)
        if base_dir:
            candidates.append(os.path.join(base_dir, "ComicInfo.xml"))
            parent = os.path.dirname(base_dir.rstrip("/\\"))
            if parent and parent != base_dir:
                candidates.append(os.path.join(parent, "ComicInfo.xml"))
    for path in candidates:
        if os.path.isfile(path):
            return path
    if candidates:
        return candidates[0]
    return os.path.join(os.path.dirname(source_path), "ComicInfo.xml")


def field_values(root: ET.Element, name: str) -> list[str]:
    values: list[str] = []
    for elem in root.iter():
        if xml_local_name(elem.tag) != name:
            continue
        value = (elem.text or "").strip()
        if value:
            values.append(value)
    return values


def split_people(value: str) -> list[str]:
    normalized = value.replace(";", ",")
    return [part.strip() for part in normalized.split(",") if part.strip()]


def is_translator_like(value: str) -> bool:
    text = value.strip().casefold()
    return text.startswith("translator") or text.startswith("translation") or text.startswith("перевод")


def read_embedded_title_author(source: str) -> tuple[str, str]:
    """Metadata carried inside an archive, for sources with no ComicInfo.xml."""
    if not os.path.isfile(source):
        return "", ""
    try:
        from kindlecomicconverter import metadata as kcc_metadata

        meta = kcc_metadata.MetadataParser(source)
    except Exception:
        return "", ""

    title = str(meta.data.get("Title", "") or "").strip()
    people: list[str] = []
    seen: set[str] = set()
    for field in ("Writers", "Pencillers", "Inkers", "Colorists"):
        for person in meta.data.get(field, []):
            text = str(person or "").strip()
            if not text:
                continue
            key = text.casefold()
            if key in seen:
                continue
            seen.add(key)
            people.append(text)

    regular = [person for person in people if not is_translator_like(person)]
    translators = [person for person in people if is_translator_like(person)]
    return title, ", ".join(regular + translators)


def issue_date_from_parts(year: str, month: str, day: str) -> str:
    """ComicInfo's Year/Month/Day as the ISO date Kindle metadata carries.

    Every store KFX writes a full ``issue_date`` ("2023-03-01"), so a source
    that names only a year is padded to the first of January rather than
    shortened.  A source with no year names no point in time at all, and
    inventing one would put a fact in the book that nobody put in the source.
    """
    if not year.strip().isdigit():
        return ""
    try:
        return date(
            int(year), int(month) if month.strip().isdigit() else 1,
            int(day) if day.strip().isdigit() else 1,
        ).isoformat()
    except ValueError:
        return ""


def empty_metadata() -> dict[str, Any]:
    return {
        "title": "",
        "authors": [],
        "series": "",
        "volume": "",
        "number": "",
        "raw_title": "",
        "language": "",
        "publisher": "",
        "issue_date": "",
        "reading_direction": None,
        "bookmarks": [],
    }


def metadata_from_root(root: ET.Element, vol_prefix: str = "Vol.") -> dict[str, Any]:
    """Everything the two pipelines need out of one parsed ComicInfo tree."""
    # Title from Series/Volume/Number/Title, the same shape as KCC's defaultTitle.
    series_values = field_values(root, "Series")
    volume_values = field_values(root, "Volume")
    number_values = field_values(root, "Number")
    title_values = field_values(root, "Title")

    series = series_values[0] if series_values else ""
    volume = volume_values[0] if volume_values else ""
    number = number_values[0] if number_values else ""
    raw_title = title_values[0] if title_values else ""

    if series:
        title = series
        suffix = ""
        if volume:
            # Preserve volume formatting from ComicInfo; avoid forced zero-padding ("1" -> "01").
            suffix += ", " + vol_prefix + " " + volume
        if number:
            suffix += " #" + number.zfill(3)
        if raw_title:
            suffix += ": " + raw_title
        title = title + suffix
    else:
        title = raw_title

    all_parts: list[str] = []
    seen: set[str] = set()

    def _append_unique(value: str) -> None:
        text = value.strip()
        if not text:
            return
        key = text.casefold()
        if key in seen:
            return
        seen.add(key)
        all_parts.append(text)

    def _append_field_people(field_name: str) -> None:
        for raw_value in field_values(root, field_name):
            if field_name == "Translator":
                # Keep all teams under the same translation credit. Splitting
                # them into authors would move later teams ahead of "Перевод:".
                _append_unique(AUTHOR_SEPARATOR.join(split_people(raw_value)))
                continue
            for person in split_people(raw_value):
                _append_unique(person)

    # Base author priority: Writer, then explicit Author, then other creator roles.
    _append_field_people("Writer")
    _append_field_people("Author")
    _append_field_people("Penciller")
    _append_field_people("Inker")
    _append_field_people("Colorist")
    _append_field_people("Letterer")
    _append_field_people("CoverArtist")
    _append_field_people("Translator")

    # Translator-like entries (e.g. "Translator: Japit Comics" stored in Writer field)
    # must always come after real authors regardless of field order in the source.
    regular = [p for p in all_parts if not is_translator_like(p)]
    translators = [p for p in all_parts if is_translator_like(p)]

    def _first(field_name: str) -> str:
        values = field_values(root, field_name)
        return values[0] if values else ""

    language_values = field_values(root, "LanguageISO")
    manga_values = field_values(root, "Manga")

    # <Page Image="n" Bookmark="..."> is KCC's chapter source when maic has no
    # sidecar anchors; Image is a 0-based index into the page list.
    bookmarks: list[tuple[int, str]] = []
    for elem in root.iter():
        if xml_local_name(elem.tag) != "Page":
            continue
        label = str(elem.attrib.get("Bookmark", "") or "").strip()
        image = str(elem.attrib.get("Image", "") or "").strip()
        if not label or not image:
            continue
        try:
            bookmarks.append((int(image), label))
        except ValueError:
            continue

    return {
        "title": title,
        "authors": regular + translators,
        "series": series,
        "volume": volume,
        "number": number,
        "raw_title": raw_title,
        "language": language_values[0] if language_values else "",
        "publisher": _first("Publisher").strip(),
        "issue_date": issue_date_from_parts(
            _first("Year"), _first("Month"), _first("Day")),
        "reading_direction": _MANGA_DIRECTION.get(
            manga_values[0].strip().casefold() if manga_values else ""),
        "bookmarks": bookmarks,
    }


def read_comicinfo(source: str, *, vol_prefix: str = "Vol.") -> dict[str, Any]:
    """Read the ComicInfo.xml belonging to *source*, or empty metadata."""
    xml_path = comicinfo_xml_path_for_source(source)
    if not os.path.isfile(xml_path):
        return empty_metadata()
    try:
        root = ET.parse(xml_path).getroot()
    except Exception:
        return empty_metadata()
    return metadata_from_root(root, vol_prefix)


def read_title_author(source: str, vol_prefix: str = "Vol.") -> tuple[str, str]:
    """Title and joined author string, falling back to archive-embedded metadata."""
    xml_path = comicinfo_xml_path_for_source(source)
    if not os.path.isfile(xml_path):
        return read_embedded_title_author(source)
    try:
        root = ET.parse(xml_path).getroot()
    except Exception:
        return read_embedded_title_author(source)
    meta = metadata_from_root(root, vol_prefix)
    return meta["title"], ", ".join(meta["authors"])


def read_raw_title(source: str) -> str:
    """The bare <Title> field, without the series/volume decoration."""
    xml_path = comicinfo_xml_path_for_source(source)
    if not os.path.isfile(xml_path):
        return ""
    try:
        root = ET.parse(xml_path).getroot()
    except Exception:
        return ""
    title_values = field_values(root, "Title")
    return title_values[0] if title_values else ""
