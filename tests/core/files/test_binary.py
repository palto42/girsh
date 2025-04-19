import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from loguru import logger

# Import the module using the new submodule path
from girsh.core import files

# -------------------------------
# Tests for find_binary
# -------------------------------


class FindBinaryTest(unittest.TestCase):
    def setUp(self) -> None:
        logger.remove()  # Remove all loguru handlers to silence logging output
        self.temp_dir: tempfile.TemporaryDirectory = tempfile.TemporaryDirectory()
        self.temp_path: Path = Path(self.temp_dir.name)
        self.bin_dir = self.temp_path / "bin"
        self.bin_dir.mkdir()
        self.app1 = self.bin_dir / "app1"
        self.app1.write_text("binary1")
        self.app1.chmod(0o755)
        self.app2 = self.bin_dir / "app2"
        self.app2.write_text("binary2")
        self.app2.chmod(0o755)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_find_binary_with_pattern(self) -> None:
        result = files.find_binary(self.bin_dir, "app1")
        self.assertEqual(result, self.app1)

    def test_find_binary_no_pattern_multiple_executables(self) -> None:
        result = files.find_binary(self.bin_dir, None)
        self.assertIn(result, [self.app1, self.app2])

    def test_find_binary_no_executables(self) -> None:
        extract_dir = self.temp_path / "empty_extract"
        extract_dir.mkdir()
        no_exec = extract_dir / "not_exec"
        no_exec.write_text("dummy_text")
        no_exec.chmod(0o644)
        result = files.find_binary(extract_dir, None)
        self.assertIsNone(result)

    def test_find_binary_empty_extract_dir(self) -> None:
        extract_dir = self.temp_path / "empty_extract"
        dummy_dir = extract_dir / "dummy"
        dummy_dir.mkdir(parents=True)
        with patch.object(logger, "debug") as mock_logger_debug:
            result = files.find_binary(extract_dir, "DummyPattern")
            mock_logger_debug.assert_called_with(f"Binary not found in {extract_dir}")
            self.assertIsNone(result)


# -------------------------------
# Tests for copy_to_bin
# -------------------------------


class CopyToBinTest(unittest.TestCase):
    def setUp(self) -> None:
        logger.remove()  # Remove all loguru handlers to silence logging output
        self.temp_dir: tempfile.TemporaryDirectory = tempfile.TemporaryDirectory()
        self.temp_path: Path = Path(self.temp_dir.name)
        self.binary_file = self.temp_path / "binary"
        self.binary_file.write_text("binary")
        self.bin_base_folder = self.temp_path / "bin"
        self.bin_base_folder.mkdir()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_copy_to_bin_success(self) -> None:
        result = files.copy_to_bin(
            binary_path=self.binary_file, bin_base_folder=self.bin_base_folder, binary_name="new_binary"
        )
        dest = self.bin_base_folder / "new_binary"
        self.assertEqual(result, dest)
        self.assertTrue(dest.exists())
        self.assertEqual(dest.read_text(), "binary")
        self.assertEqual(dest.stat().st_mode & 0o111, 0o111)

    def test_copy_to_bin_permission_error(self) -> None:
        # Patch the mkdir method on the entire Path class.
        with patch("pathlib.Path.mkdir", side_effect=PermissionError), self.assertRaises(SystemExit):
            files.copy_to_bin(
                binary_path=self.binary_file,
                bin_base_folder=self.bin_base_folder,
                binary_name="new_binary",
            )

    def test_copy_to_bin_copy_permission_error(self) -> None:
        with patch("shutil.copy2", side_effect=PermissionError), self.assertRaises(SystemExit):
            files.copy_to_bin(
                binary_path=self.binary_file,
                bin_base_folder=self.bin_base_folder,
                binary_name="new_binary",
            )

    def test_copy_to_bin_copy_oserror(self) -> None:
        with patch("shutil.copy2", side_effect=OSError("error")), self.assertRaises(SystemExit):
            files.copy_to_bin(
                binary_path=self.binary_file,
                bin_base_folder=self.bin_base_folder,
                binary_name="new_binary",
            )


if __name__ == "__main__":
    unittest.main()
