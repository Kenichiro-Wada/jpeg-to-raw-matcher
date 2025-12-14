"""
データモデル定義

RAW-JPEG Matcher Toolで使用するデータクラスを定義します。
"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple


@dataclass
class RawFileInfo:
    """RAWファイルの情報"""
    path: Path
    basename: str  # 拡張子を除いたファイル名（小文字）
    capture_datetime: Optional[datetime]
    file_size: int


@dataclass
class JpegFileInfo:
    """JPEGファイルの情報"""
    path: Path
    basename: str  # 拡張子を除いたファイル名（小文字）
    capture_datetime: Optional[datetime]


@dataclass
class MatchResult:
    """マッチング結果"""
    jpeg_path: Path
    raw_path: Path
    match_method: str  # 'basename_and_datetime' or 'basename_only'


@dataclass
class CopyResult:
    """コピー結果"""
    success: int
    skipped: int
    failed: int
    errors: List[Tuple[Path, str]]


@dataclass
class ProcessingStats:
    """処理統計情報"""
    raw_files_found: int
    jpeg_files_found: int
    matches_found: int
    files_copied: int
    files_skipped: int
    files_failed: int
    errors: List[Tuple[str, str]]  # (file_path, error_message)