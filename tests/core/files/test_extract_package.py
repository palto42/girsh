import io
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from loguru import logger

# Import the module using the new submodule path
from girsh.core import files

# -------------------------------
# Tests for extract_package
# -------------------------------


class ExtractPackageTest(unittest.TestCase):
    def setUp(self) -> None:
        logger.remove()  # Remove all loguru handlers to silence logging output
        self.temp_dir: tempfile.TemporaryDirectory = tempfile.TemporaryDirectory()
        self.temp_path: Path = Path(self.temp_dir.name)
        self.extract_to = self.temp_path / "extract"
        self.extract_to.mkdir()
        self.package_name = "test_package"
        self.package_path = self.extract_to / "package"
        self.package_path.mkdir()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_extract_package_common(self) -> None:
        pkg_dir = self.extract_to / self.package_name
        self.assertFalse(pkg_dir.is_dir())
        with patch("girsh.core.files.extract_archive", return_value=str(self.package_path)):
            files.extract_package(self.package_path, self.extract_to, self.package_name)

        self.assertTrue(pkg_dir.is_dir())

    def test_extract_package_rename_permission_error(self) -> None:
        pkg_dir = self.extract_to / self.package_name
        self.assertFalse(pkg_dir.is_dir())
        with (
            patch("girsh.core.files.extract_archive", return_value=str(self.package_path)),
            patch("pathlib.Path.rename", side_effect=PermissionError("permission_error")),
            patch.object(logger, "error") as mock_logger_error,
        ):
            files.extract_package(self.package_path, self.extract_to, self.package_name)
            mock_logger_error.assert_called_once_with(
                f"Failed to rename {self.package_path} to {pkg_dir}: permission_error"
            )
        self.assertFalse(pkg_dir.is_dir())

    def test_extract_package_os_error(self) -> None:
        pkg_dir = self.extract_to / self.package_name
        self.assertFalse(pkg_dir.is_dir())
        with (
            patch("girsh.core.files.extract_archive", return_value=str(self.package_path)),
            patch("pathlib.Path.rename", side_effect=OSError("os_error")),
            patch.object(logger, "error") as mock_logger_error,
        ):
            files.extract_package(self.package_path, self.extract_to, self.package_name)
            mock_logger_error.assert_called_once_with(f"Failed to rename {self.package_path} to {pkg_dir}: os_error")
        self.assertFalse(pkg_dir.is_dir())

    def test_extract_package_no_common(self) -> None:
        zip_file_path = self.temp_path / "package.zip"
        package_name = "my_package"
        with (
            patch("girsh.core.files.extract_archive", return_value=None),
            patch.object(logger, "debug") as mock_logger,
        ):
            files.extract_package(zip_file_path, self.extract_to, package_name)
        mock_logger.assert_called_with(
            f"Extraction complete. Files are in: {self.temp_path / 'extract' / 'my_package'}"
        )

    def test_extract_package_new_folder_exists(self) -> None:
        zip_file_path = self.temp_path / "package.zip"
        package_name = "my_package"
        pkg_dir = self.extract_to / package_name
        pkg_dir.mkdir()
        with (
            patch("girsh.core.files.extract_archive", return_value="common"),
            patch.object(logger, "debug") as mock_logger,
        ):
            files.extract_package(zip_file_path, self.extract_to, package_name)
        self.assertTrue(pkg_dir.is_dir())
        mock_logger.assert_any_call(f"Target folder {pkg_dir} already exists; skipping rename.")

    def test_extract_package_tar(self) -> None:
        tar_file_path = self.temp_path / "package.tar.gz"
        package_name = "my_package"
        with tarfile.open(tar_file_path, "w:gz") as tar:
            info = tarfile.TarInfo(name="common/file.txt")
            content = b"tar content"
            info.size = len(content)
            tar.addfile(info, fileobj=io.BytesIO(content))

        files.extract_package(tar_file_path, self.extract_to, package_name)
        pkg_dir = self.extract_to / package_name
        self.assertTrue(pkg_dir.is_dir())
        self.assertTrue((pkg_dir / "file.txt").exists())

    def test_extract_package_unsupported(self) -> None:
        txt_file = self.temp_path / "file.txt"
        txt_file.write_text("not an archive")
        files.extract_package(txt_file, self.extract_to, "pkg")
        self.assertFalse((self.extract_to / "pkg").exists())


if __name__ == "__main__":
    unittest.main()
