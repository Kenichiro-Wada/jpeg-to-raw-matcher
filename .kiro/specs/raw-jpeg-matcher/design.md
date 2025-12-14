# Design Document

## Overview

RAW-JPEG Matcher Toolは、JPEGファイルに対応するRAWファイルを効率的に検索してコピーするPythonアプリケーションです。本システムは以下の主要な設計原則に基づいています：

1. **高速処理**: 事前インデックス作成と並列処理により、大量のファイルを効率的に処理
2. **クロスプラットフォーム**: macOSとWindowsの両方で動作する移植性の高い実装
3. **堅牢性**: エラーハンドリングとログ機能により、予期しない状況でも安全に動作
4. **拡張性**: 新しいRAWファイル形式に対応できる柔軟な設計

## Architecture

システムは以下のレイヤーで構成されます：

```
┌─────────────────────────────────────┐
│     CLI Interface Layer             │
│  (コマンドライン引数の解析と実行)    │
└─────────────────────────────────────┘
              ↓
┌─────────────────────────────────────┐
│     Application Layer               │
│  (メイン処理フローの制御)            │
└─────────────────────────────────────┘
              ↓
┌──────────────┬──────────────┬───────┐
│   Indexer    │   Matcher    │ Copier│
│   (索引作成) │  (照合処理)  │(コピー)│
└──────────────┴──────────────┴───────┘
              ↓
┌─────────────────────────────────────┐
│     Core Services Layer             │
│  - ExifReader (Exif情報読取)        │
│  - FileScanner (ファイル検索)        │
│  - PathValidator (パス検証)          │
└─────────────────────────────────────┘
              ↓
┌─────────────────────────────────────┐
│     Infrastructure Layer            │
│  - Logging (ログ出力)                │
│  - Progress (進捗表示)               │
│  - FileSystem (ファイル操作)         │
└─────────────────────────────────────┘
```

### 処理フロー

1. **初期化フェーズ**
   - コマンドライン引数の解析
   - ディレクトリパスの検証
   - ログシステムの初期化

2. **インデックス作成フェーズ**
   - ソースディレクトリのスキャン
   - RAWファイルの検出
   - 並列処理によるExif情報の読取
   - インメモリインデックスの構築

3. **マッチングフェーズ**
   - ターゲットディレクトリのJPEGファイルスキャン
   - 各JPEGファイルのExif情報読取
   - インデックスを使用した高速マッチング
   - ファイル名とExif日時による二段階照合

4. **コピーフェーズ**
   - マッチしたRAWファイルのコピー
   - エラーハンドリングと進捗表示
   - 結果サマリーの出力

## Components and Interfaces

### 1. CLI Interface (`cli.py`)

コマンドライン引数を解析し、アプリケーションを起動します。

