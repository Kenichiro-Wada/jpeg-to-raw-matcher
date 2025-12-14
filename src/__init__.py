# RAW-JPEG Matcher Tool
# A Python tool to find and copy RAW files corresponding to JPEG files

from .models import RawFileInfo, JpegFileInfo, ProcessingStats
from .exceptions import (
    ProcessingError, ValidationError, FileOperationError, ExifReadError
)
from .path_validator import PathValidator
from .file_scanner import FileScanner
from .exif_reader import ExifReader
from .logger import ProgressLogger, LogConfig, create_default_logger, get_default_log_file
from .index_manager import IndexManager
from .match_manager import MatchManager

__all__ = [
    'RawFileInfo',
    'JpegFileInfo',
    'ProcessingStats',
    'ProcessingError',
    'ValidationError',
    'FileOperationError',
    'ExifReadError',
    'PathValidator',
    'FileScanner',
    'ExifReader',
    'ProgressLogger',
    'LogConfig',
    'create_default_logger',
    'get_default_log_file',
    'IndexManager',
    'MatchManager'
]