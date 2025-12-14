"""
Exif情報読み取りモジュール

JPEGファイルとRAWファイルからExif情報（特に撮影日時）を読み取る機能を提供します。
ExifToolを外部コマンドとして実行してExif情報を取得します。
読み取り結果はキャッシュされ、同じファイルの重複読み取りを避けます。
"""

import json
import logging
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from .exceptions import ExifReadError


class ExifReader:
    """ExifTool を使用したExif情報読み取りクラス（キャッシュ機能付き）"""
    
    def __init__(self):
        """ExifReaderを初期化"""
        self.cache: Dict[Path, Optional[datetime]] = {}
        self.logger = logging.getLogger(__name__)
        self.exiftool_path: Optional[Path] = None
        
        # 撮影日時を表すExifタグの優先順位リスト（ExifTool形式）
        self._datetime_tags = [
            'DateTimeOriginal',    # 撮影日時（最優先）
            'CreateDate',          # 作成日時
            'ModifyDate',          # 更新日時
            'DateTime',            # 一般的な日時
        ]
        
        # ExifToolの初期化チェック
        self._check_exiftool_availability()
    
    def _check_exiftool_availability(self) -> None:
        """ExifToolが利用可能かチェックし、パスを設定"""
        try:
            self.exiftool_path = self._find_exiftool()
            # ExifToolのバージョンを確認
            result = subprocess.run(
                [str(self.exiftool_path), '-ver'],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                version = result.stdout.strip()
                self.logger.info(f"ExifTool が見つかりました: {self.exiftool_path} (バージョン: {version})")
            else:
                raise ExifReadError("ExifTool の実行に失敗しました")
                
        except Exception as e:
            error_msg = (
                "ExifTool が見つかりません。以下の方法でインストールしてください:\n"
                "Windows: https://exiftool.org/ からダウンロードしてPATHに追加\n"
                "macOS: brew install exiftool\n"
                "Linux: sudo apt-get install libimage-exiftool-perl (Ubuntu/Debian)"
            )
            self.logger.error(error_msg)
            raise ExifReadError(error_msg) from e
    
    def _find_exiftool(self) -> Path:
        """ExifToolの実行可能ファイルを検索"""
        # システムPATHから検索
        exiftool_name = 'exiftool.exe' if sys.platform == 'win32' else 'exiftool'
        exiftool_path = shutil.which(exiftool_name)
        
        if exiftool_path:
            return Path(exiftool_path)
        
        # 一般的なインストール場所を検索
        common_paths = []
        if sys.platform == 'win32':
            common_paths = [
                Path('C:/Windows/exiftool.exe'),
                Path('C:/Program Files/exiftool/exiftool.exe'),
                Path('C:/Program Files (x86)/exiftool/exiftool.exe'),
            ]
        else:
            common_paths = [
                Path('/usr/local/bin/exiftool'),
                Path('/usr/bin/exiftool'),
                Path('/opt/homebrew/bin/exiftool'),  # Apple Silicon Mac
            ]
        
        for path in common_paths:
            if path.exists() and path.is_file():
                return path
        
        raise FileNotFoundError("ExifTool が見つかりません")
    
    def check_exiftool_availability(self) -> bool:
        """ExifToolが利用可能かチェック（外部から呼び出し可能）"""
        try:
            self._check_exiftool_availability()
            return True
        except ExifReadError:
            return False
    
    def read_capture_datetime(self, file_path: Path) -> Optional[datetime]:
        """
        ファイルから撮影日時を読み取る（キャッシュ付き）
        
        Args:
            file_path: 読み取り対象のファイルパス
            
        Returns:
            撮影日時（取得できない場合はNone）
            
        Raises:
            ExifReadError: Exif読み取りでエラーが発生した場合
        """
        # キャッシュから確認
        if file_path in self.cache:
            self.logger.debug(f"キャッシュから撮影日時を取得: {file_path}")
            return self.cache[file_path]
        
        try:
            # ファイルの存在確認
            if not file_path.exists():
                self.logger.warning(f"ファイルが存在しません: {file_path}")
                self.cache[file_path] = None
                return None
            
            # ファイルサイズチェック（0バイトファイルを除外）
            if file_path.stat().st_size == 0:
                self.logger.warning(f"ファイルサイズが0バイトです: {file_path}")
                self.cache[file_path] = None
                return None
            
            # ExifToolを使用してExif情報を読み取り
            capture_datetime = self._extract_datetime_with_exiftool(file_path)
            
            # キャッシュに保存
            self.cache[file_path] = capture_datetime
            
            if capture_datetime:
                self.logger.debug(f"撮影日時を取得: {file_path} -> {capture_datetime}")
            else:
                self.logger.debug(f"撮影日時が見つかりません: {file_path}")
            
            return capture_datetime
            
        except Exception as e:
            error_msg = f"Exif読み取りエラー: {file_path} - {str(e)}"
            self.logger.error(error_msg)
            # エラーの場合もキャッシュしてNoneを返す（再試行を避ける）
            self.cache[file_path] = None
            raise ExifReadError(error_msg) from e
    
    def _extract_datetime_with_exiftool(self, file_path: Path) -> Optional[datetime]:
        """
        ExifToolを使用してファイルからExif日時情報を抽出
        
        Args:
            file_path: 読み取り対象のファイルパス
            
        Returns:
            撮影日時（取得できない場合はNone）
        """
        try:
            # ExifToolを実行してJSON形式でExif情報を取得
            exif_data = self._run_exiftool(file_path, self._datetime_tags)
            
            # 優先順位に従って撮影日時を検索
            for tag_name in self._datetime_tags:
                if tag_name in exif_data:
                    tag_value = exif_data[tag_name]
                    datetime_obj = self._parse_exif_datetime(tag_value)
                    if datetime_obj:
                        self.logger.debug(f"ExifTool: 撮影日時タグ '{tag_name}' から取得: {datetime_obj}")
                        return datetime_obj
            
            self.logger.debug(f"ExifToolで撮影日時が見つかりません: {file_path}")
            return None
            
        except Exception as e:
            self.logger.debug(f"ExifTool実行中にエラー: {file_path} - {str(e)}")
            return None
    
    def _run_exiftool(self, file_path: Path, tags: List[str]) -> Dict[str, str]:
        """
        ExifToolを実行してExif情報を取得
        
        Args:
            file_path: 読み取り対象のファイルパス
            tags: 取得するExifタグのリスト
            
        Returns:
            Exif情報の辞書
            
        Raises:
            ExifReadError: ExifTool実行でエラーが発生した場合
        """
        if not self.exiftool_path:
            raise ExifReadError("ExifTool が初期化されていません")
        
        try:
            # ExifToolコマンドを構築
            cmd = [str(self.exiftool_path), '-j']  # JSON出力
            
            # 指定されたタグを追加
            for tag in tags:
                cmd.extend(['-' + tag])
            
            cmd.append(str(file_path))
            
            # ExifToolを実行
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,  # 30秒でタイムアウト
                encoding='utf-8'
            )
            
            if result.returncode != 0:
                error_msg = f"ExifTool実行エラー (終了コード: {result.returncode}): {result.stderr}"
                raise ExifReadError(error_msg)
            
            # JSON出力を解析
            try:
                json_data = json.loads(result.stdout)
                if json_data and len(json_data) > 0:
                    return json_data[0]  # 最初のファイルの情報を返す
                else:
                    return {}
            except json.JSONDecodeError as e:
                raise ExifReadError(f"ExifTool JSON出力の解析エラー: {str(e)}")
                
        except subprocess.TimeoutExpired:
            raise ExifReadError(f"ExifTool実行がタイムアウトしました: {file_path}")
        except Exception as e:
            raise ExifReadError(f"ExifTool実行中に予期しないエラー: {str(e)}") from e
    
    def _parse_exif_datetime(self, datetime_str: str) -> Optional[datetime]:
        """
        Exif日時文字列をdatetimeオブジェクトに変換
        
        Args:
            datetime_str: Exif日時文字列（例: "2023:12:25 14:30:45" または "2023-12-25T14:30:45"）
            
        Returns:
            datetimeオブジェクト（解析できない場合はNone）
        """
        if not datetime_str or datetime_str.strip() == '':
            return None
        
        # ExifToolの出力形式に対応した複数のフォーマットを試行
        formats = [
            '%Y:%m:%d %H:%M:%S',      # 標準Exifフォーマット
            '%Y-%m-%d %H:%M:%S',      # ISO形式（スペース区切り）
            '%Y-%m-%dT%H:%M:%S',      # ISO形式（T区切り）
            '%Y-%m-%dT%H:%M:%SZ',     # ISO形式（UTC）
            '%Y-%m-%dT%H:%M:%S%z',    # ISO形式（タイムゾーン付き）
            '%Y/%m/%d %H:%M:%S',      # スラッシュ区切り
            '%Y.%m.%d %H:%M:%S',      # ドット区切り
        ]
        
        # タイムゾーン情報を除去（簡単な処理）
        clean_datetime_str = datetime_str.split('+')[0].split('-')[0] if 'T' in datetime_str else datetime_str
        
        for fmt in formats:
            try:
                return datetime.strptime(clean_datetime_str, fmt)
            except ValueError:
                continue
        
        # Exif標準フォーマットの特別処理
        try:
            # コロン区切りの日付をハイフン区切りに変換
            if ':' in datetime_str and len(datetime_str.split(':')) >= 3:
                parts = datetime_str.split(' ')
                if len(parts) == 2:
                    date_part = parts[0].replace(':', '-')
                    time_part = parts[1]
                    normalized_str = f"{date_part} {time_part}"
                    return datetime.strptime(normalized_str, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            pass
        
        self.logger.debug(f"日時文字列の解析に失敗: '{datetime_str}'")
        return None
    
    def clear_cache(self) -> None:
        """キャッシュをクリア"""
        self.cache.clear()
        self.logger.debug("Exifキャッシュをクリアしました")
    
    def get_cache_size(self) -> int:
        """キャッシュサイズを取得"""
        return len(self.cache)
    
    def is_cached(self, file_path: Path) -> bool:
        """ファイルがキャッシュされているかチェック"""
        return file_path in self.cache