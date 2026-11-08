"""Native joint MOBI6+KF8 generation for fixed-layout comics.

The on-disk entry point writes the two-part Palm database shape kindlegen
uses: a simple MOBI6 image book, shared resources, a ``BOUNDARY`` record, and
the modern fixed-layout KF8 book.  The fallback is useful on old readers, but
the joint wrapper also matters on current Kindle firmware: a standalone KF8
can parse correctly and still be refused by the device.

The shape it targets is the same one _kfx_native targets: an image-only
fixed-layout manga, where every page is one picture and there is no text at
all.  That is what keeps the flow layout tractable -- a page whose body is a
single container holds exactly one chunk, so the tag-boundary chunker that
dominates a general MOBI writer collapses into "take the body out".  It does
not collapse any further than that: a KF8 reader renders a page by splicing
its chunks back into a skeleton, so skeleton and chunk have to be genuinely
different byte ranges or the reconstruction produces a different book.

Validated structurally, against tools/mobi_unpack.py and against a
kindlegen-built volume via tools/mobi_native_spike.py.
"""

import base64
import os
import re
import struct
import time

from ._page_groups import _image_format, _set_page_backgrounds
from .version import BUILD_STAMP

# The window PalmDOC can reach back into, and the longest match it can encode.
_LZ_MAX_DISTANCE = 2047
_LZ_MAX_LENGTH = 10
_LZ_MIN_LENGTH = 3


def palmdoc_decompress(data):
    """PalmDOC LZ77 -> plain bytes.

    Raises ValueError on a record that cannot decode -- a back-reference
    reaching before the start of the output, a literal run claiming more
    bytes than remain, or a two-byte marker cut off by the end of the
    record.  This has to raise rather than return something plausible:
    Task 5 points this same function at a kindlegen-built file this
    project did not write, to diff our output against it, and garbage
    that decodes without complaint there would be misread as a
    difference in our writer instead of a bug in this decoder.

    The added checks are one comparison per control byte, not per byte
    copied -- cheap next to the copy loop itself, which runs unchecked.
    """
    out = bytearray()
    i, n = 0, len(data)
    while i < n:
        c = data[i]
        i += 1
        if c == 0x00:
            out.append(0)
        elif c <= 0x08:
            if i + c > n:
                raise ValueError(
                    f"literal run at offset {i - 1} claims {c} bytes but only "
                    f"{n - i} remain in the record"
                )
            out += data[i:i + c]
            i += c
        elif c <= 0x7F:
            out.append(c)
        elif c <= 0xBF:
            if i >= n:
                raise ValueError(
                    f"back-reference marker at offset {i - 1} is truncated -- "
                    "no second byte before the end of the record"
                )
            value = (c << 8) | data[i]
            i += 1
            distance = (value >> 3) & 0x07FF
            length = (value & 0x07) + _LZ_MIN_LENGTH
            start = len(out) - distance
            if start < 0:
                raise ValueError(
                    f"back-reference at offset {i - 2} reaches distance {distance} "
                    f"but only {len(out)} bytes have been produced so far"
                )
            for offset in range(length):
                out.append(out[start + offset])
        else:
            out.append(0x20)
            out.append(c ^ 0x80)
    return bytes(out)


def palmdoc_compress(data):
    """Plain bytes -> PalmDOC LZ77.

    Deliberately simple: the text of an image-only comic is a few hundred
    kilobytes of near-identical XHTML, so a naive search over the window costs
    nothing measurable and keeps the encoder readable.
    """
    out = bytearray()
    pending = bytearray()
    i, n = 0, len(data)

    def flush():
        while pending:
            chunk = bytes(pending[:8])
            del pending[:8]
            out.append(len(chunk))
            out.extend(chunk)

    while i < n:
        best_length, best_distance = 0, 0
        limit = min(_LZ_MAX_LENGTH, n - i)
        if limit >= _LZ_MIN_LENGTH:
            for start in range(max(0, i - _LZ_MAX_DISTANCE), i):
                length = 0
                while length < limit and data[start + length] == data[i + length]:
                    length += 1
                if length > best_length:
                    best_length, best_distance = length, i - start
                    if length == limit:
                        break
        if best_length >= _LZ_MIN_LENGTH:
            flush()
            value = 0x8000 | ((best_distance << 3) & 0x3FF8) | (best_length - _LZ_MIN_LENGTH)
            out += bytes(((value >> 8) & 0xFF, value & 0xFF))
            i += best_length
            continue

        c = data[i]
        i += 1
        if c == 0x20 and i < n and 0x40 <= data[i] <= 0x7F:
            flush()
            out.append(data[i] ^ 0x80)
            i += 1
        elif c == 0x00 or 0x09 <= c <= 0x7F:
            flush()
            out.append(c)
        else:
            pending.append(c)
            if len(pending) == 8:
                flush()
    flush()
    return bytes(out)


# --------------------------------------------------------------------------
# Markup: page_groups + toc_entries -> XHTML pages, a stylesheet, resources.
#
# Pure strings and bytes, no MOBI structure in sight -- everything here can
# be checked without a container to unpack.  The helper can draw a two-image
# section for callers testing markup in isolation.  The real KF8 container
# flattens facing groups first, because KCC represents them as separate
# skeletons joined by RESC rather than as a double-width XHTML page.
# --------------------------------------------------------------------------

_STYLESHEET = """\
html, body { margin: 0; padding: 0; }
body { text-align: left; }
div.page { position: relative; margin: 0; padding: 0; }
img.frame { position: absolute; top: 0; margin: 0; padding: 0; }
"""

# Once the real container has flattened the spine to one image per XHTML,
# absolute positioning and an explicit full-height wrapper buy nothing.  In
# Calibre they make every spine item overflow into a second, empty black
# viewport.  KCC's proven single-page shape keeps the image in normal flow.
_KCC_STYLESHEET = """\
@page { margin: 0; }
body { display: block; margin: 0; padding: 0; }
"""

# Transcribed character for character from a page pulled out of a working
# kindlegen-built volume (Aposimz-01.mobi), not reconstructed from a spec --
# see the "Page markup" section of docs/mobi-container-research.md.  The
# declaration, doctype, <html> and <head> sit on one line with no
# whitespace between them; kindlegen then joins the head's own children
# with "\r\n" rather than "\n", and closes straight from </head> into
# <body> and from </body> into </html> with no break at all.  <title>'s
# text is maic's own -- the bisection that tracked the chapter name down
# to this markup proved the title string itself is inert, and copying
# kindlegen's "kcc-NNNN-kcc-x" would only be pretending to be kindlegen.
#
# The container div's "top" percentage is kindlegen's vertical centering
# offset for an image shorter than its viewport.  Every image maic places
# here is rendered to exactly fill its page's viewport (the <meta> and the
# <img> share width and height), so that offset is always zero and kindlegen
# itself omits the property rather than writing "top:0%" -- confirmed by
# the one KCC page sampled with a full-bleed image, which carries
# ``style="text-align:center;"`` and nothing else.
_KCC_PAGE_TEMPLATE = (
    '<?xml version="1.0" encoding="UTF-8"?><!DOCTYPE html>'
    '<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">'
    '<head>\r\n'
    '<title>%(title)s</title>\r\n'
    '<link href="kindle:flow:0001?mime=text/css" type="text/css" rel="stylesheet"/>\r\n'
    '<meta name="viewport" content="width=%(width)d, height=%(height)d"/>\r\n'
    '</head><body style="%(background_style)s" aid="%(body_aid)s">\n'
    '<div style="text-align:center;" aid="%(div_aid)s">\n'
    '<div style="display:none;" data-AmznRemoved-M8="true" data-AmznRemoved="mobi7" aid="%(spacer_aid)s">.</div>\n'
    '<img width="%(width)d" height="%(height)d" src="kindle:embed:%(number)s?mime=%(mime)s"/>\n'
    '</div>\n'
    '</body></html>'
)

_PAGE_TEMPLATE = """\
<?xml version="1.0" encoding="utf-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
<meta name="viewport" content="width=%(width)d, height=%(height)d"/>
<link href="kindle:flow:0001?mime=text/css" rel="stylesheet" type="text/css"/>
</head>
<body aid="%(body_aid)s">
<div class="page" style="width:%(width)dpx;height:%(height)dpx;" aid="%(div_aid)s">
%(images)s
</div>
</body>
</html>
"""

_IMAGE_TEMPLATE = ('<img class="frame" '
                   'src="kindle:embed:%(number)s?mime=%(mime)s" '
                   'style="left:%(left)dpx;width:%(width)dpx;height:%(height)dpx;"/>')

# "image/jpg" is not the registered spelling and is what kindlegen writes
# anyway -- every page of a KCC-built volume carries
# ``kindle:embed:0002?mime=image/jpg``.  A reader that matches the string
# rather than sniffing the bytes would find nothing behind "image/jpeg", and
# a page whose image does not resolve renders as the viewport's background
# and nothing else.  Convergence on the working reference beats being right
# about IANA here.
_MIME = {"jpg": "image/jpg", "png": "image/png", "gif": "image/gif"}

# The selector a chunk names its owning element by, and the ``aid`` attribute
# that element has to carry for the name to resolve.  Both spellings are
# transcribed, not inferred.  calibre builds the string as
# ``"{}-//*[@aid='{}']"`` (writer8/skeleton.py), with the leading letter being
# 'P' for a chunk produced while inside the element and 'S' for one produced
# after it closed; every chunk maic writes is the inside of a page's <body>,
# so all of them are 'P'.  KindleUnpack reads the aid back out of that same
# CNCX string as ``idtext[12:-2]`` (lib/mobi_k8proc.py) -- a slice that lands
# on the aid only for exactly this twelve-character prefix and two-character
# suffix, which pins the spelling from the reading side too.
#
# **The element named is the one the chunk is spliced back INTO, not the
# chunk's own outermost tag.**  Read straight out of the kindlegen-built
# Aposimz-01.mobi by tools/mobi_native_spike.py: page 0's body is aid="0" and
# its selector is ``P-//*[@aid='0']`` while the chunk's own div is aid="1";
# page 1's chunk div is aid="UGI1" and the selector is ``P-//*[@aid='UGI0']``,
# its body.  Naming the chunk's own element instead reads back perfectly and
# points a device at the wrong node.
#
# calibre also re-sets the attribute purely to move it (``kindlegen always
# puts the aid last``), which is why it sits at the end of the tag below.
_CHUNK_SELECTOR = "P-//*[@aid='%s']"

# The alphabet a kindle:embed/kindle:flow URI counts in.  Verified against
# KindleUnpack's toBase32/fromBase32 (lib/mobi_utils.py): digits 0-9 then
# the letters A-V, 32 symbols in all, and a resource's number is 1-based --
# KindleUnpack looks one up as ``self.rscnames[imageNumber - 1]``.
_BASE32_ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUV"


def _resource_number(index):
    """The base32 string a kindle:embed URI carries for resource *index*.

    Matches KindleUnpack's ``toBase32(value, npad=4)`` exactly: zero-padded
    to four characters when the value fits in them, but not truncated when
    it does not.  A fixed four-iteration encoder would silently drop a
    resource's true identity past 32**4 images -- no real manga volume gets
    there, but there is no reason to encode it wrong anyway.
    """
    return _base32(index).rjust(4, "0")


def _base32(value):
    """A non-negative integer in the 32 digits this format counts in."""
    digits = ""
    while value:
        value, remainder = divmod(value, 32)
        digits = _BASE32_ALPHABET[remainder] + digits
    return digits or "0"


def _aid(counter):
    """The ``aid`` the *counter*-th aided element in the book carries.

    Base32 straight off a counter and *not* zero-padded, which is calibre's
    ``to_base(aidbase + j, base=32)`` with no minimum width -- the same 32
    digits ``_resource_number`` counts in, but padded there and not here.
    The two only look alike: one is a resource number inside a URI, this is
    an element's identity within the book.

    The counter runs over *elements*, not pages, and it is global to the
    book: kindlegen numbers a page's <body> and then everything inside it,
    so page 0 gets aids 0 and 1 and page 1 gets 2 and 3.  Nothing downstream
    re-derives an aid from a page number any more -- ``build_flow`` reads the
    body's aid back out of the markup it is handed -- so the numbering here
    only has to be unique and in kindlegen's order.
    """
    return _base32(counter)


def build_markup(page_groups, toc_entries, reading_direction="rtl",
                 kcc_single_pages=False):
    """Sections -> (XHTML per section, one stylesheet, resource blobs).

    A section holding two pages is drawn as one page of double width.  Under
    ``rtl`` the page that reads first sits on the
    right, which is the whole point of the pairing: reading order is
    reversed into *draw* order first, and x-offsets are then accumulated
    over draw order, each page claiming exactly its own width.  Reusing the
    natural-order offsets and only swapping which page occupies each one
    would misplace both pages whenever the pair's two widths differ -- the
    offsets would still be sized for the page that no longer sits there.

    *toc_entries* is accepted but not consulted here -- it names sections for
    the NCX the container builds later, and has nothing to add to a page's
    own markup.

    Each page carries two ``aid`` attributes, one on its <body> and one on
    its container div, from a single counter running across the whole book
    in kindlegen's order: the body first, then what is inside it.  Both are
    needed and they are needed for different reasons.  The div's is what the
    chunk's own markup is identified by; the **body's** is what the FRAG
    index's CNCX selector names, because a chunk is named by the element it
    is spliced back into rather than by its own outermost tag -- read out of
    a kindlegen-built volume, where page 0's chunk is a div with aid="1" and
    its selector is ``P-//*[@aid='0']``, the body.  Without an aid on the
    body there is nothing for that selector to resolve to.

    kindlegen puts an aid on every tag in its own recognised set; maic puts
    one on the two elements the container actually refers to, and leaves the
    images bare rather than emitting identities nothing dereferences.

    Returns the resource list in the order the container must store it, so a
    resource's position in the list is its ``kindle:embed`` number minus one.
    """
    if kcc_single_pages:
        pages, resources = [], []
        for page_index, group in enumerate(page_groups):
            if len(group) != 1:
                raise ValueError("KCC-style KF8 markup requires one image per page")
            page = group[0]
            background = str(page.get("background_color") or "black").lower()
            if background not in {"black", "white"}:
                raise ValueError("unsupported page background: %r" % background)
            # calibre/kindlegen reserve a million aid values for each source
            # spine item. The values need only be unique, but keeping that
            # namespace makes selectors conventional for the Kindle renderer
            # as well as merely resolvable by unpackers.
            aid_counter = page_index * 1000000
            resources.append(page["data"])
            pages.append(_KCC_PAGE_TEMPLATE % {
                "title": "page_%05d" % page_index,
                "width": int(page["width"]),
                "height": int(page["height"]),
                "number": _resource_number(len(resources)),
                "mime": _MIME.get(_image_format(page["data"]), "image/jpeg"),
                "body_aid": _aid(aid_counter),
                "div_aid": _aid(aid_counter + 1),
                # kindlegen aids the hidden spacer too, three to a page
                # where maic had two.  An aid is what makes an element
                # addressable at all in KF8, where a position is written
                # pos:fid:off, so how many a page carries is how finely the
                # page can be pointed at.
                "spacer_aid": _aid(aid_counter + 2),
                # Keep the user's choice true even under a dark reader theme.
                "background_style": "background-color:#%s;" % (
                    "000000" if background == "black" else "FFFFFF"),
            })
        return pages, _KCC_STYLESHEET, resources

    rtl = str(reading_direction or "rtl").strip().lower() != "ltr"
    pages, resources = [], []
    aid_counter = 0

    for group in page_groups:
        total_width = sum(int(page["width"]) for page in group)
        height = max(int(page["height"]) for page in group)

        # Resource numbers are handed out in reading order, independent of
        # how the pair is later drawn -- resource 1 is always the page that
        # reads first, on either a manga or a Western volume.
        numbered = []
        for page in group:
            resources.append(page["data"])
            numbered.append((len(resources), page))

        # Manga: the page that reads first is drawn last (rightmost), so the
        # pair is reversed into draw order before any x-offset is worked out.
        draw_order = list(reversed(numbered)) if (rtl and len(numbered) == 2) else numbered

        placed = []
        left = 0
        for number, page in draw_order:
            placed.append((number, left, page))
            left += int(page["width"])

        images = "\n".join(
            _IMAGE_TEMPLATE % {
                "number": _resource_number(number),
                "mime": _MIME.get(_image_format(page["data"]), "image/jpeg"),
                "left": left_px,
                "width": int(page["width"]),
                "height": int(page["height"]),
            }
            for number, left_px, page in placed
        )
        pages.append(_PAGE_TEMPLATE % {
            "width": total_width, "height": height, "images": images,
            "body_aid": _aid(aid_counter), "div_aid": _aid(aid_counter + 1)})
        aid_counter += 2

    return pages, _STYLESHEET, resources


