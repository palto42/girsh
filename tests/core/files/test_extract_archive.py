import bz2
import io
import shutil
import tarfile
import tempfile
import unittest
import zipfile
from pathlib import Path
from typing import Any
from unittest.mock import patch

from loguru import logger

# Import the module using the new submodule path
from girsh.core import files


# A base test class to set up temporary directories and dummy config.
class BaseTest(unittest.TestCase):
    def setUp(self) -> None:
        logger.remove()  # Remove all loguru handlers to silence logging output
        self.temp_dir: tempfile.TemporaryDirectory = tempfile.TemporaryDirectory()
        self.temp_path: Path = Path(self.temp_dir.name)
        self.extract_to = self.temp_path / "extract"
        self.extract_to.mkdir()
        self.package_name = "test_package"

    def tearDown(self) -> None:
        self.temp_dir.cleanup()


def fake_is_safe_path(base: Path, target: Path) -> bool:
    return "unsafe.txt" not in str(target)


# -------------------------------
# Tests for extract_archive
# -------------------------------


class ExtractArchiveTest(BaseTest):
    def test_extract_zip_no_common(self) -> None:
        zip_file = self.temp_path / "test.zip"
        with zipfile.ZipFile(zip_file, "w") as zf:
            zf.writestr("dummy", "dummy content")
        with patch("girsh.core.files.get_common_prefix", return_value=None):
            result = files.extract_archive(zip_file, self.extract_to, self.package_name)
        self.assertIsNone(result)

    def test_extract_gz_no_common(self) -> None:
        gz_file = self.temp_path / "test.tar.gz"
        with tarfile.open(gz_file, "w:gz") as tar:
            info = tarfile.TarInfo(name="safe.txt")
            content = b"safe content"
            info.size = len(content)
            tar.addfile(info, fileobj=io.BytesIO(content))
        with patch("girsh.core.files.get_common_prefix", return_value=None):
            result = files.extract_archive(gz_file, self.extract_to, self.package_name)
        self.assertIsNone(result)

    def test_extract_zip(self) -> None:
        zip_file = self.temp_path / "test.zip"
        with zipfile.ZipFile(zip_file, "w") as zf:
            zf.writestr("dummy", "dummy content")
        with (
            patch("girsh.core.files.get_common_prefix", return_value="common"),
            patch("girsh.core.files.extract_zip_archive") as mock_extract_zip_archive,
        ):
            result = files.extract_archive(zip_file, self.extract_to, self.package_name)
            mock_extract_zip_archive.assert_called_once()
        self.assertEqual(result, "common")

    def test_extract_tar_bz2(self) -> None:
        bz2_file = self.temp_path / "test.tar.bz2"
        with tarfile.open(bz2_file, "w:bz2") as tar:
            info = tarfile.TarInfo(name="safe.txt")
            content = b"safe content"
            info.size = len(content)
            tar.addfile(info, fileobj=io.BytesIO(content))
        with (
            patch("girsh.core.files.get_common_prefix", return_value="common"),
            patch("girsh.core.files.extract_tar_archive") as mock_extract_tar_archive,
        ):
            result = files.extract_archive(bz2_file, self.extract_to, self.package_name)
            mock_extract_tar_archive.assert_called_once()
        self.assertEqual(result, "common")

    def test_extract_tar_bz2_no_common(self) -> None:
        bz2_file = self.temp_path / "test.tar.bz2"
        with tarfile.open(bz2_file, "w:bz2") as tar:
            info = tarfile.TarInfo(name="safe.txt")
            content = b"safe content"
            info.size = len(content)
            tar.addfile(info, fileobj=io.BytesIO(content))
        with patch("girsh.core.files.get_common_prefix", return_value=None):
            result = files.extract_archive(bz2_file, self.extract_to, self.package_name)
        self.assertIsNone(result)

    def test_extract_bz2(self) -> None:
        bz2_file = self.temp_path / "test.bz2"
        with tarfile.open(bz2_file, "w:bz2") as tar:
            info = tarfile.TarInfo(name="safe.txt")
            content = b"safe content"
            info.size = len(content)
            tar.addfile(info, fileobj=io.BytesIO(content))
        with (
            patch("girsh.core.files.extract_bz2_archive") as mock_extract_bz2_archive,
        ):
            result = files.extract_archive(bz2_file, self.extract_to, self.package_name)
            mock_extract_bz2_archive.assert_called_once()
        self.assertIsNone(result)

    def test_extract_is_binary(self) -> None:
        bin_file = self.temp_path / "test_bin"
        with bin_file.open("wb") as f:
            f.write(b"binary content")
        result = files.extract_archive(bin_file, self.extract_to, self.package_name)
        self.assertIsNone(result)
        self.assertTrue((self.extract_to / "test_bin").exists())


