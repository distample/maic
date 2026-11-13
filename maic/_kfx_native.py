"""Native KFX generation for image-only fixed-layout comics.

maic builds page images and the KFX fragment graph directly without the
EPUB-to-KPF round trip through Kindle Previewer. The Python implementation
uses kfxlib for Ion/YJ types and final container serialization.
"""

import io
import os
from datetime import date as _date

from .version import BUILD_STAMP

# The source-to-pages half lives in its own module now; this file only builds
# the KFX container from what it produces.
from ._page_groups import (
    _decode_image_size,
    _image_format,
    _make_thumbnail,
    _thumb_mode,
    _THUMB_COVER_QUALITY,
    _THUMB_QUALITY,
)

# Re-exported because tests/test_native_source.py imports them from here in
# about sixty places.
from ._page_groups import (  # noqa: F401
    _pages_from_file,
    _thumbnail_from_image,
    _THUMB_BOX,
    page_groups_from_dir,
    pair_facing_pages,
)

# Symbols for image container formats, from kfxlib.resources.FORMAT_SYMBOLS.
_FORMAT_SYMBOL = {"jpg": "$285", "png": "$284", "gif": "$286"}

# -- Lazy kfxlib type accessors (mirrors _kfx_postprocess) --
_IS = None
_ion_annotation = None
_ion_blob = None
_ion_struct = None
_yj_fragment = None
_yj_book = None
_yj_metadata = None


def _init_kfxlib_types():
    global _IS, _ion_annotation, _ion_blob, _ion_struct, _yj_fragment, _yj_book, _yj_metadata
    if _IS is not None:
        return
    try:
        from calibre_plugins.kfx_output.kfxlib.ion import IS, IonAnnotation, IonBLOB, IonStruct
        from calibre_plugins.kfx_output.kfxlib.yj_container import YJFragment
        from calibre_plugins.kfx_output.kfxlib import YJ_Book, YJ_Metadata
    except Exception:
        from kfxlib.ion import IS, IonAnnotation, IonBLOB, IonStruct  # type: ignore[import-not-found]
        from kfxlib.yj_container import YJFragment  # type: ignore[import-not-found]
        from kfxlib import YJ_Book, YJ_Metadata  # type: ignore[import-not-found]
    _IS = IS
    _ion_annotation = IonAnnotation
    _ion_blob = IonBLOB
    _ion_struct = IonStruct
    _yj_fragment = YJFragment
    _yj_book = YJ_Book
    _yj_metadata = YJ_Metadata


class _IdGen:
    """Allocate the short base36-ish local symbol names KFX uses (c0, c8, cT...).

    kfxlib validates local symbol names by prefix (``allowed_symbol_prefix``),
    so section/layout/entity/style/nav names must keep their conventional
    first letter.
    """

    _ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"

    def __init__(self, prefix):
        self.prefix = prefix
        self._n = 0

    def next(self):
        n = self._n
        self._n += 1
        if n == 0:
            return "%s0" % self.prefix
        out = ""
        while n:
            n, rem = divmod(n, 36)
            out = self._ALPHABET[rem] + out
        return "%s%s" % (self.prefix, out)


class _Builder:
    def __init__(self, book, log_fn=None):
        self.book = book
        self._log = log_fn or (lambda msg: None)
        self.sections = _IdGen("c")
        self.layouts = _IdGen("l")
        self.entities = _IdGen("e")
        self.navs = _IdGen("n")
        self._pid = 1
        self._resource_n = 1

    def pid(self):
        pid = self._pid
        self._pid += 1
        return pid

    def sym(self, name):
        """Register a local symbol and return it as an IonSymbol."""
        return self.book.create_local_symbol(name)

    def resource_name(self):
        name = "resource/rsrc%d" % self._resource_n
        self._resource_n += 1
        return name

    def add(self, ftype, fid, value):
        frag = _yj_fragment(ftype=_IS(ftype), fid=_IS(fid) if fid else None, value=value)
        self.book.fragments.append(frag)
        return frag


def _jpeg_has_restart_markers(data):
    for i in range(len(data) - 1):
        if data[i] == 0xFF and 0xD0 <= data[i + 1] <= 0xD7:
            return True
    return False


def _mk_version(major, minor=0):
    return _ion_struct(_IS("version"), _ion_struct(_IS("$587"), major, _IS("$588"), minor))


def _kv(key, value):
    return _ion_struct(_IS("$492"), key, _IS("$307"), value)


def _category(name, entries):
    return _ion_struct(_IS("$495"), name, _IS("$258"), [_kv(k, v) for k, v in entries])


