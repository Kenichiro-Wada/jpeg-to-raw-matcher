#!/usr/bin/env python3
"""
RAW-JPEG Matcher Tool - 高度な使用例

このスクリプトは、RAW-JPEG Matcher Toolの高度な機能と
カスタマイズされた使用方法を示します。
"""

import sys
import time
from pathlib import Path
from typing import List, Optional

# プロジェクトのsrcディレクトリをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from exif_reader import ExifReader
from file_scanner import FileScanner
from indexer import Indexer, IndexCache
from matcher import Matcher
from copier import Copier
from models import RawFileInfo, JpegFileInfo, MatchResult
from logger import create_default_logger, get_default_log_file


def example_custom_matching_logic():
    """カスタムマッチングロジックの例"""
    print("=" * 60)
    print("カスタムマッチングロジックの例")
    print("=" * 60)
    
    # テスト用のディレクトリ
    raw_directory = Path("tests/data")  # テストデータを使用
    jpeg_directory = Path("tests/data")
    
    if not raw_directory.exists() or not jpeg_directory.exists():
        print("⚠️  テストデータディレクトリが見つかりません")
        print("このスクリプトはプロジェクトルートから実行してください")
        return
    
    try:
        # 各コンポーネントを個別に初期化
        exif_reader = ExifReader()
        file_scanner = FileScanner()
        indexer = Indexer(exif_reader, file_scanner)
        
        print("1. RAWファイルのインデックス作成...")
        
        # インデックスを構築
        index = indexer.build_index(raw_directory, recursive=False, force_rebuild=True)
        
        print(f"   インデックス作成完了: {index.file_count}ファイル")
        print()
        
        print("2. JPEGファイルのスキャン...")
        
        # JPEGファイルをスキャン
        jpeg_files = file_scanner.scan_jpeg_files(jpeg_directory, recursive=False)
        print(f"   JPEGファイル発見: {len(jpeg_files)}個")
        
        # 各JPEGファイルの詳細情報を表示
        for jpeg_file in jpeg_files:
            basename = file_scanner.get_basename(jpeg_file)
            capture_datetime = exif_reader.read_capture_datetime(jpeg_file)
            print(f"   - {jpeg_file.name}: ベース名={basename}, 撮影日時={capture_datetime}")
        
        print()
        
        print("3. カスタムマッチング処理...")
        
        # マッチャーを初期化
        matcher = Matcher(exif_reader, index)
        
        # マッチングを実行
        matches = matcher.find_matches(jpeg_files)
        
        print(f"   マッチ発見: {len(matches)}個")
        
        # マッチング結果の詳細表示
        for i, match in enumerate(matches, 1):
            print(f"   {i}. {match.jpeg_path.name} -> {match.raw_path.name}")
            print(f"      マッチ方法: {match.match_method}")
        
        print()
        
        # マッチング統計を表示
        stats = matcher.get_match_statistics(matches)
        print("マッチング統計:")
        print(f"  - 総マッチ数: {stats['total_matches']}")
        print(f"  - ファイル名+日時マッチ: {stats['basename_and_datetime_matches']}")
        print(f"  - ファイル名のみマッチ: {stats['basename_only_matches']}")
        
        print()
        print("✅ カスタムマッチング処理が完了しました！")
        
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()


