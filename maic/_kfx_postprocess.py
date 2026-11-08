"""KFX post-processing helper.

Injects comic reading-mode metadata (EBOK, cover, authors, features, etc.).
Facing-pages layout restructuring can merge explicit split-page pairs (and,
optionally, adjacent portrait single-page sections) into two-page facing
spreads, using the existing $155 position IDs from the original layout pages
so that $264/$265 position maps stay valid.

Standalone usage::

    python _kfx_postprocess.py <path-to-kfx>

Optional env:

    MAIC_KFX_CDE_TYPE=EBOK|PDOC
"""

import io
import os
import sys
import types

_EPUB_AUTHOR_SEPARATOR = "‚ "

# Amazon splits resource containers at ~3 MB.
# Single KFX files >16 MB crash on Kindle e-ink devices.
_KFX_ATTACHABLE_CHUNK_SIZE = 3 * 1024 * 1024  # 3 MB per .azw.res


def _env_bool(name, default=False):
    val = os.environ.get(name)
    if val is None:
        return default
    return str(val).strip().lower() not in {"0", "false", "no", "off", ""}


class _SimpleLog:
    def info(self, msg):
        print(msg)

    def warning(self, msg):
        print(msg)

    def error(self, msg):
        print(msg)


def _is_translator_like(value):
    text = str(value or "").strip().casefold()
    return (
        text.startswith("translator")
        or text.startswith("translation")
        or text.startswith("перевод")
    )


def _merge_authors_single(authors):
    """Normalize KFX authors to a single display string (MOBI-compatible style)."""
    if not authors:
        return None
    parts = []
    for raw in list(authors):
        text = str(raw or "").replace("‚", ",").replace(";", ",")
        for part in text.split(","):
            part = part.strip()
            if part:
                parts.append(part)
    if not parts:
        return None
    merged = _EPUB_AUTHOR_SEPARATOR.join(parts).strip()
    if not merged:
        return None
    return [merged]


# -- Helper functions (no kfxlib imports needed) --

def _find_or_add_category(categories, cat_name):
    for cm in categories:
        if cm.get("$495", "") == cat_name:
            return cm
    new_cm = _ion_struct(_IS("$495"), cat_name, _IS("$258"), [])
    categories.append(new_cm)
    return new_cm


def _ensure_kv(cat, entries):
    kvs = cat.get("$258", [])
    existing = set(kv.get("$492", "") for kv in kvs)
    for k, v in entries:
        if k not in existing:
            kvs.append(_ion_struct(_IS("$492"), k, _IS("$307"), v))
    cat[_IS("$258")] = kvs


def _drop_kv(cat, keys):
    keys = set(keys)
    kvs = cat.get("$258", [])
    cat[_IS("$258")] = [kv for kv in kvs if kv.get("$492", "") not in keys]


def _build_style_index(book_obj):
    out = {}
    for frag in book_obj.fragments:
        if str(getattr(frag, "ftype", "")) != "$157":
            continue
        out[str(getattr(frag, "fid", ""))] = frag
    return out


def _detect_rtl_reading(book_obj):
    for frag_id in ("$538", "$258"):
        frag = book_obj.fragments.get(frag_id)
        if frag is None or not hasattr(frag, "value"):
            continue
        try:
            direction = str(frag.value.get("$192", ""))
        except Exception:
            direction = ""
        if direction == "$375":
            return True
        if direction == "$376":
            return False
    return False


def _pop_key(obj, key):
    if not hasattr(obj, "pop"):
        return
    try:
        obj.pop(_IS(key), None)
    except Exception:
        pass
    try:
        obj.pop(key, None)
    except Exception:
        pass


def _to_int_or_none(value):
    try:
        if value is None:
            return None
        return int(value)
    except Exception:
        return None


def _flatten_reading_order_entries(order_entries):
    flat = []
    if not isinstance(order_entries, list):
        return flat
    for entry in order_entries:
        if not hasattr(entry, "get"):
            continue
        sids = entry.get("$170", [])
        if not isinstance(sids, list):
            continue
        for sid in sids:
            flat.append(str(sid))
    return flat


class _PidAllocator:
    """Allocate unique integer position IDs ($155) for wrapper pages."""
    def __init__(self, book_obj):
        self._next = 0
        for frag in book_obj.fragments:
            self._scan(frag.value)

    def _scan(self, data):
        if hasattr(data, 'items'):
            for k, v in data.items():
                if str(k) == "$155" and isinstance(v, int):
                    if v >= self._next:
                        self._next = v + 1
                else:
                    self._scan(v)
        elif isinstance(data, list):
            for item in data:
                self._scan(item)

    def alloc(self):
        pid = self._next
        self._next += 1
        return pid


# -- Lazy kfxlib type accessors (set by _init_kfxlib_types or postprocess caller) --
_IS = None
_ion_blob = None
_ion_struct = None
_ion_unannotated = None
_yj_fragment = None


def _init_kfxlib_types():
    """Resolve kfxlib Ion types from whatever import path is active."""
    global _IS, _ion_blob, _ion_struct, _ion_unannotated, _yj_fragment
    if _IS is not None:
        return
    try:
        from calibre_plugins.kfx_output.kfxlib.ion import IS, IonBLOB, IonStruct, unannotated
        from calibre_plugins.kfx_output.kfxlib.yj_container import YJFragment
    except Exception:
        from kfxlib.ion import IS, IonBLOB, IonStruct, unannotated  # type: ignore[import-not-found]
        from kfxlib.yj_container import YJFragment  # type: ignore[import-not-found]
    _IS = IS
    _ion_blob = IonBLOB
    _ion_struct = IonStruct
    _ion_unannotated = unannotated
    _yj_fragment = YJFragment


def _build_book_indexes(book_obj):
    sections_by_id = {}
    layouts_by_id = {}
    entities_by_id = {}
    entities_w_h = {}
    resources_by_id = {}

    for frag in book_obj.fragments:
        ft = str(getattr(frag, "ftype", ""))
        fid = str(getattr(frag, "fid", ""))
        if ft == "$260":
            sections_by_id[fid] = frag
        elif ft == "$259":
            layouts_by_id[fid] = frag
        elif ft == "$164":
            entities_by_id[fid] = frag
            v = getattr(frag, "value", None)
            if hasattr(v, "get"):
                w = v.get("$422")
                h = v.get("$423")
                if w is not None and h is not None:
                    try:
                        entities_w_h[fid] = (int(w), int(h))
                    except (TypeError, ValueError):
                        pass
        elif ft == "$417":
            resources_by_id[fid] = frag

    return sections_by_id, layouts_by_id, entities_by_id, entities_w_h, resources_by_id


def _walk_first_pid(node):
    if not hasattr(node, "get"):
        return None
    pid = node.get("$155")
    if pid is not None:
        return pid
    for child in (node.get("$146") or []):
        child_pid = _walk_first_pid(child)
        if child_pid is not None:
            return child_pid
    return None


def _walk_first_entity(node):
    if not hasattr(node, "get"):
        return None, None
    eid = node.get("$175")
    if eid is not None:
        return eid, node.get("$155")
    for child in (node.get("$146") or []):
        child_eid, child_pid = _walk_first_entity(child)
        if child_eid is not None:
            return child_eid, child_pid
    return None, None


def _collect_section_page_entities(section_order, sections_by_id, layouts_by_id):
    ordered = []
    seen = set()

    for sid in section_order:
        sec = sections_by_id.get(str(sid))
        if sec is None:
            continue
        items = sec.value.get("$141", [])
        if not items:
            continue
        lid = str(items[0].get("$176", "") or "")
        layout = layouts_by_id.get(lid)
        if layout is None:
            continue
        pages = layout.value.get("$146", [])
        if not isinstance(pages, list):
            continue
        for pg in pages:
            eid_raw, _ = _walk_first_entity(pg)
            eid = str(eid_raw or "")
            if eid and eid not in seen:
                seen.add(eid)
                ordered.append(eid)

    return ordered


def _jpeg_has_restart_markers(blob):
    try:
        data = bytes(blob)
    except Exception:
        return False

    i = 0
    limit = max(0, len(data) - 1)
    while i < limit:
        if data[i] == 0xFF and 0xD0 <= data[i + 1] <= 0xD7:
            return True
        i += 1
    return False


def _blob_looks_like_jpeg(blob):
    try:
        data = bytes(blob)
    except Exception:
        return False
    return len(data) >= 2 and data[0] == 0xFF and data[1] == 0xD8


def _build_paired_page_resource_order(page_entity_ids, entities_by_id, resources_by_id):
    ordered_ids = []
    seen = set()
    pair_count = 0

    for eid in page_entity_ids:
        entity_frag = entities_by_id.get(str(eid))
        if entity_frag is None or not hasattr(entity_frag, "value"):
            continue
        entity_val = entity_frag.value
        main_resource_id = str(entity_val.get("$165", "") or "")
        thumb_id = str(entity_val.get("$214", "") or "")
        thumb_resource_id = ""
        if thumb_id:
            thumb_frag = entities_by_id.get(thumb_id)
            if thumb_frag is not None and hasattr(thumb_frag, "value"):
                thumb_resource_id = str(thumb_frag.value.get("$165", "") or "")

        for rid in (main_resource_id, thumb_resource_id):
            if not rid or rid in seen or rid not in resources_by_id:
                continue
            seen.add(rid)
            ordered_ids.append(rid)

        if (main_resource_id in seen) and thumb_resource_id and (thumb_resource_id in seen):
            pair_count += 1

    return ordered_ids, pair_count


