"""
ロギングシステムのプロパティベーステスト

**Feature: raw-jpeg-matcher, Property 10: エラーログの完全性**
**Validates: Requirements 7.5**
"""

import tempfile
import logging
from pathlib import Path
from datetime import datetime
from hypothesis import given, strategies as st
from hypothesis import settings

from src.logger import ProgressLogger, LogConfig, create_default_logger
from src.exceptions import ProcessingError, ValidationError, FileOperationError, ExifReadError


class TestLoggerProperties:
    """ロギングシステムのプロパティテスト"""
    
    @given(
        file_paths=st.lists(
            st.text(min_size=1, max_size=100).filter(lambda x: x.strip() and '/' not in x and '\\' not in x and '\n' not in x and '\r' not in x),
            min_size=1,
            max_size=10
        ),
        error_messages=st.lists(
            st.text(min_size=1, max_size=200).filter(lambda x: x.strip() and '\n' not in x and '\r' not in x),
            min_size=1,
            max_size=10
        )
    )
    @settings(max_examples=100)
    def test_error_log_completeness_property(self, file_paths, error_messages):
        """
        **Feature: raw-jpeg-matcher, Property 10: エラーログの完全性**
        **Validates: Requirements 7.5**
        
        任意の処理中に発生したエラーに対して、エラーログはエラーが発生した
        ファイルパスとエラーの説明の両方を含むべきである。
        """
        # 一時ログファイルを作成
        with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as temp_log:
            log_file = Path(temp_log.name)
        
        try:
            # ロガーを設定
            config = LogConfig(
                console_level=logging.ERROR,  # コンソール出力を抑制
                file_level=logging.DEBUG,
                log_file=log_file,
                verbose=True
            )
            logger = ProgressLogger(config)
            
            # エラーログを記録
            logged_errors = []
            for i, (file_path_str, error_msg) in enumerate(zip(file_paths, error_messages)):
                file_path = Path(f"test_file_{i}_{file_path_str}")
                logger.log_error(file_path, error_msg)
                logged_errors.append((file_path, error_msg))
            
            # ログファイルの内容を読み取り
            log_content = log_file.read_text(encoding='utf-8')
            
            # 各エラーについて、ファイルパスとエラーメッセージの両方が含まれていることを確認
            for file_path, error_msg in logged_errors:
                # ファイルパスが含まれていることを確認
                assert str(file_path) in log_content, f"ログにファイルパス '{file_path}' が含まれていません"
                
                # エラーメッセージが含まれていることを確認
                assert error_msg in log_content, f"ログにエラーメッセージ '{error_msg}' が含まれていません"
                
                # "エラー" という文字列が含まれていることを確認（日本語ログ形式）
                assert "エラー" in log_content, "ログに 'エラー' という文字列が含まれていません"
        
        finally:
            # 一時ファイルをクリーンアップ
            if log_file.exists():
                log_file.unlink()
    
    @given(
        file_paths=st.lists(
            st.text(min_size=1, max_size=50).filter(lambda x: x.strip() and '/' not in x and '\\' not in x and '\n' not in x and '\r' not in x),
            min_size=1,
            max_size=5
        ),
        error_messages=st.lists(
            st.text(min_size=1, max_size=100).filter(lambda x: x.strip() and '\n' not in x and '\r' not in x),
            min_size=1,
            max_size=5
        ),
        exception_types=st.lists(
            st.sampled_from([ProcessingError, ValidationError, FileOperationError, ExifReadError]),
            min_size=1,
            max_size=5
        )
    )
    @settings(max_examples=100)
    def test_error_log_with_exceptions_property(self, file_paths, error_messages, exception_types):
        """
        **Feature: raw-jpeg-matcher, Property 10: エラーログの完全性**
        **Validates: Requirements 7.5**
        
        例外オブジェクトと共にエラーログを記録する場合、ファイルパス、
        エラーメッセージ、例外情報の全てが含まれるべきである。
        """
        # 一時ログファイルを作成
        with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as temp_log:
            log_file = Path(temp_log.name)
        
        try:
            # ロガーを設定
            config = LogConfig(
                console_level=logging.ERROR,  # コンソール出力を抑制
                file_level=logging.DEBUG,
                log_file=log_file,
                verbose=True
            )
            logger = ProgressLogger(config)
            
            # エラーログを例外と共に記録
            logged_errors = []
            for i, (file_path_str, error_msg, exc_type) in enumerate(zip(file_paths, error_messages, exception_types)):
                file_path = Path(f"test_file_{i}_{file_path_str}")
                exception = exc_type(f"Test exception: {error_msg}")
                logger.log_error(file_path, error_msg, exception)
                logged_errors.append((file_path, error_msg, exception))
            
            # ログファイルの内容を読み取り
            log_content = log_file.read_text(encoding='utf-8')
            
            # 各エラーについて、必要な情報が全て含まれていることを確認
            for file_path, error_msg, exception in logged_errors:
                # ファイルパスが含まれていることを確認
                assert str(file_path) in log_content, f"ログにファイルパス '{file_path}' が含まれていません"
                
                # エラーメッセージが含まれていることを確認
                assert error_msg in log_content, f"ログにエラーメッセージ '{error_msg}' が含まれていません"
                
                # 例外クラス名が含まれていることを確認
                assert type(exception).__name__ in log_content, f"ログに例外クラス名 '{type(exception).__name__}' が含まれていません"
        
        finally:
            # 一時ファイルをクリーンアップ
            if log_file.exists():
                log_file.unlink()
    
    @given(
        messages=st.lists(
            st.text(min_size=1, max_size=100).filter(lambda x: x.strip() and '\n' not in x and '\r' not in x),
            min_size=1,
            max_size=10
        )
    )
    @settings(max_examples=100)
    def test_console_and_file_logging_consistency_property(self, messages):
        """
        コンソールとファイルの両方にログが出力される場合、
        重要な情報が両方に含まれることを確認する。
        """
        # 一時ログファイルを作成
        with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as temp_log:
            log_file = Path(temp_log.name)
        
        try:
            # ロガーを設定（両方に出力）
            config = LogConfig(
                console_level=logging.INFO,
                file_level=logging.DEBUG,
                log_file=log_file,
                verbose=True
            )
            logger = ProgressLogger(config)
            
            # 各種ログメッセージを記録
            for message in messages:
                logger.log_info(message)
            
            # ログファイルの内容を読み取り
            log_content = log_file.read_text(encoding='utf-8')
            
            # 各メッセージがファイルログに含まれていることを確認
            for message in messages:
                assert message in log_content, f"ログファイルにメッセージ '{message}' が含まれていません"
        
        finally:
            # 一時ファイルをクリーンアップ
            if log_file.exists():
                log_file.unlink()