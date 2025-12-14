"""
コマンドラインインターフェース

RAW-JPEG Matcher Toolのメインエントリーポイントです。
argparseのサブコマンド機能を使用して、index、match、list-index、clear-cacheコマンドを提供します。
"""

import argparse
import sys
from pathlib import Path
from typing import Optional

from .exceptions import ProcessingError, ValidationError
from .index_manager import IndexManager
from .match_manager import MatchManager
from .path_validator import PathValidator


def create_parser() -> argparse.ArgumentParser:
    """
    コマンドライン引数パーサーを作成
    
    Returns:
        設定済みのArgumentParser
    """
    parser = argparse.ArgumentParser(
        prog='raw-jpeg-matcher',
        description='JPEGファイルに対応するRAWファイルを検索してコピーするツール',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  # RAWファイルのインデックスを作成
  raw-jpeg-matcher index /path/to/raw/files
  
  # JPEGファイルに対応するRAWファイルを検索してコピー
  raw-jpeg-matcher match /path/to/jpeg/files
  
  # インデックス化されたディレクトリ一覧を表示
  raw-jpeg-matcher list-index
  
  # インデックスキャッシュをクリア
  raw-jpeg-matcher clear-cache

詳細については各サブコマンドのヘルプを参照してください:
  raw-jpeg-matcher <command> --help
        """
    )
    
    # サブコマンドを作成
    subparsers = parser.add_subparsers(
        dest='command',
        help='利用可能なコマンド',
        metavar='<command>'
    )
    
    # indexコマンド（エイリアス: i）
    index_parser = subparsers.add_parser(
        'index',
        aliases=['i'],
        help='RAWファイルのインデックスを作成・更新',
        description='指定されたディレクトリ内のRAWファイルをスキャンしてインデックスを作成または更新します。',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  # 基本的な使用方法
  raw-jpeg-matcher index /path/to/raw/files
  
  # サブディレクトリを検索しない
  raw-jpeg-matcher index /path/to/raw/files --no-recursive
  
  # 詳細ログを表示
  raw-jpeg-matcher index /path/to/raw/files --verbose
  
  # 強制的に再構築
  raw-jpeg-matcher index /path/to/raw/files --force-rebuild
        """
    )
    index_parser.add_argument(
        'source',
        type=str,
        help='RAWファイルのソースディレクトリパス'
    )
    index_parser.add_argument(
        '--no-recursive', '-nr',
        action='store_true',
        help='サブディレクトリを検索しない（デフォルトは再帰的に検索）'
    )
    index_parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='詳細ログを表示'
    )
    index_parser.add_argument(
        '--force-rebuild', '-f',
        action='store_true',
        help='該当ディレクトリのインデックスを強制的に再構築'
    )
    
    # matchコマンド（エイリアス: m）
    match_parser = subparsers.add_parser(
        'match',
        aliases=['m'],
        help='JPEGファイルに対応するRAWファイルを検索してコピー',
        description='指定されたディレクトリ内のJPEGファイルに対応するRAWファイルを検索し、同じディレクトリにコピーします。',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  # 基本的な使用方法
  raw-jpeg-matcher match /path/to/jpeg/files
  
  # サブディレクトリを検索しない
  raw-jpeg-matcher match /path/to/jpeg/files --no-recursive
  
  # 詳細ログを表示
  raw-jpeg-matcher match /path/to/jpeg/files --verbose
  
  # 特定のソースディレクトリのRAWファイルのみを対象
  raw-jpeg-matcher match /path/to/jpeg/files --source-filter /path/to/specific/raw/files
        """
    )
    match_parser.add_argument(
        'target',
        type=str,
        help='JPEGファイルのターゲットディレクトリパス'
    )
    match_parser.add_argument(
        '--no-recursive', '-nr',
        action='store_true',
        help='サブディレクトリを検索しない（デフォルトは再帰的に検索）'
    )
    match_parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='詳細ログを表示'
    )
    match_parser.add_argument(
        '--source-filter', '-s',
        type=str,
        help='特定のソースディレクトリのRAWファイルのみを対象にする'
    )
    
    # list-indexコマンド（エイリアス: l）
    list_parser = subparsers.add_parser(
        'list-index',
        aliases=['l'],
        help='インデックス化されたディレクトリ一覧を表示',
        description='現在インデックス化されているディレクトリの一覧と統計情報を表示します。',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  # 基本的な一覧表示
  raw-jpeg-matcher list-index
  
  # 詳細情報を表示
  raw-jpeg-matcher list-index --verbose
        """
    )
    list_parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='詳細情報を表示'
    )
    
    # clear-cacheコマンド（エイリアス: c）
    cache_parser = subparsers.add_parser(
        'clear-cache',
        aliases=['c'],
        help='インデックスキャッシュをクリア',
        description='インデックスキャッシュを削除します。特定のディレクトリまたは全体のキャッシュをクリアできます。',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  # 全体のキャッシュをクリア
  raw-jpeg-matcher clear-cache
  
  # 特定ディレクトリのキャッシュのみクリア
  raw-jpeg-matcher clear-cache --source /path/to/raw/files
        """
    )
    cache_parser.add_argument(
        '--source', '-s',
        type=str,
        help='特定のソースディレクトリのキャッシュのみクリア（省略時は全体）'
    )
    
    return parser


def handle_index_command(args) -> int:
    """
    indexコマンドを処理
    
    Args:
        args: 解析されたコマンドライン引数
        
    Returns:
        終了コード（0: 成功、1: エラー）
    """
    try:
        source_path = Path(args.source)
        
        # パス検証
        PathValidator.validate_directory(source_path)
        
        # IndexManagerを使用してインデックス作成
        index_manager = IndexManager()
        recursive = not args.no_recursive  # デフォルトはTrue
        
        index_manager.build_or_update_index(
            source_dir=source_path,
            recursive=recursive,
            force_rebuild=args.force_rebuild,
            verbose=args.verbose
        )
        
        return 0
        
    except ValidationError as e:
        print(f"❌ 入力エラー: {e}", file=sys.stderr)
        return 1
    except ProcessingError as e:
        print(f"❌ 処理エラー: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"❌ 予期しないエラー: {e}", file=sys.stderr)
        return 1


def handle_match_command(args) -> int:
    """
    matchコマンドを処理
    
    Args:
        args: 解析されたコマンドライン引数
        
    Returns:
        終了コード（0: 成功、1: エラー）
    """
    try:
        target_path = Path(args.target)
        
        # パス検証
        PathValidator.validate_directory(target_path)
        
        # ソースフィルターが指定されている場合は検証
        if args.source_filter:
            source_filter_path = Path(args.source_filter)
            PathValidator.validate_directory(source_filter_path)
        
        # MatchManagerを使用してマッチング処理
        match_manager = MatchManager()
        recursive = not args.no_recursive  # デフォルトはTrue
        
        match_manager.find_and_copy_matches(
            target_dir=target_path,
            recursive=recursive,
            source_filter=args.source_filter,
            verbose=args.verbose
        )
        
        return 0
        
    except ValidationError as e:
        print(f"❌ 入力エラー: {e}", file=sys.stderr)
        return 1
    except ProcessingError as e:
        print(f"❌ 処理エラー: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"❌ 予期しないエラー: {e}", file=sys.stderr)
        return 1


def handle_list_index_command(args) -> int:
    """
    list-indexコマンドを処理
    
    Args:
        args: 解析されたコマンドライン引数
        
    Returns:
        終了コード（0: 成功、1: エラー）
    """
    try:
        # IndexManagerを使用してディレクトリ一覧表示
        index_manager = IndexManager()
        index_manager.list_indexed_directories(verbose=args.verbose)
        
        return 0
        
    except ProcessingError as e:
        print(f"❌ 処理エラー: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"❌ 予期しないエラー: {e}", file=sys.stderr)
        return 1


def handle_clear_cache_command(args) -> int:
    """
    clear-cacheコマンドを処理
    
    Args:
        args: 解析されたコマンドライン引数
        
    Returns:
        終了コード（0: 成功、1: エラー）
    """
    try:
        source_path = None
        if args.source:
            source_path = Path(args.source)
            # 存在チェックはしない（削除済みディレクトリのキャッシュもクリアできるように）
        
        # IndexManagerを使用してキャッシュクリア
        index_manager = IndexManager()
        index_manager.clear_cache(source_dir=source_path)
        
        return 0
        
    except ProcessingError as e:
        print(f"❌ 処理エラー: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"❌ 予期しないエラー: {e}", file=sys.stderr)
        return 1


def main() -> int:
    """
    メインエントリーポイント
    
    Returns:
        終了コード（0: 成功、1: エラー）
    """
    parser = create_parser()
    
    # 引数が指定されていない場合はヘルプを表示
    if len(sys.argv) == 1:
        parser.print_help()
        return 0
    
    args = parser.parse_args()
    
    # コマンドが指定されていない場合はヘルプを表示
    if not args.command:
        parser.print_help()
        return 0
    
    # 各コマンドの処理を実行
    if args.command in ['index', 'i']:
        return handle_index_command(args)
    elif args.command in ['match', 'm']:
        return handle_match_command(args)
    elif args.command in ['list-index', 'l']:
        return handle_list_index_command(args)
    elif args.command in ['clear-cache', 'c']:
        return handle_clear_cache_command(args)
    else:
        print(f"❌ 不明なコマンド: {args.command}", file=sys.stderr)
        parser.print_help()
        return 1


if __name__ == '__main__':
    sys.exit(main())