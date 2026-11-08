"""Native EPUB 3 fixed-layout generation for comics.

The third serializer over the contract :mod:`maic._page_groups` produces, and
the smallest of the three: an EPUB is a ZIP of files a reader already knows how
to draw, so there is no container format to reconstruct the way _mobi_native
and _kfx_native have to.  What it buys is everything the shared pipeline does
-- selectable manga restoration, maic's crop, page-number cleanup, edit ops, the
1400x1920 render canvas, spread-aware pairing -- for a format that until now
could only be built by KCC.

The one real decision here is how a facing pair is expressed.  KFX and KF8 both
draw two images into one section, because that is the only thing their readers
understand.  EPUB has a vocabulary for it instead: each page stays its own
XHTML document and the spine says which side of the fold it falls on, so a
landscape screen shows the pair and a portrait screen shows one page.  maic
still decides *which* pages pair -- :func:`~maic._page_groups.pair_facing_pages`
reads the source's own bisected spreads to keep the parity the paper had -- and
only the drawing is left to the reader.

The file layout matches the one the C++ desktop's ``build_epub`` writes, so a
volume built by either side of maic unpacks the same way.
"""

import os
import zipfile

from ._page_groups import _image_format, _set_page_backgrounds
from .version import BUILD_STAMP

# Where the OPF lives, and what every href inside a page document is relative
# to.  Kept identical to native/src/volume_builder.cpp's layout.
_OPF_PATH = "OEBPS/content.opf"

_MIMETYPE = "application/epub+zip"

_CONTAINER_XML = (
    '<?xml version="1.0" encoding="utf-8"?>\n'
    '<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">\n'
    '  <rootfiles><rootfile full-path="' + _OPF_PATH + '" '
    'media-type="application/oebps-package+xml"/></rootfiles>\n'
    '</container>\n'
)

# No background here: maic picks one per page (auto/white/black, the same
# control KCC calls W/B margins) and writes it inline, so a book whose pages
# disagree does not need two stylesheets.
_STYLESHEET = (
    "html,body{margin:0;padding:0;width:100%;height:100%;}"
    "body{display:flex;align-items:center;justify-content:center;overflow:hidden;}"
    "img{display:block;width:100%;height:100%;object-fit:contain;}\n"
)

_PAGE_TEMPLATE = (
    '<?xml version="1.0" encoding="utf-8"?>\n'
    '<!DOCTYPE html>\n'
    '<html xmlns="http://www.w3.org/1999/xhtml">\n'
    '<head>'
    '<title>%(label)s</title>'
    '<meta name="viewport" content="width=%(width)d,height=%(height)d"/>'
    '<link rel="stylesheet" type="text/css" href="../styles.css"/>'
    '</head>'
    '<body style="background:%(background)s;">'
    '<img src="../images/%(id)s.%(ext)s" alt="%(label)s"/>'
    '</body></html>\n'
)

# EPUB wants the registered spelling, unlike the "image/jpg" kindlegen writes
# into a KF8 page's kindle:embed URI.
_MEDIA_TYPES = {"jpg": "image/jpeg", "png": "image/png", "gif": "image/gif"}

_BACKGROUNDS = {"white": "#ffffff", "black": "#000000"}

# "page-spread-left" and "page-spread-right" are in the package document's
# default vocabulary and take no prefix.  "page-spread-center" is not: it lives
# in the rendition vocabulary, which is why <package> declares that prefix.
_SPREAD_CENTER = "rendition:page-spread-center"


