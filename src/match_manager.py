"""
マッチング管理モジュール

JPEGファイルに対応するRAWファイルの検索とコピー処理を管理します。
全インデックスからの検索、フィルタリング、マッチング、コピーの統合的な処理を提供します。
"""

import time
from pathlib import Path
from typing import List, Optional

from .copier import Copier
from .exif_reader import ExifReader
from .file_scanner import FileScanner
from .indexer import IndexCache, RawFileIndex
from .logger import create_default_logger, get_default_log_file
from .matcher import Matcher
from .models import ProcessingStats



class MatchManager:
    """マッチング処理を担当するクラス"""
    
    def __init__(self):
        """MatchManagerを初期化"""
        self.cache = IndexCache()
        self.exif_reader = ExifReader()
        self.file_scanner = FileScanner()
        self.copier = Copier()
        self.progress_logger = None
    
    def find_and_copy_matches(self, target_dir: Path, recursive: bool,
                              source_filter: Optional[str], verbose: bool) -> None:
        """
        JPEGファイルに対応するRAWファイルを検索してコピー
        
        Args:
            target_dir: JPEGファイルのターゲットディレクトリ
            recursive: サブディレクトリも検索する場合True
            source_filter: 特定のソースディレクトリのRAWファイルのみを対象にする
            verbose: 詳細ログを表示する場合True
        """
        # プログレスロガーを初期化
        log_file = get_default_log_file() if verbose else None
        self.progress_logger = create_default_logger(verbose=verbose, log_file=log_file)
        
        # 処理開始のログ
        source_dirs = self._get_source_directories(source_filter)
        self.progress_logger.log_processing_start(source_dirs, target_dir)
        
        try:
            # 1. 全インデックスの読み込み
            global_index = self._load_global_index(source_filter)
            
            # 2. インデックス存在チェックと警告表示
            if not self._check_index_availability(source_filter):
                return
            
            # 3. JPEGファイルのスキャン
            self.progress_logger.log_info(f"JPEGファイルをスキャン中: {target_dir}")
            jpeg_files = self.file_scanner.scan_jpeg_files(target_dir, recursive)
            
            if not jpeg_files:
                self.progress_logger.log_info("JPEGファイルが見つかりませんでした。")
                return
            
            self.progress_logger.log_info(f"JPEGファイル発見: {len(jpeg_files)}個")
            
            # 4. マッチング処理
            self.progress_logger.log_matching_start(target_dir, recursive)
            start_time = time.time()
            
            matcher = Matcher(self.exif_reader, global_index)
            matches = []
            
            # 進捗表示付きでマッチング処理
            for i, jpeg_file in enumerate(jpeg_files):
                if verbose:
                    self.progress_logger.log_matching_progress(
                        len(jpeg_files), i, len(matches), jpeg_file
                    )
                
                file_matches = matcher.find_matches([jpeg_file])
                matches.extend(file_matches)
            
            # マッチング完了
            matching_time = time.time() - start_time
            self.progress_logger.log_matching_complete(len(matches), matching_time)
            
            if not matches:
                self.progress_logger.log_info("マッチするRAWファイルが見つかりませんでした。")
                return
            
            # マッチング統計を表示
            if verbose:
                stats = matcher.get_match_statistics(matches)
                basename_datetime = stats['basename_and_datetime_matches']
                basename_only = stats['basename_only_matches']
                self.progress_logger.log_info(f"  ファイル名+日時マッチ: {basename_datetime}個")
                self.progress_logger.log_info(f"  ファイル名のみマッチ: {basename_only}個")
            
            # 5. コピー処理
            self.progress_logger.log_copy_start(len(matches))
            start_time = time.time()
            
            copy_result = self.copier.copy_files(matches, target_dir, self.progress_logger)
            
            copy_time = time.time() - start_time
            self.progress_logger.log_copy_complete(copy_result, copy_time)
            
            # 6. 結果レポート
            stats = ProcessingStats(
                raw_files_found=global_index.file_count,
                jpeg_files_found=len(jpeg_files),
                matches_found=len(matches),
                files_copied=copy_result.success,
                files_skipped=copy_result.skipped,
                files_failed=copy_result.failed,
                errors=copy_result.errors
            )
            
            self.progress_logger.log_processing_complete(stats)
            
        except Exception as e:
            error_msg = f"マッチング処理エラー: {e}"
            if self.progress_logger:
                self.progress_logger.log_error(target_dir, error_msg, e)
            else:
                print(f"エラー: {error_msg}")
            raise
    
    def _get_source_directories(self, source_filter: Optional[str]) -> List[Path]:
        """
        ソースディレクトリのリストを取得
        
        Args:
            source_filter: 特定のソースディレクトリフィルター
            
        Returns:
            ソースディレクトリのリスト
        """
        directories = self.cache.list_indexed_directories()
        source_dirs = []
        
        for source_dir, _, _ in directories:
            if source_filter and str(source_dir) != source_filter:
                continue
            source_dirs.append(source_dir)
        
        return source_dirs
    
    def _load_global_index(self, source_filter: Optional[str]) -> RawFileIndex:
        """
        全インデックスを読み込み、統合されたインデックスを作成
        
        Args:
            source_filter: 特定のソースディレクトリフィルター
            
        Returns:
            統合されたRAWファイルインデックス
        """
        global_index = RawFileIndex()
        
        # 全ディレクトリのインデックスを読み込み
        directories = self.cache.list_indexed_directories()
        
        for source_dir, _, _ in directories:
            # ソースフィルターが指定されている場合はチェック
            if source_filter and str(source_dir) != source_filter:
                continue
            
            # ディレクトリのインデックスを読み込み
            dir_index = self.cache.load_directory_index(source_dir)
            if dir_index:
                # グローバルインデックスに統合
                for raw_info in dir_index.get_all_files():
                    global_index.add(raw_info)
                
                if self.progress_logger:
                    self.progress_logger.log_debug(f"インデックス読み込み: {source_dir} ({dir_index.file_count}ファイル)")
        
        if self.progress_logger:
            self.progress_logger.log_info(f"グローバルインデックス作成完了: {global_index.file_count}ファイル")
        return global_index
    
    def _check_index_availability(self, source_filter: Optional[str]) -> bool:
        """
        インデックスの利用可能性をチェックし、必要に応じて警告を表示
        
        Args:
            source_filter: 特定のソースディレクトリフィルター
            
        Returns:
            インデックスが利用可能な場合True
        """
        directories = self.cache.list_indexed_directories()
        
        if not directories:
            self._display_index_warning([])
            return False
        
        # ソースフィルターが指定されている場合
        if source_filter:
            filter_path = Path(source_filter)
            matching_dirs = [d for d, _, _ in directories if d == filter_path]
            
            if not matching_dirs:
                self._display_index_warning([filter_path])
                return False
        
        return True
    
    def _display_index_warning(self, missing_directories: List[Path]) -> None:
        """
        インデックス不足の警告メッセージを表示
        
        Args:
            missing_directories: 不足しているディレクトリのリスト
        """
        if self.progress_logger:
            self.progress_logger.log_warning("RAWファイルのインデックスが見つかりません")
            self.progress_logger.log_info("")
            
            if missing_directories:
                self.progress_logger.log_info("以下のディレクトリのインデックスが必要です:")
                for directory in missing_directories:
                    self.progress_logger.log_info(f"  - {directory}")
            else:
                self.progress_logger.log_info("インデックス化されたディレクトリがありません。")
            
            self.progress_logger.log_info("")
            self.progress_logger.log_info("インデックスを作成するには以下のコマンドを実行してください:")
            
            if missing_directories:
                for directory in missing_directories:
                    self.progress_logger.log_info(f"  raw-jpeg-matcher index '{directory}'")
            else:
                self.progress_logger.log_info("  raw-jpeg-matcher index <RAWファイルのディレクトリ>")
            
            self.progress_logger.log_info("")
            self.progress_logger.log_info("既存のインデックスを確認するには:")
            self.progress_logger.log_info("  raw-jpeg-matcher list-index")
        else:
            print("⚠️  警告: RAWファイルのインデックスが見つかりません")
            print()
            
            if missing_directories:
                print("以下のディレクトリのインデックスが必要です:")
                for directory in missing_directories:
                    print(f"  - {directory}")
            else:
                print("インデックス化されたディレクトリがありません。")
            
            print()
            print("インデックスを作成するには以下のコマンドを実行してください:")
            
            if missing_directories:
                for directory in missing_directories:
                    print(f"  raw-jpeg-matcher index '{directory}'")
            else:
                print("  raw-jpeg-matcher index <RAWファイルのディレクトリ>")
            
            print()
            print("既存のインデックスを確認するには:")
            print("  raw-jpeg-matcher list-index")
    
