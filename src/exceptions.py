"""
カスタム例外クラス定義

RAW-JPEG Matcher Toolで使用する例外クラスを定義します。
"""


class ProcessingError(Exception):
    """処理エラーの基底クラス"""
    pass


class ValidationError(ProcessingError):
    """検証エラー"""
    pass


class FileOperationError(ProcessingError):
    """ファイル操作エラー"""
    pass


class ExifReadError(ProcessingError):
    """Exif読取エラー"""
    pass