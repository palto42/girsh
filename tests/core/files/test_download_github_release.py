import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import Mock, patch

import requests
from loguru import logger
from requests.exceptions import HTTPError, RequestException

# Import the module using the new submodule path
from girsh.core import files

# -------------------------------
# Tests for download_github_release
# -------------------------------


class DownloadGithubReleaseTest(unittest.TestCase):
    def setUp(self) -> None:
        logger.remove()  # Remove all loguru handlers to silence logging output
        self.temp_dir: tempfile.TemporaryDirectory = tempfile.TemporaryDirectory()
        self.output_dir: Path = Path(self.temp_dir.name)
        # self.dummy_file = self.download_dir / "dummy_file.txt"
        # self.dummy_file.touch()  # Create a dummy file in the download folder

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_download_github_release_with_download_url(self) -> None:
        release_info = {"tag_name": "v1.0", "assets": []}
        with patch("girsh.core.files.download_package", return_value=Path(self.output_dir) / "dummy.txt"):
            result = files.download_github_release(
                "http://api.github.com/releases/latest",
                "pattern",
                self.output_dir,
                release_info,
                download_url="http://example.com/{version}/download.zip",
            )
        self.assertIsNotNone(result)
        if result:
            path, tag = result
            self.assertEqual(tag, "v1.0")
            self.assertEqual(path.name, "dummy.txt")

    def test_download_github_release_with_asset_match(self) -> None:
        release_info = {
            "tag_name": "v2.0",
            "assets": [{"name": "match.zip", "browser_download_url": "http://example.com/match.zip"}],
        }
        fake_func = lambda url, out_dir, filename=None: Path(out_dir) / (filename if filename else "dummy")
        with patch("girsh.core.files.download_package", side_effect=fake_func):
            result = files.download_github_release(
                "http://api.github.com/releases/latest", "match", self.output_dir, release_info
            )
        self.assertIsNotNone(result)
        if result:
            path, tag = result
            self.assertEqual(tag, "v2.0")
            self.assertEqual(path.name, "match.zip")

    def test_download_github_release_with_asset_match_none(self) -> None:
        release_info = {
            "tag_name": "v2.0",
            "assets": [{"name": "match.zip"}],
        }
        fake_func = lambda url, out_dir, filename=None: Path(out_dir) / (filename if filename else "dummy")
        with (
            patch("girsh.core.files.download_package", side_effect=fake_func),
            patch.object(logger, "warning") as mock_logger,
        ):
            result = files.download_github_release(
                "http://api.github.com/releases/latest", "match", self.output_dir, release_info
            )
            mock_logger.assert_called_once_with("No download URL found for asset: match.zip")
        self.assertIsNone(result)

    def test_download_github_release_no_match(self) -> None:
        release_info = {
            "tag_name": "v3.0",
            "assets": [{"name": "nomatch.zip", "browser_download_url": "http://example.com/nomatch.zip"}],
        }
        result = files.download_github_release(
            "http://api.github.com/releases/latest", "pattern", self.output_dir, release_info
        )
        self.assertIsNone(result)

    def test_download_github_release_http_error(self) -> None:
        def fake_get(url: str, headers: dict[str, str], timeout: int) -> Any:
            raise HTTPError("error")

        with patch("requests.get", side_effect=fake_get):
            result = files.download_github_release("http://api.github.com/releases/latest", "pattern", self.output_dir)
        self.assertIsNone(result)

    def test_download_github_release_request_exception(self) -> None:
        def fake_get(url: str, headers: dict[str, str], timeout: int) -> Any:
            raise RequestException("error")

        with patch("requests.get", side_effect=fake_get):
            result = files.download_github_release("http://api.github.com/releases/latest", "pattern", self.output_dir)
        self.assertIsNone(result)

    @patch("girsh.core.files.requests.get")
    def girsh(self, mock_get: Mock) -> None:
        """Test case when raise_for_status() raises an HTTPError."""
        # Mock the response object
        mock_response = Mock()
        mock_get.return_value = mock_response

        # Set up the mock for raise_for_status to raise an HTTPError
        mock_response.raise_for_status.side_effect = requests.HTTPError("HTTP Error")

        # Provide dummy parameters for the function
        url: str = "https://api.github.com/repos/user/repo/releases/latest"
        package_pattern: str = "some_pattern"

        # Call the function and verify if raise_for_status was called and exception is raised
        with self.assertRaises(requests.HTTPError):
            files.download_github_release(url, package_pattern, self.output_dir)

    @patch("girsh.core.files.requests.get")
    def test_download_github_release_success(self, mock_get: Mock) -> None:
        """Test case for a successful download."""
        # Mock the response object for a successful request
        mock_response = Mock()
        mock_get.return_value = mock_response

        # Simulate the response being successful and return JSON data
        mock_response.raise_for_status.return_value = None  # No exception raised
        mock_response.json.return_value = {
            "tag_name": "v1.0.0",
            "assets": [{"name": "asset1.zip", "browser_download_url": "http://example.com/asset1.zip"}],
        }

        # Mock the `iter_content` method of the response to simulate downloading in chunks
        mock_response.iter_content.return_value = [b"chunk1", b"chunk2", b"chunk3"]

        # Provide dummy parameters for the function
        url: str = "https://api.github.com/repos/user/repo/releases/latest"
        package_pattern: str = "asset1"

        # Call the function and assert the expected return value
        result = files.download_github_release(url, package_pattern, self.output_dir)
        self.assertIsNotNone(result)
        self.assertEqual(result[1], "v1.0.0")  # type: ignore[index]


if __name__ == "__main__":
    unittest.main()
