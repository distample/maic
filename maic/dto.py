"""Typed DTO declarations for validated API payloads."""

from __future__ import annotations

from typing import Any, Literal, NotRequired, TypedDict


class BatchFileRef(TypedDict):
    path: str
    name: NotRequired[str]
    relPath: NotRequired[str]
    folder: NotRequired[str]


class BatchDetectPayload(TypedDict, total=False):
    files: list[BatchFileRef]
    confidence: Any


class BatchCleanPayload(TypedDict, total=False):
    method: str
    padding: Any
    output_dir: str
    root_dir: str
    has_subfolders: bool
    all_files: list[BatchFileRef]


class TocScrapePayload(TypedDict, total=False):
    url: str
    source: str


class ComicInfoWritePayload(TypedDict, total=False):
    source: str
    fields: dict[str, Any]
    bookmarks: list[dict[str, Any]]


CropSidecarSavePayload = TypedDict(
    "CropSidecarSavePayload",
    {
        "source": str,
        "no-crop": list[str],
        "custom-crop": dict[str, dict[str, Any]],
        "custom-split": dict[str, dict[str, Any]],
        "excluded": list[str],
        "bookmarks": list[dict[str, Any]] | None,
        "extra-margin": dict[str, dict[str, Any]] | None,
        "edit-ops": dict[str, list[dict[str, Any]]] | None,
        "watermark-matches": list[str] | None,
    },
    total=False,
)


class PresetsSavePayload(TypedDict, total=False):
    name: str
    data: dict[str, Any]


class DetectPathPayload(TypedDict, total=False):
    path: str
    confidence: Any


class FileMtimesPayload(TypedDict, total=False):
    paths: list[str]


class BrowseSourcePayload(TypedDict, total=False):
    type: Literal["folder", "file"]
    extensions: str
    multiple: bool


class ScanFolderPayload(TypedDict, total=False):
    path: str


class ConvertLogModePayload(TypedDict, total=False):
    advanced: bool


class ConvertCrop(TypedDict, total=False):
    top: float | int
    bottom: float | int
    left: float | int
    right: float | int
    width: float | int
    height: float | int


class ConvertSplit(TypedDict, total=False):
    split: float | int
    width: float | int
    height: float | int
    axis: str


ConvertPerSource = TypedDict(
    "ConvertPerSource",
    {
        "no-crop": list[str],
        "custom-crop": dict[str, ConvertCrop],
        "custom-split": dict[str, ConvertSplit],
    },
    total=False,
)


class ConvertStartPayload(TypedDict, total=False):
    sources: list[str]
    per_source_crop: dict[str, ConvertPerSource]
    excluded_files: list[str]
    bookmarks: dict[str, str]
    maic_crop: bool
    maic_margin_pct: float
    maic_watermarks: bool
    maic_page_numbers: bool
    cleanup_method: str
    cleanup_padding: int
    manga_upscale: int
    scan_cleanup: bool
    facing_pages: bool
    force_spread_preview: bool
    spread_preview_mode: int
    auto_balance_margins: bool
    auto_balance_margin_px: int
    auto_balance_margin_unit: str
    auto_balance_margin_pct: float
    kindle_doc_type: str