def build_native_kfx_book(
    page_groups,
    *,
    title="Untitled",
    authors=None,
    language="en",
    publisher=None,
    issue_date=None,
    cde_type="PDOC",
    asin=None,
    asset_id=None,
    book_id=None,
    thumbnails=True,
    thumbnail_pad="none",
    toc_entries=None,
    image_fit="box",
    reading_direction=None,
    canvas=None,
    background_color=None,
    thumbnail_pad_color=(255, 255, 255),
    page_list=True,
    log_fn=None,
):
    """Build a complete ``YJ_Book`` from page images.

    Parameters
    ----------
    page_groups : list[list[dict]]
        Sections, in reading order.  Group 0 is the cover and must hold exactly
        one page.  Later groups hold one page (single) or two (facing spread).
        Each page dict needs ``data`` (image bytes) and optionally ``width`` /
        ``height`` (decoded from the image when absent).
    thumbnails : {"full", "reuse", "off"} or bool
        What ``$214`` points at for a page.  ``"full"`` stores a separate 512px
        preview, the way every store book does; ``"reuse"`` points the page at
        itself so nothing extra is stored; ``"off"`` leaves it without one.  The
        cover is exempt and always keeps a real preview.
    toc_entries : list[tuple[int, str]] or None
        ``(page_index, title)`` pairs for the table of contents, counting pages
        in reading order with the cover as page 0.  A page and not a section:
        a facing pair holds two pages, and a chapter that opens on the far one
        has to say so or the entry lands a page short of the chapter.
    image_fit : {"box", "contain"}
        Which of the two style profiles found in Amazon's own comics to emit.

        ``"box"`` reproduces the profile maic's postprocess targets today
        (B09YVK8W81, B0FH45YTXR and others): ``sJ`` at 100%x100%, a leaf style
        holding a fixed box and ``$580=$320``.  The image is drawn at the box
        size, so **the box must share the image's aspect ratio** or the page is
        stretched.  Every book measured in this profile keeps them equal.

        ``"contain"`` reproduces the other profile (B0DV8JK61F, B0D615X5TX,
        B09FP6VPN7 and others): four nesting levels, leaf and middle styles
        carrying ``$546=$377`` with ``$183=$324/$488``, and a page-container
        style holding ``$19``, an ARGB background colour.  Here the image keeps
        its own proportions inside the canvas whatever their aspects, and the
        remaining area shows that colour -- no padded pixels needed.
        B0D615X5TX ships a 1725x2587 box over a 1338x1920 image, so the aspects
        genuinely differ there.
    canvas : (int, int) or None
        Canvas box for "contain".  Defaults to the largest page.
    background_color : int or None
        ARGB for "contain", e.g. ``0xFF808080``.  Amazon uses opaque black in
        every book in the corpus that sets it, but on device that exact value
        does not paint -- see the notes in ``docs/kfx-container-research.md``.
    thumbnail_pad_color : (int, int, int)
        Fill for the thumbnail padding that keeps the Page Flip strip from
        stretching previews.  Independent of ``background_color``.
    """
    _init_kfxlib_types()
    _log = log_fn or (lambda msg: None)

    if not page_groups:
        raise ValueError("page_groups is empty")
    if len(page_groups[0]) != 1:
        raise ValueError("the cover group must hold exactly one page")

    book = _yj_book("native.kfx")
    b = _Builder(book, log_fn=_log)

    # Match the Amazon fixed-layout comic pattern used by _kfx_postprocess:
    # $192 is the reading direction ($375=rtl, $376=ltr), while $560 remains
    # horizontal-tb ($557) in both modes.  $559 is vertical-rl writing mode,
    # not a second RTL flag; using it for manga made the two checkbox states
    # collapse to right-to-left behaviour on Kindle.
    _rtl = str(reading_direction or "rtl").strip().lower() != "ltr"
    direction_symbol = "$375" if _rtl else "$376"
    # $192 answers two different questions depending on where it sits.  In $538
    # it is the book's page progression, which is what the checkbox sets.  On a
    # page node it is the direction of that box's own content, and a page
    # holding one image has no content that runs either way: all 14 reference
    # store files write $376 on their page nodes even in a right-to-left book,
    # and so does Amazon's conversion of a maic EPUB that asked for RTL (its
    # own $538 says $375).  Feeding the book's direction to the nodes as well
    # was the one thing maic did that no reference file does.
    node_direction_symbol = "$376"
    progression_symbol = "$557"

    contain = image_fit == "contain"
    thumb_mode = _thumb_mode(thumbnails)
    bg = 0xFF000000 if background_color is None else int(background_color)
    thumb_aspect = None
    # Kept separate from $19 on purpose: this one is baked into the thumbnail
    # pixels and shows up in the Page Flip strip and the spread mini-preview,
    # where a dark bar reads as a defect rather than as a page margin.
    thumb_rgb = tuple(thumbnail_pad_color)
    # "pages" pads every preview except the halves of a spread, "all" pads
    # those too, "none" leaves each preview the shape of its own page.  "none"
    # is the answer: the strip letterboxes a preview into its slot rather than
    # stretching it -- device-confirmed on a book whose pages were padded to
    # 1440x1920 while their previews kept 28 different shapes of their own.
    # Padding would only bake white into the preview for nothing.
    thumb_pad_mode = str(thumbnail_pad or "none").strip().lower()
    if thumb_pad_mode is True:
        thumb_pad_mode = "pages"
    if contain and canvas and thumb_pad_mode in {"pages", "all"}:
        thumb_aspect = float(canvas[0]) / float(canvas[1])

    # -- Images: $164 entities + $417 resources ---------------------------
    for group_index, group in enumerate(page_groups):
        is_half = len(group) == 2
        # The cover's preview feeds the library grid and the standby screen
        # rather than the Page Flip strip, so it is built whatever the pages do,
        # from the cover itself and at full quality: it is shown far larger than
        # a page ever is in the strip, and there is one of it.
        is_cover = group_index == 0
        page_mode = "full" if is_cover else thumb_mode
        for page in group:
            data = page["data"]
            if not page.get("width") or not page.get("height"):
                page["width"], page["height"] = _decode_image_size(data)
            fmt = _image_format(data)

            eid = b.sym(b.entities.next())
            res_name = b.resource_name()
            b.sym(res_name)

            value = _ion_struct(
                _IS("$175"), eid,
                _IS("$161"), _IS(_FORMAT_SYMBOL.get(fmt, "$285")),
                _IS("$162"), "image/%s" % fmt,
                # $165 must be a plain string, not a symbol.
                _IS("$165"), res_name,
                _IS("$422"), int(page["width"]),
                _IS("$423"), int(page["height"]),
            )
            b.add("$417", res_name, _ion_blob(data))

            if page_mode == "reuse":
                # No second blob: the page entity is its own preview, and the
                # reader is left to scale the full-size image into the strip.
                value[_IS("$214")] = eid
            elif page_mode == "full":
                try:
                    # The Page Flip strip draws each preview inside a frame, so
                    # any white the page carries reads as the preview failing to
                    # fill its box.  Where the driver already cut a preview from
                    # the art before it padded the page, ship that one: it is
                    # edge to edge, and re-encoding it would only lose a
                    # generation.
                    ready = None if is_cover else page.get("thumb_data")
                    if ready:
                        thumb_data = ready
                        tw, th = page.get("thumb_size") or _decode_image_size(ready)
                    else:
                        # A spread half keeps its own shape by default: the spread
                        # mini-preview butts the two together, and padding puts a
                        # bar down the middle there.
                        pad_this = thumb_aspect if (thumb_pad_mode == "all" or not is_half) else None
                        thumb_data, tw, th = _make_thumbnail(
                            data, pad_this, thumb_rgb,
                            _THUMB_COVER_QUALITY if is_cover else _THUMB_QUALITY)
                except Exception as exc:
                    _log("THUMB: skipped for %s (%s)" % (eid, exc))
                else:
                    thumb_eid = b.sym("%s-thumb" % eid)
                    thumb_res = "%s-thumb" % res_name
                    b.sym(thumb_res)
                    value[_IS("$214")] = thumb_eid
                    b.add("$417", thumb_res, _ion_blob(thumb_data))
                    b.add("$164", thumb_eid, _ion_struct(
                        _IS("$175"), thumb_eid,
                        _IS("$161"), _IS("$285"),
                        _IS("$162"), "image/jpg",
                        _IS("$165"), thumb_res,
                        _IS("$422"), int(tw),
                        _IS("$423"), int(th),
                    ))

            b.add("$164", eid, value)
            page["eid"] = eid
            page["is_jpeg"] = fmt == "jpg"
            page["has_rst"] = page["is_jpeg"] and _jpeg_has_restart_markers(data)

    # -- Styles ------------------------------------------------------------
    # sG covers full pages, sH the narrower halves of a split spread.
    full = [p for g in page_groups[1:] if len(g) == 1 for p in g]
    halves = [p for g in page_groups[1:] if len(g) == 2 for p in g]
    all_pages = [p for g in page_groups for p in g]

    sg_w = max([p["width"] for p in full] or [p["width"] for p in all_pages])
    sg_h = max([p["height"] for p in full] or [p["height"] for p in all_pages])
    sh_w = max([p["width"] for p in halves] or [0])
    sh_h = max([p["height"] for p in halves] or [0])

    sm = sp = None

    if contain:
        # One canvas for every page.  With $546=$377 the image keeps its own
        # proportions inside it whatever its aspect, so nothing needs padding,
        # and sP's $19 fills whatever the image does not cover.
        cw, ch = canvas or (sg_w, sg_h)
        sp = b.sym("sP")
        b.add("$157", sp, _ion_struct(
            _IS("$19"), bg,
            _IS("$70"), 0xFFFFFFFF,
            _IS("$173"), sp,
        ))
        sm = b.sym("sM")
        b.add("$157", sm, _ion_struct(
            _IS("$56"), float(cw), _IS("$57"), float(ch),
            _IS("$546"), _IS("$377"), _IS("$173"), sm, _IS("$183"), _IS("$488"),
            # $580=$320 is the centre value of -kfx-box-align, the alignment
            # property the other profile uses.  Without it the device anchors
            # the image top-left inside the larger box (device-confirmed).
            _IS("$580"), _IS("$320"),
        ))
        sj = b.sym("sJ")
        b.add("$157", sj, _ion_struct(
            _IS("$173"), sj, _IS("$183"), _IS("$324"), _IS("$580"), _IS("$320")))
        # There is no fit mode.  Measured across all 14 store samples, on 1016
        # page nodes: the leaf style box always shares the image's aspect ratio,
        # worst deviation 0.0004, no exceptions.  Publishers with mixed aspects
        # ship one style per aspect -- B09FP6VPN7 uses s32 at 1153x865 for its
        # one landscape frame beside sG at 1153x1730 for the portraits.
        # So: one style per distinct image size, and $19 on the viewport fills
        # whatever the screen has left over.
        by_size = {}
        for page in all_pages:
            by_size.setdefault((int(page["width"]), int(page["height"])), None)
        for i, size in enumerate(sorted(by_size)):
            sid = b.sym("sI%d" % i)
            b.add("$157", sid, _ion_struct(
                _IS("$56"), float(size[0]), _IS("$57"), float(size[1]),
                _IS("$546"), _IS("$377"), _IS("$173"), sid, _IS("$183"), _IS("$324"),
            ))
            by_size[size] = sid
        contain_styles = by_size
        sg = sh = None
        sg_w, sg_h = int(cw), int(ch)
        _log("STYLES: contain profile, %d size styles, background=#%08X"
             % (len(by_size), bg))

    if not contain:
        sj = b.sym("sJ")
        b.add("$157", sj, _ion_struct(
            _IS("$56"), _ion_struct(_IS("$307"), 100.0, _IS("$306"), _IS("$314")),
            _IS("$57"), _ion_struct(_IS("$307"), 100.0, _IS("$306"), _IS("$314")),
            _IS("$10"), "ja",
            _IS("$173"), sj,
        ))

        def _leaf_style(name, w, h):
            sid = b.sym(name)
            b.add("$157", sid, _ion_struct(
                _IS("$56"), float(w),
                _IS("$57"), float(h),
                _IS("$58"), 0.0,
                _IS("$59"), 0.0,
                _IS("$580"), _IS("$320"),
                _IS("$173"), sid,
            ))
            return sid

        sg = _leaf_style("sG", sg_w, sg_h)
        sh = _leaf_style("sH", sh_w, sh_h) if (sh_w and sh_h) else sg
        _log("STYLES: sG=%dx%d sH=%s"
             % (sg_w, sg_h, "%dx%d" % (sh_w, sh_h) if sh is not sg else "(=sG)"))

    def _leaf_for(page, fallback_style, fallback_w, fallback_h):
        """Style and viewport box for one page image."""
        if contain:
            size = (int(page["width"]), int(page["height"]))
            return contain_styles[size], size[0], size[1]
        return fallback_style, fallback_w, fallback_h

    def _wrap(leaf_node, plain=False):
        """Nest a leaf under the profile's container levels.

        *plain* skips the contain-profile extras.  Spread halves use it: their
        box already equals the image, so they need no background and no middle
        container, and the box they would otherwise inherit is the full canvas.

        That last part is the load-bearing one, and it is not about overflow.
        A leaf style's $56/$57 are the size the image is *drawn* at, not a
        frame it is fitted inside -- see the $546 correction in
        docs/kfx-container-research.md.  Put a 1338x1920 half in the canvas's
        1400x1920 box and the device draws it 1400 wide: a 4.6% horizontal
        stretch, no letterboxing.  Device-confirmed 2026-08-23 against a probe
        build that did exactly that, which is also what Amazon's own
        Send-to-Kindle conversion does to every bisected half it is handed.
        """
        node = _ion_struct(
            _IS("$155"), b.pid(),
            _IS("$156"), _IS("$323"),
            _IS("$157"), sj,
            _IS("$159"), _IS("$270"),
            _IS("$146"), [leaf_node],
        )
        if contain and not plain:
            # Amazon's "contain" books add one more level between viewport and sJ.
            node = _ion_struct(
                _IS("$155"), b.pid(),
                _IS("$156"), _IS("$323"),
                _IS("$157"), sm,
                _IS("$159"), _IS("$270"),
                _IS("$146"), [node],
            )
        return node

    def _viewport(child, width, height, plain=False):
        node = _ion_struct(
            _IS("$155"), b.pid(),
            _IS("$192"), _IS(node_direction_symbol),
            _IS("$16"), 16.0,
            _IS("$560"), _IS("$557"),
            _IS("$66"), int(width),
            _IS("$67"), int(height),
            _IS("$156"), _IS("$326"),
            _IS("$140"), _IS("$320"),
            _IS("$159"), _IS("$270"),
            _IS("$146"), [child],
        )
        if contain and not plain:
            node[_IS("$157")] = sp
        return node

    # -- Sections and layouts ---------------------------------------------
    section_ids = []
    # One pid per page, which is what both the page list and the TOC need: a
    # facing pair is one section but two numbered pages, and a chapter can open
    # on either of them.  These are content-node pids, the space $246 navigates
    # in -- not page["eid"], which names the image resource and resolves to
    # nothing from a nav entry.
    page_start_pid = []

    # A TOC entry names a page; the section holding it is what carries the
    # IS_TARGET_SECTION marker below, so the one has to be looked up from the
    # other.
    group_of_page = []
    for index, group in enumerate(page_groups):
        group_of_page.extend([index] * len(group))

    # Kindle Previewer emits a "<section>-ad" $597 carrying IS_TARGET_SECTION
    # only for sections something navigates to, not for every section.
    # Measured: 10 for 91 sections with a 12-entry TOC; Amazon ships 3 for 11.
    nav_target_groups = {0}
    for page_index, _ in (toc_entries or []):
        if 0 <= page_index < len(group_of_page):
            nav_target_groups.add(group_of_page[page_index])

    for index, group in enumerate(page_groups):
        sid = b.sym(b.sections.next())
        lid = b.sym(b.layouts.next())
        section_ids.append(sid)
        item_pid = b.pid()

        if index == 0:
            # Cover: flat $271 node, section item carries explicit dimensions.
            page = group[0]
            cover_pid = b.pid()
            b.add("$259", lid, _ion_struct(_IS("$176"), lid, _IS("$146"), [
                _ion_struct(
                    _IS("$159"), _IS("$271"),
                    _IS("$155"), cover_pid,
                    _IS("$175"), page["eid"],
                ),
            ]))
            item = _ion_struct(
                _IS("$155"), item_pid,
                _IS("$176"), lid,
                _IS("$434"), _IS("$441"),
                _IS("$159"), _IS("$270"),
                _IS("$156"), _IS("$326"),
                _IS("$140"), _IS("$320"),
                _IS("$66"), int(page["width"]),
                _IS("$67"), int(page["height"]),
            )
            page_start_pid.append(cover_pid)

        elif len(group) == 1:
            page = group[0]
            style, box_w, box_h = _leaf_for(page, sg, sg_w, sg_h)
            wrapper = _wrap(_ion_struct(
                _IS("$155"), b.pid(),
                _IS("$157"), style,
                _IS("$159"), _IS("$271"),
                _IS("$175"), page["eid"],
            ))
            if contain:
                # The background lives on the viewport style, so every page
                # needs one -- not only the halves of a spread.  The viewport is
                # the full canvas while the leaf keeps the image's own box, so
                # there is an actual uncovered area for $19 to paint.  With both
                # set to the image size (as Amazon ships them) that area is
                # empty and no colour can show.
                wrapper = _viewport(wrapper, sg_w, sg_h)
            pass_pid = wrapper.get("$155")
            b.add("$259", lid, _ion_struct(_IS("$176"), lid, _IS("$146"), [wrapper]))
            item = _ion_struct(
                _IS("$192"), _IS(node_direction_symbol),
                _IS("$16"), 16.0,
                _IS("$560"), _IS("$557"),
                _IS("$66"), int(sg_w),
                _IS("$67"), int(sg_h),
                _IS("$434"), _IS("$441"),
                _IS("$156"), _IS("$326"),
                _IS("$140"), _IS("$320"),
                _IS("$159"), _IS("$270"),
                _IS("$155"), item_pid,
                _IS("$176"), lid,
            )
            page_start_pid.append(pass_pid)

        else:
            # Facing spread: each half gets an outer viewport page.
            outer_nodes = []
            for page in group[:2]:
                style, box_w, box_h = _leaf_for(page, sh, sh_w or sg_w, sh_h or sg_h)
                outer_nodes.append(_viewport(
                    _wrap(_ion_struct(
                        _IS("$155"), b.pid(),
                        _IS("$157"), style,
                        _IS("$159"), _IS("$271"),
                        _IS("$175"), page["eid"],
                    ), plain=contain),
                    box_w, box_h, plain=contain,
                ))
            b.add("$259", lid, _ion_struct(_IS("$176"), lid, _IS("$146"), outer_nodes))
            item = _ion_struct(
                _IS("$155"), item_pid,
                _IS("$176"), lid,
                _IS("$159"), _IS("$270"),
                _IS("$156"), _IS("$437"),
                _IS("$434"), _IS("$441"),
            )
            page_start_pid.extend(node.get("$155") for node in outer_nodes)

        b.add("$260", sid, _ion_struct(_IS("$174"), sid, _IS("$141"), [item]))

        if index in nav_target_groups:
            ad_id = b.sym("%s-ad" % sid)
            b.add("$597", ad_id, _ion_struct(
                _IS("$598"), ad_id,
                _IS("$258"), [_kv("IS_TARGET_SECTION", True)],
            ))

    _log("STRUCTURE: %d sections (%d spreads), %d nav-target sections"
         % (len(section_ids), sum(1 for g in page_groups if len(g) == 2),
            len(nav_target_groups)))

    # -- Reading order -----------------------------------------------------
    reading_order = [_ion_struct(_IS("$178"), _IS("$351"), _IS("$170"), list(section_ids))]

    d1ed = b.sym("d1ED")
    b.add("$597", d1ed, _ion_struct(
        _IS("$598"), d1ed,
        _IS("$258"), [_kv("has_large_data_table", False)],
    ))

    # "max_id" belongs here too -- all 14 reference store files and Kindle
    # Previewer write it -- but its value is the size of the finished symbol
    # table, which is not known until check_symbol_table has rebuilt it.
    # finalize_native_kfx_book fills it in.
    b.add("$538", None, _ion_struct(
        _IS("$560"), _IS(progression_symbol),
        _IS("$192"), _IS(direction_symbol),
        _IS("$477"), _IS("$56"),
        _IS("$169"), reading_order,
        _IS("$597"), _ion_struct(_IS("$614"), d1ed),
    ))

    # Format capabilities: an empty list in every reference file examined,
    # Amazon's and Kindle Previewer's alike.
    b.add("$593", None, [])

    # -- Navigation --------------------------------------------------------
    nav_ids = []

    if toc_entries:
        toc_id = b.sym(b.navs.next())
        entries = []
        for page_index, entry_title in toc_entries:
            if not (0 <= page_index < len(page_start_pid)):
                continue
            # The page's own pid, not the section's.  Where the parity of a
            # bisected spread forced a chapter opening into the far half of a
            # facing pair, the section begins on the page before the chapter,
            # and naming it sends the reader there instead.
            entries.append(_ion_annotation([_IS("$393")], _ion_struct(
                _IS("$241"), _ion_struct(_IS("$244"), str(entry_title)),
                _IS("$246"), _ion_struct(_IS("$155"), page_start_pid[page_index], _IS("$143"), 0),
            )))
        if entries:
            b.add("$391", toc_id, _ion_struct(
                _IS("$235"), _IS("$212"),
                _IS("$239"), toc_id,
                _IS("$247"), entries,
            ))
            nav_ids.append(toc_id)

    landmark_id = b.sym(b.navs.next())
    b.add("$391", landmark_id, _ion_struct(
        _IS("$235"), _IS("$236"),
        _IS("$239"), landmark_id,
        _IS("$247"), [_ion_annotation([_IS("$393")], _ion_struct(
            _IS("$238"), _IS("$233"),
            _IS("$241"), _ion_struct(_IS("$244"), "cover-nav-unit"),
            _IS("$246"), _ion_struct(_IS("$155"), page_start_pid[0], _IS("$143"), 0),
        ))],
    ))
    nav_ids.append(landmark_id)

    # A page list, which is the difference between a Kindle saying "Page 4 of
    # 160" and falling back to "Location 7 of 320".  The count it already shows
    # is right; only the label is wrong, and this is the fragment that fixes
    # it: a third nav container beside the TOC and the landmarks.
    #
    # Measured against a maic EPUB that went through Send-to-Kindle and came
    # back as KFX (2026-08-23): Amazon builds exactly this, one entry per page
    # labelled "1".."N" pointing at the page's own eid.  That book also
    # declares yj_double_page_spread, so a page list and facing pairs coexist
    # in a book Amazon itself produced; kfxlib's own
    # create_approximate_page_list refuses to generate one for a spread book,
    # and this is the evidence that its refusal is a policy of kfxlib's and not
    # a limit of the format.
    #
    # The cover is numbered with the rest, which is where this departs from
    # Amazon's conversion.  Leaving it out reads as a bug on the device: the
    # cover has no number to show, so the reader falls back to "Location 1 of
    # 160" there and switches to "Page 1 of 159" on the next screen.  One
    # sequence over every screen in the book is worth more than matching a
    # converter that nothing else here follows anyway.
    if page_list and page_start_pid:
        page_list_id = b.sym(b.navs.next())
        b.add("$391", page_list_id, _ion_struct(
            _IS("$235"), _IS("$237"),
            _IS("$239"), page_list_id,
            _IS("$247"), [
                _ion_annotation([_IS("$393")], _ion_struct(
                    _IS("$241"), _ion_struct(_IS("$244"), str(number)),
                    _IS("$246"), _ion_struct(_IS("$155"), pid, _IS("$143"), 0),
                ))
                for number, pid in enumerate(page_start_pid, start=1)
            ],
        ))
        nav_ids.append(page_list_id)

    b.add("$389", None, [_ion_struct(_IS("$178"), _IS("$351"), _IS("$392"), list(nav_ids))])
    b.add("$395", None, _ion_struct(_IS("$247"), []))

    # -- Metadata ----------------------------------------------------------
    author_text = None
    if authors:
        if isinstance(authors, (list, tuple)):
            # One author line holding every name, joined the way the KCC path
            # joins them into a single <dc:creator>.  Keeping only the first
            # would quietly drop the translator credit, which for scanlations
            # is the name readers actually look for.
            from ._comicinfo import AUTHOR_SEPARATOR

            names = [str(a).strip() for a in authors if str(a).strip()]
            author_text = AUTHOR_SEPARATOR.join(names) or None
        else:
            author_text = str(authors)

    # cde_content_type defaults to PDOC on purpose.  With EBOK a sideloaded
    # book is treated as a store title and the device looks its cover art up in
    # the content catalogue by ASIN; for a book it does not own that lookup
    # fails and the library tile stays blank, even though the cover renders
    # fine once the book is open.  Confirmed on device 2026-08-17.
    title_entries = [
        ("title", str(title)),
        ("language", str(language)),
        ("cde_content_type", str(cde_type)),
        ("is_sample", False),
        ("override_kindle_font", False),
        ("cover_image", str(page_groups[0][0]["eid"])),
    ]
    if author_text:
        title_entries.insert(1, ("author", author_text))
    # ComicInfo wins where it says anything; otherwise both fields record who
    # made this file and when.  Amazon's Send-to-Kindle conversion dates a book
    # the same way -- issue_date is the day it ran -- but leaves publisher
    # empty, which tells a reader nothing, so maic signs it instead.
    #
    # The cost of a build date is that a volume rebuilt after midnight is no
    # longer byte-identical to the one before it.  The identity fields that
    # matter to a device (ASIN, content_id, asset_id, book_id) are derived from
    # the book's own content and do not move, so the device still recognises a
    # replaced file as the same book.
    title_entries.append(("publisher", str(publisher or BUILD_STAMP)))
    title_entries.append(("issue_date", str(issue_date or _date.today().isoformat())))
    if asin:
        # The device caches a book's cover under its ASIN; that cached cover is
        # what it shows on the standby screen.  kfxlib writes the same value
        # into content_id, so this follows it.
        title_entries.append(("ASIN", str(asin)))
        title_entries.append(("content_id", str(asin)))
    if book_id:
        title_entries.append(("book_id", str(book_id)))
    if asset_id:
        # Also makes output reproducible: without it check_fragment_usage falls
        # back to a random container id.
        title_entries.append(("asset_id", str(asset_id)))

    b.add("$490", None, _ion_struct(_IS("$491"), [
        _category("kindle_title_metadata", title_entries),
        _category("kindle_capability_metadata", [
            ("yj_fixed_layout", 1),
            ("yj_double_page_spread", 1),
            ("continuous_popup_progression", 0),
        ]),
        _category("kindle_audit_metadata", [("file_creator", "maic")]),
    ]))

    b.add("$258", None, _ion_struct(_IS("$169"), reading_order))

    ns_yj = "com.amazon.yjconversion"
    features = [
        (ns_yj, "yj_non_pdf_fixed_layout", 2),
        (ns_yj, "yj_double_page_spread", 1),
        ("SDK.Marker", "CanonicalFormat", 2),
    ]
    # The cover keeps a preview in every mode, but the feature describes the
    # pages, so it goes when they stop carrying one.
    if thumb_mode != "off":
        features.insert(2, (ns_yj, "yj_thumbnails_present", 1))
    # kfxlib validates this as "any JPEG in the book carries restart markers"
    # (yj_structure.py:560,618), so declare it on the same rule.  Note this is
    # looser than _kfx_postprocess, which requires every main page JPEG to have
    # them and therefore trips kfxlib's consistency check on mixed books.
    if any(p.get("has_rst") for p in all_pages):
        features.append((ns_yj, "yj_jpg_rst_marker_present", 1))
    b.add("$585", None, _ion_struct(_IS("$590"), [
        _ion_struct(_IS("$586"), ns, _IS("$492"), name, _IS("$589"), _mk_version(ver))
        for ns, name, ver in features
    ]))

    return book


