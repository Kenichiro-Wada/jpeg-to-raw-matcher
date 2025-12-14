"""
FileScannerのプロパティベーステスト

Property 3: ベース名抽出の一貫性を検証します。
"""

import tempfile
from pathlib import Path
from hypothesis import given, strategies as st
from hypothesis import settings
import pytest

from src.file_scanner import FileScanner
from src.exceptions import ValidationError


# ファイルシステムで安全に使用できる文字のストラテジー
safe_filename_strategy = st.text(
    alphabet=st.characters(
        whitelist_categories=('Lu', 'Ll', 'Nd'),
        min_codepoint=32,
        max_codepoint=126
    ),
    min_size=1,
    max_size=50
).filter(lambda x: x.strip() and not any(c in x for c in '<>:"|?*\\/.'))


@st.composite
def file_with_extension_strategy(draw):
    """ファイル名と拡張子のペアを生成するストラテジー"""
    # ベースファイル名を生成
    basename = draw(safe_filename_strategy)
    
    # 拡張子を選択（RAWまたはJPEG）
    extension = draw(st.sampled_from([
        '.CR2', '.cr2', '.CR3', '.cr3', '.NEF', '.nef', 
        '.ARW', '.arw', '.RAF', '.raf', '.ORF', '.orf',
        '.RW2', '.rw2', '.PEF', '.pef', '.DNG', '.dng',
        '.RWL', '.rwl', '.3FR', '.3fr', '.IIQ', '.iiq',
        '.JPG', '.jpg', '.JPEG', '.jpeg'
    ]))
    
    return basename, extension


@st.composite
def mixed_case_filename_pairs_strategy(draw):
    """同じベース名で大文字小文字が異なるファイル名ペアを生成"""
    # ベースファイル名を生成（英字を含むものに限定）
    base_name = draw(st.text(
        alphabet=st.characters(
            whitelist_categories=('Lu', 'Ll'),  # 英字のみ
            min_codepoint=65,  # 'A'
            max_codepoint=122  # 'z'
        ),
        min_size=2,
        max_size=20
    ).filter(lambda x: x.strip() and x.lower() != x.upper()))  # 大文字小文字が異なることを保証
    
    # 大文字小文字のバリエーションを作成
    variations = set()
    variations.add(base_name)
    variations.add(base_name.upper())
    variations.add(base_name.lower())
    variations.add(base_name.capitalize())
    
    # 少なくとも2つの異なるバリエーションがあることを確認
    variations_list = list(variations)
    if len(variations_list) < 2:
        # フォールバック: 手動で異なるバリエーションを作成
        variations_list = [base_name.lower(), base_name.upper()]
    
    # 2つの異なるバリエーションを選択
    selected = draw(st.lists(
        st.sampled_from(variations_list),
        min_size=2,
        max_size=2,
        unique=True
    ))
    
    return selected[0], selected[1]


@settings(max_examples=100)
@given(file_with_extension_strategy())
def test_basename_extraction_consistency_property(file_data):
    """
    **Feature: raw-jpeg-matcher, Property 3: ベース名抽出の一貫性**
    **検証対象: 要件 2.1, 2.2, 2.3**

    任意の拡張子を持つファイルパスに対して、ベース名の抽出は拡張子を除去し、
    大文字小文字を区別しない比較を行うことで、同じベース名を持つが
    大文字小文字が異なるファイルをマッチと見なすべきである。
    """
    basename, extension = file_data
    
    # FileScannerインスタンスを作成
    scanner = FileScanner()
    
    # ファイルパスを作成
    file_path = Path(f"/test/path/{basename}{extension}")
    
    # ベース名を抽出
    extracted_basename = scanner.get_basename(file_path)
    
    # プロパティ検証
    # 1. 抽出されたベース名は文字列であるべき
    assert isinstance(extracted_basename, str)
    
    # 2. 抽出されたベース名は小文字であるべき
    assert extracted_basename == extracted_basename.lower()
    
    # 3. 抽出されたベース名は元のベース名の小文字版と一致するべき
    assert extracted_basename == basename.lower()
    
    # 4. 拡張子は含まれていないべき
    assert extension.lower() not in extracted_basename
    
    # 5. 空文字列ではないべき（元のベース名が有効な場合）
    if basename.strip():
        assert len(extracted_basename) > 0


@settings(max_examples=100)
@given(mixed_case_filename_pairs_strategy())
def test_case_insensitive_basename_matching_property(filename_pair):
    """
    大文字小文字を区別しないベース名マッチングのプロパティテスト
    
    同じベース名を持つが大文字小文字が異なるファイルは、
    同じベース名として認識されるべきである。
    """
    filename1, filename2 = filename_pair
    
    # FileScannerインスタンスを作成
    scanner = FileScanner()
    
    # 異なる拡張子でファイルパスを作成
    file_path1 = Path(f"/test/path/{filename1}.CR2")
    file_path2 = Path(f"/test/path/{filename2}.jpg")
    
    # ベース名を抽出
    basename1 = scanner.get_basename(file_path1)
    basename2 = scanner.get_basename(file_path2)
    
    # プロパティ検証: 大文字小文字を区別しない比較
    # 同じベース名（大文字小文字の違いを除く）のファイルは同じベース名を持つべき
    if filename1.lower() == filename2.lower():
        assert basename1 == basename2
    
    # 両方とも小文字であるべき
    assert basename1 == basename1.lower()
    assert basename2 == basename2.lower()


