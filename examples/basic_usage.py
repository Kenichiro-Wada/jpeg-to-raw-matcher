#!/usr/bin/env python3
"""
RAW-JPEG Matcher Tool - 基本的な使用例

このスクリプトは、RAW-JPEG Matcher Toolの基本的な使用方法を示します。
プログラムから直接ツールの機能を呼び出す例を提供します。
"""

import sys
from pathlib import Path

# プロジェクトのsrcディレクトリをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from index_manager import IndexManager
from match_manager import MatchManager


def example_basic_workflow():
    """基本的なワークフローの例"""
    print("=" * 60)
    print("RAW-JPEG Matcher Tool - 基本的な使用例")
    print("=" * 60)
    
    # 例用のディレクトリパス（実際の使用時は適切なパスに変更してください）
    raw_directory = Path("~/Photos/RAW_Files").expanduser()
    jpeg_directory = Path("~/Photos/Selected_JPEGs").expanduser()
    
    print(f"RAWファイルディレクトリ: {raw_directory}")
    print(f"JPEGファイルディレクトリ: {jpeg_directory}")
    print()
    
    # ディレクトリの存在確認
    if not raw_directory.exists():
        print(f"⚠️  RAWディレクトリが存在しません: {raw_directory}")
        print("実際のディレクトリパスに変更してください。")
        return
    
    if not jpeg_directory.exists():
        print(f"⚠️  JPEGディレクトリが存在しません: {jpeg_directory}")
        print("実際のディレクトリパスに変更してください。")
        return
    
    try:
        # ステップ1: RAWファイルのインデックス作成
        print("ステップ1: RAWファイルのインデックス作成")
        print("-" * 40)
        
        index_manager = IndexManager()
        index_manager.build_or_update_index(
            source_dir=raw_directory,
            recursive=True,  # サブディレクトリも検索
            force_rebuild=False,  # 差分更新を使用
            verbose=True  # 詳細ログを表示
        )
        
        print()
        
        # ステップ2: インデックス一覧の表示
        print("ステップ2: インデックス一覧の表示")
        print("-" * 40)
        
        index_manager.list_indexed_directories(verbose=True)
        
        print()
        
        # ステップ3: マッチングとコピー
        print("ステップ3: マッチングとコピー")
        print("-" * 40)
        
        match_manager = MatchManager()
        match_manager.find_and_copy_matches(
            target_dir=jpeg_directory,
            recursive=True,  # サブディレクトリも検索
            source_filter=None,  # すべてのインデックスを使用
            verbose=True  # 詳細ログを表示
        )
        
        print()
        print("✅ 処理が完了しました！")
        
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")
        return


def example_multiple_raw_sources():
    """複数のRAWソースを使用する例"""
    print("=" * 60)
    print("RAW-JPEG Matcher Tool - 複数RAWソースの例")
    print("=" * 60)
    
    # 複数のRAWディレクトリ
    raw_directories = [
        Path("~/Photos/2024/Camera1_RAW").expanduser(),
        Path("~/Photos/2024/Camera2_RAW").expanduser(),
        Path("~/Photos/2024/Phone_RAW").expanduser(),
    ]
    
    jpeg_directory = Path("~/Photos/2024/Selected_JPEGs").expanduser()
    
    print("RAWファイルディレクトリ:")
    for raw_dir in raw_directories:
        print(f"  - {raw_dir}")
    print(f"JPEGファイルディレクトリ: {jpeg_directory}")
    print()
    
    try:
        index_manager = IndexManager()
        
        # 各RAWディレクトリのインデックスを作成
        print("複数のRAWディレクトリをインデックス化中...")
        for i, raw_dir in enumerate(raw_directories, 1):
            if raw_dir.exists():
                print(f"  {i}. {raw_dir}")
                index_manager.build_or_update_index(
                    source_dir=raw_dir,
                    recursive=True,
                    force_rebuild=False,
                    verbose=False
                )
            else:
                print(f"  {i}. {raw_dir} (スキップ - ディレクトリが存在しません)")
        
        print()
        
        # インデックス一覧を表示
        print("インデックス化されたディレクトリ:")
        index_manager.list_indexed_directories(verbose=False)
        
        print()
        
        # マッチングとコピー（すべてのインデックスを使用）
        if jpeg_directory.exists():
            print("マッチングとコピーを実行中...")
            match_manager = MatchManager()
            match_manager.find_and_copy_matches(
                target_dir=jpeg_directory,
                recursive=True,
                source_filter=None,  # すべてのインデックスを使用
                verbose=True
            )
        else:
            print(f"⚠️  JPEGディレクトリが存在しません: {jpeg_directory}")
        
        print()
        print("✅ 複数ソースの処理が完了しました！")
        
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")
        return


