"""Typed state declarations used by runtime globals."""

from __future__ import annotations

from typing import Any, TypedDict


class AppState(TypedDict):
    yolo_model: Any
    lama_model: Any
    device: str
    model_path: str
    training: bool
    training_progress: int
    training_log: list[str]
    training_epochs_total: int
    training_epoch_current: int
    converting: bool
    convert_stop_requested: bool
    convert_progress: int
    convert_log: list[str]
    convert_phase: str
    convert_current_file: str
    convert_total: int
    convert_done: int
    convert_output_files: list[str]
    convert_advanced_log: bool
    default_convert_output_dir: str
    default_clean_output_dir: str
    allowed_read_roots: list[str]
    allowed_write_roots: list[str]
    cpu_name: str
    cuda_available: bool
    gpu_name: str


class BatchState(TypedDict):
    running: bool
    stop_requested: bool
    phase: str
    current: int
    total: int
    currentFile: str
    log: list[str]
    detections: dict[str, dict[str, Any]]
    user_masks: dict[str, bytes]
    user_edits: set[str]
    corrections_dir: str
    corrections_count: int
