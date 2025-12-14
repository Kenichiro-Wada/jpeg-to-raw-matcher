"""
Copierのプロパティベーステスト

Property 7: ファイルコピーの保存性を検証します。
"""

import tempfile
import shutil
from pathlib import Path
from hypothesis import given, strategies as st
from hypothesis import settings
import hashlib

from src.models import MatchResult
from src.copier import Copier


def calculate_file_hash(file_path: Path) -> str:
    """ファイルのハッシュ値を計算"""
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


@st.composite
def file_copy_scenario_strategy(draw):
    """ファイルコピーのテストシナリオを生成するストラテジー"""
    # ファイル名を生成
    basename = draw(st.text(
        alphabet=st.characters(
            whitelist_categories=('Lu', 'Ll', 'Nd'),
            min_codepoint=32,
            max_codepoint=126
        ),
        min_size=1,
        max_size=20
    ).filter(lambda x: x.strip() and not any(c in x for c in '<>:"|?*')))
    
    # ファイル内容を生成（バイナリデータ）
    file_content = draw(st.binary(min_size=100, max_size=10000))
    
    # RAW拡張子を選択
    raw_extension = draw(st.sampled_from(['.CR2', '.NEF', '.ARW', '.RAF', '.ORF']))
    
    return {
        'basename': basename,
        'file_content': file_content,
        'raw_extension': raw_extension
    }


@settings(max_examples=100)
@given(file_copy_scenario_strategy())
def test_file_copy_preservation_property(scenario):
    """
    **Feature: raw-jpeg-matcher, Property 7: ファイルコピーの保存性**
    **検証対象: 要件 5.1, 5.2**

    任意のターゲットディレクトリにコピーされたマッチしたRAWファイルに対して、
    コピーされたファイルは元のファイルと同じファイル名と同じファイル内容を持つべきである。
    """
    # テストデータを取得
    basename = scenario['basename']
    file_content = scenario['file_content']
    raw_extension = scenario['raw_extension']
    
    # 一時ディレクトリを作成
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        source_dir = temp_path / "source"
        target_dir = temp_path / "target"
        
        source_dir.mkdir()
        target_dir.mkdir()
        
        # ソースファイルを作成
        jpeg_filename = f"{basename}.jpg"
        raw_filename = f"{basename}{raw_extension}"
        
        jpeg_path = source_dir / jpeg_filename
        raw_path = source_dir / raw_filename
        
        # ファイル内容を書き込み
        jpeg_path.write_bytes(b"fake jpeg content")
        raw_path.write_bytes(file_content)
        
        # 元ファイルのハッシュ値を計算
        original_hash = calculate_file_hash(raw_path)
        original_size = raw_path.stat().st_size
        
        # MatchResultを作成
        match = MatchResult(
            jpeg_path=jpeg_path,
            raw_path=raw_path,
            match_method='basename_and_datetime'
        )
        
        # Copierを作成してコピー実行
        copier = Copier()
        result = copier.copy_files([match], target_dir)
        
        # プロパティ検証: ファイルコピーの保存性
        
        # 1. コピーが成功している
        assert result.success == 1, f"コピーが失敗しました: success={result.success}, errors={result.errors}"
        assert result.failed == 0, f"コピーエラーが発生しました: failed={result.failed}, errors={result.errors}"
        
        # 2. コピー先ファイルが存在する
        copied_file_path = target_dir / raw_filename
        assert copied_file_path.exists(), f"コピー先ファイルが存在しません: {copied_file_path}"
        
        # 3. ファイル名が保持されている
        assert copied_file_path.name == raw_filename, f"ファイル名が保持されていません: 期待={raw_filename}, 実際={copied_file_path.name}"
        
        # 4. ファイル内容が同じ（ハッシュ値で比較）
        copied_hash = calculate_file_hash(copied_file_path)
        assert copied_hash == original_hash, f"ファイル内容が異なります: 元={original_hash}, コピー={copied_hash}"
        
        # 5. ファイルサイズが同じ
        copied_size = copied_file_path.stat().st_size
        assert copied_size == original_size, f"ファイルサイズが異なります: 元={original_size}, コピー={copied_size}"


