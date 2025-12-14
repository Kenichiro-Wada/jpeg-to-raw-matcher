"""
統合テスト

エンドツーエンドの処理フローをテストします。
実際のサンプルファイルを使用して、index、match、list-index、clear-cacheの
各コマンドが正しく動作することを確認します。
"""

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import List, Tuple
import pytest

from src.cli import main
from src.index_manager import IndexManager
from src.match_manager import MatchManager
from src.models import ProcessingStats


class TestIntegration:
    """統合テストクラス"""
    
    @pytest.fixture
    def test_data_dir(self) -> Path:
        """テストデータディレクトリのパスを取得"""
        return Path(__file__).parent / "data"
    
    @pytest.fixture
    def temp_source_dir(self, test_data_dir: Path) -> Path:
        """一時的なソースディレクトリを作成（RAWファイル用）"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # RAWファイルをコピー
            raw_files = [
                "test001.CR3",
                "test002.cr3", 
                "test004.CR3"
            ]
            
            for raw_file in raw_files:
                src_file = test_data_dir / raw_file
                if src_file.exists():
                    shutil.copy2(src_file, temp_path / raw_file)
            
            yield temp_path
    
    @pytest.fixture
    def temp_target_dir(self, test_data_dir: Path) -> Path:
        """一時的なターゲットディレクトリを作成（JPEGファイル用）"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # JPEGファイルをコピー
            jpeg_files = [
                "test001.JPG",
                "test002.jpg",
                "test003.JPG",
                "test004.JPG"
            ]
            
            for jpeg_file in jpeg_files:
                src_file = test_data_dir / jpeg_file
                if src_file.exists():
                    shutil.copy2(src_file, temp_path / jpeg_file)
            
            yield temp_path
    
    @pytest.fixture
    def clean_cache(self):
        """テスト前後でキャッシュをクリア"""
        # テスト前にキャッシュをクリア
        index_manager = IndexManager()
        index_manager.clear_cache()
        
        yield
        
        # テスト後にキャッシュをクリア
        index_manager.clear_cache()
    
    def test_end_to_end_workflow(self, temp_source_dir: Path, temp_target_dir: Path, clean_cache):
        """
        エンドツーエンドの処理フローをテスト
        
        1. indexコマンドでRAWファイルをインデックス化
        2. list-indexコマンドでインデックス確認
        3. matchコマンドでマッチング処理
        4. 結果の検証
        5. clear-cacheコマンドでキャッシュクリア
        """
        # 1. indexコマンドでRAWファイルをインデックス化
        index_manager = IndexManager()
        index_manager.build_or_update_index(
            source_dir=temp_source_dir,
            recursive=True,
            force_rebuild=False,
            verbose=False
        )
        
        # 2. インデックスが作成されたことを確認
        indexed_dirs = index_manager.cache.list_indexed_directories()
        assert len(indexed_dirs) == 1
        # パスの正規化を考慮して比較
        assert indexed_dirs[0][0].resolve() == temp_source_dir.resolve()
        assert indexed_dirs[0][2] == 3  # RAWファイル数
        
        # 3. matchコマンドでマッチング処理
        match_manager = MatchManager()
        
        # マッチング前のターゲットディレクトリのファイル数を確認
        initial_files = list(temp_target_dir.glob("*"))
        initial_jpeg_count = len([f for f in initial_files if f.suffix.lower() in ['.jpg', '.jpeg']])
        initial_raw_count = len([f for f in initial_files if f.suffix.lower() in ['.cr2', '.cr3', '.nef', '.arw']])
        
        assert initial_jpeg_count == 4  # test001.JPG, test002.jpg, test003.JPG, test004.JPG
        assert initial_raw_count == 0   # 初期状態ではRAWファイルはない
        
        # マッチング処理を実行
        match_manager.find_and_copy_matches(
            target_dir=temp_target_dir,
            recursive=True,
            source_filter=None,
            verbose=False
        )
        
        # 4. 結果の検証
        final_files = list(temp_target_dir.glob("*"))
        final_jpeg_count = len([f for f in final_files if f.suffix.lower() in ['.jpg', '.jpeg']])
        final_raw_count = len([f for f in final_files if f.suffix.lower() in ['.cr2', '.cr3', '.nef', '.arw']])
        
        # JPEGファイル数は変わらない
        assert final_jpeg_count == 4
        
        # マッチしたRAWファイルがコピーされている
        # test001.JPG ↔ test001.CR3: マッチする（同じ撮影日時）
        # test002.jpg ↔ test002.cr3: マッチする（同じ撮影日時、大文字小文字を区別しない）
        # test003.JPG: マッチするRAWファイルなし
        # test004.JPG ↔ test004.CR3: マッチしない（撮影日時が異なる）
        expected_raw_count = 2  # test001.CR3, test002.cr3
        assert final_raw_count == expected_raw_count
        
        # 具体的なファイルの存在確認
        assert (temp_target_dir / "test001.CR3").exists()
        assert (temp_target_dir / "test002.cr3").exists()
        assert not (temp_target_dir / "test004.CR3").exists()  # 撮影日時が異なるためマッチしない
        
        # 5. clear-cacheコマンドでキャッシュクリア
        index_manager.clear_cache()
        
        # キャッシュがクリアされたことを確認
        indexed_dirs_after_clear = index_manager.cache.list_indexed_directories()
        assert len(indexed_dirs_after_clear) == 0
    
    def test_cli_index_command(self, temp_source_dir: Path, clean_cache, monkeypatch):
        """CLIのindexコマンドをテスト"""
        # コマンドライン引数を設定
        test_args = ['raw-jpeg-matcher', 'index', str(temp_source_dir), '--verbose']
        monkeypatch.setattr(sys, 'argv', test_args)
        
        # CLIを実行
        exit_code = main()
        assert exit_code == 0
        
        # インデックスが作成されたことを確認
        index_manager = IndexManager()
        indexed_dirs = index_manager.cache.list_indexed_directories()
        assert len(indexed_dirs) == 1
        # パスの正規化を考慮して比較
        assert indexed_dirs[0][0].resolve() == temp_source_dir.resolve()
    
    def test_cli_match_command(self, temp_source_dir: Path, temp_target_dir: Path, clean_cache, monkeypatch):
        """CLIのmatchコマンドをテスト"""
        # まずインデックスを作成
        index_manager = IndexManager()
        index_manager.build_or_update_index(
            source_dir=temp_source_dir,
            recursive=True,
            force_rebuild=False,
            verbose=False
        )
        
        # コマンドライン引数を設定
        test_args = ['raw-jpeg-matcher', 'match', str(temp_target_dir), '--verbose']
        monkeypatch.setattr(sys, 'argv', test_args)
        
        # CLIを実行
        exit_code = main()
        assert exit_code == 0
        
        # マッチしたRAWファイルがコピーされていることを確認
        assert (temp_target_dir / "test001.CR3").exists()
        assert (temp_target_dir / "test002.cr3").exists()
    
    def test_cli_list_index_command(self, temp_source_dir: Path, clean_cache, monkeypatch, capsys):
        """CLIのlist-indexコマンドをテスト"""
        # まずインデックスを作成
        index_manager = IndexManager()
        index_manager.build_or_update_index(
            source_dir=temp_source_dir,
            recursive=True,
            force_rebuild=False,
            verbose=False
        )
        
        # コマンドライン引数を設定
        test_args = ['raw-jpeg-matcher', 'list-index', '--verbose']
        monkeypatch.setattr(sys, 'argv', test_args)
        
        # CLIを実行
        exit_code = main()
        assert exit_code == 0
        
        # 出力を確認
        captured = capsys.readouterr()
        assert str(temp_source_dir) in captured.out
    
    def test_cli_clear_cache_command(self, temp_source_dir: Path, clean_cache, monkeypatch):
        """CLIのclear-cacheコマンドをテスト"""
        # まずインデックスを作成
        index_manager = IndexManager()
        index_manager.build_or_update_index(
            source_dir=temp_source_dir,
            recursive=True,
            force_rebuild=False,
            verbose=False
        )
        
        # インデックスが存在することを確認
        indexed_dirs = index_manager.cache.list_indexed_directories()
        assert len(indexed_dirs) == 1
        
        # コマンドライン引数を設定
        test_args = ['raw-jpeg-matcher', 'clear-cache']
        monkeypatch.setattr(sys, 'argv', test_args)
        
        # CLIを実行
        exit_code = main()
        assert exit_code == 0
        
        # キャッシュがクリアされたことを確認
        indexed_dirs_after_clear = index_manager.cache.list_indexed_directories()
        assert len(indexed_dirs_after_clear) == 0
    
    def test_source_filter_functionality(self, temp_source_dir: Path, temp_target_dir: Path, clean_cache):
        """ソースフィルター機能をテスト"""
        # 追加のソースディレクトリを作成
        with tempfile.TemporaryDirectory() as temp_dir2:
            temp_source_dir2 = Path(temp_dir2)
            
            # 異なるRAWファイルをコピー（test003に対応するRAWファイルを作成）
            test_data_dir = Path(__file__).parent / "data"
            if (test_data_dir / "test001.CR3").exists():
                # test001.CR3をtest003.CR3として別ディレクトリにコピー
                shutil.copy2(test_data_dir / "test001.CR3", temp_source_dir2 / "test003.CR3")
            
            # 両方のディレクトリをインデックス化
            index_manager = IndexManager()
            index_manager.build_or_update_index(temp_source_dir, True, False, False)
            index_manager.build_or_update_index(temp_source_dir2, True, False, False)
            
            # ソースフィルターを使用してマッチング
            match_manager = MatchManager()
            match_manager.find_and_copy_matches(
                target_dir=temp_target_dir,
                recursive=True,
                source_filter=str(temp_source_dir.resolve()),  # 正規化されたパスを使用
                verbose=False
            )
            
            # 最初のディレクトリのRAWファイルのみがコピーされていることを確認
            assert (temp_target_dir / "test001.CR3").exists()
            assert (temp_target_dir / "test002.cr3").exists()
            assert not (temp_target_dir / "test003.CR3").exists()  # フィルターで除外される
    
    def test_no_recursive_option(self, temp_source_dir: Path, temp_target_dir: Path, clean_cache):
        """--no-recursiveオプションをテスト"""
        # サブディレクトリを作成してRAWファイルを配置
        sub_dir = temp_source_dir / "subdir"
        sub_dir.mkdir()
        
        test_data_dir = Path(__file__).parent / "data"
        if (test_data_dir / "test001.CR3").exists():
            shutil.copy2(test_data_dir / "test001.CR3", sub_dir / "test005.CR3")
        
        # --no-recursiveでインデックス化
        index_manager = IndexManager()
        index_manager.build_or_update_index(
            source_dir=temp_source_dir,
            recursive=False,  # サブディレクトリを検索しない
            force_rebuild=False,
            verbose=False
        )
        
        # サブディレクトリのファイルはインデックス化されていないことを確認
        # 実際のインデックスオブジェクトを読み込み
        source_index = index_manager.cache.load_directory_index(temp_source_dir)
        assert source_index is not None
        
        # ルートディレクトリのRAWファイルのみがインデックス化されている
        indexed_files = []
        for basename, file_list in source_index.by_basename.items():
            indexed_files.extend([info.path.name for info in file_list])
        
        assert "test001.CR3" in indexed_files
        assert "test002.cr3" in indexed_files
        assert "test004.CR3" in indexed_files
        assert "test005.CR3" not in indexed_files  # サブディレクトリのファイルは除外
    
    def test_force_rebuild_option(self, temp_source_dir: Path, clean_cache):
        """--force-rebuildオプションをテスト"""
        # 最初のインデックス作成
        index_manager = IndexManager()
        index_manager.build_or_update_index(temp_source_dir, True, False, False)
        
        # インデックスの最終更新時刻を取得
        first_index = index_manager.cache.load_directory_index(temp_source_dir)
        assert first_index is not None
        first_update_time = first_index.last_updated
        
        # 少し待機
        import time
        time.sleep(0.1)
        
        # 強制再構築
        index_manager.build_or_update_index(temp_source_dir, True, True, False)
        
        # インデックスが再構築されたことを確認
        second_index = index_manager.cache.load_directory_index(temp_source_dir)
        assert second_index is not None
        second_update_time = second_index.last_updated
        
        assert second_update_time > first_update_time
    
    def test_cross_platform_path_handling(self, temp_source_dir: Path, clean_cache):
        """クロスプラットフォームのパス処理をテスト"""
        # 異なるパス表現でも正しく処理されることを確認
        index_manager = IndexManager()
        
        # 絶対パスでインデックス作成
        index_manager.build_or_update_index(temp_source_dir.resolve(), True, False, False)
        
        # インデックスが作成されたことを確認
        indexed_dirs = index_manager.cache.list_indexed_directories()
        assert len(indexed_dirs) == 1
        
        # パスが正規化されて保存されていることを確認
        stored_path = indexed_dirs[0][0]
        assert stored_path.is_absolute()
    
    def test_error_handling_invalid_paths(self, clean_cache, monkeypatch):
        """無効なパスに対するエラーハンドリングをテスト"""
        # 存在しないディレクトリを指定
        invalid_path = "/nonexistent/directory"
        
        # indexコマンドでエラーハンドリング
        test_args = ['raw-jpeg-matcher', 'index', invalid_path]
        monkeypatch.setattr(sys, 'argv', test_args)
        
        exit_code = main()
        assert exit_code == 1  # エラーで終了
        
        # matchコマンドでエラーハンドリング
        test_args = ['raw-jpeg-matcher', 'match', invalid_path]
        monkeypatch.setattr(sys, 'argv', test_args)
        
        exit_code = main()
        assert exit_code == 1  # エラーで終了
    
    def test_matching_different_raw_formats(self, temp_target_dir: Path, clean_cache):
        """異なるRAW形式のマッチングをテスト（模擬）"""
        # 実際のテストでは、各カメラメーカーのRAWファイルが必要
        # ここでは既存のCR3ファイルを使用して基本的な動作を確認
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_source_dir = Path(temp_dir)
            test_data_dir = Path(__file__).parent / "data"
            
            # 異なる拡張子でRAWファイルをコピー（模擬的に）
            if (test_data_dir / "test001.CR3").exists():
                # CR3ファイルを異なる拡張子でコピー（実際のファイル形式は同じ）
                shutil.copy2(test_data_dir / "test001.CR3", temp_source_dir / "test001.NEF")
                shutil.copy2(test_data_dir / "test002.cr3", temp_source_dir / "test002.arw")
            
            # インデックス作成
            index_manager = IndexManager()
            index_manager.build_or_update_index(temp_source_dir, True, False, False)
            
            # マッチング処理
            match_manager = MatchManager()
            match_manager.find_and_copy_matches(temp_target_dir, True, None, False)
            
            # 異なる拡張子のRAWファイルもマッチングされることを確認
            # （実際のExif情報は同じなので、マッチするはず）
            raw_files = list(temp_target_dir.glob("*.NEF")) + list(temp_target_dir.glob("*.arw"))
            assert len(raw_files) >= 1  # 少なくとも1つはマッチする
    
    def test_case_insensitive_matching(self, temp_target_dir: Path, clean_cache):
        """大文字小文字を区別しないマッチングをテスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_source_dir = Path(temp_dir)
            test_data_dir = Path(__file__).parent / "data"
            
            # 大文字小文字が異なるファイル名でRAWファイルをコピー
            if (test_data_dir / "test001.CR3").exists():
                shutil.copy2(test_data_dir / "test001.CR3", temp_source_dir / "TEST001.cr3")
                shutil.copy2(test_data_dir / "test002.cr3", temp_source_dir / "Test002.CR3")
            
            # インデックス作成
            index_manager = IndexManager()
            index_manager.build_or_update_index(temp_source_dir, True, False, False)
            
            # マッチング処理
            match_manager = MatchManager()
            match_manager.find_and_copy_matches(temp_target_dir, True, None, False)
            
            # 大文字小文字が異なってもマッチングされることを確認
            copied_raw_files = [f for f in temp_target_dir.glob("*") 
                              if f.suffix.lower() in ['.cr2', '.cr3', '.nef', '.arw']]
            assert len(copied_raw_files) >= 1
    
    def test_windows_path_compatibility(self, clean_cache):
        """Windowsパス形式の互換性をテスト（模擬）"""
        # Windowsスタイルのパス文字列を使用してテスト
        # 実際のWindowsでなくても、パス処理の互換性を確認
        
        # Windowsスタイルのパス文字列（模擬）
        windows_style_paths = [
            "C:\\Users\\Test\\Photos\\RAW",
            "D:\\Photography\\2024\\January",
            "E:\\Backup\\Images"
        ]
        
        # pathlibがこれらのパスを適切に処理できることを確認
        for path_str in windows_style_paths:
            try:
                # Pathオブジェクトとして処理
                path_obj = Path(path_str)
                
                # パスの各部分が正しく解析されることを確認
                assert path_obj.parts is not None
                assert len(path_obj.parts) > 0
                
                # 文字列表現が取得できることを確認
                str_repr = str(path_obj)
                assert isinstance(str_repr, str)
                assert len(str_repr) > 0
                
            except Exception as e:
                pytest.fail(f"Windowsパス処理でエラー: {path_str} - {e}")
    
    def test_platform_specific_behavior(self, clean_cache):
        """プラットフォーム固有の動作をテスト"""
        import platform
        
        current_platform = platform.system()
        
        if current_platform == "Darwin":  # macOS
            # macOSでの動作確認
            test_path = Path("/Users/test/Documents")
            assert test_path.is_absolute()
            
        elif current_platform == "Windows":  # Windows
            # Windowsでの動作確認
            test_path = Path("C:\\Users\\test\\Documents")
            assert test_path.is_absolute()
            
        elif current_platform == "Linux":  # Linux
            # Linuxでの動作確認
            test_path = Path("/home/test/Documents")
            assert test_path.is_absolute()
        
        # 共通の動作確認
        temp_path = Path(tempfile.gettempdir())
        assert temp_path.exists()
        assert temp_path.is_dir()
    
    def test_large_file_collection_simulation(self, clean_cache):
        """大規模ファイルコレクションの模擬テスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_source_dir = Path(temp_dir)
            temp_target_dir = Path(temp_dir) / "target"
            temp_target_dir.mkdir()
            
            test_data_dir = Path(__file__).parent / "data"
            
            # 複数のサブディレクトリを作成して、ファイルを分散配置
            subdirs = ["2024-01", "2024-02", "2024-03"]
            
            for subdir in subdirs:
                sub_path = temp_source_dir / subdir
                sub_path.mkdir()
                
                # 各サブディレクトリにRAWファイルをコピー
                if (test_data_dir / "test001.CR3").exists():
                    shutil.copy2(test_data_dir / "test001.CR3", sub_path / f"{subdir}_001.CR3")
                if (test_data_dir / "test002.cr3").exists():
                    shutil.copy2(test_data_dir / "test002.cr3", sub_path / f"{subdir}_002.cr3")
            
            # 対応するJPEGファイルをターゲットディレクトリに配置
            for subdir in subdirs:
                if (test_data_dir / "test001.JPG").exists():
                    shutil.copy2(test_data_dir / "test001.JPG", temp_target_dir / f"{subdir}_001.JPG")
                if (test_data_dir / "test002.jpg").exists():
                    shutil.copy2(test_data_dir / "test002.jpg", temp_target_dir / f"{subdir}_002.jpg")
            
            # インデックス作成
            index_manager = IndexManager()
            index_manager.build_or_update_index(temp_source_dir, True, False, False)
            
            # インデックスが正しく作成されたことを確認
            indexed_dirs = index_manager.cache.list_indexed_directories()
            assert len(indexed_dirs) == 1
            assert indexed_dirs[0][2] == 6  # 6個のRAWファイル（3サブディレクトリ × 2ファイル）
            
            # マッチング処理
            match_manager = MatchManager()
            match_manager.find_and_copy_matches(temp_target_dir, True, None, False)
            
            # マッチしたRAWファイルがコピーされていることを確認
            copied_raw_files = [f for f in temp_target_dir.glob("*") 
                              if f.suffix.lower() in ['.cr2', '.cr3', '.nef', '.arw']]
            
            # 少なくとも一部のファイルがマッチしてコピーされることを確認
            assert len(copied_raw_files) >= 3  # 各サブディレクトリから少なくとも1つ