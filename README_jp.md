# RAW-JPEG Matcher Tool

JPEGファイルに対応するRAWカメラファイルを効率的に検索してコピーするPythonコマンドラインツールです。選択したJPEG画像に対応するRAWファイルを収集したい写真家のために設計されています。

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 特徴

- **正確なマッチング**: ファイル名とExif撮影日時の両方でマッチングし、高精度を実現
- **高性能**: RAWファイルの事前インデックス化により、大量のファイルコレクションでも高速処理
- **クロスプラットフォーム**: macOSとWindowsでシームレスに動作
- **包括的なフォーマットサポート**: 主要なカメラメーカーのRAW形式をすべてサポート（Canon、Nikon、Sony、Fujifilmなど）
- **堅牢なエラーハンドリング**: 個別ファイルが失敗しても処理を継続
- **詳細なログ**: 包括的な進捗レポートとエラーサマリーを提供

## インストール

### 前提条件

このツールは、RAWファイルからExifメタデータを読み取るために **ExifTool** がシステムにインストールされている必要があります。

#### ExifToolのインストール

**macOS（Homebrewを使用）:**
```bash
brew install exiftool
```

**Windows:**
1. [https://exiftool.org/](https://exiftool.org/) からExifToolをダウンロード
2. `exiftool.exe` をPATH内のディレクトリに展開（例：`C:\Windows\System32`）

**Linux（Ubuntu/Debian）:**
```bash
sudo apt-get install libimage-exiftool-perl
```

### RAW-JPEG Matcher Toolのインストール

#### ソースから

1. リポジトリをクローン:
```bash
git clone <repository-url>
cd raw-jpeg-matcher
```

2. パッケージをインストール:
```bash
pip install -e .
```

3. テスト依存関係を含む開発用インストール:
```bash
pip install -e ".[test]"
```

#### pipを使用（公開時）

```bash
pip install raw-jpeg-matcher
```

## 使用方法

ツールは4つの主要コマンドを提供します：`index`、`match`、`list-index`、`clear-cache`。

### 基本的なワークフロー

1. **RAWファイルのインデックス作成**（ディレクトリごとに一度だけ実行）:
```bash
raw-jpeg-matcher index /path/to/your/raw/files
```

2. **選択したJPEGに対応するRAWファイルのマッチングとコピー**:
```bash
raw-jpeg-matcher match /path/to/your/jpeg/files
```

### コマンドリファレンス

#### `index` - RAWファイルインデックスの作成

指定されたディレクトリ内のRAWファイルのインデックスを作成または更新します。

```bash
# 基本的な使用方法
raw-jpeg-matcher index /path/to/raw/files

# サブディレクトリを検索しない
raw-jpeg-matcher index /path/to/raw/files --no-recursive

# 詳細な進捗を表示
raw-jpeg-matcher index /path/to/raw/files --verbose

# インデックスの完全再構築を強制
raw-jpeg-matcher index /path/to/raw/files --force-rebuild
```

**オプション:**
- `--no-recursive, -nr`: サブディレクトリを検索しない（デフォルト：再帰的）
- `--verbose, -v`: 詳細ログを表示
- `--force-rebuild, -f`: インデックスの完全再構築を強制

#### `match` - マッチするRAWファイルの検索とコピー

JPEGファイルにマッチするRAWファイルを検索し、同じディレクトリにコピーします。

```bash
# 基本的な使用方法
raw-jpeg-matcher match /path/to/jpeg/files

# サブディレクトリを検索しない
raw-jpeg-matcher match /path/to/jpeg/files --no-recursive

# 詳細な進捗を表示
raw-jpeg-matcher match /path/to/jpeg/files --verbose

# 特定のソースからのRAWファイルのみを使用
raw-jpeg-matcher match /path/to/jpeg/files --source-filter /path/to/specific/raw/source
```

**オプション:**
- `--no-recursive, -nr`: サブディレクトリを検索しない（デフォルト：再帰的）
- `--verbose, -v`: 詳細ログを表示
- `--source-filter, -s`: 指定されたソースディレクトリからのRAWファイルのみを使用

#### `list-index` - インデックス化されたディレクトリの表示

現在インデックス化されているディレクトリの情報を表示します。

```bash
# 基本的な一覧表示
raw-jpeg-matcher list-index

# 詳細情報を表示
raw-jpeg-matcher list-index --verbose
```

#### `clear-cache` - インデックスキャッシュのクリア

キャッシュされたインデックスデータを削除します。

```bash
# すべてのキャッシュされたインデックスをクリア
raw-jpeg-matcher clear-cache

# 特定のディレクトリのキャッシュのみをクリア
raw-jpeg-matcher clear-cache --source /path/to/raw/files
```

### 使用例

#### 例1: 基本的な使用方法

```bash
# ステップ1: RAWファイルのインデックス作成（RAWディレクトリごとに一度実行）
raw-jpeg-matcher index ~/Photos/2024/RAW_Files

# ステップ2: 選択したJPEGに対応するRAWファイルをコピー
raw-jpeg-matcher match ~/Photos/2024/Selected_JPEGs
```

#### 例2: 複数のRAWソース

```bash
# 複数のRAWディレクトリをインデックス化
raw-jpeg-matcher index ~/Photos/2024/Camera1_RAW
raw-jpeg-matcher index ~/Photos/2024/Camera2_RAW

# マッチングはすべてのインデックス化されたディレクトリを検索
raw-jpeg-matcher match ~/Photos/2024/Selected_JPEGs
```

#### 例3: 特定のソースフィルタリング

```bash
# マッチングにCamera1のRAWファイルのみを使用
raw-jpeg-matcher match ~/Photos/2024/Selected_JPEGs --source-filter ~/Photos/2024/Camera1_RAW
```

## サポートされているファイル形式

### RAW形式
- **Canon**: .CR2, .CR3
- **Nikon**: .NEF
- **Sony**: .ARW
- **Fujifilm**: .RAF
- **Olympus**: .ORF
- **Panasonic**: .RW2
- **Pentax**: .PEF
- **Leica**: .DNG, .RWL
- **Hasselblad**: .3FR
- **Phase One**: .IIQ
- **Adobe**: .DNG

### JPEG形式
- .jpg, .jpeg（大文字小文字を区別しない）

## 動作原理

1. **インデックス作成フェーズ**: ツールはRAWディレクトリをスキャンし、以下を含むインデックスを作成します：
   - ベースファイル名（拡張子なし）
   - フルファイルパス
   - Exif撮影日時
   - ファイルメタデータ

2. **マッチングフェーズ**: 各JPEGファイルに対して：
   - ベースファイル名とExif撮影日時を抽出
   - マッチするベースファイル名を持つRAWファイルをインデックスから検索
   - Exif撮影日時を使用してマッチを検証
   - 撮影時刻が完全に一致するファイルのみがマッチと見なされます

3. **コピーフェーズ**: マッチしたRAWファイルは以下の条件でJPEGディレクトリにコピーされます：
   - 元のファイル名を保持
   - 既存ファイルをスキップ（上書きしない）
   - 詳細な進捗レポート

## 設定

ツールはインデックスキャッシュファイルを `~/.raw_jpeg_matcher/cache/` に保存します。このディレクトリは自動的に作成され、すべてのキャッシュデータをクリアするために安全に削除できます。

## トラブルシューティング

### ExifToolが見つからない
```
❌ 処理エラー: ExifTool not found. Please install ExifTool first.
```
**解決方法**: 上記のインストール手順に従ってExifToolをインストールしてください。

### インデックスが見つからない
```
⚠️  Warning: No index found for matching. Please run 'index' command first.
```
**解決方法**: マッチングの前にRAWディレクトリで `index` コマンドを実行してください。

### 権限エラー
```
❌ 処理エラー: Permission denied accessing directory
```
**解決方法**: ソースディレクトリの読み取り権限とターゲットディレクトリの書き込み権限があることを確認してください。

## 開発

### テストの実行

```bash
# テスト依存関係をインストール
pip install -e ".[test]"

# すべてのテストを実行
pytest

# カバレッジ付きで実行
pytest --cov=src

# プロパティベーステストを実行
pytest tests/test_*_properties.py -v
```

### プロジェクト構造

```
raw-jpeg-matcher/
├── src/                    # メインソースコード
│   ├── cli.py             # コマンドラインインターフェース
│   ├── index_manager.py   # インデックス管理
│   ├── match_manager.py   # マッチングワークフロー
│   ├── indexer.py         # RAWファイルインデックス化
│   ├── matcher.py         # ファイルマッチングロジック
│   ├── copier.py          # ファイルコピー操作
│   ├── exif_reader.py     # Exifメタデータ読み取り
│   ├── file_scanner.py    # ディレクトリスキャン
│   └── path_validator.py  # パス検証
├── tests/                 # テストスイート
└── pyproject.toml         # プロジェクト設定
```

## 貢献

1. リポジトリをフォーク
2. フィーチャーブランチを作成（`git checkout -b feature/amazing-feature`）
3. 変更を加える
4. 新機能にテストを追加
5. テストスイートを実行（`pytest`）
6. 変更をコミット（`git commit -m 'Add amazing feature'`）
7. ブランチにプッシュ（`git push origin feature/amazing-feature`）
8. プルリクエストを開く

## ライセンス

このプロジェクトはMITライセンスの下でライセンスされています - 詳細は[LICENSE](LICENSE)ファイルを参照してください。

## 謝辞

- 包括的なExifメタデータサポートを提供するPhil HarveyによるExifTool
- 優れたライブラリとツールを提供するPythonコミュニティ