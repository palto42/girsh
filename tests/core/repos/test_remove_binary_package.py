import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import patch

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
# Tests for remove_binary
# -------------------------------
class TestRemoveBinary(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path: Path = Path(self.temp_dir.name)
        self.bin_dir = self.temp_path / "bin"
        self.bin_dir.mkdir()
        self.installed = {
            "owner/repo1": {"tag": "v1.0", "binary": "binary1", "path": str(self.bin_dir)},
            "owner/repo2": {"tag": "v1.0", "binary": "binary2", "path": str(self.bin_dir)},
        }

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_remove_binary_success(self) -> None:
        binary1 = self.bin_dir / "binary1"
        binary1.touch()
        with (
            patch.object(logger, "info") as mock_logger,
        ):
            repos.remove_binary("owner/repo1", self.installed["owner/repo1"], dry_run=False)
            self.assertFalse(binary1.exists())
            mock_logger.assert_called_once_with(SubstringMatcher(containing="Uninstalled binary1"))

    def test_remove_binary_permission_error(self) -> None:
        binary1 = self.bin_dir / "binary1"
        binary1.touch()
        with (
            patch("pathlib.Path.unlink", side_effect=PermissionError),
            patch.object(logger, "error") as mock_logger,
        ):
            repos.remove_binary("owner/repo1", self.installed["owner/repo1"], dry_run=False)
            self.assertTrue(binary1.exists())
            mock_logger.assert_called_once_with(SubstringMatcher(containing="Permission denied"))

    def test_remove_binary_dry_run(self) -> None:
        binary1 = self.bin_dir / "binary1"
        binary1.touch()
        with (
            patch.object(logger, "info") as mock_logger,
        ):
            repos.remove_binary("owner/repo1", self.installed["owner/repo1"], dry_run=True)
            self.assertTrue(binary1.exists())
            mock_logger.assert_called_once_with(SubstringMatcher(containing="Dry-run:"))

    def test_remove_binary_not_exists(self) -> None:
        with (
            patch.object(logger, "info") as mock_logger,
        ):
            repos.remove_binary("owner/repo2", self.installed["owner/repo2"], dry_run=False)
        mock_logger.assert_not_called()


# -------------------------------
# Tests for remove_package
# -------------------------------
class TestRemovePackage(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path: Path = Path(self.temp_dir.name)
        self.package_path = self.temp_path / "bin"
        self.package_path.mkdir()
        self.installed = {
            "owner/repo1": {"tag": "v1.0", "package_path": str(self.package_path / "package1")},
            "owner/repo2": {"tag": "v1.0", "package_path": str(self.package_path / "package2")},
        }

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_remove_package_success(self) -> None:
        package1 = self.package_path / "package1"
        package1.mkdir(exist_ok=True)
        with (
            patch.object(logger, "info") as mock_logger,
        ):
            repos.remove_package("owner/repo1", self.installed["owner/repo1"], dry_run=False)
            self.assertFalse(package1.exists())
            mock_logger.assert_called_once_with(SubstringMatcher(containing="Deleted package folder"))

    def test_remove_package_permission_error(self) -> None:
        package1 = self.package_path / "package1"
        package1.mkdir(exist_ok=True)
        with (
            patch("shutil.rmtree", side_effect=PermissionError),
            patch.object(logger, "error") as mock_logger,
        ):
            repos.remove_package("owner/repo1", self.installed["owner/repo1"], dry_run=False)
            self.assertTrue(package1.exists())
            mock_logger.assert_called_once_with(SubstringMatcher(containing="Permission denied"))

    def test_remove_package_dry_run(self) -> None:
        package1 = self.package_path / "package1"
        package1.mkdir(exist_ok=True)
        with (
            patch.object(logger, "info") as mock_logger,
        ):
            repos.remove_package("owner/repo1", self.installed["owner/repo1"], dry_run=True)
            self.assertTrue(package1.exists())
            mock_logger.assert_called_once_with(SubstringMatcher(containing="Dry-run:"))

    def test_remove_package_not_exists(self) -> None:
        with (
            patch.object(logger, "info") as mock_logger,
        ):
            repos.remove_package("owner/repo2", self.installed["owner/repo2"], dry_run=False)
        mock_logger.assert_not_called()

    def test_remove_package_path_none(self) -> None:
        with (
            patch.object(logger, "info") as mock_logger,
        ):
            repos.remove_package("owner/repo2", {}, dry_run=False)
        mock_logger.assert_not_called()


if __name__ == "__main__":
    unittest.main()
