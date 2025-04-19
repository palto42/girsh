import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

from loguru import logger

from girsh.core import repos


class SubstringMatcher:
    def __init__(self, containing: str) -> None:
        self.containing: str = containing.lower()

    def __eq__(self, other: Any) -> Any:
        return other.lower().find(self.containing) > -1

    def __unicode__(self) -> str:
        return f'a string containing "{self.containing}"'

    def __str__(self) -> str:
        return self.__unicode__().encode("utf-8").decode("utf-8")

    __repr__ = __unicode__


# -------------------------------
# Dummy classes used for testing
# -------------------------------
@dataclass
class DummyRepository:
    version: str | None = None
    comment: str = ""
    package_pattern: str | None = None
    download_url: str | None = None
    filter_pattern: str | None = None
    multi_file: bool = False
    binary_name: str | None = None
    pre_update_commands: list[str] | None = None
    post_update_commands: list[str] | None = None


def dummy_show_installed(installed: dict[Any, Any], repositories: dict) -> int:
    return 0


def dummy_remove_binary(repo: str, info: dict, dry_run: bool) -> None:
    return


def dummy_remove_package(repo: str, info: dict, dry_run: bool) -> None:
    return


def dummy_save_installed(installed_file: Path, data: dict) -> int:
    return 42


# -------------------------------
# Tests for uninstall
# -------------------------------
class TestUninstall(unittest.TestCase):
    def setUp(self) -> None:
        # Disable loguru logger output
        from loguru import logger

        logger.remove()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path: Path = Path(self.temp_dir.name)
        self.bin_dir = self.temp_path / "bin"
        self.dummy_repositories = {"dummy1": DummyRepository(version="v1.0")}
        self.dummy_installed: dict[Any, Any] = {}

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    @patch("girsh.core.repos.logger")
    def test_uninstall_not_installed(self, mock_logger: MagicMock) -> None:
        result = repos.uninstall(
            repositories=self.dummy_repositories,  # type: ignore[arg-type]
            installed={},
            dry_run=False,
        )
        self.assertEqual(result, {})
        mock_logger.log.assert_called_once_with("SUCCESS", "No binaries installed.")

    def test_uninstall_removes_unlisted_repo(self) -> None:
        binary_name = "binary1"
        pre_commands = ["echo UNINSTALL", rf"%stop_processes% {binary_name}"]
        installed = {
            "unknown/repo": {
                "tag": "v1.0",
                "binary": binary_name,
                "path": str(self.temp_path),
                "pre_update_commands": pre_commands,
            }
        }
        binary_path = self.temp_path / binary_name
        binary_path.touch()
        with (
            patch.object(logger, "success") as mock_logger_success,
            patch.object(logger, "info") as mock_logger_info,
            patch("girsh.core.utils.run_commands", return_value=True) as mock_run_commands,
        ):
            summary: dict = repos.uninstall(
                repositories=self.dummy_repositories,  # type: ignore[arg-type]
                installed=installed,
                dry_run=False,
            )
        self.assertEqual(summary, {repos.RepoResult.uninstalled: 1})
        self.assertNotIn("unknown/repo", installed)
        mock_run_commands.assert_called_once_with(pre_commands, "repo: pre-uninstall")
        info_logs = [
            "Uninstall binaries no longer in config.",
            "Running commands for repo: pre-uninstall",
        ]
        for n, call in enumerate(mock_logger_info.call_args_list):
            self.assertEqual(call.args[0], info_logs[n])

        mock_logger_success.assert_called_once_with(
            f"Uninstalled {binary_path.name} from {binary_path} originated from unknown/repo"
        )

    def test_uninstall_all(self) -> None:
        binary_name = "binary1"
        pre_commands = ["echo UNINSTALL", rf"%stop_processes% {binary_name}"]
        installed = {
            "unknown/repo": {
                "tag": "v1.0",
                "binary": binary_name,
                "path": str(self.temp_path),
                "pre_update_commands": pre_commands,
            }
        }
        binary_path = self.temp_path / binary_name
        binary_path.touch()
        with (
            patch.object(logger, "success") as mock_logger_success,
            patch.object(logger, "info") as mock_logger_info,
            patch("girsh.core.utils.run_commands", return_value=True) as mock_run_commands,
            patch("girsh.core.utils.confirm_default_no", return_value=True),
        ):
            summary: dict = repos.uninstall(
                repositories=[],  # Uninstall-all is achieved by passing empty repositories dict
                installed=installed,
                dry_run=False,
            )
        self.assertEqual(summary, {repos.RepoResult.uninstalled: 1})
        self.assertNotIn("unknown/repo", installed)
        mock_run_commands.assert_called_once_with(pre_commands, "repo: pre-uninstall")
        info_logs = [
            "Uninstall all binaries.",
            "Running commands for repo: pre-uninstall",
        ]
        for n, call in enumerate(mock_logger_info.call_args_list):
            self.assertEqual(call.args[0], info_logs[n])

        mock_logger_success.assert_called_once_with(
            f"Uninstalled {binary_path.name} from {binary_path} originated from unknown/repo"
        )

    def test_uninstall_all_cancelled(self) -> None:
        binary_name = "binary1"
        pre_commands = ["echo UNINSTALL", rf"%stop_processes% {binary_name}"]
        installed = {
            "unknown/repo": {
                "tag": "v1.0",
                "binary": binary_name,
                "path": str(self.temp_path),
                "pre_update_commands": pre_commands,
            }
        }
        binary_path = self.temp_path / binary_name
        binary_path.touch()
        with (
            patch.object(logger, "success") as mock_logger_success,
            patch.object(logger, "info") as mock_logger_info,
            patch("girsh.core.utils.run_commands", return_value=True) as mock_run_commands,
            patch("girsh.core.utils.confirm_default_no", return_value=False),
        ):
            summary: dict = repos.uninstall(
                repositories=[],  # Uninstall-all is achieved by passing empty repositories dict
                installed=installed,
                dry_run=False,
            )
        self.assertEqual(summary, {repos.RepoResult.cancelled: 1})
        self.assertIn("unknown/repo", installed)
        mock_run_commands.assert_not_called()
        info_logs = [
            "Uninstall cancelled.",
            "Running commands for repo: pre-uninstall",
        ]
        for n, call in enumerate(mock_logger_info.call_args_list):
            self.assertEqual(call.args[0], info_logs[n])
        mock_logger_success.assert_not_called()

    def test_uninstall_not_exists(self) -> None:
        installed = {"unknown/repo": {"tag": "v1.0", "binary": "binary1", "path": str(self.temp_path)}}
        # binary_path = self.temp_path / installed["unknown/repo"]["binary"]
        # # binary_path.touch()
        with patch.object(logger, "info") as mock_logger:
            summary: dict = repos.uninstall(
                repositories=self.dummy_repositories,  # type: ignore[arg-type]
                installed=installed,
                dry_run=False,
            )
        self.assertEqual(summary, {repos.RepoResult.uninstalled: 1})
        self.assertNotIn("unknown/repo", installed)
        mock_logger.assert_called_with("Uninstall binaries no longer in config.")

    def test_uninstall_keep_listed_repo(self) -> None:
        installed = {"dummy1": {"tag": "v1.0", "binary": "binary1", "path": str(self.temp_path)}}
        with patch.object(logger, "info") as mock_logger:
            summary: dict = repos.uninstall(
                repositories=self.dummy_repositories,  # type: ignore[arg-type]
                installed=installed,
                dry_run=False,
            )
        self.assertEqual(summary, {})
        self.assertNotIn("unknown/repo", installed)
        mock_logger.assert_called_with("Uninstall binaries no longer in config.")

    def test_uninstall_dry_run(self) -> None:
        installed = {"unknown/repo": {"tag": "v1.0", "binary": "binary1", "path": str(self.temp_path)}}
        binary_path = self.temp_path / installed["unknown/repo"]["binary"]
        binary_path.touch()
        with (
            patch.object(logger, "success") as mock_logger,
        ):
            result = repos.uninstall(
                repositories=self.dummy_repositories,  # type: ignore[arg-type]
                installed=installed,
                dry_run=True,
            )
        self.assertEqual(result, {repos.RepoResult.dry_run_uninstall: 1})
        mock_logger.assert_called_with(f"Dry-run: unknown/repo: Would uninstall binary1 from {binary_path}.")

    def test_uninstall_permission_error(self) -> None:
        installed = {"unknown/repo": {"tag": "v1.0", "binary": "binary1", "path": str(self.temp_path)}}
        binary_path = self.temp_path / installed["unknown/repo"]["binary"]
        binary_path.touch()
        with (
            patch("pathlib.Path.unlink", side_effect=PermissionError),
            patch("girsh.core.utils.run_commands", return_value=True),
            patch.object(logger, "error") as mock_logger,
        ):
            result = repos.uninstall(
                repositories=self.dummy_repositories,  # type: ignore[arg-type]
                installed=installed,
                dry_run=False,
            )
        self.assertEqual(result, {repos.RepoResult.uninstall_failed: 1})
        mock_logger.assert_called_with(f"Permission denied when trying to uninstall {binary_path}")


if __name__ == "__main__":
    unittest.main()
