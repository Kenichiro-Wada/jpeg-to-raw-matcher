"""
Matcherのプロパティベーステスト

Property 5: 日時マッチングの厳密性を検証します。
"""

from datetime import datetime, timedelta
from pathlib import Path
from hypothesis import given, strategies as st
from hypothesis import settings
from unittest.mock import Mock

from src.models import RawFileInfo, JpegFileInfo, MatchResult
from src.matcher import Matcher
from src.indexer import RawFileIndex


class MockExifReader:
    """テスト用のExifReaderのモック実装"""
    
    def __init__(self):
        self.datetime_map = {}  # Path -> datetime のマッピング
    
    def set_datetime(self, file_path: Path, capture_datetime: datetime) -> None:
        """ファイルの撮影日時を設定"""
        self.datetime_map[file_path] = capture_datetime
    
    def read_capture_datetime(self, file_path: Path) -> datetime:
        """ファイルから撮影日時を読み取る（モック）"""
        return self.datetime_map.get(file_path)


# Hypothesis strategies for generating test data
@st.composite
def datetime_matching_scenario_strategy(draw):
    """日時マッチングのテストシナリオを生成するストラテジー"""
    # 基準となる撮影日時
    base_datetime = draw(st.datetimes(
        min_value=datetime(2020, 1, 1),
        max_value=datetime(2024, 12, 31)
    ))
    
    # ベース名
    basename = draw(st.text(
        alphabet=st.characters(
            whitelist_categories=('Lu', 'Ll', 'Nd'),
            min_codepoint=32,
            max_codepoint=126
        ),
        min_size=1,
        max_size=20
    ).filter(lambda x: x.strip() and not any(c in x for c in '<>:"|?*')))
    
    # JPEGファイル情報
    jpeg_path = Path(f"/jpeg/{basename}.jpg")
    jpeg_info = JpegFileInfo(
        path=jpeg_path,
        basename=basename.lower(),
        capture_datetime=base_datetime
    )
    
    # RAWファイル候補を生成
    num_raw_files = draw(st.integers(min_value=1, max_value=5))
    raw_files = []
    
    # 少なくとも1つは完全一致するRAWファイルを含める
    exact_match_raw = RawFileInfo(
        path=Path(f"/raw/{basename}_exact.CR2"),
        basename=basename.lower(),
        capture_datetime=base_datetime,  # 完全一致
        file_size=draw(st.integers(min_value=1000000, max_value=50000000))
    )
    raw_files.append(exact_match_raw)
    
    # 他のRAWファイルは異なる日時を持つ
    for i in range(num_raw_files - 1):
        # 異なる日時を生成（完全一致を避ける）
        different_datetime = draw(st.datetimes(
            min_value=datetime(2020, 1, 1),
            max_value=datetime(2024, 12, 31)
        ).filter(lambda dt: dt != base_datetime))
        
        raw_file = RawFileInfo(
            path=Path(f"/raw/{basename}_{i}.CR2"),
            basename=basename.lower(),
            capture_datetime=different_datetime,
            file_size=draw(st.integers(min_value=1000000, max_value=50000000))
        )
        raw_files.append(raw_file)
    
    return {
        'jpeg_info': jpeg_info,
        'raw_files': raw_files,
        'expected_match_path': exact_match_raw.path
    }


@st.composite
def no_datetime_match_scenario_strategy(draw):
    """日時が一致しないシナリオを生成するストラテジー"""
    # 基準となる撮影日時
    jpeg_datetime = draw(st.datetimes(
        min_value=datetime(2020, 1, 1),
        max_value=datetime(2024, 12, 31)
    ))
    
    # ベース名
    basename = draw(st.text(
        alphabet=st.characters(
            whitelist_categories=('Lu', 'Ll', 'Nd'),
            min_codepoint=32,
            max_codepoint=126
        ),
        min_size=1,
        max_size=20
    ).filter(lambda x: x.strip() and not any(c in x for c in '<>:"|?*')))
    
    # JPEGファイル情報
    jpeg_path = Path(f"/jpeg/{basename}.jpg")
    jpeg_info = JpegFileInfo(
        path=jpeg_path,
        basename=basename.lower(),
        capture_datetime=jpeg_datetime
    )
    
    # すべてのRAWファイルが異なる日時を持つ
    num_raw_files = draw(st.integers(min_value=1, max_value=3))
    raw_files = []
    
    for i in range(num_raw_files):
        # JPEGとは異なる日時を生成
        different_datetime = draw(st.datetimes(
            min_value=datetime(2020, 1, 1),
            max_value=datetime(2024, 12, 31)
        ).filter(lambda dt: dt != jpeg_datetime))
        
        raw_file = RawFileInfo(
            path=Path(f"/raw/{basename}_{i}.CR2"),
            basename=basename.lower(),
            capture_datetime=different_datetime,
            file_size=draw(st.integers(min_value=1000000, max_value=50000000))
        )
        raw_files.append(raw_file)
    
    return {
        'jpeg_info': jpeg_info,
        'raw_files': raw_files
    }