# -- Reading a KCC-produced EPUB -------------------------------------------

def _epub_opf_path(zf):
    import xml.etree.ElementTree as ET
    try:
        root = ET.fromstring(zf.read("META-INF/container.xml"))
    except Exception:
        return ""
    for node in root.iter():
        if node.tag.rsplit("}", 1)[-1] == "rootfile":
            return str(node.attrib.get("full-path", "") or "").strip()
    return ""


def page_groups_from_epub(epub_path, log_fn=None):
    """Turn a KCC-produced EPUB into page groups and a table of contents.

    KCC has already done the real page work -- cleaning, cropping, spread
    splitting, margins, device sizing -- so this only has to read the result in
    spine order.  A ``-kcc-b`` page followed by a ``-kcc-c`` page is the two
    halves of one split spread and becomes a facing pair.

    Image dimensions are taken as they are.  Whether they carry padded margins
    is KCC's decision, not this function's: the leaf style is sized per image
    either way, which is what keeps the page from being stretched.
    """
    import posixpath
    import xml.etree.ElementTree as ET
    import zipfile

    _log = log_fn or (lambda msg: None)

    def local(tag):
        return tag.rsplit("}", 1)[-1]

    with zipfile.ZipFile(epub_path, "r") as zf:
        opf_rel = _epub_opf_path(zf)
        if not opf_rel:
            raise ValueError("EPUB has no OPF: %s" % epub_path)
        opf_dir = posixpath.dirname(opf_rel.replace("\\", "/"))
        root = ET.fromstring(zf.read(opf_rel))

        manifest = {}
        spine = None
        for elem in root.iter():
            name = local(elem.tag)
            if name == "item":
                item_id = str(elem.attrib.get("id", "") or "").strip()
                href = str(elem.attrib.get("href", "") or "").strip()
                if item_id and href:
                    manifest[item_id] = href
            elif name == "spine" and spine is None:
                spine = elem
        if spine is None:
            raise ValueError("EPUB has no spine: %s" % epub_path)

        def resolve(path, base=""):
            p = path.replace("\\", "/")
            p = posixpath.join(base or opf_dir, p) if (base or opf_dir) else p
            return posixpath.normpath(p).lstrip("/")

        def image_of(href):
            """The single image a KCC page document points at."""
            xhtml = resolve(href)
            try:
                page_root = ET.fromstring(zf.read(xhtml))
            except Exception:
                return None
            src = ""
            for node in page_root.iter():
                if local(node.tag) == "img":
                    src = str(node.attrib.get("src", "") or "").strip()
                    if src:
                        break
            if not src:
                return None
            img_path = resolve(src, posixpath.dirname(xhtml))
            try:
                data = zf.read(img_path)
            except KeyError:
                return None
            width, height = _decode_image_size(data)
            return {
                "data": data, "width": width, "height": height,
                "href": href, "image_path": img_path,
            }

        # KCC declares the cover through the manifest only ("Root cover kept for
        # metadata only"), so it never appears in the spine.  KFX needs it as a
        # real first section, or the book opens on page one and the library tile
        # has nothing to show.
        cover_href = ""
        for elem in root.iter():
            if local(elem.tag) == "item" and "cover-image" in str(elem.attrib.get("properties", "")):
                cover_href = str(elem.attrib.get("href", "") or "").strip()
                break
        if not cover_href:
            for elem in root.iter():
                if local(elem.tag) == "meta" and str(elem.attrib.get("name", "")) == "cover":
                    cover_href = manifest.get(str(elem.attrib.get("content", "") or "").strip(), "")
                    break

        hrefs = []
        for elem in list(spine):
            if local(elem.tag) != "itemref":
                continue
            href = manifest.get(str(elem.attrib.get("idref", "") or "").strip(), "")
            if href:
                hrefs.append(href.replace("\\", "/"))

        page_groups = []
        # Which page of the finished book each spine document becomes.
        # KCC gives the two halves of a cut spread a document each, so a
        # navPoint aimed at the second half names the second page.
        href_to_page = {}
        book_pages = 0
        index = 0
        spreads = 0

        if cover_href:
            cover_path = resolve(cover_href)
            first = image_of(hrefs[0]) if hrefs else None
            already_first = bool(first and first.get("image_path") == cover_path)
            if not already_first:
                try:
                    data = zf.read(cover_path)
                except KeyError:
                    data = b""
                if data:
                    width, height = _decode_image_size(data)
                    page_groups.append([{
                        "data": data, "width": width, "height": height,
                        "href": cover_href, "image_path": cover_path,
                    }])
                    _log("EPUB: cover taken from the manifest (%dx%d)" % (width, height))
        while index < len(hrefs):
            href = hrefs[index]
            nxt = hrefs[index + 1] if index + 1 < len(hrefs) else ""
            page = image_of(href)
            if page is None:
                index += 1
                continue
            if href.lower().endswith("-kcc-b.xhtml") and nxt.lower().endswith("-kcc-c.xhtml"):
                other = image_of(nxt)
                if other is not None:
                    href_to_page[href] = book_pages
                    href_to_page[nxt] = book_pages + 1
                    page_groups.append([page, other])
                    book_pages += 2
                    spreads += 1
                    index += 2
                    continue
            href_to_page[href] = book_pages
            page_groups.append([page])
            book_pages += 1
            index += 1

        toc_entries = []
        ncx_rel = ""
        for item_id, href in manifest.items():
            if href.lower().endswith(".ncx"):
                ncx_rel = resolve(href)
                break
        if ncx_rel:
            try:
                ncx = ET.fromstring(zf.read(ncx_rel))
                ncx_dir = posixpath.dirname(ncx_rel)
                for point in ncx.iter():
                    if local(point.tag) != "navPoint":
                        continue
                    label = ""
                    target = ""
                    for node in point.iter():
                        if local(node.tag) == "text" and not label:
                            label = (node.text or "").strip()
                        elif local(node.tag) == "content" and not target:
                            target = str(node.attrib.get("src", "") or "").split("#")[0]
                    if not (label and target):
                        continue
                    resolved = resolve(target, ncx_dir)
                    for href, page_index in href_to_page.items():
                        if resolve(href) == resolved:
                            toc_entries.append((page_index, label))
                            break
            except Exception as exc:
                _log("TOC: could not read %s (%s)" % (ncx_rel, exc))

    _log("EPUB: %d sections (%d spreads), %d TOC entries"
         % (len(page_groups), spreads, len(toc_entries)))
    return page_groups, toc_entries