def example_batch_processing():
    """バッチ処理の例"""
    print("=" * 60)
    print("バッチ処理の例")
    print("=" * 60)
    
    # 複数のディレクトリペアを定義
    directory_pairs = [
        {
            'raw_dir': Path("~/Photos/2024/01_January/RAW").expanduser(),
            'jpeg_dir': Path("~/Photos/2024/01_January/Selected").expanduser(),
        },
        {
            'raw_dir': Path("~/Photos/2024/02_February/RAW").expanduser(),
            'jpeg_dir': Path("~/Photos/2024/02_February/Selected").expanduser(),
        },
        {
            'raw_dir': Path("~/Photos/2024/03_March/RAW").expanduser(),
            'jpeg_dir': Path("~/Photos/2024/03_March/Selected").expanduser(),
        },
    ]
    
    print("バッチ処理対象:")
    for i, pair in enumerate(directory_pairs, 1):
        print(f"  {i}. RAW: {pair['raw_dir']}")
        print(f"     JPEG: {pair['jpeg_dir']}")
    
    print()
    
    try:
        # 各コンポーネントを初期化
        exif_reader = ExifReader()
        file_scanner = FileScanner()
        indexer = Indexer(exif_reader, file_scanner)
        copier = Copier()
        
        # ログ設定
        log_file = get_default_log_file()
        logger = create_default_logger(verbose=True, log_file=log_file)
        
        total_processed = 0
        total_matches = 0
        total_copied = 0
        
        # 各ディレクトリペアを処理
        for i, pair in enumerate(directory_pairs, 1):
            raw_dir = pair['raw_dir']
            jpeg_dir = pair['jpeg_dir']
            
            print(f"処理中 {i}/{len(directory_pairs)}: {raw_dir.name}")
            
            # ディレクトリの存在確認
            if not raw_dir.exists():
                print(f"  ⚠️  RAWディレクトリが存在しません: {raw_dir}")
                continue
            
            if not jpeg_dir.exists():
                print(f"  ⚠️  JPEGディレクトリが存在しません: {jpeg_dir}")
                continue
            
            try:
                # インデックス作成
                print(f"  インデックス作成中...")
                index = indexer.build_index(raw_dir, recursive=True, force_rebuild=False)
                
                # JPEGファイルスキャン
                jpeg_files = file_scanner.scan_jpeg_files(jpeg_dir, recursive=True)
                print(f"  JPEGファイル: {len(jpeg_files)}個")
                
                if not jpeg_files:
                    print(f"  スキップ: JPEGファイルが見つかりません")
                    continue
                
                # マッチング
                matcher = Matcher(exif_reader, index)
                matches = matcher.find_matches(jpeg_files)
                print(f"  マッチ: {len(matches)}個")
                
                if matches:
                    # コピー実行
                    copy_result = copier.copy_files(matches, jpeg_dir)
                    print(f"  コピー: 成功={copy_result.success}, スキップ={copy_result.skipped}, 失敗={copy_result.failed}")
                    
                    total_copied += copy_result.success
                
                total_processed += len(jpeg_files)
                total_matches += len(matches)
                
            except Exception as e:
                print(f"  ❌ エラー: {e}")
                continue
            
            print()
        
        # 最終サマリー
        print("=" * 40)
        print("バッチ処理完了サマリー")
        print("=" * 40)
        print(f"処理したディレクトリペア: {len(directory_pairs)}")
        print(f"総JPEGファイル数: {total_processed}")
        print(f"総マッチ数: {total_matches}")
        print(f"総コピー数: {total_copied}")
        print(f"詳細ログ: {log_file}")
        
        print()
        print("✅ バッチ処理が完了しました！")
        
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()


def example_performance_monitoring():
    """パフォーマンス監視の例"""
    print("=" * 60)
    print("パフォーマンス監視の例")
    print("=" * 60)
    
    # テスト用のディレクトリ
    test_directory = Path("tests/data")
    
    if not test_directory.exists():
        print("⚠️  テストデータディレクトリが見つかりません")
        return
    
    try:
        # 各コンポーネントを初期化
        exif_reader = ExifReader()
        file_scanner = FileScanner()
        indexer = Indexer(exif_reader, file_scanner)
        
        print("パフォーマンステスト開始...")
        print()
        
        # 1. ファイルスキャンのパフォーマンス
        print("1. ファイルスキャンのパフォーマンス")
        start_time = time.time()
        
        raw_files = file_scanner.scan_raw_files(test_directory, recursive=True)
        jpeg_files = file_scanner.scan_jpeg_files(test_directory, recursive=True)
        
        scan_time = time.time() - start_time
        print(f"   スキャン時間: {scan_time:.3f}秒")
        print(f"   RAWファイル: {len(raw_files)}個")
        print(f"   JPEGファイル: {len(jpeg_files)}個")
        print()
        
        # 2. Exif読み取りのパフォーマンス
        print("2. Exif読み取りのパフォーマンス")
        start_time = time.time()
        
        exif_success = 0
        exif_failed = 0
        
        all_files = raw_files + jpeg_files
        for file_path in all_files:
            try:
                capture_datetime = exif_reader.read_capture_datetime(file_path)
                if capture_datetime:
                    exif_success += 1
                else:
                    exif_failed += 1
            except Exception:
                exif_failed += 1
        
        exif_time = time.time() - start_time
        print(f"   Exif読み取り時間: {exif_time:.3f}秒")
        print(f"   成功: {exif_success}個")
        print(f"   失敗: {exif_failed}個")
        print(f"   平均時間/ファイル: {exif_time/len(all_files):.3f}秒")
        print()
        
        # 3. インデックス構築のパフォーマンス
        print("3. インデックス構築のパフォーマンス")
        start_time = time.time()
        
        index = indexer.build_index(test_directory, recursive=True, force_rebuild=True)
        
        index_time = time.time() - start_time
        print(f"   インデックス構築時間: {index_time:.3f}秒")
        print(f"   インデックスファイル数: {index.file_count}")
        print(f"   ベース名エントリ数: {len(index.by_basename)}")
        print(f"   日時エントリ数: {len(index.by_datetime)}")
        print()
        
        # 4. マッチングのパフォーマンス
        print("4. マッチングのパフォーマンス")
        start_time = time.time()
        
        matcher = Matcher(exif_reader, index)
        matches = matcher.find_matches(jpeg_files)
        
        match_time = time.time() - start_time
        print(f"   マッチング時間: {match_time:.3f}秒")
        print(f"   マッチ数: {len(matches)}")
        if jpeg_files:
            print(f"   平均時間/JPEGファイル: {match_time/len(jpeg_files):.3f}秒")
        print()
        
        # 5. キャッシュ効果の確認
        print("5. キャッシュ効果の確認")
        print(f"   Exifキャッシュサイズ: {exif_reader.get_cache_size()}")
        
        # 2回目のExif読み取り（キャッシュ効果を確認）
        start_time = time.time()
        for file_path in all_files[:5]:  # 最初の5ファイルのみテスト
            exif_reader.read_capture_datetime(file_path)
        cached_time = time.time() - start_time
        
        print(f"   キャッシュ済み読み取り時間（5ファイル）: {cached_time:.3f}秒")
        print()
        
        # 総合パフォーマンスサマリー
        total_time = scan_time + exif_time + index_time + match_time
        print("=" * 40)
        print("パフォーマンスサマリー")
        print("=" * 40)
        print(f"総処理時間: {total_time:.3f}秒")
        print(f"  - ファイルスキャン: {scan_time:.3f}秒 ({scan_time/total_time*100:.1f}%)")
        print(f"  - Exif読み取り: {exif_time:.3f}秒 ({exif_time/total_time*100:.1f}%)")
        print(f"  - インデックス構築: {index_time:.3f}秒 ({index_time/total_time*100:.1f}%)")
        print(f"  - マッチング: {match_time:.3f}秒 ({match_time/total_time*100:.1f}%)")
        
        print()
        print("✅ パフォーマンス監視が完了しました！")
        
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()


