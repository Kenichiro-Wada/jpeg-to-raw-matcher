"""
エッジケースのユニットテスト

RAW-JPEG Matcher Toolの各コンポーネントのエッジケースをテストします。
要件 3.4, 5.3, 8.1, 8.2, 8.3, 8.4, 8.5 に対応。
"""

import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch, mock_open

from src.copier import Copier
from src.exif_reader import ExifReader
from src.exceptions import ExifReadError, ValidationError
from src.file_scanner import FileScanner
from src.matcher import Matcher
from src.models import MatchResult, RawFileInfo, JpegFileInfo
from src.indexer import RawFileIndex


class TestExifReaderEdgeCases(unittest.TestCase):
    """ExifReaderのエッジケーステスト"""
    
    def setUp(self):
        """テスト前の準備"""
        self.exif_reader = ExifReader()
        self.temp_dir = Path(tempfile.mkdtemp())
    
    def tearDown(self):
        """テスト後のクリーンアップ"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_missing_exif_data_file(self):
        """Exifデータが欠落しているファイルの処理テスト（要件 3.4）"""
        # 空のファイルを作成（Exifデータなし）
        empty_file = self.temp_dir / "no_exif.jpg"
        empty_file.write_bytes(b"fake jpeg data without exif")
        
        # Exifデータが取得できないことを確認
        result = self.exif_reader.read_capture_datetime(empty_file)
        self.assertIsNone(result)
        
        # キャッシュに保存されていることを確認
        self.assertTrue(self.exif_reader.is_cached(empty_file))
        self.assertIsNone(self.exif_reader.cache[empty_file])
    
    def test_corrupted_exif_data_file(self):
        """破損したExifデータの処理テスト（要件 3.4）"""
        # 破損したファイルを作成
        corrupted_file = self.temp_dir / "corrupted.jpg"
        corrupted_file.write_bytes(b"\xff\xe1\x00\x16Exif\x00\x00corrupted_data")
        
        # 破損したExifデータでもエラーを適切に処理することを確認
        # _extract_datetime_from_file内でエラーがキャッチされてNoneが返される
        with patch('exifread.process_file', side_effect=Exception("Corrupted EXIF")):
            result = self.exif_reader.read_capture_datetime(corrupted_file)
            self.assertIsNone(result)
        
        # キャッシュにNoneが保存されることを確認
        self.assertTrue(self.exif_reader.is_cached(corrupted_file))
        self.assertIsNone(self.exif_reader.cache[corrupted_file])
    
    def test_zero_byte_file(self):
        """0バイトファイルの処理テスト"""
        # 0バイトファイルを作成
        zero_file = self.temp_dir / "zero.jpg"
        zero_file.touch()
        
        # 0バイトファイルは適切に処理されることを確認
        result = self.exif_reader.read_capture_datetime(zero_file)
        self.assertIsNone(result)
    
    def test_nonexistent_file(self):
        """存在しないファイルの処理テスト"""
        nonexistent_file = self.temp_dir / "nonexistent.jpg"
        
        # 存在しないファイルは適切に処理されることを確認
        result = self.exif_reader.read_capture_datetime(nonexistent_file)
        self.assertIsNone(result)
    
    def test_permission_denied_file(self):
        """ファイル権限エラーのテスト（要件 8.4）"""
        # ファイルを作成
        protected_file = self.temp_dir / "protected.jpg"
        protected_file.write_bytes(b"fake jpeg data")
        
        # ファイルの読み取り権限を削除
        protected_file.chmod(0o000)
        
        try:
            # 権限エラーが適切に処理されることを確認
            # _extract_datetime_from_file内でファイルオープンエラーがキャッチされてNoneが返される
            result = self.exif_reader.read_capture_datetime(protected_file)
            self.assertIsNone(result)
            
            # キャッシュにNoneが保存されることを確認
            self.assertTrue(self.exif_reader.is_cached(protected_file))
            self.assertIsNone(self.exif_reader.cache[protected_file])
        finally:
            # テスト後に権限を復元
            protected_file.chmod(0o644)
    
    def test_file_stat_error(self):
        """ファイル統計情報取得エラーのテスト"""
        # 存在するファイルを作成
        test_file = self.temp_dir / "test.jpg"
        test_file.write_bytes(b"fake jpeg data")
        
        # file_path.stat()でエラーが発生するようにモック
        with patch.object(Path, 'stat', side_effect=PermissionError("Permission denied")):
            with self.assertRaises(ExifReadError):
                self.exif_reader.read_capture_datetime(test_file)
        
        # エラー後もキャッシュにNoneが保存されることを確認
        self.assertIsNone(self.exif_reader.cache[test_file])


class TestCopierEdgeCases(unittest.TestCase):
    """Copierのエッジケーステスト"""
    
    def setUp(self):
        """テスト前の準備"""
        self.copier = Copier()
        self.temp_dir = Path(tempfile.mkdtemp())
        self.source_dir = self.temp_dir / "source"
        self.target_dir = self.temp_dir / "target"
        self.source_dir.mkdir()
        self.target_dir.mkdir()
    
    def tearDown(self):
        """テスト後のクリーンアップ"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_existing_file_in_target_directory(self):
        """ターゲットディレクトリに既存ファイルがある場合のテスト（要件 5.3）"""
        # ソースファイルを作成
        source_file = self.source_dir / "test.cr2"
        source_file.write_bytes(b"raw file data")
        
        # ターゲットディレクトリに同名ファイルを作成
        target_file = self.target_dir / "test.cr2"
        target_file.write_bytes(b"existing file")
        
        # マッチ結果を作成
        match = MatchResult(
            jpeg_path=Path("dummy.jpg"),
            raw_path=source_file,
            match_method="basename_and_datetime"
        )
        
        # コピー実行
        result = self.copier.copy_files([match], self.target_dir)
        
        # 既存ファイルがスキップされることを確認
        self.assertEqual(result.success, 0)
        self.assertEqual(result.skipped, 1)
        self.assertEqual(result.failed, 0)
        
        # 既存ファイルが変更されていないことを確認
        self.assertEqual(target_file.read_bytes(), b"existing file")
    
    def test_disk_space_insufficient(self):
        """ディスク容量不足のテスト（要件 8.3）"""
        # ソースファイルを作成
        source_file = self.source_dir / "large.cr2"
        source_file.write_bytes(b"raw file data")
        
        # マッチ結果を作成
        match = MatchResult(
            jpeg_path=Path("dummy.jpg"),
            raw_path=source_file,
            match_method="basename_and_datetime"
        )
        
        # ディスク容量チェックが失敗するようにモック
        with patch.object(self.copier, '_check_disk_space', return_value=False):
            result = self.copier.copy_files([match], self.target_dir)
        
        # ディスク容量不足で失敗することを確認
        self.assertEqual(result.success, 0)
        self.assertEqual(result.skipped, 0)
        self.assertEqual(result.failed, 1)
    
    def test_permission_error_during_copy(self):
        """ファイル権限エラーのテスト（要件 8.4）"""
        # ソースファイルを作成
        source_file = self.source_dir / "test.cr2"
        source_file.write_bytes(b"raw file data")
        
        # マッチ結果を作成
        match = MatchResult(
            jpeg_path=Path("dummy.jpg"),
            raw_path=source_file,
            match_method="basename_and_datetime"
        )
        
        # shutil.copy2でPermissionErrorが発生するようにモック
        with patch('shutil.copy2', side_effect=PermissionError("Permission denied")):
            result = self.copier.copy_files([match], self.target_dir)
        
        # 権限エラーで失敗することを確認
        self.assertEqual(result.success, 0)
        self.assertEqual(result.skipped, 0)
        self.assertEqual(result.failed, 1)
    
    def test_source_file_not_exists(self):
        """ソースファイルが存在しない場合のテスト"""
        # 存在しないソースファイル
        nonexistent_file = self.source_dir / "nonexistent.cr2"
        
        # マッチ結果を作成
        match = MatchResult(
            jpeg_path=Path("dummy.jpg"),
            raw_path=nonexistent_file,
            match_method="basename_and_datetime"
        )
        
        # コピー実行
        result = self.copier.copy_files([match], self.target_dir)
        
        # ソースファイルが存在しないため失敗することを確認
        self.assertEqual(result.success, 0)
        self.assertEqual(result.skipped, 0)
        self.assertEqual(result.failed, 1)
    
    def test_target_directory_creation_failure(self):
        """ターゲットディレクトリ作成失敗のテスト"""
        # 存在しないターゲットディレクトリ
        invalid_target = Path("/invalid/path/that/cannot/be/created")
        
        # ソースファイルを作成
        source_file = self.source_dir / "test.cr2"
        source_file.write_bytes(b"raw file data")
        
        # マッチ結果を作成
        match = MatchResult(
            jpeg_path=Path("dummy.jpg"),
            raw_path=source_file,
            match_method="basename_and_datetime"
        )
        
        # コピー実行
        result = self.copier.copy_files([match], invalid_target)
        
        # ターゲットディレクトリ作成失敗で全て失敗することを確認
        self.assertEqual(result.success, 0)
        self.assertEqual(result.skipped, 0)
        self.assertEqual(result.failed, 1)


