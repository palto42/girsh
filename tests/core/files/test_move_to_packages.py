import os
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import patch

from loguru import logger

# Import the module using the new submodule path
from girsh.core import files


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
# Tests for move_to_packages
# -------------------------------


class MoveToPackagesTest(unittest.TestCase):
    def setUp(self) -> None:
        logger.remove()  # Remove all loguru handlers to silence logging output
        self.temp_dir: tempfile.TemporaryDirectory = tempfile.TemporaryDirectory()
        self.temp_path: Path = Path(self.temp_dir.name)
        self.bin_base_folder = self.temp_path / "bin"
        self.bin_base_folder.mkdir()
        self.package_base_folder = self.temp_path / "packages"
        self.package_base_folder.mkdir()
        self.package_source = self.temp_path / "package_source"
        self.package_source.mkdir()
        self.binary_rel = "bin/executable"
        self.binary_file = self.package_source / self.binary_rel
        self.binary_file.parent.mkdir(parents=True, exist_ok=True)
        self.binary_file.write_text("binary")

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_move_to_packages_success(self) -> None:
        result = files.move_to_packages(
            package_source=self.package_source,
            package_base_folder=self.package_base_folder,
            bin_base_folder=self.bin_base_folder,
            binary_path=self.binary_file,
            binary_name="symlink",
        )
        package_path = self.package_base_folder / self.package_source.name
        self.assertTrue(package_path.is_dir())
        dest_bin = self.bin_base_folder / "symlink"
        self.assertTrue(dest_bin.is_symlink())
        expected_target = package_path / self.binary_file.relative_to(self.package_source)
        self.assertEqual(os.readlink(dest_bin), str(expected_target))
        self.assertEqual(result, dest_bin)

    def test_move_to_packages_existing_package(self) -> None:
        existing = self.package_base_folder / self.package_source.name
        existing.mkdir(parents=True, exist_ok=True)
        (existing / "old.txt").write_text("old")
        _result = files.move_to_packages(
            package_source=self.package_source,
            package_base_folder=self.package_base_folder,
            bin_base_folder=self.bin_base_folder,
            binary_path=self.binary_file,
            binary_name="symlink",
        )
        package_path = self.package_base_folder / self.package_source.name
        self.assertTrue(package_path.is_dir())
        self.assertFalse((package_path / "old.txt").exists())

    def test_move_to_packages_mkdir_permission_error(self) -> None:
        with (
            patch("pathlib.Path.mkdir", side_effect=PermissionError),
            patch("sys.exit", side_effect=SystemExit) as mock_exit,
            patch.object(logger, "error") as mock_logger_error,
        ):
            with self.assertRaises(SystemExit):
                files.move_to_packages(
                    package_source=self.package_source,
                    package_base_folder=self.package_base_folder,
                    bin_base_folder=self.bin_base_folder,
                    binary_path=self.binary_file,
                    binary_name="symlink",
                )
            mock_logger_error.assert_called_once_with(
                SubstringMatcher(containing="Permission denied when creating packages folder")
            )
            mock_exit.assert_called_once_with(1)

    def test_move_to_packages_rename_permission_error(self) -> None:
        with (
            patch("pathlib.Path.rename", side_effect=PermissionError),
            patch("sys.exit", side_effect=SystemExit) as mock_exit,
            patch.object(logger, "error") as mock_logger_error,
        ):
            with self.assertRaises(SystemExit):
                files.move_to_packages(
                    package_source=self.package_source,
                    package_base_folder=self.package_base_folder,
                    bin_base_folder=self.bin_base_folder,
                    binary_path=self.binary_file,
                    binary_name="symlink",
                )
            mock_logger_error.assert_called_once_with(
                SubstringMatcher(containing="Permission denied to move package to")
            )
            mock_exit.assert_called_once_with(1)

    def test_move_to_packages_rename_oserror(self) -> None:
        self.package_base_folder.mkdir(exist_ok=True)
        with (
            patch("pathlib.Path.rename", side_effect=OSError),
            patch("sys.exit", side_effect=SystemExit) as mock_exit,
            patch.object(logger, "error") as mock_logger_error,
        ):
            with self.assertRaises(SystemExit):
                files.move_to_packages(
                    package_source=self.package_source,
                    package_base_folder=self.package_base_folder,
                    bin_base_folder=self.bin_base_folder,
                    binary_path=self.binary_file,
                    binary_name="symlink",
                )
            mock_logger_error.assert_called_once_with(
                f"Move package to '{self.package_base_folder / self.package_source.name}' failed with error: None"
            )
            mock_exit.assert_called_once_with(1)

    def test_move_to_packages_unlink_permission_error(self) -> None:
        with (
            patch("pathlib.Path.unlink", side_effect=PermissionError),
            patch("sys.exit", side_effect=SystemExit) as mock_exit,
            patch.object(logger, "error") as mock_logger_error,
        ):
            with self.assertRaises(SystemExit):
                files.move_to_packages(
                    package_source=self.package_source,
                    package_base_folder=self.package_base_folder,
                    bin_base_folder=self.bin_base_folder,
                    binary_path=self.binary_file,
                    binary_name="symlink",
                )
            mock_logger_error.assert_called_once_with(
                SubstringMatcher(containing="Permission denied to create symlink")
            )
            mock_exit.assert_called_once_with(1)

    def test_move_to_packages_symlink_permission_error(self) -> None:
        with (
            patch("pathlib.Path.symlink_to", side_effect=PermissionError),
            patch("sys.exit", side_effect=SystemExit) as mock_exit,
            patch.object(logger, "error") as mock_logger_error,
        ):
            with self.assertRaises(SystemExit):
                files.move_to_packages(
                    package_source=self.package_source,
                    package_base_folder=self.package_base_folder,
                    bin_base_folder=self.bin_base_folder,
                    binary_path=self.binary_file,
                    binary_name="symlink",
                )
            mock_logger_error.assert_called_once_with(
                SubstringMatcher(containing="Permission denied to create symlink")
            )
            mock_exit.assert_called_once_with(1)

    def test_move_to_packages_symlink_os_error(self) -> None:
        with (
            patch("pathlib.Path.symlink_to", side_effect=OSError),
            patch("sys.exit", side_effect=SystemExit) as mock_exit,
            patch.object(logger, "error") as mock_logger_error,
        ):
            with self.assertRaises(SystemExit):
                files.move_to_packages(
                    package_source=self.package_source,
                    package_base_folder=self.package_base_folder,
                    bin_base_folder=self.bin_base_folder,
                    binary_path=self.binary_file,
                    binary_name="symlink",
                )
            mock_logger_error.assert_called_once_with(SubstringMatcher(containing="Symlink moved package to"))
            mock_exit.assert_called_once_with(1)


if __name__ == "__main__":
    unittest.main()
