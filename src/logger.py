"""
ロギングシステム

RAW-JPEG Matcher Toolのロギング機能を提供します。
標準出力とファイル出力の両方をサポートし、進捗表示とエラーログを管理します。
"""

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple
from dataclasses import dataclass

from .models import ProcessingStats


@dataclass
class LogConfig:
    """ログ設定"""
    console_level: int = logging.INFO
    file_level: int = logging.DEBUG
    log_file: Optional[Path] = None
    verbose: bool = False


class ProgressLogger:
    """進捗表示とロギングを管理するクラス"""
    
    def __init__(self, config: LogConfig):
        self.config = config
        self.logger = self._setup_logger()
        self._start_time: Optional[datetime] = None
        
    def _setup_logger(self) -> logging.Logger:
        """ロガーのセットアップ"""
        logger = logging.getLogger('raw_jpeg_matcher')
        logger.setLevel(logging.DEBUG)
        
        # 既存のハンドラーをクリア
        logger.handlers.clear()
        
        # フォーマッターを作成
        console_formatter = logging.Formatter(
            '%(message)s'
        )
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # コンソールハンドラー
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(self.config.console_level)
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
        
        # ファイルハンドラー（指定されている場合）
        if self.config.log_file:
            # ログディレクトリを作成
            self.config.log_file.parent.mkdir(parents=True, exist_ok=True)
            
            file_handler = logging.FileHandler(self.config.log_file, encoding='utf-8')
            file_handler.setLevel(self.config.file_level)
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)
        
        return logger
    
    def log_processing_start(self, source_dirs: List[Path], target_dir: Optional[Path] = None):
        """処理開始時のサマリー表示"""
        self._start_time = datetime.now()
        
        self.logger.info("=" * 60)
        self.logger.info("RAW-JPEG Matcher Tool - 処理開始")
        self.logger.info("=" * 60)
        self.logger.info(f"開始時刻: {self._start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        if source_dirs:
            self.logger.info("ソースディレクトリ:")
            for source_dir in source_dirs:
                self.logger.info(f"  - {source_dir}")
        
        if target_dir:
            self.logger.info(f"ターゲットディレクトリ: {target_dir}")
        
        self.logger.info("")
    
    def log_index_start(self, source_dir: Path, recursive: bool):
        """インデックス構築開始のログ"""
        self.logger.info(f"インデックス構築開始: {source_dir}")
        if recursive:
            self.logger.info("  - サブディレクトリも含めて検索します")
        else:
            self.logger.info("  - 指定ディレクトリのみを検索します")
    
    def log_index_progress(self, files_found: int, files_processed: int, current_file: Optional[Path] = None):
        """インデックス構築時の進捗表示"""
        if self.config.verbose and current_file:
            self.logger.info(f"処理中: {current_file.name}")
        
        if files_found > 0:
            progress = (files_processed / files_found) * 100
            self.logger.info(f"インデックス構築進捗: {files_processed}/{files_found} ({progress:.1f}%)")
    
    def log_index_complete(self, raw_files_count: int, processing_time: float):
        """インデックス構築完了のログ"""
        self.logger.info(f"インデックス構築完了: {raw_files_count}個のRAWファイルを処理")
        self.logger.info(f"処理時間: {processing_time:.2f}秒")
        self.logger.info("")
    
    def log_matching_start(self, target_dir: Path, recursive: bool):
        """マッチング処理開始のログ"""
        self.logger.info(f"マッチング処理開始: {target_dir}")
        if recursive:
            self.logger.info("  - サブディレクトリも含めて検索します")
        else:
            self.logger.info("  - 指定ディレクトリのみを検索します")
    
    def log_matching_progress(self, jpeg_files_found: int, files_processed: int, matches_found: int, current_file: Optional[Path] = None):
        """マッチング時の進捗表示"""
        if self.config.verbose and current_file:
            self.logger.info(f"処理中: {current_file.name}")
        
        if jpeg_files_found > 0:
            progress = (files_processed / jpeg_files_found) * 100
            self.logger.info(f"マッチング進捗: {files_processed}/{jpeg_files_found} ({progress:.1f}%) - マッチ数: {matches_found}")
    
    def log_matching_complete(self, matches_found: int, processing_time: float):
        """マッチング処理完了のログ"""
        self.logger.info(f"マッチング処理完了: {matches_found}個のマッチを発見")
        self.logger.info(f"処理時間: {processing_time:.2f}秒")
        self.logger.info("")
    
    def log_copy_start(self, matches_count: int):
        """コピー処理開始のログ"""
        self.logger.info(f"コピー処理開始: {matches_count}個のファイルをコピー予定")
    
    def log_copy_progress(self, total_files: int, files_processed: int, current_file: Optional[Path] = None):
        """コピー時の進捗表示"""
        if self.config.verbose and current_file:
            self.logger.info(f"コピー中: {current_file.name}")
        
        if total_files > 0:
            progress = (files_processed / total_files) * 100
            self.logger.info(f"コピー進捗: {files_processed}/{total_files} ({progress:.1f}%)")
    
    def log_copy_complete(self, copy_result, processing_time: float):
        """コピー処理完了のログ"""
        self.logger.info(f"コピー処理完了:")
        self.logger.info(f"  - 成功: {copy_result.success}個")
        self.logger.info(f"  - スキップ: {copy_result.skipped}個")
        self.logger.info(f"  - 失敗: {copy_result.failed}個")
        self.logger.info(f"処理時間: {processing_time:.2f}秒")
        self.logger.info("")
    
    def log_processing_complete(self, stats: ProcessingStats):
        """処理完了時のサマリー表示"""
        end_time = datetime.now()
        total_time = (end_time - self._start_time).total_seconds() if self._start_time else 0
        
        self.logger.info("=" * 60)
        self.logger.info("処理完了サマリー")
        self.logger.info("=" * 60)
        self.logger.info(f"終了時刻: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info(f"総処理時間: {total_time:.2f}秒")
        self.logger.info("")
        self.logger.info("処理結果:")
        self.logger.info(f"  - RAWファイル発見数: {stats.raw_files_found}")
        self.logger.info(f"  - JPEGファイル発見数: {stats.jpeg_files_found}")
        self.logger.info(f"  - マッチ数: {stats.matches_found}")
        self.logger.info(f"  - コピー成功: {stats.files_copied}")
        self.logger.info(f"  - スキップ: {stats.files_skipped}")
        self.logger.info(f"  - 失敗: {stats.files_failed}")
        
        if stats.errors:
            self.logger.info("")
            self.logger.info(f"エラー詳細 ({len(stats.errors)}件):")
            for file_path, error_msg in stats.errors:
                self.logger.error(f"  - {file_path}: {error_msg}")
        
        self.logger.info("=" * 60)
    
    def log_error(self, file_path: Path, error_message: str, exception: Optional[Exception] = None):
        """エラーログの詳細記録"""
        error_msg = f"エラー - {file_path}: {error_message}"
        
        if exception:
            error_msg += f" ({type(exception).__name__}: {str(exception)})"
        
        self.logger.error(error_msg)
        
        # 詳細なスタックトレースはファイルログのみに記録
        if exception and self.config.log_file:
            self.logger.debug("スタックトレース:", exc_info=exception)
    
    def log_warning(self, message: str):
        """警告メッセージのログ"""
        self.logger.warning(f"警告: {message}")
    
    def log_info(self, message: str):
        """情報メッセージのログ"""
        self.logger.info(message)
    
    def log_debug(self, message: str):
        """デバッグメッセージのログ"""
        self.logger.debug(message)


def create_default_logger(verbose: bool = False, log_file: Optional[Path] = None) -> ProgressLogger:
    """デフォルトのロガーを作成"""
    config = LogConfig(
        console_level=logging.DEBUG if verbose else logging.INFO,
        file_level=logging.DEBUG,
        log_file=log_file,
        verbose=verbose
    )
    return ProgressLogger(config)


def get_default_log_file() -> Path:
    """デフォルトのログファイルパスを取得"""
    log_dir = Path.home() / '.raw_jpeg_matcher' / 'logs'
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    return log_dir / f'raw_jpeg_matcher_{timestamp}.log'