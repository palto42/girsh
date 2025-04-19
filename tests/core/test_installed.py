import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import yaml
from loguru import logger

from girsh.core import installed


# -------------------------------
# Dummy classes used for testing
# -------------------------------
@dataclass
class DummyRepo:
    comment: str


class TestInstalledModule(unittest.TestCase):
    def setUp(self) -> None:
        logger.remove()  # Remove any existing logger handlers to avoid duplicate logs.
        # Create a temporary directory and file to use as installed file.
        self.temp_dir: tempfile.TemporaryDirectory = tempfile.TemporaryDirectory()
        self.temp_path: Path = Path(self.temp_dir.name)
        self.installed_file: Path = self.temp_path / "installed.yaml"
        self.output_dir = self.temp_path / "output"
        self.download_dir = self.temp_path / "downloads"
        self.bin_base_folder = self.temp_path / "bin"
        self.package_base_folder = self.temp_path / "packages"

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    # --- Tests for load_installed ---

    def test_load_installed_normal(self) -> None:
        # Write valid YAML dict data to the installed file.
        expected_data: dict[str, dict[str, str]] = {"repo1": {"tag": "v1.0", "binary": "bin1"}}
        with self.installed_file.open("w") as f:
            yaml.safe_dump(expected_data, f)
        ret_data = installed.load_installed(installed_file=self.installed_file)
        self.assertEqual(ret_data, expected_data)

    def test_load_installed_non_dict(self) -> None:
        # Write valid YAML that is not a dict (e.g. a list).
        with self.installed_file.open("w") as f:
            yaml.safe_dump([1, 2, 3], f)
        ret_data = installed.load_installed(installed_file=self.installed_file)
        self.assertEqual(ret_data, {})

    def test_load_installed_file_not_exists(self) -> None:
        # Use a path that does not exist.
        non_existent: Path = self.temp_path / "nonexistent.yaml"
        if non_existent.exists():
            non_existent.unlink()
        ret_data = installed.load_installed(installed_file=non_existent)
        self.assertEqual(ret_data, {})

    @patch("girsh.core.installed.Path.mkdir")
    @patch("sys.exit", side_effect=SystemExit)
    def test_load_installed_permission_error_on_mkdir(self, mock_exit: MagicMock, mock_mkdir: MagicMock) -> None:
        # Simulate a PermissionError when creating the installed folder.
        mock_mkdir.side_effect = PermissionError("No permission")
        with patch.object(logger, "error") as mock_logger_error:
            with self.assertRaises(SystemExit):
                installed.load_installed(installed_file=self.installed_file)
            mock_logger_error.assert_called_once_with(
                f"Permission denied when creating installed folder '{self.installed_file.parent}'."
            )
        mock_exit.assert_called_once_with(1)

    def test_load_installed_permission_error_on_open(self) -> None:
        # Simulate PermissionError when opening the file for reading.
        self.installed_file.touch()  # Ensure the file exists.
        with (
            patch("girsh.core.installed.Path.exists", return_value=True),
            patch("pathlib.Path.open", side_effect=PermissionError("No permission")),
            patch.object(logger, "error") as mock_logger,
        ):
            ret_data = installed.load_installed(installed_file=self.installed_file)
            self.assertEqual(ret_data, {})
            mock_logger.assert_called_with(
                f"Warning: Permission denied when reading installed file '{self.installed_file}'. Proceeding with empty installed."
            )

    def test_load_installed_file_not_found_during_open(self) -> None:
        # Simulate FileNotFoundError when opening the file, even though exists() returns True.
        self.installed_file.touch()  # Ensure the file exists.
        with (
            patch("girsh.core.installed.Path.exists", return_value=False),
            # patch("girsh.core.installed.Path.open", side_effect=FileNotFoundError("Not found")),
            patch.object(logger, "info") as mock_logger_info,
        ):
            ret_data = installed.load_installed(installed_file=self.installed_file)
            self.assertEqual(ret_data, {})
            mock_logger_info.assert_called_with(
                f"Installed packages file '{self.installed_file}' not found. Proceeding with empty installed."
            )

    # --- Tests for save_installed ---

    def test_save_installed_success(self) -> None:
        data: dict[str, dict[str, str]] = {"repo2": {"tag": "v2.0", "binary": "bin2"}}
        ret: int = installed.save_installed(self.installed_file, data)
        self.assertEqual(ret, 0)
        # Verify that the file was written.
        with self.installed_file.open("r") as f:
            loaded: Any = yaml.safe_load(f)
        self.assertEqual(loaded, data)

    def test_save_installed_permission_error(self) -> None:
        with (
            patch("girsh.core.installed.Path.open", side_effect=PermissionError("No permission")),
            patch.object(logger, "error") as mock_logger_error,
        ):
            ret: int = installed.save_installed(self.installed_file, {"key": "value"})
            self.assertEqual(ret, 1)
            mock_logger_error.assert_called_once_with(
                f"Permission denied when writing to installed file '{self.installed_file}'."
            )

    def test_save_installed_file_not_found(self) -> None:
        with (
            patch("girsh.core.installed.Path.open", side_effect=FileNotFoundError("Not found")),
            patch.object(logger, "error") as mock_logger_error,
        ):
            ret: int = installed.save_installed(self.installed_file, {"key": "value"})
            self.assertEqual(ret, 1)
            mock_logger_error.assert_called_once_with(
                f"installed file '{self.installed_file}' not found and cannot be created."
            )

    # --- Tests for get_comment ---

    def test_get_comment_found(self) -> None:
        # Set up CONFIG to include a repository.
        repositories = {"test/repo": DummyRepo("A test repo")}
        comment: str = installed.get_comment("test/repo", repositories=repositories)  # type: ignore[arg-type]
        self.assertEqual(comment, "A test repo")

    def test_get_comment_not_found(self) -> None:
        with patch.object(logger, "debug") as mock_logger_debug:
            comment: str = installed.get_comment("nonexistent/repo", repositories={})
            self.assertEqual(comment, "Not found in config.")
            mock_logger_debug.assert_called_once_with(
                "The repository nonexistent/repo is not present in current config."
            )

    # --- Tests for show_installed ---

    def test_show_installed_empty(self) -> None:
        with patch.object(logger, "success") as mock_logger:
            ret: int = installed.show_installed({}, {})
            self.assertEqual(ret, 0)
            mock_logger.assert_called_with("Nothing installed via `girsh`")

    def test_show_installed_non_empty(self) -> None:
        # Set up CONFIG so that get_comment returns a meaningful comment.
        repositories = {"repo1": DummyRepo("Test comment")}
        data: dict[str, dict[str, str]] = {"repo1": {"binary": "binA", "tag": "v1.1"}}
        with patch.object(logger, "success") as mock_logger:
            ret: int = installed.show_installed(data, repositories)  # type: ignore[arg-type]
            self.assertEqual(ret, 0)
            # Verify that table components were logged.
            calls: list[Any] = [call.args[0] for call in mock_logger.call_args_list]
            self.assertTrue(any("Currently installed binaries:" in msg for msg in calls))
            # Expect at least one separator line that starts and ends with '+'.
            self.assertTrue(any(msg.startswith("+") and msg.endswith("+") for msg in calls))


if __name__ == "__main__":
    unittest.main()