def example_specific_source_filter():
    """特定のソースフィルタリングの例"""
    print("=" * 60)
    print("RAW-JPEG Matcher Tool - ソースフィルタリングの例")
    print("=" * 60)
    
    # 特定のRAWディレクトリのみを使用
    specific_raw_directory = Path("~/Photos/2024/Camera1_RAW").expanduser()
    jpeg_directory = Path("~/Photos/2024/Selected_JPEGs").expanduser()
    
    print(f"特定のRAWディレクトリ: {specific_raw_directory}")
    print(f"JPEGファイルディレクトリ: {jpeg_directory}")
    print()
    
    if not specific_raw_directory.exists():
        print(f"⚠️  RAWディレクトリが存在しません: {specific_raw_directory}")
        return
    
    if not jpeg_directory.exists():
        print(f"⚠️  JPEGディレクトリが存在しません: {jpeg_directory}")
        return
    
    try:
        # インデックス作成
        print("特定のRAWディレクトリをインデックス化中...")
        index_manager = IndexManager()
        index_manager.build_or_update_index(
            source_dir=specific_raw_directory,
            recursive=True,
            force_rebuild=False,
            verbose=True
        )
        
        print()
        
        # 特定のソースのみを使用してマッチング
        print("特定のソースのみを使用してマッチング中...")
        match_manager = MatchManager()
        match_manager.find_and_copy_matches(
            target_dir=jpeg_directory,
            recursive=True,
            source_filter=str(specific_raw_directory),  # 特定のソースのみ
            verbose=True
        )
        
        print()
        print("✅ ソースフィルタリングの処理が完了しました！")
        
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")
        return


def example_cache_management():
    """キャッシュ管理の例"""
    print("=" * 60)
    print("RAW-JPEG Matcher Tool - キャッシュ管理の例")
    print("=" * 60)
    
    try:
        index_manager = IndexManager()
        
        # 現在のインデックス一覧を表示
        print("現在のインデックス一覧:")
        index_manager.list_indexed_directories(verbose=True)
        
        print()
        
        # 特定ディレクトリのキャッシュをクリア
        specific_directory = Path("~/Photos/RAW_Files").expanduser()
        if input(f"'{specific_directory}' のキャッシュをクリアしますか？ (y/N): ").lower() == 'y':
            index_manager.clear_cache(source_dir=specific_directory)
            print(f"✅ '{specific_directory}' のキャッシュをクリアしました")
        
        print()
        
        # 全キャッシュをクリア
        if input("すべてのキャッシュをクリアしますか？ (y/N): ").lower() == 'y':
            index_manager.clear_cache()
            print("✅ すべてのキャッシュをクリアしました")
        
        print()
        
        # クリア後のインデックス一覧を表示
        print("クリア後のインデックス一覧:")
        index_manager.list_indexed_directories(verbose=False)
        
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")
        return


def main():
    """メイン関数 - 使用例を選択して実行"""
    print("RAW-JPEG Matcher Tool - 使用例スクリプト")
    print()
    print("実行する例を選択してください:")
    print("1. 基本的なワークフロー")
    print("2. 複数のRAWソース")
    print("3. 特定のソースフィルタリング")
    print("4. キャッシュ管理")
    print("0. 終了")
    print()
    
    while True:
        try:
            choice = input("選択 (0-4): ").strip()
            
            if choice == '0':
                print("終了します。")
                break
            elif choice == '1':
                example_basic_workflow()
            elif choice == '2':
                example_multiple_raw_sources()
            elif choice == '3':
                example_specific_source_filter()
            elif choice == '4':
                example_cache_management()
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