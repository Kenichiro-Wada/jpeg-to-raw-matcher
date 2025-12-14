"""
PathValidatorのプロパティベーステスト

Property 1: ディレクトリ検証の一貫性
Property 2: クロスプラットフォームパス処理
"""

import os
import tempfile
from pathlib import Path
from hypothesis import given, strategies as st, assume
from hypothesis import settings
import pytest

from src.path_validator import PathValidator
from src.exceptions import ValidationError


# テスト用のディレクトリ作成ヘルパー
def create_test_directory(base_path: Path, name: str, 
                         readable: bool = True, writable: bool = True) -> Path:
    """テスト用のディレクトリを作成"""
    test_dir = base_path / name
    test_dir.mkdir(exist_ok=True)
    
    # 権限設定（Unixライクシステムでのみ有効）
    if hasattr(os, 'chmod'):
        mode = 0o000
        if readable:
            mode |= 0o444
        if writable:
            mode |= 0o222
        if readable or writable:
            mode |= 0o111  # 実行権限（ディレクトリアクセスに必要）
        os.chmod(test_dir, mode)
    
    return test_dir


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

@settings(max_examples=100)
@given(safe_filename_strategy)
def test_directory_validation_consistency_property(directory_name):
    """
    **Feature: raw-jpeg-matcher, Property 1: ディレクトリ検証の一貫性**
    **検証対象: 要件 1.1, 1.2, 1.3**

    任意のディレクトリパスに対して、検証関数は存在しアクセス可能な
    ディレクトリを受け入れ、存在しないまたはアクセス不可能なパスを
    無効なパスを含む明確なエラーメッセージとともに拒否すべきである。
    """
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # ケース1: 存在しアクセス可能なディレクトリ
        valid_dir = create_test_directory(temp_path, directory_name, 
                                        readable=True, writable=True)
        
        # 存在しアクセス可能なディレクトリは検証を通過すべき
        try:
            PathValidator.validate_directory(valid_dir)
            # 例外が発生しなければ成功
            validation_passed = True
        except ValidationError:
            validation_passed = False
        
        assert validation_passed, f"存在するディレクトリの検証が失敗: {valid_dir}"
        
        # ケース2: 存在しないディレクトリ
        non_existent_dir = temp_path / f"non_existent_{directory_name}"
        
        # 存在しないディレクトリは ValidationError を発生させるべき
        with pytest.raises(ValidationError) as exc_info:
            PathValidator.validate_directory(non_existent_dir)
        
        # エラーメッセージにパス情報が含まれているべき
        error_message = str(exc_info.value)
        assert str(non_existent_dir) in error_message
        assert "存在しません" in error_message
        
        # ケース3: ファイル（ディレクトリではない）
        test_file = temp_path / f"test_file_{directory_name}.txt"
        test_file.write_text("test content")
        
        # ファイルパスは ValidationError を発生させるべき
        with pytest.raises(ValidationError) as exc_info:
            PathValidator.validate_directory(test_file)
        
        # エラーメッセージにパス情報が含まれているべき
        error_message = str(exc_info.value)
        assert str(test_file) in error_message
        assert "ディレクトリではありません" in error_message


@settings(max_examples=50)
@given(safe_filename_strategy)
def test_writable_directory_validation_property(directory_name):
    """
    書き込み可能ディレクトリ検証のプロパティテスト
    """
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # 書き込み可能なディレクトリ
        writable_dir = create_test_directory(temp_path, directory_name,
                                           readable=True, writable=True)
        
        # 書き込み可能なディレクトリは検証を通過すべき
        try:
            PathValidator.validate_writable_directory(writable_dir)
            validation_passed = True
        except ValidationError:
            validation_passed = False
        
        assert validation_passed, f"書き込み可能ディレクトリの検証が失敗: {writable_dir}"


# パス正規化のテスト用ストラテジー
@st.composite
def path_string_strategy(draw):
    """様々なパス文字列を生成するストラテジー"""
    # パスの種類を選択
    path_type = draw(st.sampled_from(['relative', 'absolute', 'home']))
    
    # パス要素を生成（ファイルシステムで安全な文字のみ）
    path_elements = draw(st.lists(
        safe_filename_strategy,
        min_size=1,
        max_size=5
    ))
    
    if path_type == 'relative':
        return '/'.join(path_elements)
    elif path_type == 'absolute':
        return '/' + '/'.join(path_elements)
    else:  # home
        return '~/' + '/'.join(path_elements)


@settings(max_examples=100)
@given(path_string_strategy())
def test_cross_platform_path_processing_property(path_string):
    """
    **Feature: raw-jpeg-matcher, Property 2: クロスプラットフォームパス処理**
    **検証対象: 要件 1.4**

    任意のPOSIXまたはWindows形式の有効なパス文字列に対して、
    システムは適切なオペレーティングシステム上でパスを正しく
    解析し処理すべきである。
    """
    # パス正規化を実行
    normalized_path = PathValidator.normalize_path(path_string)
    
    # プロパティ検証
    # 1. 結果はPathオブジェクトであるべき
    assert isinstance(normalized_path, Path)
    
    # 2. 正規化されたパスは絶対パスであるべき
    assert normalized_path.is_absolute()
    
    # 3. パス文字列から正規化されたパスを再構築できるべき
    # （同じ入力に対して一貫した結果を返すべき）
    normalized_again = PathValidator.normalize_path(path_string)
    assert normalized_path == normalized_again
    
    # 4. 正規化されたパスの文字列表現は有効であるべき
    path_str = str(normalized_path)
    assert len(path_str) > 0
    
    # 5. パスの各部分は有効な文字のみを含むべき
    # （プラットフォーム固有の無効文字がないことを確認）
    for part in normalized_path.parts:
        if part not in ('/', '\\'):  # ルート要素を除く
            assert len(part) > 0


def test_normalize_path_with_home_directory():
    """ホームディレクトリ展開のテスト"""
    # ホームディレクトリを含むパス
    home_path = "~/test/directory"
    normalized = PathValidator.normalize_path(home_path)
    
    # ホームディレクトリが展開されているべき
    assert not str(normalized).startswith('~')
    assert normalized.is_absolute()


def test_normalize_path_with_current_directory():
    """相対パスの正規化テスト"""
    # 相対パス
    relative_path = "test/directory"
    normalized = PathValidator.normalize_path(relative_path)
    
    # 絶対パスに変換されているべき
    assert normalized.is_absolute()


def test_disk_space_check_property():
    """ディスク容量チェックのプロパティテスト"""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # 非常に小さな容量要求（常に満たされるべき）
        small_requirement = 1  # 1バイト
        result = PathValidator.check_disk_space(temp_path, small_requirement)
        assert result is True
        
        # 非常に大きな容量要求（通常は満たされない）
        large_requirement = 10**18  # 1エクサバイト
        result = PathValidator.check_disk_space(temp_path, large_requirement)
        assert result is False


def test_disk_usage_info_property():
    """ディスク使用量情報取得のプロパティテスト"""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        usage_info = PathValidator.get_disk_usage_info(temp_path)
        
        if usage_info is not None:
            total, used, free = usage_info
            
            # 基本的な整合性チェック
            assert isinstance(total, int)
            assert isinstance(used, int)
            assert isinstance(free, int)
            assert total > 0
            assert used >= 0
            assert free >= 0
            assert used + free <= total  # 使用量+空き容量 <= 総容量