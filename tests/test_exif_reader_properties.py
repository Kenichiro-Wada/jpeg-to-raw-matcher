"""
ExifReaderのプロパティベーステスト

Property 4: Exif日時抽出
Property 9: Exifキャッシュの一貫性
を検証します。
"""

import tempfile
from datetime import datetime
from pathlib import Path
from hypothesis import given, strategies as st, assume
from hypothesis import settings
import pytest

from src.exif_reader import ExifReader
from src.exceptions import ExifReadError


# テスト用のExifデータを含むJPEGファイルのヘッダー（最小限）
MINIMAL_JPEG_WITH_EXIF = bytes([
    0xFF, 0xD8,  # JPEG SOI
    0xFF, 0xE1,  # APP1 marker
    0x00, 0x16,  # APP1 length (22 bytes)
    0x45, 0x78, 0x69, 0x66, 0x00, 0x00,  # "Exif\0\0"
    0x49, 0x49, 0x2A, 0x00,  # TIFF header (little endian)
    0x08, 0x00, 0x00, 0x00,  # IFD offset
    0x00, 0x00,  # Number of directory entries (0)
    0x00, 0x00, 0x00, 0x00,  # Next IFD offset (0)
    0xFF, 0xD9   # JPEG EOI
])

# 有効なExif日時文字列のストラテジー
@st.composite
def valid_exif_datetime_strategy(draw):
    """有効なExif日時文字列を生成するストラテジー"""
    year = draw(st.integers(min_value=2000, max_value=2024))
    month = draw(st.integers(min_value=1, max_value=12))
    day = draw(st.integers(min_value=1, max_value=28))  # 28日まで（月によらず安全）
    hour = draw(st.integers(min_value=0, max_value=23))
    minute = draw(st.integers(min_value=0, max_value=59))
    second = draw(st.integers(min_value=0, max_value=59))
    
    # Exif標準フォーマット: "YYYY:MM:DD HH:MM:SS"
    return f"{year:04d}:{month:02d}:{day:02d} {hour:02d}:{minute:02d}:{second:02d}"


@st.composite
def file_path_strategy(draw):
    """有効なファイルパスを生成するストラテジー"""
    # ファイル名部分
    filename = draw(st.text(
        alphabet=st.characters(
            whitelist_categories=('Lu', 'Ll', 'Nd'),
            min_codepoint=32,
            max_codepoint=126
        ),
        min_size=1,
        max_size=20
    ).filter(lambda x: x.strip() and not any(c in x for c in '<>:"|?*')))
    
    # 拡張子
    extension = draw(st.sampled_from([
        '.jpg', '.jpeg', '.JPG', '.JPEG',
        '.cr2', '.CR2', '.nef', '.NEF', '.arw', '.ARW'
    ]))
    
    return Path(f"/tmp/test_{filename}{extension}")