def _reorder_resource_fragments(book_obj, desired_resource_ids):
    frags = list(book_obj.fragments)
    resource_frags = [frag for frag in frags if str(frag.ftype) == "$417"]
    if len(resource_frags) < 2:
        return 0

    resources_by_id = {str(frag.fid): frag for frag in resource_frags}
    ordered_resources = []
    seen = set()

    for rid in desired_resource_ids:
        frag = resources_by_id.get(str(rid))
        if frag is None:
            continue
        if rid in seen:
            continue
        seen.add(rid)
        ordered_resources.append(frag)

    for frag in resource_frags:
        rid = str(frag.fid)
        if rid in seen:
            continue
        seen.add(rid)
        ordered_resources.append(frag)

    old_order = [str(frag.fid) for frag in resource_frags]
    new_order = [str(frag.fid) for frag in ordered_resources]
    if new_order == old_order:
        return 0

    rebuilt = []
    inserted = False
    for frag in frags:
        if str(frag.ftype) == "$417":
            if not inserted:
                rebuilt.extend(ordered_resources)
                inserted = True
            continue
        rebuilt.append(frag)

    if inserted:
        book_obj.fragments.clear()
        for frag in rebuilt:
            book_obj.fragments.append(frag)
        return len(resource_frags)

    return 0


def _thumb_resource_is_paired(main_resource_id, thumb_resource_id):
    main_resource_id = str(main_resource_id or "")
    thumb_resource_id = str(thumb_resource_id or "")
    return bool(main_resource_id and thumb_resource_id and thumb_resource_id.startswith(main_resource_id) and thumb_resource_id != main_resource_id)


def _allocate_paired_resource_symbol(book_obj, existing_ids, main_resource_id):
    base = str(main_resource_id or "").strip()
    if not base:
        return _allocate_resource_symbol(book_obj, existing_ids)

    candidate = "%s-thumb" % base
    idx = 2
    while candidate in existing_ids:
        candidate = "%s-thumb-resized-1-%d" % (base, idx)
        idx += 1
    existing_ids.add(candidate)
    return book_obj.create_local_symbol(candidate)


def _allocate_resource_symbol(book_obj, existing_ids):
    idx = 1
    while True:
        candidate = "resource/rsrcT%d" % idx
        if candidate not in existing_ids:
            existing_ids.add(candidate)
            return book_obj.create_local_symbol(candidate)
        idx += 1


def _allocate_local_symbol(book_obj, existing_ids, base_name):
    base = str(base_name or "").strip() or "n"
    candidate = base
    idx = 2
    while candidate in existing_ids:
        candidate = "%s%d" % (base, idx)
        idx += 1
    existing_ids.add(candidate)
    return book_obj.create_local_symbol(candidate)


def _allocate_thumb_symbol(book_obj, existing_ids, base_name):
    base = "%s-thumb" % str(base_name or "").strip()
    if not base:
        base = "thumb"
    candidate = base
    idx = 2
    while candidate in existing_ids:
        candidate = "%s%d" % (base, idx)
        idx += 1
    existing_ids.add(candidate)
    return book_obj.create_local_symbol(candidate)


# -- Main postprocess function --

