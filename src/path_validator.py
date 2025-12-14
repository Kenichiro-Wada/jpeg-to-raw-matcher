"""
パス検証ユーティリティ

ディレクトリパスの検証とクロスプラットフォーム対応を提供します。
"""

import os
import shutil
from pathlib import Path
from typing import Optional

from .exceptions import ValidationError


class PathValidator:
    """パス検証を行うユーティリティクラス"""
    
    @staticmethod
    def validate_directory(path: Path) -> None:
        """
        ディレクトリの存在とアクセス権を検証
        
        Args:
            path: 検証するディレクトリパス
            
        Raises:
            ValidationError: ディレクトリが存在しない、アクセス不可能、
                           またはディレクトリではない場合
        """
        if not path.exists():
            raise ValidationError(f"ディレクトリが存在しません: {path}")
        
        if not path.is_dir():
            raise ValidationError(f"指定されたパスはディレクトリではありません: {path}")
        
        # 読み取り権限の確認
        if not os.access(path, os.R_OK):
            raise ValidationError(f"ディレクトリに読み取り権限がありません: {path}")
    
    @staticmethod
    def validate_writable_directory(path: Path) -> None:
        """
        書き込み可能なディレクトリかどうかを検証
        
        Args:
            path: 検証するディレクトリパス
            
        Raises:
            ValidationError: ディレクトリが存在しない、アクセス不可能、
                           または書き込み権限がない場合
        """
        # まず基本的な検証を実行
        PathValidator.validate_directory(path)
        
        # 書き込み権限の確認
        if not os.access(path, os.W_OK):
            raise ValidationError(f"ディレクトリに書き込み権限がありません: {path}")
    
    @staticmethod
    def normalize_path(path_str: str) -> Path:
        """
        パス文字列を正規化してPathオブジェクトに変換
        macOSとWindowsの両方のパス形式をサポート
        
        Args:
            path_str: パス文字列
            
        Returns:
            正規化されたPathオブジェクト
        """
        # パス文字列をPathオブジェクトに変換（自動的にOS固有の形式に正規化される）
        path = Path(path_str).expanduser().resolve()
        return path
    
    @staticmethod
    def check_disk_space(path: Path, required_bytes: int) -> bool:
        """
        ディスクの空き容量を確認
        
        Args:
            path: 確認するディレクトリパス
            required_bytes: 必要な容量（バイト）
            
        Returns:
            十分な空き容量がある場合True
        """
        try:
            # ディスクの使用量情報を取得
            total, used, free = shutil.disk_usage(path)
            return free >= required_bytes
        except (OSError, ValueError):
            # エラーが発生した場合は安全側に倒してFalseを返す
            return False
    
    @staticmethod
    def get_disk_usage_info(path: Path) -> Optional[tuple[int, int, int]]:
        """
        ディスクの使用量情報を取得
        
        Args:
            path: 確認するディレクトリパス
            
        Returns:
            (total, used, free) のタプル（バイト単位）、
            エラーの場合はNone
        """
        try:
            return shutil.disk_usage(path)
        except (OSError, ValueError):
            return None