```python
def main():
    """メインエントリーポイント"""
    parser = argparse.ArgumentParser(
        description='JPEGファイルに対応するRAWファイルを検索してコピー'
    )
    
    # サブコマンドを作成
    subparsers = parser.add_subparsers(dest='command', help='利用可能なコマンド')
    
    # indexコマンド（インデックス作成）
    index_parser = subparsers.add_parser('index', aliases=['i'], help='RAWファイルのインデックスを作成・更新')
    index_parser.add_argument('source', help='RAWファイルのソースディレクトリ')
    index_parser.add_argument('--no-recursive', '-nr', action='store_true', help='サブディレクトリを検索しない（デフォルトは再帰的に検索）')
    index_parser.add_argument('--verbose', '-v', action='store_true', help='詳細ログを表示')
    index_parser.add_argument('--force-rebuild', '-f', action='store_true', help='該当ディレクトリのインデックスを強制的に再構築')
    
    # matchコマンド（マッチング処理）
    match_parser = subparsers.add_parser('match', aliases=['m'], help='JPEGファイルに対応するRAWファイルを検索してコピー')
    match_parser.add_argument('target', help='JPEGファイルのターゲットディレクトリ')
    match_parser.add_argument('--no-recursive', '-nr', action='store_true', help='サブディレクトリを検索しない（デフォルトは再帰的に検索）')
    match_parser.add_argument('--verbose', '-v', action='store_true', help='詳細ログを表示')
    match_parser.add_argument('--source-filter', '-s', help='特定のソースディレクトリのRAWファイルのみを対象にする')
    
    # list-indexコマンド（インデックス一覧表示）
    list_parser = subparsers.add_parser('list-index', aliases=['l'], help='インデックス化されたディレクトリ一覧を表示')
    list_parser.add_argument('--verbose', '-v', action='store_true', help='詳細情報を表示')
    
    # clear-cacheコマンド
    cache_parser = subparsers.add_parser('clear-cache', aliases=['c'], help='インデックスキャッシュをクリア')
    cache_parser.add_argument('--source', '-s', help='特定のソースディレクトリのキャッシュのみクリア（省略時は全体）')
    
    args = parser.parse_args()
    
    if args.command == 'index':
        indexer = IndexManager()
        recursive = not args.no_recursive  # デフォルトはTrue
        indexer.build_or_update_index(Path(args.source), recursive, args.force_rebuild, args.verbose)
    elif args.command == 'match':
        matcher = MatchManager()
        recursive = not args.no_recursive  # デフォルトはTrue
        matcher.find_and_copy_matches(Path(args.target), recursive, args.source_filter, args.verbose)
    elif args.command == 'list-index':
        indexer = IndexManager()
        indexer.list_indexed_directories(args.verbose)
    elif args.command == 'clear-cache':
        indexer = IndexManager()
        if args.source:
            indexer.clear_cache(Path(args.source))
            print(f"ソースディレクトリ '{args.source}' のキャッシュをクリアしました")
        else:
            indexer.clear_cache()
            print("すべてのインデックスキャッシュをクリアしました")
    else:
        parser.print_help()
```

### 2. IndexManager (`index_manager.py`)

インデックス作成と管理を担当します。

```python
class IndexManager:
    def __init__(self):
        self.cache = IndexCache()
        self.exif_reader = ExifReader()
        self.file_scanner = FileScanner()
        
    def build_or_update_index(self, source_dir: Path, recursive: bool, force_rebuild: bool, verbose: bool) -> None:
        """インデックスを作成または更新"""
        # 1. 既存インデックスの確認
        # 2. 差分更新または新規追加
        # 3. 結果レポート
        
    def list_indexed_directories(self, verbose: bool) -> None:
        """インデックス化されたディレクトリ一覧を表示"""
        
    def clear_cache(self, source_dir: Optional[Path] = None) -> None:
        """キャッシュをクリア"""

class MatchManager:  # match_manager.py
    def __init__(self):
        self.cache = IndexCache()
        self.exif_reader = ExifReader()
        self.file_scanner = FileScanner()
        self.matcher = Matcher()
        self.copier = Copier()
        
    def find_and_copy_matches(self, target_dir: Path, recursive: bool, source_filter: Optional[str], verbose: bool) -> None:
        """JPEGファイルに対応するRAWファイルを検索してコピー"""
        # 1. 全インデックスの読み込み
        # 2. インデックス存在チェックと警告表示
        # 3. JPEGファイルのスキャン
        # 4. マッチング処理
        # 5. コピー処理
        # 6. 結果レポート
        
    def check_index_availability(self, source_filter: Optional[str]) -> bool:
        """インデックスの利用可能性をチェックし、必要に応じて警告を表示"""
        # インデックスが存在しない場合の警告処理
        
    def display_index_warning(self, missing_directories: List[Path]) -> None:
        """インデックス不足の警告メッセージを表示"""
```

### 3. Indexer (`indexer.py`)

RAWファイルのインデックスを作成し、永続化します。