def postprocess_kfx_book(
    book,
    *,
    cde_type="EBOK",
    reading_direction=None,
    enable_facing=True,
    merge_adjacent_pairs=False,
    explicit_split_pairs=None,
    epub_first_spine_is_cover=None,
    log_fn=None,
):
    """Post-process a decoded KFX book object in-place.

    Parameters
    ----------
    book : YJ_Book
        Already decoded book (``book.decode_book()`` must have been called).
    cde_type : str
        Content type: ``"EBOK"`` or ``"PDOC"``.
    reading_direction : str or None
        Explicit ``"ltr"``/``"rtl"`` override from the native worker.  When
        omitted, preserve the direction decoded from the source book.
    enable_facing : bool
        Whether to merge single-page sections into facing-page pairs.
    merge_adjacent_pairs : bool
        Whether to auto-merge adjacent candidate pages in addition to
        explicit split pairs.
    log_fn : callable or None
        Logging function ``log_fn(message_string)``.  Falls back to ``print``.
    """
    _init_kfxlib_types()
    _log = log_fn or print
    direction_override = str(reading_direction or "").strip().lower()
    rtl_reading = (
        direction_override == "rtl"
        if direction_override in {"ltr", "rtl"}
        else _detect_rtl_reading(book)
    )
    direction_symbol = "$375" if rtl_reading else "$376"

    # Track whether we need a final fragment/symbol rebuild.
    needs_rebuild = False

    # -- Fix authors (calibre sorts them) --
    # NOTE: Do NOT set cover_image_data -- KC reference doesn't store it,
    # and set_yj_metadata_to_book pollutes the cover layout with a thumbnail entity.
    try:
        from kfxlib import YJ_Metadata  # type: ignore[import-not-found]
    except Exception:
        from calibre_plugins.kfx_output.kfxlib import YJ_Metadata

    existing = book.get_yj_metadata_from_book()
    fix_md = YJ_Metadata(author_sort_fn=lambda a: a)
    merged_authors = _merge_authors_single(existing.authors)
    fix_md.authors = merged_authors
    if merged_authors:
        _log("AUTHORS: merged to single creator: %s" % merged_authors[0])
    book.set_yj_metadata_to_book(fix_md)

    # -- Inject capability metadata into $490 --
    frag490 = book.fragments.get("$490")
    if frag490 is not None:
        categories = frag490.value.get("$491")
        if categories is not None:
            cap = _find_or_add_category(categories, "kindle_capability_metadata")
            _drop_kv(cap, ["yj_facing_page", "yj_publisher_panels", "yj_textbook"])
            _ensure_kv(cap, [
                ("yj_fixed_layout", 1),
                ("yj_double_page_spread", 1),
                ("continuous_popup_progression", 0),
            ])
            # Remove kindle_ebook_metadata — Amazon reference doesn't have it
            categories[:] = [c for c in categories if c.get("$495") != "kindle_ebook_metadata"]

            # Set file_creator to maic in kindle_audit_metadata
            audit = _find_or_add_category(categories, "kindle_audit_metadata")
            _drop_kv(audit, ["file_creator", "creator_version"])
            _ensure_kv(audit, [("file_creator", "maic")])
            _log("METADATA: set file_creator=maic")

    # -- Rewrite $585 features --
    frag585 = book.fragments.get("$585", first=True)
    if frag585 is not None:
        old = frag585.value.get("$590", [])
        ns_yj = "com.amazon.yjconversion"
        ns_sdk = "SDK.Marker"
        resources_for_features = {}
        for frag in book.fragments:
            if str(frag.ftype) == "$417":
                resources_for_features[str(frag.fid)] = frag.value
        jpg_main_entities = 0
        jpg_rst_entities = 0
        for frag in book.fragments:
            if str(frag.ftype) != "$164" or not hasattr(frag, "value"):
                continue
            fid = str(frag.fid)
            if fid.endswith("-thumb"):
                continue
            entity_val = frag.value
            resource_id = str(entity_val.get("$165", "") or "")
            resource_blob = resources_for_features.get(resource_id)
            if resource_blob is None:
                continue
            mime = str(entity_val.get("$162", "") or "")
            if mime and mime != "image/jpg":
                continue
            if not mime and not _blob_looks_like_jpeg(resource_blob):
                continue
            jpg_main_entities += 1
            if _jpeg_has_restart_markers(resource_blob):
                jpg_rst_entities += 1
        jpg_rst_feature_enabled = bool(jpg_main_entities) and jpg_rst_entities == jpg_main_entities
        drop_yj = {
            "reflow-style",
            "jp-reflow-language",
            "jpvertical-reflow-language",
            "yj_facing_page",
            "yj_jpg_rst_marker_present",
            "yj_textbook",
        }
        kept = [
            cf for cf in old
            if not (cf.get("$586", "") == ns_yj and cf.get("$492", "") in drop_yj)
        ]

        def _mk_ver(major, minor=0):
            return _ion_struct(
                _IS("version"), _ion_struct(_IS("$587"), major, _IS("$588"), minor)
            )

        desired = {
            (ns_yj, "yj_non_pdf_fixed_layout"): 2,
            (ns_yj, "yj_double_page_spread"): 1,
            (ns_yj, "yj_thumbnails_present"): 1,
            (ns_sdk, "CanonicalFormat"): 2,
        }
        if jpg_rst_feature_enabled:
            desired[(ns_yj, "yj_jpg_rst_marker_present")] = 1
        existing_f = {}
        for cf in kept:
            existing_f[(cf.get("$586", ""), cf.get("$492", ""))] = cf
        for (ns, fname), fver in desired.items():
            key = (ns, fname)
            if key in existing_f:
                existing_f[key][_IS("$589")] = _mk_ver(fver)
            else:
                kept.append(_ion_struct(
                    _IS("$586"), ns, _IS("$492"), fname, _IS("$589"), _mk_ver(fver)
                ))
        frag585.value[_IS("$590")] = kept
        _log("FEATURES_RST: %d/%d main JPEGs with restart markers" % (jpg_rst_entities, jpg_main_entities))
        _log("FEATURES: %s" % [cf.get("$492", "") for cf in kept])

    # -- KC reference does not set orientation flags in $258 --
    # Reading direction belongs in $538 only. Amazon books never carry $192
    # here, and kfxlib rejects it as "Unknown metadata"; writing it made the
    # device resolve the page-turn direction inverted.
    frag258 = book.fragments.get("$258")
    if frag258 is not None:
        _pop_key(frag258.value, "$192")
        _pop_key(frag258.value, "$217")
        _pop_key(frag258.value, "$218")

    # -- Set $538 document flags (Amazon YJ reference pattern) --
    # Amazon manga B0D45V4WDT (fixed-layout comic, drawn right-to-left) has:
    # $192=$375, $560=$557, $477=$56, $597={$614: d1ED}
    #
    # $192 is the reading direction: $375=rtl, $376=ltr.
    # $560 is writing-mode: $557=horizontal-tb, $559=vertical-rl, $558=vertical-lr.
    # A manga page is horizontal text, so writing-mode stays horizontal-tb and
    # the direction alone carries the page progression, exactly as Amazon does
    # it and as the page templates below already do. Forcing vertical-rl here
    # (copied from the vertical-text Japanese book B09YVK8W81) made every book
    # progress right-to-left on its own, and combined with an explicit rtl
    # direction the two cancelled out into left-to-right page turns.
    # Remove KC-specific flags that Amazon doesn't use
    frag538 = book.fragments.get("$538")
    if frag538 is not None:
        frag538.value[_IS("$192")] = _IS(direction_symbol)
        frag538.value[_IS("$560")] = _IS("$557")
        frag538.value[_IS("$477")] = _IS("$56")
        _pop_key(frag538.value, "$581")
        _pop_key(frag538.value, "$436")
        _pop_key(frag538.value, "$112")

        # Add $597 reference pointing to d1ED fragment
        frag538.value[_IS("$597")] = _ion_struct(_IS("$614"), _IS("d1ED"))
        _log("DOC_FLAGS: added $538.$597 -> d1ED")

    # -- Create $597 d1ED metadata fragment (Amazon YJ reference pattern) --
    existing_d1ed = book.fragments.get(ftype="$597", fid="d1ED")
    if existing_d1ed is None:
        book.create_local_symbol("d1ED")
        d1ed_value = _ion_struct(
            _IS("$598"), _IS("d1ED"),
            _IS("$258"), [
                _ion_struct(_IS("$492"), "has_large_data_table", _IS("$307"), False),
            ],
        )
        book.fragments.append(
            _yj_fragment(ftype=_IS("$597"), fid=_IS("d1ED"), value=d1ed_value)
        )
        needs_rebuild = True
        _log("METADATA: created $597 d1ED fragment")

    # -- Restructure layouts: merge pairs into facing-page layouts --
    sections_by_id, layouts_by_id, entities_by_id, entities_w_h, resources_by_id = _build_book_indexes(book)

    section_order = []
    if frag258 is not None:
        ordered258 = frag258.value.get("$169", [])
        section_order = _flatten_reading_order_entries(ordered258)
        if section_order and len(ordered258) > 1:
            frag258.value[_IS("$169")] = [
                _ion_struct(
                    _IS("$178"), _IS("$351"),
                    _IS("$170"), [_IS(sid) for sid in section_order],
                )
            ]
            needs_rebuild = True
            _log(
                "READING_ORDER: flattened $258 groups %d -> 1 (%d sections)"
                % (len(ordered258), len(section_order))
            )

    if frag538 is not None:
        ordered538 = frag538.value.get("$169", [])
        flat538 = _flatten_reading_order_entries(ordered538)
        target = section_order or flat538
        if target and (len(ordered538) > 1 or flat538 != target):
            frag538.value[_IS("$169")] = [
                _ion_struct(
                    _IS("$178"), _IS("$351"),
                    _IS("$170"), [_IS(sid) for sid in target],
                )
            ]
            needs_rebuild = True
            _log(
                "READING_ORDER: normalized $538 groups %d -> 1 (%d sections)"
                % (len(ordered538), len(target))
            )
        if not section_order:
            section_order = target

    _log("READING_DIR: %s" % ("rtl" if rtl_reading else "ltr"))

    explicit_pairs: list[dict[str, int | None]] = []
    for item in (explicit_split_pairs or []):
        if isinstance(item, dict):
            try:
                l_idx = int(item.get("left_idx"))  # type: ignore[arg-type]
                r_idx = int(item.get("right_idx"))  # type: ignore[arg-type]
            except Exception:
                continue
            explicit_pairs.append({
                "left_idx": l_idx,
                "right_idx": r_idx,
                "left_w": int(item.get("left_w")) if item.get("left_w") is not None else None,  # type: ignore[arg-type]
                "left_h": int(item.get("left_h")) if item.get("left_h") is not None else None,  # type: ignore[arg-type]
                "right_w": int(item.get("right_w")) if item.get("right_w") is not None else None,  # type: ignore[arg-type]
                "right_h": int(item.get("right_h")) if item.get("right_h") is not None else None,  # type: ignore[arg-type]
            })
        elif isinstance(item, (list, tuple)) and len(item) >= 2:
            try:
                l_idx = int(item[0])
                r_idx = int(item[1])
            except Exception:
                continue
            explicit_pairs.append({
                "left_idx": l_idx,
                "right_idx": r_idx,
                "left_w": None,
                "left_h": None,
                "right_w": None,
                "right_h": None,
            })

    merged_forced = 0
    merged_adjacent = 0
    merged_count = 0
    forced_spread_half_eids: set[str] = set()
    if enable_facing and len(section_order) > 2:
        pair_candidates = []
        for sid in section_order:
            sec = sections_by_id.get(sid)
            if sec is None:
                continue
            items = sec.value.get("$141", [])
            if not items:
                continue
            item0 = items[0]
            lid = str(item0.get("$176", ""))
            layout = layouts_by_id.get(lid)
            if layout is None:
                continue
            pages = layout.value.get("$146", [])
            if not isinstance(pages, list) or len(pages) != 1:
                continue
            pg = pages[0]
            eid = str(pg.get("$175", ""))
            if not eid:
                inner = pg.get("$146", [])
                if isinstance(inner, list) and inner:
                    eid = str(inner[0].get("$175", ""))
            if not eid:
                continue
            wh = entities_w_h.get(eid)
            if not wh:
                continue
            w, h = wh
            if w > 0 and h > 0 and w <= h:
                pair_candidates.append({
                    "sid": sid,
                    "layout": layout,
                    "page": pg,
                    "w": int(w),
                    "h": int(h),
                })

        candidate_by_sid = {str(c["sid"]): c for c in pair_candidates}
        skip_first = section_order[0] if section_order else None
        removed_sids = set()
        removed_layout_ids = set()
        used_sids = set()

        def _merge_pair(left_sid, right_sid, *, forced=False):
            left_sid = str(left_sid)
            right_sid = str(right_sid)
            if left_sid == right_sid:
                return False
            if left_sid in used_sids or right_sid in used_sids:
                return False
            left = candidate_by_sid.get(left_sid)
            right = candidate_by_sid.get(right_sid)
            if not left or not right:
                return False
            if forced:
                left_eid, _ = _walk_first_entity(left["page"])
                right_eid, _ = _walk_first_entity(right["page"])
                if left_eid:
                    forced_spread_half_eids.add(str(left_eid))
                if right_eid:
                    forced_spread_half_eids.add(str(right_eid))
            right_sec = sections_by_id.get(right_sid)
            right_lid = None
            if right_sec is not None:
                right_items = right_sec.value.get("$141", [])
                if right_items:
                    right_lid = str(right_items[0].get("$176", ""))
            left["layout"].value[_IS("$146")] = [left["page"], right["page"]]
            if right_sec is not None:
                book.fragments.remove(right_sec)
            if right_lid:
                removed_layout_ids.add(right_lid)
            removed_sids.add(right_sid)
            used_sids.add(left_sid)
            used_sids.add(right_sid)
            return True

        forced_total = len(explicit_pairs)

        def _dims_close(actual, expected) -> bool:
            if not actual or not expected:
                return False
            aw, ah = actual
            ew, eh = expected
            if aw is None or ah is None or ew is None or eh is None:
                return False
            return abs(int(aw) - int(ew)) <= 2 and abs(int(ah) - int(eh)) <= 2

        if forced_total:
            max_idx = len(section_order) - 1
            best_offset = 0
            best_key = None
            # Bias tie-breaking for cover/no-cover mismatches between EPUB spine
            # and KFX section order.
            offset_hint = 0
            if epub_first_spine_is_cover is not None:
                dims_freq = {}
                for c in pair_candidates:
                    key = (int(c.get("w") or 0), int(c.get("h") or 0))
                    dims_freq[key] = dims_freq.get(key, 0) + 1
                dominant_dims = None
                if dims_freq:
                    dominant_dims = max(dims_freq.items(), key=lambda kv: kv[1])[0]

                lead_coverlike = False
                first_sid = str(section_order[0]) if section_order else ""
                first_candidate = candidate_by_sid.get(first_sid)
                if dominant_dims and first_candidate:
                    dw, dh = dominant_dims
                    fw = int(first_candidate.get("w") or 0)
                    fh = int(first_candidate.get("h") or 0)
                    if dw > 0 and dh > 0 and fw > 0 and fh > 0:
                        # Consider lead page cover-like when dimensions differ
                        # significantly from dominant content page size.
                        lead_coverlike = (abs(fw - dw) > max(8, int(dw * 0.10))) or (
                            abs(fh - dh) > max(8, int(dh * 0.10))
                        )

                if lead_coverlike and not bool(epub_first_spine_is_cover):
                    offset_hint = 1
                elif (not lead_coverlike) and bool(epub_first_spine_is_cover):
                    offset_hint = -1

                _log(
                    "FACING_FORCED_HINT: epub_first_cover=%s lead_coverlike=%s offset_hint=%d"
                    % ("yes" if epub_first_spine_is_cover else "no", "yes" if lead_coverlike else "no", offset_hint)
                )

            # KFX order can be shifted by an inserted lead section (e.g., metadata cover).
            for offset in (-3, -2, -1, 0, 1, 2, 3):
                candidate_score = 0
                size_score = 0
                in_range = 0
                for pair in explicit_pairs:
                    l_idx = int(pair["left_idx"] or 0)
                    r_idx = int(pair["right_idx"] or 0)
                    li = l_idx + offset
                    ri = r_idx + offset
                    if li < 0 or ri < 0 or li > max_idx or ri > max_idx:
                        continue
                    in_range += 1
                    l_sid = str(section_order[li])
                    r_sid = str(section_order[ri])
                    if l_sid in candidate_by_sid and r_sid in candidate_by_sid:
                        candidate_score += 1
                        lw = candidate_by_sid[l_sid].get("w")
                        lh = candidate_by_sid[l_sid].get("h")
                        rw = candidate_by_sid[r_sid].get("w")
                        rh = candidate_by_sid[r_sid].get("h")
                        expected_left = (pair.get("left_w"), pair.get("left_h"))
                        expected_right = (pair.get("right_w"), pair.get("right_h"))
                        if _dims_close((lw, lh), expected_left) and _dims_close((rw, rh), expected_right):
                            size_score += 2
                        elif _dims_close((lw, lh), expected_right) and _dims_close((rw, rh), expected_left):
                            # Allow swapped size hints; prefer exact orientation match above.
                            size_score += 1
                score_key = (
                    size_score,
                    candidate_score,
                    in_range,
                    -abs(offset - offset_hint),
                    -abs(offset),
                )
                if best_key is None or score_key > best_key:
                    best_key = score_key
                    best_offset = offset

            for pair in explicit_pairs:
                l_idx = int(pair["left_idx"] or 0)
                r_idx = int(pair["right_idx"] or 0)
                li = l_idx + best_offset
                ri = r_idx + best_offset
                if li < 0 or ri < 0 or li >= len(section_order) or ri >= len(section_order):
                    continue
                if _merge_pair(section_order[li], section_order[ri], forced=True):
                    merged_forced += 1

            if best_key is not None:
                _log(
                    "FACING_FORCED: offset=%d size_score=%d candidate_score=%d in_range=%d"
                    % (best_offset, best_key[0], best_key[1], best_key[2])
                )

        _log("FACING_FORCED: merged %d/%d explicit split pairs" % (merged_forced, forced_total))

        # Build segments of unpaired pages between forced pairs.
        # Each segment is a contiguous run of candidate sections in
        # section_order that are NOT used by forced pairs and not the
        # cover.  Segments are separated by forced-pair positions so
        # that sequential pairing never jumps across a forced spread.
        if merge_adjacent_pairs:
            candidate_set = {str(c["sid"]) for c in pair_candidates}
            segments: list[list[str]] = []
            cur_seg: list[str] = []
            for sid in section_order:
                sid_s = str(sid)
                if sid_s == str(skip_first):
                    continue
                if sid_s in used_sids:
                    # Forced pair boundary -- flush current segment
                    if cur_seg:
                        segments.append(cur_seg)
                        cur_seg = []
                    continue
                if sid_s in candidate_set:
                    cur_seg.append(sid_s)
                else:
                    # Non-candidate section (landscape / multi-page) -- also a boundary
                    if cur_seg:
                        segments.append(cur_seg)
                        cur_seg = []
            if cur_seg:
                segments.append(cur_seg)

            seg_sizes = [len(s) for s in segments]
            _log("FACING_SEGMENTS: %d segments, sizes=%s" % (len(segments), seg_sizes))

            for seg in segments:
                if len(seg) % 2 != 0:
                    seg.pop()  # drop last orphan in this segment
                for i in range(0, len(seg), 2):
                    if _merge_pair(seg[i], seg[i + 1]):
                        merged_adjacent += 1
        else:
            _log("FACING_ADJACENT: skipped automatic adjacent pairing (explicit pairs only)")

        if removed_sids:
            for order_frag in (book.fragments.get("$258"), book.fragments.get("$538")):
                if order_frag is None:
                    continue
                ordered = order_frag.value.get("$169", [])
                if not ordered:
                    continue
                old_list = ordered[0].get("$170", [])
                ordered[0][_IS("$170")] = [s for s in old_list if str(s) not in removed_sids]
            section_order = [sid for sid in section_order if str(sid) not in removed_sids]

        for rid in list(removed_layout_ids):
            right_layout = book.fragments.get(ftype="$259", fid=rid)
            if right_layout is not None:
                book.fragments.remove(right_layout)
            layouts_by_id.pop(str(rid), None)
        for rsid in list(removed_sids):
            sections_by_id.pop(str(rsid), None)

        merged_count = merged_forced + merged_adjacent
        _log("FACING: merged %d total (%d forced + %d adjacent), removed %d sections"
             % (merged_count, merged_forced, merged_adjacent, len(removed_sids)))
        if merged_count:
            needs_rebuild = True
    else:
        if not enable_facing:
            _log("FACING: layout restructuring disabled (metadata only)")
        else:
            _log("FACING: too few sections to pair (%d)" % len(section_order))

    nav_pid_aliases: dict[int, int] = {}

    def _node_pids(node) -> set[int]:
        pids: set[int] = set()

        def _walk(n):
            if not hasattr(n, "get"):
                return
            pid = n.get("$155")
            if isinstance(pid, int):
                pids.add(int(pid))
            for child in (n.get("$146") or []):
                _walk(child)

        _walk(node)
        return pids

    def _record_nav_pid_aliases(old_pids: set[int], new_pids: set[int], target_pid) -> None:
        if not isinstance(target_pid, int):
            return
        target = int(target_pid)
        for old_pid in old_pids:
            if old_pid not in new_pids:
                nav_pid_aliases.setdefault(old_pid, target)

    # -- PID allocator for unique wrapper position IDs --
    pid_alloc = _PidAllocator(book)

    # -- Create Amazon-pattern styles for spread pages --
    # Amazon B09YVK8W81 3-level nesting: outer page > sJ (pass) > sG (image)
    # No sP (background) or sM (spread) wrapper — styling is on the outer page node.

    # sJ: passthrough container style — Amazon uses percentage-based 100% sizing
    # Amazon B09YVK8W81 sJ: $56={$307:100,$306:$314}, $57={$307:100,$306:$314}, $10='ja'
    _sj_id = "sJ"
    _sj_frag = book.fragments.get(ftype="$157", fid=_sj_id)
    if _sj_frag is not None:
        # Fix existing sJ style to match Amazon pattern
        old_val = _sj_frag.value
        _sj_frag.value = _ion_struct(
            _IS("$56"), _ion_struct(_IS("$307"), 100.0, _IS("$306"), _IS("$314")),
            _IS("$57"), _ion_struct(_IS("$307"), 100.0, _IS("$306"), _IS("$314")),
            _IS("$10"), "ja",
            _IS("$173"), _IS(_sj_id),
        )
        needs_rebuild = True
        _log("STYLES: fixed sJ to Amazon percentage-based pattern")
    else:
        book.create_local_symbol(_sj_id)
        _sj_value = _ion_struct(
            _IS("$56"), _ion_struct(_IS("$307"), 100.0, _IS("$306"), _IS("$314")),
            _IS("$57"), _ion_struct(_IS("$307"), 100.0, _IS("$306"), _IS("$314")),
            _IS("$10"), "ja",
            _IS("$173"), _IS(_sj_id),
        )
        book.fragments.append(
            _yj_fragment(ftype=_IS("$157"), fid=_IS(_sj_id), value=_sj_value)
        )
        needs_rebuild = True
        _log("STYLES: created sJ (percentage 100%, Amazon pattern)")

    # sG: leaf style for full (single) pages.
    # sH: leaf style for spread halves (narrower).
    # $580=$320 = fit/center mode on both.
    _all_max_w = max((wh[0] for wh in entities_w_h.values()), default=0)
    _all_max_h = max((wh[1] for wh in entities_w_h.values()), default=0)
    _forced_spread_half_eids = {
        eid for eid in forced_spread_half_eids
        if eid in entities_w_h
    }
    _spread_half_eids: set[str] = set(_forced_spread_half_eids)
    if _forced_spread_half_eids:
        _log(
            "STYLES: spread halves from explicit split pairs: %d entities"
            % len(_forced_spread_half_eids)
        )
    elif not explicit_pairs:
        # Fallback for books without explicit -kcc-b/-kcc-c pairs: identify
        # spread halves by entity width. Use a tolerance instead of a single
        # strict bucket because near-equal source spreads can differ by a few
        # pixels after KPR/KCC scaling.
        _spread_half_eids = {
            eid for eid, wh in entities_w_h.items()
            if _all_max_w > 0 and _all_max_h > 0
            and wh[0] < _all_max_w * 0.985
            and wh[1] >= _all_max_h * 0.90
        }
        if _spread_half_eids:
            _log(
                "STYLES: spread halves from size fallback: %d entities"
                % len(_spread_half_eids)
            )
    _full_wh = [(wh[0], wh[1]) for eid, wh in entities_w_h.items() if eid not in _spread_half_eids]
    _half_wh = [(wh[0], wh[1]) for eid, wh in entities_w_h.items() if eid in _spread_half_eids]
    _sg_max_w = max((w for w, h in _full_wh), default=_all_max_w)
    _sg_max_h = max((h for w, h in _full_wh), default=_all_max_h)
    _sh_max_w = max((w for w, h in _half_wh), default=0)
    _sh_max_h = max((h for w, h in _half_wh), default=0)
    if _spread_half_eids:
        _log("STYLES: spread halves detected: %d entities (%dx%d)" % (len(_spread_half_eids), _sh_max_w, _sh_max_h))

    spread_style_index = _build_style_index(book)

    def _ensure_leaf_style(style_id, max_w, max_h):
        if style_id in spread_style_index:
            frag = spread_style_index[style_id]
            frag.value[_IS("$56")] = float(max_w)
            frag.value[_IS("$57")] = float(max_h)
            _log("STYLES: updated %s (%dx%d)" % (style_id, max_w, max_h))
        else:
            book.create_local_symbol(style_id)
            val = _ion_struct(
                _IS("$56"), float(max_w),
                _IS("$57"), float(max_h),
                _IS("$58"), 0.0,
                _IS("$59"), 0.0,
                _IS("$580"), _IS("$320"),
                _IS("$173"), _IS(style_id),
            )
            new_frag = _yj_fragment(ftype=_IS("$157"), fid=_IS(style_id), value=val)
            book.fragments.append(new_frag)
            spread_style_index[style_id] = new_frag
            _log("STYLES: created %s (%dx%d)" % (style_id, max_w, max_h))

    _sg_id = "sG"
    _ensure_leaf_style(_sg_id, _sg_max_w, _sg_max_h)

    _sh_id = "sH"
    if _sh_max_w > 0 and _sh_max_h > 0:
        _ensure_leaf_style(_sh_id, _sh_max_w, _sh_max_h)
    else:
        _sh_id = _sg_id  # fallback: no spread halves detected

    # No sM style needed — Amazon B09YVK8W81 doesn't use spread containers.

    # -- Normalize spread sections to Amazon B09YVK8W81 structure --
    # Three-level nesting: outer page ($270/$326) > pass ($270/$323/sJ) > leaf ($271/sG)
    # Section template: $156=$437 (spread), no explicit dims.
    # Outer page: $192=$376, $16=16.0, $560=$557, $156=$326, $140=$320, dims = image 1:1.
    kc_norm_sections = 0
    kc_norm_pages = 0
    for sid in section_order[1:]:
        sec = sections_by_id.get(sid)
        if sec is None:
            continue
        items = sec.value.get("$141", [])
        if not items:
            continue
        item0 = items[0]
        lid = str(item0.get("$176", ""))
        layout = layouts_by_id.get(lid)
        if layout is None:
            continue
        pages = layout.value.get("$146", [])
        if not isinstance(pages, list) or len(pages) < 2:
            continue

        # Section template: spread marker, NO explicit dimensions
        item0[_IS("$159")] = _IS("$270")
        item0[_IS("$156")] = _IS("$437")
        item0[_IS("$434")] = _IS("$441")
        _pop_key(item0, "$140")
        _pop_key(item0, "$66")
        _pop_key(item0, "$67")

        for pg in pages[:2]:
            if not hasattr(pg, "get"):
                continue
            old_pids = _node_pids(pg)

            # Extract image entity reference (handle flat, 2-level, 3-level, 4-level)
            eid_raw = None
            inner_pid = None

            def _find_leaf(node, depth=0):
                nonlocal eid_raw, inner_pid
                if depth > 5 or not hasattr(node, "get"):
                    return
                e = node.get("$175")
                if e is not None:
                    eid_raw = e
                    inner_pid = node.get("$155")
                    return
                for child in (node.get("$146") or []):
                    _find_leaf(child, depth + 1)
                    if eid_raw is not None:
                        return

            _find_leaf(pg)

            eid = str(eid_raw or "")
            w, h = entities_w_h.get(eid, (0, 0))
            if not w or not h:
                continue

            # Use sH for spread halves (narrower), sG for regular pages.
            is_half = eid in _spread_half_eids
            _leaf_style = _sh_id if is_half else _sg_id
            page_w = int(_sh_max_w) if is_half else int(_sg_max_w)
            page_h = int(_sh_max_h) if is_half else int(_sg_max_h)

            # Build leaf image node ($271 with matching leaf style)
            leaf = _ion_struct(
                _IS("$155"), inner_pid if inner_pid is not None else pid_alloc.alloc(),
                _IS("$157"), _IS(_leaf_style),
                _IS("$159"), _IS("$271"),
                _IS("$175"), eid_raw,
            )

            # Build passthrough container ($270/$323/sJ)
            passthrough = _ion_struct(
                _IS("$155"), pid_alloc.alloc(),
                _IS("$156"), _IS("$323"),
                _IS("$157"), _IS(_sj_id),
                _IS("$159"), _IS("$270"),
                _IS("$146"), [leaf],
            )

            # Rebuild outer page wrapper on pg in-place ($270/$326, direct styling)
            outer_pid = pg.get("$155")
            if outer_pid is None or outer_pid == inner_pid:
                outer_pid = pid_alloc.alloc()

            pg[_IS("$155")] = outer_pid
            pg[_IS("$192")] = _IS("$376")
            pg[_IS("$16")] = 16.0
            pg[_IS("$560")] = _IS("$557")
            pg[_IS("$66")] = page_w
            pg[_IS("$67")] = page_h
            pg[_IS("$156")] = _IS("$326")
            pg[_IS("$140")] = _IS("$320")
            pg[_IS("$159")] = _IS("$270")
            pg[_IS("$146")] = [passthrough]
            _pop_key(pg, "$175")
            _pop_key(pg, "$183")
            _pop_key(pg, "$546")
            _pop_key(pg, "$56")
            _pop_key(pg, "$57")
            _pop_key(pg, "$157")
            _record_nav_pid_aliases(old_pids, _node_pids(pg), outer_pid)
            kc_norm_pages += 1

        kc_norm_sections += 1

    if kc_norm_sections:
        needs_rebuild = True
    _log("KC_NORM: updated %d sections (%d pages) [Amazon 3-level]" % (kc_norm_sections, kc_norm_pages))

    # -- Normalize cover section/layout to Amazon pattern --
    # Amazon reference: cover layout is a flat $271 node with resource ref only.
    # Cover section template has explicit $66/$67 dimensions.
    if section_order:
        cover_sid = section_order[0]
        cover_sec = sections_by_id.get(cover_sid)
        if cover_sec is not None:
            cover_items = cover_sec.value.get("$141", [])
            if cover_items:
                ci0 = cover_items[0]
                cover_lid = str(ci0.get("$176", ""))
                cover_layout = layouts_by_id.get(cover_lid)
                if cover_layout is not None:
                    cover_pages = cover_layout.value.get("$146", [])
                    if isinstance(cover_pages, list) and cover_pages:
                        # Find cover image entity (traverse any nesting depth)
                        eid_raw = None
                        cover_pid = None

                        def _find_cover_entity(node):
                            nonlocal eid_raw, cover_pid
                            if not hasattr(node, "get"):
                                return
                            e = node.get("$175")
                            if e is not None:
                                eid_raw = e
                                cover_pid = node.get("$155")
                                return
                            for child in (node.get("$146") or []):
                                _find_cover_entity(child)
                                if eid_raw is not None:
                                    return

                        for pg in cover_pages:
                            _find_cover_entity(pg)
                            if eid_raw is not None:
                                break

                        eid = str(eid_raw or "")
                        w, h = entities_w_h.get(eid, (0, 0))
                        if not w or not h:
                            w = ci0.get("$66", 0)
                            h = ci0.get("$67", 0)

                        if w and h:
                            # Cover: flat $271 node (no sJ/sG wrapping)
                            cover_inner = _ion_struct(
                                _IS("$159"), _IS("$271"),
                            )
                            if cover_pid is not None:
                                cover_inner[_IS("$155")] = cover_pid
                            if eid_raw is not None:
                                cover_inner[_IS("$175")] = eid_raw

                            cover_layout.value[_IS("$146")] = [cover_inner]

                            # Section template: explicit dims
                            ci0[_IS("$434")] = _IS("$441")
                            ci0[_IS("$159")] = _IS("$270")
                            ci0[_IS("$156")] = _IS("$326")
                            ci0[_IS("$140")] = _IS("$320")
                            ci0[_IS("$66")] = int(w)
                            ci0[_IS("$67")] = int(h)
                            needs_rebuild = True
                            _log("COVER: normalized to Amazon pattern (w=%d h=%d)" % (w, h))

                            # Set cover_image in $490 kindle_title_metadata
                            # Amazon uses the entity fid (e.g. "e6") as cover_image value
                            if eid_raw is not None:
                                frag490 = book.fragments.get("$490")
                                if frag490 is not None:
                                    cats490 = frag490.value.get("$491")
                                    if cats490 is not None:
                                        title_meta = _find_or_add_category(
                                            cats490, "kindle_title_metadata")
                                        _drop_kv(title_meta, ["cover_image"])
                                        _ensure_kv(title_meta,
                                                   [("cover_image", str(eid_raw))])
                                        _log("COVER: set $490 cover_image=%s"
                                             % str(eid_raw))

    # -- Normalize remaining single-page sections to Amazon pattern --
    # Amazon B09YVK8W81: all pages use 3-level nesting: viewport → sJ → sG.
    # Section template: $434=$441, $156=$326, $140=$320.
    # Viewport page: $192=$376, $16=16, $560=$557, $66/$67, $156=$326, $140=$320.
    kc_norm_single_sections = 0
    kc_norm_single_pages = 0

    for sid in section_order[1:]:
        sec = sections_by_id.get(sid)
        if sec is None:
            continue
        items = sec.value.get("$141", [])
        if not items:
            continue
        item0 = items[0]
        lid = str(item0.get("$176", ""))
        layout = layouts_by_id.get(lid)
        if layout is None:
            continue
        pages = layout.value.get("$146", [])
        if not isinstance(pages, list) or len(pages) != 1:
            continue

        pg = pages[0]
        if not hasattr(pg, "get"):
            continue
        old_pids = _node_pids(pg)

        # Find image entity (traverse any nesting depth)
        eid_raw = None
        img_pid = None

        def _find_single_entity(node):
            nonlocal eid_raw, img_pid
            if not hasattr(node, "get"):
                return
            e = node.get("$175")
            if e is not None:
                eid_raw = e
                img_pid = node.get("$155")
                return
            for child in (node.get("$146") or []):
                _find_single_entity(child)
                if eid_raw is not None:
                    return

        _find_single_entity(pg)
        if eid_raw is None:
            continue

        eid = str(eid_raw or "")
        ent_w, ent_h = entities_w_h.get(eid, (0, 0))
        w = (
            _to_int_or_none(ent_w)
            or _to_int_or_none(pg.get("$56"))
            or _to_int_or_none(pg.get("$66"))
            or _to_int_or_none(item0.get("$66"))
            or 0
        )
        h = (
            _to_int_or_none(ent_h)
            or _to_int_or_none(pg.get("$57"))
            or _to_int_or_none(pg.get("$67"))
            or _to_int_or_none(item0.get("$67"))
            or 0
        )
        if not w or not h:
            continue

        # Section template: full properties (working version)
        item0[_IS("$192")] = _IS("$376")
        item0[_IS("$16")] = 16.0
        item0[_IS("$560")] = _IS("$557")
        item0[_IS("$66")] = int(_sg_max_w)
        item0[_IS("$67")] = int(_sg_max_h)
        item0[_IS("$434")] = _IS("$441")
        item0[_IS("$156")] = _IS("$326")
        item0[_IS("$140")] = _IS("$320")
        item0[_IS("$159")] = _IS("$270")

        # Layout: sJ→sG wrapper directly in layout
        leaf = _ion_struct(
            _IS("$155"), img_pid if img_pid is not None else pid_alloc.alloc(),
            _IS("$157"), _IS(_sg_id),
            _IS("$159"), _IS("$271"),
            _IS("$175"), eid_raw,
        )
        passthrough = _ion_struct(
            _IS("$155"), pid_alloc.alloc(),
            _IS("$156"), _IS("$323"),
            _IS("$157"), _IS(_sj_id),
            _IS("$159"), _IS("$270"),
            _IS("$146"), [leaf],
        )

        layout.value[_IS("$146")] = [passthrough]
        _record_nav_pid_aliases(old_pids, _node_pids(passthrough), passthrough.get("$155"))

        kc_norm_single_sections += 1
        kc_norm_single_pages += 1

    if kc_norm_single_sections:
        needs_rebuild = True
    _log(
        "KC_NORM_SINGLE: updated %d sections (%d pages)"
        % (kc_norm_single_sections, kc_norm_single_pages)
    )

    # Refresh indexes after all structural edits before metadata/resource passes.
    sections_by_id, layouts_by_id, entities_by_id, entities_w_h, resources_by_id = _build_book_indexes(book)

    # -- Externalize inline nav containers to standalone $391 fragments --
    frag389 = book.fragments.get("$389", first=True)
    nav_refs_rewritten = 0
    nav_fragments_created = 0
    existing_nav_ids = {str(getattr(frag, "fid", "")) for frag in book.fragments if str(getattr(frag, "ftype", "")) == "$391"}

    if frag389 is not None and isinstance(frag389.value, list):
        for nav in frag389.value:
            if not hasattr(nav, "get"):
                continue
            nav_containers = nav.get("$392", [])
            if not isinstance(nav_containers, list) or not nav_containers:
                continue
            new_refs = []
            changed = False
            for nav_container in nav_containers:
                nav_data = _ion_unannotated(nav_container)
                if isinstance(nav_data, str):
                    new_refs.append(nav_data)
                    continue
                if not hasattr(nav_data, "get"):
                    new_refs.append(nav_container)
                    continue

                nav_fid = str(nav_data.get("$239", "") or "")
                if not nav_fid:
                    nav_fid = str(_allocate_local_symbol(book, existing_nav_ids, "nNav"))
                    nav_data[_IS("$239")] = _IS(nav_fid)
                elif nav_fid not in existing_nav_ids:
                    existing_nav_ids.add(nav_fid)
                    book.create_local_symbol(nav_fid)

                if book.fragments.get(ftype="$391", fid=nav_fid) is None:
                    book.fragments.append(
                        _yj_fragment(ftype=_IS("$391"), fid=_IS(nav_fid), value=nav_data)
                    )
                    nav_fragments_created += 1

                new_refs.append(_IS(nav_fid))
                changed = True
                nav_refs_rewritten += 1

            if changed:
                nav[_IS("$392")] = new_refs

    nav_types = set()
    if frag389 is not None and isinstance(frag389.value, list):
        for nav in frag389.value:
            if not hasattr(nav, "get"):
                continue
            for nav_ref in nav.get("$392", []):
                nav_fid = str(_ion_unannotated(nav_ref) or "")
                if not nav_fid:
                    continue
                nav_frag = book.fragments.get(ftype="$391", fid=nav_fid)
                if nav_frag is None or not hasattr(nav_frag, "value"):
                    continue
                nav_types.add(str(nav_frag.value.get("$235", "") or ""))

    if "$236" not in nav_types and section_order:
        nav_entries = []
        cover_sec = sections_by_id.get(str(section_order[0]))
        if cover_sec is not None:
            cover_items = cover_sec.value.get("$141", [])
            if cover_items:
                cover_layout = layouts_by_id.get(str(cover_items[0].get("$176", "") or ""))
                if cover_layout is not None:
                    cover_pages = cover_layout.value.get("$146", [])
                    if isinstance(cover_pages, list) and cover_pages:
                        cover_pid = _walk_first_pid(cover_pages[0])
                        if cover_pid is not None:
                            nav_entries.append(_ion_struct(
                                _IS("$238"), _IS("$233"),
                                _IS("$241"), _ion_struct(_IS("$244"), "cover-nav-unit"),
                                _IS("$246"), _ion_struct(_IS("$155"), cover_pid, _IS("$143"), 0),
                            ))

        if len(section_order) > 1:
            content_sec = sections_by_id.get(str(section_order[1]))
            if content_sec is not None:
                content_items = content_sec.value.get("$141", [])
                if content_items:
                    content_layout = layouts_by_id.get(str(content_items[0].get("$176", "") or ""))
                    if content_layout is not None:
                        content_pages = content_layout.value.get("$146", [])
                        if isinstance(content_pages, list) and content_pages:
                            content_pid = _walk_first_pid(content_pages[0])
                            if content_pid is not None:
                                nav_entries.append(_ion_struct(
                                    _IS("$241"), _ion_struct(_IS("$244"), "Start of Content"),
                                    _IS("$246"), _ion_struct(_IS("$155"), content_pid, _IS("$143"), 0),
                                ))

        if nav_entries:
            nav_fid = "n1E2"
            if nav_fid not in existing_nav_ids:
                existing_nav_ids.add(nav_fid)
                book.create_local_symbol(nav_fid)
            nav_value = _ion_struct(
                _IS("$235"), _IS("$236"),
                _IS("$239"), _IS(nav_fid),
                _IS("$247"), nav_entries,
            )
            if book.fragments.get(ftype="$391", fid=nav_fid) is None:
                book.fragments.append(
                    _yj_fragment(ftype=_IS("$391"), fid=_IS(nav_fid), value=nav_value)
                )
                nav_fragments_created += 1

            if frag389 is not None and isinstance(frag389.value, list) and frag389.value:
                target_nav = None
                for nav in frag389.value:
                    if hasattr(nav, "get") and str(nav.get("$178", "") or "") == "$351":
                        target_nav = nav
                        break
                if target_nav is None:
                    target_nav = _ion_struct(_IS("$178"), _IS("$351"), _IS("$392"), [_IS(nav_fid)])
                    frag389.value.append(target_nav)
                else:
                    current_refs = list(target_nav.get("$392", []))
                    if _IS(nav_fid) not in current_refs and nav_fid not in [str(_ion_unannotated(x) or "") for x in current_refs]:
                        current_refs.append(_IS(nav_fid))
                        target_nav[_IS("$392")] = current_refs
            _log("NAV: created standalone $391 %s with %d entries" % (nav_fid, len(nav_entries)))

    if nav_pid_aliases:
        nav_pid_rewrites = 0
        for nav_frag in book.fragments.get_all(ftype="$391"):
            if nav_frag is None or not hasattr(nav_frag, "value") or not hasattr(nav_frag.value, "get"):
                continue
            for entry in nav_frag.value.get("$247", []) or []:
                entry_data = _ion_unannotated(entry)
                if not hasattr(entry_data, "get"):
                    continue
                target = entry_data.get("$246")
                if not hasattr(target, "get"):
                    continue
                old_pid = target.get("$155")
                if not isinstance(old_pid, int):
                    continue
                new_pid = nav_pid_aliases.get(int(old_pid))
                if not isinstance(new_pid, int) or new_pid == old_pid:
                    continue
                target[_IS("$155")] = int(new_pid)
                nav_pid_rewrites += 1
        if nav_pid_rewrites:
            needs_rebuild = True
            _log("NAV: rewrote %d TOC target pid(s) after layout normalization" % nav_pid_rewrites)

    if nav_refs_rewritten or nav_fragments_created:
        needs_rebuild = True
        _log(
            "NAV: externalized %d inline refs, created %d $391 fragments"
            % (nav_refs_rewritten, nav_fragments_created)
        )

    # -- Generate actual thumbnail entities/resources for page images --
    thumb_entities_created = 0
    thumb_resources_written = 0
    thumb_failures = 0
    page_entity_ids = _collect_section_page_entities(section_order, sections_by_id, layouts_by_id)

    if page_entity_ids:
        try:
            import io
            from PIL import Image
        except Exception as exc:
            _log("THUMBS: skipped thumbnail generation (%s)" % exc)
        else:
            existing_entity_ids = set(entities_by_id.keys())
            existing_resource_ids = set(resources_by_id.keys())

            for eid in page_entity_ids:
                entity_frag = entities_by_id.get(str(eid))
                if entity_frag is None or not hasattr(entity_frag, "value"):
                    continue
                entity_val = entity_frag.value
                resource_id = str(entity_val.get("$165", "") or "")
                resource_frag = resources_by_id.get(resource_id)
                if resource_frag is None:
                    continue

                thumb_id = str(entity_val.get("$214", "") or "")
                thumb_frag = entities_by_id.get(thumb_id) if thumb_id else None
                existing_thumb_resource_id = ""
                if thumb_frag is not None and hasattr(thumb_frag, "value"):
                    existing_thumb_resource_id = str(thumb_frag.value.get("$165", "") or "")
                if existing_thumb_resource_id and _thumb_resource_is_paired(resource_id, existing_thumb_resource_id):
                    continue

                try:
                    image = Image.open(io.BytesIO(bytes(resource_frag.value)))
                    if image.mode not in {"RGB", "L"}:
                        image = image.convert("RGB")
                    image.thumbnail((512, 512), Image.LANCZOS)
                    thumb_w, thumb_h = image.size
                    out = io.BytesIO()
                    image.save(out, "JPEG", quality=50, optimize=True)
                    image.close()
                    thumb_data = out.getvalue()
                except Exception:
                    thumb_failures += 1
                    continue

                if not thumb_id:
                    thumb_id = str(_allocate_thumb_symbol(book, existing_entity_ids, eid))
                    entity_val[_IS("$214")] = _IS(thumb_id)

                thumb_resource_id = ""
                thumb_res_frag = None
                if thumb_frag is not None and hasattr(thumb_frag, "value"):
                    thumb_resource_id = str(thumb_frag.value.get("$165", "") or "")
                    thumb_res_frag = resources_by_id.get(thumb_resource_id)

                if thumb_resource_id and not _thumb_resource_is_paired(resource_id, thumb_resource_id):
                    if thumb_res_frag is not None:
                        try:
                            book.fragments.remove(thumb_res_frag)
                        except Exception:
                            pass
                        resources_by_id.pop(thumb_resource_id, None)
                    thumb_resource_id = ""
                    thumb_res_frag = None

                if not thumb_resource_id:
                    thumb_resource_id = str(
                        _allocate_paired_resource_symbol(book, existing_resource_ids, resource_id)
                    )

                if thumb_frag is None:
                    thumb_frag = _yj_fragment(
                        ftype=_IS("$164"),
                        fid=_IS(thumb_id),
                        value=_ion_struct(_IS("$175"), _IS(thumb_id)),
                    )
                    book.fragments.append(thumb_frag)
                    entities_by_id[thumb_id] = thumb_frag
                    thumb_entities_created += 1

                thumb_val = thumb_frag.value
                thumb_val[_IS("$161")] = _IS("$285")
                thumb_val[_IS("$162")] = "image/jpg"
                thumb_val[_IS("$165")] = thumb_resource_id
                thumb_val[_IS("$175")] = _IS(thumb_id)
                thumb_val[_IS("$422")] = int(thumb_w)
                thumb_val[_IS("$423")] = int(thumb_h)
                _pop_key(thumb_val, "$56")
                _pop_key(thumb_val, "$57")
                _pop_key(thumb_val, "$66")
                _pop_key(thumb_val, "$67")

                thumb_res_frag = resources_by_id.get(thumb_resource_id) if thumb_res_frag is None else thumb_res_frag
                if thumb_res_frag is None:
                    thumb_res_frag = _yj_fragment(
                        ftype=_IS("$417"),
                        fid=_IS(thumb_resource_id),
                        value=_ion_blob(thumb_data),
                    )
                    book.fragments.append(thumb_res_frag)
                    resources_by_id[thumb_resource_id] = thumb_res_frag
                else:
                    thumb_res_frag.value = _ion_blob(thumb_data)
                thumb_resources_written += 1

    if thumb_entities_created or thumb_resources_written:
        needs_rebuild = True
        _log(
            "THUMBS: created %d thumb entities, wrote %d resources"
            % (thumb_entities_created, thumb_resources_written)
        )
    elif thumb_failures:
        _log("THUMBS: no thumbnails written (%d decode failures)" % thumb_failures)

    paired_resource_ids, paired_resource_count = _build_paired_page_resource_order(
        page_entity_ids, entities_by_id, resources_by_id
    )

    # -- Ensure $162 (content_type) on all $164 entities --
    # Amazon B09YVK8W81 has $162:'image/jpg' on every entity.
    # KPR sometimes omits $162 on page images (only thumbnails get it).
    _ct_fixed = 0
    for frag in book.fragments:
        if str(frag.ftype) != "$164" or not hasattr(frag.value, "get"):
            continue
        if frag.value.get("$162") is None:
            # Determine content type from resource reference
            res_ref = str(frag.value.get("$165", "") or "")
            ct = "image/jpg"  # default for manga page images
            if res_ref:
                res_frag = resources_by_id.get(
                    res_ref.replace("resource/", "")
                ) or resources_by_id.get(res_ref)
                if res_frag is not None:
                    raw = res_frag.value
                    if isinstance(raw, (bytes, bytearray)) and len(raw) > 4:
                        if raw[:4] == b"\x89PNG":
                            ct = "image/png"
            frag.value[_IS("$162")] = ct
            _ct_fixed += 1
    if _ct_fixed:
        _log("ENTITY_FIX: added $162 content_type to %d entities" % _ct_fixed)

    # -- Single consolidated rebuild pass --
    if needs_rebuild:
        # Rebuild position/location maps AFTER all structural changes
        # (facing merge, KC normalization, cover normalization, alignment)
        pos_info = book.collect_content_position_info()
        book.create_position_map(pos_info)
        # Approximate KFX locations reset at each section.  Once two comic
        # pages share a facing section that collapses them to one displayed
        # location.  The image nodes remain separate, so use them as the exact
        # one-page-per-location targets, matching the native MOBI DATP path.
        loc_info = [chunk for chunk in pos_info
                    if getattr(chunk, "image_resource", None) is not None]
        if not loc_info:
            loc_info = book.generate_approximate_locations(pos_info)
        book.create_location_map(loc_info)
        _log("LOCATION_MAP: %d page locations" % len(loc_info))

        # De-duplicate fragments before validation (style creation can race
        # with kfxlib internal rebuild which may re-create fragments).
        _seen_keys = set()
        _dedup = []
        for _f in book.fragments:
            _fkey = (str(_f.ftype), str(_f.fid))
            if _fkey in _seen_keys:
                _log("DEDUP: removing duplicate fragment %s:%s" % _fkey)
                continue
            _seen_keys.add(_fkey)
            _dedup.append(_f)
        if len(_dedup) != len(book.fragments):
            book.fragments.clear()
            book.fragments.extend(_dedup)

        book.check_fragment_usage(rebuild=True, ignore_extra=True)
        book.check_symbol_table(rebuild=True, ignore_unused=True)

    reordered_resources = _reorder_resource_fragments(book, paired_resource_ids)
    if reordered_resources:
        _log(
            "THUMBS_ORDER: reordered %d resources across %d main/thumb pairs"
            % (reordered_resources, paired_resource_count)
        )

    return book