def _flatten_kf8_spine(page_groups, toc_entries, reading_direction="rtl",
                       alternate_spreads=False):
    """One image per KF8 skeleton, plus its synthetic-spread side.

    ``page_groups`` is shared with KFX and deliberately groups a facing pair
    into one section.  KF8 does not represent that pair as two images inside
    one XHTML page.  kindlegen writes two skeletons and keeps the relationship
    in RESC's OPF spine as ``page-spread-right`` / ``page-spread-left``.

    A one-page group stands on its own.  That covers the book cover, a
    landscape page, a chapter opener and an unpaired tail.  A two-page group
    is a real or requested facing pair and gets the two physical sides in
    reading order.  With ``alternate_spreads`` a lone page states the leading
    side as well, so the spine starts a fresh spread at it and leaves the
    facing slot empty rather than filling it with the next page.  The TOC
    arrives keyed to pages, and one page is one skeleton, so a target needs
    no moving -- including a chapter that opens on the far half of a pair.
    """
    rtl = str(reading_direction or "rtl").strip().lower() != "ltr"
    pair_sides = ("right", "left") if rtl else ("left", "right")
    flat, properties = [], []
    for group_index, group in enumerate(page_groups):
        if not group:
            raise ValueError("page group %d is empty" % group_index)
        if len(group) > 2:
            raise ValueError(
                "page group %d holds %d pages; KF8 supports at most a facing pair"
                % (group_index, len(group))
            )
        # A two-page group is a real spread, cut in half, and its halves
        # belong on stated sides whether or not synthetic pairing is on.  With
        # pairing on, a section holding a single page states the leading side
        # too: two of those in a row is how the spine says "start a fresh
        # spread here", and it is what keeps the cover -- and a chapter's own
        # odd page -- off the same screen as the page that follows it.
        if len(group) == 2:
            sides = pair_sides
        elif alternate_spreads:
            sides = (pair_sides[0],) * len(group)
        else:
            sides = (None,) * len(group)
        for page, side in zip(group, sides):
            flat.append([page])
            properties.append(None if side is None else "page-spread-%s" % side)

    # The sides above are the whole of it.  They used to be thrown away here
    # and replaced by a plain alternation from the first page on, which reads
    # the same for a book that is nothing but pairs and wrongly for every
    # other: it put the cover and page one on one spread, and left every pair
    # after a single-page section a page out of step with the sections the KFX
    # build draws from the same groups -- the two containers then showed the
    # same volume paired two different ways.
    #
    # What is never written is "page-spread-center": that is not a value the
    # spine vocabulary has -- EPUB spells the centred case
    # "rendition:page-spread-center", and bare
    # left and right are the only two unprefixed spellings.  A KCC volume of
    # this same source carries 88 rights and 87 lefts and not one centre,
    # while ours carried 173 centres, which is a spine a strict parser has
    # every reason to throw away whole.
    #
    # What that costs shows up on the device.  With no spine there are no
    # pages to count, so locations fall back to bytes: 665 of them for our
    # 99672 bytes at the usual 150 each, against 176 for a KCC volume of 175
    # pages.  A book whose positions are bytes has no page to hang a chapter
    # on either, which is why the reader menu named no chapter.
    moved_toc = []
    for page_index, title in toc_entries or ():
        index = int(page_index)
        if index < 0 or index >= len(flat):
            raise ValueError(
                "TOC entry %r points outside %d pages"
                % (title, len(flat))
            )
        moved_toc.append((index, title))

    # Keep the cover outside chapter one when the source TOC starts on the
    # page after it. Earlier builds pulled the first target back to skeleton
    # zero while diagnosing a missing reader-footer label. NCX TBS turned out
    # to be the missing mechanism; with that map present, inventing a chapter
    # target on the cover only makes Kindle display "Chapter 1" one location
    # too early.
    return flat, moved_toc, properties


_MOBI6_PREFIX = b"<html><head><guide></guide></head><body>"
_MOBI6_SUFFIX = b"</body></html>"


def build_mobi6_markup(spine_groups):
    """Build the compatibility half's image-only HTML and page positions.

    MOBI6 has no fixed-layout spine.  Kindlegen's fallback represents every
    page as an image followed by ``mbp:pagebreak`` and addresses images by a
    one-based decimal ``recindex``.  The returned offsets name the opening
    ``div`` of every page and are therefore suitable for NCX tag 1.
    """
    parts = [bytearray(_MOBI6_PREFIX)]
    starts = []
    position = len(_MOBI6_PREFIX)
    for index, group in enumerate(spine_groups, 1):
        if len(group) != 1:
            raise ValueError("MOBI6 compatibility pages must contain one image")
        page = group[0]
        starts.append(position)
        fragment = (
            '<div align="center"><img width="%d" height="%d" '
            'recindex="%05d"/></div><mbp:pagebreak/>'
            % (int(page["width"]), int(page["height"]), index)
        ).encode("ascii")
        parts.append(bytearray(fragment))
        position += len(fragment)
    parts.append(bytearray(_MOBI6_SUFFIX))
    return b"".join(bytes(part) for part in parts), starts


def build_resc(spread_properties, reading_direction="rtl", modified=None):
    """Build the KF8 RESC resource carrying the reconstructed OPF spine.

    The binary envelope is copied from kindlegen output and agrees across the
    KCC books used as references::

        RESC | header-size=16 | version=1 | descriptor-size
             | size=<base32 XML bytes>&version=1&type=1 | XML

    ``skelid`` is the zero-based SKEL entry, which is the part a reader uses
    to connect an itemref back to reconstructed XHTML.  ``idref`` only has to
    be unique because a RESC omits the manifest it originally referred to.
    """
    import datetime
    import struct

    direction = "ltr" if str(reading_direction or "rtl").strip().lower() == "ltr" else "rtl"
    if modified is None:
        modified = datetime.datetime.now(datetime.timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ")

    items = []
    for skelid, prop in enumerate(spread_properties):
        # None means the item states no side at all, which is the only valid
        # way to say "do not pair this page".  "page-spread-center" is not in
        # the vocabulary -- EPUB spells that case
        # "rendition:page-spread-center" -- and writing it put an unknown
        # value on almost every item of the spine.
        if prop is None:
            items.append('<itemref idref="page_%05d" linear="yes" skelid="%d"/>'
                         % (skelid, skelid))
            continue
        prop = str(prop)
        if prop not in {"page-spread-left", "page-spread-right"}:
            raise ValueError("unsupported KF8 page spread property: %r" % prop)
        items.append(
            '<itemref idref="page_%05d" linear="yes" properties="%s" skelid="%d"/>'
            % (skelid, prop, skelid)
        )

    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<metadata xmlns:opf="http://www.idpf.org/2007/opf" '
        'xmlns:dc="http://purl.org/dc/elements/1.1/" '
        'xmlns="http://www.idpf.org/2007/opf">'
        '<meta property="dcterms:modified">%s</meta>'
        '<meta name="cover" content="cover"/>'
        '<meta name="ke-border-color" content="#FFFFFF"/>'
        '<meta name="ke-border-width" content="0"/>'
        '<meta property="rendition:spread">landscape</meta>'
        '<meta property="rendition:layout">pre-paginated</meta>'
        '</metadata>'
        '<spine page-progression-direction="%s" toc="ncx">%s</spine>'
    ) % (modified, direction, "".join(items))
    xml_bytes = xml.encode("utf-8")
    descriptor = (
        "size=%s&version=1&type=1" % _base32(len(xml_bytes))
    ).encode("ascii")
    return (b"RESC" + struct.pack(">III", 16, 1, len(descriptor))
            + descriptor + xml_bytes)


# --------------------------------------------------------------------------
# Flow: XHTML pages + stylesheet -> one byte stream, an FDST map, and a page
# index into it.
#
# KF8 keeps the stylesheet inside the same stream as the markup and tells
# them apart with FDST rather than storing it as a separate resource; maic
# follows suit and puts the stylesheet in flow 1.
#
# The part of this that is not obvious, and that maic got wrong until a
# kindlegen-built volume was diffed against it, is what a skeleton and a
# chunk actually are.  **A reader does not read a page out of the stream
# whole.**  It takes the skeleton, splices each of the page's chunks back in
# at the position the FRAG index records, and renders the result.  So the
# two cannot cover the same bytes: read out of Aposimz-01.mobi, kindlegen's
# skeleton 0 is the page *with its body emptied* and chunk 0 is the body
# content that was taken out, and they lie interleaved in the stream --
# skeleton 0, chunk 0, skeleton 1, chunk 1, and so on.
#
# Splitting the stream into text records is normally the fiddliest part of a
# MOBI writer, because a general KF8 chunker has to find a tag boundary near
# every 4096-byte mark so a chunk never straddles an HTML tag.  A comic page
# needs no such search: its body is one container of images, so the whole
# body is one chunk and there is exactly one split point per page.
# --------------------------------------------------------------------------

TEXT_RECORD_SIZE = 4096


class Chunk:
    """One piece of a page's body, and where a reader splices it back in.

    ``insert`` is an **absolute** position in the text stream: the byte in
    the owning skeleton at which this chunk's bytes belong, which for a page
    whose whole body is one chunk is exactly where ``</body>`` begins.  It is
    also what the FRAG index uses as the entry's name.

    ``offset`` is emphatically *not* absolute, and this is the pair that
    reads plausibly either way round.  It is the chunk's offset within its
    own skeleton's chunk area -- the run of bytes immediately after that
    skeleton -- so the first chunk of every page has offset 0.  FRAG tag 6 is
    ``(offset, length)``, and a reader recovers the bytes as
    ``text[s_start + s_len + offset : ... + length]``.  Read absolutely
    instead, a plausible-looking number lands in the middle of a later page.

    ``aid`` is the identity of the element the chunk is spliced *into* -- the
    page's <body> -- because that is what the FRAG CNCX selector names.
    """

    def __init__(self, insert, offset, length, aid):
        self.insert = insert
        self.offset = offset
        self.length = length
        self.aid = aid


class Skeleton:
    """One XHTML page with its body emptied, and its place in the stream.

    ``start`` and ``length`` describe the *skeleton*, not the page: the page
    is longer than the skeleton by exactly the chunks that were taken out of
    it, and those sit after it rather than inside it.  SKEL tag 6 is this
    pair, absolute in the text.

    ``chunk_count`` is derived rather than stored so that the SKEL index and
    the FRAG index cannot disagree about how many chunks a page has -- SKEL
    declares the count and FRAG writes the entries, and a reader that
    believed a count larger than the entries would read another page's.
    """

    def __init__(self, index, name, start, length, chunks=(), body_offset=0):
        self.index = index
        self.name = name
        self.start = start
        self.length = length
        self.chunks = list(chunks)
        # Where <body opens inside this skeleton.  The table of contents
        # points there rather than at the skeleton's first byte, which is
        # the XML declaration and not a position a reader can resolve.
        self.body_offset = body_offset

    @property
    def chunk_count(self):
        return len(self.chunks)


class Flow:
    """The concatenated byte stream, its FDST flow table, and its skeletons."""

    def __init__(self, text, flows, skeletons):
        self.text = text
        self.flows = flows
        self.skeletons = skeletons


# Where a page comes apart.  The skeleton is everything up to and including
# the <body> open tag plus the </body>...</html> tail; the chunk is what sat
# between them.  Searching the markup rather than splitting the template on a
# marker is what makes the aid in the CNCX selector provably the aid in the
# markup: both come out of the same bytes.
_BODY_OPEN = re.compile(rb"<body\b[^>]*>")
_BODY_AID = re.compile(rb'\baid="([^"]*)"')
_BODY_CLOSE = b"</body>"


def _split_body(encoded):
    """A page's bytes -> (where <body opens, start of its content, end of it, aid).

    The first of those is what the table of contents points at.  A chapter
    named by the first byte of its page names the XML declaration, which is
    not a place a reader can put a cursor -- kindlegen names the ``<body``
    tag instead, 323 bytes into a 360-byte skeleton in the reference volume,
    which is exactly where its own ``<body`` begins.

    Everything is refused rather than guessed at, because each of these has a
    plausible wrong answer.  A page with no <body> would otherwise become a
    skeleton covering the whole page and a chunk of nothing, which is the
    shape this module used to write and which no reader can reconstruct.  A
    body with no ``aid`` would produce a FRAG selector resolving to no
    element at all, and nothing downstream reads the selector back.
    """
    opening = _BODY_OPEN.search(encoded)
    if opening is None:
        raise ValueError("a page with no <body> cannot be split into a "
                         "skeleton and a chunk")
    aid = _BODY_AID.search(opening.group())
    if aid is None:
        raise ValueError(
            "the <body> of a page carries no aid, so the chunk spliced into "
            "it would have nothing for its selector to name")
    close = encoded.rfind(_BODY_CLOSE)
    if close < opening.end():
        raise ValueError("a page whose <body> is never closed cannot be split")
    if close == opening.end():
        raise ValueError("a page with an empty <body> has no chunk to splice")
    return (opening.start(), opening.end(), close,
            aid.group(1).decode("ascii"))


def build_flow(pages, stylesheet):
    """XHTML pages and a stylesheet -> one byte stream, plus its map.

    Every page is taken apart before it is laid down.  Its skeleton -- the
    page with its body emptied -- goes into the stream first, then that
    page's chunk, then the next page's skeleton, so the stream is interleaved
    rather than page after page.  That is the layout kindlegen writes and,
    more to the point, it is the layout the recorded geometry describes: FRAG
    tag 6's offset is measured from the end of the owning skeleton, so a
    chunk that did not sit immediately after its own skeleton would be read
    out of whatever did.

    Each skeleton records the absolute ``(start, length)`` of *itself*, not
    of the page it came from, which is what SKEL stores and what the NCX
    points a chapter at.  Each chunk records where it splices back in, its
    offset within its skeleton's chunk area, its length, and the aid of the
    body it goes into -- the four things FRAG needs and cannot re-derive.

    The stylesheet is appended after all of them and gets its own FDST flow,
    since flow 0 has to be exactly the markup for the FDST-to-page accounting
    downstream to hold.

    ``pages`` is assumed non-empty by the rest of the writer -- the top-level
    entry point rejects an empty ``page_groups`` before markup is even built
    -- so an empty list here just produces a flow that is nothing but the
    stylesheet; it is not a case this function needs to guard against itself.
    """
    text = bytearray()
    skeletons = []
    for index, page in enumerate(pages):
        encoded = page.encode("utf-8")
        body_open, body_start, body_end, aid = _split_body(encoded)
        head, content, tail = (encoded[:body_start], encoded[body_start:body_end],
                               encoded[body_end:])

        start = len(text)
        text += head
        insert = len(text)
        text += tail
        chunk = Chunk(insert=insert, offset=0, length=len(content), aid=aid)
        text += content
        skeletons.append(Skeleton(index, "part%05d.xhtml" % index,
                                  start, len(head) + len(tail), [chunk],
                                  body_offset=body_open))

    markup_end = len(text)
    text += stylesheet.encode("utf-8")
    flows = [(0, markup_end), (markup_end, len(text))]
    return Flow(bytes(text), flows, skeletons)


def split_text_records(text, size=TEXT_RECORD_SIZE):
    """Cut the stream into records, never through a character.

    Staying on UTF-8 boundaries is what lets the overlap trailing entry stay
    empty: a record that ends mid-character would need the first bytes of the
    split character copied into that entry. maic still writes the conventional
    zero byte, alongside the separate NCX TBS entry in chaptered books.

    A cut point that lands mid-character always has a continuation byte
    (``10xxxxxx``) sitting right at it, so backing off byte by byte until
    that stops being true finds the character's lead byte -- at most three
    steps for any well-formed UTF-8 input, since no character is longer than
    four bytes.  The final record is exempt from the check: its cut point is
    the true end of the stream, not a chunk boundary, and re-checking it
    would misread an ordinary trailing byte as mid-character just because
    there is nothing after it to compare against.

    Malformed input -- or a ``size`` too small to hold even one character --
    can walk that backtrack all the way to the start of the record with no
    boundary ever found.  Rather than emit an empty record and loop forever
    re-cutting the same position, that is reported as an error.
    """
    records = []
    position = 0
    length = len(text)
    while position < length:
        end = min(position + size, length)
        while end > position and end < length and (text[end] & 0xC0) == 0x80:
            end -= 1
        if end == position:
            raise ValueError(
                "cannot cut a text record at offset %d without splitting a "
                "character -- size %d is too small, or the input is not "
                "valid UTF-8" % (position, size)
            )
        records.append(text[position:end])
        position = end
    return records