```python
class RawFileIndex:
    """RAWファイル情報を保持するインデックス"""
    def __init__(self):
        self.by_basename: Dict[str, List[RawFileInfo]] = {}
        self.by_datetime: Dict[datetime, List[RawFileInfo]] = {}
        self.source_directory: Optional[Path] = None
        self.last_updated: Optional[datetime] = None
        
    def add(self, info: RawFileInfo) -> None:
        """インデックスにRAWファイル情報を追加"""
        
    def remove(self, file_path: Path) -> None:
        """インデックスからファイル情報を削除"""
        
    def find_by_basename(self, basename: str) -> List[RawFileInfo]:
        """ベース名でRAWファイルを検索"""
        
    def find_by_datetime(self, dt: datetime) -> List[RawFileInfo]:
        """撮影日時でRAWファイルを検索"""
        
    def save_to_disk(self, cache_dir: Path) -> None:
        """インデックスをディスクに保存"""
        
    @classmethod
    def load_from_disk(cls, cache_dir: Path, source_dir: Path) -> Optional['RawFileIndex']:
        """ディスクからインデックスを読み込み"""

class IndexCache:
    """インデックスキャッシュ管理"""
    def __init__(self):
        self.cache_dir = Path.home() / '.raw_jpeg_matcher' / 'cache'
        self.global_index_file = self.cache_dir / 'global_index.json'
        
    def get_cache_path(self, source_dir: Path) -> Path:
        """ソースディレクトリに対応するキャッシュファイルパスを取得"""
        
    def load_global_index(self) -> Dict[str, RawFileIndex]:
        """全ディレクトリのインデックスを読み込み"""
        
    def save_global_index(self, global_index: Dict[str, RawFileIndex]) -> None:
        """全ディレクトリのインデックスを保存"""
        
    def add_or_update_directory_index(self, source_dir: Path, index: RawFileIndex) -> None:
        """特定ディレクトリのインデックスを追加または更新"""
        
    def remove_directory_index(self, source_dir: Path) -> None:
        """特定ディレクトリのインデックスを削除"""
        
    def list_indexed_directories(self) -> List[Tuple[Path, datetime, int]]:
        """インデックス化されたディレクトリ一覧を取得（パス、最終更新日時、ファイル数）"""
        
    def clear_all_cache(self) -> None:
        """すべてのキャッシュを削除"""

class Indexer:
    def __init__(self, exif_reader: ExifReader, file_scanner: FileScanner):
        self.exif_reader = exif_reader
        self.file_scanner = file_scanner
        self.cache = IndexCache()
        
    def build_index(self, source_dir: Path, recursive: bool, force_rebuild: bool = False) -> RawFileIndex:
        """RAWファイルのインデックスを構築（差分更新対応）"""
        # 1. 既存インデックスの読み込み
        # 2. ファイルシステムとの差分チェック
        # 3. 新規・更新・削除ファイルの処理
        # 4. インデックスの保存
        
    def update_index_incrementally(self, index: RawFileIndex, source_dir: Path, recursive: bool) -> RawFileIndex:
        """インデックスの差分更新"""
        
    def clear_cache(self, source_dir: Optional[Path] = None) -> None:
        """キャッシュをクリア（特定ディレクトリまたは全体）"""
```

### 4. Matcher (`matcher.py`)

JPEGファイルとRAWファイルをマッチングします。

```python
class MatchResult:
    """マッチング結果"""
    jpeg_path: Path
    raw_path: Path
    match_method: str  # 'basename_and_datetime' or 'basename_only'

class Matcher:
    def __init__(self, exif_reader: ExifReader, index: RawFileIndex):
        self.exif_reader = exif_reader
        self.index = index
        
    def find_matches(self, jpeg_files: List[Path]) -> List[MatchResult]:
        """JPEGファイルに対応するRAWファイルを検索"""
        # 1. ファイル名でフィルタリング
        # 2. Exif日時で検証
```

### 5. Copier (`copier.py`)

マッチしたRAWファイルをコピーします。

```python
class CopyResult:
    """コピー結果"""
    success: int
    skipped: int
    failed: int
    errors: List[Tuple[Path, str]]

class Copier:
    def copy_files(self, matches: List[MatchResult], target_dir: Path) -> CopyResult:
        """マッチしたRAWファイルをターゲットディレクトリにコピー"""
```

### 6. ExifReader (`exif_reader.py`)

Exif情報を読み取ります。