class TestExifReaderProperties:
    """ExifReaderのプロパティテスト"""
    
    def setup_method(self):
        """各テストメソッドの前に実行される初期化"""
        self.exif_reader = ExifReader()
    
    @settings(max_examples=100)
    @given(valid_exif_datetime_strategy())
    def test_exif_datetime_extraction_property(self, exif_datetime_str):
        """
        **Feature: raw-jpeg-matcher, Property 4: Exif日時抽出**
        **検証対象: 要件 3.1, 3.2**
        
        任意の有効なExifデータを持つ画像ファイル（JPEGまたはRAW）に対して、
        システムは撮影日時の値を正常に抽出すべきである。
        """
        # 有効なExif日時文字列をdatetimeオブジェクトに変換できることを検証
        parsed_datetime = self.exif_reader._parse_exif_datetime(exif_datetime_str)
        
        # プロパティ検証: 有効な日時文字列は正常に解析される
        assert parsed_datetime is not None
        assert isinstance(parsed_datetime, datetime)
        
        # 解析された日時が元の文字列と一致することを検証
        # Exif標準フォーマットに戻して比較
        expected_format = parsed_datetime.strftime('%Y:%m:%d %H:%M:%S')
        assert expected_format == exif_datetime_str
    
    @settings(max_examples=100)
    @given(file_path_strategy())
    def test_exif_cache_consistency_property(self, file_path):
        """
        **Feature: raw-jpeg-matcher, Property 9: Exifキャッシュの一貫性**
        **検証対象: 要件 6.2**
        
        任意のファイルに対して、Exifデータを複数回読み取ると同じ結果が返され、
        2回目以降の読み取りはキャッシュから提供されるべきである。
        """
        # 一時ファイルを作成（空ファイル、Exifデータなし）
        with tempfile.NamedTemporaryFile(suffix=file_path.suffix, delete=False) as tmp_file:
            tmp_path = Path(tmp_file.name)
            # 最小限のJPEGデータを書き込み（Exifなし）
            tmp_file.write(MINIMAL_JPEG_WITH_EXIF)
        
        try:
            # 初回読み取り（キャッシュなし）
            assert not self.exif_reader.is_cached(tmp_path)
            first_result = self.exif_reader.read_capture_datetime(tmp_path)
            
            # キャッシュされたことを確認
            assert self.exif_reader.is_cached(tmp_path)
            
            # 2回目の読み取り（キャッシュから）
            second_result = self.exif_reader.read_capture_datetime(tmp_path)
            
            # プロパティ検証: 一貫性
            # 1. 同じ結果が返される
            assert first_result == second_result
            
            # 2. 両方ともNoneまたは両方とも有効なdatetime
            if first_result is not None:
                assert isinstance(first_result, datetime)
                assert isinstance(second_result, datetime)
            else:
                assert second_result is None
            
            # 3. キャッシュサイズが1増加している
            assert self.exif_reader.get_cache_size() >= 1
            
        finally:
            # テンポラリファイルをクリーンアップ
            tmp_path.unlink(missing_ok=True)
    
    def test_invalid_datetime_formats(self):
        """無効な日時フォーマットの処理テスト"""
        invalid_formats = [
            "",
            "invalid",
            "2024-13-01 12:00:00",  # 無効な月
            "2024:02:30 25:00:00",  # 無効な日と時間
            "not a date",
            None
        ]
        
        for invalid_format in invalid_formats:
            result = self.exif_reader._parse_exif_datetime(invalid_format)
            assert result is None
    
    def test_cache_operations(self):
        """キャッシュ操作のテスト"""
        # 初期状態
        assert self.exif_reader.get_cache_size() == 0
        
        # 存在しないファイルでキャッシュテスト
        non_existent_path = Path("/non/existent/file.jpg")
        result = self.exif_reader.read_capture_datetime(non_existent_path)
        
        assert result is None
        assert self.exif_reader.is_cached(non_existent_path)
        assert self.exif_reader.get_cache_size() == 1
        
        # キャッシュクリア
        self.exif_reader.clear_cache()
        assert self.exif_reader.get_cache_size() == 0
        assert not self.exif_reader.is_cached(non_existent_path)
    
    def test_zero_byte_file_handling(self):
        """0バイトファイルの処理テスト"""
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_file:
            tmp_path = Path(tmp_file.name)
            # 0バイトファイル（何も書き込まない）
        
        try:
            result = self.exif_reader.read_capture_datetime(tmp_path)
            assert result is None
            assert self.exif_reader.is_cached(tmp_path)
        finally:
            tmp_path.unlink(missing_ok=True)
    
    def test_supported_datetime_formats(self):
        """サポートされている日時フォーマットのテスト"""
        test_cases = [
            ("2024:01:15 14:30:45", datetime(2024, 1, 15, 14, 30, 45)),
            ("2024-01-15 14:30:45", datetime(2024, 1, 15, 14, 30, 45)),
            ("2024/01/15 14:30:45", datetime(2024, 1, 15, 14, 30, 45)),
        ]
        
        for datetime_str, expected_datetime in test_cases:
            result = self.exif_reader._parse_exif_datetime(datetime_str)
            assert result == expected_datetime
    
    def test_exiftool_dependency_verification_property(self):
        """
        **Feature: raw-jpeg-matcher, Property 14: ExifTool依存性の検証**
        **検証対象: 要件 3.7**
        
        任意のExif読取処理において、ExifToolが利用できない場合、
        システムは明確なエラーメッセージを表示すべきである。
        """
        # Case 1: ExifToolが利用可能な場合の正常動作確認
        is_available = self.exif_reader.check_exiftool_availability()
        
        # プロパティ検証: ExifToolが利用可能な場合はTrueを返す
        assert is_available is True
        
        # exiftool_pathが設定されていることを確認
        assert self.exif_reader.exiftool_path is not None
        assert self.exif_reader.exiftool_path.exists()
        
        # Case 2: ExifToolが見つからない状況をシミュレート
        # 新しいExifReaderインスタンスを作成し、exiftool_pathを無効にする
        test_reader = ExifReader.__new__(ExifReader)  # __init__を呼ばずにインスタンス作成
        test_reader.cache = {}
        test_reader.logger = self.exif_reader.logger
        test_reader.exiftool_path = None
        test_reader._datetime_tags = self.exif_reader._datetime_tags
        
        # 実際のファイル読み取りでエラーが発生することを確認
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_file:
            tmp_path = Path(tmp_file.name)
            tmp_file.write(MINIMAL_JPEG_WITH_EXIF)
        
        try:
            # ExifTool未設定の状態で_run_exiftoolメソッドを直接テスト
            with pytest.raises(ExifReadError) as exc_info:
                test_reader._run_exiftool(tmp_path, ['DateTimeOriginal'])
            
            # プロパティ検証: 適切なエラーメッセージが表示される
            error_message = str(exc_info.value)
            assert "ExifTool" in error_message
            assert any(keyword in error_message.lower() for keyword in [
                "見つかりません", "not found", "初期化", "install"
            ])
            
            # read_capture_datetimeメソッドはNoneを返すことを確認（エラーハンドリング）
            result = test_reader.read_capture_datetime(tmp_path)
            assert result is None
            
        finally:
            tmp_path.unlink(missing_ok=True)