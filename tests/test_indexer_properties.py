"""
Indexerのプロパティベーステスト

インデックス作成と永続化の正確性を検証します。
"""

import tempfile
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from hypothesis import given, strategies as st, assume
from hypothesis.strategies import composite

from src.indexer import RawFileIndex, IndexCache, Indexer
from src.models import RawFileInfo


@composite
def raw_file_info_strategy(draw):
    """RawFileInfoを生成するストラテジー"""
    # ユニークなファイルパスを生成するためにUUIDを使用
    import uuid
    unique_id = str(uuid.uuid4())[:8]
    filename = draw(st.text(min_size=1, max_size=10, 
                           alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))))
    extension = draw(st.sampled_from(['.CR2', '.NEF', '.ARW', '.RAF', '.ORF']))
    path = Path(f"/test/{filename}_{unique_id}{extension}")
    
    # ベース名（小文字）
    basename = f"{filename}_{unique_id}".lower()
    
    # 撮影日時（オプション）
    has_datetime = draw(st.booleans())
    capture_datetime = None
    if has_datetime:
        capture_datetime = draw(st.datetimes(
            min_value=datetime(2020, 1, 1),
            max_value=datetime(2024, 12, 31)
        ))
    
    # ファイルサイズ
    file_size = draw(st.integers(min_value=1, max_value=100_000_000))
    
    return RawFileInfo(
        path=path,
        basename=basename,
        capture_datetime=capture_datetime,
        file_size=file_size
    )


@composite
def raw_file_index_strategy(draw):
    """RawFileIndexを生成するストラテジー"""
    index = RawFileIndex()
    
    # ソースディレクトリを設定
    source_dir = Path(f"/test/source_{draw(st.integers(min_value=1, max_value=1000))}")
    index.source_directory = source_dir
    
    # 最終更新日時を設定
    index.last_updated = draw(st.datetimes(
        min_value=datetime(2020, 1, 1),
        max_value=datetime(2024, 12, 31)
    ))
    
    # ファイル情報を追加
    file_infos = draw(st.lists(raw_file_info_strategy(), min_size=0, max_size=10))
    for info in file_infos:
        index.add(info)
    
    return index