def xml_escape(text):
    """The five characters that cannot appear as themselves in XML text."""
    return (str(text if text is not None else "")
            .replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;").replace("'", "&apos;"))


def author_line(authors):
    """Every name on one line, which is what the other writers put out.

    A Kindle shows only the first creator, so a book with a separate
    ``<dc:creator>`` per name loses the translator credit -- the name a
    scanlation's readers actually look for.  build_native_kfx_book joins its
    author field for exactly this reason, and _comicinfo.AUTHOR_SEPARATOR is
    the separator both use: U+201A, which reads like a comma but cannot be
    confused with the commas inside a name.
    """
    from ._comicinfo import AUTHOR_SEPARATOR

    if not authors:
        return ""
    if isinstance(authors, (list, tuple)):
        names = [str(name).strip() for name in authors if str(name).strip()]
        return AUTHOR_SEPARATOR.join(names)
    return str(authors).strip()


def page_id(index):
    """The zero-padded stem a page's image and document share."""
    return "%05d" % (int(index) + 1)


def flatten(page_groups):
    """Sections -> a flat reading order, plus where each section starts.

    The spine is a list of documents, one per page, while a section can hold
    two of them.  Returns ``(pages, group_starts)`` with ``group_starts[i]``
    the flat index of section *i*'s first page.
    """
    pages, starts = [], []
    for group in page_groups:
        starts.append(len(pages))
        pages.extend(group)
    return pages, starts


def spine_properties(page_groups, righttoleft=True, facing_pages=True):
    """One spine property per page, in reading order.

    A two-page section is a facing pair -- either a bisected source spread or a
    pair :func:`~maic._page_groups.pair_facing_pages` made -- and its halves
    name the sides of the fold.  Which half is which follows the reading
    direction: in manga the page read first is the right one.

    With *facing_pages* on, single pages are pinned to the centre as well.
    Without that an odd page would hand the reader a spare slot and every pair
    after it would fall on the wrong side of the fold -- the parity maic just
    spent a whole pass getting right.

    With *facing_pages* off the reader is left to pair as it likes, which is
    what turning the option off asks for, and only a bisected spread is pinned:
    its halves were one drawing on paper and have to stay one on screen.
    """
    first, second = (("page-spread-right", "page-spread-left") if righttoleft
                     else ("page-spread-left", "page-spread-right"))
    out = []
    for group in page_groups:
        if len(group) == 2:
            out.extend((first, second))
        else:
            out.extend([_SPREAD_CENTER if facing_pages else ""] * len(group))
    return out


def content_uuid(title, page_groups, spine=None):
    """A stable UUID for ``dc:identifier``, hashed from the book's own content.

    Derived rather than random for the reason _mobi_native's ``content_asin``
    is: rebuilding an unchanged volume must not produce a book a library
    believes it has never seen.  *spine* is folded in because two books whose
    pages match can still read differently -- one paired, one not -- and a
    library treats one identifier as one book.

    Salted with the format so the same volume built as EPUB and as MOBI does
    not claim to be one book in two files.
    """
    import hashlib

    digest = hashlib.sha256()
    digest.update(b"epub\0")
    digest.update(str(title or "").encode("utf-8"))
    for group in page_groups:
        for page in group:
            digest.update(b"%d,%d,%d;" % (int(page["width"]), int(page["height"]),
                                          len(page["data"])))
    for item in spine or ():
        digest.update(str(item).encode("utf-8") + b";")
    raw = digest.hexdigest()[:32]
    return "%s-%s-%s-%s-%s" % (raw[:8], raw[8:12], raw[12:16], raw[16:20], raw[20:32])


def modified_time(now=None):
    """``dcterms:modified``, which EPUB 3 requires and pins to UTC seconds."""
    import time

    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now))


def page_xhtml(page, number):
    """One page's document.  *number* is its 1-based place in the book."""
    label = "Page %d" % int(number)
    background = _BACKGROUNDS.get(str(page.get("background_color") or ""), "#ffffff")
    return _PAGE_TEMPLATE % {
        "label": label,
        "width": int(page["width"]),
        "height": int(page["height"]),
        "background": background,
        "id": page_id(number - 1),
        "ext": _image_format(page["data"]),
    }


def build_nav(pages, entries, title):
    """The EPUB 3 navigation document.

    *entries* is the TOC already re-keyed to flat page indices.  An empty list
    is not an option -- a nav document with no items does not validate -- so a
    book whose source offered no chapters gets one entry per page, which is
    what the C++ builder falls back to as well.
    """
    listed = list(entries) or [(index, "Page %d" % (index + 1))
                               for index in range(len(pages))]
    out = ['<?xml version="1.0" encoding="utf-8"?>\n<!DOCTYPE html>\n'
           '<html xmlns="http://www.w3.org/1999/xhtml" '
           'xmlns:epub="http://www.idpf.org/2007/ops"><head><title>'
           + xml_escape(title) + '</title></head><body>'
           '<nav epub:type="toc" id="toc"><h1>' + xml_escape(title) + '</h1><ol>']
    for index, name in listed:
        out.append('<li><a href="pages/%s.xhtml">%s</a></li>'
                   % (page_id(index), xml_escape(name)))
    out.append('</ol></nav></body></html>\n')
    return "".join(out)