@st.composite
def multiple_files_scenario_strategy(draw):
    """複数ファイルのコピーシナリオを生成するストラテジー"""
    # ファイル数を生成
    num_files = draw(st.integers(min_value=1, max_value=5))
    
    files = []
    for i in range(num_files):
        basename = draw(st.text(
            alphabet=st.characters(
                whitelist_categories=('Lu', 'Ll', 'Nd'),
                min_codepoint=32,
                max_codepoint=126
            ),
            min_size=1,
            max_size=15
        ).filter(lambda x: x.strip() and not any(c in x for c in '<>:"|?*')))
        
        # 重複を避けるためにインデックスを追加
        unique_basename = f"{basename}_{i}"
        
        file_content = draw(st.binary(min_size=50, max_size=5000))
        raw_extension = draw(st.sampled_from(['.CR2', '.NEF', '.ARW']))
        
        files.append({
            'basename': unique_basename,
            'file_content': file_content,
            'raw_extension': raw_extension
        })
    
    return files


@settings(max_examples=50)
@given(multiple_files_scenario_strategy())
def test_multiple_files_copy_preservation_property(files_data):
    """
    **Feature: raw-jpeg-matcher, Property 7: ファイルコピーの保存性**
    **検証対象: 要件 5.1, 5.2**

    複数ファイルのコピーでも保存性が維持されることを検証します。
    """
    # 一時ディレクトリを作成
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        source_dir = temp_path / "source"
        target_dir = temp_path / "target"
        
        source_dir.mkdir()
        target_dir.mkdir()
        
        matches = []
        original_hashes = {}
        
        # ソースファイルを作成
        for file_data in files_data:
            basename = file_data['basename']
            file_content = file_data['file_content']
            raw_extension = file_data['raw_extension']
            
            jpeg_filename = f"{basename}.jpg"
            raw_filename = f"{basename}{raw_extension}"
            
            jpeg_path = source_dir / jpeg_filename
            raw_path = source_dir / raw_filename
            
            # ファイル内容を書き込み
            jpeg_path.write_bytes(b"fake jpeg content")
            raw_path.write_bytes(file_content)
            
            # 元ファイルのハッシュ値を記録
            original_hashes[raw_filename] = calculate_file_hash(raw_path)
            
            # MatchResultを作成
            match = MatchResult(
                jpeg_path=jpeg_path,
                raw_path=raw_path,
                match_method='basename_and_datetime'
            )
            matches.append(match)
        
        # Copierを作成してコピー実行
        copier = Copier()
        result = copier.copy_files(matches, target_dir)
        
        # プロパティ検証: 複数ファイルの保存性
        
        # 1. すべてのファイルがコピーされている
        assert result.success == len(files_data), f"コピー数が期待と異なります: 期待={len(files_data)}, 実際={result.success}"
        assert result.failed == 0, f"コピーエラーが発生しました: failed={result.failed}, errors={result.errors}"
        
        # 2. 各ファイルの保存性を検証
        for file_data in files_data:
            basename = file_data['basename']
            raw_extension = file_data['raw_extension']
            raw_filename = f"{basename}{raw_extension}"
            
            copied_file_path = target_dir / raw_filename
            
            # ファイルが存在する
            assert copied_file_path.exists(), f"コピー先ファイルが存在しません: {copied_file_path}"
            
            # ファイル内容が同じ
            copied_hash = calculate_file_hash(copied_file_path)
            original_hash = original_hashes[raw_filename]
            assert copied_hash == original_hash, f"ファイル内容が異なります: {raw_filename}"


@st.composite
def existing_file_scenario_strategy(draw):
    """既存ファイルがある場合のシナリオを生成するストラテジー"""
    basename = draw(st.text(
        alphabet=st.characters(
            whitelist_categories=('Lu', 'Ll', 'Nd'),
            min_codepoint=32,
            max_codepoint=126
        ),
        min_size=1,
        max_size=20
    ).filter(lambda x: x.strip() and not any(c in x for c in '<>:"|?*')))
    
    # 元ファイルと既存ファイルの内容を生成
    original_content = draw(st.binary(min_size=100, max_size=5000))
    existing_content = draw(st.binary(min_size=100, max_size=5000))
    
    raw_extension = draw(st.sampled_from(['.CR2', '.NEF', '.ARW']))
    
    return {
        'basename': basename,
        'original_content': original_content,
        'existing_content': existing_content,
        'raw_extension': raw_extension
    }


