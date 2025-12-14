# 統合テスト

## 概要

`test_integration.py`は、RAW-JPEG Matcher Toolのエンドツーエンドの処理フローをテストする統合テストです。実際のサンプルファイルを使用して、システム全体の動作を検証します。

## テストケース

### 基本機能テスト

1. **test_end_to_end_workflow**
   - 完全なワークフローをテスト（index → match → clear-cache）
   - 実際のファイルマッチングの検証
   - 期待される結果の確認

2. **test_cli_index_command**
   - CLIのindexコマンドの動作確認
   - インデックス作成の検証

3. **test_cli_match_command**
   - CLIのmatchコマンドの動作確認
   - ファイルコピーの検証

4. **test_cli_list_index_command**
   - CLIのlist-indexコマンドの動作確認
   - インデックス一覧表示の検証

5. **test_cli_clear_cache_command**
   - CLIのclear-cacheコマンドの動作確認
   - キャッシュクリアの検証

### 高度な機能テスト

6. **test_source_filter_functionality**
   - ソースフィルター機能のテスト
   - 複数ソースディレクトリでの選択的マッチング

7. **test_no_recursive_option**
   - --no-recursiveオプションのテスト
   - サブディレクトリ除外の確認

8. **test_force_rebuild_option**
   - --force-rebuildオプションのテスト
   - インデックス強制再構築の確認

### クロスプラットフォーム対応テスト

9. **test_cross_platform_path_handling**
   - パス正規化の確認
   - 絶対パス処理の検証

10. **test_windows_path_compatibility**
    - Windowsパス形式の互換性テスト
    - pathlibによるクロスプラットフォーム処理

11. **test_platform_specific_behavior**
    - プラットフォーム固有の動作確認
    - macOS/Windows/Linuxでの動作検証

### エラーハンドリングテスト

12. **test_error_handling_invalid_paths**
    - 無効なパスに対するエラーハンドリング
    - 適切な終了コードの確認

### ファイル形式・マッチングテスト

13. **test_matching_different_raw_formats**
    - 異なるRAW形式のマッチングテスト
    - 拡張子の違いによる動作確認

14. **test_case_insensitive_matching**
    - 大文字小文字を区別しないマッチング
    - ファイル名の正規化確認

### パフォーマンステスト

15. **test_large_file_collection_simulation**
    - 大規模ファイルコレクションの模擬テスト
    - 複数サブディレクトリでの処理確認

## テストデータ

統合テストは`tests/data/`ディレクトリ内の実際のサンプルファイルを使用します：

- **test001.JPG** ↔ **test001.CR3**: マッチするペア
- **test002.jpg** ↔ **test002.cr3**: マッチするペア（大文字小文字混在）
- **test003.JPG**: マッチしないJPEGファイル
- **test004.JPG** ↔ **test004.CR3**: 撮影日時が異なるためマッチしないペア

## 実行方法

```bash
# 全ての統合テストを実行
python -m pytest tests/test_integration.py -v

# 特定のテストケースを実行
python -m pytest tests/test_integration.py::TestIntegration::test_end_to_end_workflow -v

# カバレッジ付きで実行
python -m pytest tests/test_integration.py --cov=src --cov-report=html
```

## 検証項目

### 要件1.5, 1.6 (macOSとWindowsでの動作確認)
- `test_cross_platform_path_handling`
- `test_windows_path_compatibility`
- `test_platform_specific_behavior`

### 要件3.5 (各カメラメーカーのRAW形式のテスト)
- `test_matching_different_raw_formats`
- `test_case_insensitive_matching`

### 一致するペアと一致しないペアの両方をテスト
- `test_end_to_end_workflow`
- `test_source_filter_functionality`
- `test_large_file_collection_simulation`

## 注意事項

- テストは一時ディレクトリを使用し、テスト後に自動的にクリーンアップされます
- 実際のExifToolが必要です（システムにインストールされている必要があります）
- テスト実行前後でキャッシュが自動的にクリアされます
- macOS環境での実行を前提としていますが、Windows/Linuxでも動作するように設計されています

## トラブルシューティング

### ExifToolが見つからない場合
```bash
# macOS
brew install exiftool

# Windows
# ExifToolの公式サイトからダウンロードしてPATHに追加

# Linux
sudo apt-get install libimage-exiftool-perl
```

### パス関連のエラー
- macOSでは`/private/var`と`/var`の正規化が自動的に処理されます
- Windowsでは大文字小文字を区別しないファイルシステムに対応しています

### メモリ不足エラー
- 大規模テストでメモリ不足が発生する場合は、テストデータのサイズを調整してください