def build_ncx(pages, entries, title, identifier):
    """The EPUB 2 table of contents, for Calibre and older readers."""
    listed = list(entries) or [(index, "Page %d" % (index + 1))
                               for index in range(len(pages))]
    out = ['<?xml version="1.0" encoding="utf-8"?>\n'
           '<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">'
           '<head><meta name="dtb:uid" content="' + xml_escape(identifier) + '"/></head>'
           '<docTitle><text>' + xml_escape(title) + '</text></docTitle><navMap>']
    for order, (index, name) in enumerate(listed, start=1):
        out.append('<navPoint id="nav%d" playOrder="%d"><navLabel><text>%s</text>'
                   '</navLabel><content src="pages/%s.xhtml"/></navPoint>'
                   % (order, order, xml_escape(name), page_id(index)))
    out.append('</navMap></ncx>\n')
    return "".join(out)


def build_opf(pages, properties, *, title, authors=(), language="en",
              identifier="", reading_direction="rtl", series="",
              series_position="", publisher="", issue_date="",
              original_resolution=None, modified=None):
    """The package document: metadata, manifest and spine.

    *properties* is :func:`spine_properties`' output and has to be as long as
    *pages*; the first image is additionally the ``cover-image``, following the
    contract both other serializers already assume, that section 0 is the
    cover.

    *original_resolution* is the canvas the pages were rendered at.  Amazon's
    converter refuses a fixed-layout book without it -- ``E34002`` -- and that
    is what a Send-to-Kindle upload comes back as a bare "Failed".  The rest of
    the ``<meta name=...>`` block below is the same OPF2-style contract KCC
    writes and the C++ desktop's kindle_source profile writes: deprecated
    spelling, but it is what the converter reads.
    """
    if len(properties) != len(pages):
        raise ValueError("one spine property per page, got %d for %d pages"
                         % (len(properties), len(pages)))
    direction = "rtl" if str(reading_direction or "rtl").strip().lower() != "ltr" else "ltr"
    out = ['<?xml version="1.0" encoding="utf-8"?>\n'
           '<package xmlns="http://www.idpf.org/2007/opf" version="3.0" '
           'unique-identifier="book-id" '
           'prefix="rendition: http://www.idpf.org/vocab/rendition/#">'
           '<metadata xmlns:dc="http://purl.org/dc/elements/1.1/">'
           '<dc:identifier id="book-id">urn:uuid:' + xml_escape(identifier)
           + '</dc:identifier>'
           '<dc:title>' + xml_escape(title) + '</dc:title>'
           '<dc:language>' + xml_escape(language or "en") + '</dc:language>']
    creator = author_line(authors)
    if creator:
        out.append('<dc:creator>' + xml_escape(creator) + '</dc:creator>')
    # Who built the file, the way KCC names itself here and the way the KFX
    # writer puts "maic" in its audit metadata.
    out.append('<dc:contributor>' + xml_escape(BUILD_STAMP) + '</dc:contributor>')
    # Both optional in EPUB 3, and both only ever hold what the source said.
    # build_kfx_from_epub reads them back, so an EPUB that dropped them made
    # folder -> EPUB -> KFX lose a publisher folder -> KFX keeps; writing them
    # empty would be worse, overriding the KFX writer's own stamp with nothing.
    if str(publisher or "").strip():
        out.append('<dc:publisher>' + xml_escape(publisher) + '</dc:publisher>')
    if str(issue_date or "").strip():
        out.append('<dc:date>' + xml_escape(issue_date) + '</dc:date>')
    if str(series or "").strip():
        out.append('<meta property="belongs-to-collection" id="series">'
                   + xml_escape(series) + '</meta>')
        out.append('<meta refines="#series" property="collection-type">series</meta>')
        if str(series_position or "").strip():
            out.append('<meta refines="#series" property="group-position">'
                       + xml_escape(series_position) + '</meta>')
    out.append('<meta property="dcterms:modified">' + modified_time(modified) + '</meta>')
    if pages:
        # The library tile, named the OPF2 way. The EPUB3 spelling is the
        # manifest's cover-image property below; readers disagree about which
        # they honour, so the book carries both.
        out.append('<meta name="cover" content="img%s"/>' % page_id(0))
    width, height = original_resolution or (0, 0)
    if int(width) > 0 and int(height) > 0:
        out.append('<meta name="original-resolution" content="%dx%d"/>'
                   % (int(width), int(height)))
    out.append('<meta name="fixed-layout" content="true"/>'
               '<meta name="book-type" content="comic"/>'
               '<meta name="zero-gutter" content="true"/>'
               '<meta name="zero-margin" content="true"/>'
               '<meta name="ke-border-color" content="#FFFFFF"/>'
               '<meta name="ke-border-width" content="0"/>'
               '<meta name="orientation-lock" content="none"/>'
               '<meta name="region-mag" content="false"/>')
    out.append('<meta name="primary-writing-mode" content="%s"/>'
               % ("horizontal-rl" if direction == "rtl" else "horizontal-lr"))
    # A comic is one drawing per page and the pages differ in size, so the
    # layout is fixed and each document states its own viewport.  Spreads are
    # offered in landscape only: two manga pages across a portrait screen are
    # half the size for no gain.
    out.append('<meta property="rendition:layout">pre-paginated</meta>'
               '<meta property="rendition:orientation">auto</meta>'
               '<meta property="rendition:spread">landscape</meta>'
               '</metadata><manifest>'
               '<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" '
               'properties="nav"/>'
               '<item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>'
               '<item id="css" href="styles.css" media-type="text/css"/>')
    for index, page in enumerate(pages):
        stem = page_id(index)
        fmt = _image_format(page["data"])
        out.append('<item id="img%s" href="images/%s.%s" media-type="%s"%s/>'
                   % (stem, stem, fmt, _MEDIA_TYPES.get(fmt, "image/jpeg"),
                      ' properties="cover-image"' if index == 0 else ""))
        out.append('<item id="page%s" href="pages/%s.xhtml" '
                   'media-type="application/xhtml+xml"/>' % (stem, stem))
    out.append('</manifest><spine toc="ncx" page-progression-direction="%s">' % direction)
    for index in range(len(pages)):
        prop = properties[index]
        out.append('<itemref idref="page%s"%s/>'
                   % (page_id(index), ' properties="%s"' % prop if prop else ""))
    out.append('</spine></package>\n')
    return "".join(out)


