"""The source walk the native KFX path uses instead of KCC's.

KCC decides three things before any image is touched: which files are pages,
what order they read in, and where a chapter starts.  Those decisions end up
baked into the EPUB, and the native path has to make the same ones -- step 4 of
the native-pipeline plan validates spread splitting by converting one volume
both ways and diffing the page lists, which only means anything if the lists
line up to begin with.

So this module deliberately mirrors ``comic2ebook.sanitizeTree``/``buildEPUB``
and the maic patches around them:

* files and directories sort with ``natsort``'s OS-like key -- KCC's
  ``OS_SORT_KEY`` -- so "Chapter 3.5" follows "Chapter 3" and "Chapter 10"
  follows "Chapter 9";
* images directly under the source root come before any chapter folder;
* a root ``cover.*`` is metadata, not a page (maic defers it, and the KFX side
  re-adds it as the first section);
* a root ``credits.*`` moves to the very end;
* chapter titles come from the original folder names, overridden by maic's
  sidecar bookmark anchors, which is what the UI actually edits.

Nothing here opens an image or imports KCC.
"""

import os
import zipfile

from ._image_pipeline import IMAGE_EXTS

_COVER_STEMS = {"cover"}
_CREDITS_STEMS = {"credits", "credit"}
_ZIP_CHAPTER_EXTS = {".zip", ".cbz"}
ARCHIVE_SEP = "||"

_OS_SORT_KEY = None


def _noop_log(msg):
    pass


def natural_key(name):
    """KCC's ``OS_SORT_KEY``: natsort's OS-like ordering.

    Sharing the key is the point -- a different tie-break would reorder pages
    against the KCC path, and the difference would only show up as a volume
    that reads out of order.
    """
    global _OS_SORT_KEY
    if _OS_SORT_KEY is None:
        from natsort import os_sort_keygen

        _OS_SORT_KEY = os_sort_keygen()
    return _OS_SORT_KEY(name)


def normalize_rel(rel):
    """Lower-cased, forward-slashed relative path, for comparing user input."""
    return str(rel or "").replace("\\", "/").strip("/").lower()


def rel_variants(rel, source_name=""):
    """Every spelling of *rel* a sidecar might carry.

    Sidecar paths are written by the UI relative to the source folder, but some
    entries arrive with the folder name still on the front, and archives that
    wrap their contents in a folder of the same name produce a doubled first
    segment.  Both are accepted rather than silently ignored.
    """
    norm = normalize_rel(rel)
    if not norm:
        return set()
    variants = {norm}
    base = normalize_rel(source_name)
    if base and norm.startswith(base + "/"):
        variants.add(norm[len(base) + 1:])
    parts = [p for p in norm.split("/") if p]
    if len(parts) >= 3 and parts[0] == parts[1]:
        variants.add("/".join([parts[0], *parts[2:]]))
    return variants


def is_image(name):
    return os.path.splitext(name.lower())[1] in IMAGE_EXTS


def _zip_image_names(path):
    """Image members of one ZIP/CBZ chapter, in KCC-compatible order."""
    from .path_access import is_safe_archive_internal_path

    try:
        with zipfile.ZipFile(path, "r") as archive:
            names = [
                info.filename.replace("\\", "/").lstrip("/")
                for info in archive.infolist()
                if (not info.is_dir() and is_image(info.filename)
                    and is_safe_archive_internal_path(info.filename))
            ]
    except (OSError, zipfile.BadZipFile, zipfile.LargeZipFile) as exc:
        raise ValueError("cannot read archived chapter %s: %s" % (path, exc)) from exc
    return sorted((name for name in names if name), key=natural_key)


