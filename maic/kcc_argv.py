"""KCC command line argument builder."""

from __future__ import annotations

from typing import Any


def build_kcc_argv(data: dict[str, Any]) -> list[str]:
    """Build argv for comic2ebook.main() from request parameters."""
    argv: list[str] = []

    if data.get("profile"):
        argv += ["-p", data["profile"]]

    fmt = data.get("format", "Auto")
    if fmt:
        argv += ["-f", fmt]

    if data.get("manga_mode"):
        argv.append("-m")
    if data.get("hq"):
        argv.append("-q")
    if data.get("autoscale"):
        argv.append("-2")
    if data.get("webtoon"):
        argv.append("-w")
    if data.get("upscale"):
        argv.append("-u")
    if data.get("stretch"):
        argv.append("-s")
    if data.get("no_processing"):
        argv.append("-n")

    splitter = data.get("splitter", 0)
    if splitter:
        argv += ["-r", str(splitter)]

    cropping = data.get("cropping")
    if cropping is not None:
        argv += ["-c", str(cropping)]

    cp = data.get("cropping_power")
    if cp and float(cp) != 1.0:
        argv += ["--cp", str(cp)]

    pm_h = data.get("preserve_margin_h", 0)
    pm_v = data.get("preserve_margin_v", 0)
    if pm_h and int(pm_h) > 0:
        argv += ["--preservemarginh", str(int(pm_h))]
    if pm_v and int(pm_v) > 0:
        argv += ["--preservemarginv", str(int(pm_v))]

    gamma = data.get("gamma", 0)
    if gamma and float(gamma) > 0.1:
        argv += ["-g", str(gamma)]

    if data.get("force_color"):
        argv.append("--forcecolor")
    if data.get("force_png"):
        argv.append("--forcepng")
    if data.get("mozjpeg"):
        argv.append("--mozjpeg")
    if data.get("erase_rainbow"):
        argv.append("--eraserainbow")
    if data.get("no_autocontrast"):
        argv.append("--noautocontrast")
    if data.get("color_autocontrast"):
        argv.append("--colorautocontrast")
    if data.get("autolevel"):
        argv.append("--autolevel")
    if data.get("no_rotate"):
        argv.append("--norotate")
    if data.get("rotate_first"):
        argv.append("--rotatefirst")
    if data.get("spread_shift"):
        argv.append("--spreadshift")
    if data.get("file_fusion"):
        argv.append("--filefusion")
    if data.get("delete_input"):
        argv.append("-d")

    borders = data.get("borders_color", "none")
    if borders == "white":
        argv.append("--whiteborders")
    elif borders == "black":
        argv.append("--blackborders")

    ipc = data.get("inter_panel_crop", 0)
    if ipc:
        argv += ["--ipc", str(ipc)]

    bs = data.get("batch_split", 0)
    if bs:
        argv += ["-b", str(bs)]

    title = data.get("title", "")
    if title:
        argv += ["-t", title]

    author = data.get("author", "")
    if author:
        argv += ["-a", author]

    mt = data.get("metadata_title", 0)
    if mt:
        argv += ["--metadatatitle", str(mt)]

    output_dir = data.get("output_dir", "")
    if output_dir:
        argv += ["-o", output_dir]

    cw = data.get("custom_width", 0)
    if cw and int(cw) > 0:
        argv += ["--customwidth", str(int(cw))]
    ch = data.get("custom_height", 0)
    if ch and int(ch) > 0:
        argv += ["--customheight", str(int(ch))]

    jq = data.get("jpeg_quality", 0)
    if jq and int(jq) > 0:
        argv += ["--jpeg-quality", str(int(jq))]

    cs = data.get("chunk_size", 0)
    if cs and int(cs) > 0:
        argv += ["--targetsize", str(int(cs))]
    if data.get("pdf_legacy"):
        argv.append("--pdfextract")

    return argv