```python
class ExifReader:
    def __init__(self):
        self.cache: Dict[Path, Optional[datetime]] = {}
        self.exiftool_path: Optional[Path] = None
        
    def _find_exiftool(self) -> Path:
        """ExifToolの実行可能ファイルを検索"""
        # Windows: exiftool.exe, macOS/Linux: exiftool
        
    def _run_exiftool(self, file_path: Path, tags: List[str]) -> Dict[str, str]:
        """ExifToolを実行してExif情報を取得"""
        # subprocess.run()を使用してExifToolを実行
        
    def read_capture_datetime(self, file_path: Path) -> Optional[datetime]:
        """ファイルから撮影日時を読み取る（キャッシュ付き）"""
        # ExifToolを使用してExif情報を読取
        # DateTimeOriginal, CreateDate, ModifyDateの順で試行
        
    def check_exiftool_availability(self) -> bool:
        """ExifToolが利用可能かチェック"""
```

### 7. FileScanner (`file_scanner.py`)

ディレクトリをスキャンしてファイルを検索します。

```python
class FileScanner:
    RAW_EXTENSIONS = {'.cr2', '.cr3', '.nef', '.arw', '.raf', '.orf', 
                      '.rw2', '.pef', '.dng', '.rwl', '.3fr', '.iiq',
                      '.CR2', '.CR3', '.NEF', '.ARW', '.RAF', '.ORF',
                      '.RW2', '.PEF', '.DNG', '.RWL', '.3FR', '.IIQ'}
    JPEG_EXTENSIONS = {'.jpg', '.jpeg', '.JPG', '.JPEG'}
    
    def scan_raw_files(self, directory: Path, recursive: bool) -> List[Path]:
        """RAWファイルをスキャン（大文字小文字両方の拡張子に対応）"""
        
    def scan_jpeg_files(self, directory: Path, recursive: bool) -> List[Path]:
        """JPEGファイルをスキャン（大文字小文字両方の拡張子に対応）"""
```

### 8. PathValidator (`path_validator.py`)

パスの検証を行います。

```python
class PathValidator:
    @staticmethod
    def validate_directory(path: Path) -> None:
        """ディレクトリの存在とアクセス権を検証"""
        
    @staticmethod
    def check_disk_space(path: Path, required_bytes: int) -> bool:
        """ディスク空き容量を確認"""
```

## Data Models

### RawFileInfo

```python
@dataclass
class RawFileInfo:
    """RAWファイルの情報"""
    path: Path
    basename: str  # 拡張子を除いたファイル名（小文字）
    capture_datetime: Optional[datetime]
    file_size: int
```

### JpegFileInfo

```python
@dataclass
class JpegFileInfo:
    """JPEGファイルの情報"""
    path: Path
    basename: str  # 拡張子を除いたファイル名（小文字）
    capture_datetime: Optional[datetime]
```

### ProcessingStats

```python
@dataclass
class ProcessingStats:
    """処理統計情報"""
    raw_files_found: int
    jpeg_files_found: int
    matches_found: int
    files_copied: int
    files_skipped: int
    files_failed: int
    errors: List[Tuple[str, str]]  # (file_path, error_message)
```


## 正確性プロパティ

*プロパティとは、システムのすべての有効な実行において真であるべき特性や動作のことです。つまり、システムが何をすべきかについての形式的な記述です。プロパティは、人間が読める仕様と機械で検証可能な正確性保証との橋渡しをします。*

### プロパティ1: ディレクトリ検証の一貫性

*任意の*ディレクトリパスに対して、検証関数は存在しアクセス可能なディレクトリを受け入れ、存在しないまたはアクセス不可能なパスを無効なパスを含む明確なエラーメッセージとともに拒否すべきである。

**検証対象: 要件 1.1, 1.2, 1.3**

### プロパティ2: クロスプラットフォームパス処理

*任意の*POSIXまたはWindows形式の有効なパス文字列に対して、システムは適切なオペレーティングシステム上でパスを正しく解析し処理すべきである。

**検証対象: 要件 1.4**

### プロパティ3: ベース名抽出の一貫性

*任意の*拡張子を持つファイルパスに対して、ベース名の抽出は拡張子を除去し、大文字小文字を区別しない比較を行うことで、同じベース名を持つが大文字小文字が異なるファイルをマッチと見なすべきである。