def epub_metadata(epub_path):
    """Title, authors, language, publisher and date from an EPUB's OPF."""
    import xml.etree.ElementTree as ET
    import zipfile

    title = ""
    authors = []
    language = ""
    publisher = ""
    issue_date = ""
    try:
        with zipfile.ZipFile(epub_path, "r") as zf:
            opf_rel = _epub_opf_path(zf)
            if not opf_rel:
                return "", [], "", "", ""
            for node in ET.fromstring(zf.read(opf_rel)).iter():
                name = node.tag.rsplit("}", 1)[-1]
                text = (node.text or "").strip()
                if not text:
                    continue
                if name == "title" and not title:
                    title = text
                elif name == "creator":
                    authors.append(text)
                elif name == "language" and not language:
                    language = text
                elif name == "publisher" and not publisher:
                    publisher = text
                elif name == "date" and not issue_date:
                    # OPF dates are ISO but may carry a time; the metadata
                    # field is a date, and every store book writes only one.
                    issue_date = text[:10]
    except Exception:
        pass
    return title, authors, language, publisher, issue_date


def _resize_page_to_height(page, target_height, *, quality=85, fmt=None,
                           mozjpeg=False, log_fn=None):
    """Resize one encoded page to *target_height*, preserving its aspect."""
    target_height = max(1, int(target_height))
    if int(page.get("height") or 0) == target_height:
        return page

    from PIL import Image

    from ._image_pipeline import _resize_method, encode_page

    with Image.open(io.BytesIO(page["data"])) as image:
        image.load()
        width = max(1, int(round(image.width * target_height / float(image.height))))
        size = (width, target_height)
        resized = image.resize(size, _resize_method(image, size))
        page["data"] = encode_page(
            resized,
            fmt=str(fmt or _image_format(page["data"])),
            quality=quality,
            mozjpeg=mozjpeg,
            log_fn=log_fn,
        )
    page["width"], page["height"] = size
    return page