def build_native_epub_book(page_groups, toc_entries, *, title="Untitled",
                           authors=(), language="en", reading_direction="rtl",
                           series="", series_position="", publisher="",
                           issue_date="", facing_pages=True,
                           original_resolution=None, modified=None, log_fn=None):
    """Sections -> the complete set of ZIP members, in the order they go in.

    Returns ``[(name, bytes, compress_type), ...]``.  Nothing touches the disk:
    :func:`write_epub` does that in one pass, so an interrupted build cannot
    leave half an EPUB behind.
    """
    _log = log_fn or (lambda message: None)
    if not page_groups:
        raise ValueError("the book has no pages")

    pages, _starts = flatten(page_groups)
    righttoleft = str(reading_direction or "rtl").strip().lower() != "ltr"
    properties = spine_properties(page_groups, righttoleft=righttoleft,
                                  facing_pages=facing_pages)
    flat_toc = []
    seen = set()
    for page_index, name in toc_entries or ():
        # The entry names a page, not the section holding it: a facing pair is
        # one section and two documents, and a chapter forced onto the far half
        # of one would otherwise open a page early.
        index = int(page_index)
        if not (0 <= index < len(pages)):
            continue
        key = (index, name)
        if key in seen:
            continue
        seen.add(key)
        flat_toc.append(key)

    identifier = content_uuid(title, page_groups, spine=properties)
    # Said out loud the way the KFX writer says its ASIN: a library keys on
    # this, so a rebuild that changed it is worth seeing in the log.
    _log("IDENTITY: urn:uuid:%s" % identifier)

    entries = [
        # The magic the format is recognised by: first in the archive and
        # stored, not deflated.
        ("mimetype", _MIMETYPE.encode("ascii"), zipfile.ZIP_STORED),
        ("META-INF/container.xml", _CONTAINER_XML.encode("utf-8"), zipfile.ZIP_DEFLATED),
        ("OEBPS/styles.css", _STYLESHEET.encode("utf-8"), zipfile.ZIP_DEFLATED),
    ]
    for index, page in enumerate(pages):
        stem = page_id(index)
        entries.append(("OEBPS/images/%s.%s" % (stem, _image_format(page["data"])),
                        page["data"], zipfile.ZIP_STORED))
        entries.append(("OEBPS/pages/%s.xhtml" % stem,
                        page_xhtml(page, index + 1).encode("utf-8"),
                        zipfile.ZIP_DEFLATED))
    entries.append(("OEBPS/nav.xhtml",
                    build_nav(pages, flat_toc, title).encode("utf-8"),
                    zipfile.ZIP_DEFLATED))
    entries.append(("OEBPS/toc.ncx",
                    build_ncx(pages, flat_toc, title, identifier).encode("utf-8"),
                    zipfile.ZIP_DEFLATED))
    entries.append((_OPF_PATH,
                    build_opf(pages, properties, title=title, authors=authors,
                              language=language, identifier=identifier,
                              reading_direction=reading_direction, series=series,
                              series_position=series_position,
                              publisher=publisher, issue_date=issue_date,
                              original_resolution=original_resolution,
                              modified=modified).encode("utf-8"),
                    zipfile.ZIP_DEFLATED))

    paired = sum(1 for group in page_groups if len(group) == 2)
    _log("EPUB: %d documents in %d sections (%d hold a facing pair), %d TOC entries"
         % (len(pages), len(page_groups), paired, len(flat_toc)))
    return entries