**検証対象: 要件 2.1, 2.2, 2.3**

### プロパティ4: Exif日時抽出

*任意の*有効なExifデータを持つ画像ファイル（JPEGまたはRAW）に対して、システムは撮影日時の値を正常に抽出すべきである。

**検証対象: 要件 3.1, 3.2**

### プロパティ5: 日時マッチングの厳密性

*任意の*撮影日時の値を持つファイルのペアに対して、システムは日時の値が完全に一致する場合のみマッチと見なすべきである。

**検証対象: 要件 3.3**

### プロパティ6: インデックスの完全性

*任意の*ソースディレクトリ内のRAWファイルに対して、インデックスはそのファイルのベース名、フルパス、撮影日時（利用可能な場合）を含むエントリを持つべきである。

**検証対象: 要件 4.2**

### プロパティ7: ファイルコピーの保存性

*任意の*ターゲットディレクトリにコピーされたマッチしたRAWファイルに対して、コピーされたファイルは元のファイルと同じファイル名と同じファイル内容を持つべきである。

**検証対象: 要件 5.1, 5.2**

### プロパティ8: 処理サマリーの正確性

*任意の*完了した処理実行に対して、報告される統計情報（コピーされたファイル数、スキップされたファイル数、失敗したファイル数）は見つかったマッチの総数と一致すべきである。

**検証対象: 要件 5.5**

### プロパティ9: Exifキャッシュの一貫性

*任意の*ファイルに対して、Exifデータを複数回読み取ると同じ結果が返され、2回目以降の読み取りはキャッシュから提供されるべきである。

**検証対象: 要件 6.2**

### プロパティ10: エラーログの完全性

*任意の*処理中に発生したエラーに対して、エラーログはエラーが発生したファイルパスとエラーの説明の両方を含むべきである。

**検証対象: 要件 7.5**

### プロパティ11: インデックス永続化の一貫性

*任意の*RAWファイルインデックスに対して、ディスクに保存してから読み込んだインデックスは元のインデックスと同じ内容を持つべきである。

**検証対象: 要件 9.1**

### プロパティ12: 差分更新の正確性

*任意の*既存インデックスと新しいファイルセットに対して、差分更新後のインデックスは完全再構築したインデックスと同じ結果を持つべきである。

**検証対象: 要件 9.2, 9.4, 9.5**

### プロパティ13: インデックス不足時の警告表示

*任意の*マッチング処理において、利用可能なインデックスが存在しない場合、システムは適切な警告メッセージを表示すべきである。

**検証対象: 要件 10.7**

### プロパティ14: ExifTool依存性の検証

*任意の*Exif読取処理において、ExifToolが利用できない場合、システムは明確なエラーメッセージを表示すべきである。

**検証対象: 要件 3.7**

## エラーハンドリング

### エラーカテゴリ

1. **入力検証エラー**
   - 存在しないディレクトリ
   - アクセス権限のないディレクトリ
   - 無効なパス形式

2. **ファイル処理エラー**
   - Exif読取失敗
   - ファイルコピー失敗
   - ディスク容量不足

3. **データエラー**
   - 破損したExifデータ
   - 未対応のファイル形式

### エラーハンドリング戦略

- **フェイルファスト**: 初期検証エラーは即座に処理を中断
- **継続処理**: 個別ファイルのエラーは記録して処理を継続
- **詳細ログ**: すべてのエラーにファイルパスとエラー詳細を記録
- **ユーザーフィードバック**: エラーサマリーを最終レポートに含める

### エラー処理の実装

```python
class ProcessingError(Exception):
    """処理エラーの基底クラス"""
    pass

class ValidationError(ProcessingError):
    """検証エラー"""
    pass

class FileOperationError(ProcessingError):
    """ファイル操作エラー"""
    pass

class ExifReadError(ProcessingError):
    """Exif読取エラー"""
    pass
```

## テスト戦略

### テストアプローチ

本システムは、ユニットテストとプロパティベーステストの両方を使用して包括的なテストカバレッジを実現します。

### ユニットテスト

ユニットテストは以下の具体的なケースを検証します：

