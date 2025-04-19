import unittest

from loguru import logger

# Import the module using the new submodule path
from girsh.core import files

# -------------------------------
# Tests for get_filename_from_cd
# -------------------------------


class GetFilenameFromCDTest(unittest.TestCase):
    def setUp(self) -> None:
        logger.remove()  # Remove all loguru handlers to silence logging output

    def test_get_filename_from_cd_none(self) -> None:
        self.assertIsNone(files.get_filename_from_cd(None))

    def test_get_filename_from_cd_empty(self) -> None:
        self.assertIsNone(files.get_filename_from_cd(""))

    def test_get_filename_from_cd_valid(self) -> None:
        header = 'attachment; filename="archive.tar.gz"'
        filename = files.get_filename_from_cd(header)
        self.assertEqual(filename, '"archive.tar.gz"')

    def test_get_filename_from_cd_invalid(self) -> None:
        header = "attachment; something_else"
        filename = files.get_filename_from_cd(header)
        self.assertIsNone(filename)


if __name__ == "__main__":
    unittest.main()