def write_epub(out_path, entries):
    """Write the members to *out_path*, mimetype first and uncompressed.

    A JPEG is already compressed; deflating it again costs the whole book's
    worth of CPU to save nothing, so page images go in stored too.
    """
    with zipfile.ZipFile(out_path, "w") as archive:
        for name, data, compress_type in entries:
            archive.writestr(zipfile.ZipInfo(name), data, compress_type=compress_type)
    return out_path


def build_epub_from_dir(
    source_dir,
    out_path,
    *,
    title=None,
    authors=None,
    language=None,
    vol_prefix="Vol.",
    excluded=None,
    bookmarks=None,
    reading_direction=None,
    device_canvas="KPW12",
    hq=False,
    resize=False,
    no_padding=False,
    split_spreads=True,
    rotate_spreads=True,
    upscale=True,
    stretch=False,
    grayscale=False,
    page_format="jpg",
    mozjpeg=False,
    quality=85,
    borders_color="none",
    crop=True,
    margin_pct=0.6,
    watermarks=False,
    watermark_matches=None,
    nocrop=None,
    custom_crops=None,
    custom_splits=None,
    edit_ops=None,
    extra_margin=None,
    page_numbers=False,
    cleanup_method="lama",
    cleanup_padding=0,
    page_number_scope="",
    manga_upscale=0,
    scan_cleanup=False,
    facing_pages=True,
    force_spread_preview=True,
    spread_preview_mode=None,
    progress_fn=None,
    stop_requested_fn=None,
    log_fn=None,
):
    """Source folder -> EPUB 3 fixed layout, without KCC in the path.

    The sibling of build_mobi_from_dir in maic/_mobi_native.py and
    build_kfx_from_dir in maic/_kfx_native.py, argument for argument, minus the
    knobs an EPUB has no use for: there is no ``cde_type`` because nothing here
    claims to be a Kindle document, and no ``thumbnails`` because the format
    stores no page-flip strip.

    ``spread_preview_mode`` and its legacy boolean counterpart
    ``force_spread_preview`` are here, though they look Kindle-only.
    An EPUB sent through Send-to-Kindle arrives on the device as KFX, and the
    reader decides whether to offer its combined-spread button by comparing
    the pixels along the two inner edges -- the same test, reached by a
    different road.

    Nothing is written to *out_path* until the whole book is in memory: a stop
    request raises out of page_groups_from_dir before the archive is opened, so
    no partial file is ever left on disk.
    """
    _log = log_fn or (lambda message: None)

    from ._image_pipeline import device_canvas as _resolve_canvas

    device_canvas = _resolve_canvas(device_canvas, hq=hq)
    _log("DEVICE: canvas %dx%d" % device_canvas)

    # What Amazon's converter calls the original resolution: the canvas the
    # pages are built at, which page_groups_from_dir lifts above the screen for
    # the same reason the other two writers do. Without it the converter stops
    # at E34002 and Send-to-Kindle reports a bare "Failed".
    from ._image_pipeline import page_render_canvas

    render_canvas = page_render_canvas(device_canvas) if resize else device_canvas

    from ._comicinfo import read_comicinfo

    meta = read_comicinfo(source_dir, vol_prefix=vol_prefix)

    if (excluded is None or bookmarks is None or nocrop is None or watermark_matches is None or custom_crops is None
            or custom_splits is None or edit_ops is None or extra_margin is None):
        from .sidecar import load_sidecar

        sidecar = load_sidecar(source_dir)
        if excluded is None:
            excluded = sidecar.get("excluded") or ()
        if bookmarks is None:
            bookmarks = sidecar.get("bookmarks") or ()
        if nocrop is None:
            nocrop = list(sidecar.get("no-crop") or ())
        if watermark_matches is None and sidecar.get("_watermark-matches-saved"):
            watermark_matches = list(sidecar.get("watermark-matches") or ())
        if custom_crops is None:
            custom_crops = dict(sidecar.get("custom-crop") or {})
        if custom_splits is None:
            custom_splits = dict(sidecar.get("custom-split") or {})
        if edit_ops is None:
            edit_ops = dict(sidecar.get("edit-ops") or {})
        if extra_margin is None:
            extra_margin = dict(sidecar.get("extra-margin") or {})

    reading_direction = reading_direction or meta["reading_direction"]

    from ._page_groups import page_groups_from_dir

    page_groups, toc_entries = page_groups_from_dir(
        source_dir,
        excluded=excluded,
        bookmarks=bookmarks,
        comicinfo_bookmarks=meta["bookmarks"],
        canvas=device_canvas,
        resize=resize,
        no_padding=no_padding,
        upscale=upscale,
        stretch=stretch,
        grayscale=grayscale,
        page_format=page_format,
        mozjpeg=mozjpeg,
        # Which half of a spread is read first, so it has to follow the same
        # default the generator uses when nothing says otherwise: manga order.
        righttoleft=str(reading_direction or "rtl").strip().lower() != "ltr",
        split_spreads=split_spreads,
        rotate_spreads=rotate_spreads,
        force_spread_preview=force_spread_preview,
        spread_preview_mode=spread_preview_mode,
        quality=quality,
        borders_color=borders_color,
        crop=crop,
        margin_pct=margin_pct,
        watermarks=watermarks,
        watermark_matches=watermark_matches,
        nocrop=nocrop,
        custom_crops=custom_crops,
        custom_splits=custom_splits,
        edit_ops=edit_ops,
        extra_margin=extra_margin,
        page_numbers=page_numbers,
        cleanup_method=cleanup_method,
        cleanup_padding=cleanup_padding,
        page_number_scope=page_number_scope or str(source_dir),
        manga_upscale=manga_upscale,
        scan_cleanup=scan_cleanup,
        facing_pages=facing_pages,
        # EPUB stores no page-flip strip, so building one would be a 512px
        # resize and a re-encode on every page, thrown away.
        build_previews=False,
        # The cover is a spine document like any other and is also the
        # cover-image a library tile is drawn from.  Sizing it with the rest
        # keeps an outsized source cover from being the largest page in a book
        # whose every other page is one height.
        resize_cover=True,
        progress_fn=progress_fn,
        stop_requested_fn=stop_requested_fn,
        log_fn=_log,
    )

    title = title or meta["title"] or os.path.basename(str(source_dir).rstrip("/\\"))
    authors = authors or meta["authors"]
    language = language or meta["language"] or "en"

    # The existing W/B margins control is also KCC's page-background choice:
    # auto detects each source, while white/black force every page.  The
    # background belongs in the document even when no pixel padding was baked.
    _set_page_backgrounds(page_groups, borders_color, log_fn=_log)

    entries = build_native_epub_book(
        page_groups,
        toc_entries,
        title=title,
        authors=authors,
        language=language,
        reading_direction=reading_direction,
        series=meta["series"],
        series_position=meta["volume"] or meta["number"],
        publisher=meta["publisher"],
        issue_date=meta["issue_date"],
        facing_pages=facing_pages,
        original_resolution=render_canvas,
        log_fn=_log,
    )
    write_epub(out_path, entries)
    size = sum(len(data) for _, data, _ in entries)
    _log("EPUB_OUT: %s (%d KB)" % (os.path.basename(out_path), size // 1024))
    return out_path
