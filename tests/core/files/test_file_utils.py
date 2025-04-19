import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

# Import the module using the new submodule path
from girsh.core import files

# -------------------------------
# Tests for get_common_prefix
# -------------------------------


class CommonPrefixTest(unittest.TestCase):
    def test_get_common_prefix_common(self) -> None:
        names = ["folder/file1.txt", "folder/file2.txt"]
        prefix = files.get_common_prefix(names)
        self.assertEqual(prefix, "folder")

    def test_get_common_prefix_no_common(self) -> None:
        names = ["folder1/file.txt", "folder2/file.txt"]
        prefix = files.get_common_prefix(names)
        self.assertIsNone(prefix)

    def test_get_common_prefix_empty(self) -> None:
        prefix = files.get_common_prefix([])
        self.assertIsNone(prefix)


# -------------------------------
# Tests for is_safe_path
# -------------------------------


class IsSafePathTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_is_safe_path_true(self) -> None:
        subdir = self.temp_path / "subdir"
        subdir.mkdir()
        target = subdir / "file.txt"
        target.write_text("content")
        self.assertTrue(files.is_safe_path(self.temp_path, target))

    def test_is_safe_path_false(self) -> None:
        try:
            other_dir = tempfile.TemporaryDirectory()
            other_path = Path(other_dir.name)
            target = other_path / "file.txt"
            target.write_text("content")
            self.assertFalse(files.is_safe_path(self.temp_path, target))
        finally:
            other_dir.cleanup()

    def test_is_safe_path_oserror(self) -> None:
        target = self.temp_path / "file.txt"
        target.write_text("content")
        with patch("pathlib.Path.resolve", side_effect=OSError):
            self.assertFalse(files.is_safe_path(self.temp_path, target))


if __name__ == "__main__":
    unittest.main()