def test_file_type_detection_consistency():
    """ファイルタイプ検出の一貫性テスト"""
    scanner = FileScanner()
    
    # RAWファイルのテスト
    raw_extensions = ['.CR2', '.cr2', '.NEF', '.nef', '.ARW', '.arw']
    for ext in raw_extensions:
        file_path = Path(f"/test/image{ext}")
        assert scanner.is_raw_file(file_path), f"RAWファイル検出失敗: {ext}"
        assert not scanner.is_jpeg_file(file_path), f"JPEG誤検出: {ext}"
    
    # JPEGファイルのテスト
    jpeg_extensions = ['.JPG', '.jpg', '.JPEG', '.jpeg']
    for ext in jpeg_extensions:
        file_path = Path(f"/test/image{ext}")
        assert scanner.is_jpeg_file(file_path), f"JPEGファイル検出失敗: {ext}"
        assert not scanner.is_raw_file(file_path), f"RAW誤検出: {ext}"
    
    # 未対応拡張子のテスト
    unsupported_extensions = ['.txt', '.pdf', '.png', '.tiff']
    for ext in unsupported_extensions:
        file_path = Path(f"/test/file{ext}")
        assert not scanner.is_raw_file(file_path), f"RAW誤検出: {ext}"
        assert not scanner.is_jpeg_file(file_path), f"JPEG誤検出: {ext}"


def test_scanner_with_real_directory_structure():
    """実際のディレクトリ構造でのスキャナーテスト"""
    scanner = FileScanner()
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # テスト用ファイルを作成
        test_files = [
            "IMG_001.CR2", "IMG_001.jpg",
            "IMG_002.NEF", "IMG_002.jpeg",
            "IMG_003.ARW", "IMG_003.JPG",
            "document.txt", "readme.md"
        ]
        
        for filename in test_files:
            file_path = temp_path / filename
            file_path.write_text("test content")
        
        # サブディレクトリも作成
        sub_dir = temp_path / "subdir"
        sub_dir.mkdir()
        (sub_dir / "IMG_004.DNG").write_text("test content")
        (sub_dir / "IMG_004.JPEG").write_text("test content")
        
        # RAWファイルをスキャン（非再帰）
        raw_files = scanner.scan_raw_files(temp_path, recursive=False)
        expected_raw = ["IMG_001.CR2", "IMG_002.NEF", "IMG_003.ARW"]
        assert len(raw_files) == len(expected_raw)
        for expected in expected_raw:
            assert any(f.name == expected for f in raw_files)
        
        # JPEGファイルをスキャン（非再帰）
        jpeg_files = scanner.scan_jpeg_files(temp_path, recursive=False)
        expected_jpeg = ["IMG_001.jpg", "IMG_002.jpeg", "IMG_003.JPG"]
        assert len(jpeg_files) == len(expected_jpeg)
        for expected in expected_jpeg:
            assert any(f.name == expected for f in jpeg_files)
        
        # 再帰的スキャン
        raw_files_recursive = scanner.scan_raw_files(temp_path, recursive=True)
        assert len(raw_files_recursive) == 4  # 3 + 1 (subdir)
        
        jpeg_files_recursive = scanner.scan_jpeg_files(temp_path, recursive=True)
        assert len(jpeg_files_recursive) == 4  # 3 + 1 (subdir)


def test_scanner_with_invalid_directory():
    """無効なディレクトリでのスキャナーテスト"""
    scanner = FileScanner()
    
    # 存在しないディレクトリ
    non_existent = Path("/non/existent/directory")
    
    with pytest.raises(ValidationError):
        scanner.scan_raw_files(non_existent)
    
    with pytest.raises(ValidationError):
        scanner.scan_jpeg_files(non_existent)


def test_basename_extraction_edge_cases():
    """ベース名抽出のエッジケーステスト"""
    scanner = FileScanner()
    
    # 複数のドットを含むファイル名
    file_path = Path("/test/my.photo.backup.CR2")
    basename = scanner.get_basename(file_path)
    assert basename == "my.photo.backup"
    
    # 数字のみのファイル名
    file_path = Path("/test/12345.NEF")
    basename = scanner.get_basename(file_path)
    assert basename == "12345"
    
    # 特殊文字を含むファイル名（ファイルシステムで許可される範囲）
    file_path = Path("/test/IMG_001-final.jpg")
    basename = scanner.get_basename(file_path)
    assert basename == "img_001-final"


def test_file_extensions_completeness():
    """ファイル拡張子の完全性テスト"""
    scanner = FileScanner()
    
    # 設計ドキュメントで指定されたすべての拡張子が含まれているかチェック
    expected_raw_extensions = {
        '.cr2', '.CR2', '.cr3', '.CR3', '.nef', '.NEF', 
        '.arw', '.ARW', '.raf', '.RAF', '.orf', '.ORF',
        '.rw2', '.RW2', '.pef', '.PEF', '.dng', '.DNG',
        '.rwl', '.RWL', '.3fr', '.3FR', '.iiq', '.IIQ'
    }
    
    expected_jpeg_extensions = {
        '.jpg', '.JPG', '.jpeg', '.JPEG'
    }
    
    # RAW拡張子の確認
    assert scanner.RAW_EXTENSIONS == expected_raw_extensions
    
    # JPEG拡張子の確認
    assert scanner.JPEG_EXTENSIONS == expected_jpeg_extensions
    
    # 大文字小文字両方が含まれていることを確認
    for ext in expected_raw_extensions:
        if ext.islower():
            assert ext.upper() in expected_raw_extensions
        else:
            assert ext.lower() in expected_raw_extensions
    
    for ext in expected_jpeg_extensions:
        if ext.islower():
            assert ext.upper() in expected_jpeg_extensions
        else:
            assert ext.lower() in expected_jpeg_extensions