def _content_canvas(page_groups):
    """Shared box for standalone pages, excluding cover and facing spreads.

    Facing pairs have per-image viewports and never use this box. A wide
    spread half must not enlarge it: fitting a 1400x1920 standalone page
    inside a 1453x1920 box shrinks its height and adds horizontal bars.
    Books with only facing pairs (or only a cover) still need a fallback.
    """
    groups = page_groups[1:] or page_groups
    groups = [group for group in groups if len(group) == 1] or groups
    return (
        max(int(page["width"]) for group in groups for page in group),
        max(int(page["height"]) for group in groups for page in group),
    )


def build_kfx_from_epub(
    epub_path,
    out_path,
    *,
    title=None,
    authors=None,
    language="en",
    cde_type="PDOC",
    asin=None,
    asset_id=None,
    background_color=None,
    reading_direction=None,
    thumbnails=True,
    log_fn=None,
):
    """KCC-produced EPUB -> KFX, with no Kindle Previewer in the path."""
    _init_kfxlib_types()
    _log = log_fn or (lambda msg: None)

    page_groups, toc_entries = page_groups_from_epub(epub_path, log_fn=_log)
    if not page_groups:
        raise ValueError("no page images found in %s" % epub_path)

    # KCC keeps the manifest cover outside its resized page sequence. Bring it
    # to the native render height before it can enlarge the shared viewport.
    from ._image_pipeline import KFX_PAGE_HEIGHT

    cover = page_groups[0][0]
    before = (int(cover["width"]), int(cover["height"]))
    _resize_page_to_height(cover, KFX_PAGE_HEIGHT, log_fn=_log)
    if before != (cover["width"], cover["height"]):
        _log("EPUB: cover resized %dx%d -> %dx%d" % (
            before[0], before[1], cover["width"], cover["height"]))

    opf_title, opf_authors, opf_language, opf_publisher, opf_date = epub_metadata(epub_path)
    title = title or opf_title
    authors = authors or opf_authors
    language = language or opf_language or "en"

    # Per-image leaf styles: box aspect always equals image aspect, which is
    # the invariant that stops the renderer stretching a page.  Holds whether
    # or not KCC padded the images.
    canvas = _content_canvas(page_groups)

    book = build_native_kfx_book(
        page_groups,
        title=title or os.path.splitext(os.path.basename(epub_path))[0],
        authors=authors,
        language=language,
        publisher=opf_publisher,
        issue_date=opf_date,
        cde_type=cde_type,
        asin=asin,
        asset_id=asset_id,
        thumbnails=thumbnails,
        toc_entries=toc_entries,
        image_fit="contain",
        reading_direction=reading_direction,
        canvas=canvas,
        background_color=background_color,
        log_fn=_log,
    )
    finalize_native_kfx_book(book, log_fn=_log)
    return write_native_kfx(book, out_path, log_fn=_log)


