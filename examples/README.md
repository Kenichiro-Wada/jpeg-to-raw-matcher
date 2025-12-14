# 使用例スクリプト

このディレクトリには、RAW-JPEG Matcher Toolの使用方法を示すサンプルスクリプトが含まれています。

## ファイル一覧

### `basic_usage.py`
基本的な使用方法を示すスクリプトです。

**含まれる例:**
- 基本的なワークフロー（インデックス作成 → マッチング → コピー）
- 複数のRAWソースディレクトリの管理
- 特定のソースディレクトリのフィルタリング
- キャッシュ管理

**実行方法:**
```bash
cd examples
python basic_usage.py
```

### `advanced_usage.py`
高度な機能とカスタマイズされた使用方法を示すスクリプトです。

**含まれる例:**
- カスタムマッチングロジック
- バッチ処理（複数ディレクトリの一括処理）
- パフォーマンス監視
- エラーハンドリング

**実行方法:**
```bash
cd examples
python advanced_usage.py
```

## 使用前の準備

### 1. 依存関係のインストール
```bash
# プロジェクトルートで実行
pip install -e .
```

### 2. ExifToolのインストール
**macOS:**
```bash
brew install exiftool
```

**Windows:**
1. [https://exiftool.org/](https://exiftool.org/) からダウンロード
2. `exiftool.exe` をPATH内のディレクトリに配置

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get install libimage-exiftool-perl
```

### 3. ディレクトリパスの設定
スクリプト内のディレクトリパスを実際の環境に合わせて変更してください：

```python
# 例: basic_usage.py内
raw_directory = Path("~/Photos/RAW_Files").expanduser()
jpeg_directory = Path("~/Photos/Selected_JPEGs").expanduser()
```

## 実行例

### 基本的なワークフロー
```bash
python basic_usage.py
# 選択: 1 (基本的なワークフロー)
```

### カスタムマッチング
```bash
python advanced_usage.py
# 選択: 1 (カスタムマッチングロジック)
```

### パフォーマンステスト
```bash
python advanced_usage.py
# 選択: 3 (パフォーマンス監視)
```

## 注意事項

- スクリプトはプロジェクトルートまたは`examples`ディレクトリから実行してください
- 実際のファイルを使用する前に、テストデータで動作確認することをお勧めします
- 大量のファイルを処理する場合は、事前にバックアップを取ってください

## カスタマイズ

これらのスクリプトは、あなたの特定のニーズに合わせてカスタマイズできます：

1. **ディレクトリ構造**: 実際のディレクトリ構造に合わせてパスを変更
2. **ファイルフィルタリング**: 特定のファイル形式や日付範囲でフィルタリング
3. **ログ設定**: ログレベルや出力先をカスタマイズ
4. **エラーハンドリング**: 特定のエラー条件に対する処理を追加

## トラブルシューティング

### よくある問題

1. **ModuleNotFoundError**
   ```bash
   # プロジェクトルートで実行
   pip install -e .
   ```

2. **ExifTool not found**
   - ExifToolがインストールされていることを確認
   - PATHに正しく設定されていることを確認

3. **ディレクトリが見つからない**
   - スクリプト内のディレクトリパスを実際の環境に合わせて変更

4. **権限エラー**
   - ディレクトリの読み取り/書き込み権限を確認
   - 必要に応じて権限を変更

### ログの確認

詳細なログは以下の場所に保存されます：
```
~/.raw_jpeg_matcher/logs/raw_jpeg_matcher_YYYYMMDD_HHMMSS.log
```

### サポート

問題が解決しない場合は、以下の情報を含めてサポートに連絡してください：
- 使用しているOS
- Pythonのバージョン
- ExifToolのバージョン
- エラーメッセージの全文
- 実行したコマンド