@settings(max_examples=50)
@given(existing_file_scenario_strategy())
def test_existing_file_skip_property(scenario):
    """
    既存ファイルのスキップ処理をテスト
    
    これは保存性プロパティの補完テストです。
    """
    # テストデータを取得
    basename = scenario['basename']
    original_content = scenario['original_content']
    existing_content = scenario['existing_content']
    raw_extension = scenario['raw_extension']
    
    # 一時ディレクトリを作成
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        source_dir = temp_path / "source"
        target_dir = temp_path / "target"
        
        source_dir.mkdir()
        target_dir.mkdir()
        
        # ソースファイルを作成
        jpeg_filename = f"{basename}.jpg"
        raw_filename = f"{basename}{raw_extension}"
        
        jpeg_path = source_dir / jpeg_filename
        raw_path = source_dir / raw_filename
        
        jpeg_path.write_bytes(b"fake jpeg content")
        raw_path.write_bytes(original_content)
        
        # ターゲットディレクトリに既存ファイルを作成
        existing_file_path = target_dir / raw_filename
        existing_file_path.write_bytes(existing_content)
        existing_hash = calculate_file_hash(existing_file_path)
        
        # MatchResultを作成
        match = MatchResult(
            jpeg_path=jpeg_path,
            raw_path=raw_path,
            match_method='basename_and_datetime'
        )
        
        # Copierを作成してコピー実行
        copier = Copier()
        result = copier.copy_files([match], target_dir)
        
        # プロパティ検証: 既存ファイルのスキップ
        
        # 1. ファイルがスキップされている
        assert result.skipped == 1, f"ファイルがスキップされませんでした: skipped={result.skipped}"
        assert result.success == 0, f"既存ファイルが上書きされました: success={result.success}"
        assert result.failed == 0, f"予期しないエラーが発生しました: failed={result.failed}"
        
        # 2. 既存ファイルの内容が保持されている
        final_hash = calculate_file_hash(existing_file_path)
        assert final_hash == existing_hash, f"既存ファイルの内容が変更されました"


def test_copier_basic_functionality():
    """Copierの基本機能テスト"""
    # 一時ディレクトリを作成
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        source_dir = temp_path / "source"
        target_dir = temp_path / "target"
        
        source_dir.mkdir()
        target_dir.mkdir()
        
        # テストファイルを作成
        jpeg_path = source_dir / "test.jpg"
        raw_path = source_dir / "test.CR2"
        
        jpeg_path.write_bytes(b"fake jpeg content")
        raw_path.write_bytes(b"fake raw content")
        
        # MatchResultを作成
        match = MatchResult(
            jpeg_path=jpeg_path,
            raw_path=raw_path,
            match_method='basename_and_datetime'
        )
        
        # Copierを作成してコピー実行
        copier = Copier()
        result = copier.copy_files([match], target_dir)
        
        # 結果を検証
        assert result.success == 1
        assert result.skipped == 0
        assert result.failed == 0
        assert len(result.errors) == 0
        
        # コピー先ファイルが存在することを確認
        copied_file = target_dir / "test.CR2"
        assert copied_file.exists()
        assert copied_file.read_bytes() == b"fake raw content"


def test_copier_nonexistent_source():
    """存在しないソースファイルの処理テスト"""
    # 一時ディレクトリを作成
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        target_dir = temp_path / "target"
        target_dir.mkdir()
        
        # 存在しないファイルパス
        nonexistent_jpeg = Path("/nonexistent/test.jpg")
        nonexistent_raw = Path("/nonexistent/test.CR2")
        
        # MatchResultを作成
        match = MatchResult(
            jpeg_path=nonexistent_jpeg,
            raw_path=nonexistent_raw,
            match_method='basename_and_datetime'
        )
        
        # Copierを作成してコピー実行
        copier = Copier()
        result = copier.copy_files([match], target_dir)
        
        # 結果を検証（失敗として処理される）
        assert result.success == 0
        assert result.skipped == 0
        assert result.failed == 1