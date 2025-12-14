"""
ファイルスキャナー

ディレクトリをスキャンしてRAWファイルとJPEGファイルを検索する機能を提供します。
"""

from pathlib import Path
from typing import List, Set

from .exceptions import ValidationError
from .path_validator import PathValidator


class FileScanner:
    """ディレクトリをスキャンしてファイルを検索するクラス"""
    
    # RAWファイル拡張子（大文字小文字両方）
    RAW_EXTENSIONS: Set[str] = {
        '.cr2', '.CR2',    # Canon
        '.cr3', '.CR3',    # Canon
        '.nef', '.NEF',    # Nikon
        '.arw', '.ARW',    # Sony
        '.raf', '.RAF',    # Fujifilm
        '.orf', '.ORF',    # Olympus
        '.rw2', '.RW2',    # Panasonic
        '.pef', '.PEF',    # Pentax
        '.dng', '.DNG',    # Adobe/Leica
        '.rwl', '.RWL',    # Leica
        '.3fr', '.3FR',    # Hasselblad
        '.iiq', '.IIQ',    # Phase One
    }
    
    # JPEG拡張子（大文字小文字両方）
    JPEG_EXTENSIONS: Set[str] = {
        '.jpg', '.JPG',
        '.jpeg', '.JPEG'
    }
    
    def __init__(self):
        """FileScannerを初期化"""
        pass
    
    def scan_raw_files(self, directory: Path, recursive: bool = True) -> List[Path]:
        """
        ディレクトリをスキャンしてRAWファイルを検索
        
        Args:
            directory: スキャンするディレクトリ
            recursive: サブディレクトリも検索する場合True
            
        Returns:
            見つかったRAWファイルのパスのリスト
            
        Raises:
            ValidationError: ディレクトリが無効な場合
        """
        # ディレクトリの検証
        PathValidator.validate_directory(directory)
        
        raw_files = []
        
        if recursive:
            # 再帰的にスキャン
            for file_path in directory.rglob('*'):
                if file_path.is_file() and file_path.suffix in self.RAW_EXTENSIONS:
                    raw_files.append(file_path)
        else:
            # 指定ディレクトリのみスキャン
            for file_path in directory.iterdir():
                if file_path.is_file() and file_path.suffix in self.RAW_EXTENSIONS:
                    raw_files.append(file_path)
        
        return sorted(raw_files)
    
    def scan_jpeg_files(self, directory: Path, recursive: bool = True) -> List[Path]:
        """
        ディレクトリをスキャンしてJPEGファイルを検索
        
        Args:
            directory: スキャンするディレクトリ
            recursive: サブディレクトリも検索する場合True
            
        Returns:
            見つかったJPEGファイルのパスのリスト
            
        Raises:
            ValidationError: ディレクトリが無効な場合
        """
        # ディレクトリの検証
        PathValidator.validate_directory(directory)
        
        jpeg_files = []
        
        if recursive:
            # 再帰的にスキャン
            for file_path in directory.rglob('*'):
                if file_path.is_file() and file_path.suffix in self.JPEG_EXTENSIONS:
                    jpeg_files.append(file_path)
        else:
            # 指定ディレクトリのみスキャン
            for file_path in directory.iterdir():
                if file_path.is_file() and file_path.suffix in self.JPEG_EXTENSIONS:
                    jpeg_files.append(file_path)
        
        return sorted(jpeg_files)
    
    def get_basename(self, file_path: Path) -> str:
        """
        ファイルパスからベース名（拡張子を除いた小文字のファイル名）を取得
        
        Args:
            file_path: ファイルパス
            
        Returns:
            ベース名（小文字）
        """
        return file_path.stem.lower()
    
    def is_raw_file(self, file_path: Path) -> bool:
        """
        ファイルがRAWファイルかどうかを判定
        
        Args:
            file_path: ファイルパス
            
        Returns:
            RAWファイルの場合True
        """
        return file_path.suffix in self.RAW_EXTENSIONS
    
    def is_jpeg_file(self, file_path: Path) -> bool:
        """
        ファイルがJPEGファイルかどうかを判定
        
        Args:
            file_path: ファイルパス
            
        Returns:
            JPEGファイルの場合True
        """
        return file_path.suffix in self.JPEG_EXTENSIONS