@settings(max_examples=100)
@given(datetime_matching_scenario_strategy())
def test_datetime_matching_strictness_property_exact_match(scenario):
    """
    **Feature: raw-jpeg-matcher, Property 5: 日時マッチングの厳密性**
    **検証対象: 要件 3.3**

    任意の撮影日時の値を持つファイルのペアに対して、システムは
    日時の値が完全に一致する場合のみマッチと見なすべきである。
    
    このテストは完全一致のケースを検証します。
    """
    # テストデータを取得
    jpeg_info = scenario['jpeg_info']
    raw_files = scenario['raw_files']
    expected_match_path = scenario['expected_match_path']
    
    # インデックスを作成してRAWファイルを追加
    index = RawFileIndex()
    for raw_file in raw_files:
        index.add(raw_file)
    
    # モックExifReaderを作成
    mock_exif_reader = MockExifReader()
    mock_exif_reader.set_datetime(jpeg_info.path, jpeg_info.capture_datetime)
    
    # Matcherを作成
    matcher = Matcher(mock_exif_reader, index)
    
    # マッチングを実行
    matches = matcher.find_matches([jpeg_info.path])
    
    # プロパティ検証: 日時マッチングの厳密性
    # 1. 完全一致する日時を持つRAWファイルが存在する場合、必ずマッチする
    assert len(matches) == 1, f"完全一致する日時があるのにマッチしませんでした: JPEG={jpeg_info.capture_datetime}"
    
    match = matches[0]
    
    # 2. マッチしたRAWファイルは完全一致する日時を持つもの
    assert match.raw_path == expected_match_path, f"期待されたRAWファイルとマッチしませんでした"
    
    # 3. マッチ方法は日時とベース名の両方
    assert match.match_method == 'basename_and_datetime', f"マッチ方法が期待と異なります: {match.match_method}"
    
    # 4. JPEGパスが正しく設定されている
    assert match.jpeg_path == jpeg_info.path


@settings(max_examples=100)
@given(no_datetime_match_scenario_strategy())
def test_datetime_matching_strictness_property_no_match(scenario):
    """
    **Feature: raw-jpeg-matcher, Property 5: 日時マッチングの厳密性**
    **検証対象: 要件 3.3**

    任意の撮影日時の値を持つファイルのペアに対して、システムは
    日時の値が完全に一致する場合のみマッチと見なすべきである。
    
    このテストは完全一致しないケースを検証します。
    """
    # テストデータを取得
    jpeg_info = scenario['jpeg_info']
    raw_files = scenario['raw_files']
    
    # インデックスを作成してRAWファイルを追加
    index = RawFileIndex()
    for raw_file in raw_files:
        index.add(raw_file)
    
    # モックExifReaderを作成
    mock_exif_reader = MockExifReader()
    mock_exif_reader.set_datetime(jpeg_info.path, jpeg_info.capture_datetime)
    
    # Matcherを作成
    matcher = Matcher(mock_exif_reader, index)
    
    # マッチングを実行
    matches = matcher.find_matches([jpeg_info.path])
    
    # プロパティ検証: 日時マッチングの厳密性
    # 完全一致する日時を持つRAWファイルが存在しない場合、マッチしない
    assert len(matches) == 0, f"日時が一致しないのにマッチしました: JPEG={jpeg_info.capture_datetime}, RAW日時={[r.capture_datetime for r in raw_files]}"