def build_kfx_from_dir(
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
    asin=None,
    asset_id=None,
    book_id=None,
    thumbnails=True,
    # Every preview keeps its page's own shape here.  The strip frames each
    # one, so padding a preview only puts white inside that frame; the pages
    # themselves are padded to the canvas and that is a separate decision.
    thumbnail_pad="none",
    background_color=None,
    reading_direction=None,
    device_canvas="KPW12",
    hq=False,
    resize=False,
    no_padding=False,
    split_spreads=True,
    rotate_spreads=True,
    force_spread_preview=False,
    spread_preview_mode=None,
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
    page_list=True,
    image_fit="contain",
    progress_fn=None,
    stop_requested_fn=None,
    log_fn=None,
):
    """Source folder -> KFX, with neither KCC nor Kindle Previewer in the path.

    Metadata comes from ComicInfo.xml and the page selection from the source's
    sidecar, the same two files the KCC path reads, unless the caller passes
    *excluded* / *bookmarks* explicitly -- the conversion routes already hold
    them, and re-reading the sidecar there would race the UI.

    *device_canvas* is the target screen, either a ``(width, height)`` pair or
    a device profile name the UI's picker uses, e.g. ``"KPW12"``.  Facing
    spreads are cut against it; pages are only resized to it when *resize* is
    set, and then every page comes out at the screen's height.
    """
    _init_kfxlib_types()
    _log = log_fn or (lambda msg: None)

    from ._image_pipeline import device_canvas as _resolve_canvas

    device_canvas = _resolve_canvas(device_canvas, hq=hq)
    _log("DEVICE: canvas %dx%d" % device_canvas)

    if mozjpeg:
        # The same call the KCC path makes for KFX (kcc_patch.py).  mozjpeg
        # re-packs a page progressive and drops its restart markers; measured
        # on a real volume that buys 3.9% and costs both.  Every one of the
        # 2018 JPEGs across the 14 reference store books is baseline, and every
        # page image in them carries restart markers -- which is also what
        # yj_jpg_rst_marker_present below ends up declaring.  Nothing about the
        # finished file shows the option was ignored, so say it here.
        _log("JPEG: KFX disables mozjpeg to preserve restart markers")
        mozjpeg = False

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
        # The KFX cover is a dedicated first section. Keeping it at arbitrary
        # source dimensions makes it enlarge the viewport for every page.
        resize_cover=True,
        progress_fn=progress_fn,
        stop_requested_fn=stop_requested_fn,
        log_fn=_log,
    )

    title = title or meta["title"] or os.path.basename(str(source_dir).rstrip("/\\"))
    authors = authors or meta["authors"]
    language = language or meta["language"] or "en"

    identity = content_identity(title, page_groups)
    # Same book, same bytes, and an identity the device can cache a cover
    # against.  Anything the caller supplied wins.
    asin = asin or identity["asin"]
    asset_id = asset_id or identity["asset_id"]
    book_id = book_id or identity["book_id"]
    _log("IDENTITY: asin=%s asset=%s cde=%s" % (asin, asset_id, cde_type))
    if str(cde_type).strip().upper() == "EBOK":
        # Nothing about the file itself shows this went wrong, and the device
        # only reveals it hours later in the library, so say it while building.
        _log("WARN: EBOK looks its cover art up in the store catalogue by ASIN; "
             "a sideloaded book gets a blank cover in the library and on standby")

    # The leaf style box has to share each image's aspect ratio or the page is
    # stretched, so styles are sized per image; the canvas is only the viewport
    # the pages sit in.
    canvas = _content_canvas(page_groups)

    book = build_native_kfx_book(
        page_groups,
        title=title,
        authors=authors,
        language=language,
        publisher=meta["publisher"],
        issue_date=meta["issue_date"],
        cde_type=cde_type,
        asin=asin,
        asset_id=asset_id,
        book_id=book_id,
        thumbnails=thumbnails,
        thumbnail_pad=thumbnail_pad,
        toc_entries=toc_entries,
        image_fit=image_fit,
        reading_direction=reading_direction,
        canvas=canvas,
        background_color=background_color,
        page_list=page_list,
        log_fn=_log,
    )
    finalize_native_kfx_book(book, log_fn=_log)
    return write_native_kfx(book, out_path, log_fn=_log)