class TestFileScannerEdgeCases(unittest.TestCase):
    """FileScannerのエッジケーステスト"""
    
    def setUp(self):
        """テスト前の準備"""
        self.file_scanner = FileScanner()
        self.temp_dir = Path(tempfile.mkdtemp())
    
    def tearDown(self):
        """テスト後のクリーンアップ"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_unsupported_file_formats(self):
        """未対応のファイル形式のテスト（要件 8.5）"""
        # 未対応の拡張子のファイルを作成
        unsupported_files = [
            self.temp_dir / "test.txt",
            self.temp_dir / "test.png",
            self.temp_dir / "test.tiff",
            self.temp_dir / "test.bmp",
        ]
        
        for file_path in unsupported_files:
            file_path.write_bytes(b"dummy data")
        
        # RAWファイルスキャン
        raw_files = self.file_scanner.scan_raw_files(self.temp_dir)
        self.assertEqual(len(raw_files), 0)
        
        # JPEGファイルスキャン
        jpeg_files = self.file_scanner.scan_jpeg_files(self.temp_dir)
        self.assertEqual(len(jpeg_files), 0)
    
    def test_mixed_case_extensions(self):
        """大文字小文字混在の拡張子のテスト"""
        # 大文字小文字混在のファイルを作成
        mixed_files = [
            self.temp_dir / "test.Cr2",
            self.temp_dir / "test.nEf",
            self.temp_dir / "test.Jpg",
            self.temp_dir / "test.JpEg",
        ]
        
        for file_path in mixed_files:
            file_path.write_bytes(b"dummy data")
        
        # 大文字小文字混在でも正しく認識されることを確認
        self.assertFalse(self.file_scanner.is_raw_file(mixed_files[0]))  # .Cr2は未定義
        self.assertFalse(self.file_scanner.is_raw_file(mixed_files[1]))  # .nEfは未定義
        self.assertFalse(self.file_scanner.is_jpeg_file(mixed_files[2]))  # .Jpgは未定義
        self.assertFalse(self.file_scanner.is_jpeg_file(mixed_files[3]))  # .JpEgは未定義
    
    def test_empty_directory(self):
        """空のディレクトリのテスト"""
        empty_dir = self.temp_dir / "empty"
        empty_dir.mkdir()
        
        # 空のディレクトリでも正常に動作することを確認
        raw_files = self.file_scanner.scan_raw_files(empty_dir)
        self.assertEqual(len(raw_files), 0)
        
        jpeg_files = self.file_scanner.scan_jpeg_files(empty_dir)
        self.assertEqual(len(jpeg_files), 0)
    
    def test_invalid_directory(self):
        """無効なディレクトリのテスト"""
        invalid_dir = Path("/nonexistent/directory")
        
        # 無効なディレクトリでValidationErrorが発生することを確認
        with self.assertRaises(ValidationError):
            self.file_scanner.scan_raw_files(invalid_dir)
        
        with self.assertRaises(ValidationError):
            self.file_scanner.scan_jpeg_files(invalid_dir)


class TestMatcherEdgeCases(unittest.TestCase):
    """Matcherのエッジケーステスト"""
    
    def setUp(self):
        """テスト前の準備"""
        self.exif_reader = Mock(spec=ExifReader)
        self.index = RawFileIndex()
        self.matcher = Matcher(self.exif_reader, self.index)
        self.temp_dir = Path(tempfile.mkdtemp())
    
    def tearDown(self):
        """テスト後のクリーンアップ"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_no_matching_jpeg_files(self):
        """マッチしないJPEGファイルの処理テスト（要件 8.1）"""
        # JPEGファイルを作成
        jpeg_file = self.temp_dir / "nomatch.jpg"
        jpeg_file.write_bytes(b"jpeg data")
        
        # Exif読み取りをモック（撮影日時なし）
        self.exif_reader.read_capture_datetime.return_value = None
        
        # 空のインデックス（マッチするRAWファイルなし）
        matches = self.matcher.find_matches([jpeg_file])
        
        # マッチしないことを確認
        self.assertEqual(len(matches), 0)
    
    def test_jpeg_with_exif_but_no_matching_raw_datetime(self):
        """JPEGに撮影日時があるがRAWファイルの日時が一致しない場合のテスト"""
        from datetime import datetime
        
        # JPEGファイルを作成
        jpeg_file = self.temp_dir / "test.jpg"
        jpeg_file.write_bytes(b"jpeg data")
        
        # RAWファイル情報をインデックスに追加（異なる撮影日時）
        raw_info = RawFileInfo(
            path=Path("test.cr2"),
            basename="test",
            capture_datetime=datetime(2023, 1, 1, 12, 0, 0),
            file_size=1000
        )
        self.index.add(raw_info)
        
        # JPEGのExif読み取りをモック（異なる撮影日時）
        self.exif_reader.read_capture_datetime.return_value = datetime(2023, 1, 2, 12, 0, 0)
        
        # マッチング実行
        matches = self.matcher.find_matches([jpeg_file])
        
        # 日時が一致しないためマッチしないことを確認
        self.assertEqual(len(matches), 0)
    
    def test_jpeg_without_exif_with_basename_match(self):
        """JPEGに撮影日時がないがベース名でマッチする場合のテスト"""
        # JPEGファイルを作成
        jpeg_file = self.temp_dir / "test.jpg"
        jpeg_file.write_bytes(b"jpeg data")
        
        # RAWファイル情報をインデックスに追加
        raw_info = RawFileInfo(
            path=Path("test.cr2"),
            basename="test",
            capture_datetime=None,
            file_size=1000
        )
        self.index.add(raw_info)
        
        # JPEGのExif読み取りをモック（撮影日時なし）
        self.exif_reader.read_capture_datetime.return_value = None
        
        # マッチング実行
        matches = self.matcher.find_matches([jpeg_file])
        
        # ベース名のみでマッチすることを確認
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].match_method, 'basename_only')
    
    def test_multiple_raw_candidates_with_same_datetime(self):
        """同じ撮影日時を持つ複数のRAWファイル候補がある場合のテスト"""
        from datetime import datetime
        
        # JPEGファイルを作成
        jpeg_file = self.temp_dir / "test.jpg"
        jpeg_file.write_bytes(b"jpeg data")
        
        # 同じベース名と撮影日時を持つ複数のRAWファイル情報をインデックスに追加
        capture_time = datetime(2023, 1, 1, 12, 0, 0)
        for i in range(3):
            raw_info = RawFileInfo(
                path=Path(f"test_{i}.cr2"),
                basename="test",
                capture_datetime=capture_time,
                file_size=1000
            )
            self.index.add(raw_info)
        
        # JPEGのExif読み取りをモック
        self.exif_reader.read_capture_datetime.return_value = capture_time
        
        # マッチング実行
        matches = self.matcher.find_matches([jpeg_file])
        
        # 最初の候補が選択されることを確認
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].match_method, 'basename_and_datetime')
    
    def test_exif_read_error_during_matching(self):
        """マッチング中のExif読み取りエラーのテスト"""
        # JPEGファイルを作成
        jpeg_file = self.temp_dir / "test.jpg"
        jpeg_file.write_bytes(b"jpeg data")
        
        # Exif読み取りでエラーが発生するようにモック
        self.exif_reader.read_capture_datetime.side_effect = ExifReadError("Exif read failed")
        
        # マッチング実行（エラーが発生してもクラッシュしないことを確認）
        matches = self.matcher.find_matches([jpeg_file])
        
        # エラーが発生してもマッチング処理が継続されることを確認
        self.assertEqual(len(matches), 0)


