"""
インデックス管理モジュール

RAWファイルのインデックス作成と管理を担当します。
複数ディレクトリのインデックス管理、差分更新、一覧表示機能を提供します。
"""

import time
from pathlib import Path
from typing import Optional

from .exif_reader import ExifReader
from .file_scanner import FileScanner
from .indexer import IndexCache, Indexer
from .logger import create_default_logger, get_default_log_file


class IndexManager:
    """インデックス作成と管理を担当するクラス"""
    
    def __init__(self):
        """IndexManagerを初期化"""
        self.cache = IndexCache()
        self.exif_reader = ExifReader()
        self.file_scanner = FileScanner()
        self.indexer = Indexer(self.exif_reader, self.file_scanner)
        self.progress_logger = None
    
    def build_or_update_index(self, source_dir: Path, recursive: bool, force_rebuild: bool, verbose: bool) -> None:
        """
        インデックスを作成または更新
        
        Args:
            source_dir: ソースディレクトリパス
            recursive: サブディレクトリも検索する場合True
            force_rebuild: 強制的に再構築する場合True
            verbose: 詳細ログを表示する場合True
        """
        # プログレスロガーを初期化
        log_file = get_default_log_file() if verbose else None
        self.progress_logger = create_default_logger(verbose=verbose, log_file=log_file)
        
        # 処理開始のログ
        self.progress_logger.log_processing_start([source_dir])
        
        try:
            # インデックス構築開始のログ
            self.progress_logger.log_index_start(source_dir, recursive)
            start_time = time.time()
            
            # 1. 既存インデックスの確認
            existing_index = None if force_rebuild else self.cache.load_directory_index(source_dir)
            
            if existing_index and not force_rebuild:
                self.progress_logger.log_info(f"既存インデックスを発見: {existing_index.file_count}ファイル")
                action = "差分更新"
            else:
                if force_rebuild:
                    self.progress_logger.log_info("強制再構築モードでインデックスを作成")
                    action = "強制再構築"
                else:
                    self.progress_logger.log_info("新規インデックスを作成")
                    action = "新規作成"
            
            # 2. インデックスの構築または更新
            updated_index = self.indexer.build_index(source_dir, recursive, force_rebuild, self.progress_logger)
            
            # 処理時間を計算
            processing_time = time.time() - start_time
            
            # インデックス構築完了のログ
            self.progress_logger.log_index_complete(updated_index.file_count, processing_time)
            
            # 3. 結果レポート
            self.progress_logger.log_info(f"インデックス{action}完了:")
            self.progress_logger.log_info(f"  ソースディレクトリ: {source_dir}")
            self.progress_logger.log_info(f"  再帰的検索: {'有効' if recursive else '無効'}")
            self.progress_logger.log_info(f"  RAWファイル数: {updated_index.file_count}")
            self.progress_logger.log_info(f"  最終更新: {updated_index.last_updated.strftime('%Y-%m-%d %H:%M:%S') if updated_index.last_updated else 'N/A'}")
            
            if verbose:
                # 詳細情報を表示
                self.progress_logger.log_info(f"  ベース名インデックス: {len(updated_index.by_basename)}エントリ")
                self.progress_logger.log_info(f"  日時インデックス: {len(updated_index.by_datetime)}エントリ")
                
                # ファイル形式の統計
                extensions = {}
                for info in updated_index.get_all_files():
                    ext = info.path.suffix.lower()
                    extensions[ext] = extensions.get(ext, 0) + 1
                
                if extensions:
                    self.progress_logger.log_info("  ファイル形式別統計:")
                    for ext, count in sorted(extensions.items()):
                        self.progress_logger.log_info(f"    {ext}: {count}ファイル")
            
        except Exception as e:
            error_msg = f"インデックス処理エラー: {e}"
            if self.progress_logger:
                self.progress_logger.log_error(source_dir, error_msg, e)
            else:
                print(f"エラー: {error_msg}")
            raise
    
    def list_indexed_directories(self, verbose: bool) -> None:
        """
        インデックス化されたディレクトリ一覧を表示
        
        Args:
            verbose: 詳細情報を表示する場合True
        """
        # プログレスロガーを初期化
        log_file = get_default_log_file() if verbose else None
        self.progress_logger = create_default_logger(verbose=verbose, log_file=log_file)
        
        try:
            directories = self.cache.list_indexed_directories()
            
            if not directories:
                self.progress_logger.log_info("インデックス化されたディレクトリはありません。")
                self.progress_logger.log_info("'raw-jpeg-matcher index <directory>' コマンドでインデックスを作成してください。")
                return
            
            self.progress_logger.log_info(f"インデックス化されたディレクトリ: {len(directories)}件")
            self.progress_logger.log_info("")
            
            for i, (source_dir, last_updated, file_count) in enumerate(directories, 1):
                self.progress_logger.log_info(f"{i}. {source_dir}")
                self.progress_logger.log_info(f"   最終更新: {last_updated.strftime('%Y-%m-%d %H:%M:%S')}")
                self.progress_logger.log_info(f"   RAWファイル数: {file_count}")
                
                if verbose:
                    # 詳細情報を表示
                    index = self.cache.load_directory_index(source_dir)
                    if index:
                        self.progress_logger.log_info(f"   ベース名インデックス: {len(index.by_basename)}エントリ")
                        self.progress_logger.log_info(f"   日時インデックス: {len(index.by_datetime)}エントリ")
                        
                        # ファイル形式の統計
                        extensions = {}
                        for info in index.get_all_files():
                            ext = info.path.suffix.lower()
                            extensions[ext] = extensions.get(ext, 0) + 1
                        
                        if extensions:
                            self.progress_logger.log_info("   ファイル形式別統計:")
                            for ext, count in sorted(extensions.items()):
                                self.progress_logger.log_info(f"     {ext}: {count}ファイル")
                
                self.progress_logger.log_info("")
            
        except Exception as e:
            error_msg = f"ディレクトリ一覧取得エラー: {e}"
            if self.progress_logger:
                self.progress_logger.log_error(Path(""), error_msg, e)
            else:
                print(f"エラー: {error_msg}")
            raise
    
    def clear_cache(self, source_dir: Optional[Path] = None) -> None:
        """
        キャッシュをクリア
        
        Args:
            source_dir: 特定ディレクトリのキャッシュのみクリア（Noneの場合は全体）
        """
        # プログレスロガーを初期化
        self.progress_logger = create_default_logger(verbose=False)
        
        try:
            if source_dir:
                # 特定ディレクトリのキャッシュをクリア
                success = self.cache.remove_directory_index(source_dir)
                if success:
                    self.progress_logger.log_info(f"ソースディレクトリ '{source_dir}' のキャッシュをクリアしました")
                else:
                    self.progress_logger.log_warning(f"ソースディレクトリ '{source_dir}' のキャッシュが見つかりませんでした")
            else:
                # すべてのキャッシュをクリア
                self.cache.clear_all_cache()
                self.progress_logger.log_info("すべてのインデックスキャッシュをクリアしました")
                
        except Exception as e:
            error_msg = f"キャッシュクリアエラー: {e}"
            if self.progress_logger:
                self.progress_logger.log_error(source_dir or Path(""), error_msg, e)
            else:
                print(f"エラー: {error_msg}")
            raise