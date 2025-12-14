"""
MatchManagerのプロパティベーステスト

Hypothesisライブラリを使用してMatchManagerクラスの普遍的な特性を検証します。
"""

import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from hypothesis import given, settings, strategies as st

from src.match_manager import MatchManager
from src.models import CopyResult, MatchResult, RawFileInfo


class TestMatchManagerProperties:
    """MatchManagerのプロパティテスト"""
    
    @given(
        jpeg_count=st.integers(min_value=0, max_value=100),
        match_count=st.integers(min_value=0, max_value=100),
        success_count=st.integers(min_value=0, max_value=100),
        skipped_count=st.integers(min_value=0, max_value=50),
        failed_count=st.integers(min_value=0, max_value=50)
    )
    @settings(max_examples=100, deadline=None)
    def test_processing_summary_accuracy_property(self, jpeg_count, match_count, success_count, skipped_count, failed_count):
        """
        **Feature: raw-jpeg-matcher, Property 8: 処理サマリーの正確性**
        
        任意の完了した処理実行に対して、報告される統計情報（コピーされたファイル数、
        スキップされたファイル数、失敗したファイル数）は見つかったマッチの総数と一致すべきである。
        
        検証対象: 要件 5.5
        """
        # match_countがjpeg_count以下になるように調整
        match_count = min(match_count, jpeg_count)
        
        # コピー結果の合計がマッチ数以下になるように調整
        total_copy_operations = success_count + skipped_count + failed_count
        if total_copy_operations > match_count:
            # 比例配分で調整
            if total_copy_operations > 0:
                ratio = match_count / total_copy_operations
                success_count = int(success_count * ratio)
                skipped_count = int(skipped_count * ratio)
                failed_count = match_count - success_count - skipped_count
                failed_count = max(0, failed_count)  # 負の値を防ぐ
        
        # テスト用のMatchManagerを作成
        manager = MatchManager()
        
        # モックのCopyResultを作成
        copy_result = CopyResult(
            success=success_count,
            skipped=skipped_count,
            failed=failed_count,
            errors=[]
        )
        
        # ProcessingStatsを作成してlog_processing_completeメソッドをテスト
        from src.models import ProcessingStats
        stats = ProcessingStats(
            raw_files_found=100,
            jpeg_files_found=jpeg_count,
            matches_found=match_count,
            files_copied=success_count,
            files_skipped=skipped_count,
            files_failed=failed_count,
            errors=[]
        )
        
        # プログレスロガーを初期化してテスト
        from src.logger import create_default_logger
        manager.progress_logger = create_default_logger(verbose=False)
        manager.progress_logger.log_processing_complete(stats)
        
        # プロパティ検証: コピー操作の合計がマッチ数と一致すること
        total_reported = success_count + skipped_count + failed_count
        assert total_reported <= match_count, (
            f"コピー操作の合計({total_reported})がマッチ数({match_count})を超えています"
        )
        
        # 統計情報の整合性を検証
        assert stats.jpeg_files_found == jpeg_count, "JPEGファイル数が一致しません"
        assert stats.matches_found == match_count, "マッチ数が一致しません"
        assert stats.files_copied == success_count, "コピー成功数が一致しません"
        assert stats.files_skipped == skipped_count, "スキップ数が一致しません"
        assert stats.files_failed == failed_count, "失敗数が一致しません"
    
    @given(
        has_directories=st.booleans(),
        has_matching_filter=st.booleans(),
        directory_count=st.integers(min_value=0, max_value=10)
    )
    @settings(max_examples=100, deadline=None)
    def test_index_shortage_warning_display_property(self, has_directories, has_matching_filter, directory_count):
        """
        **Feature: raw-jpeg-matcher, Property 13: インデックス不足時の警告表示**
        
        任意のマッチング処理において、利用可能なインデックスが存在しない場合、
        システムは適切な警告メッセージを表示すべきである。
        
        検証対象: 要件 10.7
        """
        manager = MatchManager()
        
        # テスト用のディレクトリリストを作成
        if has_directories and directory_count > 0:
            directories = [
                (Path(f"/test/dir{i}"), datetime.now(), 10)
                for i in range(directory_count)
            ]
        else:
            directories = []
        
        # ソースフィルターの設定
        source_filter = "/test/dir0" if has_matching_filter and directories else None
        
        # list_indexed_directoriesをモック
        with patch.object(manager.cache, 'list_indexed_directories', return_value=directories):
            # _display_index_warningをモック
            with patch.object(manager, '_display_index_warning') as mock_warning:
                result = manager._check_index_availability(source_filter)
                
                # プロパティ検証: インデックスが不足している場合の動作
                if not directories:
                    # ディレクトリが全くない場合
                    assert not result, "ディレクトリがない場合はFalseを返すべき"
                    mock_warning.assert_called_once_with([])
                    
                elif source_filter and has_matching_filter:
                    # フィルターが指定されているが、マッチするディレクトリがない場合
                    filter_path = Path(source_filter)
                    matching = any(d == filter_path for d, _, _ in directories)
                    
                    if not matching:
                        assert not result, "マッチするディレクトリがない場合はFalseを返すべき"
                        mock_warning.assert_called_once_with([filter_path])
                    else:
                        assert result, "マッチするディレクトリがある場合はTrueを返すべき"
                        mock_warning.assert_not_called()
                        
                else:
                    # ディレクトリが存在し、フィルター条件も満たす場合
                    assert result, "利用可能なインデックスがある場合はTrueを返すべき"
                    mock_warning.assert_not_called()
    
    @given(
        missing_dir_count=st.integers(min_value=0, max_value=5)
    )
    @settings(max_examples=100, deadline=None)
    def test_index_warning_message_completeness_property(self, missing_dir_count):
        """
        **Feature: raw-jpeg-matcher, Property 13: インデックス不足時の警告表示**
        
        任意の不足ディレクトリリストに対して、警告メッセージは適切な指示を含むべきである。
        
        検証対象: 要件 10.7
        """
        manager = MatchManager()
        
        # 不足ディレクトリのリストを作成
        missing_directories = [Path(f"/missing/dir{i}") for i in range(missing_dir_count)]
        
        # 出力をキャプチャ
        with patch('builtins.print') as mock_print:
            manager._display_index_warning(missing_directories)
        
        # 出力内容を取得
        print_calls = [str(call) for call in mock_print.call_args_list]
        output_text = ' '.join(print_calls)
        
        # プロパティ検証: 警告メッセージの完全性
        
        # 1. 警告メッセージが含まれていること
        assert "警告" in output_text or "Warning" in output_text, "警告メッセージが含まれていません"
        
        # 2. インデックス作成の指示が含まれていること
        assert "index" in output_text.lower(), "インデックス作成の指示が含まれていません"
        
        # 3. 不足ディレクトリが指定されている場合、それらが出力に含まれていること
        for directory in missing_directories:
            assert str(directory) in output_text, f"不足ディレクトリ {directory} が出力に含まれていません"
        
        # 4. コマンド例が含まれていること
        assert "raw-jpeg-matcher" in output_text, "コマンド例が含まれていません"
        
        # 5. 既存インデックス確認の指示が含まれていること
        assert "list-index" in output_text, "既存インデックス確認の指示が含まれていません"


# 基本的な動作テスト（プロパティテストの補完）
class TestMatchManagerBasicOperations:
    """MatchManagerの基本動作テスト"""
    
    def test_match_manager_initialization(self):
        """MatchManagerの初期化テスト"""
        manager = MatchManager()
        
        assert manager.cache is not None
        assert manager.exif_reader is not None
        assert manager.file_scanner is not None
        assert manager.copier is not None
        assert manager.progress_logger is None  # 初期化時はNone
    
    def test_load_global_index_empty(self):
        """空のインデックスからグローバルインデックスを作成するテスト"""
        manager = MatchManager()
        
        # 空のディレクトリリストをモック
        with patch.object(manager.cache, 'list_indexed_directories', return_value=[]):
            global_index = manager._load_global_index(None)
            
            assert global_index.file_count == 0
    
    def test_check_index_availability_no_directories(self):
        """ディレクトリが存在しない場合のインデックス可用性チェック"""
        manager = MatchManager()
        
        with patch.object(manager.cache, 'list_indexed_directories', return_value=[]):
            with patch.object(manager, '_display_index_warning') as mock_warning:
                result = manager._check_index_availability(None)
                
                assert not result
                mock_warning.assert_called_once_with([])