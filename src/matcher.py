"""
マッチング処理モジュール

JPEGファイルに対応するRAWファイルを検索してマッチングする機能を提供します。
ファイル名とExif撮影日時の両方を使用して正確なマッチングを行います。
"""

import logging
from pathlib import Path
from typing import List, Optional

from .exif_reader import ExifReader
from .file_scanner import FileScanner
from .indexer import RawFileIndex
from .models import JpegFileInfo, MatchResult, RawFileInfo


class Matcher:
    """JPEGファイルとRAWファイルをマッチングするクラス"""
    
    def __init__(self, exif_reader: ExifReader, index: RawFileIndex):
        """
        Matcherを初期化
        
        Args:
            exif_reader: Exif情報読み取りオブジェクト
            index: RAWファイルインデックス
        """
        self.exif_reader = exif_reader
        self.index = index
        self.file_scanner = FileScanner()
        self.logger = logging.getLogger(__name__)
    
    def find_matches(self, jpeg_files: List[Path]) -> List[MatchResult]:
        """
        JPEGファイルに対応するRAWファイルを検索
        
        Args:
            jpeg_files: マッチング対象のJPEGファイルパスのリスト
            
        Returns:
            マッチング結果のリスト
        """
        matches = []
        
        self.logger.info(f"マッチング開始: {len(jpeg_files)}個のJPEGファイル")
        
        for jpeg_path in jpeg_files:
            try:
                # JPEGファイル情報を作成
                jpeg_info = self._create_jpeg_info(jpeg_path)
                
                # マッチするRAWファイルを検索
                match_result = self._find_matching_raw(jpeg_info)
                
                if match_result:
                    matches.append(match_result)
                    self.logger.debug(f"マッチ発見: {jpeg_path.name} -> {match_result.raw_path.name} ({match_result.match_method})")
                else:
                    self.logger.debug(f"マッチなし: {jpeg_path.name}")
                    
            except Exception as e:
                self.logger.warning(f"JPEGファイル処理エラー: {jpeg_path} - {e}")
                continue
        
        self.logger.info(f"マッチング完了: {len(matches)}個のマッチを発見")
        return matches
    
    def _create_jpeg_info(self, jpeg_path: Path) -> JpegFileInfo:
        """
        JPEGファイルパスからJpegFileInfoオブジェクトを作成
        
        Args:
            jpeg_path: JPEGファイルパス
            
        Returns:
            JpegFileInfoオブジェクト
        """
        basename = self.file_scanner.get_basename(jpeg_path)
        
        # Exif撮影日時を読み取り
        capture_datetime = None
        try:
            capture_datetime = self.exif_reader.read_capture_datetime(jpeg_path)
        except Exception as e:
            self.logger.debug(f"JPEG Exif読み取りエラー（処理継続）: {jpeg_path} - {e}")
        
        return JpegFileInfo(
            path=jpeg_path,
            basename=basename,
            capture_datetime=capture_datetime
        )
    
    def _find_matching_raw(self, jpeg_info: JpegFileInfo) -> Optional[MatchResult]:
        """
        JPEGファイル情報に対応するRAWファイルを検索
        
        Args:
            jpeg_info: JPEGファイル情報
            
        Returns:
            マッチング結果（見つからない場合はNone）
        """
        # 1. ファイル名でフィルタリング（大文字小文字を区別しない比較）
        basename_matches = self.index.find_by_basename(jpeg_info.basename)
        
        if not basename_matches:
            self.logger.debug(f"ベース名マッチなし: {jpeg_info.basename}")
            return None
        
        self.logger.debug(f"ベース名マッチ: {jpeg_info.basename} -> {len(basename_matches)}個の候補")
        
        # 2. Exif日時で検証（完全一致のみ）
        if jpeg_info.capture_datetime:
            # JPEGに撮影日時がある場合は、日時マッチングを優先
            datetime_matches = []
            for raw_info in basename_matches:
                if raw_info.capture_datetime and raw_info.capture_datetime == jpeg_info.capture_datetime:
                    datetime_matches.append(raw_info)
            
            if datetime_matches:
                # 日時マッチがある場合は最初のものを選択
                selected_raw = datetime_matches[0]
                self.logger.debug(f"日時マッチ選択: {selected_raw.path.name}")
                
                if len(datetime_matches) > 1:
                    self.logger.warning(f"複数の日時マッチ: {jpeg_info.basename} - {len(datetime_matches)}個、最初のものを選択")
                
                return MatchResult(
                    jpeg_path=jpeg_info.path,
                    raw_path=selected_raw.path,
                    match_method='basename_and_datetime'
                )
            else:
                # 日時マッチがない場合の処理
                self.logger.debug(f"日時マッチなし: {jpeg_info.basename} (JPEG日時: {jpeg_info.capture_datetime})")
                
                # RAWファイルの日時情報をログ出力（デバッグ用）
                for raw_info in basename_matches:
                    self.logger.debug(f"  候補RAW: {raw_info.path.name} (日時: {raw_info.capture_datetime})")
                
                # 厳密マッチングのため、日時が一致しない場合はマッチなしとする
                return None
        
        # 3. JPEGに撮影日時がない場合の処理
        else:
            self.logger.debug(f"JPEG撮影日時なし: {jpeg_info.basename}")
            
            # ベース名のみでマッチング（複数候補がある場合は最初のものを選択）
            selected_raw = basename_matches[0]
            
            if len(basename_matches) > 1:
                self.logger.warning(f"複数のベース名マッチ: {jpeg_info.basename} - {len(basename_matches)}個、最初のものを選択")
            
            return MatchResult(
                jpeg_path=jpeg_info.path,
                raw_path=selected_raw.path,
                match_method='basename_only'
            )
    
    def get_match_statistics(self, matches: List[MatchResult]) -> dict:
        """
        マッチング統計情報を取得
        
        Args:
            matches: マッチング結果のリスト
            
        Returns:
            統計情報の辞書
        """
        basename_and_datetime_count = sum(1 for m in matches if m.match_method == 'basename_and_datetime')
        basename_only_count = sum(1 for m in matches if m.match_method == 'basename_only')
        
        return {
            'total_matches': len(matches),
            'basename_and_datetime_matches': basename_and_datetime_count,
            'basename_only_matches': basename_only_count
        }