# -------------------------------
# Tests for extract_zip_archive
# -------------------------------


class ExtractZipArchiveTest(BaseTest):
    def test_extract_zip_archive_safe(self) -> None:
        zip_path = self.temp_path / "test.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("safe.txt", "safe content")
            zf.writestr("unsafe.txt", "unsafe content")
        with (
            zipfile.ZipFile(zip_path, "r") as archive,
            patch("girsh.core.files.is_safe_path", side_effect=fake_is_safe_path),
        ):
            extracted = []
            original_extract = archive.extract

            def fake_extract(name: str, base_dir: Path) -> Any:
                extracted.append(name)
                return original_extract(name, base_dir)

            with patch.object(archive, "extract", side_effect=fake_extract):
                files.extract_zip_archive(archive, self.extract_to)
            self.assertIn("safe.txt", extracted)
            self.assertNotIn("unsafe.txt", extracted)


# -------------------------------
# Tests for extract_tar_archive
# -------------------------------


class ExtractTarArchiveTest(BaseTest):
    def test_extract_tar_archive_safe(self) -> None:
        temp_dir = Path(tempfile.mkdtemp())
        try:
            tar_path = temp_dir / "test.tar.gz"
            with tarfile.open(tar_path, "w:gz") as tar:
                info = tarfile.TarInfo(name="safe.txt")
                content = b"safe content"
                info.size = len(content)
                tar.addfile(info, fileobj=io.BytesIO(content))
                info2 = tarfile.TarInfo(name="unsafe.txt")
                content2 = b"unsafe content"
                info2.size = len(content2)
                tar.addfile(info2, fileobj=io.BytesIO(content2))
            with (
                tarfile.open(tar_path, "r:gz") as archive,
                patch("girsh.core.files.is_safe_path", side_effect=fake_is_safe_path),
            ):
                extract_dir = temp_dir / "extract"
                extract_dir.mkdir()
                extracted = []
                original_extract = archive.extract

                def fake_extract(member: tarfile.TarInfo, base_dir: Path) -> Any:
                    extracted.append(member.name)
                    return original_extract(member, base_dir)

                with patch.object(archive, "extract", side_effect=fake_extract):
                    files.extract_tar_archive(archive, extract_dir)
                self.assertIn("safe.txt", extracted)
                self.assertNotIn("unsafe.txt", extracted)
        finally:
            shutil.rmtree(temp_dir)


# -------------------------------
# Tests for extract_bz2_archive
# -------------------------------


class ExtractBZ2ArchiveTest(BaseTest):
    def test_extract_bz2_archive_success(self) -> None:
        bz2_file = self.temp_path / "test.bz2"
        content = b"test content"
        with bz2.BZ2File(bz2_file, "wb") as f:
            f.write(content)

        files.extract_bz2_archive(bz2_file, self.extract_to, self.package_name)

        extracted_file = self.extract_to / self.package_name / "test"
        self.assertTrue(extracted_file.exists())
        self.assertEqual(extracted_file.read_bytes(), content)

    def test_extract_bz2_archive_no_permission(self) -> None:
        bz2_file = self.temp_path / "test.bz2"
        content = b"test content"
        with bz2_file.open("wb") as f:
            f.write(content)

        with patch("pathlib.Path.mkdir", side_effect=PermissionError), self.assertRaises(PermissionError):
            files.extract_bz2_archive(bz2_file, self.extract_to, self.package_name)

    def test_extract_bz2_archive_os_error(self) -> None:
        bz2_file = self.temp_path / "test.bz2"
        content = b"test content"
        with bz2_file.open("wb") as f:
            f.write(content)

        with patch("shutil.copyfileobj", side_effect=OSError), self.assertRaises(OSError):
            files.extract_bz2_archive(bz2_file, self.extract_to, self.package_name)


if __name__ == "__main__":
    unittest.main()