1. **パス処理**
   - macOSスタイルのパス処理
   - Windowsスタイルのパス処理（ドライブレター付き）

2. **ファイル形式サポート**
   - 各カメラメーカーのRAW形式（Canon CR2/CR3, Nikon NEF, Sony ARW等）
   - JPEG形式（.jpg, .jpeg）

3. **エッジケース**
   - Exifデータが欠落しているファイル
   - 破損したExifデータ
   - ターゲットディレクトリに既存ファイルがある場合
   - ディスク容量不足
   - ファイル権限エラー
   - 未対応のファイル形式

4. **出力とログ**
   - 処理開始時のサマリー表示
   - インデックス構築時のRAWファイル数表示
   - 進捗情報の表示
   - 最終サマリーの表示

### プロパティベーステスト

プロパティベーステストには**Hypothesis**ライブラリを使用します。各プロパティテストは最低100回の反復実行を行います。

各プロパティテストは、対応する正確性プロパティを明示的に参照するコメントを含める必要があります：

```python
# Feature: raw-jpeg-matcher, Property 1: Directory validation consistency
def test_directory_validation_property():
    ...
```

プロパティテストは以下の普遍的な特性を検証します：

1. **ディレクトリ検証の一貫性** (Property 1)
2. **クロスプラットフォームパス処理** (Property 2)
3. **ベース名抽出の一貫性** (Property 3)
4. **Exif日時抽出** (Property 4)
5. **日時マッチングの厳密性** (Property 5)
6. **インデックスの完全性** (Property 6)
7. **ファイルコピーの保存性** (Property 7)
8. **処理サマリーの正確性** (Property 8)
9. **Exifキャッシュの一貫性** (Property 9)
10. **エラーログの完全性** (Property 10)

### テスト環境

- Python 3.10, 3.11, 3.12でのテスト
- macOSとWindows環境でのテスト
- 様々なカメラメーカーのサンプルRAWファイルを使用

### 依存ライブラリ

- **ExifTool**: 外部コマンドラインツール（最新のRAW形式を含む包括的なExif情報読取）
- **Hypothesis**: プロパティベーステスト
- **pytest**: テストフレームワーク
- **pathlib**: クロスプラットフォームパス処理

## 実装ノート

### パフォーマンス最適化

1. **並列処理**
   - `concurrent.futures.ThreadPoolExecutor`を使用してExif読取を並列化
   - I/O待機時間を最小化

2. **キャッシング**
   - Exif読取結果をメモリにキャッシュ
   - 同じファイルの重複読取を回避

3. **インデックス構造**
   - ベース名と日時の両方でインデックス化
   - O(1)の検索時間を実現

### クロスプラットフォーム対応

1. **パス処理**
   - `pathlib.Path`を使用してOS依存性を抽象化
   - パス区切り文字の自動変換

2. **ファイルシステム操作**
   - `shutil.copy2`を使用してメタデータを保持
   - OS固有のファイル属性を適切に処理

3. **文字エンコーディング**
   - UTF-8を標準として使用
   - ファイル名の正規化処理

### ExifTool統合

1. **インストール要件**
   - Windows: ExifTool実行ファイル（exiftool.exe）をPATHに配置
   - macOS: Homebrew経由でインストール（`brew install exiftool`）
   - Linux: パッケージマネージャー経由でインストール

2. **自動検出**
   - システムPATHからExifToolを自動検出
   - 複数の場所を検索（/usr/local/bin, /usr/bin, Windowsの場合はPATH環境変数）

3. **エラーハンドリング**
   - ExifTool未インストール時の明確なエラーメッセージ
   - インストール手順の案内

### 拡張性

1. **新しいRAW形式への対応**
   - `FileScanner.RAW_EXTENSIONS`に拡張子を追加するだけで対応可能
   - ExifToolが新形式をサポートすれば自動的に対応

2. **カスタムマッチングロジック**
   - `Matcher`クラスを拡張して独自のマッチングアルゴリズムを実装可能

3. **プラグイン機構**
   - 将来的にカスタムExifリーダーやコピー戦略を追加可能な設計