def example_error_handling():
    """エラーハンドリングの例"""
    print("=" * 60)
    print("エラーハンドリングの例")
    print("=" * 60)
    
    try:
        # 各コンポーネントを初期化
        exif_reader = ExifReader()
        file_scanner = FileScanner()
        
        print("1. 存在しないディレクトリの処理")
        try:
            non_existent_dir = Path("/non/existent/directory")
            raw_files = file_scanner.scan_raw_files(non_existent_dir)
        except Exception as e:
            print(f"   期待されるエラー: {type(e).__name__}: {e}")
        
        print()
        
        print("2. 存在しないファイルのExif読み取り")
        try:
            non_existent_file = Path("/non/existent/file.jpg")
            capture_datetime = exif_reader.read_capture_datetime(non_existent_file)
        except Exception as e:
            print(f"   期待されるエラー: {type(e).__name__}: {e}")
        
        print()
        
        print("3. 破損ファイルの処理")
        # 空のファイルを作成してテスト
        temp_file = Path("temp_empty_file.jpg")
        try:
            temp_file.touch()  # 空のファイルを作成
            capture_datetime = exif_reader.read_capture_datetime(temp_file)
            print(f"   空ファイルの処理結果: {capture_datetime}")
        except Exception as e:
            print(f"   空ファイルエラー: {type(e).__name__}: {e}")
        finally:
            if temp_file.exists():
                temp_file.unlink()  # 一時ファイルを削除
        
        print()
        
        print("4. ExifTool利用可能性チェック")
        try:
            is_available = exif_reader.check_exiftool_availability()
            print(f"   ExifTool利用可能: {is_available}")
        except Exception as e:
            print(f"   ExifToolエラー: {type(e).__name__}: {e}")
        
        print()
        
        print("5. キャッシュ操作")
        try:
            cache = IndexCache()
            
            # 存在しないディレクトリのキャッシュ読み込み
            non_existent_dir = Path("/non/existent/directory")
            index = cache.load_directory_index(non_existent_dir)
            print(f"   存在しないディレクトリのキャッシュ: {index}")
            
            # インデックス一覧の取得
            directories = cache.list_indexed_directories()
            print(f"   インデックス化されたディレクトリ数: {len(directories)}")
            
        except Exception as e:
            print(f"   キャッシュエラー: {type(e).__name__}: {e}")
        
        print()
        print("✅ エラーハンドリングテストが完了しました！")
        
    except Exception as e:
        print(f"❌ 予期しないエラー: {e}")
        import traceback
        traceback.print_exc()


def main():
    """メイン関数 - 高度な使用例を選択して実行"""
    print("RAW-JPEG Matcher Tool - 高度な使用例スクリプト")
    print()
    print("実行する例を選択してください:")
    print("1. カスタムマッチングロジック")
    print("2. バッチ処理")
    print("3. パフォーマンス監視")
    print("4. エラーハンドリング")
    print("0. 終了")
    print()
    
    while True:
        try:
            choice = input("選択 (0-4): ").strip()
            
            if choice == '0':
                print("終了します。")
                break
            elif choice == '1':
                example_custom_matching_logic()
            elif choice == '2':
                example_batch_processing()
            elif choice == '3':
                example_performance_monitoring()
            elif choice == '4':
                example_error_handling()
            else:
                print("無効な選択です。0-4の数字を入力してください。")
                continue
            
            print()
            if input("他の例を実行しますか？ (y/N): ").lower() != 'y':
                break
            print()
            
        except KeyboardInterrupt:
            print("\n\n処理が中断されました。")
            break
        except Exception as e:
            print(f"❌ 予期しないエラー: {e}")
            break


if __name__ == '__main__':
    main()