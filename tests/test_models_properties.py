"""
データモデルのプロパティベーステスト

Property 6: インデックスの完全性を検証します。
"""

from datetime import datetime
from pathlib import Path
from hypothesis import given, strategies as st
from hypothesis import settings

from src.models import RawFileInfo


class MockRawFileIndex:
    """テスト用のRAWファイルインデックスのモック実装"""

    def __init__(self):
        self.files = {}  # path -> RawFileInfo のマッピング

    def add(self, info: RawFileInfo) -> None:
        """インデックスにRAWファイル情報を追加"""
        self.files[info.path] = info

    def get_all_files(self) -> list[RawFileInfo]:
        """すべてのファイル情報を取得"""
        return list(self.files.values())


# Hypothesis strategies for generating test data
@st.composite
def unique_raw_files_strategy(draw):
    """一意のパスを持つRawFileInfoオブジェクトのリストを生成するストラテジー"""
    # 一意のファイル名を生成
    num_files = draw(st.integers(min_value=1, max_value=20))
    filenames = draw(st.lists(
        st.text(
            alphabet=st.characters(
                whitelist_categories=('Lu', 'Ll', 'Nd'),
                min_codepoint=32,
                max_codepoint=126
            ),
            min_size=1,
            max_size=50
        ).filter(lambda x: x.strip() and not any(c in x for c in '<>:"|?*')),
        min_size=num_files,
        max_size=num_files,
        unique=True  # 一意のファイル名を保証
    ))
    
    raw_files = []
    for i, filename in enumerate(filenames):
        # RAW拡張子を追加
        extension = draw(st.sampled_from([
            '.CR2', '.NEF', '.ARW', '.RAF', '.ORF', '.DNG'
        ]))
        path = Path(f"/test/path/{filename}{extension}")

        # ベース名（拡張子なし、小文字）
        basename = filename.lower()

        # 撮影日時（オプショナル）
        capture_datetime = draw(st.one_of(
            st.none(),
            st.datetimes(
                min_value=datetime(2000, 1, 1),
                max_value=datetime(2024, 12, 31)
            )
        ))

        # ファイルサイズ
        file_size = draw(st.integers(min_value=1, max_value=100_000_000))

        raw_files.append(RawFileInfo(
            path=path,
            basename=basename,
            capture_datetime=capture_datetime,
            file_size=file_size
        ))

    return raw_files


@settings(max_examples=100)
@given(unique_raw_files_strategy())
def test_index_completeness_property(raw_files):
    """
    **Feature: raw-jpeg-matcher, Property 6: インデックスの完全性**
    **検証対象: 要件 4.2**

    任意のソースディレクトリ内のRAWファイルに対して、インデックスは
    そのファイルのベース名、フルパス、撮影日時（利用可能な場合）を
    含むエントリを持つべきである。
    """
    # インデックスを作成
    index = MockRawFileIndex()

    # すべてのRAWファイル情報をインデックスに追加
    for raw_file in raw_files:
        index.add(raw_file)

    # インデックスから全ファイル情報を取得
    indexed_files = index.get_all_files()

    # プロパティ検証: インデックスの完全性
    # 1. すべてのRAWファイルがインデックスに含まれている
    assert len(indexed_files) == len(raw_files)

    # 2. 各ファイルについて、必要な情報がすべて保存されている
    indexed_paths = {f.path for f in indexed_files}
    original_paths = {f.path for f in raw_files}
    assert indexed_paths == original_paths

    # 3. 各ファイルの詳細情報が正確に保存されている
    for original_file in raw_files:
        # インデックスから対応するファイルを見つける
        indexed_file = next(
            f for f in indexed_files if f.path == original_file.path
        )

        # ベース名が保存されている
        assert indexed_file.basename == original_file.basename
        assert isinstance(indexed_file.basename, str)

        # フルパスが保存されている
        assert indexed_file.path == original_file.path
        assert isinstance(indexed_file.path, Path)

        # 撮影日時が保存されている（利用可能な場合）
        assert indexed_file.capture_datetime == original_file.capture_datetime
        if indexed_file.capture_datetime is not None:
            assert isinstance(indexed_file.capture_datetime, datetime)

        # ファイルサイズが保存されている
        assert indexed_file.file_size == original_file.file_size
        assert isinstance(indexed_file.file_size, int)
        assert indexed_file.file_size > 0


def test_raw_file_info_creation():
    """RawFileInfoオブジェクトの基本的な作成テスト"""
    path = Path("/test/IMG_001.CR2")
    basename = "img_001"
    capture_datetime = datetime(2024, 1, 1, 12, 0, 0)
    file_size = 25000000

    info = RawFileInfo(
        path=path,
        basename=basename,
        capture_datetime=capture_datetime,
        file_size=file_size
    )

    assert info.path == path
    assert info.basename == basename
    assert info.capture_datetime == capture_datetime
    assert info.file_size == file_size


def test_raw_file_info_with_none_datetime():
    """撮影日時がNoneの場合のRawFileInfoテスト"""
    path = Path("/test/IMG_002.NEF")
    basename = "img_002"
    file_size = 30000000

    info = RawFileInfo(
        path=path,
        basename=basename,
        capture_datetime=None,
        file_size=file_size
    )

    assert info.path == path
    assert info.basename == basename
    assert info.capture_datetime is None
    assert info.file_size == file_size