def walk_source(root, *, excluded=(), log_fn=None):
    """Read a source folder into pages, chapters and a cover.

    Returns a dict with:

    ``pages``
        reading order, each ``{"path", "rel", "chapter"}``.  The cover is not
        in here; a root ``credits.*`` is, last.
    ``cover``
        ``{"path", "rel"}`` or None.
    ``chapters``
        ``{"rel", "name", "first_page"}`` per folder that still has pages,
        in reading order.  ``first_page`` indexes ``pages``.
    ``all_rels``
        every page's rel path *before* exclusions, in the same order.  TOC
        anchors need it: an anchor may point at a page the user excluded, and
        the label still has to land somewhere sensible.
    """
    log = log_fn or _noop_log
    source_name = os.path.basename(str(root).rstrip("/\\"))

    excluded_norm = set()
    for rel in excluded or ():
        excluded_norm.update(rel_variants(rel, source_name))

    pages = []
    chapters = []
    all_rels = []
    cover = None
    credits_page = None

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames.sort(key=natural_key)
        filenames.sort(key=natural_key)

        rel_dir = os.path.relpath(dirpath, root).replace("\\", "/")
        if rel_dir == ".":
            rel_dir = ""
        first_page = None

        for name in filenames:
            ext = os.path.splitext(name.lower())[1]
            if ext in _ZIP_CHAPTER_EXTS:
                archive_path = os.path.join(dirpath, name)
                chapter_name = os.path.splitext(name)[0]
                chapter_rel = "%s/%s" % (rel_dir, chapter_name) if rel_dir else chapter_name
                archive_first_page = None
                archive_pages = 0
                for internal in _zip_image_names(archive_path):
                    rel = "%s/%s" % (chapter_rel, internal)
                    all_rels.append(rel)
                    if normalize_rel(rel) in excluded_norm:
                        continue
                    if archive_first_page is None:
                        archive_first_page = len(pages)
                    pages.append({
                        "path": archive_path + ARCHIVE_SEP + internal,
                        "rel": rel,
                        "chapter": chapter_rel,
                    })
                    archive_pages += 1
                if archive_first_page is not None:
                    chapters.append({
                        "rel": chapter_rel,
                        "name": chapter_name,
                        "first_page": archive_first_page,
                    })
                log("SOURCE: archived chapter %s (%d pages)" % (chapter_rel, archive_pages))
                continue
            if ext not in IMAGE_EXTS:
                continue
            rel = "%s/%s" % (rel_dir, name) if rel_dir else name
            stem = os.path.splitext(name)[0].lower()

            # Root cover and credits are placed by hand, not by walk order.
            if not rel_dir and stem in _COVER_STEMS and cover is None:
                if normalize_rel(rel) not in excluded_norm:
                    cover = {"path": os.path.join(dirpath, name), "rel": rel}
                continue
            if not rel_dir and stem in _CREDITS_STEMS and credits_page is None:
                if normalize_rel(rel) not in excluded_norm:
                    credits_page = {
                        "path": os.path.join(dirpath, name), "rel": rel, "chapter": "",
                    }
                continue

            all_rels.append(rel)
            if normalize_rel(rel) in excluded_norm:
                continue
            if rel_dir and first_page is None:
                first_page = len(pages)
            pages.append({
                "path": os.path.join(dirpath, name), "rel": rel, "chapter": rel_dir,
            })

        if rel_dir and first_page is not None:
            chapters.append({
                "rel": rel_dir,
                "name": os.path.basename(rel_dir),
                "first_page": first_page,
            })

    chapters.sort(key=lambda chapter: chapter["first_page"])

    if credits_page is not None:
        all_rels.append(credits_page["rel"])
        pages.append(credits_page)

    log("SOURCE: %d pages, %d chapters%s"
        % (len(pages), len(chapters), ", cover" if cover else ", no cover"))
    return {
        "root": root,
        "pages": pages,
        "chapters": chapters,
        "cover": cover,
        "all_rels": all_rels,
    }


def _anchor_page_index(scan, rel_norm, rel_to_index):
    """Where a bookmark anchor lands, after exclusions moved things around.

    An excluded anchor falls forward to the next surviving page in the same
    folder, matching what the KCC path does; an anchor whose whole folder is
    gone has nowhere to land and is dropped.
    """
    index = rel_to_index.get(rel_norm)
    if index is not None:
        return index

    all_rels = [normalize_rel(r) for r in scan.get("all_rels", [])]
    try:
        start = all_rels.index(rel_norm)
    except ValueError:
        return None
    anchor_dir = os.path.dirname(rel_norm)
    for later in all_rels[start + 1:]:
        if os.path.dirname(later) != anchor_dir:
            continue
        index = rel_to_index.get(later)
        if index is not None:
            return index
    return None


def build_toc_entries(scan, *, bookmarks=(), comicinfo_bookmarks=(), log_fn=None):
    """``(page_index, title)`` pairs, from the best source available.

    Sidecar bookmark anchors first -- they are what the maic sidebar edits and
    they survive re-ordering because they name a file.  Then ComicInfo's
    ``<Page Bookmark>`` entries, which is what KCC falls back to.  Then one
    entry per chapter folder, which is KCC's default.
    """
    log = log_fn or _noop_log
    pages = scan.get("pages", [])
    rel_to_index = {}
    for index, page in enumerate(pages):
        rel_to_index.setdefault(normalize_rel(page["rel"]), index)

    source_name = os.path.basename(str(scan.get("root", "")).rstrip("/\\"))
    entries = []
    for bookmark in bookmarks or ():
        if not isinstance(bookmark, dict):
            continue
        rel = (bookmark.get("relPath") or bookmark.get("anchor_relpath")
               or bookmark.get("anchorRelPath") or "")
        title = str(bookmark.get("name") or bookmark.get("Bookmark")
                    or bookmark.get("title") or "").strip()
        if not rel or not title:
            continue
        index = None
        for variant in rel_variants(rel, source_name):
            index = _anchor_page_index(scan, variant, rel_to_index)
            if index is not None:
                break
        if index is None:
            log("TOC: skipped '%s', anchor not found (excluded or missing): %s" % (title, rel))
            continue
        entries.append((index, title))

    if not entries:
        for raw_index, title in comicinfo_bookmarks or ():
            try:
                index = int(raw_index)
            except (TypeError, ValueError):
                continue
            title = str(title or "").strip()
            if title and 0 <= index < len(pages):
                entries.append((index, title))

    if not entries:
        entries = [(c["first_page"], c["name"]) for c in scan.get("chapters", [])]

    seen = set()
    unique = []
    for index, title in sorted(entries, key=lambda item: item[0]):
        key = (index, title)
        if key in seen:
            continue
        seen.add(key)
        unique.append(key)
    return unique


def rekey_toc_entries(entries, page_to_book_page):
    """Re-key TOC entries from source page indices to book page indices.

    A source page the splitter cut in half becomes two pages of the book, and
    the cover shifts everything by one, so the mapping is not an offset.  What
    comes out counts pages of the finished book, cover first -- not sections:
    a chapter can open on the far half of a facing pair, and a section names
    only the half the pair begins with.
    """
    out = []
    seen = set()
    for page_index, title in entries or ():
        book_page = page_to_book_page.get(page_index)
        if book_page is None:
            continue
        key = (book_page, title)
        if key in seen:
            continue
        seen.add(key)
        out.append(key)
    return out