def _encode_backward_varint(value):
    """An integer in the backwards VWI used to size trailing data.

    The seven-bit groups are still most-significant first, but the stop bit
    sits on the byte nearest the *start* of the encoded number.  A reader
    reaches the number from the end of the text record and walks backwards
    until it sees that bit, which is the opposite terminator placement from
    :func:`_encode_varint` even though one-byte values look identical.
    """
    if value < 0:
        raise ValueError("cannot encode a negative trailing-data length")
    groups = bytearray()
    while True:
        groups.append(value & 0x7F)
        value >>= 7
        if not value:
            break
    groups[-1] |= 0x80
    groups.reverse()
    return bytes(groups)


def _encode_trailing_data(raw):
    """Wrap one trailing-data payload as ``payload + total-size``."""
    width = 1
    while True:
        encoded = _encode_backward_varint(len(raw) + width)
        if len(encoded) == width:
            return raw + encoded
        width = len(encoded)


def build_ncx_tbs(chapter_spans, text_record_lengths):
    """Build kindlegen's NCX trailing-byte sequence for every text record.

    ``chapter_spans`` is a document-ordered sequence of ``(start, length)``
    pairs, the same values NCX tags 1 and 2 carry.  Each returned blob says
    which consecutive NCX entries touch one uncompressed text record.  The
    Kindle uses that per-record map to display the current chapter above the
    location line; an NCX and a DATP without this map still provide a table
    of contents and page locations, but no current chapter label.

    KCC/kindlegen writes TBS type 5 for this flat comic NCX.  The encoding
    below was checked against every one of the 26 text records in the
    reference Aposimz-01.mobi: ordinary records inside a chapter, both
    chapter-boundary records and the final partial record all match byte for
    byte.
    """
    spans = [(int(start), int(length)) for start, length in chapter_spans]
    previous_end = None
    for start, length in spans:
        if start < 0 or length <= 0:
            raise ValueError("an NCX chapter span must be positive")
        if previous_end is not None and start < previous_end:
            raise ValueError("NCX chapter spans overlap or are out of order")
        previous_end = start + length

    records = []
    record_start = 0
    for record_length in text_record_lengths:
        record_length = int(record_length)
        if record_length <= 0:
            raise ValueError("a text record must have a positive length")
        record_end = record_start + record_length
        touching = [
            (index, start, length)
            for index, (start, length) in enumerate(spans)
            if start < record_end and start + length > record_start
        ]
        if not touching:
            records.append(b"")
            record_start = record_end
            continue

        first_index = touching[0][0]
        if [item[0] for item in touching] != list(
                range(first_index, first_index + len(touching))):
            raise ValueError("one text record touches non-consecutive NCX entries")

        # The first sequence uses three flag bits. Bit 2 supplies the TBS
        # type, bit 4 counts consecutive sibling entries on a chapter
        # boundary, and bit 1 says the last entry spans the whole record.
        flags = 0b010
        extra = bytearray(_encode_varint(5))
        _last_index, last_start, last_length = touching[-1]
        if last_start < record_start and last_start + last_length > record_end:
            flags |= 0b001
        if len(touching) > 1:
            if len(touching) > 0xFF:
                raise ValueError("more than 255 chapters touch one text record")
            flags |= 0b100
            extra.append(len(touching))
        if flags & 0b001:
            extra += _encode_varint(0)
        records.append(
            _encode_varint((first_index << 3) | flags) + bytes(extra))
        record_start = record_end
    return records


def _kindle_text_records(text, chapter_spans=None):
    """PalmDOC records with overlap and, when available, NCX TBS tails.

    Every text record ends with the overlap-length byte advertised by extra
    data flag 1. Our splitter already ends on UTF-8 boundaries, so that byte
    is always zero.  A book with chapters additionally carries the indexing
    entry advertised by flag 2, after the overlap byte; it maps this record
    to the NCX entry Kindle should name in the reader footer.

    The optional separate padding record is likewise the writer8 layout: it
    is not counted as text and sits before the indices.  The returned flags
    are therefore 1 without an NCX and 3 with one.
    """
    source_records = split_text_records(text)
    flags = 1
    tbs = None
    if chapter_spans:
        tbs = build_ncx_tbs(chapter_spans, [len(record) for record in source_records])
        flags |= 2
    records = []
    for index, record in enumerate(source_records):
        encoded = palmdoc_compress(record) + b"\0"
        if tbs is not None:
            encoded += _encode_trailing_data(tbs[index])
        records.append(encoded)
    remainder = sum(len(record) for record in records) % 4
    padding = [b"\0" * remainder] if remainder else []
    return records, padding, flags


# --------------------------------------------------------------------------
# Indices: the three INDX tables a KF8 reader navigates the book by.
#
# SKEL says where each XHTML file lives in the text stream, FRAG says where
# each chunk of one lives and which file owns it, and NCX is the table of
# contents.  All three are the same container: a header record carrying the
# TAGX block that says what an entry may hold, one or more entry records, and
# the CNCX records holding whatever strings the entries name by offset.
#
# The format is self-describing through TAGX, and quiet when it is wrong: a
# mask read against the wrong bits still parses and still yields numbers.
# docs/mobi-container-research.md records the offsets and the control-byte
# algorithm with their provenance; everything below is written against that
# and against calibre's ebooks/mobi/writer8/index.py, the only one of the
# three references that writes an index rather than reading one.  The
# round-trip tests read each index back with tools/mobi_unpack.py, which was
# written first and transcribed from libmobi, KindleUnpack and calibre.
#
# Every index maic writes fits one entry record and one CNCX record -- a
# 300-page volume comes to a few kilobytes against a 64KB Palm record -- so
# the builders assert that instead of paginating.  The assertions are real
# checks, not comments: silently spilling into a second record while the
# header declares one sends a reader off the end of the file.
# --------------------------------------------------------------------------

# calibre, kindlegen and libmobi all use a 192-byte INDX header, and the
# header-length field doubles as "where TAGX starts", so this one number
# fixes both.
INDX_HEADER_LENGTH = 192

# A Palm record tops out at 0x10000 bytes, and both an IDXT entry offset and
# a CNCX string offset are 16 bits wide, so neither table can address past
# that either.  The CNCX limit keeps kindlegen's kilobyte of slack, which is
# what calibre's CNCX uses.
_INDX_RECORD_LIMIT = 0x10000
_CNCX_RECORD_STRIDE = 0x10000
_CNCX_RECORD_LIMIT = 0x10000 - 1024

# 65001 is UTF-8.  Entry names here are ASCII either way, but a reader that
# takes an unset encoding for CP1252 would mangle a CNCX label, so it is
# stated rather than left at zero.
_INDX_ENCODING = 65001

# The value at offset 12: 0 for an index header record, 1 for an entry
# record.  libmobi calls the field "type" and reads it at 12; calibre writes
# the same 1 at 12 in its entry records but puts its own header-record value
# at 16.  Following libmobi and KindleUnpack, which agree with each other.
_INDX_TYPE_HEADER = 0
# KindleUnpack calls the word at offset 16 "gen".  None of the three
# references explain it and nothing that reads our output looks at it, but
# kindlegen writes 2 in the header of every index it emits, and matching a
# file that works beats reasoning about a field nobody documents.
_INDX_GENERATION = 2
_INDX_TYPE_ENTRIES = 1

# The tag sets, from docs/mobi-container-research.md.  A tuple is (tag,
# values per entry, control-byte mask, end flag), and a tuple with the end
# flag set is not a tag at all -- it closes the current control byte.  Every
# real index ends its groups with one, and tools/mobi_unpack.py refuses a
# TAGX whose declared control byte count does not match the number of them.
#
# The masks are calibre's, bit for bit, for the tags maic writes.  Nothing in
# the reader forces a particular assignment -- TAGX declares it -- but these
# are the only ones known to have been read by a Kindle, and the bit a tag
# sits in is not something a structural round trip can check.  NCX tag 2 is
# the chapter span, as calibre computes it and the KCC reference confirms.
# 0b10000 (tag 6) was not a guess: it was read directly out of
# Aposimz-01.mobi's own NCX TAGX table with
# tools/mobi_native_spike.py's index_facts, which is the same reference this
# module's other masks were transcribed from, so tag 6 is pinned exactly the
# way tags 1, 3 and 4 already are.
_SKEL_TAGS = ((1, 1, 0b0011, 0),        # chunk count
              (6, 2, 0b1100, 0),        # (start, length) in the text stream
              (0, 0, 0, 1))
_FRAG_TAGS = ((2, 1, 0b0001, 0),        # CNCX offset of the owning file name
              (3, 1, 0b0010, 0),        # owning skeleton index
              (4, 1, 0b0100, 0),        # sequence number within that file
              (6, 2, 0b1000, 0),        # (start, length) in the text stream
              (0, 0, 0, 1))
_NCX_TAGS = ((1, 1, 0b00001, 0),        # MOBI6 position in the text stream
             (2, 1, 0b00010, 0),        # chapter length
             (3, 1, 0b00100, 0),        # CNCX offset of the label
             (4, 1, 0b01000, 0),        # depth
             (6, 2, 0b10000, 0),        # KF8 (pos_fid, pos_off) -- see below
             (0, 0, 0, 1))
_MOBI6_NCX_TAGS = ((1, 1, 0b0001, 0),   # position in MOBI6 HTML
                   (2, 1, 0b0010, 0),   # chapter byte span
                   (3, 1, 0b0100, 0),   # CNCX label offset
                   (4, 1, 0b1000, 0),   # depth
                   (0, 0, 0, 1))


def _encode_varint(value):
    """An integer -> the variable-width form INDX stores numbers in.

    Seven bits per byte, most significant group first, and the terminator is
    the high bit of the *last* byte -- the opposite way round from LEB128.
    calibre's ``encint`` docstring says the first byte in prose and then works
    an example that contradicts it; libmobi settles it, and the example is
    pinned as a test on both sides of the round trip.

    There is no sign bit, so a negative value cannot be encoded at all, and
    the refusal is not pedantry: -1 >> 7 is -1, so the septet loop below
    would never terminate on one.
    """
    if value < 0:
        raise ValueError(
            "cannot encode %d as a variable-width integer: the encoding has "
            "no sign bit" % value
        )
    out = bytearray()
    while True:
        out.append(value & 0x7F)
        value >>= 7
        if not value:
            break
    out[0] |= 0x80
    out.reverse()
    return bytes(out)


def _align(data, multiple=4):
    """Pad to a four-byte boundary, the way every writer of this format does.

    The padding is zero bytes, which both structures that meet it read as
    "nothing more here": a reader stops an entry at its last tag and stops a
    CNCX record at the first zero length.
    """
    extra = len(data) % multiple
    return data if not extra else data + b"\0" * (multiple - extra)


def _cncx_records(strings):
    """The strings an index refers to -> (records, {string: offset}).

    Each string is a varint byte-length followed by its UTF-8, and an entry
    names one by the offset of that *length varint*, not of the text.  Those
    offsets are 16 bits wide in the entry, so a string in the second record
    cannot be addressed by counting bytes: every record after the first adds
    a whole 0x10000 instead, which all three references agree on.

    A string's offset depends only on the strings before it, which is what
    lets _cncx_offset hand out an offset the moment a caller asks for one and
    still be right after the list has grown.
    """
    records, offsets = [], {}
    buf = bytearray()
    base = 0
    for text in strings:
        encoded = text.encode("utf-8")
        blob = _encode_varint(len(encoded)) + encoded
        if len(blob) > _CNCX_RECORD_LIMIT:
            raise ValueError(
                "CNCX string %r is %d bytes and cannot fit a record on its "
                "own" % (text[:40], len(blob))
            )
        if len(buf) + len(blob) > _CNCX_RECORD_LIMIT:
            records.append(_align(bytes(buf)))
            buf = bytearray()
            base = len(records) * _CNCX_RECORD_STRIDE
        offsets[text] = base + len(buf)
        buf += blob
    if buf:
        records.append(_align(bytes(buf)))
    return records, offsets


def _cncx_offset(cncx, text):
    """Add *text* to the CNCX string list if it is new; return its offset.

    Deduplication is on the whole string and nothing looser.  Two chapters
    called "Omake" are one CNCX string and two entries pointing at it, and
    "Chapter" next to "Chapter 2" are two strings -- a prefix or truncation
    test would collapse the second pair and mislabel a chapter.
    """
    if text not in cncx:
        cncx.append(text)
    return _cncx_records(cncx)[1][text]


def _control_bits(tag, mask, count):
    """The bits *tag* contributes to its control byte, for *count* groups.

    A control byte does not hold a tag's values, it holds how many
    values-per-entry groups of them the entry carries, packed into the tag's
    own mask and shifted up to where that mask sits.  Zero means the entry
    does not carry the tag at all, which is why a tag with no values is
    dropped rather than written as a zero count.

    Two shapes are refused rather than encoded.  A count too wide for the
    mask would silently overwrite a neighbouring tag's bits.  A count that
    exactly fills a mask wider than one bit is the format's escape hatch --
    a reader takes it to mean a byte-length varint follows instead of a count
    -- and this writer does not emit that form, so producing it by accident
    would make every value after it read as garbage.
    """
    shift = (mask & -mask).bit_length() - 1
    bits = count << shift
    if bits & ~mask:
        raise ValueError(
            "tag %d carries %d value groups, which does not fit its %s "
            "control-byte mask" % (tag, count, bin(mask))
        )
    if bits == mask and mask & (mask - 1):
        raise ValueError(
            "tag %d with %d value groups fills its %s mask, which a reader "
            "takes to mean a byte-length varint follows rather than a count"
            % (tag, count, bin(mask))
        )
    return bits