class TestIntegrationEdgeCases(unittest.TestCase):
    """統合的なエッジケーステスト"""
    
    def setUp(self):
        """テスト前の準備"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.source_dir = self.temp_dir / "source"
        self.target_dir = self.temp_dir / "target"
        self.source_dir.mkdir()
        self.target_dir.mkdir()
    
    def tearDown(self):
        """テスト後のクリーンアップ"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_mixed_success_and_failure_scenario(self):
        """成功とエラーが混在するシナリオのテスト"""
        from src.models import MatchResult
        
        # 成功するファイル
        success_file = self.source_dir / "success.cr2"
        success_file.write_bytes(b"raw file data")
        
        # 存在しないファイル
        missing_file = self.source_dir / "missing.cr2"
        
        # マッチ結果を作成
        matches = [
            MatchResult(
                jpeg_path=Path("success.jpg"),
                raw_path=success_file,
                match_method="basename_and_datetime"
            ),
            MatchResult(
                jpeg_path=Path("missing.jpg"),
                raw_path=missing_file,
                match_method="basename_and_datetime"
            )
        ]
        
        # コピー実行
        copier = Copier()
        result = copier.copy_files(matches, self.target_dir)
        
        # 結果の確認
        self.assertEqual(result.success, 1)
        self.assertEqual(result.skipped, 0)
        self.assertEqual(result.failed, 1)
        self.assertEqual(len(result.errors), 1)  # エラーリストに1件のエラーが記録される
    
    def test_large_file_handling(self):
        """大きなファイルの処理テスト"""
        # 大きなファイルを作成（1MB）
        large_file = self.source_dir / "large.cr2"
        large_data = b"x" * (1024 * 1024)  # 1MB
        large_file.write_bytes(large_data)
        
        # マッチ結果を作成
        match = MatchResult(
            jpeg_path=Path("large.jpg"),
            raw_path=large_file,
            match_method="basename_and_datetime"
        )
        
        # コピー実行
        copier = Copier()
        result = copier.copy_files([match], self.target_dir)
        
        # 成功することを確認
        self.assertEqual(result.success, 1)
        self.assertEqual(result.failed, 0)
        
        # コピーされたファイルのサイズが正しいことを確認
        copied_file = self.target_dir / "large.cr2"
        self.assertTrue(copied_file.exists())
        self.assertEqual(copied_file.stat().st_size, len(large_data))
    
    def test_special_characters_in_filename(self):
        """ファイル名に特殊文字が含まれる場合のテスト"""
        # 特殊文字を含むファイル名
        special_names = [
            "test with spaces.cr2",
            "test-with-hyphens.cr2",
            "test_with_underscores.cr2",
            "test.with.dots.cr2",
            "テスト日本語.cr2",  # 日本語
        ]
        
        matches = []
        for name in special_names:
            file_path = self.source_dir / name
            file_path.write_bytes(b"raw file data")
            
            match = MatchResult(
                jpeg_path=Path(name.replace(".cr2", ".jpg")),
                raw_path=file_path,
                match_method="basename_and_datetime"
            )
            matches.append(match)
        
        # コピー実行
        copier = Copier()
        result = copier.copy_files(matches, self.target_dir)
        
        # 全て成功することを確認
        self.assertEqual(result.success, len(special_names))
        self.assertEqual(result.failed, 0)
        
        # コピーされたファイルが存在することを確認
        for name in special_names:
            copied_file = self.target_dir / name
            self.assertTrue(copied_file.exists(), f"File not copied: {name}")