@st.composite
def basename_only_matching_scenario_strategy(draw):
    """JPEGに撮影日時がない場合のシナリオを生成するストラテジー"""
    # ベース名
    basename = draw(st.text(
        alphabet=st.characters(
            whitelist_categories=('Lu', 'Ll', 'Nd'),
            min_codepoint=32,
            max_codepoint=126
        ),
        min_size=1,
        max_size=20
    ).filter(lambda x: x.strip() and not any(c in x for c in '<>:"|?*')))
    
    # JPEGファイル情報（撮影日時なし）
    jpeg_path = Path(f"/jpeg/{basename}.jpg")
    jpeg_info = JpegFileInfo(
        path=jpeg_path,
        basename=basename.lower(),
        capture_datetime=None  # 撮影日時なし
    )
    
    # RAWファイル候補を生成
    num_raw_files = draw(st.integers(min_value=1, max_value=3))
    raw_files = []
    
    for i in range(num_raw_files):
        # 任意の日時（またはNone）
        capture_datetime = draw(st.one_of(
            st.none(),
            st.datetimes(
                min_value=datetime(2020, 1, 1),
                max_value=datetime(2024, 12, 31)
            )
        ))
        
        raw_file = RawFileInfo(
            path=Path(f"/raw/{basename}_{i}.CR2"),
            basename=basename.lower(),
            capture_datetime=capture_datetime,
            file_size=draw(st.integers(min_value=1000000, max_value=50000000))
        )
        raw_files.append(raw_file)
    
    return {
        'jpeg_info': jpeg_info,
        'raw_files': raw_files
    }


@settings(max_examples=100)
@given(basename_only_matching_scenario_strategy())
def test_basename_only_matching_when_no_jpeg_datetime(scenario):
    """
    JPEGに撮影日時がない場合のベース名のみマッチングをテスト
    
    これは厳密性プロパティの補完テストです。
    """
    # テストデータを取得
    jpeg_info = scenario['jpeg_info']
    raw_files = scenario['raw_files']
    
    # インデックスを作成してRAWファイルを追加
    index = RawFileIndex()
    for raw_file in raw_files:
        index.add(raw_file)
    
    # モックExifReaderを作成（JPEGの撮影日時はNone）
    mock_exif_reader = MockExifReader()
    mock_exif_reader.set_datetime(jpeg_info.path, None)
    
    # Matcherを作成
    matcher = Matcher(mock_exif_reader, index)
    
    # マッチングを実行
    matches = matcher.find_matches([jpeg_info.path])
    
    # プロパティ検証: JPEGに撮影日時がない場合の動作
    # 1. ベース名が一致するRAWファイルがある場合、マッチする
    assert len(matches) == 1, f"ベース名が一致するRAWファイルがあるのにマッチしませんでした"
    
    match = matches[0]
    
    # 2. マッチしたRAWファイルは同じベース名を持つ
    matched_raw = next(r for r in raw_files if r.path == match.raw_path)
    assert matched_raw.basename == jpeg_info.basename
    
    # 3. マッチ方法はベース名のみ
    assert match.match_method == 'basename_only', f"マッチ方法が期待と異なります: {match.match_method}"


def test_matcher_basic_functionality():
    """Matcherの基本機能テスト"""
    # テストデータを作成
    jpeg_path = Path("/test/IMG_001.jpg")
    raw_path = Path("/test/IMG_001.CR2")
    capture_datetime = datetime(2024, 1, 1, 12, 0, 0)
    
    # RAWファイル情報
    raw_info = RawFileInfo(
        path=raw_path,
        basename="img_001",
        capture_datetime=capture_datetime,
        file_size=25000000
    )
    
    # インデックスを作成
    index = RawFileIndex()
    index.add(raw_info)
    
    # モックExifReaderを作成
    mock_exif_reader = MockExifReader()
    mock_exif_reader.set_datetime(jpeg_path, capture_datetime)
    
    # Matcherを作成
    matcher = Matcher(mock_exif_reader, index)
    
    # マッチングを実行
    matches = matcher.find_matches([jpeg_path])
    
    # 結果を検証
    assert len(matches) == 1
    match = matches[0]
    assert match.jpeg_path == jpeg_path
    assert match.raw_path == raw_path
    assert match.match_method == 'basename_and_datetime'


def test_matcher_no_match():
    """マッチしない場合のテスト"""
    # テストデータを作成
    jpeg_path = Path("/test/IMG_001.jpg")
    raw_path = Path("/test/IMG_002.CR2")  # 異なるベース名
    capture_datetime = datetime(2024, 1, 1, 12, 0, 0)
    
    # RAWファイル情報
    raw_info = RawFileInfo(
        path=raw_path,
        basename="img_002",  # 異なるベース名
        capture_datetime=capture_datetime,
        file_size=25000000
    )
    
    # インデックスを作成
    index = RawFileIndex()
    index.add(raw_info)
    
    # モックExifReaderを作成
    mock_exif_reader = MockExifReader()
    mock_exif_reader.set_datetime(jpeg_path, capture_datetime)
    
    # Matcherを作成
    matcher = Matcher(mock_exif_reader, index)
    
    # マッチングを実行
    matches = matcher.find_matches([jpeg_path])
    
    # 結果を検証（マッチしない）
    assert len(matches) == 0