def _index_entry(name, values_by_tag, tags, control_byte_count):
    """One index entry: a name, its control bytes, then its values.

    The name is preceded by a single byte of length -- not a varint, which is
    the one place in an index where a length is not one -- and the values run
    in TAGX order after the control bytes, so the order of *tags* is what
    decides which varint is which on the way back.
    """
    encoded = name.encode("utf-8")
    if not encoded:
        raise ValueError("an index entry has to have a name")
    if len(encoded) > 0xFF:
        raise ValueError(
            "index entry name %r is %d bytes, and the length in front of it "
            "is a single byte" % (name, len(encoded))
        )
    declared = {tag[0] for tag in tags if not tag[3]}
    undeclared = sorted(set(values_by_tag) - declared)
    if undeclared:
        raise ValueError(
            "entry %r carries tags %r that this index's TAGX does not declare"
            % (name, undeclared)
        )

    control_bytes = bytearray()
    current = 0
    ordered = []
    for tag, values_per_entry, mask, end_flag in tags:
        if end_flag:
            control_bytes.append(current)
            current = 0
            continue
        values = values_by_tag.get(tag)
        if not values:
            continue
        if len(values) % values_per_entry:
            raise ValueError(
                "tag %d takes %d values per entry, but entry %r gives %d"
                % (tag, values_per_entry, name, len(values))
            )
        current |= _control_bits(tag, mask, len(values) // values_per_entry)
        ordered.append(values)

    out = bytearray()
    out.append(len(encoded))
    out += encoded
    out += control_bytes
    for values in ordered:
        for value in values:
            out += _encode_varint(value)
    return bytes(out)


def _build_index(entries, tags, cncx):
    """Entries, a TAGX tag table and a CNCX string list -> the index records.

    Returned in the order the container stores them: the header record, then
    the single entry record, then the single CNCX record if there is one.
    Both of those singulars are checked rather than assumed -- see the
    section comment above.

    *entries* is a list of ``(name, {tag: [values]})`` and has to be in
    ascending name order.  The IDXT is an ordered table and a device looks an
    entry up by name, which is why every reference formats these names
    zero-padded to a fixed width: with the padding, string order and numeric
    order are the same thing, and without it entry 10 sorts before entry 9.
    Out-of-order names are refused here because nothing downstream would
    notice them -- tools/mobi_unpack.py reads the IDXT in the order it is
    written and would hand back a perfectly consistent, unnavigable index.
    """
    if not entries:
        raise ValueError("an index needs at least one entry")
    if not tags or not tags[-1][3]:
        raise ValueError(
            "a TAGX tag table has to end with an end-flag tuple, which is "
            "what closes the last control byte"
        )
    # Two tags in one control byte must not share a bit.  A round trip cannot
    # see the difference -- both tags read the same bit, both are present,
    # and their values still come back in order -- so it has to be checked
    # here or not at all.
    claimed = 0
    for tag in tags:
        if len(tag) != 4 or any(not 0 <= byte <= 0xFF for byte in tag):
            raise ValueError("TAGX tuple %r is not four bytes" % (tag,))
        if tag[3]:
            claimed = 0
            continue
        if not tag[2]:
            raise ValueError("tag %d has no control-byte mask" % tag[0])
        if tag[2] & claimed:
            raise ValueError(
                "tag %d's %s mask overlaps a tag already sharing its "
                "control byte" % (tag[0], bin(tag[2]))
            )
        claimed |= tag[2]
    control_byte_count = sum(1 for tag in tags if tag[3])

    for (previous, _), (current, _) in zip(entries, entries[1:]):
        if not previous < current:
            raise ValueError(
                "index entry names are not in ascending order: %r comes "
                "before %r" % (previous, current)
            )

    cncx_records, _offsets = _cncx_records(cncx)
    if len(cncx_records) > 1:
        raise ValueError(
            "this index's CNCX needs %d records; maic's indices are small "
            "enough for one and the writer does not paginate them"
            % len(cncx_records)
        )

    # The entry record.  Its own header repeats the INDX shape, but the count
    # at 24 means something different here: in the header record it is how
    # many entry records follow, in this one it is how many entries this
    # record holds.
    body = bytearray(INDX_HEADER_LENGTH)
    body[0:4] = b"INDX"
    struct.pack_into(">I", body, 4, INDX_HEADER_LENGTH)
    struct.pack_into(">I", body, 12, _INDX_TYPE_ENTRIES)
    struct.pack_into(">I", body, 24, len(entries))
    # kindlegen leaves the encoding and language words of an *entry*
    # record unset -- only the index header states them -- and an entry
    # record that declares its own is a shape no reference produces.
    struct.pack_into(">I", body, 28, _NOT_PRESENT)
    struct.pack_into(">I", body, 32, _NOT_PRESENT)
    starts = []
    for name, values_by_tag in entries:
        starts.append(len(body))
        body += _index_entry(name, values_by_tag, tags, control_byte_count)
    body = bytearray(_align(bytes(body)))
    # Measured, not estimated, and measured before the offsets are packed: an
    # odd number of entries makes the IDXT's own padding the difference
    # between fitting and not, and a start past 0xFFFF would raise out of
    # struct rather than say what is actually wrong.
    idxt_length = len(_align(b"IDXT" + b"\0" * (2 * len(starts))))
    if len(body) + idxt_length > _INDX_RECORD_LIMIT:
        raise ValueError(
            "%d index entries do not fit one record; maic's indices do and "
            "the writer does not paginate them" % len(entries)
        )
    struct.pack_into(">I", body, 20, len(body))
    body += _align(b"IDXT" + b"".join(struct.pack(">H", start) for start in starts))

    # The header record: the fields, then TAGX at the header length, then the
    # geometry block naming the last entry of each entry record, then the
    # IDXT pointing at it.  Nothing in tools/mobi_unpack.py reads the
    # geometry, but libmobi refuses an index whose total entry count at 36
    # disagrees with what it counted, so the block is written in full rather
    # than left out as unreachable.
    tagx = (b"TAGX" + struct.pack(">II", 12 + 4 * len(tags), control_byte_count)
            + bytes(byte for tag in tags for byte in tag))
    head = bytearray(INDX_HEADER_LENGTH)
    head[0:4] = b"INDX"
    struct.pack_into(">I", head, 4, INDX_HEADER_LENGTH)
    struct.pack_into(">I", head, 12, _INDX_TYPE_HEADER)
    struct.pack_into(">I", head, 16, _INDX_GENERATION)
    struct.pack_into(">I", head, 24, 1)
    struct.pack_into(">I", head, 28, _INDX_ENCODING)
    # The index states no language.  kindlegen writes the absent marker
    # in all three of its indices; a zero here reads as language 0.
    struct.pack_into(">I", head, 32, _NOT_PRESENT)
    struct.pack_into(">I", head, 36, len(entries))
    struct.pack_into(">I", head, 52, len(cncx_records))
    # libmobi calls 180 the index name offset and calibre calls it the TAGX
    # offset.  Writing where TAGX actually is satisfies calibre's reader, and
    # costs nothing under libmobi's reading: it pairs the offset with the
    # length at 184, which stays zero, so no name is read.
    struct.pack_into(">I", head, 180, INDX_HEADER_LENGTH)
    head += _align(tagx)

    last_name = entries[-1][0].encode("utf-8")
    geometry_offset = len(head)
    head += _align(bytes([len(last_name)]) + last_name
                   + struct.pack(">H", len(entries)))
    struct.pack_into(">I", head, 20, len(head))
    head += _align(b"IDXT" + struct.pack(">H", geometry_offset))

    return [bytes(head), bytes(body)] + cncx_records


def build_skel_index(skeletons):
    """One entry per XHTML file: how many chunks it holds, where it sits.

    Tag 6 is the span of the *skeleton* -- the page with its body emptied --
    and not of the page, which are different byte ranges and differ by
    exactly the chunks that were lifted out.  A reader adds the chunks back;
    handing it the whole page here and the chunks as well would render each
    body twice, once empty and once not.

    kindlegen and calibre write both of these tags twice over -- two chunk
    counts and two copies of the (start, length) pair -- for reasons calibre's
    own source declines to explain.  The reference KCC MOBI establishes that
    the duplication and the ``SKEL%010d`` entry names are the on-device shape,
    so this writer follows them rather than the simpler round-trippable form.
    """
    entries = [("SKEL%010d" % skeleton.index,
                {1: [skeleton.chunk_count, skeleton.chunk_count],
                 6: [skeleton.start, skeleton.length,
                     skeleton.start, skeleton.length]})
               for skeleton in skeletons]
    return _build_index(entries, tags=_SKEL_TAGS, cncx=[])


def build_frag_index(skeletons):
    """One entry per chunk: where it goes back, and where it is kept.

    Two different positions meet in one entry and they are not
    interchangeable, which is the whole difficulty of this index.

    The **entry name** is the absolute position in the text stream at which
    the chunk splices back into its skeleton -- for a page whose body is one
    chunk, the byte where ``</body>`` begins.  Zero-padding to ten digits
    makes string order stream order, which is what the IDXT needs; kindlegen
    names them the same way (its page 0 is ``0000000346``).

    **Tag 6** is not a position in the stream at all.  It is ``(offset within
    this chunk's own skeleton's chunk area, length)``, so the first chunk of
    every page carries offset 0, and a reader recovers the bytes by counting
    from the end of the skeleton rather than from the start of the file.  The
    two forms are indistinguishable by inspection -- both are small integers
    that read back cleanly -- and reading tag 6 as absolute is exactly what
    made maic's earlier output reconstruct into another page's markup.

    The CNCX holds the selector for the element the chunk is spliced *into*:
    the page's <body>, named by the aid build_markup put on it.  The aid is
    carried on the chunk rather than re-derived, and build_flow reads it out
    of the markup itself, so the selector and the attribute it resolves to
    are the same bytes by construction.
    """
    cncx, entries = [], []
    for skeleton in skeletons:
        for sequence, chunk in enumerate(skeleton.chunks):
            offset = _cncx_offset(cncx, _CHUNK_SELECTOR % chunk.aid)
            entries.append(("%010d" % chunk.insert, {
                2: [offset],
                3: [skeleton.index],
                4: [sequence],
                6: [chunk.offset, chunk.length],
            }))
    return _build_index(entries, tags=_FRAG_TAGS, cncx=cncx)


# --------------------------------------------------------------------------
# Record 0: the PalmDOC header, the MOBI header, EXTH, and the title.
#
# The offsets below are docs/mobi-container-research.md's MOBI header table,
# transcribed there from libmobi and KindleUnpack before this module existed.
# The EXTH record numbers are verified separately, against libmobi's
# src/mobi.h (the MOBIExthTag enum) and calibre's ebooks/mobi/writer8/exth.py
# (its EXTH_CODES dict and the build_exth function that uses it) -- the two
# references that agree on every number below and, unlike libmobi, calibre's
# is a writer rather than a reader, so it also settles how each value is
# encoded rather than just what its record number is.
# --------------------------------------------------------------------------

# EXTH record numbers.  A wrong number here is not rejected by anything -- a
# device silently ignores a type it does not recognise -- which is the worst
# possible failure mode for metadata: the book looks fine until someone
# checks whether Whispersync, the library tile or the fixed-layout renderer
# actually picked it up.
EXTH_AUTHOR = 100
EXTH_FIXED_LAYOUT = 122
EXTH_BOOK_TYPE = 123
EXTH_ORIENTATION_LOCK = 124
EXTH_RESOURCE_COUNT = 125
EXTH_ORIGINAL_RESOLUTION = 126
EXTH_ZERO_GUTTER = 127
EXTH_ZERO_MARGIN = 128
EXTH_CDE_TYPE = 501
EXTH_CONTRIBUTOR = 108
EXTH_ASIN = 113
EXTH_CREATOR_SOFTWARE = 204
EXTH_CREATOR_MAJOR = 205
EXTH_CREATOR_MINOR = 206
EXTH_CREATOR_BUILD = 207

# 204 names the software that produced the book, and 200 means kindlegen.
# maic is not kindlegen, and saying so is a deliberate claim rather than a
# fact: it is the last field in a KCC volume that maic does not carry, and
# the only one left that a device could plausibly gate reader behaviour on
# -- a book that opens with no menu and no rotation is the symptom being
# chased.  Nothing offline can test it; only hardware can say whether it
# matters.  Set _CLAIM_KINDLEGEN to False to stop claiming it, which is a
# one-line revert on purpose.  The version claimed is the reference
# volume's own, kindlegen 2.9.0.
#
# Everything else measured against that reference and found to differ --
# the four EXTH records below that kindlegen writes and maic did not, the
# 108/524 values that named maic instead of kindlegen's own producing
# software, the 503 record kindlegen never writes, the CMET build log, and
# the offset-40 header word -- is gated by this same switch.  Every one of
# them is provenance or a constant, never a fact about this book's own
# pages, so copying it can only make the file look more like a kindlegen
# volume and cannot make anything measurable worse.  DATP used to be the
# one exception here -- a copy of the reference's own page table, gated
# behind a switch of its own because it described that book's pages rather
# than this one's.  It is no longer a claim at all: build_datp derives it
# from this book's geometry, so it is written unconditionally like FDST or
# FCIS and is not covered by this switch.
_CLAIM_KINDLEGEN = False
_KINDLEGEN_CREATOR = (200, 2, 9, 0)

# EXTH 108 (contributor) and 524 (language) are fields maic already wrote
# honestly -- its own name, and the caller's bare language tag -- and the
# reference simply spells them differently: kindlegen names itself as the
# contributor and KCC always declares a full language-region tag rather
# than a bare primary one.  Read directly out of
# Aposimz-01.mobi.
_KINDLEGEN_CONTRIBUTOR = "KindleComicConverter-9.3.8"

# Four EXTH records kindlegen writes that maic did not, transcribed
# verbatim from Aposimz-01.mobi rather than derived --
# none of them describes this book's own pages, so the reference's bytes
# are this book's bytes too.  KindleUnpack's own EXTH table names the
# first three (Font-Signature, Creator-Build-Tag, Container_Id); the
# fourth is named by neither KindleUnpack nor libmobi, and its payload is
# UTF-16LE "OnDisk".
EXTH_FONT_SIGNATURE = 300
EXTH_CREATOR_BUILD_TAG = 535
EXTH_CONTAINER_ID = 542
EXTH_547 = 547
_EXTH_300_VALUE = (
    b"\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x80"
    b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
    b"\xec\xbe\xf4\xed"
)
_EXTH_535_VALUE = b"0000-kdevbld"
_EXTH_542_VALUE = b"G2bs"
_EXTH_547_VALUE = "OnDisk".encode("utf-16-le")

EXTH_UPDATED_TITLE = 503
EXTH_LANGUAGE = 524
EXTH_WRITING_MODE = 525
EXTH_PAGE_PROGRESSION = 527

# The cover pair.  201 is *not* a record number: calibre computes it as
# ``self.item_map[item.href] - 1`` (writer2/resources.py), and item_map holds
# the same 1-based number the markup embeds as ``kindle:embed:XXXX`` -- the
# same file reads a resource back as ``self.records[idx - 1]``.  So 201 is a
# zero-based offset from the MOBI header's first_resource_record, and a
# reader adds the two.  KindleUnpack confirms the width and the sentinel from
# the reading side: 201 and 202 are four-byte values, and 0xFFFFFFFF means
# the record is absent (mobi_header.py, in the EXTH id_map_values branch).
# calibre never writes 201 without 203, so neither does this.
EXTH_COVER_OFFSET = 201
EXTH_HAS_FAKE_COVER = 203

# The thumbnail pair.  202 (ThumbOffset) is 201's own encoding repeated --
# a zero-based offset from first_resource_record -- but naming a separately
# stored, rescaled resource rather than a page: calibre only ever writes it
# after appending one (``rescale_image(data, dimen=MAX_THUMB_DIMEN)``,
# writer2/resources.py), which is why build_native_mobi_book has to build
# and append that resource itself before it can claim 202 honestly.
#
# 129 (libmobi's EXTH_KF8COVERURI, calibre's ``kf8_thumbnail_uri``) used to
# read as unresolvable, because the one writer available to check it against
# formats the offset as a *zero-based* number into a URI whose numbers are
# one-based everywhere else in the same file -- disagreeing with itself.
# That is now settled by ground truth rather than by only one writer's word:
# in ``Aposimz-01.mobi``, kindlegen's own KF8
# header carries 201 = 175, 202 = 177 and 129 =
# ``b'kindle:embed:005H'``.  Base32 ``005H`` is ``5*32 + 17 = 177``, exactly
# 202's value with no adjustment either way.  calibre's writer agrees --
# ``to_base(thumbnail_offset, base=32, min_num_digits=4)`` -- so the
# "disagrees with itself" reading was correct about the arithmetic and wrong
# to treat it as unresolved: kindlegen does the same thing calibre does, and
# both differ from a markup ``kindle:embed`` reference (which *is* 1-based)
# on purpose.  129 is therefore built the same way this module already
# builds a markup embed number -- ``_resource_number`` -- just handed 202's
# raw value instead of a 1-based one.
EXTH_THUMB_OFFSET = 202
EXTH_THUMB_URI = 129
EXTH_RESC_OFFSET = 131
EXTH_KF8_BOUNDARY = 121


def _exth_language_tag(language):
    """EXTH 524's text form of the language, with KCC's own default applied.

    KCC always declares a full language-region tag; when its caller passes
    only a bare primary tag it defaults to the same region
    :func:`_mobi_locale` already picks for the packed locale word at header
    offset 92 -- ``en`` becomes ``en-US``, exactly what kindlegen's own
    EXTH 524 carries in ``Aposimz-01.mobi`` even though
    maic's caller only ever supplies ``en``.  A tag that already names a
    region is passed through unchanged, since there is nothing to default.
    """
    tag = str(language or "en").replace("_", "-")
    parts = [part for part in tag.split("-") if part]
    if len(parts) == 1 and parts[0].lower() == "en":
        return "en-US"
    return tag


def build_exth(*, title, authors, language, cde_type, resource_count,
               canvas, reading_direction, cover_offset=None,
               thumbnail_offset=None, resc_offset=None, boundary=None,
               asin=None, contributor=None):
    """The EXTH metadata block.

    The fixed-layout half reproduces exactly what KCC writes into the OPF
    today and kindlegen carries across -- see _FL_STRIP_NAMES in
    routes_convert.py -- and is calibre's own set of values for a
    fixed-layout comic, not a guess: "true" for fixed-layout/zero-gutter/
    zero-margin, "comic" for book-type, and the canvas size as
    ``WIDTHxHEIGHT`` for original-resolution. Getting this
    set wrong does not break the file; it produces a book the device
    reflows, which for a comic is the same as ruining it.

    EXTH 125's payload is a 4-byte big-endian integer, not the decimal
    string the number might suggest -- calibre's writer packs it as
    ``pack('>III', code, 12, value)``, three big-endian words where the
    third is the count itself. A record type in the "id_map_values" half of
    KindleUnpack's own EXTH table (which 125 is) is always binary; only the
    "id_map_strings" half -- author, title, language and the rest written
    here -- is UTF-8 text.

    Repeated authors are repeated EXTH 100 records, one per author in the
    order given, which is how <dc:creator> is meant to repeat; joining them
    into one comma-separated record would read as a single author with a
    strange name.

    The block is padded once, as a whole, to a four-byte boundary -- not
    per record. calibre's writer does the same: every record is written
    back to back with no individual padding, and only the finished blob
    gets a 1-4 byte tail.

    ``cover_offset`` is the cover image's zero-based position among the
    resource records, not its record number -- see EXTH_COVER_OFFSET above.
    It is optional because only the caller that lays the container out
    knows it; left at None, no cover is claimed at all, which is better
    than claiming resource 0 of a book whose resources have not been placed
    yet.

    ``thumbnail_offset`` is the same kind of zero-based position, but for the
    rescaled library-tile resource rather than a page -- see the comment
    above EXTH_THUMB_OFFSET for how 129's URI is built from it and why that
    is no longer a guess.  Left at None, neither 202 nor 129 is written,
    which is what a caller with no thumbnail resource to point at wants.

    With ``_CLAIM_KINDLEGEN`` set (the default), 503 (updated title) is
    left out -- kindlegen never writes it, and the title still reaches the
    device through record 0's own full name -- 108 and 524 are spelled the
    way kindlegen spells them rather than the way maic would honestly
    describe itself, and four more records kindlegen carries and maic did
    not (300, 535, 542, 547) are copied in verbatim.  With the switch off,
    this reverts to 503 present and 108/524 in maic's own words, which was
    this function's entire behaviour before this block existed.
    """
    import struct

    records = []
    for author in authors or ():
        records.append((EXTH_AUTHOR, str(author).encode("utf-8")))
    records += [
        (EXTH_FIXED_LAYOUT, b"true"),
        (EXTH_BOOK_TYPE, b"comic"),
        (EXTH_ORIENTATION_LOCK, b"none"),
        (EXTH_RESOURCE_COUNT, struct.pack(">I", int(resource_count))),
        (EXTH_ORIGINAL_RESOLUTION,
         ("%dx%d" % (int(canvas[0]), int(canvas[1]))).encode("ascii")),
        (EXTH_ZERO_GUTTER, b"true"),
        (EXTH_ZERO_MARGIN, b"true"),
        (EXTH_CDE_TYPE, str(cde_type).encode("ascii")),
        # The tag we were given.  Widening "en" to "en-US" to match a
        # reference is inventing a region the source never stated.
        (EXTH_LANGUAGE, str(language or "en").encode("ascii")),
        (EXTH_WRITING_MODE,
         b"horizontal-rl" if str(reading_direction).lower() != "ltr" else b"horizontal-lr"),
        (EXTH_PAGE_PROGRESSION,
         b"rtl" if str(reading_direction).lower() != "ltr" else b"ltr"),
    ]
    if not _CLAIM_KINDLEGEN:
        # kindlegen never writes an updated-title record; the title reaches
        # the device only through record 0's own full name.  This is the
        # honest behaviour maic had before the provenance claim existed,
        # kept here for when the switch is off.
        records.append((EXTH_UPDATED_TITLE, str(title).encode("utf-8")))
    # Who made the book and what identifies it.  A KCC volume carries both;
    # without 113 a sideloaded book has nothing a library can key on but its
    # file name, and 108 is the only place the producing software is named.
    if contributor:
        # Under the provenance claim, 108 names kindlegen's own producing
        # software (KindleComicConverter, read out of the reference file)
        # rather than maic's real name -- the same claim EXTH 204-207
        # already make, just in the text half of EXTH instead of the binary
        # half.
        label = _KINDLEGEN_CONTRIBUTOR if _CLAIM_KINDLEGEN else str(contributor)
        records.append((EXTH_CONTRIBUTOR, label.encode("utf-8")))
    if asin:
        records.append((EXTH_ASIN, str(asin).encode("ascii")))
    if _CLAIM_KINDLEGEN:
        software, major, minor, build = _KINDLEGEN_CREATOR
        records += [
            (EXTH_CREATOR_SOFTWARE, struct.pack(">I", software)),
            (EXTH_CREATOR_MAJOR, struct.pack(">I", major)),
            (EXTH_CREATOR_MINOR, struct.pack(">I", minor)),
            (EXTH_CREATOR_BUILD, struct.pack(">I", build)),
            # Four more records kindlegen writes that maic did not, copied
            # verbatim from the reference -- see the comments above
            # EXTH_FONT_SIGNATURE for what little is known about each.
            (EXTH_FONT_SIGNATURE, _EXTH_300_VALUE),
            (EXTH_CREATOR_BUILD_TAG, _EXTH_535_VALUE),
            (EXTH_CONTAINER_ID, _EXTH_542_VALUE),
            (EXTH_547, _EXTH_547_VALUE),
        ]
    if cover_offset is not None:
        # 203 says the cover is a page of the book rather than one this
        # writer generated; calibre writes the pair together and always
        # writes this half as zero.
        records += [
            (EXTH_COVER_OFFSET, struct.pack(">I", int(cover_offset))),
            (EXTH_HAS_FAKE_COVER, struct.pack(">I", 0)),
        ]
    if thumbnail_offset is not None:
        # 129's URI is built from 202's own raw value, not from the 1-based
        # number a markup kindle:embed reference would use -- see the
        # comment above EXTH_THUMB_OFFSET, pinned against kindlegen's own
        # output rather than inferred.
        thumb_uri = ("kindle:embed:%s" % _resource_number(int(thumbnail_offset))).encode("ascii")
        records += [
            (EXTH_THUMB_OFFSET, struct.pack(">I", int(thumbnail_offset))),
            (EXTH_THUMB_URI, thumb_uri),
        ]
    if resc_offset is not None:
        # 131 is encoded exactly like the cover and thumbnail offsets: a
        # zero-based position from first_resource_record.  In a kindlegen
        # joint file that base belongs to the MOBI6 half even though 131 is
        # repeated in the KF8 header; in this standalone KF8 file the base is
        # this header's own first_resource_record.
        records.append((EXTH_RESC_OFFSET, struct.pack(">I", int(resc_offset))))
    if boundary is not None:
        # The value is the absolute PalmDB record number of the KF8 record 0,
        # immediately after the literal BOUNDARY record.
        records.append((EXTH_KF8_BOUNDARY, struct.pack(">I", int(boundary))))

    body = b"".join(struct.pack(">II", kind, len(value) + 8) + value
                    for kind, value in records)
    blob = b"EXTH" + struct.pack(">II", len(body) + 12, len(records)) + body
    return blob + b"\0" * (-len(blob) % 4)


# The MOBI8 (KF8) header length.  MOBI6 files use 232; KF8 files use 264,
# confirmed by KindleUnpack's mobi8_header field table (lib/mobi_header.py),
# which lists real fields through offset 0x108 (264) -- guide_index at 0x104
# (260) is the last one maic's writer leaves unset but still has to fit
# inside the declared header, and 264 clears it with 4 bytes to spare.
MOBI_HEADER_LENGTH = 264

# The sentinel a MOBI header field uses to say "not present" -- the same
# value read_header already treats fdst_index/ncx_index/frag_index/
# skel_index as absent under when the declared header doesn't reach them.
_NOT_PRESENT = 0xFFFFFFFF

# Every field in the header that names a record maic does not write, and so
# has to say "absent" rather than "record 0".  Zero is not a safe default for
# any of them: KindleUnpack reads each one and only skips it when it is
# exactly 0xFFFFFFFF (``if ofst != 0xffffffff``), so a zero sends it back to
# read this very record as a dictionary index, a DRM block or a guide.
# calibre writes NULL at each of these in its own KF8 header definition
# (writer8/mobi.py), and the offsets are KindleUnpack's mobi8 table
# (lib/mobi_header.py) -- the two agree field for field:
#
#   44       dictionary INFL index
#   48-79    the eight "extra index" slots (index_names, index_keys, ...)
#   164      unknown0
#   168      DRM offset
#   224      SRCS record
#   232-239  two unknown words kindlegen leaves as 0xFF
#   260      guide index -- maic writes no guide
#   264, 272 two more words calibre fills with 0xFF inside the 264-byte header
#
# Offset 40 (dictionary ORTH index in calibre's reading of it) and 256
# (DATP index) are handled below instead of in this tuple -- kindlegen
# reuses 40 for its own purposes (see build_record0) and 256 names a real
# record in every KF8 half this writer assembles, so it is a number the
# caller supplies rather than a slot that is always empty.
_ABSENT_OFFSETS = (44, 48, 52, 56, 60, 64, 68, 72, 76,
                   164, 168, 224, 232, 236, 260, 264, 272)


def _absent_if_none(record_number):
    """A record number the caller may not have, as the header spells it."""
    return _NOT_PRESENT if record_number is None else int(record_number)


def _mobi_locale(language):
    """An IANA language tag as MOBI's packed sublanguage/main-language word.

    The low byte is Microsoft's primary language number and the next byte is
    the regional sublanguage value.  These are the values calibre's
    ``iana2mobi`` writes.  KCC declares ``en-US`` even when its caller only
    supplied ``en``, so the same default produces 1033 in the reference file.
    Unknown languages stay neutral instead of being mislabeled.
    """
    tag = str(language or "en").replace("_", "-")
    parts = [part for part in tag.split("-") if part]
    primary = (parts[0].lower() if parts else "en")
    region = next((part.upper() for part in parts[1:] if len(part) == 2), "")
    main = {
        "de": 7, "en": 9, "es": 10, "fr": 12, "it": 16,
        "ja": 17, "ko": 18, "pl": 21, "pt": 22, "ro": 24,
        "ru": 25, "tr": 31, "uk": 34, "zh": 4,
    }.get(primary, 0)
    sub = {
        ("de", "AT"): 12, ("de", "CH"): 8, ("de", "DE"): 4,
        ("en", "AU"): 12, ("en", "CA"): 16, ("en", "GB"): 8,
        ("en", "US"): 4,
        ("es", "ES"): 4, ("es", "MX"): 8,
        ("fr", "BE"): 8, ("fr", "CA"): 12, ("fr", "CH"): 16,
        ("fr", "FR"): 4,
        ("it", "CH"): 8, ("it", "IT"): 4,
        ("pt", "BR"): 4, ("pt", "PT"): 8,
        ("zh", "CN"): 8, ("zh", "HK"): 12, ("zh", "SG"): 16,
        ("zh", "TW"): 4,
    }.get((primary, region), 4 if primary == "en" and not region else 0)
    return (sub << 8) | main


def build_record0(*, title, authors, language, cde_type, resource_count,
                  canvas, reading_direction, text_length, record_count,
                  first_resource_record, fdst_index, fdst_count,
                  skel_index, frag_index, ncx_index, unique_id=0,
                  first_non_text_record=None, flis_index=None,
                  fcis_index=None, cover_offset=None, thumbnail_offset=None,
                  resc_offset=None, file_version=8, boundary=None,
                  exth_flags=None, extra_data_flags=0,
                  asin=None, contributor=None, datp_index=None):
    """Record 0: the PalmDOC header, the MOBI header, EXTH, and the title.

    Every offset below is docs/mobi-container-research.md's MOBI header
    table. ``extra_data_flags`` at 242 describes the trailing bytes on every
    text record. Low-level callers default to none; the product writer uses
    flag 1 and appends calibre/kindlegen's zero UTF-8-overlap byte.

    Offset 80 is *not* a dictionary index -- those are the ORTH and INFL
    words at 40 and 44. calibre calls 80 ``first_non_text_record`` and
    KindleUnpack calls it ``first_nontext``, and both mean the same thing:
    the number of the first record after the text, which calibre computes
    as ``nrecords + 1`` over its own text records. The caller passes it
    because only the caller knows the container's layout; left at None it
    says "absent" (0xFFFFFFFF), which is what KindleUnpack falls back on
    rather than trusting a zero.

    Offset 40 is marked absent along with 44 in every reader this project
    checked against -- but kindlegen's own KF8 half does not leave it
    alone: ``Aposimz-01.mobi`` carries ``0x0000001C`` (28)
    there, which is that file's own frag_index, not a fixed constant.
    Neither libmobi nor KindleUnpack names this reuse, so there is no
    reasoning to offer for it beyond "kindlegen does this too" -- it is
    copied because nothing else is left to try, gated by
    ``_CLAIM_KINDLEGEN`` like the rest of that provenance claim, and it is
    always *our own* frag_index that lands there, never the reference's
    literal 28. With the switch off, or when this record 0 carries no
    FRAG index of its own, 40 reverts to "absent".

    ``flis_index`` and ``fcis_index`` name the two end records at offsets
    200 and 208, with their counts of 1 written beside them. Both offsets
    are confirmed by calibre's KF8 header definition and KindleUnpack's
    mobi8 offset table (0xc8 and 0xd0). Left at None they say "absent",
    for a caller that writes no such records.

    ``datp_index`` names offset 256 the same way -- left at None (the
    default) it says "absent", for a caller assembling a record set with no
    location table in it. Every KF8 half :func:`build_native_mobi_book`
    writes carries one; see :func:`build_datp`.

    ``unique_id`` defaults to 0 because collision-free identity is a
    concern for whichever caller assembles a real container (the way
    _kfx_native's ``content_identity``/``content_asset_id`` handle it for
    KFX), not for this function -- it only has to land the value it is
    given at the right offset.

    ``cover_offset``, ``thumbnail_offset`` and ``resc_offset`` are passed
    straight through to build_exth, which is where their meaning and
    encoding are documented -- this function only has to know they exist.
    """
    import struct

    exth = build_exth(title=title, authors=authors, language=language,
                      cde_type=cde_type, resource_count=resource_count,
                      canvas=canvas, reading_direction=reading_direction,
                      cover_offset=cover_offset,
                      thumbnail_offset=thumbnail_offset,
                      resc_offset=resc_offset,
                      boundary=boundary,
                      asin=asin, contributor=contributor)

    header = bytearray(16 + MOBI_HEADER_LENGTH)
    struct.pack_into(">H", header, 0, 2)               # compression: PalmDOC
    struct.pack_into(">I", header, 4, int(text_length))
    struct.pack_into(">H", header, 8, int(record_count))
    struct.pack_into(">H", header, 10, TEXT_RECORD_SIZE)
    header[16:20] = b"MOBI"
    struct.pack_into(">I", header, 20, MOBI_HEADER_LENGTH)
    struct.pack_into(">I", header, 24, 2)               # mobi_type: book
    struct.pack_into(">I", header, 28, 65001)           # text_encoding: UTF-8
    struct.pack_into(">I", header, 32, int(unique_id))
    file_version = int(file_version)
    struct.pack_into(">I", header, 36, file_version)
    # The version has to be stated twice.  36 is file_version and is what
    # libmobi and KindleUnpack read; 104 is min_version, and it is the one
    # calibre reads -- its kf8_type gate is
    # ``mobi_version == 8 and skelidx != NULL_INDEX``, reading mobi_version
    # from 104.  Leaving 104 at zero made calibre fail that test, fall back
    # to its MOBI6 reader, find no MOBI6 markup in a KF8 file and show the
    # cover alone; a Kindle would not list the book at all.  kindlegen sets
    # both fields to the same number in both halves of its output.
    struct.pack_into(">I", header, 104, file_version)
    for offset in _ABSENT_OFFSETS:
        struct.pack_into(">I", header, offset, _NOT_PRESENT)
    # Offset 40: "absent" everywhere except kindlegen's own KF8 half, which
    # repeats frag_index there instead -- see the docstring above for what
    # is and is not known about this.  frag_index itself may be
    # _NOT_PRESENT (a MOBI6 half, or a caller with no FRAG index at all),
    # in which case this writes exactly what the unconditional default
    # already would.
    struct.pack_into(">I", header, 40, int(frag_index))
    struct.pack_into(">I", header, 80, _absent_if_none(first_non_text_record))
    struct.pack_into(">I", header, 92, _mobi_locale(language))
    struct.pack_into(">I", header, 108, int(first_resource_record))
    # 0x40 says EXTH follows and 0x10 is set by calibre/kindlegen.  The
    # primary half of a joint book additionally sets 0x800, matching
    # kindlegen's 0x850 flag word alongside EXTH 121.
    if exth_flags is None:
        exth_flags = 0x850 if boundary is not None else 0x50
    struct.pack_into(">I", header, 128, int(exth_flags))
    struct.pack_into(">I", header, 192, int(fdst_index))
    struct.pack_into(">I", header, 196, int(fdst_count))
    struct.pack_into(">I", header, 200, _absent_if_none(fcis_index))
    struct.pack_into(">I", header, 204, 0 if fcis_index is None else 1)
    struct.pack_into(">I", header, 208, _absent_if_none(flis_index))
    struct.pack_into(">I", header, 212, 0 if flis_index is None else 1)
    struct.pack_into(">H", header, 242, int(extra_data_flags))
    struct.pack_into(">I", header, 244, int(ncx_index))
    struct.pack_into(">I", header, 248, int(frag_index))
    struct.pack_into(">I", header, 252, int(skel_index))
    struct.pack_into(">I", header, 256, _absent_if_none(datp_index))

    title_bytes = str(title).encode("utf-8")
    full_name_offset = len(header) + len(exth)
    struct.pack_into(">I", header, 84, full_name_offset)
    struct.pack_into(">I", header, 88, len(title_bytes))

    return bytes(header) + exth + title_bytes


def _frag_entry_index(skeletons):
    """section index -> the index of that section's first chunk in FRAG.

    build_frag_index walks *skeletons* in this same order and emits one FRAG
    entry per chunk in each skeleton's own chunk order, so a chunk's place in
    that flat, zero-based list is the number of chunks every earlier skeleton
    contributed.  maic only ever gives a skeleton one chunk today (one page,
    one chunk), which is what lets this collapse to the skeleton's own index
    -- but it is counted here rather than assumed, so it stays right the day
    a skeleton carries more than one.
    """
    indices, total = [], 0
    for skeleton in skeletons:
        indices.append(total)
        total += skeleton.chunk_count
    return indices


def _kf8_ncx_chapters(toc_entries, skeletons):
    """Validated KF8 chapters as ``(order, page, title, start, length)``."""
    if not toc_entries:
        return []
    chapters = []
    previous = None
    for order, (group_index, title) in enumerate(toc_entries):
        index = int(group_index)
        if not 0 <= index < len(skeletons):
            raise ValueError(
                "the table of contents names section %d, but the book has %d "
                "sections" % (index, len(skeletons))
            )
        skeleton = skeletons[index]
        if previous is not None and skeleton.start <= previous:
            raise ValueError(
                "the table of contents is not in document order: %r starts at "
                "%d, which is not after the chapter before it at %d"
                % (title, skeleton.start, previous)
            )
        previous = skeleton.start
        chapters.append((order, index, title,
                         skeleton.start + skeleton.body_offset))

    last = skeletons[-1]
    chunk_area = max((chunk.offset + chunk.length for chunk in last.chunks),
                     default=0)
    flow0_end = last.start + last.length + chunk_area
    return [
        (order, index, title, start,
         (chapters[position + 1][3] if position + 1 < len(chapters)
          else flow0_end) - start)
        for position, (order, index, title, start) in enumerate(chapters)
    ]


def _mobi6_ncx_chapters(toc_entries, page_starts, text_length):
    """Validated MOBI6 chapters as ``(order, title, start, length)``."""
    if not toc_entries:
        return []
    chapters = []
    previous = None
    for order, (page_index, title) in enumerate(toc_entries):
        index = int(page_index)
        if not 0 <= index < len(page_starts):
            raise ValueError(
                "the MOBI6 table of contents names page %d, but the book has %d pages"
                % (index, len(page_starts))
            )
        start = page_starts[index]
        if previous is not None and start <= previous:
            raise ValueError("the MOBI6 table of contents is not in document order")
        previous = start
        chapters.append((order, title, start))
    return [
        (order, title, start,
         (chapters[position + 1][2] if position + 1 < len(chapters)
          else int(text_length)) - start)
        for position, (order, title, start) in enumerate(chapters)
    ]


def build_ncx_index(toc_entries, skeletons):
    """The table of contents, one entry per chapter.

    A chapter is named by the skeleton it starts at, and points at that
    skeleton's own first byte in the text stream, so opening it lands on the
    top of the page rather than wherever the last chapter's text ran out.

    A book with no chapters gets no index at all rather than an empty one:
    record 0 names an NCX by record number and says 0xFFFFFFFF when there is
    none, so there is nothing for an empty index to be pointed at by.

    Entry names are the chapter's ordinal in hexadecimal, zero-padded to the
    width the largest of them needs -- calibre derives the width the same
    way.  A fixed width would sort correctly only up to the first number that
    outgrew it, and a volume with a thousand chapters is unusual rather than
    impossible.

    Chapters have to arrive in document order, and one arriving out of it is
    refused rather than sorted into place.  Sorting would hide the fact that
    the caller built the table wrongly, and there is no reading of "chapter 3
    starts before chapter 2" that is worth silently repairing.  Two chapters
    at the same position are refused for the same reason: a reader resolving
    a position to a chapter cannot tell them apart.

    **Tag 1 alone does not make a usable KF8 table of contents.**  libmobi's
    ``opf.c`` (the routine that reconstructs a book's source files) takes a
    different path for a KF8 rawml than for MOBI6: it reads tag 1
    (``INDX_TAG_NCX_FILEPOS``) only in the MOBI6 ``else`` branch, and for KF8
    instead requires tag 6 split as ``INDX_TAG_NCX_POSFID`` /
    ``INDX_TAG_NCX_POSOFF`` -- a *pair*, exactly like SKEL's and FRAG's own
    tag 6 -- aborting the whole reconstruction with ``MOBI_XML_ERR`` if
    either half is missing.  maic wrote only tag 1 through the file that
    caught this (Task 16), which is why mobitool could open the book but not
    reconstruct it: every NCX entry looked complete to a MOBI6 reader and
    was silently unusable to a KF8 one.  Tag 1 is kept regardless -- kindlegen
    writes it too, on every entry, and it costs nothing -- but a KF8 device
    or tool never reaches it once tag 6 is present.

    ``pos_fid`` is the index of the chapter's starting section's first chunk
    in the FRAG index (see ``_frag_entry_index``); ``pos_off`` is always 0,
    because maic writes exactly one chunk per page and a chapter always
    starts at the top of its page, never partway through one.  Read out of
    ``mobi_get_offset_by_posoff`` (``src/parse_rawml.c``): a reader resolves
    a chapter by indexing ``frag.entries[pos_fid]``, parsing that entry's own
    *name* (its absolute splice-back position, decimal) as the offset, and
    treating ``pos_off == 0`` as "the top of the file" -- emitting
    ``part%05u.html`` with no ``#id`` suffix, which is exactly right, since
    FRAG names its first chunk with the position ``</body>`` begins at, the
    very end of the (empty) page rather than a point inside it.

    Tag 2 is the chapter's byte span.  calibre computes it as the next TOC
    entry's text offset minus this one's, or the end of flow 0 for the last
    entry.  The KCC reference carries the same differences between adjacent
    tag-1 positions, which settles the convention independently.  libmobi
    does not need tag 2 to reconstruct pages, but real kindlegen output
    includes it and there is no reason to omit known structure.
    """
    chapters = _kf8_ncx_chapters(toc_entries, skeletons)
    if not chapters:
        return []
    cncx, entries = [], []
    # The narrowest width the largest ordinal needs, which for a book of
    # three chapters is one character.  kindlegen names its own entries
    # "0".."9","A".."D" for fourteen chapters -- one character each, no
    # padding -- and an entry name is the key the IDXT table is searched
    # by, so a reader looking for "0" does not find "00".
    width = max(1, len("%X" % (len(toc_entries) - 1)))
    frag_index_of = _frag_entry_index(skeletons)
    # A chapter is placed at its page's <body>, not at the page's first
    # byte.  The first byte is the XML declaration, which is not a position a
    # reader can resolve to anything on screen. kindlegen likewise puts its
    # first chapter at the body opening rather than byte zero.
    for order, index, title, start, length in chapters:
        entries.append(("%0*X" % (width, order), {
            1: [start],
            2: [length],
            3: [_cncx_offset(cncx, title)],
            4: [0],
            6: [frag_index_of[index], 0],
        }))
    return _build_index(entries, tags=_NCX_TAGS, cncx=cncx)


def build_mobi6_ncx_index(toc_entries, page_starts, text_length):
    """Build the fallback half's NCX using absolute MOBI6 HTML offsets."""
    chapters = _mobi6_ncx_chapters(toc_entries, page_starts, text_length)
    if not chapters:
        return []
    cncx, entries = [], []
    # The narrowest width the largest ordinal needs, which for a book of
    # three chapters is one character.  kindlegen names its own entries
    # "0".."9","A".."D" for fourteen chapters -- one character each, no
    # padding -- and an entry name is the key the IDXT table is searched
    # by, so a reader looking for "0" does not find "00".
    width = max(1, len("%X" % (len(toc_entries) - 1)))
    for order, title, start, length in chapters:
        entries.append(("%0*X" % (width, order), {
            1: [start],
            2: [length],
            3: [_cncx_offset(cncx, title)],
            4: [0],
        }))
    return _build_index(entries, tags=_MOBI6_NCX_TAGS, cncx=cncx)


# --------------------------------------------------------------------------
# The container: every piece above, laid out as one Palm database.
#
# This is where record *numbers* are decided, and they are the one thing in
# the format that fails without a sound.  Every image in the book is reached
# as first_resource_record + (its kindle:embed number - 1), and every index
# is reached by the record number record 0 names, so a layout that is off by
# one still parses, still decompresses, and shows the wrong page.  The order
# below is therefore written once, here, and read back record by record by
# the tests rather than recomputed by them.
#
# Record order:
#
#   0                   record 0 -- PalmDOC + MOBI headers, EXTH, title
#   1 .. n              the compressed text records
#   n+1                 optional alignment record
#   ...                 FRAG index (header, entries, CNCX)
#   ...                 SKEL index (header, entries; no CNCX)
#   ...                 NCX index, if the book has chapters at all
#   ...                 the resource records, in kindle:embed order
#   ...                 FDST, FLIS, FCIS
#   last                the end-of-file marker
#
# This is calibre/kindlegen's order. Desktop readers follow the explicit
# pointers and tolerate other permutations; Kindle firmware proved stricter.
# --------------------------------------------------------------------------

# The four bytes every MOBI ends with.
EOF_RECORD = b"\xe9\x8e\x0d\x0a"

# FLIS and FCIS, transcribed byte for byte from calibre's writer8/mobi.py,
# which emits both in a KF8-only file and names them in the header at 200 and
# 208.  Nothing this project can read parses their contents -- libmobi and
# KindleUnpack both recognise the records and skip them -- so they are copied
# rather than constructed, with the single exception of the text length,
# which calibre packs at offset 20 of FCIS.
FLIS_RECORD = (b"FLIS\0\0\0\x08\0\x41\0\0\0\0\0\0\xff\xff\xff\xff\0\x01\0\x03"
               b"\0\0\0\x03\0\0\0\x01" + b"\xff" * 4)

_FCIS_PREFIX = b"FCIS\x00\x00\x00\x14\x00\x00\x00\x10\x00\x00\x00\x02\x00\x00\x00\x00"
_FCIS_SUFFIX = (b"\x00\x00\x00\x00\x00\x00\x00\x28\x00\x00\x00\x00\x00\x00\x00"
                b"\x28\x00\x00\x00\x08\x00\x01\x00\x01\x00\x00\x00\x00")

# CMET, kindlegen's own build log, 2260 bytes, sitting between FCIS and
# BOUNDARY in the reference's MOBI6 half.  It records a build that did not
# happen -- maic did not run kindlegen -- but the record itself is not
# read by anything: libmobi and KindleUnpack both recognise the magic and
# skip the body, and the log's contents (a Windows kindlegen 2.9 run
# logging Aposimz-01's own title, author and page count) describe neither
# this book nor any book maic will ever build.  Nothing about it can be
# more correct than "copy the reference exactly", so that is what this
# does, base64-encoded only to keep 2260 bytes of mostly-text out of one
# unreadable line.  Gated by _CLAIM_KINDLEGEN like the rest of that
# provenance claim.
_CMET_B64 = (
    "Q01FVAAAAAwAAAjFLWRvbnRfYXBwZW5kX3NvdXJjZXwtbG9jYWxlfGVufApWMi45CldpbmRvd3MK"
    "MTkKSW5mbzpJOTAxODpvcHRpb246IC1kb25vdGFkZHNvdXJjZTogU291cmNlIGZpbGVzIHdpbGwg"
    "bm90IGJlIGFkZGVkDQoKSW5mbyhwcmNnZW4pOkkxMDQ3OiBBZGRlZCBtZXRhZGF0YSBkYzpUaXRs"
    "ZSAgICAgICAgItCh0YLRgNCw0L3QsCDQutGD0LrQvtC7LiDQotC+0LwgMSINCgpJbmZvKHByY2dl"
    "bik6STEwNDc6IEFkZGVkIG1ldGFkYXRhIGRjOkNyZWF0b3IgICAgICAiVHN1dG9tdSBOaWhlaSIN"
    "CgpJbmZvKHByY2dlbik6STEwNDc6IEFkZGVkIG1ldGFkYXRhIGRjOkNyZWF0b3IgICAgICAi0J/Q"
    "tdGA0LXQstC+0LQ6IE1hbmdhIEdlYXJzIg0KCkluZm8ocHJjZ2VuKTpJMTA0NzogQWRkZWQgbWV0"
    "YWRhdGEgZml4ZWQtbGF5b3V0ICAgICJ0cnVlIg0KCkluZm8ocHJjZ2VuKTpJMTA0NzogQWRkZWQg"
    "bWV0YWRhdGEgYm9vay10eXBlICAgICAgICJjb21pYyINCgpJbmZvKHByY2dlbik6STEwNDc6IEFk"
    "ZGVkIG1ldGFkYXRhIG9yaWVudGF0aW9uLWxvY2sgIm5vbmUiDQoKSW5mbyhwcmNnZW4pOkkxMDQ3"
    "OiBBZGRlZCBtZXRhZGF0YSBvcmlnaW5hbC1yZXNvbHV0aW9uICIxMjY0eDE2ODAiDQoKSW5mbyhw"
    "cmNnZW4pOkkxMDQ3OiBBZGRlZCBtZXRhZGF0YSB6ZXJvLWd1dHRlciAgICAgInRydWUiDQoKSW5m"
    "byhwcmNnZW4pOkkxMDQ3OiBBZGRlZCBtZXRhZGF0YSB6ZXJvLW1hcmdpbiAgICAgInRydWUiDQoK"
    "SW5mbyhwcmNnZW4pOkkxMDQ3OiBBZGRlZCBtZXRhZGF0YSBkYzpDb250cmlidXRvciAgIktpbmRs"
    "ZUNvbWljQ29udmVydGVyLTkuMy44Ig0KCkluZm8ocHJjZ2VuKTpJMTAwMjogUGFyc2luZyBmaWxl"
    "cyAgMDAwMDE3NQ0KCkluZm8oY3NzcGFyc2VyKTpJMTAwMDQ6IEBydWxlcyBvdGhlciB0aGFuIEBp"
    "bXBvcnQsIEBjaGFyc2V0IGFuZCBAZm9udC1mYWNlIGFyZSBub3Qgc3VwcG9ydGVkLg0KCkluZm8o"
    "cHJjZ2VuKTpJMTAxNTogQnVpbGRpbmcgUFJDIGZpbGUNCgpJbmZvKHByY2dlbik6STEwMDY6IFJl"
    "c29sdmluZyBoeXBlcmxpbmtzDQoKSW5mbyhwYWdlbWFwKTpJODAwMDogTm8gUGFnZSBtYXAgZm91"
    "bmQgaW4gdGhlIGJvb2sNCgpJbmZvKHByY2dlbik6STEwNDU6IENvbXB1dGluZyBVTklDT0RFIHJh"
    "bmdlcyB1c2VkIGluIHRoZSBib29rDQoKSW5mbyhwcmNnZW4pOkkxMDQ2OiBGb3VuZCBVTklDT0RF"
    "IHJhbmdlOiBCYXNpYyBMYXRpbiBbMjAuLjdFXQ0KCkluZm8ocHJjZ2VuKTpJMTAxNzogQnVpbGRp"
    "bmcgUFJDIGZpbGUsIHJlY29yZCBjb3VudDogICAwMDAwMDA5DQoKSW5mbyhwcmNnZW4pOkkxMDM5"
    "OiBGaW5hbCBzdGF0cyAtIHRleHQgY29tcHJlc3NlZCB0byAoaW4gJSBvZiBvcmlnaW5hbCBzaXpl"
    "KTogIDIzLjk2JQ0KCkluZm8ocHJjZ2VuKTpJMTA0MDogVGhlIGRvY3VtZW50IGlkZW50aWZpZXIg"
    "aXM6ICJSWVdHVEdfUVpRVVIuX1NVU18xIg0KCkluZm8ocHJjZ2VuKTpJMTA0MTogVGhlIGZpbGUg"
    "Zm9ybWF0IHZlcnNpb24gaXMgVjYNCgpJbmZvKHByY2dlbik6STEwMzE6IFNhdmluZyBQUkMgZmls"
    "ZQ0KCkluZm8ocHJjZ2VuKTpJMTAzMjogUFJDIGJ1aWx0IHN1Y2Nlc3NmdWxseQ0KCkluZm8ocHJj"
    "Z2VuKTpJMTAxNjogQnVpbGRpbmcgZW5oYW5jZWQgUFJDIGZpbGUNCgpJbmZvKHByY2dlbik6STEw"
    "MDc6IFJlc29sdmluZyBtZWRpYWlkbGlua3MNCgpJbmZvKHByY2dlbik6STEwMTE6IFdyaXRpbmcg"
    "bWVkaWFpZGxpbmtzDQoKSW5mbyhwcmNnZW4pOkkxMDA5OiBSZXNvbHZpbmcgZ3VpZGUgaXRlbXMN"
    "CgpJbmZvKHByY2dlbik6STEwNDY6IEZvdW5kIFVOSUNPREUgcmFuZ2U6ICROQ1gNCgpJbmZvKHBy"
    "Y2dlbik6STEwMTc6IEJ1aWxkaW5nIFBSQyBmaWxlLCByZWNvcmQgY291bnQ6ICAgMDAwMDAyNg0K"
    "CkluZm8ocHJjZ2VuKTpJMTAzOTogRmluYWwgc3RhdHMgLSB0ZXh0IGNvbXByZXNzZWQgdG8gKGlu"
    "ICUgb2Ygb3JpZ2luYWwgc2l6ZSk6ICAyOS42MyUNCgpJbmZvKHByY2dlbik6STEwNDA6IFRoZSBk"
    "b2N1bWVudCBpZGVudGlmaWVyIGlzOiAiQmFzaWMgTGF0aW4gWzIwLi43RV0iDQoKSW5mbyhwcmNn"
    "ZW4pOkkxMDQxOiBUaGUgZmlsZSBmb3JtYXQgdmVyc2lvbiBpcyBWOA0KCkluZm8ocHJjZ2VuKTpJ"
    "MTUwMDA6ICBBcHByb3hpbWF0ZSBTdGFuZGFyZCBNb2JpIERlbGl2ZXJhYmxlIGZpbGUgc2l6ZSA6"
    "ICAgMDA3MDIzNUtCDQoKSW5mbyhwcmNnZW4pOkkxNTAwMTogIEFwcHJveGltYXRlIEtGOCBEZWxp"
    "dmVyYWJsZSBmaWxlIHNpemUgOiAgIDAwNzAyNzBLQg0KCgAAAA=="
)
CMET_RECORD = base64.b64decode(_CMET_B64)

# --------------------------------------------------------------------------
# DATP: the table a device counts locations in.
#
# Nothing parses this record.  libmobi, KindleUnpack and calibre all track
# only its record number, so every field below was measured against
# kindlegen output rather than read anywhere: thirteen volumes built by the
# kindlegen on this machine (2 to 40 pages, uniform and mixed page sizes,
# flat and chaptered), four of them rebuilt from the same images a second
# time, and the reference volume
# Aposimz-01.mobi -- eighteen DATP records in
# all.  build_datp reproduces every one of them byte for byte apart from
# the alignment padding, which kindlegen leaves uninitialised; see
# tests/test_mobi_native.py and the DATP section of
# docs/mobi-container-research.md for the derivation.
#
# Why it matters: a device with no DATP counts positions in bytes and
# reports one location per 150 bytes of markup, and a position measured in
# bytes has no page to hang a chapter name on.  With DATP the same book
# reports one location per page and shows the chapter above the location
# line.  A bisection on hardware established that this record alone is the
# mechanism -- deleting it from a working KCC volume dropped a 176-location
# book to 700-plus, while renaming aids, page titles and RESC idrefs, and
# deleting CMET, all left it at 176.
#
# The record is two tables over the same quantity: the absolute position at
# which each page's body content splices back into its skeleton -- exactly
# the FRAG index's entry names, which is where the writer's own numbers
# come from.  The fine table is those positions delta-encoded, one uint16
# per location; the coarse table is a uint32 checkpoint every sixteenth
# location so a reader can seek without summing the deltas.
# --------------------------------------------------------------------------

# What offset 4 declares: the thirteen bytes at 8..20 that come before the
# coarse table.  4 + 4 + 13 is 21, which is where the payload begins in
# every sample.
_DATP_HEADER_LENGTH = 13

# One coarse checkpoint per sixteen fine entries.  Every sample agrees on
# the count -- floor(pages / 16), which is 0 at 15 pages, 1 at 16, still 1
# at 31, 2 at 32 and 10 at 175 -- so the stride is pinned from both sides.
_DATP_COARSE_STRIDE = 16

# The fine table is uint16, so a page whose markup is longer than this
# cannot be described at all.  A comic page runs to roughly 600 bytes, so
# this is unreachable in practice and is checked rather than assumed: a
# silently truncated delta would put every location after it in the wrong
# place, which is precisely the failure this record exists to prevent.
_DATP_MAX_STEP = 0xFFFF


def build_datp(insert_positions, *, include_origin=True):
    """The location table, from where each page's body splices back in.

    *insert_positions* are absolute positions in the text stream, one per
    page, ascending -- the same numbers :func:`build_frag_index` writes as
    its entry names.  That identity is not a convenience: it was how the
    format was recognised.  The running sums of the fine table in every
    kindlegen sample are the FRAG entry names of that same book, digit for
    digit, so DATP is not describing pages or bytes but the very splice
    points the FRAG index already records.

    ``include_origin=True`` reproduces kindlegen byte for byte: a synthetic
    zero position precedes the real page positions, so an N-page comic is
    displayed as locations 2 through N+1.  Kindle hardware also accepts the
    table without that origin and then displays the useful range 1 through N;
    maic's product writer uses that device-verified form.  Keeping the switch
    here preserves the kindlegen ground truth as a testable reference rather
    than rewriting the format history around the preferred UI.

    The layout, all big-endian (``fine_count`` is pages plus the optional
    origin):

        0..3    b"DATP"
        4..7    13, the header length -- the payload starts at 8 + 13
        8       1
        9       4
        10..11  the fine table's entry count
        12      2
        13..16  the last fine prefix sum, i.e. the last insert position
        17..20  0
        21..    the coarse table, uint32, floor((fine_count - 1) / 16) entries
        ...     the fine table, uint16, delta-encoded positions
        ...     zero padding to a four-byte boundary

    Bytes 8, 9 and 12 never varied across the samples and nothing explains
    them; 9 and 12 are the two tables' element widths in bytes, which is
    either the answer or a coincidence of two constants.  The word at 17
    was likewise always zero, and reads equally well as a reserved field or
    as the coarse table's own leading zero -- the two produce identical
    bytes, so the choice cannot be tested and does not matter.

    With kindlegen's leading zero, the declared count is pages+1 and that is
    also the number a device reports: a 175-page volume says 176 locations
    and opens its first visible page at location 2.  Without it, the same
    device reports 175 and opens the page at location 1; all real prefix sums
    are identical in the two forms.

    kindlegen leaves the trailing pad as whatever was in its buffer -- zero
    in twelve of the eighteen records measured, stale bytes in the other
    six, and rebuilding the same source images twice produced different
    padding each time.  This writes zeros, which is what kindlegen writes
    when its own buffer happens to be clean.
    """
    positions = [int(position) for position in insert_positions]
    if not positions:
        raise ValueError("a book with no pages has no locations to describe")

    steps, previous = ([0] if include_origin else []), 0
    for position in positions:
        if position < previous:
            raise ValueError(
                "insert positions must ascend: %d comes after %d"
                % (position, previous)
            )
        step = position - previous
        if step > _DATP_MAX_STEP:
            raise ValueError(
                "a page of %d bytes cannot be described by DATP's 16-bit "
                "table" % step
            )
        steps.append(step)
        previous = position

    record = bytearray(b"DATP")
    record += struct.pack(">I", _DATP_HEADER_LENGTH)
    record += struct.pack(">BBHB", 1, 4, len(steps), 2)
    record += struct.pack(">II", positions[-1], 0)
    # A reader infers the number of checkpoints as floor((fine_count-1)/16).
    # Checkpoint n is the prefix sum after 16n fine entries. With the origin
    # present that is positions[16n-2]; without it, positions[16n-1]. The
    # distinction is what keeps the adjusted table internally consistent
    # instead of merely changing its declared count.
    coarse_count = (len(steps) - 1) // _DATP_COARSE_STRIDE
    origin_shift = 2 if include_origin else 1
    for group in range(1, coarse_count + 1):
        record += struct.pack(
            ">I", positions[group * _DATP_COARSE_STRIDE - origin_shift])
    for step in steps:
        record += struct.pack(">H", step)
    record += b"\0" * (-len(record) % 4)
    return bytes(record)


# The library tile a MOBI reader shows is not the cover -- it is the
# separate, deliberately small resource EXTH 202/129 point at (see the
# comment above EXTH_THUMB_OFFSET).  calibre's writer2/resources.py rescales
# into ``MAX_THUMB_DIMEN = (180, 240)``, and the reference this project has
# already diffed against agrees rather than using some device-specific
# figure of its own: kindlegen's own thumbnail in
# ``Aposimz-01.mobi`` is a 169x240 JPEG -- the
# height calibre's box allows, and the width a source cover near that
# aspect produces when fit into it.  maic follows the same box.
_THUMBNAIL_BOX = (180, 240)


def _build_cover_resource(cover_data, quality=90, log_fn=None):
    """The cover again, as its own resource and in colour.

    EXTH 201 points here, and this is what a device shows on the library
    shelf and on the standby screen.  It used to be page one's bytes reused
    unchanged, which costs nothing and is wrong for one reason: a manga
    build greyscales its pages, so the tile came out single-channel too, and
    a device that renders grayscale pages perfectly well showed no cover at
    all.  A KCC volume greyscales 170 of its 175 pages and still writes an
    RGB cover and an RGB thumbnail.

    Re-encoding one image to gain three channels is a second lossy pass over
    the artwork, which is why the pages do not get one -- they are read by
    something that does not care.
    """
    import io

    from PIL import Image

    _log = log_fn or (lambda message: None)
    with Image.open(io.BytesIO(cover_data)) as opened:
        image = opened.convert("RGB")
    buffer = io.BytesIO()
    image.save(buffer, "JPEG", quality=quality, optimize=True)
    data = buffer.getvalue()
    _log("COVER: %dx%d RGB, %d bytes" % (image.size[0], image.size[1], len(data)))
    return data


def _build_cover_thumbnail(cover_data, quality=85, log_fn=None):
    """The cover, rescaled to the library tile a MOBI reader actually shows.

    ``build_markup`` never sees this image: it is not one of the pages a
    section owns, gets no ``aid``, and no page's markup embeds it as a
    ``kindle:embed`` reference.  It exists purely as the resource EXTH 202
    and 129 point at.  Downscaling is the whole point -- a manga cover
    straight off a scan is a multi-megabyte JPEG at the page's own
    resolution, and every place this field is read wants a tile a few
    kilobytes across, not the page again at a smaller size on disk.

    *quality* is 85, the same figure this module already defaults page
    encoding to elsewhere in the project, rather than the 100 KFX's own
    cover preview uses (``_THUMB_COVER_QUALITY`` in _page_groups.py, chosen
    there because that preview is the only place a KFX reader ever shows
    the cover at all). This resource competes with the opposite goal --
    keeping a MOBI small -- and at 180x240 pixels 85 stays comfortably under
    calibre's own ``MAX_THUMB_SIZE`` (16 KB) for a real manga cover without
    a second, size-driven compression pass this project has no reference
    for.
    """
    import io

    from PIL import Image

    _log = log_fn or (lambda message: None)
    with Image.open(io.BytesIO(cover_data)) as opened:
        # Always RGB, even from a grayscale page.  A KCC volume greyscales
        # its pages and keeps the cover and this thumbnail in colour, and
        # that split is not decoration: the pages go through the reader,
        # which is happy with one channel, while these two go to the library
        # tile and the standby screen, which showed nothing at all until
        # they were three.
        image = opened.convert("RGB")
        image.thumbnail(_THUMBNAIL_BOX, Image.LANCZOS)
        out = io.BytesIO()
        image.save(out, "JPEG", quality=quality, optimize=True)
        blob = out.getvalue()
    _log("COVER: thumbnail %dx%d, %d bytes" % (image.size[0], image.size[1], len(blob)))
    return blob


# A Palm database counts its records in sixteen bits, and every record offset
# is a 32-bit file position.
_MAX_RECORDS = 0xFFFF
_MAX_FILE_SIZE = 0xFFFFFFFF

# The database name is 32 bytes and has to end with a NUL, so 31 are usable.
_PALMDB_NAME_LENGTH = 32

# Palm counts seconds from 1904, not 1970.
_PALM_EPOCH_OFFSET = 2082844800


def content_asin(title, page_groups, spine=None):
    """A stable UUID-shaped identifier, hashed from the book's own content.

    A KCC volume carries one at EXTH 113 -- the UUID its source EPUB had --
    and a sideloaded book without one has nothing a device's library can key
    on but its file name.  Derived rather than random for the same reason
    :func:`content_unique_id` is: rebuilding a volume unchanged must not
    produce a book the library believes it has never seen.

    *spine* is folded in because the pages alone do not identify the book.
    Building one volume twice, once with facing pairs and once without,
    changes how it reads and not one pixel of it -- and two files carrying
    the same identifier are one book as far as a library is concerned, so
    the second would go missing rather than merely look like the first.
    """
    import hashlib

    digest = hashlib.sha256()
    digest.update(str(title or "").encode("utf-8"))
    for group in page_groups:
        for page in group:
            digest.update(b"%d,%d,%d;" % (int(page["width"]), int(page["height"]),
                                          len(page["data"])))
    for item in spine or ():
        digest.update(str(item).encode("utf-8") + b";")
    raw = digest.hexdigest()[:32]
    return "%s-%s-%s-%s-%s" % (raw[:8], raw[8:12], raw[12:16], raw[16:20], raw[20:32])


def content_unique_id(title, page_groups):
    """A deterministic MOBI ``unique_id``, hashed from the book's own content.

    ``build_record0`` defaults this field to 0 because it only has to land
    whatever value it is given; something upstream has to decide what that
    value is. calibre randomises it, but a random id means rebuilding the
    exact same volume produces a book a device's library treats as new --
    the same problem _kfx_native's ``content_identity`` solves for the ASIN,
    asset id and book id it hands KFX. This follows the same recipe: hash
    the title together with each page's dimensions and byte length, so the
    same volume always gets the same id and a changed one gets a different
    id, with no state to keep between builds.
    """
    import hashlib

    digest = hashlib.sha256()
    digest.update(str(title).encode("utf-8", "replace"))
    for group in page_groups:
        for page in group:
            digest.update(b"%d,%d,%d;" % (page["width"], page["height"], len(page["data"])))
    return int.from_bytes(digest.digest()[:4], "big")


def build_native_mobi_book(page_groups, toc_entries, *, title="Untitled",
                           authors=None, language="en", cde_type="PDOC",
                           canvas=(1272, 1696), reading_direction="rtl",
                           unique_id=None, joint=False,
                           alternate_spreads=False, log_fn=None):
    """Sections -> a complete MOBI container, as bytes.

    Nothing here touches the filesystem, which is what lets the whole writer
    be tested against tools/mobi_unpack.py without building a real volume.

    *toc_entries* is a list of ``(page index, chapter title)``; an empty
    one produces a book with no NCX at all rather than an empty index, and
    record 0 says so with the not-present sentinel.

    *unique_id* left at None is computed from the content itself via
    :func:`content_unique_id`, rather than left at ``build_record0``'s own
    default of 0 -- every book this function writes should carry an id, and
    a deterministic one at that.

    Every image becomes its own skeleton.  A two-image page group is carried
    as two RESC itemrefs with complementary ``page-spread`` properties, the
    structure kindlegen writes, rather than as one XHTML page with two images.

    A dedicated cover, RESC and a rescaled cover thumbnail are appended as
    resources after every page. EXTH 201 points at the dedicated cover, EXTH
    131 at RESC, and EXTH 202/129 at the thumbnail.
    ``page_groups[0][0]`` is the source image: _page_groups.py's own contract
    for ``page_groups`` -- shared with KFX -- is that group 0 is the cover and
    holds exactly one page.

    With ``joint=True`` the page resources live in a MOBI6 primary half and a
    KF8 record 0 follows a literal ``BOUNDARY`` record.  Record numbers in
    that second half are local to it, while its image and RESC offsets resolve
    against the primary half's resource base, exactly as in kindlegen output.
    The low-level default stays standalone for callers that test KF8 pieces
    in isolation; :func:`build_mobi_from_dir` always requests the joint form.
    """
    _log = log_fn or (lambda message: None)
    if not page_groups:
        raise ValueError("page_groups is empty")

    spine_groups, spine_toc, spread_properties = _flatten_kf8_spine(
        page_groups, toc_entries, reading_direction=reading_direction,
        alternate_spreads=alternate_spreads)
    pages, stylesheet, resources = build_markup(
        spine_groups, spine_toc, reading_direction=reading_direction,
        kcc_single_pages=True)
    for number, blob in enumerate(resources, 1):
        # A zero-length record cannot be stored: the record-info table is
        # nothing but offsets, so an empty record and the one after it start
        # in the same place and no reader can tell where either ends.
        # tools/mobi_unpack.py refuses exactly that, and finding out here
        # names the image instead of the symptom.
        if not blob:
            raise ValueError("resource %d has no data" % number)

    # Keep a dedicated cover resource, as kindlegen does. Reusing the first
    # page bytes is intentional: the separate record is about resource role,
    # not a second lossy re-encode of the artwork.
    cover = _build_cover_resource(resources[0], log_fn=_log)
    thumbnail = _build_cover_thumbnail(page_groups[0][0]["data"], log_fn=_log)

    flow = build_flow(pages, stylesheet)
    kf8_chapters = _kf8_ncx_chapters(spine_toc, flow.skeletons)
    text_records, text_padding, kf8_extra_data_flags = _kindle_text_records(
        flow.text, [(chapter[3], chapter[4]) for chapter in kf8_chapters])

    fdst = _build_fdst(flow.flows)
    skel = build_skel_index(flow.skeletons)
    frag = build_frag_index(flow.skeletons)
    ncx = build_ncx_index(spine_toc, flow.skeletons)
    resc = build_resc(spread_properties, reading_direction=reading_direction)
    # The location table, off the same splice points the FRAG index names --
    # taken from the flow rather than re-derived, so the two records cannot
    # disagree about where a page's body begins.
    datp = build_datp(
        [chunk.insert for skeleton in flow.skeletons
         for chunk in skeleton.chunks],
        # kindlegen prepends a synthetic origin and therefore exposes an
        # N-page volume as locations 2..N+1. Kindle hardware accepts the
        # same table without it and then reports the intuitive 1..N range.
        include_origin=False)

    # Record numbers are decided here, because record 0 has to name them and
    # every one of them sits after it.  An index is a *run* of records --
    # a header, its entries and its CNCX -- so the cursor steps by the run's
    # length rather than by one.  The NCX is the run that can be empty: a
    # book with no chapters gets no records and no record number, and the
    # resources simply start three records earlier.
    position = 1 + len(text_records) + len(text_padding)
    first_non_text_record = position
    frag_index = position
    position += len(frag)
    skel_index = position
    position += len(skel)
    ncx_index = position if ncx else _NOT_PRESENT
    position += len(ncx)
    first_resource_record = position
    position += len(resources)
    cover_offset = len(resources)
    position += 1
    resc_offset = len(resources) + 1
    position += 1
    thumbnail_offset = len(resources) + 2
    position += 1
    fdst_index = position
    position += 1
    flis_index = position
    fcis_index = position + 1
    datp_index = position + 2

    if unique_id is None:
        unique_id = content_unique_id(title, page_groups)
    asin = content_asin(title, page_groups, spread_properties)
    contributor = BUILD_STAMP

    if joint:
        # The KF8 half has its own, boundary-relative record namespace and no
        # image records of its own.  Its first-resource field therefore
        # points at its tail, while readers resolve kindle:embed references
        # against the MOBI6 header's shared resource base.
        k8_position = 1 + len(text_records) + len(text_padding)
        k8_first_non_text = k8_position
        k8_frag_index = k8_position
        k8_position += len(frag)
        k8_skel_index = k8_position
        k8_position += len(skel)
        k8_ncx_index = k8_position if ncx else _NOT_PRESENT
        k8_position += len(ncx)
        k8_first_resource = k8_position
        k8_fdst_index = k8_position
        k8_position += 1
        k8_flis_index = k8_position
        k8_fcis_index = k8_position + 1
        # DATP sits at the tail of the KF8 half, right before EOF, which is
        # where kindlegen puts it in every sample -- FDST, FLIS, FCIS, DATP,
        # EOF -- and offset 256 names it.
        k8_datp_index = k8_fcis_index + 1

        k8_record0 = build_record0(
            title=title, authors=authors, language=language, cde_type=cde_type,
            resource_count=0, canvas=canvas,
            reading_direction=reading_direction,
            # The markup only.  kindlegen stops text_length at the end of flow 0
        # and leaves the stylesheet outside it, so a device's notion of how
        # long a book is never includes a stylesheet.
        text_length=flow.flows[0][1], record_count=len(text_records),
            first_resource_record=k8_first_resource,
            first_non_text_record=k8_first_non_text,
            fdst_index=k8_fdst_index, fdst_count=len(flow.flows),
            skel_index=k8_skel_index, frag_index=k8_frag_index,
            ncx_index=k8_ncx_index, flis_index=k8_flis_index,
            fcis_index=k8_fcis_index, datp_index=k8_datp_index,
            unique_id=unique_id,
            asin=asin, contributor=contributor,
            cover_offset=cover_offset,
            thumbnail_offset=thumbnail_offset, resc_offset=resc_offset,
            extra_data_flags=kf8_extra_data_flags)
        k8_records = ([k8_record0] + text_records + text_padding + frag + skel + ncx
                      + [fdst, FLIS_RECORD, _fcis_record(flow.flows[0][1]),
                         datp, EOF_RECORD])

        mobi6_text, mobi6_page_starts = build_mobi6_markup(spine_groups)
        mobi6_chapters = _mobi6_ncx_chapters(
            spine_toc, mobi6_page_starts, len(mobi6_text))
        mobi6_text_records, mobi6_padding, mobi6_extra_data_flags = (
            _kindle_text_records(
                mobi6_text,
                [(chapter[2], chapter[3]) for chapter in mobi6_chapters]))
        mobi6_ncx = build_mobi6_ncx_index(
            spine_toc, mobi6_page_starts, len(mobi6_text))

        mobi6_position = 1 + len(mobi6_text_records) + len(mobi6_padding)
        mobi6_ncx_index = mobi6_position if mobi6_ncx else _NOT_PRESENT
        mobi6_position += len(mobi6_ncx)
        mobi6_first_resource = mobi6_position
        mobi6_position += len(resources) + 3  # pages, cover, RESC, thumbnail
        mobi6_flis_index = mobi6_position
        mobi6_fcis_index = mobi6_position + 1
        # CMET sits between FCIS and BOUNDARY in the reference -- see
        # CMET_RECORD above.  Nothing in the header names it by record
        # number, so inserting it only has to shift boundary_record (and
        # everything counted from it) by one when the switch is on.
        boundary_record = mobi6_position + 2 + (1 if _CLAIM_KINDLEGEN else 0)
        k8_boundary = boundary_record + 1

        mobi6_record0 = build_record0(
            title=title, authors=authors, language=language, cde_type=cde_type,
            resource_count=len(resources) + 3, canvas=canvas,
            reading_direction=reading_direction,
            text_length=len(mobi6_text), record_count=len(mobi6_text_records),
            first_resource_record=mobi6_first_resource,
            first_non_text_record=(mobi6_ncx_index if mobi6_ncx
                                   else mobi6_first_resource),
            fdst_index=_NOT_PRESENT, fdst_count=1,
            skel_index=_NOT_PRESENT, frag_index=_NOT_PRESENT,
            ncx_index=mobi6_ncx_index, flis_index=mobi6_flis_index,
            fcis_index=mobi6_fcis_index, unique_id=unique_id,
            asin=asin, contributor=contributor,
            cover_offset=cover_offset,
            thumbnail_offset=thumbnail_offset, resc_offset=resc_offset,
            file_version=6, boundary=k8_boundary,
            extra_data_flags=mobi6_extra_data_flags)

        mobi6_tail = [cover, resc, thumbnail, FLIS_RECORD,
                     _fcis_record(len(mobi6_text))]
        if _CLAIM_KINDLEGEN:
            mobi6_tail.append(CMET_RECORD)
        mobi6_tail.append(b"BOUNDARY")
        records = ([mobi6_record0] + mobi6_text_records + mobi6_padding + mobi6_ncx
                   + list(resources) + mobi6_tail
                   + k8_records)
        _log("MOBI: joint MOBI6+KF8 at record %d; %d pages, %d records in all"
             % (k8_boundary, len(spine_groups), len(records)))
        return _write_palmdb(title, records)

    record0 = build_record0(
        title=title, authors=authors, language=language, cde_type=cde_type,
        # +3 for the cover, RESC and thumbnail: calibre's num_of_resources is
        # len(self.records) - before across the whole resource-append step
        # (writer8/mobi.py), and kindlegen's MOBI6 header counts both records.
        resource_count=len(resources) + 3, canvas=canvas,
        reading_direction=reading_direction,
        # The markup only.  kindlegen stops text_length at the end of flow 0
        # and leaves the stylesheet outside it, so a device's notion of how
        # long a book is never includes a stylesheet.
        text_length=flow.flows[0][1], record_count=len(text_records),
        first_resource_record=first_resource_record,
        first_non_text_record=first_non_text_record,
        fdst_index=fdst_index, fdst_count=len(flow.flows),
        skel_index=skel_index, frag_index=frag_index, ncx_index=ncx_index,
        flis_index=flis_index, fcis_index=fcis_index, datp_index=datp_index,
        unique_id=unique_id,
        asin=asin, contributor=contributor,
        cover_offset=cover_offset, thumbnail_offset=thumbnail_offset,
        resc_offset=resc_offset, extra_data_flags=kf8_extra_data_flags)

    # DATP goes before EOF here for the same reason it does in the joint
    # half: the record describes the KF8 markup, and a standalone KF8 book
    # is that half on its own -- there is no reading on which one form of
    # this writer's output should count locations by page and the other by
    # byte.
    records = ([record0] + text_records + text_padding + frag + skel + ncx
               + list(resources) + [cover, resc, thumbnail, fdst]
               + [FLIS_RECORD, _fcis_record(flow.flows[0][1]), datp,
                  EOF_RECORD])
    _log("MOBI: %d skeletons, %d page resources plus cover, RESC and thumbnail, "
         "%d text records, "
         "%d records in all"
         % (len(spine_groups), len(resources), len(text_records), len(records)))
    return _write_palmdb(title, records)


def _build_fdst(flows):
    """The flow table: where the markup ends and the stylesheet begins.

    The data offset is always 12 and libmobi refuses the record when it is
    anything else, so it is written as the constant it is rather than
    measured.
    """
    blob = b"FDST" + struct.pack(">II", 12, len(flows))
    for start, end in flows:
        blob += struct.pack(">II", start, end)
    return blob


def _fcis_record(text_length):
    """FCIS, with the one field in it that is not a constant."""
    return _FCIS_PREFIX + struct.pack(">I", int(text_length)) + _FCIS_SUFFIX


def _palmdb_name(title):
    """The database's 32-byte name field.

    Palm stores the name as a NUL-terminated 32-byte field, so 31 bytes are
    usable, and a UTF-8 title does not care where byte 31 falls.  Slicing
    there can cut a character in half, which is a replacement glyph in
    whatever lists the file and a byte sequence no decoder accepts.  The
    name is built up a character at a time instead and simply stops before
    the one that would not fit.

    (calibre sidesteps this by transliterating the title to ASCII first.
    maic keeps the real characters: the field is bytes as far as Palm is
    concerned, this project's own reader decodes it as UTF-8, and a Japanese
    title reduced to underscores is less useful than a short true one.)
    """
    name = b""
    for character in str(title or ""):
        encoded = character.encode("utf-8", "replace")
        if character == "\0":
            encoded = b"_"          # a NUL would end the name early
        if len(name) + len(encoded) > _PALMDB_NAME_LENGTH - 1:
            break
        name += encoded
    return name.ljust(_PALMDB_NAME_LENGTH, b"\0")


def _write_palmdb(title, records):
    """Wrap the records in a Palm database.

    The 78-byte header is followed by one eight-byte entry per record -- a
    four-byte file offset, a one-byte attribute field and a **three**-byte
    unique id -- then two bytes of gap, then the records themselves, back to
    back.  The id being three bytes and not four is the part worth stating:
    an entry packed as offset/byte/byte/short happens to lay down the same
    bytes for small record numbers, and no reader that only wants the offset
    could tell the difference.

    The ids and the seed follow calibre's writer8/mobi.py, which numbers
    records ``2 * index`` and seeds the header with ``2 * count - 1``.
    """
    if not records:
        raise ValueError("a Palm database needs at least one record")
    if len(records) > _MAX_RECORDS:
        raise ValueError(
            "a Palm database counts its records in 16 bits and this one has "
            "%d" % len(records)
        )

    header = bytearray(_palmdb_name(title))
    stamp = int(time.time()) + _PALM_EPOCH_OFFSET
    # attributes, version, created, modified, backed up, modification
    # number, app-info offset, sort-info offset.
    header += struct.pack(">HHIIIIII", 0, 0, stamp, stamp, 0, 0, 0, 0)
    header += b"BOOKMOBI"                       # type and creator
    header += struct.pack(">IIH", 2 * len(records) - 1, 0, len(records))

    offset = len(header) + len(records) * 8 + 2
    for index, record in enumerate(records):
        if not record:
            raise ValueError(
                "record %d is empty, and a record is delimited by where the "
                "next one starts" % index
            )
        if offset > _MAX_FILE_SIZE:
            raise ValueError("the book is too large for a Palm database")
        header += struct.pack(">I", offset)
        header += b"\0" + struct.pack(">I", 2 * index)[1:]
        offset += len(record)
    header += b"\0\0"
    return bytes(header) + b"".join(records)


def build_mobi_from_dir(
    source_dir,
    out_path,
    *,
    title=None,
    authors=None,
    language=None,
    vol_prefix="Vol.",
    excluded=None,
    bookmarks=None,
    cde_type="PDOC",
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
    progress_fn=None,
    stop_requested_fn=None,
    log_fn=None,
):
    """Source folder -> joint MOBI6+KF8, without KCC or kindlegen.

    This mirrors build_kfx_from_dir in maic/_kfx_native.py argument for
    argument -- same defaults, same ComicInfo.xml and sidecar fallbacks for
    metadata and page selection -- except for the knobs MOBI has no use for
    (thumbnails, thumbnail_pad, image_fit, background_color, asin, asset_id,
    book_id: MOBI stores no page-flip strip and carries its own notion of
    identity, below). ``facing_pages`` defaults on just as it does for KFX.
    KF8 keeps each page in its own viewport and records the pair in RESC; the
    MOBI6 fallback keeps the same pages in reading order with explicit page
    breaks.  This is KCC/kindlegen's joint-book structure.

    Nothing is written to *out_path* until the whole container is built in
    memory: a stop request raises out of page_groups_from_dir before
    build_native_mobi_book is ever called, so no partial file is ever left
    on disk.
    """
    _log = log_fn or (lambda msg: None)

    from ._image_pipeline import device_canvas as _resolve_canvas

    device_canvas = _resolve_canvas(device_canvas, hq=hq)
    _log("DEVICE: canvas %dx%d" % device_canvas)

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
        # MOBI stores no page-flip strip, so building one would be a 512px
        # resize and a re-encode on every page, thrown away. Not to be
        # confused with build_native_kfx_book's tri-state `thumbnails`,
        # which this path has no equivalent of.
        build_previews=False,
        # MOBI's library tile is the separate resource build_native_mobi_book
        # appends (see EXTH_THUMB_OFFSET), not the cover itself, so nothing
        # here depends on the cover keeping its source size the way KFX's
        # cover-as-library-tile does. Hardcoded rather than exposed as a
        # parameter of this function, the same way build_previews is above.
        resize_cover=True,
        progress_fn=progress_fn,
        stop_requested_fn=stop_requested_fn,
        log_fn=_log,
    )

    title = title or meta["title"] or os.path.basename(str(source_dir).rstrip("/\\"))
    authors = authors or meta["authors"]
    language = language or meta["language"] or "en"

    # original-resolution is the screen the book was built for, not the size
    # of any page in it.  kindlegen writes the device canvas -- 1264x1680 for
    # a volume whose pages are 1264x1637, 1102x1680 and a dozen other shapes,
    # because a fixed-layout comic's pages genuinely differ from one another
    # and each states its own size in its own viewport.  Deriving this from
    # the pages instead put the largest page in the book here, which is a
    # different number that answers a different question.
    canvas = device_canvas

    # The existing W/B margins control is also KCC's page-background choice:
    # auto detects each source, while white/black force every page. The
    # background belongs in XHTML even when no pixel padding was requested.
    _set_page_backgrounds(page_groups, borders_color, log_fn=_log)

    data = build_native_mobi_book(
        page_groups,
        toc_entries,
        title=title,
        authors=authors,
        language=language,
        cde_type=cde_type,
        canvas=canvas,
        reading_direction=reading_direction,
        joint=True,
        alternate_spreads=facing_pages,
        log_fn=_log,
    )
    with open(out_path, "wb") as handle:
        handle.write(data)
    _log("MOBI_OUT: %s (%d KB)" % (os.path.basename(out_path), len(data) // 1024))
    return out_path