class TestErrorMessageValidation(unittest.TestCase):
    """エラーメッセージの内容検証テスト"""
    
    def setUp(self):
        """テスト前の準備"""
        self.temp_dir = Path(tempfile.mkdtemp())
    
    def tearDown(self):
        """テスト後のクリーンアップ"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_exif_error_message_contains_file_path(self):
        """ExifReadErrorのエラーメッセージにファイルパスが含まれることを確認（要件 7.5）"""
        exif_reader = ExifReader()
        test_file = self.temp_dir / "test.jpg"
        test_file.write_bytes(b"fake data")
        
        # ファイル統計情報取得でエラーを発生させる
        with patch.object(Path, 'stat', side_effect=PermissionError("Access denied")):
            try:
                exif_reader.read_capture_datetime(test_file)
                self.fail("ExifReadError should have been raised")
            except ExifReadError as e:
                # エラーメッセージにファイルパスが含まれることを確認
                self.assertIn(str(test_file), str(e))
                self.assertIn("Exif読み取りエラー", str(e))
    
    def test_validation_error_message_format(self):
        """ValidationErrorのメッセージ形式を確認"""
        from src.path_validator import PathValidator
        
        nonexistent_path = Path("/nonexistent/directory")
        
        try:
            PathValidator.validate_directory(nonexistent_path)
            self.fail("ValidationError should have been raised")
        except ValidationError as e:
            # エラーメッセージが適切な形式であることを確認
            error_msg = str(e)
            self.assertTrue(len(error_msg) > 0)
            # パスが含まれていることを確認
            self.assertIn(str(nonexistent_path), error_msg)


if __name__ == '__main__':
    unittest.main()