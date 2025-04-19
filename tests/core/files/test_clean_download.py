import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from loguru import logger

# Import the module using the new submodule path
from girsh.core import files

# -------------------------------
# Tests for clean_downloads_folder
# -------------------------------


class CleanDownloadsFolderTest(unittest.TestCase):
    def setUp(self) -> None:
        logger.remove()  # Remove all loguru handlers to silence logging output
        self.temp_dir: tempfile.TemporaryDirectory = tempfile.TemporaryDirectory()
        self.download_dir: Path = Path(self.temp_dir.name)
        self.dummy_file = self.download_dir / "dummy_file.txt"
        self.dummy_file.touch()  # Create a dummy file in the download folder

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_clean_downloads_folder_success(self) -> None:
        self.assertTrue(self.download_dir.exists())
        ret = files.clean_downloads_folder(download_dir=self.download_dir)
        self.assertEqual(ret, 0)
        self.assertFalse(self.download_dir.exists())
        self.assertFalse(self.dummy_file.exists())

    def test_clean_downloads_folder_no_folder(self) -> None:
        shutil.rmtree(self.download_dir)
        with patch.object(logger, "info") as mock_logger_info:
            ret = files.clean_downloads_folder(download_dir=self.download_dir)
            mock_logger_info.assert_called_once_with(f"Download folder {self.download_dir} doesn't exist.")
        self.assertEqual(ret, 0)

    def test_clean_downloads_folder_permission_error(self) -> None:
        with patch("shutil.rmtree", side_effect=PermissionError), patch.object(logger, "error") as mock_logger_error:
            ret = files.clean_downloads_folder(download_dir=self.download_dir)
            mock_logger_error.assert_called_once_with(
                f"No permission to delete the download folder {self.download_dir}"
            )
        self.assertEqual(ret, 1)


if __name__ == "__main__":
    unittest.main()