class TestIndexerProperties:
    """Indexerのプロパティテスト"""
    
    @given(raw_file_index_strategy())
    def test_index_persistence_consistency(self, original_index):
        """
        **Feature: raw-jpeg-matcher, Property 11: インデックス永続化の一貫性**
        **Validates: Requirements 9.1**
        
        任意のRAWファイルインデックスに対して、ディスクに保存してから読み込んだ
        インデックスは元のインデックスと同じ内容を持つべきである。
        """
        # 一時ディレクトリを作成
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # IndexCacheを作成（一時ディレクトリを使用）
            cache = IndexCache()
            cache.cache_dir = temp_path / 'cache'
            cache.cache_dir.mkdir(parents=True, exist_ok=True)
            cache.global_index_file = cache.cache_dir / 'global_index.json'
            
            # ソースディレクトリが設定されていない場合はスキップ
            assume(original_index.source_directory is not None)
            
            # インデックスを保存
            cache.save_directory_index(original_index.source_directory, original_index)
            
            # インデックスを読み込み
            loaded_index = cache.load_directory_index(original_index.source_directory)
            
            # 読み込みが成功することを確認
            assert loaded_index is not None
            
            # 基本情報の一致を確認
            assert loaded_index.source_directory == original_index.source_directory
            assert loaded_index.file_count == original_index.file_count
            
            # ファイル情報の一致を確認
            original_files = original_index.get_all_files()
            loaded_files = loaded_index.get_all_files()
            
            assert len(loaded_files) == len(original_files)
            
            # ファイル情報をパスでソートして比較
            original_sorted = sorted(original_files, key=lambda x: str(x.path))
            loaded_sorted = sorted(loaded_files, key=lambda x: str(x.path))
            
            for orig, loaded in zip(original_sorted, loaded_sorted):
                assert loaded.path == orig.path
                assert loaded.basename == orig.basename
                assert loaded.capture_datetime == orig.capture_datetime
                assert loaded.file_size == orig.file_size
            
            # インデックス検索機能の一致を確認
            for orig_file in original_files:
                # ベース名での検索
                orig_by_basename = original_index.find_by_basename(orig_file.basename)
                loaded_by_basename = loaded_index.find_by_basename(orig_file.basename)
                assert len(loaded_by_basename) == len(orig_by_basename)
                
                # 撮影日時での検索（日時が存在する場合）
                if orig_file.capture_datetime:
                    orig_by_datetime = original_index.find_by_datetime(orig_file.capture_datetime)
                    loaded_by_datetime = loaded_index.find_by_datetime(orig_file.capture_datetime)
                    assert len(loaded_by_datetime) == len(orig_by_datetime)
                    
                    # ベース名と撮影日時での検索
                    orig_by_both = original_index.find_by_basename_and_datetime(
                        orig_file.basename, orig_file.capture_datetime)
                    loaded_by_both = loaded_index.find_by_basename_and_datetime(
                        orig_file.basename, orig_file.capture_datetime)
                    assert len(loaded_by_both) == len(orig_by_both)
    
    @given(st.lists(raw_file_info_strategy(), min_size=1, max_size=5))
    def test_index_add_remove_consistency(self, file_infos):
        """
        インデックスへの追加と削除の一貫性をテスト
        
        任意のファイル情報リストに対して、インデックスに追加してから削除すると
        元の空の状態に戻るべきである。
        """
        index = RawFileIndex()
        
        # 初期状態の確認
        assert index.file_count == 0
        assert len(index.get_all_files()) == 0
        
        # ファイルを追加
        for info in file_infos:
            index.add(info)
        
        # 追加後の状態確認
        assert index.file_count == len(file_infos)
        assert len(index.get_all_files()) == len(file_infos)
        
        # ファイルを削除
        for info in file_infos:
            removed = index.remove(info.path)
            assert removed is True
        
        # 削除後の状態確認（元の空の状態に戻る）
        assert index.file_count == 0
        assert len(index.get_all_files()) == 0
        assert len(index.by_basename) == 0
        assert len(index.by_datetime) == 0
    
    @given(raw_file_info_strategy())
    def test_index_search_consistency(self, file_info):
        """
        インデックス検索の一貫性をテスト
        
        任意のファイル情報に対して、インデックスに追加した後の検索結果は
        一貫性を保つべきである。
        """
        index = RawFileIndex()
        index.add(file_info)
        
        # ベース名での検索
        by_basename = index.find_by_basename(file_info.basename)
        assert len(by_basename) >= 1
        assert file_info in by_basename
        
        # 撮影日時での検索（日時が存在する場合）
        if file_info.capture_datetime:
            by_datetime = index.find_by_datetime(file_info.capture_datetime)
            assert len(by_datetime) >= 1
            assert file_info in by_datetime
            
            # ベース名と撮影日時での検索
            by_both = index.find_by_basename_and_datetime(
                file_info.basename, file_info.capture_datetime)
            assert len(by_both) >= 1
            assert file_info in by_both
            
            # ベース名と撮影日時での検索結果は、両方の条件を満たすはず
            for result in by_both:
                assert result.basename == file_info.basename
                assert result.capture_datetime == file_info.capture_datetime
    
    @given(st.lists(raw_file_info_strategy(), min_size=0, max_size=10))
    def test_index_serialization_roundtrip(self, file_infos):
        """
        インデックスのシリアライゼーション往復テスト
        
        任意のファイル情報リストに対して、インデックスを辞書に変換してから
        復元すると元のインデックスと同じ内容になるべきである。
        """
        # 元のインデックスを作成
        original_index = RawFileIndex()
        original_index.source_directory = Path("/test/source")
        original_index.last_updated = datetime(2024, 1, 1, 12, 0, 0)
        
        for info in file_infos:
            original_index.add(info)
        
        # 辞書に変換
        index_dict = original_index.to_dict()
        
        # 辞書から復元
        restored_index = RawFileIndex.from_dict(index_dict)
        
        # 基本情報の一致を確認
        assert restored_index.source_directory == original_index.source_directory
        assert restored_index.file_count == original_index.file_count
        
        # ファイル情報の一致を確認
        original_files = original_index.get_all_files()
        restored_files = restored_index.get_all_files()
        
        assert len(restored_files) == len(original_files)
        
        # ファイル情報をパスでソートして比較
        original_sorted = sorted(original_files, key=lambda x: str(x.path))
        restored_sorted = sorted(restored_files, key=lambda x: str(x.path))
        
        for orig, restored in zip(original_sorted, restored_sorted):
            assert restored.path == orig.path
            assert restored.basename == orig.basename
            assert restored.capture_datetime == orig.capture_datetime
            assert restored.file_size == orig.file_size
    
    @given(st.lists(raw_file_info_strategy(), min_size=0, max_size=8),
           st.lists(raw_file_info_strategy(), min_size=0, max_size=3))
    def test_incremental_update_accuracy(self, initial_files, additional_files):
        """
        **Feature: raw-jpeg-matcher, Property 12: 差分更新の正確性**
        **Validates: Requirements 9.2, 9.4, 9.5**
        
        任意の既存インデックスと新しいファイルセットに対して、差分更新後の
        インデックスは完全再構築したインデックスと同じ結果を持つべきである。
        """
        # 一時ディレクトリを作成
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            source_dir = temp_path / "source"
            source_dir.mkdir()
            
            # 初期ファイルを作成
            initial_file_paths = []
            for i, info in enumerate(initial_files):
                file_path = source_dir / f"initial_{i}{info.path.suffix}"
                file_path.write_text(f"dummy content {i}")
                initial_file_paths.append(file_path)
            
            # モックのExifReaderとFileScannerを作成
            from unittest.mock import Mock
            
            mock_exif_reader = Mock()
            mock_file_scanner = Mock()
            
            # 初期ファイルのスキャン結果を設定
            mock_file_scanner.scan_raw_files.return_value = initial_file_paths
            mock_file_scanner.get_basename.side_effect = lambda p: p.stem.lower()
            
            # Exif読み取り結果を設定
            def mock_read_exif(path):
                # パスに基づいて決定的な日時を返す
                path_hash = hash(str(path)) % 1000
                if path_hash % 3 == 0:  # 1/3の確率で日時を返す
                    return datetime(2024, 1, 1) + timedelta(days=path_hash % 365)
                return None
            
            mock_exif_reader.read_capture_datetime.side_effect = mock_read_exif
            
            # Indexerを作成
            indexer = Indexer(mock_exif_reader, mock_file_scanner)
            
            # 初期インデックスを構築
            initial_index = indexer.build_index(source_dir, recursive=True, force_rebuild=True)
            
            # 追加ファイルを作成
            additional_file_paths = []
            for i, info in enumerate(additional_files):
                file_path = source_dir / f"additional_{i}{info.path.suffix}"
                file_path.write_text(f"additional content {i}")
                additional_file_paths.append(file_path)
            
            # 全ファイルのスキャン結果を更新
            all_file_paths = initial_file_paths + additional_file_paths
            mock_file_scanner.scan_raw_files.return_value = all_file_paths
            
            # 差分更新を実行
            updated_index = indexer.update_index_incrementally(
                initial_index, source_dir, recursive=True)
            
            # 完全再構築を実行（比較用）
            rebuilt_index = indexer._build_new_index(source_dir, recursive=True)
            
            # 結果の比較
            assert updated_index.file_count == rebuilt_index.file_count
            
            # ファイル情報の比較
            updated_files = sorted(updated_index.get_all_files(), key=lambda x: str(x.path))
            rebuilt_files = sorted(rebuilt_index.get_all_files(), key=lambda x: str(x.path))
            
            assert len(updated_files) == len(rebuilt_files)
            
            for updated, rebuilt in zip(updated_files, rebuilt_files):
                assert updated.path == rebuilt.path
                assert updated.basename == rebuilt.basename
                assert updated.capture_datetime == rebuilt.capture_datetime
                assert updated.file_size == rebuilt.file_size
            
            # インデックス検索結果の比較
            for file_info in updated_files:
                # ベース名での検索
                updated_by_basename = updated_index.find_by_basename(file_info.basename)
                rebuilt_by_basename = rebuilt_index.find_by_basename(file_info.basename)
                assert len(updated_by_basename) == len(rebuilt_by_basename)
                
                # 撮影日時での検索（日時が存在する場合）
                if file_info.capture_datetime:
                    updated_by_datetime = updated_index.find_by_datetime(file_info.capture_datetime)
                    rebuilt_by_datetime = rebuilt_index.find_by_datetime(file_info.capture_datetime)
                    assert len(updated_by_datetime) == len(rebuilt_by_datetime)
    
    @given(st.lists(raw_file_info_strategy(), min_size=1, max_size=5))
    def test_file_deletion_update_accuracy(self, initial_files):
        """
        ファイル削除時の差分更新の正確性をテスト
        
        任意の初期ファイルセットに対して、一部のファイルを削除した後の
        差分更新は正確に削除を反映すべきである。
        """
        # 一時ディレクトリを作成
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            source_dir = temp_path / "source"
            source_dir.mkdir()
            
            # 初期ファイルを作成
            initial_file_paths = []
            for i, info in enumerate(initial_files):
                file_path = source_dir / f"file_{i}{info.path.suffix}"
                file_path.write_text(f"content {i}")
                initial_file_paths.append(file_path)
            
            # モックのExifReaderとFileScannerを作成
            from unittest.mock import Mock
            
            mock_exif_reader = Mock()
            mock_file_scanner = Mock()
            
            # 初期ファイルのスキャン結果を設定
            mock_file_scanner.scan_raw_files.return_value = initial_file_paths
            mock_file_scanner.get_basename.side_effect = lambda p: p.stem.lower()
            mock_exif_reader.read_capture_datetime.return_value = None
            
            # Indexerを作成
            indexer = Indexer(mock_exif_reader, mock_file_scanner)
            
            # 初期インデックスを構築
            initial_index = indexer.build_index(source_dir, recursive=True, force_rebuild=True)
            
            # 一部のファイルを削除（最初のファイルを削除）
            if initial_file_paths:
                deleted_file = initial_file_paths[0]
                deleted_file.unlink()
                remaining_files = initial_file_paths[1:]
                
                # スキャン結果を更新
                mock_file_scanner.scan_raw_files.return_value = remaining_files
                
                # 差分更新を実行
                updated_index = indexer.update_index_incrementally(
                    initial_index, source_dir, recursive=True)
                
                # 削除されたファイルがインデックスから除去されていることを確認
                assert updated_index.file_count == len(remaining_files)
                
                # 削除されたファイルが検索結果に含まれないことを確認
                deleted_basename = deleted_file.stem.lower()
                found_files = updated_index.find_by_basename(deleted_basename)
                assert all(info.path != deleted_file for info in found_files)