_ID_ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
_BOOK_ID_ALPHABET = (
    "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz")


def content_identity(title, page_groups):
    """Stable ids for this exact book, derived from what is in it.

    A sideloaded book needs an identity, and not only for tidiness.  The device
    caches a book's cover under its ASIN, which is what puts that cover on the
    standby screen; a book with no ASIN never gets one cached.  kfxlib also
    derives the container id from the asset id, so without one every rebuild
    comes out byte-different and the reader treats a replaced file as the same
    book it already indexed.

    The shapes follow a maic book built through Kindle Previewer that does show
    its cover in standby: ASIN and content_id are the same 32 characters over
    [0-9A-Z] that kfxlib's own generator produces, the asset id is a container
    id, and the book id is 22 mixed-case characters.
    """
    import hashlib

    digest = hashlib.sha256()
    digest.update(str(title).encode("utf-8", "replace"))
    for group in page_groups:
        for page in group:
            digest.update(b"%d,%d,%d;" % (page["width"], page["height"], len(page["data"])))

    def token(salt, length, alphabet):
        raw = hashlib.sha256(digest.digest() + salt).digest()
        value = int.from_bytes(raw, "big")
        out = []
        for _ in range(length):
            value, index = divmod(value, len(alphabet))
            out.append(alphabet[index])
        return "".join(out)

    asin = token(b"asin", 32, _ID_ALPHABET)
    return {
        "asin": asin,
        "asset_id": "CR!" + token(b"asset", 30, _ID_ALPHABET),
        "book_id": token(b"book", 22, _BOOK_ID_ALPHABET),
    }


