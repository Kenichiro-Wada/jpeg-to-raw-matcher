"""
ファイルコピー処理モジュール

マッチしたRAWファイルをターゲットディレクトリにコピーする機能を提供します。
既存ファイルのスキップ処理、エラーハンドリング、ディスク容量チェックを含みます。
"""

import logging
import shutil
from pathlib import Path
from typing import List, Optional, Tuple

from .models import CopyResult, MatchResult


class Copier:
    """RAWファイルをコピーするクラス"""

    def __init__(self):
        """Copierを初期化"""
        self.logger = logging.getLogger(__name__)

    def copy_files(
        self, matches: List[MatchResult], target_dir: Path, progress_logger=None
    ) -> CopyResult:
        """
        マッチしたRAWファイルをターゲットディレクトリにコピー

        Args:
            matches: マッチング結果のリスト
            target_dir: コピー先ディレクトリ

        Returns:
            コピー結果
        """
        success_count = 0
        skipped_count = 0
        failed_count = 0
        errors = []

        self.logger.info(
            f"ファイルコピー開始: {len(matches)}個のファイル -> {target_dir}"
        )

        # ターゲットディレクトリが存在しない場合は作成
        try:
            target_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            error_msg = f"ターゲットディレクトリ作成失敗: {e}"
            self.logger.error(error_msg)
            return CopyResult(
                success=0,
                skipped=0,
                failed=len(matches),
                errors=[(target_dir, error_msg)]
            )

        for i, match in enumerate(matches):
            try:
                # 進捗表示
                if progress_logger:
                    progress_logger.log_copy_progress(len(matches), i, match.raw_path)
                
                result, error_msg = self._copy_single_file_with_error(match, target_dir)

                if result == 'success':
                    success_count += 1
                elif result == 'skipped':
                    skipped_count += 1
                else:  # failed
                    failed_count += 1
                    if error_msg:
                        errors.append((match.raw_path, error_msg))
                        # エラーログ
                        if progress_logger:
                            progress_logger.log_error(match.raw_path, error_msg)
                        else:
                            self.logger.error(f"ファイルコピーエラー: {match.raw_path} - {error_msg}")
                            
            except Exception as e:
                failed_count += 1
                error_msg = f"予期しないエラー: {e}"
                errors.append((match.raw_path, error_msg))
                
                # エラーログ
                if progress_logger:
                    progress_logger.log_error(match.raw_path, error_msg, e)
                else:
                    self.logger.error(f"ファイルコピーエラー: {match.raw_path} - {error_msg}")

        self.logger.info(
            f"ファイルコピー完了: 成功={success_count}, "
            f"スキップ={skipped_count}, 失敗={failed_count}"
        )
        return CopyResult(
            success=success_count,
            skipped=skipped_count,
            failed=failed_count,
            errors=errors
        )

    def _copy_single_file_with_error(self, match: MatchResult, target_dir: Path) -> Tuple[str, Optional[str]]:
        """
        単一ファイルをコピー（エラーメッセージ付き）

        Args:
            match: マッチング結果
            target_dir: コピー先ディレクトリ

        Returns:
            (結果文字列, エラーメッセージ) のタプル
            結果文字列: 'success', 'skipped', 'failed'
            エラーメッセージ: エラーが発生した場合のメッセージ、それ以外はNone
        """
        source_path = match.raw_path
        target_path = target_dir / source_path.name

        # ソースファイルの存在確認
        if not source_path.exists():
            error_msg = "ソースファイルが存在しません"
            self.logger.warning(f"コピースキップ: {source_path} - {error_msg}")
            return 'failed', error_msg

        # 既存ファイルのスキップ処理
        if target_path.exists():
            self.logger.debug(f"既存ファイルをスキップ: {target_path.name}")
            return 'skipped', None

        # ディスク容量チェック
        try:
            source_size = source_path.stat().st_size
            if not self._check_disk_space(target_dir, source_size):
                error_msg = "ディスク容量不足"
                self.logger.error(f"コピー失敗: {source_path} - {error_msg}")
                return 'failed', error_msg
        except Exception as e:
            error_msg = f"ファイルサイズ取得エラー: {e}"
            self.logger.warning(f"ディスク容量チェックスキップ: {source_path} - {error_msg}")
            # ディスク容量チェックに失敗してもコピーは継続

        # ファイルコピー実行
        try:
            # shutil.copy2を使用してメタデータも保持
            shutil.copy2(source_path, target_path)
            self.logger.debug(f"コピー成功: {source_path.name} -> {target_path}")
            return 'success', None
        except PermissionError as e:
            error_msg = f"アクセス権限エラー: {e}"
            self.logger.error(f"コピー失敗: {source_path} - {error_msg}")
            return 'failed', error_msg
        except OSError as e:
            error_msg = f"ファイル操作エラー: {e}"
            self.logger.error(f"コピー失敗: {source_path} - {error_msg}")
            return 'failed', error_msg

    def _copy_single_file(self, match: MatchResult, target_dir: Path) -> str:
        """
        単一ファイルをコピー

        Args:
            match: マッチング結果
            target_dir: コピー先ディレクトリ

        Returns:
            結果文字列 ('success', 'skipped', 'failed')
        """
        source_path = match.raw_path
        target_path = target_dir / source_path.name

        # ソースファイルの存在確認
        if not source_path.exists():
            error_msg = "ソースファイルが存在しません"
            self.logger.warning(f"コピースキップ: {source_path} - {error_msg}")
            return 'failed'

        # 既存ファイルのスキップ処理
        if target_path.exists():
            self.logger.debug(f"既存ファイルをスキップ: {target_path.name}")
            return 'skipped'

        # ディスク容量チェック
        try:
            source_size = source_path.stat().st_size
            if not self._check_disk_space(target_dir, source_size):
                error_msg = "ディスク容量不足"
                self.logger.error(
                    f"コピー失敗: {source_path} - {error_msg}"
                )
                return 'failed'
        except Exception as e:
            error_msg = f"ファイルサイズ取得エラー: {e}"
            self.logger.warning(
                f"ディスク容量チェックスキップ: {source_path} - {error_msg}"
            )
            # ディスク容量チェックに失敗してもコピーは継続

        # ファイルコピー実行
        try:
            # shutil.copy2を使用してメタデータも保持
            shutil.copy2(source_path, target_path)
            self.logger.debug(
                f"コピー成功: {source_path.name} -> {target_path}"
            )
            return 'success'
        except PermissionError as e:
            error_msg = f"アクセス権限エラー: {e}"
            self.logger.error(f"コピー失敗: {source_path} - {error_msg}")
            return 'failed'

        except OSError as e:
            error_msg = f"ファイル操作エラー: {e}"
            self.logger.error(f"コピー失敗: {source_path} - {error_msg}")
            return 'failed'

        except Exception as e:
            error_msg = f"予期しないコピーエラー: {e}"
            self.logger.error(f"コピー失敗: {source_path} - {error_msg}")
            return 'failed'

    def _check_disk_space(self, target_dir: Path, required_bytes: int) -> bool:
        """
        ディスク空き容量を確認

        Args:
            target_dir: 確認対象ディレクトリ
            required_bytes: 必要なバイト数

        Returns:
            容量が十分な場合True
        """
        try:
            # ディスク使用量を取得
            stat = shutil.disk_usage(target_dir)
            free_bytes = stat.free

            # 安全マージンとして10MBを追加
            safety_margin = 10 * 1024 * 1024  # 10MB

            if free_bytes < (required_bytes + safety_margin):
                self.logger.warning(
                    f"ディスク容量不足: 必要={required_bytes:,}bytes, "
                    f"利用可能={free_bytes:,}bytes"
                )
                return False

            return True
        except Exception as e:
            self.logger.warning(f"ディスク容量チェックエラー: {e}")
            # エラーの場合は容量チェックをスキップ（コピーを継続）
            return True