# -- Standalone script entry point --

def _install_kfxlib_calibre_shim():
    """Provide minimal calibre tweaks module required by bundled kfxlib."""
    if "calibre.utils.config_base" in sys.modules:
        return

    calibre_mod = sys.modules.get("calibre")
    if calibre_mod is None:
        calibre_mod = types.ModuleType("calibre")

    utils_mod = sys.modules.get("calibre.utils")
    if utils_mod is None:
        utils_mod = types.ModuleType("calibre.utils")

    cfg_mod = types.ModuleType("calibre.utils.config_base")
    cfg_mod.tweaks = {}

    setattr(utils_mod, "config_base", cfg_mod)
    setattr(calibre_mod, "utils", utils_mod)
    sys.modules["calibre"] = calibre_mod
    sys.modules["calibre.utils"] = utils_mod
    sys.modules["calibre.utils.config_base"] = cfg_mod


def convert_book_to_kfx_files(book, out_path, log_fn=None):
    """Convert a decoded YJ_Book to device-compatible KFX file(s).

    For small books (<16 MB), produces a single .kfx file.
    For large books, produces Amazon-style multi-container output:
      - <name>.kfx       (main container: structure, styles, metadata)
      - <name>.sdr/      (resource directory — Kindle's sideload convention)
        - 0.res … N.res  (attachable containers: resources, ~3 MB each)

    Returns list of output file paths.
    """
    import copy
    import hashlib
    _init_kfxlib_types()
    try:
        from calibre_plugins.kfx_output.kfxlib.kfx_container import (
            KfxContainer, CONTAINER_FRAGMENT_TYPES, RAW_FRAGMENT_TYPES,
        )
    except Exception:
        from kfxlib.kfx_container import (  # type: ignore[import-not-found]
            KfxContainer, CONTAINER_FRAGMENT_TYPES, RAW_FRAGMENT_TYPES,
        )
    _YJFrag = _yj_fragment
    IS = _IS
    IonStruct = _ion_struct

    _log = log_fn or (lambda msg: None)

    # --- estimate total resource size without full serialization -----------
    total_resource_bytes = 0
    for frag in book.fragments:
        if str(frag.ftype) in RAW_FRAGMENT_TYPES:
            val = frag.value
            if isinstance(val, (bytes, bytearray)):
                total_resource_bytes += len(val)

    if total_resource_bytes <= 14 * 1024 * 1024:  # 14 MB threshold (safe)
        # Small enough — single container
        single_data = book.convert_to_single_kfx()
        if not single_data:
            return []
        with open(out_path, "wb") as f:
            f.write(single_data)
        _log("KFX_OUT: single container (%d KB)" % (len(single_data) // 1024))
        return [out_path]

    _log("KFX_OUT: resources %.1f MB, splitting into multi-container"
         % (total_resource_bytes / 1048576))

    # --- separate fragments by category -----------------------------------
    meta_frags = {}   # ftype → fragment  ($270, $ion_symbol_table, $593, $419)
    structural_frags = []
    resource_groups = []
    current_chunk = []
    current_size = 0

    for frag in book.fragments:
        ft = str(frag.ftype)
        if ft in CONTAINER_FRAGMENT_TYPES:
            meta_frags[ft] = frag
        elif ft in RAW_FRAGMENT_TYPES:
            val = frag.value
            sz = len(val) if isinstance(val, (bytes, bytearray)) else 0
            if current_size + sz > _KFX_ATTACHABLE_CHUNK_SIZE and current_chunk:
                resource_groups.append(current_chunk)
                current_chunk = []
                current_size = 0
            current_chunk.append(frag)
            current_size += sz
        else:
            structural_frags.append(frag)

    if current_chunk:
        resource_groups.append(current_chunk)

    # --- extract shared metadata ------------------------------------------
    orig_270 = meta_frags.get("$270")
    orig_symtab = meta_frags.get("$ion_symbol_table")
    orig_593 = meta_frags.get("$593")
    orig_419 = meta_frags.get("$419")

    if not orig_270 or not orig_symtab or not orig_419:
        _log("KFX_OUT: missing required metadata fragments, falling back to single")
        single_data = book.convert_to_single_kfx()
        if not single_data:
            return []
        with open(out_path, "wb") as f:
            f.write(single_data)
        return [out_path]

    main_container_id = orig_270.value.get(IS("$409"), "")

    def _make_container_id(index):
        """Generate a CR!-prefixed container ID for resource chunk *index*."""
        h = hashlib.sha256(
            ("%s_res_%d" % (main_container_id, index)).encode()
        ).hexdigest()[:32].upper()
        return "CR!%s" % h

    def _collect_entity_ids(frags):
        """Collect entity IDs from fragments (same logic as rebuild_container_entity_map)."""
        ids = []
        for f in frags:
            ft = str(f.ftype)
            if ft not in CONTAINER_FRAGMENT_TYPES and str(f.fid) != ft:
                fid = f.fid
                if fid not in ids:
                    ids.append(fid)
        return ids

    # --- build main container's $419 referencing ALL containers -----------
    main_entity_ids = _collect_entity_ids(structural_frags)
    # $419 entities include themselves, so add structural + $419's own IDs
    # (rebuild_container_entity_map also includes $419 as entity)

    container_contents_list = [
        IonStruct(IS("$155"), main_container_id, IS("$181"), main_entity_ids),
    ]

    res_container_ids = []
    for i, chunk_frags in enumerate(resource_groups):
        res_cid = _make_container_id(i)
        res_container_ids.append(res_cid)
        res_entity_ids = _collect_entity_ids(chunk_frags)
        container_contents_list.append(
            IonStruct(IS("$155"), res_cid, IS("$181"), res_entity_ids),
        )

    # Preserve entity_dependencies ($253) from original $419
    new_419_value = IonStruct(IS("$252"), container_contents_list)
    old_deps = orig_419.value.get(IS("$253"), None)
    if old_deps is not None:
        new_419_value[IS("$253")] = old_deps

    new_main_419 = _YJFrag(ftype="$419", value=new_419_value)

    # --- assemble and serialize main container ----------------------------
    main_frag_list = [
        orig_symtab,
        orig_270,
    ]
    if orig_593:
        main_frag_list.append(orig_593)
    main_frag_list.append(new_main_419)
    main_frag_list.extend(structural_frags)

    main_container = KfxContainer(book.symtab, fragments=main_frag_list)
    main_data = main_container.serialize()

    # --- prepare output directory -----------------------------------------
    # Amazon on-device structure:
    #   <name>.kfx                           (main container)
    #   <name>.sdr/assets/attachables/       (resource containers as .kfx)
    out_files = []
    base, _ext = os.path.splitext(out_path)
    attach_dir = os.path.join(base + ".sdr", "assets", "attachables")
    os.makedirs(attach_dir, exist_ok=True)

    # Write main container
    with open(out_path, "wb") as f:
        f.write(main_data)
    out_files.append(out_path)
    _log("KFX_OUT: main container %d KB (%d structural frags)"
         % (len(main_data) // 1024, len(structural_frags)))

    # --- serialize and write each resource container ----------------------
    for i, chunk_frags in enumerate(resource_groups):
        res_cid = res_container_ids[i]
        res_entity_ids = _collect_entity_ids(chunk_frags)

        # Resource containers need $ion_symbol_table + $270, but NOT $419.
        # The main container's $419 references all containers.
        # Including $419 in resource containers causes duplicate fragment
        # errors when kfxlib reads the multi-container book back.
        res_270 = _YJFrag(ftype="$270", value=IonStruct(
            IS("$409"), res_cid,
            IS("$161"), "KFX attachable",
        ))
        symtab_copy = _YJFrag(
            ftype="$ion_symbol_table",
            value=copy.deepcopy(orig_symtab.value),
        )
        res_frag_list = [
            symtab_copy,
            res_270,
        ]
        res_frag_list.extend(chunk_frags)

        res_container = KfxContainer(book.symtab, fragments=res_frag_list)
        res_data = res_container.serialize()

        res_path = os.path.join(attach_dir, "%s.kfx" % res_cid)
        with open(res_path, "wb") as f:
            f.write(res_data)
        out_files.append(res_path)

    total_res_size = sum(
        os.path.getsize(p) for p in out_files[1:]
    )
    _log("KFX_OUT: %d resource containers in .sdr/assets/attachables/ "
         "(total %.1f MB, avg %.1f MB)"
         % (len(resource_groups),
            total_res_size / 1048576,
            total_res_size / max(1, len(resource_groups)) / 1048576))

    book.final_actions()
    return out_files


if __name__ == "__main__":
    kfxlib_path = str(os.environ.get("MAIC_KFXLIB_PATH", "") or "").strip()
    if kfxlib_path and kfxlib_path not in sys.path:
        sys.path.insert(0, kfxlib_path)

    try:
        from calibre_plugins.kfx_output.kfxlib import (
            set_logger, YJ_Book, YJ_Metadata, file_write_binary,
        )
        try:
            from calibre.utils.logging import Log
            log = Log()
        except Exception:
            log = _SimpleLog()
    except Exception:
        _install_kfxlib_calibre_shim()
        from kfxlib import set_logger, YJ_Book, YJ_Metadata, file_write_binary  # type: ignore[import-not-found]
        log = _SimpleLog()

    _init_kfxlib_types()
    set_logger(log)

    kfx_path = sys.argv[-1]
    cde_type = str(os.environ.get("MAIC_KFX_CDE_TYPE", "EBOK") or "EBOK").strip().upper()
    if cde_type not in {"EBOK", "PDOC"}:
        cde_type = "EBOK"

    enable_facing = _env_bool("MAIC_KFX_ENABLE_FACING", True)
    merge_adjacent_pairs = _env_bool("MAIC_KFX_MERGE_ADJACENT", True)

    book = YJ_Book(kfx_path)
    md = YJ_Metadata()
    md.cde_content_type = cde_type
    md.authors = None
    book.decode_book(set_metadata=md)

    postprocess_kfx_book(
        book,
        cde_type=cde_type,
        enable_facing=enable_facing,
        merge_adjacent_pairs=merge_adjacent_pairs,
    )

    kfx_data = book.convert_to_single_kfx()
    if kfx_data:
        file_write_binary(kfx_path, kfx_data)
        print("PATCHED_OK (single, %d bytes)" % len(kfx_data))
    else:
        print("PATCH_FAIL: serialize returned None")
        sys.exit(1)