def content_asset_id(title, page_groups):
    """Back-compatible accessor for the asset id alone."""
    return content_identity(title, page_groups)["asset_id"]


def page_locations_from_position_info(pos_info):
    """Return one KFX location target for every rendered page image.

    kfxlib's approximate location generator uses one location per 110
    positions, resetting at every section.  A native comic section is much
    shorter than that, so the result is effectively one location per section.
    That is wrong as soon as a facing section contains two pages: a 160-page
    book arranged into 82 sections is reported by Kindle as 82 locations.

    ``collect_content_position_info`` marks the actual ``$271`` image nodes
    with ``image_resource``.  Those nodes are the KFX equivalent of the page
    splice points used by MOBI's DATP, and remain distinct inside a facing
    section, so selecting them gives the required one image = one page = one
    location mapping.
    """
    return [chunk for chunk in pos_info
            if getattr(chunk, "image_resource", None) is not None]


def finalize_native_kfx_book(book, log_fn=None):
    """Build position/location maps and the container bookkeeping fragments."""
    _log = log_fn or (lambda msg: None)

    pos_info = book.collect_content_position_info()
    book.create_position_map(pos_info)
    loc_info = page_locations_from_position_info(pos_info)
    if not loc_info:
        # Defensive fallback for an unexpected non-image book passed to this
        # native-comic finalizer.  The normal path always has at least a cover.
        loc_info = book.generate_approximate_locations(pos_info)
    book.create_location_map(loc_info)
    _log("MAPS: %d position entries, %d page locations"
         % (len(pos_info), len(loc_info)))

    book.check_fragment_usage(rebuild=True, ignore_extra=True)
    book.check_symbol_table(rebuild=True, ignore_unused=True)

    # $538's "max_id" is the size of the Ion symbol table the book is written
    # against -- system symbols, the imported YJ_symbols table, and the book's
    # own local symbols -- which is only settled now that check_symbol_table
    # has rebuilt it.  The key itself is a system symbol, so writing it adds
    # nothing to the table it describes.
    frag538 = book.fragments.get("$538", first=True)
    if frag538 is not None:
        frag538.value[_IS("max_id")] = len(book.symtab.symbols)

    return book


def write_native_kfx(book, out_path, log_fn=None):
    _log = log_fn or (lambda msg: None)
    data = book.convert_to_single_kfx()
    if not data:
        raise RuntimeError("convert_to_single_kfx produced no data")
    with open(out_path, "wb") as f:
        f.write(data)
    _log("KFX_OUT: %s (%d KB)" % (os.path.basename(out_path), len(data) // 1024))
    return out_path
