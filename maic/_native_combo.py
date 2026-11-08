"""Build native KFX and MOBI from one prepared set of comic pages."""

from __future__ import annotations

import os


def build_kfx_mobi_from_dir(
    source_dir,
    out_kfx_path,
    out_mobi_path,
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
    progress_fn=None,
    stage_fn=None,
    stop_requested_fn=None,
    log_fn=None,
):
    """Prepare pages once, then write KFX first and MOBI second.

    Converting either finished container into the other would require unpacking
    format-specific navigation, spread and metadata structures.  The lossless
    common representation is the page-group list immediately before container
    serialization, so both writers consume that same in-memory list instead.
    """
    _log = log_fn or (lambda message: None)
    _stage = stage_fn or (lambda message, percent: None)

    from ._comicinfo import read_comicinfo
    from ._image_pipeline import device_canvas as resolve_device_canvas
    from ._kfx_native import (
        _content_canvas,
        _init_kfxlib_types,
        build_native_kfx_book,
        content_identity,
        finalize_native_kfx_book,
        write_native_kfx,
    )
    from ._mobi_native import _set_page_backgrounds, build_native_mobi_book
    from ._page_groups import page_groups_from_dir

    _init_kfxlib_types()
    resolved_canvas = resolve_device_canvas(device_canvas, hq=hq)
    _log("DEVICE: canvas %dx%d" % resolved_canvas)

    # KFX pages must retain JPEG restart markers.  A shared page set therefore
    # follows the stricter KFX rule; MOBI can embed those same bytes directly.
    if mozjpeg:
        _log("JPEG: shared KFX output disables mozjpeg to preserve restart markers")
        mozjpeg = False

    meta = read_comicinfo(source_dir, vol_prefix=vol_prefix)
    if (excluded is None or bookmarks is None or nocrop is None
            or watermark_matches is None or custom_crops is None
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
    _stage("Preparing shared pages", 0)
    page_groups, toc_entries = page_groups_from_dir(
        source_dir,
        excluded=excluded,
        bookmarks=bookmarks,
        comicinfo_bookmarks=meta["bookmarks"],
        canvas=resolved_canvas,
        resize=resize,
        no_padding=no_padding,
        upscale=upscale,
        stretch=stretch,
        grayscale=grayscale,
        page_format=page_format,
        mozjpeg=mozjpeg,
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
        # KFX needs these previews; MOBI simply ignores the extra bytes.
        build_previews=True,
        resize_cover=True,
        progress_fn=progress_fn,
        stop_requested_fn=stop_requested_fn,
        log_fn=_log,
    )

    title = title or meta["title"] or os.path.basename(str(source_dir).rstrip("/\\"))
    authors = authors or meta["authors"]
    language = language or meta["language"] or "en"
    identity = content_identity(title, page_groups)
    _log(
        "IDENTITY: asin=%s asset=%s cde=%s"
        % (identity["asin"], identity["asset_id"], cde_type)
    )
    if str(cde_type).strip().upper() == "EBOK":
        _log(
            "WARN: EBOK looks its cover art up in the store catalogue by ASIN; "
            "a sideloaded book gets a blank cover in the library and on standby"
        )

    if stop_requested_fn and stop_requested_fn():
        raise UserWarning("Conversion interrupted.")
    _stage("Building KFX container", 90)
    _log("STAGE 1/2: KFX container")
    kfx_book = build_native_kfx_book(
        page_groups,
        title=title,
        authors=authors,
        language=language,
        publisher=meta["publisher"],
        issue_date=meta["issue_date"],
        cde_type=cde_type,
        asin=identity["asin"],
        asset_id=identity["asset_id"],
        book_id=identity["book_id"],
        thumbnails="full",
        toc_entries=toc_entries,
        image_fit="contain",
        reading_direction=reading_direction,
        canvas=_content_canvas(page_groups),
        page_list=True,
        log_fn=_log,
    )
    finalize_native_kfx_book(kfx_book, log_fn=_log)
    write_native_kfx(kfx_book, out_kfx_path, log_fn=_log)

    if stop_requested_fn and stop_requested_fn():
        raise UserWarning("Conversion interrupted.")
    _stage("Building MOBI container", 96)
    _log("STAGE 2/2: MOBI container from the same prepared pages")
    _set_page_backgrounds(page_groups, borders_color, log_fn=_log)
    mobi_data = build_native_mobi_book(
        page_groups,
        toc_entries,
        title=title,
        authors=authors,
        language=language,
        cde_type=cde_type,
        canvas=resolved_canvas,
        reading_direction=reading_direction,
        joint=True,
        alternate_spreads=facing_pages,
        log_fn=_log,
    )
    with open(out_mobi_path, "wb") as handle:
        handle.write(mobi_data)
    _log("MOBI_OUT: %s (%d KB)" % (os.path.basename(out_mobi_path), len(mobi_data) // 1024))
    _stage("KFX and MOBI complete", 99)
    return out_kfx_path, out_mobi_path
