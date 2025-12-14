"""
RAWファイルインデックス作成モジュール

RAWファイルの情報を事前にインデックス化し、高速なマッチング処理を可能にします。
インデックス情報は永続化され、差分更新をサポートします。
"""

import json
import logging
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .exceptions import FileOperationError, ProcessingError
from .exif_reader import ExifReader
from .file_scanner import FileScanner
from .models import RawFileInfo


class RawFileIndex:
    """RAWファイル情報を保持するインデックス"""

    def __init__(self):
        """RawFileIndexを初期化"""
        self.by_basename: Dict[str, List[RawFileInfo]] = {}
        self.by_datetime: Dict[datetime, List[RawFileInfo]] = {}
        self.source_directory: Optional[Path] = None
        self.last_updated: Optional[datetime] = None
        self.file_count: int = 0
        self.logger = logging.getLogger(__name__)

    def add(self, info: RawFileInfo) -> None:
        """
        インデックスにRAWファイル情報を追加

        Args:
            info: 追加するRAWファイル情報
        """
        # ベース名でインデックス化
        if info.basename not in self.by_basename:
            self.by_basename[info.basename] = []
        self.by_basename[info.basename].append(info)

        # 撮影日時でインデックス化（日時が利用可能な場合のみ）
        if info.capture_datetime:
            if info.capture_datetime not in self.by_datetime:
                self.by_datetime[info.capture_datetime] = []
            self.by_datetime[info.capture_datetime].append(info)

        self.file_count += 1
        self.logger.debug(f"インデックスに追加: {info.path} "
                          f"(ベース名: {info.basename})")

    def remove(self, file_path: Path) -> bool:
        """
        インデックスからファイル情報を削除

        Args:
            file_path: 削除するファイルのパス

        Returns:
            削除に成功した場合True
        """
        removed = False

        # ベース名インデックスから削除
        for basename, infos in list(self.by_basename.items()):
            original_count = len(infos)
            infos[:] = [info for info in infos if info.path != file_path]
            if len(infos) < original_count:
                removed = True
                if not infos:  # リストが空になった場合はキーを削除
                    del self.by_basename[basename]

        # 日時インデックスから削除
        for dt, infos in list(self.by_datetime.items()):
            original_count = len(infos)
            infos[:] = [info for info in infos if info.path != file_path]
            if len(infos) < original_count:
                removed = True
                if not infos:  # リストが空になった場合はキーを削除
                    del self.by_datetime[dt]

        if removed:
            self.file_count -= 1
            self.logger.debug(f"インデックスから削除: {file_path}")

        return removed

    def find_by_basename(self, basename: str) -> List[RawFileInfo]:
        """
        ベース名でRAWファイルを検索

        Args:
            basename: 検索するベース名（小文字）

        Returns:
            マッチするRAWファイル情報のリスト
        """
        return self.by_basename.get(basename.lower(), [])

    def find_by_datetime(self, dt: datetime) -> List[RawFileInfo]:
        """
        撮影日時でRAWファイルを検索

        Args:
            dt: 検索する撮影日時

        Returns:
            マッチするRAWファイル情報のリスト
        """
        return self.by_datetime.get(dt, [])

    def find_by_basename_and_datetime(self, basename: str,
                                      dt: datetime) -> List[RawFileInfo]:
        """
        ベース名と撮影日時の両方でRAWファイルを検索

        Args:
            basename: 検索するベース名（小文字）
            dt: 検索する撮影日時

        Returns:
            両方の条件にマッチするRAWファイル情報のリスト
        """
        basename_matches = self.find_by_basename(basename)
        if not basename_matches:
            return []

        # 撮影日時でフィルタリング
        return [info for info in basename_matches
                if info.capture_datetime == dt]

    def get_all_files(self) -> List[RawFileInfo]:
        """
        インデックス内のすべてのRAWファイル情報を取得

        Returns:
            すべてのRAWファイル情報のリスト
        """
        all_files = []
        for infos in self.by_basename.values():
            all_files.extend(infos)
        return all_files

    def clear(self) -> None:
        """インデックスをクリア"""
        self.by_basename.clear()
        self.by_datetime.clear()
        self.file_count = 0
        self.logger.debug("インデックスをクリアしました")

    def to_dict(self) -> Dict:
        """
        インデックスを辞書形式に変換（永続化用）

        Returns:
            インデックスの辞書表現
        """
        files_data = []
        for info in self.get_all_files():
            file_data = {
                'path': str(info.path),
                'basename': info.basename,
                'capture_datetime': (info.capture_datetime.isoformat()
                                     if info.capture_datetime else None),
                'file_size': info.file_size
            }
            files_data.append(file_data)

        return {
            'source_directory': (str(self.source_directory)
                                 if self.source_directory else None),
            'last_updated': (self.last_updated.isoformat()
                             if self.last_updated else None),
            'file_count': self.file_count,
            'files': files_data
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'RawFileIndex':
        """
        辞書からインデックスを復元

        Args:
            data: インデックスの辞書表現

        Returns:
            復元されたRawFileIndex
        """
        index = cls()

        if data.get('source_directory'):
            index.source_directory = Path(data['source_directory'])

        if data.get('last_updated'):
            index.last_updated = datetime.fromisoformat(
                data['last_updated'])

        # ファイル情報を復元
        for file_data in data.get('files', []):
            capture_datetime = None
            if file_data.get('capture_datetime'):
                capture_datetime = datetime.fromisoformat(
                    file_data['capture_datetime'])

            info = RawFileInfo(
                path=Path(file_data['path']),
                basename=file_data['basename'],
                capture_datetime=capture_datetime,
                file_size=file_data['file_size']
            )
            index.add(info)

        return index


class IndexCache:
    """インデックスキャッシュ管理"""

    def __init__(self):
        """IndexCacheを初期化"""
        self.cache_dir = Path.home() / '.raw_jpeg_matcher' / 'cache'
        self.global_index_file = self.cache_dir / 'global_index.json'
        self.logger = logging.getLogger(__name__)

        # キャッシュディレクトリを作成
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get_cache_path(self, source_dir: Path) -> Path:
        """
        ソースディレクトリに対応するキャッシュファイルパスを取得

        Args:
            source_dir: ソースディレクトリ

        Returns:
            キャッシュファイルのパス
        """
        # ディレクトリパスのハッシュを作成してファイル名にする
        dir_hash = hashlib.md5(
            str(source_dir.resolve()).encode()).hexdigest()
        return self.cache_dir / f'index_{dir_hash}.json'

    def load_directory_index(self, source_dir: Path) -> Optional[RawFileIndex]:
        """
        特定ディレクトリのインデックスを読み込み

        Args:
            source_dir: ソースディレクトリ

        Returns:
            読み込まれたインデックス（存在しない場合はNone）
        """
        cache_path = self.get_cache_path(source_dir)

        if not cache_path.exists():
            self.logger.debug(f"キャッシュファイルが存在しません: {cache_path}")
            return None

        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            index = RawFileIndex.from_dict(data)
            self.logger.debug(
                f"インデックスを読み込みました: {source_dir} "
                f"({index.file_count}ファイル)")
            return index

        except Exception as e:
            self.logger.error(f"インデックス読み込みエラー: {cache_path} "
                              f"- {str(e)}")
            return None

    def save_directory_index(self, source_dir: Path,
                             index: RawFileIndex) -> None:
        """
        特定ディレクトリのインデックスを保存

        Args:
            source_dir: ソースディレクトリ
            index: 保存するインデックス

        Raises:
            FileOperationError: 保存に失敗した場合
        """
        cache_path = self.get_cache_path(source_dir)

        try:
            # インデックスの最終更新日時を設定
            index.source_directory = source_dir
            index.last_updated = datetime.now()

            # JSON形式で保存
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(index.to_dict(), f, ensure_ascii=False, indent=2)

            self.logger.debug(
                f"インデックスを保存しました: {cache_path} "
                f"({index.file_count}ファイル)")

            # グローバルインデックスも更新
            self._update_global_index(source_dir, index)

        except Exception as e:
            error_msg = f"インデックス保存エラー: {cache_path} - {str(e)}"
            self.logger.error(error_msg)
            raise FileOperationError(error_msg) from e

    def load_global_index(self) -> Dict[str, Dict]:
        """
        全ディレクトリのインデックス情報を読み込み

        Returns:
            グローバルインデックス情報の辞書
        """
        if not self.global_index_file.exists():
            return {}

        try:
            with open(self.global_index_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"グローバルインデックス読み込みエラー: {str(e)}")
            return {}

    def _update_global_index(self, source_dir: Path,
                             index: RawFileIndex) -> None:
        """
        グローバルインデックスを更新

        Args:
            source_dir: ソースディレクトリ
            index: インデックス情報
        """
        try:
            global_index = self.load_global_index()

            # ディレクトリ情報を更新
            dir_key = str(source_dir.resolve())
            global_index[dir_key] = {
                'last_updated': (index.last_updated.isoformat()
                                 if index.last_updated else None),
                'file_count': index.file_count,
                'cache_file': str(self.get_cache_path(source_dir))
            }

            # グローバルインデックスを保存
            with open(self.global_index_file, 'w', encoding='utf-8') as f:
                json.dump(global_index, f, ensure_ascii=False, indent=2)

        except Exception as e:
            self.logger.error(f"グローバルインデックス更新エラー: {str(e)}")

    def list_indexed_directories(self) -> List[Tuple[Path, datetime, int]]:
        """
        インデックス化されたディレクトリ一覧を取得

        Returns:
            (パス, 最終更新日時, ファイル数) のタプルのリスト
        """
        global_index = self.load_global_index()
        directories = []

        for dir_path, info in global_index.items():
            try:
                path = Path(dir_path)
                last_updated = (
                    datetime.fromisoformat(info['last_updated'])
                    if info.get('last_updated') else None)
                file_count = info.get('file_count', 0)

                if last_updated:
                    directories.append((path, last_updated, file_count))
            except Exception as e:
                self.logger.debug(
                    f"ディレクトリ情報の解析エラー: {dir_path} - {str(e)}")

        # 最終更新日時でソート（新しい順）
        directories.sort(key=lambda x: x[1], reverse=True)
        return directories

    def remove_directory_index(self, source_dir: Path) -> bool:
        """
        特定ディレクトリのインデックスを削除

        Args:
            source_dir: ソースディレクトリ
            
        Returns:
            削除に成功した場合True、キャッシュが見つからなかった場合False
        """
        try:
            found = False
            
            # キャッシュファイルを削除
            cache_path = self.get_cache_path(source_dir)
            if cache_path.exists():
                cache_path.unlink()
                self.logger.debug(f"キャッシュファイルを削除: {cache_path}")
                found = True

            # グローバルインデックスからも削除
            global_index = self.load_global_index()
            dir_key = str(source_dir.resolve())
            if dir_key in global_index:
                del global_index[dir_key]

                with open(self.global_index_file, 'w',
                          encoding='utf-8') as f:
                    json.dump(global_index, f, ensure_ascii=False, indent=2)

                self.logger.debug(f"グローバルインデックスから削除: {source_dir}")
                found = True
                
            return found

        except Exception as e:
            self.logger.error(f"インデックス削除エラー: {source_dir} - {str(e)}")
            return False

    def clear_all_cache(self) -> None:
        """すべてのキャッシュを削除"""
        try:
            # キャッシュディレクトリ内のすべてのファイルを削除
            if self.cache_dir.exists():
                for cache_file in self.cache_dir.glob('*.json'):
                    cache_file.unlink()
                    self.logger.debug(f"キャッシュファイルを削除: {cache_file}")

            self.logger.info("すべてのキャッシュを削除しました")

        except Exception as e:
            error_msg = f"キャッシュクリアエラー: {str(e)}"
            self.logger.error(error_msg)
            raise FileOperationError(error_msg) from e


class Indexer:
    """RAWファイルインデックス構築クラス"""

    def __init__(self, exif_reader: Optional[ExifReader] = None,
                 file_scanner: Optional[FileScanner] = None):
        """
        Indexerを初期化

        Args:
            exif_reader: Exif読み取りクラス（Noneの場合は新規作成）
            file_scanner: ファイルスキャナークラス（Noneの場合は新規作成）
        """
        self.exif_reader = exif_reader or ExifReader()
        self.file_scanner = file_scanner or FileScanner()
        self.cache = IndexCache()
        self.logger = logging.getLogger(__name__)

    def build_index(self, source_dir: Path, recursive: bool = True,
                    force_rebuild: bool = False, progress_logger=None) -> RawFileIndex:
        """
        RAWファイルのインデックスを構築（差分更新対応）

        Args:
            source_dir: ソースディレクトリ
            recursive: サブディレクトリも検索する場合True
            force_rebuild: 強制的に再構築する場合True

        Returns:
            構築されたインデックス

        Raises:
            ProcessingError: インデックス構築でエラーが発生した場合
        """
        self.logger.info(
            f"インデックス構築開始: {source_dir} "
            f"(再帰: {recursive}, 強制再構築: {force_rebuild})")

        try:
            # 既存インデックスの読み込み
            existing_index = (
                None if force_rebuild
                else self.cache.load_directory_index(source_dir))

            if existing_index and not force_rebuild:
                self.logger.info(
                    f"既存インデックスを発見: {existing_index.file_count}ファイル")
                # 差分更新を実行
                updated_index = self.update_index_incrementally(
                    existing_index, source_dir, recursive)
            else:
                self.logger.info("新規インデックスを構築します")
                # 新規インデックスを構築
                updated_index = self._build_new_index(source_dir, recursive)

            # インデックスを保存
            self.cache.save_directory_index(source_dir, updated_index)

            self.logger.info(f"インデックス構築完了: {updated_index.file_count}ファイル")
            return updated_index

        except Exception as e:
            error_msg = f"インデックス構築エラー: {source_dir} - {str(e)}"
            self.logger.error(error_msg)
            raise ProcessingError(error_msg) from e

    def update_index_incrementally(self, index: RawFileIndex,
                                   source_dir: Path,
                                   recursive: bool) -> RawFileIndex:
        """
        インデックスの差分更新

        Args:
            index: 既存のインデックス
            source_dir: ソースディレクトリ
            recursive: サブディレクトリも検索する場合True

        Returns:
            更新されたインデックス
        """
        self.logger.info("差分更新を開始します")

        # 現在のファイルシステムをスキャン
        current_files = set(
            self.file_scanner.scan_raw_files(source_dir, recursive))

        # インデックス内の既存ファイル
        existing_files = {info.path for info in index.get_all_files()}

        # 新規ファイル、削除されたファイル、更新されたファイルを特定
        new_files = current_files - existing_files
        deleted_files = existing_files - current_files
        potentially_updated_files = current_files & existing_files

        self.logger.info(
            f"差分分析: 新規={len(new_files)}, 削除={len(deleted_files)}, "
            f"更新候補={len(potentially_updated_files)}")

        # 削除されたファイルをインデックスから除去
        for deleted_file in deleted_files:
            index.remove(deleted_file)
            self.logger.debug(
                f"削除されたファイルをインデックスから除去: {deleted_file}")

        # 更新されたファイルをチェック（ファイルサイズや更新日時で判定）
        updated_files = []
        for file_path in potentially_updated_files:
            try:
                current_stat = file_path.stat()
                # インデックス内の既存情報を取得
                existing_info = None
                for info in index.get_all_files():
                    if info.path == file_path:
                        existing_info = info
                        break

                if (existing_info and
                        existing_info.file_size != current_stat.st_size):
                    # ファイルサイズが変更されている場合は更新対象
                    updated_files.append(file_path)
                    index.remove(file_path)  # 古い情報を削除

            except Exception as e:
                self.logger.debug(
                    f"ファイル状態チェックエラー: {file_path} - {str(e)}")

        # 新規ファイルと更新されたファイルを処理
        files_to_process = list(new_files) + updated_files

        if files_to_process:
            self.logger.info(f"処理対象ファイル: {len(files_to_process)}個")
            processed_infos = self._process_files_parallel(files_to_process)

            # インデックスに追加
            for info in processed_infos:
                index.add(info)

        self.logger.info(f"差分更新完了: 最終ファイル数={index.file_count}")
        return index

    def _build_new_index(self, source_dir: Path,
                         recursive: bool) -> RawFileIndex:
        """
        新規インデックスを構築

        Args:
            source_dir: ソースディレクトリ
            recursive: サブディレクトリも検索する場合True

        Returns:
            新規構築されたインデックス
        """
        # RAWファイルをスキャン
        raw_files = self.file_scanner.scan_raw_files(source_dir, recursive)
        self.logger.info(f"RAWファイルを発見: {len(raw_files)}個")

        if not raw_files:
            self.logger.warning("RAWファイルが見つかりませんでした")
            return RawFileIndex()

        # 並列処理でファイル情報を取得
        processed_infos = self._process_files_parallel(raw_files)

        # インデックスを構築
        index = RawFileIndex()
        for info in processed_infos:
            index.add(info)

        return index

    def _process_files_parallel(self, file_paths: List[Path],
                                max_workers: int = 4) -> List[RawFileInfo]:
        """
        ファイルを並列処理してRawFileInfo を作成

        Args:
            file_paths: 処理するファイルパスのリスト
            max_workers: 最大ワーカー数

        Returns:
            処理されたRawFileInfoのリスト
        """
        processed_infos = []

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # ファイル処理タスクを投入
            future_to_path = {
                executor.submit(self._process_single_file, file_path):
                file_path for file_path in file_paths
            }

            # 結果を収集
            for future in as_completed(future_to_path):
                file_path = future_to_path[future]
                try:
                    info = future.result()
                    if info:
                        processed_infos.append(info)
                except Exception as e:
                    self.logger.error(
                        f"ファイル処理エラー: {file_path} - {str(e)}")

        self.logger.info(
            f"並列処理完了: {len(processed_infos)}/{len(file_paths)}ファイル")
        return processed_infos

    def _process_single_file(self, file_path: Path) -> Optional[RawFileInfo]:
        """
        単一ファイルを処理してRawFileInfoを作成

        Args:
            file_path: 処理するファイルパス

        Returns:
            作成されたRawFileInfo（エラーの場合はNone）
        """
        try:
            # ファイル情報を取得
            stat_info = file_path.stat()
            basename = self.file_scanner.get_basename(file_path)

            # Exif情報を読み取り
            capture_datetime = None
            try:
                capture_datetime = self.exif_reader.read_capture_datetime(
                    file_path)
            except Exception as e:
                self.logger.debug(
                    f"Exif読み取りエラー（処理継続）: {file_path} - {str(e)}")

            # RawFileInfoを作成
            info = RawFileInfo(
                path=file_path,
                basename=basename,
                capture_datetime=capture_datetime,
                file_size=stat_info.st_size
            )

            self.logger.debug(f"ファイル処理完了: {file_path}")
            return info

        except Exception as e:
            self.logger.error(f"ファイル処理エラー: {file_path} - {str(e)}")
            return None

    def clear_cache(self, source_dir: Optional[Path] = None) -> None:
        """
        キャッシュをクリア

        Args:
            source_dir: 特定ディレクトリのキャッシュのみクリア（Noneの場合は全体）
        """
        if source_dir:
            self.cache.remove_directory_index(source_dir)
            self.logger.info(f"キャッシュをクリア: {source_dir}")
        else:
            self.cache.clear_all_cache()
            self.logger.info("すべてのキャッシュをクリア")